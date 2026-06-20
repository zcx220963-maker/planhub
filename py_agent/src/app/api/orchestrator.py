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
from typing import Optional, Union
import json

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


# 全局图实例和checkpointer
_graph_instance = None
_checkpointer = None


def get_graph():
    """获取或创建图实例（带checkpointer）"""
    global _graph_instance, _checkpointer
    
    if _graph_instance is None:
        from langgraph.checkpoint.memory import MemorySaver
        
        # 创建 checkpointer（内存存储，用于状态持久化）
        _checkpointer = MemorySaver()
        
        # 创建图并添加 checkpointer
        _graph_instance = create_agent_graph().compile(checkpointer=_checkpointer)
    
    return _graph_instance


def generate_session_id() -> str:
    """生成唯一的会话ID"""
    import uuid
    return str(uuid.uuid4())


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
        result = await graph.ainvoke(
            {
                "user_input": body.message,
                "session_id": session_id,
                "user_id": str(body.user_id) if body.user_id is not None else None,
                "capabilities": body.capabilities.dict() if hasattr(body.capabilities, 'dict') else dict(body.capabilities),
            },
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

        return OrchestrateResponse(
            response=response_text,
            intent=result.get("intent"),
            confidence=result.get("confidence", 0.0),
            blocked_by_capability=blocked,
            handoff_reason=handoff_reason,
            execution_trace=result.get("execution_trace", []),
            session_id=session_id  # 返回实际使用的session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"编排失败: {str(e)}")


@router.post("/stream")
async def orchestrate_stream(request: OrchestrateRequest):
    """
    流式输出版本

    使用SSE协议实时推送Agent执行过程
    """
    # 生成或使用session_id
    session_id = request.session_id or generate_session_id()
    
    async def event_generator():
        try:
            # 获取图（带checkpointer）
            graph = get_graph()
            thread_id = get_thread_id(session_id)

            # 流式执行（使用thread_id持久化状态）
            # 只传入新的 user_input，LangGraph 会自动从 checkpointer 恢复之前的状态
            async for event in graph.astream_events(
                {
                    "user_input": request.message,
                    "session_id": session_id,
                    "user_id": str(request.user_id) if request.user_id is not None else None,
                    "capabilities": request.capabilities.dict() if hasattr(request.capabilities, 'dict') else dict(request.capabilities),
                },
                config={"configurable": {"thread_id": thread_id}}
            ):
                # 格式化事件
                event_data = {
                    "type": event.get("event", "unknown"),
                    "name": event.get("name", "unknown"),
                    "data": str(event.get("data", {}))[:200]
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    # 关键：设置正确的SSE响应头，防止Nginx缓冲
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "LangGraph Orchestrator",
        "version": "1.0.0"
    }
