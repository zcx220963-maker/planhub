"""
LangGraph多Agent编排API
提供统一的Agent编排入口

关键特性：
- 使用 LangGraph checkpointer 持久化对话状态
- 支持多轮对话中的状态延续
- 从 Redis 加载之前的 execution_trace
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, validator
from typing import Any, Dict, Optional, Union
import json

from langgraph.checkpoint.base import BaseCheckpointSaver
from ..orchestrator.graph import create_agent_graph
from ..orchestrator.schemas import CapabilityFlags

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


class OrchestrateRequest(BaseModel):
    """编排请求"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[Union[str, int]] = None  # 接受字符串或整数
    model: str = "deepseek-r1:7b"
    temperature: float = 0.7
    capabilities: CapabilityFlags = CapabilityFlags()
    doc_ids: Optional[list] = None  # 用户选中的文档ID列表（兼容前端传递方式）

    @validator('user_id', pre=True)
    def convert_user_id_to_str(cls, v):
        """将user_id转换为字符串"""
        if v is not None:
            return str(v)
        return v


class OrchestrateResponse(BaseModel):
    """编排响应"""
    response: str
    intent: Optional[str] = None
    confidence: float = 0.0
    blocked_by_capability: bool = False
    handoff_reason: Optional[str] = None
    execution_trace: list = []
    session_id: Optional[str] = None
    plan_metadata: Optional[dict] = None  # 计划数据元信息，供前端展示数据来源


# 全局图实例和checkpointer
_graph_instance = None
_checkpointer = None


class _RedisCheckpointer(BaseCheckpointSaver):
    """轻量 Redis checkpointer，支持 TTL 自动过期

    仅存储最新 checkpoint，不维护版本历史。
    """
    def __init__(self, redis_url, ttl_minutes=1440):
        super().__init__()
        import redis.asyncio as aioredis
        self.redis = aioredis.from_url(redis_url, decode_responses=False)
        self.ttl = ttl_minutes * 60
        self._data = {}

    async def aget_tuple(self, config):
        """获取上一个 checkpoint"""
        from langgraph.checkpoint.base import CheckpointTuple
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None
        raw = await self.redis.get(f"ckpt:{thread_id}")
        if raw:
            import pickle
            data = pickle.loads(raw)
            serde = JsonPlusSerializer()
            checkpoint = serde.loads_typed(data["checkpoint"])
            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=data.get("metadata"),
                parent_config=None,
                pending_writes=[]
            )
        return None

    async def aput(self, config, checkpoint, metadata, new_versions):
        """存储当前 checkpoint"""
        from langgraph.checkpoint.base import CheckpointTuple
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return config
        import pickle
        serde = JsonPlusSerializer()
        raw = pickle.dumps({
            "checkpoint": serde.dumps_typed(checkpoint),
            "metadata": metadata,
            "new_versions": new_versions
        })
        await self.redis.setex(f"ckpt:{thread_id}", self.ttl, raw)
        return {"configurable": {"thread_id": thread_id, "checkpoint_ns": "", "checkpoint_id": checkpoint.get("id", "")}}

    async def aput_writes(self, config, writes, task_id):
        pass

    async def alist(self, config, *, before=None, limit=None):
        return []

    async def aget(self, config):
        t = await self.aget_tuple(config)
        return t.checkpoint if t else {}

    def get_next_version(self, current, channel):
        """生成下一个 channel 版本号（兼容新版 LangGraph）"""
        import random
        if current is None:
            current_v = 0
        elif isinstance(current, int):
            current_v = current
        else:
            current_v = int(str(current).split(".")[0])
        next_v = current_v + 1
        next_h = random.random()
        return f"{next_v:032}.{next_h:016}"

    async def aget_next_version(self, current, channel):
        return self.get_next_version(current, channel)


def _get_checkpointer():
    """创建 checkpointer（Redis + TTL）"""
    try:
        from config import settings
        password = settings.REDIS_PASSWORD
        if password:
            redis_url = f"redis://:{password}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        else:
            redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        return _RedisCheckpointer(redis_url, ttl_minutes=30)
    except Exception as e:
        print(f"[WARN] Redis checkpointer 初始化失败，回退到 MemorySaver: {e}")
        return None


def get_graph():
    """获取或创建图实例（带checkpointer）"""
    global _graph_instance, _checkpointer
    
    if _graph_instance is None:
        _checkpointer = _get_checkpointer()
        
        if _checkpointer is None:
            from langgraph.checkpoint.memory import MemorySaver
            _checkpointer = MemorySaver()
        
        _graph_instance = create_agent_graph().compile(checkpointer=_checkpointer)
    
    return _graph_instance


def generate_session_id() -> str:
    """生成唯一的会话ID"""
    import uuid
    return str(uuid.uuid4())


def _restore_state_from_history(session_id: str) -> Optional[Dict[str, Any]]:
    """
    当 LangGraph checkpoint 过期时，从 Redis 会话历史重建计划流程状态。

    返回需要注入 AgentState 的字段字典，或 None（无法恢复）。
    """
    try:
        from ..orchestrator.memory_bridge import MemoryBridge
        bridge = MemoryBridge()
        conv = bridge.get_conversation(session_id)
        if not conv or not conv.get("history"):
            return None

        history = conv["history"]
        # 只取最近 20 轮对话用于判断
        recent = history[-40:]

        # 从对话历史中提取计划流程相关字段
        plan_conversation_history = []
        plan_summary = ""
        plan_text_cache = ""
        execution_trace = []
        is_plan_flow = False

        for msg in recent:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("user", "assistant"):
                plan_conversation_history.append({"role": role, "content": content})

        # 判断是否在计划流程中：看 assistant 消息里是否有计划相关的引导语
        plan_signals = [
            "制定计划", "计划信息收集", "还有需要补充", "请说确认",
            "正在为你生成计划", "计划已生成", "是否创建到平台",
            "从合肥到杭州", "三日游",  # 示例：具体计划内容
        ]
        for msg in recent:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if any(sig in content for sig in plan_signals):
                    is_plan_flow = True
                    break

        if not is_plan_flow:
            return None

        # 尝试从对话历史中提取 plan_summary（assistant 消息中的 summary 标签内容）
        import re
        for msg in reversed(recent):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # 匹配 <summary>...</summary>
                match = re.search(r'<summary>(.*?)</summary>', content, re.DOTALL)
                if match:
                    plan_summary = match.group(1).strip()[:500]
                    break

        # 尝试提取已生成的计划文本（plan_writer 输出格式）
        for msg in reversed(recent):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # 计划文本特征：包含 "目标" + "---" 分隔
                if "目标" in content and "---" in content and len(content) > 100:
                    plan_text_cache = content[:3000]
                    break

        # 重建 execution_trace，让 supervisor 知道在计划流程中
        execution_trace.append({
            "node": "plan_generator",
            "plan_type": "custom",
            "collecting_info": bool(plan_summary and not plan_text_cache),
            "plan_generated": bool(plan_text_cache),
            "needs_plan_building": False,
            "restored_from_history": True,
        })

        result = {
            "plan_conversation_history": plan_conversation_history[-20:],  # 最多20条
            "plan_summary": plan_summary,
            "execution_trace": execution_trace,
        }
        if plan_text_cache:
            result["plan_text_cache"] = plan_text_cache

        return result

    except Exception as e:
        print(f"[WARN] restore_state_from_history 失败: {e}")
        return None


def get_thread_id(session_id: str) -> str:
    """生成唯一的线程ID"""
    return f"thread:{session_id}"


@router.post("/chat", response_model=OrchestrateResponse)
async def orchestrate_chat(request: Request, body: OrchestrateRequest):
    """
    LangGraph多Agent编排入口

    流程：
    1. Supervisor意图分类
    2. 根据意图路由到对应Agent
    3. 执行Agent
    4. 返回结果

    关键改进：
    - 使用 checkpointer 持久化对话状态
    - 支持多轮对话中的状态延续
    """
    try:
        # 从请求 Header 获取 Authorization token
        authorization = request.headers.get("Authorization")
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
        
        # 设置请求上下文的 token（用于 create_plan 等需要认证的工具）
        from app.common.llm_factory import set_request_token
        set_request_token(token)
        
        # 重置工具调用计数，防止跨会话累积
        from app.common.langchain_tools import reset_tool_call_counts
        reset_tool_call_counts()
        
        print(f"[DEBUG] orchestrator: Authorization header: {authorization[:30] if authorization else 'None'}...")
        print(f"[DEBUG] orchestrator: Token set: {'Yes' if token else 'No'}")
        
        # 使用提供的 session_id 或生成新的
        # 重要：新会话必须生成新的 session_id，避免共享状态
        session_id = body.session_id or generate_session_id()

        # 获取图（带checkpointer）
        graph = get_graph()
        thread_id = get_thread_id(session_id)

        # 执行图（使用thread_id持久化状态）
        # 只传入新的 user_input，LangGraph 会自动从 checkpointer 恢复之前的状态
        # 重要：从 doc_ids 或 capabilities.selected_doc_ids 中提取选中的文档ID
        capabilities_dict = body.capabilities.dict() if hasattr(body.capabilities, 'dict') else dict(body.capabilities)
        # 优先使用顶层 doc_ids，其次使用 capabilities.selected_doc_ids
        selected_doc_ids = body.doc_ids if body.doc_ids else capabilities_dict.get("selected_doc_ids", [])
        # 确保 selected_doc_ids 是字符串列表
        selected_doc_ids = [str(did) for did in selected_doc_ids] if selected_doc_ids else []

        # 构建初始输入
        invoke_input = {
            "user_input": body.message,
            "session_id": session_id,
            "user_id": str(body.user_id) if body.user_id is not None else None,
            "capabilities": capabilities_dict,
            "selected_doc_ids": selected_doc_ids,
            "rag_fallback_to_chat": False,  # 初始为 False，由 RAG 节点设置
        }

        # checkpoint 不存在时（已过期），尝试从 Redis 会话历史重建 plan flow 状态
        checkpoint = await _checkpointer.aget_next_version(None, "") if _checkpointer else None
        existing_tuple = await _checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}}) if _checkpointer else None
        if not existing_tuple:
            restored = _restore_state_from_history(session_id)
            if restored:
                invoke_input.update(restored)
                print(f"[DEBUG] orchestrator: checkpoint 已过期，从会话历史重建状态: plan_summary={restored.get('plan_summary', '')[:50]}")

        result = await graph.ainvoke(
            invoke_input,
            config={"configurable": {"thread_id": thread_id}}
        )

        # 提取响应
        response_text = (
            result.get("final_response") or
            result.get("agent_output") or
            "抱歉，处理失败"
        )

        # 检查是否被能力开关阻止
        blocked = result.get("blocked_by_capability", False)
        handoff_reason = result.get("handoff_reason")

        # 提取计划元数据（供前端展示数据来源）
        plan_metadata = result.get("plan_metadata")

        return OrchestrateResponse(
            response=response_text,
            intent=result.get("intent"),
            confidence=result.get("confidence", 0.0),
            blocked_by_capability=blocked,
            handoff_reason=handoff_reason,
            execution_trace=result.get("execution_trace", []),
            session_id=session_id,
            plan_metadata=plan_metadata,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] orchestrator: graph execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"编排失败: {str(e)}")


@router.post("/stream")
async def orchestrate_stream(request: Request, body: OrchestrateRequest):
    """
    流式输出版本

    SSE 协议实时推送：
    - response 事件：节点输出快照（content 为当前完整响应文本）
    - trace 事件：节点执行轨迹（用于前端调试面板）
    - done 事件：流程结束，包含完整响应 + session_id + execution_trace

    前端处理：
    1. 收到 response 事件 → 更新或追加 assistant 消息内容
    2. 收到 trace 事件 → 追加到 debug 面板
    3. 收到 done 事件 → 保存 session_id，标记流式结束
    """
    # 从请求 Header 获取 Authorization token
    authorization = request.headers.get("Authorization")
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    from app.common.llm_factory import set_request_token
    set_request_token(token)

    from app.common.langchain_tools import reset_tool_call_counts
    reset_tool_call_counts()

    session_id = body.session_id or generate_session_id()
    graph = get_graph()
    thread_id = get_thread_id(session_id)

    capabilities_dict = body.capabilities.dict() if hasattr(body.capabilities, 'dict') else dict(body.capabilities)
    selected_doc_ids = body.doc_ids if body.doc_ids else capabilities_dict.get("selected_doc_ids", [])
    selected_doc_ids = [str(did) for did in selected_doc_ids] if selected_doc_ids else []

    invoke_input = {
        "user_input": body.message,
        "session_id": session_id,
        "user_id": str(body.user_id) if body.user_id is not None else None,
        "capabilities": capabilities_dict,
        "selected_doc_ids": selected_doc_ids,
        "rag_fallback_to_chat": False,
    }

    # checkpoint 不存在时尝试从 Redis 会话历史重建
    if _checkpointer:
        try:
            existing_tuple = await _checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})
            if not existing_tuple:
                restored = _restore_state_from_history(session_id)
                if restored:
                    invoke_input.update(restored)
                    log_stream_restore = True
                else:
                    log_stream_restore = False
            else:
                log_stream_restore = False
        except Exception:
            log_stream_restore = False
    else:
        log_stream_restore = False

    async def event_generator():
        try:
            accumulated_trace = []
            final_response_text = ""
            seen_response_text = ""

            async for chunk in graph.astream(
                invoke_input,
                config={"configurable": {"thread_id": thread_id}},
                stream_mode=["updates", "values"]
            ):
                stream_type, payload = chunk

                if stream_type == "updates":
                    # 每个节点完成后推送一次 response 事件
                    # payload 是 {node_name: {agent_output: "...", execution_trace: [...]}} 这样的结构
                    for node_name, node_output in payload.items():
                        if not isinstance(node_output, dict):
                            continue

                        # 提取 response 文本
                        response_text = (
                            node_output.get("final_response") or
                            node_output.get("agent_output") or
                            ""
                        )

                        # 只在有新的响应内容时推送
                        if response_text and response_text != seen_response_text:
                            seen_response_text = response_text
                            final_response_text = response_text
                            yield f"event: response\ndata: {json.dumps({'content': response_text, 'node': node_name}, ensure_ascii=False)}\n\n"

                        # 提取 execution_trace（如果此节点新增了轨迹）
                        trace = node_output.get("execution_trace")
                        if trace:
                            new_traces = []
                            for t in trace:
                                if t not in accumulated_trace:
                                    accumulated_trace.append(t)
                                    new_traces.append(t)
                            if new_traces:
                                yield f"event: trace\ndata: {json.dumps({'traces': new_traces}, ensure_ascii=False)}\n\n"

                            # 第一个节点完成后推送 accumulate 标记，让前端知道流程开始
                            if log_stream_restore and new_traces:
                                yield f"event: restore\ndata: {'{}'}\n\n"

                elif stream_type == "values":
                    # state 快照，可以用于提取更多信息（暂时不用）
                    pass

            # 流程结束，推送 done 事件
            # 确保至少有一条 response
            if not final_response_text:
                # 如果上面没有从 updates 捕获到 response，从 values 的最后 state 里取
                final_response_text = "处理完成"

            yield f"event: done\ndata: {json.dumps({'response': final_response_text, 'session_id': session_id, 'execution_trace': accumulated_trace, 'intent': execution_trace_to_intent(accumulated_trace)}, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"event: error\ndata: {json.dumps({'detail': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


def execution_trace_to_intent(trace: list) -> str:
    """从 execution_trace 推断 intent 名称（供 done 事件返回给前端）"""
    for t in trace:
        if isinstance(t, dict) and t.get("node"):
            node = t["node"]
            if node == "supervisor":
                return t.get("intent", "unknown")
            if node.startswith("plan_"):
                return "plan_creation"
            if node in ("chat", "assistant", "rag"):
                return node
    return "unknown"


@router.post("/cancel")
async def cancel_session(body: dict):
    """
    终止会话：清除计划流程状态和 LangGraph checkpoint

    前端点击终止按钮时调用，重置会话到空闲状态
    """
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="缺少 session_id")

    thread_id = get_thread_id(session_id)

    # 1. 清除 ConversationState（内存中的任务状态）
    from ..service.conversation_state import reset_conversation_state
    reset_conversation_state(session_id)

    # 2. 清除 LangGraph checkpoint（Redis 中的计划流程状态）
    try:
        global _checkpointer
        if _checkpointer and hasattr(_checkpointer, 'redis'):
            import redis.asyncio as aioredis
            key = f"ckpt:{thread_id}"
            await _checkpointer.redis.delete(key)
            print(f"[DEBUG] cancel: 已清除 checkpoint key={key}")
    except Exception as e:
        print(f"[WARN] cancel: 清除 checkpoint 失败: {e}")

    print(f"[DEBUG] cancel: 会话 {session_id} 已终止，状态已清除")
    return {"status": "cancelled", "session_id": session_id}


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "LangGraph Orchestrator",
        "version": "1.0.0"
    }
