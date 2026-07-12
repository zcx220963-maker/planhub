"""
Agent Runner - 通用 Tool Calling ReAct Agent

被 orchestrator/nodes/assistant.py 调用，负责：
1. 用 supervisor 已解析的 action_type/action_params 构建操作指令
2. 注入对话状态和短期记忆上下文
3. 调用 LangChain create_agent 完成多步工具调用
4. 提取最终回答并更新对话状态

注意：不依赖 service/ 包下的 memory_service / context_service /
error_recovery / fallback / metrics 等已废弃服务。
短期记忆直接通过 MemoryBridge 读写 Redis。
"""

import logging
import re
import time
from typing import Optional

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from app.common.llm_factory import get_llm
from app.common.langchain_tools import ALL_TOOLS, reset_tool_call_counts
from app.service.state import get_conversation_state, ConversationStateEnum
from app.service.memory_bridge import MemoryBridge
from prompts.assistant import ASSISTANT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ─── Langfuse 集成（可观测性）─────────────────────────────────
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False


class AgentRunner:
    """轻量级 Tool Calling Agent 运行器"""

    def __init__(self, temperature: float = 0.7):
        self.temperature = temperature
        self._agent_instance = None
        self._current_session_id = None
        self.memory = MemoryBridge()

        # Langfuse Trace（可选）
        self.langfuse_client = None
        if LANGFUSE_AVAILABLE:
            try:
                from config import settings
                if settings.LANGFUSE_ENABLED:
                    self.langfuse_client = Langfuse(
                        public_key=settings.LANGFUSE_PUBLIC_KEY,
                        secret_key=settings.LANGFUSE_SECRET_KEY,
                        host=settings.LANGFUSE_HOST,
                    )
                    logger.info(f"Langfuse Trace 已启用: {settings.LANGFUSE_HOST}")
            except Exception as e:
                logger.warning(f"Langfuse 初始化失败: {e}")

    def _build_agent(self):
        """构建 LangChain create_agent 实例"""
        from langgraph.checkpoint.memory import MemorySaver

        llm = get_llm(temperature=self.temperature)
        agent = create_agent(
            model=llm,
            tools=ALL_TOOLS,
            system_prompt=ASSISTANT_SYSTEM_PROMPT,
            checkpointer=MemorySaver(),
        )
        return agent.with_config({"recursion_limit": 16})

    @property
    def agent(self):
        if self._agent_instance is None:
            self._agent_instance = self._build_agent()
        return self._agent_instance

    def reset_agent(self):
        self._agent_instance = None

    # ─── 核心入口 ─────────────────────────────────────────────

    async def run_async(
        self,
        user_input: str,
        chat_history: list | None = None,
        session_id: str = "default",
        user_id: str = None,
        action_type: str = "none",
        action_params: dict = None,
    ) -> str:
        """
        执行一次 Tool Calling 对话

        流程：
            1. 从 Redis 读取短期记忆
            2. 构建 action_instruction + 状态上下文
            3. 调用 LangChain agent.invoke 完成工具调用
            4. 将本轮对话写回 Redis
            5. 更新对话状态
        """
        reset_tool_call_counts()
        self._current_session_id = session_id

        # 1. 读取短期记忆 + 偏好
        mem_data = await self.memory.load_memory(session_id, user_id)
        short_term = mem_data.get("short_term_memory", [])
        user_preference = mem_data.get("user_preference")
        conv_state = get_conversation_state(session_id)

        logger.info(f"[Agent 开始] session={session_id}, user={user_id}, action={action_type}")

        # 2. 构建 system prompt
        system_prompt = ASSISTANT_SYSTEM_PROMPT

        if action_type and action_type != "none":
            instruction = self._build_action_instruction(action_type, action_params or {})
            if instruction:
                system_prompt = f"{ASSISTANT_SYSTEM_PROMPT}\n\n{instruction}"

        if conv_state.state != ConversationStateEnum.IDLE:
            state_ctx = conv_state.get_prompt_context()
            system_prompt = f"{system_prompt}\n\n{state_ctx}"

        if user_preference:
            system_prompt = f"{system_prompt}\n\n【用户偏好】\n{user_preference}"

        # 3. 执行
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input),
        ]
        config = {"configurable": {"thread_id": session_id or "default"}}

        try:
            if self.langfuse_client:
                from langfuse import observe

                @observe(name="planhub-agent-run", user_id=user_id or "anonymous",
                         session_id=session_id or "default")
                def _run():
                    return self.agent.invoke({"messages": messages}, config=config)

                result = _run()
                try:
                    self.langfuse_client.flush()
                except Exception:
                    pass
            else:
                result = self.agent.invoke({"messages": messages}, config=config)
        except Exception as e:
            logger.error(f"[Agent 执行异常] {e}", exc_info=True)
            return "抱歉，处理请求时出错了，请稍后再试。"

        all_msgs = result["messages"]
        final_answer = self._extract_final_answer(all_msgs)

        # 4. 保存短期记忆到 Redis
        timestamp = time.time()
        await self.memory.save_memory(
            session_id=session_id,
            user_id=user_id,
            chat_history=[
                {"role": "user", "content": user_input, "timestamp": timestamp},
                {"role": "assistant", "content": final_answer, "timestamp": timestamp + 0.1},
            ],
        )

        # 5. 更新对话状态
        self._update_state_after_response(conv_state, final_answer)

        logger.info(f"[Agent 完成] 回答长度={len(final_answer)}")
        return final_answer

    # ─── 回答提取 ─────────────────────────────────────────────

    def _extract_final_answer(self, all_msgs) -> str:
        """从消息列表中提取最终回答

        优先级：
        1. 本轮第一个有效 ToolMessage（跳过拦截/错误提示）
        2. 本轮最后一个有内容的 AIMessage（去掉 <think> 标签）
        """
        skip_keywords = [
            "本次已调用过", "请勿重复调用", "请直接回复", "已查询过",
            "无需重复调用", "无法识别", "请输入序号", "参数验证失败",
        ]

        last_human_idx = -1
        for i, m in enumerate(all_msgs):
            if isinstance(m, HumanMessage):
                last_human_idx = i
        recent = all_msgs[last_human_idx + 1:] if last_human_idx >= 0 else all_msgs

        # 优先：第一个有效 ToolMessage
        for m in recent:
            if isinstance(m, ToolMessage):
                content = getattr(m, "content", "") or ""
                if content.strip() and not any(kw in content for kw in skip_keywords):
                    return content

        # 兜底：最后一个 AIMessage
        for m in reversed(recent):
            if isinstance(m, AIMessage):
                content = getattr(m, "content", "") or ""
                content = re.sub(r'</?think>.*?</think>\s*', '', content, flags=re.DOTALL).strip()
                if content:
                    return content

        return "抱歉，未能处理您的请求，请稍后再试。"

    # ─── 操作指令构建 ─────────────────────────────────────────

    def _build_action_instruction(self, action_type: str, action_params: dict) -> str:
        """根据 action_type 构建明确的操作指示，告诉 LLM 直接调用工具"""
        lines = ["【上级已识别意图 - 直接执行，不要再猜测意图】"]

        if action_type == "search":
            keyword = action_params.get("keyword", "")
            lines.append("操作类型: 搜索")
            lines.append("应调用工具: search_plans")
            if keyword:
                lines.append(f"已解析关键词: {keyword}")
                lines.append(f"【强制】直接调用 search_plans(keyword=\"{keyword}\")，不要询问，不要回复文本！")
            else:
                lines.append("状态: 缺少关键词，请向用户询问")

        elif action_type == "checkin":
            index = action_params.get("index", 0)
            lines.append("操作类型: 打卡")
            if index:
                lines.append(f"应调用工具: check_in_plan")
                lines.append(f"已选择序号: {index}")
                lines.append(f"【强制】直接调用 check_in_plan(plan_id=\"{index}\")，不要询问，不要回复文本！")
                lines.append(f"【重要】plan_id 直接传序号 \"{index}\"，不要转成真实ID！")
            else:
                lines.append("应调用工具: 先 get_unchecked_plans() 获取列表，等用户选择后再调用 check_in_plan")
                lines.append("【强制】用户说\"打卡\"时，直接调用 get_unchecked_plans()！")

        elif action_type == "post":
            content = action_params.get("content", "")
            title = action_params.get("title", "")
            lines.append("操作类型: 发帖")
            lines.append("应调用工具: create_post")
            if content:
                lines.append(f"已解析内容: {content}")
                lines.append(f"已解析标题: {title}")
                lines.append(f"【强制】直接调用 create_post(content=\"{content}\", hashtags=\"{title or ''}\")！")
            else:
                lines.append("状态: 缺少帖子内容，请向用户询问")

        elif action_type == "detail":
            index = action_params.get("index", 0)
            lines.append(f"操作类型: 选择第 {index} 项")
            lines.append(f"- 如果上一轮是未打卡计划列表，调用 check_in_plan(plan_id=\"{index}\")")
            lines.append(f"- 如果上一轮是搜索结果，调用 get_item_detail(item_type=\"plan\", display_id={index})")
            lines.append("【强制】必须调用工具，不要直接回复文本！")

        elif action_type == "activity":
            lines.append("操作类型: 查看活动")
            lines.append("应调用工具: get_user_activity")
            lines.append("【强制】直接调用 get_user_activity(user_id=当前用户ID)！")

        else:
            lines.append(f"操作类型: {action_type}")
            lines.append("请根据用户输入判断需要调用什么工具")

        lines.append("【重要提醒】意图已识别，直接按指示执行；参数足够立即调用工具，不够则询问用户")
        return "\n".join(lines)

    # ─── 对话状态更新 ─────────────────────────────────────────

    def _update_state_after_response(self, conv_state, final_answer: str):
        """根据 AI 回答内容更新对话状态"""
        success_kw = ["成功", "完成", "已创建", "已发布", "已打卡", "已完成"]
        waiting_kw = ["请告诉我", "请提供", "请输入", "请问", "多少", "什么", "哪个"]
        select_kw = ["请选择", "请回复序号"]
        error_kw = ["失败", "错误", "无效", "找不到"]

        if any(kw in final_answer for kw in success_kw):
            conv_state.transition(ConversationStateEnum.COMPLETED)
            conv_state.reset()
        elif any(kw in final_answer for kw in waiting_kw):
            conv_state.transition(ConversationStateEnum.WAITING_PARAM)
        elif any(kw in final_answer for kw in select_kw):
            conv_state.transition(ConversationStateEnum.WAITING_SELECT)
        elif any(kw in final_answer for kw in error_kw):
            conv_state.set_error(final_answer)


# ─── 全局单例 ─────────────────────────────────────────────────

_agent_runner_instance: Optional[AgentRunner] = None


def get_agent_runner(temperature: float = 0.7) -> AgentRunner:
    """获取 AgentRunner 全局单例"""
    global _agent_runner_instance
    if _agent_runner_instance is None:
        _agent_runner_instance = AgentRunner(temperature=temperature)
    return _agent_runner_instance


# 向后兼容：assistant.py 原来用的接口名
def get_agent_service(temperature: float = 0.7) -> AgentRunner:
    """向后兼容别名，等同于 get_agent_runner()"""
    return get_agent_runner(temperature)


def reset_agent_service():
    """重置全局单例"""
    global _agent_runner_instance
    _agent_runner_instance = None
