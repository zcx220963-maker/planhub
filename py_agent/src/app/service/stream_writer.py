"""
流式 writer 共享模块 — WebSocket 段落缓冲发送

架构（参考 gpt-researcher）：
- WebSocket 连接建立后，通过 set_websocket() 注册到模块全局
- 节点在 LLM `astream` 过程中调用 emit_token(text)，内部按段落缓冲
- 遇到换行符才 flush → WebSocket 发送，减少前端渲染频率
- 无需轮询、无延迟

注意：使用模块全局变量而非 contextvars，
因为 LangGraph 节点可能在不同 context 执行，contextvars 会丢失。
"""

# 当前活跃的 WebSocket 连接（由 orchestrator.py 在 WebSocket 连接建立时设置）
_current_websocket = None

# 标记 LLM 流式生成是否结束
_streaming_complete: bool = False

# 段落缓冲区（积累 token 直到遇到换行才发送）
_paragraph_buffer: str = ""


def set_websocket(ws):
    """注册当前 WebSocket 连接"""
    global _current_websocket, _paragraph_buffer
    _current_websocket = ws
    _paragraph_buffer = ""


def clear_websocket():
    """清除 WebSocket 连接"""
    global _current_websocket, _paragraph_buffer
    _current_websocket = None
    _paragraph_buffer = ""


def get_websocket():
    """获取当前 WebSocket 连接"""
    return _current_websocket


def is_streaming() -> bool:
    """检查当前是否处于流式模式（WebSocket 已连接）"""
    return _current_websocket is not None


async def emit_token(text: str):
    """段落缓冲发送：积累 token，遇到换行才 flush 到 WebSocket

    优化原理（参考 gpt-researcher）：
    - 不是每个 token 都触发前端渲染
    - 积累到段落（换行）再一次性发送
    - 大幅减少 React 重渲染次数，输出更丝滑
    """
    global _current_websocket, _paragraph_buffer
    if _current_websocket is None:
        return

    _paragraph_buffer += text

    # 遇到换行符 → flush 缓冲区
    if "\n" in _paragraph_buffer:
        # 按换行分割，最后一段（可能不完整）留在缓冲区
        parts = _paragraph_buffer.split("\n")
        # 最后一段不完整，留到下次
        _paragraph_buffer = parts[-1]
        # 前面的完整段落一次性发送
        to_send = "\n".join(parts[:-1])
        if to_send:
            try:
                await _current_websocket.send_json({"type": "token", "content": to_send + "\n"})
            except Exception:
                pass


async def flush_buffer():
    """强制 flush 缓冲区（LLM 生成结束时调用）"""
    global _current_websocket, _paragraph_buffer
    if _current_websocket is not None and _paragraph_buffer:
        try:
            await _current_websocket.send_json({"type": "token", "content": _paragraph_buffer})
        except Exception:
            pass
        _paragraph_buffer = ""


async def emit_streaming_complete():
    """通知前端 LLM 流式生成结束（发送 WebSocket 消息，前端停止打字机动画）"""
    global _streaming_complete
    _streaming_complete = True
    if _current_websocket is not None:
        try:
            await _current_websocket.send_json({"type": "streaming_complete"})
        except Exception:
            pass


def is_streaming_complete() -> bool:
    """检查 LLM 流式生成是否已结束"""
    return _streaming_complete


def reset_streaming_complete():
    """重置流式结束标记"""
    global _streaming_complete
    _streaming_complete = False


async def emit_log(message: str):
    """发送执行日志到前端（实时显示代理执行进度）

    用于在右侧面板显示当前正在做什么，避免用户干等。
    例如：
    - "正在总结用户需求..."
    - "开始选择工具（共 21 个候选）"
    - "调用 get_weather(南京)..."
    - "读取知识库文档..."
    - "正在生成最终计划..."
    """
    global _current_websocket
    if _current_websocket is not None:
        try:
            await _current_websocket.send_json({"type": "log", "content": message})
        except Exception:
            pass


async def send_ws_message(data: dict):
    """发送任意 WebSocket 消息"""
    global _current_websocket
    if _current_websocket is not None:
        try:
            await _current_websocket.send_json(data)
        except Exception:
            pass
