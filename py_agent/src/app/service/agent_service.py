"""
PlanHub Tool Calling Agent 服务（P0-6 升级：可观测性 + Trace追踪）

核心改进：
1. 限制历史对话长度，最多保留最近10轮（20条消息），减少token消耗
2. 在 agent.run 时把 ASSISTANT_SYSTEM_PROMPT 作为 SystemMessage 注入到消息开头
3. 每轮对话的所有步骤（用户输入 → 工具调用 → 最终回答）都打印到日志
4. 保留多步对话的上下文，让用户输入"2"时能看到之前的未打卡计划列表
5. 集成记忆系统（短期/工作/长期记忆），让助手更"聪明"
6. 集成上下文工程，优化 Token 消耗
7. 集成错误恢复和降级机制
8. 集成 Langfuse Trace 追踪（可观测性、成本监控、调试能力）

底层模型：阿里云百炼 qwen-max（OpenAI tool calling 兼容），本地 Ollama 为 fallback。
"""

import logging
import time
from typing import Optional

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from app.common.llm_factory import get_llm, reset_token_stats, get_token_stats
from app.common.langchain_tools import ALL_TOOLS
from app.service.conversation_state import get_conversation_state, ConversationStateEnum
from app.service.memory_service import MemoryService
from app.service.context_service import ContextService
from app.service.error_recovery_service import ErrorRecoveryService, ErrorType
from app.service.fallback_service import FallbackService, DegradationLevel
from app.service.metrics_service import MetricsService
from prompts.assistant_prompt import ASSISTANT_SYSTEM_PROMPT

# ─── Langfuse 集成（可观测性）─────────────────────────────────
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    logging.warning("Langfuse 未安装，Trace 追踪功能未启用。安装命令: pip install langfuse")

# 最多保留的历史消息数（用户+助手各10条 = 10轮对话）
MAX_HISTORY_MESSAGES = 20

logger = logging.getLogger(__name__)


class AgentService:
    """Agent 服务类（基于 LangChain create_agent 的多步 ReAct）

    集成功能：
    - 记忆系统（短期/工作/长期记忆）
    - 上下文工程（智能历史过滤、上下文压缩）
    - 错误恢复（智能错误分类和恢复策略）
    - 降级服务（模型降级、功能降级）
    - 性能监控（请求耗时、Token 消耗）
    """

    def __init__(self, temperature: float = 0.7, redis_client=None):
        self.temperature = temperature
        self._agent_instance = None
        self._current_session_id = None

        # 初始化新服务
        self.memory_service = MemoryService(redis_client) if redis_client else None
        self.context_service = ContextService()
        self.error_recovery = ErrorRecoveryService(redis_client)
        self.fallback = FallbackService(redis_client) if redis_client else None
        self.metrics = MetricsService(redis_client) if redis_client else None

        # ─── Langfuse Trace 初始化 ─────────────────────────────
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
                logger.warning(f"Langfuse 初始化失败: {e}，Trace 追踪未启用")

        logger.info("AgentService 初始化完成（含记忆、上下文、错误恢复、降级、监控、Trace）")

    def _build_agent(self, session_id: str = None):
        """构建 LangChain create_agent 实例
        注意：create_agent 内部是一个 state graph，会自动完成
        LLM 调用 → 工具调用 → 工具返回 → 再次调用 LLM 的完整循环。
        """
        print(f"[DEBUG] _build_agent 被调用，构建 agent... session_id={session_id}", flush=True)
        llm = get_llm(temperature=self.temperature)
        print(f"[DEBUG] LLM 类型: {type(llm)}", flush=True)
        print(f"[DEBUG] 工具数量: {len(ALL_TOOLS)}", flush=True)
        print(f"[DEBUG] 工具列表: {[t.name for t in ALL_TOOLS]}", flush=True)

        # 使用 InMemorySaver 来管理对话状态，支持多轮对话
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()

        agent = create_agent(
            model=llm,
            tools=ALL_TOOLS,
            system_prompt=ASSISTANT_SYSTEM_PROMPT,
            checkpointer=checkpointer,
        )
        # 限制最大迭代次数，防止小模型重复调用工具陷入死循环
        # 每次 iteration = 1次 LLM 调用 + 1次工具执行，8 次足够完成"获取列表→选择→打卡"这类多步操作
        agent = agent.with_config({"recursion_limit": 16})
        print(f"[DEBUG] Agent 构建完成，类型: {type(agent)}", flush=True)
        return agent

    @property
    def agent(self):
        if self._agent_instance is None:
            self._agent_instance = self._build_agent()
        return self._agent_instance

    def reset_agent(self):
        """重置 agent 实例（模型或工具配置变化时使用）"""
        self._agent_instance = None

    async def run_async(self, user_input: str, chat_history: list | None = None,
                        session_id: str = "default", user_id: str = None,
                        action_type: str = "none", action_params: dict = None) -> str:
        """
        执行一次对话（异步版本，集成所有优化）

        流程：
            1. 记录指标开始
            2. 获取三层记忆
            3. 构建优化上下文
            4. 执行对话（含错误恢复）
            5. 保存记忆
            6. 记录指标结束

        Args:
            user_input: 用户输入
            chat_history: 历史对话 [{"role": "user"|"assistant", "content": "..."}]
            session_id: 会话ID（用于状态管理）
            user_id: 用户ID（用于长期记忆）
            action_type: 操作类型（supervisor 已解析），如 search/checkin/post/detail/activity
            action_params: 已解析的操作参数（supervisor 已解析）

        Returns:
            AI 回复文本（最终答案）
        """
        # DEBUG: 测试方法是否被调用
        print(f"[DEBUG] run_async 被调用! user_input={user_input[:50]}, action_type={action_type}, action_params={action_params}", flush=True)

        reset_token_stats()

        # 重置工具调用计数，防止跨会话累积
        from app.common.langchain_tools import reset_tool_call_counts
        reset_tool_call_counts()

        self._current_session_id = session_id

        # DEBUG: 测试日志是否能输出
        print(f"[DEBUG] reset_token_stats 完成", flush=True)
        print(f"[DEBUG] 准备记录日志...", flush=True)

        logger.info(f"[run_async] 开始执行，用户输入: {user_input[:100]}")
        logger.info(f"[run_async] session_id={session_id}, user_id={user_id}")

        # 1. 开始记录指标
        request_id = None
        if self.metrics:
            metrics_data = self.metrics.start_request(
                user_id=user_id,
                endpoint="agent.run",
                model="qwen-max"
            )
            request_id = metrics_data.request_id if metrics_data else None

        try:
            # 2. 获取记忆（简化版：只获取对话历史和用户偏好）
            short_term = []
            user_preference = ""

            if self.memory_service:
                short_term = self.memory_service.get_short_term(session_id)
                if user_id:
                    user_preference = self.memory_service.get_user_preference(user_id)

            # 获取对话状态
            conv_state = get_conversation_state(session_id)

            logger.info(f"[Agent 开始] session={session_id}, user={user_id}")
            logger.info(f"[用户输入] {user_input}")
            logger.info(f"[当前状态] {conv_state.state.value}")
            logger.info(f"[记忆统计] 对话历史={len(short_term)} 条")

            # 3. 构建极简上下文（只传必要信息）
            system_prompt = ASSISTANT_SYSTEM_PROMPT
            
            # 如果有 action_type（supervisor 已解析意图），添加明确操作指示
            if action_type and action_type != "none":
                action_instruction = self._build_action_instruction(action_type, action_params or {})
                if action_instruction:
                    system_prompt = f"{ASSISTANT_SYSTEM_PROMPT}\n\n{action_instruction}"
            
            # 如果有对话状态，追加状态上下文
            if conv_state.state != ConversationStateEnum.IDLE:
                state_context = conv_state.get_prompt_context()
                system_prompt = f"{system_prompt}\n\n{state_context}"

            # 使用上下文服务构建优化消息（简化版）
            optimized_context = self.context_service.build_context(
                message=user_input,
                history=short_term or chat_history or [],
                user_preference=user_preference,
                system_prompt=system_prompt
            )

            # 构建 LangChain 消息
            # 注意：不在这里传入所有历史消息，让 MemorySaver 通过 thread_id 自动管理对话状态
            # 只需要传入当前的用户输入，LangGraph 会自动从 checkpointer 恢复之前的对话
            messages = [SystemMessage(content=optimized_context)]
            messages.append(HumanMessage(content=user_input))

            # 4. 执行对话（含错误恢复）
            final_answer = await self._execute_with_recovery(messages, conv_state, user_input, session_id=session_id)

            # 5. 保存对话历史（包含工具调用结果，以支持多轮对话）
            # 注意：必须包含完整的对话历史（用户输入 → 工具调用 → 工具返回 → AI回复）
            # 这样下一轮对话时，AI 才能看到之前的工具调用结果
            if self.memory_service:
                timestamp = time.time()

                # 保存用户输入
                self.memory_service.save_short_term(session_id, {
                    "role": "user",
                    "content": user_input,
                    "timestamp": timestamp
                })

                # 保存AI最终回答
                self.memory_service.save_short_term(session_id, {
                    "role": "assistant",
                    "content": final_answer,
                    "timestamp": timestamp + 0.1
                })

                # 每 10 轮对话更新一次用户偏好（减少写入频率）
                if self.memory_service and user_id and len(short_term) % 10 == 0:
                    self.memory_service.update_user_preference(user_id, short_term)

            # 6. 获取 Token 统计
            stats = get_token_stats()
            logger.info(f"[Token 汇总] calls={stats['llm_calls']} total={stats['total_tokens']}")
            logger.info(f"[最终回答] {final_answer[:200]}")

            # 7. 结束记录指标
            if self.metrics and request_id:
                self.metrics.end_request(request_id, token_count=stats['total_tokens'])

            # 8. 更新对话状态
            self._update_state_after_response(conv_state, final_answer)

            return final_answer

        except Exception as e:
            logger.error(f"[Agent 异常] {e}", exc_info=True)

            # 记录错误指标
            if self.metrics and request_id:
                self.metrics.end_request(request_id, error=str(e))

            # 返回友好错误信息
            return await self._handle_error(e, user_input)

    def run(self, user_input: str, chat_history: list | None = None, session_id: str = "default") -> str:
        """
        执行一次对话（同步版本，向后兼容）

        对于不支持 async 的场景，使用同步方式
        """
        import asyncio

        # 使用 asyncio.run() 创建新的事件循环，避免与现有循环冲突
        return asyncio.run(
            self.run_async(user_input, chat_history, session_id)
        )

    async def _execute_with_recovery(self, messages, conv_state, user_input, session_id: str = None) -> str:
        """执行对话（含错误恢复和降级 + Langfuse Trace）"""
        print(f"[DEBUG] _execute_with_recovery 被调用, session_id={session_id}", flush=True)
        logger.info(f"[执行对话] 开始执行，用户输入: {user_input[:50]}")
        try:
            # 尝试正常执行
            print(f"[DEBUG] 准备调用 agent.invoke，消息数: {len(messages)}", flush=True)
            logger.info(f"[执行对话] 调用 agent.invoke，消息数: {len(messages)}")

            # 构建 config（包含 Langfuse callback）
            config = {"configurable": {"thread_id": session_id or "default"}}

            # ─── 添加 Langfuse Trace 追踪 ─────────────────────
            if self.langfuse_client:
                # 动态设置 user_id 和 session_id
                user_id = "anonymous"
                if conv_state and hasattr(conv_state, 'user_id') and conv_state.user_id:
                    user_id = str(conv_state.user_id)

                # 使用 Langfuse 4.x 的 observe 装饰器模式
                from langfuse import observe

                @observe(name="planhub-agent-run", user_id=user_id, session_id=session_id or "default")
                def run_agent():
                    return self.agent.invoke({"messages": messages}, config=config)

                result = run_agent()
                print(f"[DEBUG] Langfuse Trace 已记录，session_id={session_id}", flush=True)
            else:
                result = self.agent.invoke({"messages": messages}, config=config)

            print(f"[DEBUG] agent.invoke 完成", flush=True)

            # ─── 上报 Trace 到 Langfuse ──────────────────────
            if self.langfuse_client:
                try:
                    self.langfuse_client.flush()
                except Exception as e:
                    logger.warning(f"Langfuse flush 失败: {e}")
            all_msgs = result["messages"]
            print(f"[DEBUG] 返回消息数: {len(all_msgs)}", flush=True)

            # DEBUG: 打印所有返回的消息
            print(f"[DEBUG] ========== 返回的消息 ==========", flush=True)
            for i, msg in enumerate(all_msgs):
                msg_type = type(msg).__name__
                if hasattr(msg, 'content'):
                    content = msg.content[:200] if msg.content else "(空)"
                    print(f"[DEBUG] [{i}] {msg_type}: {content}", flush=True)
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    print(f"[DEBUG] [{i}] 工具调用: {msg.tool_calls}", flush=True)
            print(f"[DEBUG] ==================================", flush=True)

            # DEBUG: 检查是否有工具调用
            has_tool_calls = False
            for msg in all_msgs:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    has_tool_calls = True
                    break

            if not has_tool_calls:
                print(f"[DEBUG]  警告：agent.invoke 返回的消息中没有工具调用！", flush=True)
                print(f"[DEBUG]  这意味着 AI 模型没有调用任何工具，而是直接回复了文本", flush=True)

            logger.info(f"[执行对话] agent.invoke 完成，返回消息数: {len(all_msgs)}")

            # 打印调试信息
            self._log_messages(all_msgs, messages)

            # 提取最终回答
            final_answer = self._extract_final_answer(all_msgs)

            # 记录工具调用指标
            if self.metrics:
                for msg in all_msgs:
                    if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tc in msg.tool_calls:
                            self.metrics.record_tool_call(
                                request_id=self._current_session_id or "unknown",
                                tool_name=tc.get("name", "unknown"),
                                success=True
                            )

            # 打印工具调用和最终答案的详细日志
            logger.info(f"[工具调用详情] 共 {len(all_msgs)} 条消息")
            for idx, msg in enumerate(all_msgs):
                msg_type = type(msg).__name__
                if isinstance(msg, AIMessage):
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tc in msg.tool_calls:
                            logger.info(f"  [{idx}] AI调用工具: {tc.get('name', '?')}, 参数: {tc.get('args', {})}")
                    else:
                        content = getattr(msg, 'content', '(无内容)')
                        logger.info(f"  [{idx}] AI回复: {content[:150]}")
                elif hasattr(msg, 'name') and msg.name:
                    logger.info(f"  [{idx}] 工具返回: {msg.name} -> {str(msg.content)[:100]}")
                else:
                    logger.info(f"  [{idx}] {msg_type}: {str(msg)[:100]}")

            return final_answer

        except Exception as e:
            logger.error(f"[Agent 执行异常] {e}", exc_info=True)

            # 错误恢复策略
            if self.error_recovery:
                strategy, recovery_result = await self.error_recovery.handle_error(e, {
                    "user_input": user_input,
                    "session_id": self._current_session_id,
                    "retry_count": 0
                })

                logger.info(f"[错误恢复] 策略: {strategy.value}")

                # 根据策略执行恢复
                if strategy.value == "retry":
                    # 重试
                    return await self._retry_execution(messages, conv_state)
                elif strategy.value == "fallback_to_backup_model":
                    # 切换到备用模型
                    return await self._fallback_to_backup(messages, conv_state)
                elif strategy.value == "compress_context":
                    # 压缩上下文
                    return await self._compress_and_retry(messages, conv_state)

            # 无法恢复，返回默认回答
            return "抱歉，处理请求时出错了，请稍后再试。"

    async def _retry_execution(self, messages, conv_state, max_retries: int = 2) -> str:
        """重试执行"""
        for attempt in range(max_retries):
            try:
                logger.info(f"[重试] 第 {attempt + 1}/{max_retries} 次")
                result = self.agent.invoke({"messages": messages})
                return self._extract_final_answer(result["messages"])
            except Exception as e:
                logger.warning(f"[重试失败] 第 {attempt + 1} 次: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避

        return "抱歉，多次尝试后仍无法处理您的请求。"

    async def _fallback_to_backup(self, messages, conv_state) -> str:
        """切换到备用模型"""
        logger.info("[降级] 切换到备用模型")

        if self.fallback:
            # 使用降级服务
            try:
                result = await self.fallback.call_with_fallback(
                    messages=[{"role": "user", "content": msg.content} for msg in messages if isinstance(msg, HumanMessage)],
                    primary_func=lambda msgs, tools=None: self.agent.invoke({"messages": msgs})
                )
                return result.get("content", "抱歉，备用模型也无法处理您的请求。")
            except Exception as e:
                logger.error(f"[降级失败] {e}")

        return "抱歉，当前服务暂时不可用，请稍后再试。"

    async def _compress_and_retry(self, messages, conv_state) -> str:
        """压缩上下文后重试"""
        logger.info("[压缩] 压缩上下文后重试")

        # 压缩历史消息
        system_msg = messages[0] if messages and isinstance(messages[0], SystemMessage) else None
        human_msg = messages[-1] if messages and isinstance(messages[-1], HumanMessage) else None

        if system_msg and human_msg:
            # 只保留系统提示和当前输入
            compressed_messages = [system_msg, human_msg]

            try:
                result = self.agent.invoke({"messages": compressed_messages})
                return self._extract_final_answer(result["messages"])
            except Exception as e:
                logger.error(f"[压缩重试失败] {e}")

        return "抱歉，处理请求时出错了，请稍后再试。"

    async def _handle_error(self, error: Exception, user_input: str) -> str:
        """处理错误并返回友好信息"""
        if self.error_recovery:
            strategy, result = await self.error_recovery.handle_error(error, {
                "user_input": user_input,
                "session_id": self._current_session_id
            })

        # 根据错误类型返回友好信息
        error_type = self.error_recovery.classify_error(error) if self.error_recovery else ErrorType.UNKNOWN

        error_messages = {
            ErrorType.TIMEOUT: "抱歉，请求超时了，请稍后再试。",
            ErrorType.RATE_LIMIT: "当前请求过于频繁，请稍后再试。",
            ErrorType.SERVICE_UNAVAILABLE: "服务暂时不可用，请稍后再试。",
            ErrorType.INVALID_RESPONSE: "抱歉，处理请求时出错了，请重新描述您的问题。",
            ErrorType.CONTEXT_TOO_LONG: "对话历史太长，请开启新对话。",
            ErrorType.TOOL_ERROR: "工具调用失败，请重试。",
            ErrorType.UNKNOWN: "抱歉，处理请求时出错了，请稍后再试。",
        }

        return error_messages.get(error_type, "抱歉，处理请求时出错了，请稍后再试。")

    def _log_messages(self, all_msgs, input_messages):
        """打印消息调试信息"""
        new_msgs = all_msgs[len(input_messages):]
        for idx, m in enumerate(new_msgs):
            if isinstance(m, AIMessage):
                if hasattr(m, "tool_calls") and m.tool_calls:
                    tool_names = [tc.get("name", "?") for tc in m.tool_calls]
                    logger.info(f"[Action #{idx + 1}] 模型调用工具: {tool_names}")
                else:
                    content = (m.content if hasattr(m, "content") else str(m)) or ""
                    logger.info(f"[Answer #{idx + 1}] 模型回复: {content[:150]}")
            elif isinstance(m, ToolMessage):
                tool_name = getattr(m, "name", "?")
                content = str(m.content)[:120] if m.content else "(空)"
                logger.info(f"[Observation #{idx + 1}] 工具 {tool_name} 返回: {content}")

    def _build_action_instruction(self, action_type: str, action_params: dict) -> str:
        """
        根据 action_type 构建明确的操作指示，告诉 LLM 应该做什么、调用哪个工具、已经有哪些参数。
        这样 LLM 不需要再猜意图，直接根据指示调用工具即可。
        """
        lines = []
        lines.append("【上级已识别意图 - 直接执行，不要再猜测意图】")
        
        if action_type == "search":
            keyword = action_params.get("keyword", "")
            lines.append(f"操作类型: 搜索")
            lines.append(f"应调用工具: search_plans")
            if keyword:
                lines.append(f"已解析关键词: {keyword}")
                lines.append(f"【强制】直接调用 search_plans(keyword=\"{keyword}\")，不要询问，不要回复文本！")
            else:
                lines.append("状态: 缺少关键词")
                lines.append("请向用户询问要搜索的关键词")
        
        elif action_type == "checkin":
            index = action_params.get("index", 0)
            lines.append("操作类型: 打卡")
            if index:
                lines.append(f"应调用工具: check_in_plan")
                lines.append(f"已选择序号: {index}")
                lines.append(f"【强制】直接调用 check_in_plan(plan_id=\"{index}\")，不要询问，不要回复文本！")
                lines.append(f"【重要】plan_id 直接传序号 \"{index}\"，不要转成真实ID，工具内部自动处理！")
            else:
                lines.append("应调用工具: 先 get_unchecked_plans() 获取列表，等用户选择后再调用 check_in_plan")
                lines.append("【强制】用户说\"打卡\"/\"我要打卡\"时，直接调用 get_unchecked_plans()，不要询问，不要回复文本！")
        
        elif action_type == "post":
            content = action_params.get("content", "")
            title = action_params.get("title", "")
            lines.append("操作类型: 发帖")
            lines.append("应调用工具: create_post")
            if content:
                lines.append(f"已解析内容: {content}")
            if title:
                lines.append(f"已解析标题/标签: {title}")
            if content:
                lines.append(f"【强制】直接调用 create_post(content=\"{content}\", hashtags=\"{title or ''}\")，不要询问，不要回复文本！")
            else:
                lines.append("状态: 缺少帖子内容")
                lines.append("请向用户询问帖子内容")
        
        elif action_type == "detail":
            index = action_params.get("index", 0)
            lines.append(f"操作类型: 选择第 {index} 项")
            lines.append(f"应调用工具: 根据上下文判断")
            lines.append(f"- 如果上一轮是未打卡计划列表，调用 check_in_plan(plan_id=\"{index}\")")
            lines.append(f"- 如果上一轮是搜索结果，调用 get_item_detail(item_type=\"plan\", display_id={index})")
            lines.append(f"【强制】必须调用工具，不要直接回复文本！")
            lines.append(f"【重要】plan_id 直接传序号 \"{index}\"，不要转成真实ID，工具内部自动处理！")
        
        elif action_type == "activity":
            lines.append("操作类型: 查看活动")
            lines.append("应调用工具: get_user_activity")
            lines.append("【强制】直接调用 get_user_activity(user_id=当前用户ID)，不要询问，不要回复文本！")
        
        else:
            lines.append(f"操作类型: {action_type}")
            lines.append("请根据用户输入判断需要调用什么工具")
        
        lines.append("【重要提醒】")
        lines.append("- 意图已经识别好了，不要再猜测用户意图，直接按上面的指示执行")
        lines.append("- 如果参数足够，立即调用工具，不要回复文本")
        lines.append("- 如果参数不够，向用户询问缺失的参数")
        
        return "\n".join(lines)

    def _extract_final_answer(self, all_msgs) -> str:
        """从消息列表中提取最终回答

        逻辑：
        1. 先找到最后一条 HumanMessage（用户输入），只看它之后的消息
        2. 优先返回本轮第一个有效 ToolMessage（用户主要需求对应的工具结果）
           - 跳过拦截提示和错误提示类 ToolMessage
        3. 如果没有有效 ToolMessage，返回本轮最后一个有内容的 AIMessage
        """
        # 拦截/错误提示的关键词（这些 ToolMessage 不是真实结果）
        skip_keywords = [
            "本次已调用过", "请勿重复调用", "请直接回复", "已查询过", "无需重复调用",
            "无法识别", "请输入序号", "参数验证失败"
        ]

        # 1. 找到最后一条 HumanMessage 的位置，只看它之后的消息
        last_human_idx = -1
        for i, m in enumerate(all_msgs):
            if isinstance(m, HumanMessage):
                last_human_idx = i

        recent_msgs = all_msgs[last_human_idx + 1:] if last_human_idx >= 0 else all_msgs

        # 2. 优先返回本轮第一个有效 ToolMessage
        first_valid_tool_msg = None
        for m in recent_msgs:
            if isinstance(m, ToolMessage):
                content = m.content if hasattr(m, "content") else str(m)
                if content and content.strip():
                    if any(kw in content for kw in skip_keywords):
                        continue
                    first_valid_tool_msg = content
                    break

        if first_valid_tool_msg:
            print(f"[DEBUG] _extract_final_answer: 使用本轮第一个 ToolMessage: {first_valid_tool_msg[:100]}", flush=True)
            return first_valid_tool_msg

        # 3. 否则，返回本轮最后一个有内容的 AIMessage
        for m in reversed(recent_msgs):
            if isinstance(m, AIMessage):
                content = m.content if hasattr(m, "content") else str(m)
                if content and content.strip():
                    # 去掉 <think> 标签内容
                    import re
                    content = re.sub(r'</?think>.*?</think>\s*', '', content, flags=re.DOTALL)
                    content = content.strip()
                    if content:
                        print(f"[DEBUG] _extract_final_answer: 使用 AIMessage: {content[:100]}", flush=True)
                        return content

        return "抱歉，未能处理您的请求，请稍后再试。"

    def _convert_history(self, chat_history: list | None) -> list:
        """
        转换历史消息格式（兼容纯文本 user/assistant）
        只保留最近 MAX_HISTORY_MESSAGES 条消息，减少 token 消耗
        """
        messages = []
        for msg in (chat_history or []):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))

        # 只保留最近的消息
        return messages[-MAX_HISTORY_MESSAGES:]

    def _update_state_after_response(self, conv_state, final_answer: str):
        """
        根据AI的最终回答更新对话状态

        简单判断：
        - 如果回答包含"成功"、"完成"等关键词 → 任务完成
        - 如果回答包含"失败"、"错误"等关键词 → 任务失败
        - 如果回答包含"请告诉我"、"请提供"等关键词 → 仍在等待参数
        """
        final_answer_lower = final_answer.lower()

        # 任务完成标志
        success_keywords = ["成功", "完成", "已创建", "已发布", "已打卡", "已完成"]
        waiting_keywords = ["请告诉我", "请提供", "请输入", "请问", "多少", "什么", "哪个"]
        select_keywords = ["请选择", "请回复序号"]
        error_keywords = ["失败", "错误", "无效", "找不到"]

        if any(kw in final_answer for kw in success_keywords):
            conv_state.transition(ConversationStateEnum.COMPLETED)
            conv_state.reset()  # 完成后重置状态
        elif any(kw in final_answer for kw in waiting_keywords):
            conv_state.transition(ConversationStateEnum.WAITING_PARAM)
        elif any(kw in final_answer for kw in select_keywords):
            conv_state.transition(ConversationStateEnum.WAITING_SELECT)
        elif any(kw in final_answer for kw in error_keywords):
            conv_state.set_error(final_answer)
            # 保持在当前状态，允许重试


# 全局单例
_agent_service_instance = None


def get_agent_service(temperature: float = 0.7) -> AgentService:
    global _agent_service_instance
    if _agent_service_instance is None:
        # 使用 Redis 来持久化对话历史
        from app.dao.redis_dao import get_redis_client
        redis_client = get_redis_client()
        _agent_service_instance = AgentService(temperature=temperature, redis_client=redis_client)
    return _agent_service_instance


def reset_agent_service():
    """重置全局单例（配置变更时调用）"""
    global _agent_service_instance
    _agent_service_instance = None
