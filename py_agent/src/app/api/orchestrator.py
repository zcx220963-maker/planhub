"""
LangGraph多Agent编排API
提供统一的Agent编排入口

关键特性：
- 使用 LangGraph checkpointer 持久化对话状态
- 支持多轮对话中的状态延续
- 从 Redis 加载之前的 execution_trace
- WebSocket 实时流式输出（无轮询、无缓冲、无延迟）
"""

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, validator
from typing import Any, Dict, Optional, Union
import json
import asyncio
import os

from langgraph.checkpoint.base import BaseCheckpointSaver
from ..service.graph import create_agent_graph
from ..service.schemas import CapabilityFlags
from ..service.stream_writer import (
    set_websocket, clear_websocket, is_streaming,
    is_streaming_complete, reset_streaming_complete, send_ws_message
)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


class OrchestrateRequest(BaseModel):
    """编排请求"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[Union[str, int]] = None
    model: str = "deepseek-r1:7b"
    temperature: float = 0.7
    capabilities: CapabilityFlags = CapabilityFlags()
    doc_ids: Optional[list] = None

    @validator('user_id', pre=True)
    def convert_user_id_to_str(cls, v):
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
    plan_metadata: Optional[dict] = None


# 全局图实例和checkpointer
_graph_instance = None
_checkpointer = None


class _RedisCheckpointer(BaseCheckpointSaver):
    """轻量 Redis checkpointer，支持 TTL 自动过期"""
    def __init__(self, redis_url, ttl_minutes=1440):
        super().__init__()
        import redis.asyncio as aioredis
        self.redis = aioredis.from_url(redis_url, decode_responses=False)
        self.ttl = ttl_minutes * 60
        self._data = {}

    async def aget_tuple(self, config):
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
    """
    try:
        from ..service.memory_bridge import MemoryBridge
        bridge = MemoryBridge()
        conv = bridge.get_conversation(session_id)
        if not conv or not conv.get("history"):
            return None

        history = conv["history"]
        recent = history[-40:]

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

        plan_signals = [
            "制定计划", "计划信息收集", "还有需要补充", "请说确认",
            "正在为你生成计划", "计划已生成", "是否创建到平台",
        ]
        for msg in recent:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if any(sig in content for sig in plan_signals):
                    is_plan_flow = True
                    break

        if not is_plan_flow:
            return None

        import re
        for msg in reversed(recent):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                match = re.search(r'<summary>(.*?)</summary>', content, re.DOTALL)
                if match:
                    plan_summary = match.group(1).strip()[:500]
                    break

        for msg in reversed(recent):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if "目标" in content and "---" in content and len(content) > 100:
                    plan_text_cache = content[:3000]
                    break

        execution_trace.append({
            "node": "plan_generator",
            "plan_type": "custom",
            "collecting_info": bool(plan_summary and not plan_text_cache),
            "plan_generated": bool(plan_text_cache),
            "needs_plan_building": False,
            "restored_from_history": True,
        })

        result = {
            "plan_conversation_history": plan_conversation_history[-20:],
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
    LangGraph多Agent编排入口（非流式版本，保留兼容）
    """
    try:
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

        if _checkpointer:
            try:
                existing_tuple = await _checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})
                if not existing_tuple:
                    restored = _restore_state_from_history(session_id)
                    if restored:
                        invoke_input.update(restored)
            except Exception:
                pass

        result = await graph.ainvoke(
            invoke_input,
            config={"configurable": {"thread_id": thread_id}}
        )

        response_text = (
            result.get("final_response") or
            result.get("agent_output") or
            "抱歉，处理失败"
        )

        return OrchestrateResponse(
            response=response_text,
            intent=result.get("intent"),
            confidence=result.get("confidence", 0.0),
            blocked_by_capability=result.get("blocked_by_capability", False),
            handoff_reason=result.get("handoff_reason"),
            execution_trace=result.get("execution_trace", []),
            session_id=session_id,
            plan_metadata=result.get("plan_metadata"),
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"编排失败: {str(e)}")


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket 实时流式聊天

    协议：
    - 前端发送 JSON: {"message": "...", "session_id": "...", "user_id": "...", "capabilities": {...}, "doc_ids": [...]}
    - 后端发送 JSON: {"type": "token"|"node_complete"|"done"|"error", ...}

    type=token: token 片段，实时追加
    type=node_complete: LLM 生成结束，前端可解除加载状态
    type=done: 完整流程结束，含最终响应
    type=error: 错误信息
    """
    await websocket.accept()
    set_websocket(websocket)
    reset_streaming_complete()

    try:
        # 从前端获取第一条消息（建立连接后发送）
        data = await websocket.receive_json()
        await _handle_ws_message(websocket, data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "detail": str(e)})
        except Exception:
            pass
    finally:
        clear_websocket()
        reset_streaming_complete()


async def _handle_ws_message(websocket: WebSocket, data: dict):
    """处理 WebSocket 消息并执行流式响应"""
    message = data.get("message", "")
    session_id = data.get("session_id") or generate_session_id()
    user_id = data.get("user_id")
    capabilities = data.get("capabilities", {})
    doc_ids = data.get("doc_ids", [])

    # 获取 token
    authorization = data.get("authorization", "")
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    from app.common.llm_factory import set_request_token
    set_request_token(token)

    from app.common.langchain_tools import reset_tool_call_counts
    reset_tool_call_counts()

    graph = get_graph()
    thread_id = get_thread_id(session_id)

    selected_doc_ids = doc_ids if doc_ids else capabilities.get("selected_doc_ids", [])
    selected_doc_ids = [str(did) for did in selected_doc_ids] if selected_doc_ids else []

    invoke_input = {
        "user_input": message,
        "session_id": session_id,
        "user_id": str(user_id) if user_id is not None else None,
        "capabilities": capabilities,
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
        except Exception:
            pass

    final_response_text = ""
    accumulated_trace = []
    streaming_complete_sent = False
    preview_url = None
    plan_id = None

    try:
        # 直接流式执行 LangGraph，token 通过 emit_token 实时发送
        async for chunk in graph.astream(
            invoke_input,
            config={"configurable": {"thread_id": thread_id}},
            stream_mode=["updates", "values"]
        ):
            stream_type, payload = chunk

            if stream_type == "updates":
                for node_name, node_output in payload.items():
                    if not isinstance(node_output, dict):
                        continue

                    response_text = (
                        node_output.get("final_response") or
                        node_output.get("agent_output") or
                        ""
                    )

                    if response_text:
                        final_response_text = response_text

                    # 捕获 plan_writer 生成的预览 URL 和 plan_id
                    if node_output.get("preview_url"):
                        preview_url = node_output["preview_url"]
                    if node_output.get("plan_id"):
                        plan_id = node_output["plan_id"]

                    trace = node_output.get("execution_trace")
                    if trace:
                        for t in trace:
                            if t not in accumulated_trace:
                                accumulated_trace.append(t)

        # 流式结束，发送 node_complete
        await websocket.send_json({"type": "node_complete", "node": "end"})
        streaming_complete_sent = True

        # 发送 done
        if not final_response_text:
            final_response_text = "处理完成"

        intent = execution_trace_to_intent(accumulated_trace)
        done_payload = {
            "type": "done",
            "response": final_response_text,
            "session_id": session_id,
            "execution_trace": accumulated_trace,
            "intent": intent,
        }
        if preview_url:
            done_payload["preview_url"] = preview_url
        if plan_id:
            done_payload["plan_id"] = plan_id

        await websocket.send_json(done_payload)

    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "detail": str(e)})
        except Exception:
            pass


def execution_trace_to_intent(trace: list) -> str:
    """从 execution_trace 推断 intent 名称"""
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
    """终止会话"""
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="缺少 session_id")

    thread_id = get_thread_id(session_id)

    from ..service.state import reset_conversation_state
    reset_conversation_state(session_id)

    try:
        global _checkpointer
        if _checkpointer and hasattr(_checkpointer, 'redis'):
            key = f"ckpt:{thread_id}"
            await _checkpointer.redis.delete(key)
    except Exception as e:
        print(f"[WARN] cancel: 清除 checkpoint 失败: {e}")

    return {"status": "cancelled", "session_id": session_id}


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "LangGraph Orchestrator",
        "version": "1.0.0"
    }


# 计划预览文件目录
PLAN_PREVIEWS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "plan_previews"
)


@router.get("/plan-preview/{filename}", response_class=HTMLResponse)
async def serve_plan_preview(filename: str):
    """提供计划预览 HTML 文件（iframe 加载用）

    安全说明：
    - 仅允许 .html 文件
    - 路径限制在 plan_previews 目录内
    """
    # 安全检查：只允许 .html 文件
    if not filename.endswith('.html') or '/' in filename or '\\' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")

    filepath = os.path.join(PLAN_PREVIEWS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="预览文件不存在")

    return FileResponse(filepath, media_type="text/html")


@router.get("/plan-preview-url/{session_id}")
async def get_plan_preview_url(session_id: str):
    """获取最新的计划预览 URL

    前端在 done 事件后调用此接口获取预览地址
    """
    if not os.path.exists(PLAN_PREVIEWS_DIR):
        return {"preview_url": None}

    # 查找该 session_id 最新的预览文件
    prefix = session_id[:8]
    candidates = []
    for f in os.listdir(PLAN_PREVIEWS_DIR):
        if f.startswith(prefix) and f.endswith('.html'):
            filepath = os.path.join(PLAN_PREVIEWS_DIR, f)
            candidates.append((filepath, os.path.getmtime(filepath)))

    if not candidates:
        return {"preview_url": None}

    # 取最新文件
    candidates.sort(key=lambda x: x[1], reverse=True)
    latest = os.path.basename(candidates[0][0])
    return {"preview_url": f"/orchestrator/plan-preview/{latest}"}


@router.get("/plan-previews")
async def list_plan_previews():
    """列出所有计划预览文件（调试用）"""
    if not os.path.exists(PLAN_PREVIEWS_DIR):
        return {"files": []}

    files = []
    for f in sorted(os.listdir(PLAN_PREVIEWS_DIR)):
        if f.endswith('.html'):
            filepath = os.path.join(PLAN_PREVIEWS_DIR, f)
            stat = os.stat(filepath)
            files.append({
                "filename": f,
                "url": f"/orchestrator/plan-preview/{f}",
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })

    return {"files": files, "total": len(files)}


@router.delete("/plan-previews/{filename}")
async def delete_plan_preview(filename: str):
    """删除指定的预览文件"""
    if not filename.endswith('.html') or '/' in filename or '\\' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")

    filepath = os.path.join(PLAN_PREVIEWS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文件不存在")

    os.remove(filepath)
    return {"status": "deleted", "filename": filename}
