"""
聊天接口路由

提供简单的对话功能，支持流式和非流式响应。
新增：计划生成接口（/chat/plan），支持多轮对话和 RAG 集成。
"""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from typing import Union, Optional, List, Dict, Any

from app.common.llm_factory import get_llm
from app.dao.redis_dao import (
    get_chat_history,
    add_chat_message,
    get_redis_client,
)
from app.skills import (
    detect_plan_type,
    handle_ambiguous_plan_type,
    PlanInfoCollector,
    PlanInfoCollectorManager,
    generate_plan,
    call_apis_for_plan,
    preview_apis_to_call,
    extract_info_from_input,
)
from prompts.assistant_prompt import CHAT_SYSTEM_PROMPT

# 语言规范：专业术语可保留英文，但普通词汇必须用中文
_LANGUAGE_RULES = """
【语言规范】
- 使用中文回答，确保语句通顺自然
- 专业术语可保留英文原词（如：AI、API、HTTP、Python、Docker、OK 等）
- 普通词汇必须翻译为中文（如：lasting → 持久/深远，user → 用户，error → 错误）
- 避免中英混杂的句子结构，如"产生 lasting 影响"应改为"产生持久影响"或"产生深远影响"
"""

router = APIRouter(prefix="/chat")


# ─── 请求/响应模型 ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_history: list = []
    model: str = "deepseek-r1:7b"
    temperature: float = 0.7
    session_id: Optional[str] = None
    user_id: Optional[Union[str, int]] = None
    use_rag: bool = False  # 是否启用知识库查询
    doc_ids: Optional[List[str]] = None  # 指定查询的文档ID列表

    @field_validator("user_id", mode="before")
    @classmethod
    def convert_user_id(cls, v):
        if v is None:
            return None
        return str(v)


class ChatResponse(BaseModel):
    response: str
    session_id: str = None


class SimpleChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[Union[str, int]] = None

    @field_validator("user_id", mode="before")
    @classmethod
    def convert_user_id(cls, v):
        if v is None:
            return None
        return str(v)


# ─── 工具函数 ────────────────────────────────────────────────────

def _build_context_summary(history: List[Dict[str, Any]], max_turns: int = 10) -> str:
    """从对话历史中提取上下文摘要

    Args:
        history: 对话历史记录
        max_turns: 最多保留的对话轮数

    Returns:
        上下文摘要文本
    """
    if not history:
        return ""

    # 只保留最近的 N 轮对话
    recent_history = history[-(max_turns * 2):]  # 每轮 = user + assistant

    # 提取关键信息（如用户目标、偏好、已提供的信息）
    context_parts = []
    for msg in recent_history:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            # 跳过简单的确认消息（如"确认"、"是的"）
            if content.strip() in ["确认", "确定", "是的", "对", "可以", "ok", "OK"]:
                continue
            # 跳过包含知识库引用的消息（避免重复）
            if "[来源:" in content:
                continue
            context_parts.append(f"用户说：{content}")
        elif msg.get("role") == "assistant":
            content = msg.get("content", "")
            # 跳过简单的确认消息
            if len(content) < 20:
                continue
            # 跳过包含知识库引用的消息
            if "[来源:" in content:
                continue
            context_parts.append(f"助手回复：{content[:200]}")  # 截断过长的回复

    if not context_parts:
        return ""

    return "\n".join(context_parts)

def _build_prompt(system_prompt: str, history: List[Dict[str, Any]],
                  conversation_history: List[Dict[str, Any]], message: str,
                  max_history_turns: int = 20, use_rag: bool = False) -> str:
    """构建完整的提示词

    Args:
        system_prompt: 系统提示词
        history: 从 Redis 获取的历史记录（可能包含知识库内容）
        conversation_history: 当前会话的对话历史（可能包含知识库内容）
        message: 用户当前消息
        max_history_turns: 最多保留的对话轮数（默认20轮 = 40条消息）
        use_rag: 是否启用知识库模式（影响是否过滤知识库历史）
    """
    # 系统提示词 + 语言规范
    prompt = system_prompt + "\n\n" + _LANGUAGE_RULES + "\n\n"

    # 如果关闭了知识库模式，过滤掉 history 和 conversation_history 中的知识库引用
    # 这样可以避免 LLM 在普通对话模式下引用之前的知识库内容
    def _filter_knowledge_base_refs(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤掉包含知识库引用的消息"""
        if use_rag:
            return messages  # 开启知识库时不过滤

        filtered = []
        for msg in messages:
            content = msg.get("content", "")
            # 过滤掉包含 [来源:...] 的消息（如 [来源: 中二知识笔记.pdf#0]）
            if "[来源:" in content:
                continue
            filtered.append(msg)
        return filtered

    # 从 Redis 获取的历史记录（过滤后）
    filtered_history = _filter_knowledge_base_refs(history)

    # 从请求中携带的对话历史（过滤后）
    filtered_conversation_history = _filter_knowledge_base_refs(conversation_history)

    # 优先使用 conversation_history（当前会话的上下文），如果为空则使用 history
    if filtered_conversation_history:
        # 只保留最近的 N 轮对话
        recent_history = filtered_conversation_history[-max_history_turns * 2:]  # 每轮 = user + assistant
        for msg in recent_history:
            if msg.get("role") == "user":
                prompt += f"用户: {msg.get('content', '')}\n"
            elif msg.get("role") == "assistant":
                prompt += f"助手: {msg.get('content', '')}\n"
    elif filtered_history:
        # 如果 conversation_history 为空，使用 Redis 中的历史（过滤后）
        recent_history = filtered_history[-max_history_turns * 2:]
        for msg in recent_history:
            if msg.get("role") == "user":
                prompt += f"用户: {msg.get('content', '')}\n"
            elif msg.get("role") == "assistant":
                prompt += f"助手: {msg.get('content', '')}\n"

    prompt += f"用户: {message}\n助手:"
    return prompt


# ─── API 接口 ───────────────────────────────────────────────────

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口（服务器推送事件 SSE 格式）

    返回 SSE 格式的数据，前端可以解析实现打字机效果。

    新增功能：
    - use_rag=true 时，优先查询知识库
    - 知识库有相关内容时返回 RAG 回答
    - 知识库无相关内容时回退到普通对话
    """
    try:
        print(f"[DEBUG] chat_stream called - session_id: {request.session_id}, user_id: {request.user_id}, use_rag: {request.use_rag}")

        # 确保 user_id 是字符串
        user_id_str = str(request.user_id) if request.user_id else None

        # ─── 普通对话模式 ──────────────────────────────────
        llm = get_llm(request.temperature, force_ollama=True)

        # 从 Redis 获取历史记录
        history = []
        if request.session_id:
            history = get_chat_history(request.session_id)
            print(f"[DEBUG] Loaded {len(history)} messages from history")

        # 构建提示词（只使用当前会话的上下文历史，避免其他会话的知识库内容污染）
        # 注意：use_rag 参数会影响是否过滤知识库历史
        # - use_rag=true：保留所有历史（包括知识库内容）
        # - use_rag=false：过滤掉包含 [来源:...] 的历史消息
        prompt = _build_prompt(
            CHAT_SYSTEM_PROMPT,
            history,
            request.conversation_history,
            request.message,
            max_history_turns=20,  # 只保留最近20轮对话
            use_rag=request.use_rag  # 传递知识库开关状态
        )

        # 保存用户消息
        if request.session_id:
            print(f"[DEBUG] Saving user message to session: {request.session_id}")
            add_chat_message(
                request.session_id,
                "user",
                request.message,
                user_id=user_id_str,
                module="chat"
            )

        # ─── 生成器：流式返回 SSE 格式 ────────────────────────
        def generate():
            full_response = ""
            try:
                for chunk in llm.stream(prompt):
                    # 修复：正确提取 chunk 的内容
                    # chunk 可能是 AIMessage 对象，需要提取其 content 属性
                    if hasattr(chunk, 'content'):
                        chunk_text = chunk.content
                    elif isinstance(chunk, dict) and 'content' in chunk:
                        chunk_text = chunk['content']
                    else:
                        chunk_str = str(chunk)
                        # 如果 chunk_str 包含 LangChain 的 AIMessage 格式，跳过
                        if chunk_str.startswith("AIMessage") or "response_metadata" in chunk_str:
                            continue
                        chunk_text = chunk_str

                    if chunk_text:
                        full_response += chunk_text
                        # 返回 SSE 格式：data: {"content": "..."}
                        data = json.dumps({"content": chunk_text, "done": False}, ensure_ascii=False)
                        yield f"data: {data}\n\n"

                # 发送完成信号
                if full_response:
                    # 保存助手回复
                    if request.session_id:
                        print(f"[DEBUG] Saving assistant response to session: {request.session_id}")
                        add_chat_message(
                            request.session_id,
                            "assistant",
                            full_response,
                            user_id=user_id_str,
                            module="chat"
                        )

                yield f"data: {json.dumps({'content': '', 'done': True}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                print(f"[ERROR] Stream generation failed: {e}")
                yield f"data: {json.dumps({'error': str(e), 'done': True}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )

    except Exception as e:
        print(f"[ERROR] chat_stream failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """非流式聊天接口"""
    try:
        user_id_str = str(request.user_id) if request.user_id else None
        llm = get_llm(request.temperature, force_ollama=True)

        history = []
        if request.session_id:
            history = get_chat_history(request.session_id)

        prompt = _build_prompt(
            CHAT_SYSTEM_PROMPT,
            history,
            request.conversation_history,
            request.message,
            max_history_turns=20,  # 只保留最近20轮对话
            use_rag=request.use_rag  # 传递知识库开关状态
        )

        response = llm.predict(prompt)

        # 修复：确保 response 是字符串
        if hasattr(response, 'content'):
            response = response.content
        elif not isinstance(response, str):
            response = str(response)

        if request.session_id:
            add_chat_message(request.session_id, "user", request.message, user_id=user_id_str, module="chat")
            add_chat_message(request.session_id, "assistant", response, user_id=user_id_str, module="chat")

        return ChatResponse(response=response, session_id=request.session_id or "new_session")

    except Exception as e:
        print(f"[ERROR] chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_chat_history_api(session_id: str):
    """获取对话历史记录"""
    try:
        print(f"[DEBUG] get_chat_history called - session_id: {session_id}")
        history = get_chat_history(session_id)
        print(f"[DEBUG] Found {len(history)} messages in history")
        return {
            "session_id": session_id,
            "history": history or []
        }
    except Exception as e:
        print(f"[ERROR] get_chat_history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def chat_simple(request: SimpleChatRequest):
    """简化版聊天接口（兼容前端调用）"""
    try:
        user_id_str = str(request.user_id) if request.user_id else None
        llm = get_llm(0.7, force_ollama=True)

        prompt = CHAT_SYSTEM_PROMPT + "\n\n用户: " + request.message + "\n助手:"
        response = llm.predict(prompt)

        # 修复：确保 response 是字符串
        if hasattr(response, 'content'):
            response = response.content
        elif not isinstance(response, str):
            response = str(response)

        if request.session_id:
            add_chat_message(request.session_id, "user", request.message, user_id=user_id_str, module="chat")
            add_chat_message(request.session_id, "assistant", response, user_id=user_id_str, module="chat")

        return {"response": response, "session_id": request.session_id or "new_session"}

    except Exception as e:
        print(f"[ERROR] chat_simple failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── 辅助函数 ────────────────────────────────────────────────────

def _is_confirmation(message: str) -> bool:
    """检查用户是否确认"""
    confirmation_keywords = [
        "确认", "确定", "是的", "没错", "对", "可以", "好的", "yes", "ok",
        "没问题", "就是这样", "开始", "生成", "创建"
    ]
    message_lower = message.lower().strip()
    return any(keyword in message_lower for keyword in confirmation_keywords)

def _try_update_field(message: str, collector: PlanInfoCollector) -> Optional[str]:
    """
    尝试从用户消息中解析字段更新
    支持格式：
    - "第3个改成XX" / "第3个是XX"
    - "身高改成180" / "身高是180"
    - "把身高改为180"
    """
    import re

    field_names = {
        "topic": "学习主题",
        "goal": "目标",
        "duration": "时长",
        "daily_hours": "每天学习时间",
        "level": "基础水平",
        "activity_level": "运动强度",
        "height": "身高",
        "weight": "体重",
        "age": "年龄",
        "gender": "性别",
        "city": "所在城市",
        "location": "所在城市",
        "destination": "目的地",
        "days": "天数",
        "budget": "预算",
        "interests": "兴趣",
        "departure_date": "出发日期",
        "target_currency": "目标币种",
        "task": "任务",
        "team_size": "团队规模",
        "deadline": "截止日期",
        "monthly_income": "月收入",
        "current_savings": "当前存款",
    }

    message_lower = message.lower().strip()

    # 模式1: "第N个改成XX" 或 "第N个是XX"
    match = re.search(r'第(\d+)\s*个\s*(?:改成|是|改为|设为)\s*(.+)', message)
    if match:
        index = int(match.group(1)) - 1  # 转换为 0-based index
        new_value = match.group(2).strip()
        if index < len(collector.required_fields):
            field = collector.required_fields[index]
            if collector.update_field(field, new_value):
                return f"已将 {field_names.get(field, field)} 更新为 {new_value}"

    # 模式2: "身高改成180" 或 "把身高改为180"
    for field, field_name in field_names.items():
        # 匹配 "XX改成YY" 或 "把XX改为YY" 或 "XX是YY"
        patterns = [
            rf'{field_name}\s*(?:改成|改为|设为|是)\s*(.+)',
            rf'把{field_name}\s*(?:改成|改为|设为)\s*(.+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                new_value = match.group(1).strip()
                if collector.update_field(field, new_value):
                    return f"已将 {field_name} 更新为 {new_value}"

    return None

# ─── 计划生成接口 ─────────────────────────────────────────────────

@router.post("/plan")
async def chat_plan(request: ChatRequest):
    """
    计划生成接口（支持多轮对话 + RAG）

    功能：
    1. 检测用户意图（学习/健康/旅行/工作/财务计划）
    2. 多轮对话收集信息（状态机）
    3. 调用外部 API 获取数据
    4. 生成结构化计划文本
    5. 支持 RAG 集成（知识库 + 计划模式组合）

    请求参数：
    - message: 用户消息
    - session_id: 会话 ID（用于多轮对话）
    - user_id: 用户 ID
    - use_rag: 是否启用知识库查询
    - doc_ids: 指定查询的文档 ID 列表

    返回：
    - response: 计划文本或追问
    - session_id: 会话 ID
    """
    try:
        user_id_str = str(request.user_id) if request.user_id else None
        session_id = request.session_id or f"plan:{user_id_str}:{int(__import__('time').time() * 1000)}"

        print(f"[DEBUG] chat_plan called - session_id: {session_id}, user_id: {user_id_str}, use_rag: {request.use_rag}")

        # 1. 获取 Redis 客户端
        redis_client = get_redis_client()
        if not redis_client:
            return {"response": "抱歉，服务暂时不可用，请稍后再试。", "session_id": session_id}

        # 2. 获取历史记录（与普通对话共享上下文）
        history = get_chat_history(session_id)
        print(f"[DEBUG] Loaded {len(history)} messages from history")

        # 3. 创建计划收集器管理器
        collector_manager = PlanInfoCollectorManager(redis_client)

        # 4. 获取或恢复信息收集器
        print(f"[DEBUG] Trying to restore collector from Redis with key: plan:collector:{session_id}")
        collector = collector_manager.restore_collector(session_id)
        print(f"[DEBUG] Restore result: {collector}")

        if collector is None:
            # 新的计划请求
            plan_type = detect_plan_type(request.message)

            # 检查是否是模糊匹配（多意图冲突）
            if plan_type and plan_type.startswith("__AMBIGUOUS__"):
                # 追问用户确认
                question = handle_ambiguous_plan_type(request.message, session_id)

                # 保存对话历史（使用 module="chat" 以便在 Chatbot 会话历史中显示）
                add_chat_message(session_id, "user", request.message, user_id=user_id_str, module="chat")
                add_chat_message(session_id, "assistant", question, user_id=user_id_str, module="chat")

                return {"response": question, "session_id": session_id}

            # 检查是否是 unknown（无法识别）
            if plan_type is None or plan_type == "unknown":
                return {
                    "response": "抱歉，我不太明白你的需求。请说'制定学习计划'、'制定旅行计划'、'制定健康计划'、'制定工作计划'或'制定财务计划'。",
                    "session_id": session_id
                }

            # 创建新的收集器
            collector = PlanInfoCollector(plan_type)
            print(f"[DEBUG] Created new collector for plan_type: {plan_type}")

            # 立即保存收集器到 Redis
            collector_manager.save_collector(session_id, collector)
            print(f"[DEBUG] Saved new collector to Redis")

            # 一次性生成所有必填字段的问题
            all_questions = collector.get_all_questions_once()
            print(f"[DEBUG] Generated {len(collector.required_fields)} questions at once")

            # 如果开启了 RAG，先查询知识库（第一次触发：用用户触发词做初版检索）
            rag_context = None
            if request.use_rag:
                rag_context = await _query_rag_for_plan(
                    topic=request.message[:30],   # 第一次触发：用原始消息前30字作为粗 topic
                    goal="",
                    plan_type=plan_type,
                    session_id=session_id,
                    user_id=user_id_str,
                    doc_ids=request.doc_ids,
                )
                if rag_context:
                    print(f"[DEBUG] RAG context added: {len(rag_context)} chars")

            # 构建上下文历史摘要（从当前会话历史中提取相关信息）
            # 注意：_build_context_summary 会自动过滤掉包含 [来源:...] 的消息
            context_summary = _build_context_summary(history, max_turns=10)

            # 如果关闭了知识库模式，确保上下文摘要中也不包含知识库引用
            # （_build_context_summary 已经做了这个过滤，但这里再确认一下）
            if not request.use_rag and context_summary:
                # 移除可能包含 [来源:...] 的行
                lines = context_summary.split('\n')
                filtered_lines = [line for line in lines if '[来源:' not in line]
                context_summary = '\n'.join(filtered_lines)

            # 将知识库内容和上下文历史都保存到收集器中
            # 重要：不要覆盖之前保存的 rag_context 和 context_summary！
            # 只有当之前没有保存过，且本次请求查询到时，才保存
            existing_rag_context = collector.get_rag_context()
            existing_context_summary = collector.get_context_summary()

            if not existing_rag_context and rag_context:
                # 之前没有 rag_context，本次查询到了，保存
                collector.set_rag_context(rag_context, context_summary)
                print(f"[DEBUG] RAG context added: {len(rag_context)} chars")
            elif not existing_context_summary and context_summary:
                # 之前没有 context_summary，本次查询到了，保存（保留现有的 rag_context）
                collector.set_rag_context(existing_rag_context, context_summary)
                print(f"[DEBUG] Context summary added: {len(context_summary)} chars")
            else:
                # 之前已经保存过，不覆盖
                print(f"[DEBUG] Keeping existing rag_context: {len(existing_rag_context or '')} chars, context_summary: {len(existing_context_summary or '')} chars")

            # 保存对话历史（使用 module="chat" 以便在 Chatbot 会话历史中显示）
            add_chat_message(session_id, "user", request.message, user_id=user_id_str, module="chat")

            # 构建回复：显示必填字段 + 委婉询问是否需要额外信息
            from app.skills.plan_generator import get_suggestions_for_plan
            suggestions = get_suggestions_for_plan(plan_type)

            response = f"好的，{plan_type}计划！\n\n"
            response += f"请告诉我以下必填信息（可以一次性回答）：\n\n{all_questions}\n\n"

            if suggestions:
                response += f"💡 {suggestions}\n"

            add_chat_message(session_id, "assistant", response, user_id=user_id_str, module="chat")

            return {"response": response, "session_id": session_id}

        else:
            # 继续收集信息或修改字段
            # 检查用户是否确认
            if _is_confirmation(request.message) and collector.is_complete():
                # 用户确认且信息收集完毕，进入生成阶段
                print(f"[DEBUG] User confirmed, generating plan")

                # 生成计划
                plan_info = collector.get_collected_info()
                plan_type = collector.plan_type
                topic = plan_info.get("topic", "")
                goal = plan_info.get("goal", "")

                # ===== 1) 知识库优先查询（开启RAG时，用真实的 topic+goal 做高质量检索）=====
                rag_context = collector.get_rag_context()
                if request.use_rag:
                    print(f"[INFO] 知识库优先检索 - topic='{topic}', goal='{goal}'")
                    fresh_rag = await _query_rag_for_plan(
                        topic=topic,
                        goal=goal,
                        plan_type=plan_type,
                        session_id=session_id,
                        user_id=user_id_str,
                        doc_ids=request.doc_ids,
                    )
                    if fresh_rag:
                        rag_context = fresh_rag  # 用新检索覆盖（更精准）
                        collector.set_rag_context(rag_context, collector.get_context_summary())
                        print(f"[INFO] 知识库新检索命中: {len(rag_context)} 字符")
                    else:
                        print("[INFO] 知识库未命中，保留已有 rag_context（如有）")

                context_summary = collector.get_context_summary()

                print(f"[DEBUG] Generating plan - type: {plan_type}, info: {plan_info}")
                print(f"[DEBUG] RAG context: {len(rag_context) if rag_context else 0} chars")
                print(f"[DEBUG] Context summary: {len(context_summary) if context_summary else 0} chars")

                # ===== 2) 调用外部 API（查询词直接从知识库片段内容中提取）=====
                plan_info_with_rag = dict(plan_info)
                if rag_context:
                    plan_info_with_rag["_rag_context"] = rag_context

                selected_optional_apis = collector.get_selected_optional_apis()
                api_results = call_apis_for_plan(plan_type, plan_info_with_rag, selected_optional_apis)
                print(f"[DEBUG] API results keys: {list(api_results.keys())}")

                # ===== 3) 生成计划文本（LLM 结合知识库片段 + API 结果 + 用户填写字段）=====
                # 注意：rag_context 单独作为参数传入，与 plan_info 分离
                from app.skills.plan_generator import generate_plan_with_llm
                plan_text = generate_plan_with_llm(plan_type, plan_info, api_results, rag_context)

                # 清除收集器
                collector_manager.delete_collector(session_id)

                # 保存助手回复（使用 module="chat" 以便在 Chatbot 会话历史中显示）
                add_chat_message(session_id, "assistant", plan_text, user_id=user_id_str, module="chat")

                print(f"[DEBUG] Plan generated: {len(plan_text)} chars")
                return {"response": plan_text, "session_id": session_id}

            else:
                # 不是确认，尝试从用户消息中提取信息或修改字段
                # 1. 首先检查是否是修改某个字段（如"第3个改成XX"或"身高改成180"）
                update_result = _try_update_field(request.message, collector)

                if update_result:
                    # 字段已更新，展示更新后的信息
                    print(f"[DEBUG] Field updated: {update_result}")
                else:
                    # 2. 不是修改，尝试提取信息填充缺失字段
                    extracted_info = extract_info_from_input(request.message, collector.plan_type)

                    # 获取缺失的字段
                    missing_fields = collector.get_missing_fields()

                    # 用提取的信息填充缺失字段
                    filled_count = 0
                    for field in missing_fields:
                        if field in extracted_info and extracted_info[field]:
                            collector.add_info(field, extracted_info[field])
                            print(f"[DEBUG] Extracted {field} = {extracted_info[field]}")
                            filled_count += 1

                    # 如果没有提取到任何信息，把整个消息作为当前字段的值
                    if filled_count == 0 and collector.current_field_index < len(collector.required_fields):
                        current_field = collector.required_fields[collector.current_field_index]
                        collector.add_info(current_field, request.message)
                        print(f"[DEBUG] Using raw input for {current_field} = {request.message}")

                # 3. 检查用户是否需要额外信息（如回复 "是"、"需要" 或序号如 "1,3"）
                user_selection = _parse_optional_api_selection(request.message)
                if user_selection is not None:
                    # 用户选择了特定的 API（如 "1,3"）
                    print(f"[DEBUG] User selected optional APIs: {user_selection}")
                    collector.set_selected_optional_apis(user_selection)
                elif _wants_extra_info(request.message):
                    # 用户同意了，但没有指定具体哪些，调用全部可选 API
                    print(f"[DEBUG] User wants extra info, will call ALL optional APIs")
                    from app.skills.plan_generator import get_optional_apis_for_plan
                    optional_apis = get_optional_apis_for_plan(collector.plan_type, [])
                    # 调用所有可选 API
                    all_selection = list(range(1, len(optional_apis) + 1))
                    collector.set_selected_optional_apis(all_selection)

                # 4. 如果开启了 RAG，且之前没有查询到知识库内容，现在查询
                #    用已收集的 topic/goal 做检索，如果还没有则用当前消息做粗检索
                if request.use_rag and not collector.get_rag_context():
                    existing_info = collector.get_collected_info()
                    r_topic = existing_info.get("topic", "") or request.message[:30]
                    r_goal = existing_info.get("goal", "") or ""
                    print(f"[DEBUG] RAG enabled but no context yet, querying with topic='{r_topic}'")
                    rag_context = await _query_rag_for_plan(
                        topic=r_topic,
                        goal=r_goal,
                        plan_type=collector.plan_type,
                        session_id=session_id,
                        user_id=user_id_str,
                        doc_ids=request.doc_ids,
                    )
                    if rag_context:
                        collector.set_rag_context(rag_context, collector.get_context_summary())
                        print(f"[DEBUG] RAG context added in second request: {len(rag_context)} chars")

        # 4. 保存收集器状态
        collector_manager.save_collector(session_id, collector)

        # 5. 保存用户消息到对话历史（使用 module="chat" 以便在 Chatbot 会话历史中显示）
        add_chat_message(session_id, "user", request.message, user_id=user_id_str, module="chat")

        # 6. 无论信息是否收集完毕，都展示当前信息让用户确认或继续填写
        summary = collector.get_collected_summary()

        if collector.is_complete():
            # 信息收集完毕，显示 API 预览和确认提示
            selected_optional_apis = collector.get_selected_optional_apis()
            api_preview = preview_apis_to_call(
                collector.plan_type,
                collector.get_collected_info(),
                selected_optional_apis
            )

            response = f"已收集到以下信息：\n\n{summary}\n\n{api_preview}\n\n请确认是否正确？如果需要修改，请告诉我（如：\"第3个改成XX\" 或 \"身高改成180\"）。确认无误后请回复\"确认\"生成计划。"
        else:
            # 信息未收集完毕，提示用户继续填写缺失字段
            missing_questions = collector.get_missing_questions()
            response = f"已收集到部分信息：\n\n{summary}\n\n还需要以下信息：\n\n{missing_questions}\n\n请继续补充，或修改已填写的信息。"

        add_chat_message(session_id, "assistant", response, user_id=user_id_str, module="chat")

        return {"response": response, "session_id": session_id}

    except Exception as e:
        import traceback
        print(f"[ERROR] chat_plan failed: {e}")
        print(traceback.format_exc())
        return {"response": "抱歉，生成计划时出错了，请稍后再试。", "session_id": request.session_id or "error"}


def _parse_optional_api_selection(message: str) -> Optional[List[int]]:
    """解析用户选择的可选API

    支持格式：
    - "1,3" → [1, 3]
    - "1 3" → [1, 3]
    - "1, 2, 3" → [1, 2, 3]
    - "额外调用2" → [2]
    - "调用1和3" → [1, 3]
    - "只要第2个" → [2]

    Returns:
        用户选择的API序号列表，如果没有选择则返回 None
    """
    import re

    # 提取所有数字
    numbers = re.findall(r'\d+', message)
    if not numbers:
        return None

    # 转换为整数并去重
    try:
        selected = list(set(int(n) for n in numbers))
        selected.sort()

        # 如果只有一个数字，且消息中包含"额外"、"调用"、"只要"等关键词，说明是明确选择
        if len(selected) == 1:
            # 检查是否是明确的选择（而不是误匹配）
            selection_keywords = ["额外", "调用", "只要", "选择", "第", "个", "是", "要"]
            if any(kw in message for kw in selection_keywords):
                return selected
            else:
                # 如果只是单独的数字，没有明确的关键词，可能是误匹配
                return None

        # 多个数字，说明是明确选择
        return selected
    except:
        return None


def _wants_extra_info(message: str) -> bool:
    """检查用户是否需要额外信息

    支持格式：
    - "是" → True
    - "需要" → True
    - "好的" → True
    - "要" → True
    - "不用" → False
    - "不需要" → False
    - "跳过" → False

    Returns:
        用户是否需要额外信息
    """
    # 先检查是否明确拒绝
    reject_keywords = ["不用", "不需要", "跳过", "不要", "no", "skip"]
    for keyword in reject_keywords:
        if keyword in message.lower():
            return False

    # 再检查是否同意
    agree_keywords = ["是", "需要", "好的", "要", "行", "可以", "yes", "ok", "sure"]
    for keyword in agree_keywords:
        if keyword in message.lower():
            return True

    # 默认返回 False
    return False


async def _query_rag_for_plan(
    topic: str,
    goal: str,
    plan_type: str,
    session_id: str,
    user_id: str,
    doc_ids: list,
) -> Optional[str]:
    """
    专门为计划生成查询知识库：用 topic+goal 做检索，返回原始文档片段（带[来源]标注）。

    与普通 query_rag_internal 的区别：
    - 普通 RAG: 让 LLM 根据片段回答问题（适合问答）
    - 计划生成 RAG: 直接返回检索到的片段原文，让下游 LLM 根据这些内容制定计划
      （避免"制定计划"这种发散问题让 LLM 说"未找到相关信息"）

    Returns:
        原始片段拼接字符串（每个片段自带 [来源: 文档名#编号] 标记），或 None
    """
    try:
        from app.api.rag import hybrid_search

        # 1) 构造检索 query —— 用 topic + goal，避免用"确认"这种无效词
        if topic and goal:
            retrieval_query = f"{topic} {goal}"
        elif topic:
            retrieval_query = topic
        else:
            retrieval_query = f"{plan_type}计划 学习内容"

        print(f"[INFO] _query_rag_for_plan - 检索 query: '{retrieval_query}'")

        # 2) 直接做混合检索（向量 + BM25）
        retrieved_docs, retrieval_info = hybrid_search(
            retrieval_query,
            top_k=5,          # 计划生成要更多上下文
            fetch_k=30,       # 多拿一些，后续合并筛选
            doc_ids=doc_ids,
        )

        print(f"[INFO] 知识库命中: {len(retrieved_docs)} 条片段 (向量={retrieval_info.get('vector_count', 0)}, BM25={retrieval_info.get('bm25_count', 0)})")

        if not retrieved_docs:
            print("[INFO] 知识库中无相关片段")
            return None

        # 3) 直接拼接原始片段，每个片段自带来源标记
        context_parts = []
        for idx, doc in enumerate(retrieved_docs, 1):
            meta = doc.metadata or {}
            doc_name = meta.get("doc_name", f"文档{idx}")
            chunk_idx = meta.get("chunk_index", idx)
            ref_id = f"{doc_name}#{chunk_idx}"
            content = doc.page_content.strip()
            if content:
                context_parts.append(f"片段 {idx} [来源: {ref_id}]: {content}")

        rag_context = "\n\n".join(context_parts)
        print(f"[INFO] 计划生成 - 知识库上下文: {len(rag_context)} 字符")
        return rag_context

    except Exception as e:
        print(f"[ERROR] _query_rag_for_plan 失败: {e}")
        import traceback
        print(traceback.format_exc())
        return None
