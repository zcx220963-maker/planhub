"""
流式 writer 共享模块 — token 缓冲

节点在 LLM `astream` 过程中调用 `emit_token(text)` 写入 token，
api/orchestrator.py 的 token_producer 每隔 30ms 轮询并 flush 出去，
实现逐 token 打字机效果推送到前端。

contextvars 原理：
  - event_generator 中 init_buffer() 把 buffer 设到当前 context
  - asyncio.create_task() 拷贝当前 context，子任务共享同一个 list 对象
  - 不同 SSE 请求的 event_generator 运行在不同 context 中，buffer 互不干扰
"""

import contextvars

_token_buffer: contextvars.ContextVar = contextvars.ContextVar("token_buffer", default=None)


def init_buffer():
    buf = []
    _token_buffer.set(buf)


def is_streaming() -> bool:
    return _token_buffer.get() is not None


def emit_token(text: str):
    buf = _token_buffer.get()
    if buf is not None:
        buf.append(text)


def flush_tokens() -> str:
    buf = _token_buffer.get()
    if not buf:
        return ""
    text = "".join(buf)
    buf.clear()
    return text


def clear():
    buf = _token_buffer.get()
    if buf is not None:
        buf.clear()
