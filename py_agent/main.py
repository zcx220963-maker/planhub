"""
PlanHub AI 服务 - 应用入口

安全架构：
1. Python AI 服务作为内部服务，只监听 127.0.0.1，不直接暴露给外部
2. 只接受来自 Java 后端的内部请求（通过 X-Internal-Api-Secret 鉴权）
3. 前端请求必须经过 Java 后端（JWT 鉴权），由 Java 转发到 Python

性能优化：
1. 记忆系统（短期/工作/长期记忆）
2. 上下文工程（智能历史过滤、上下文压缩）
3. 工具调用优化（缓存、重试）
4. 性能监控（请求耗时、Token 消耗）
5. 错误恢复和降级
"""

import sys
import os
import io
import logging

# ── 崩溃日志：记录所有未捕获异常到文件 ────────────────────────
# 这样服务器崩溃时可以查看 crash.log 找到真正原因
logging.basicConfig(
    filename="crash.log",
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
crash_logger = logging.getLogger("crash")


def _global_excepthook(exc_type, exc_value, exc_tb):
    """记录未捕获的异常（包括 CancelledError 在 Python 3.9+ 是 BaseException）"""
    import traceback
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    crash_logger.error(f"未捕获的全局异常:\n{msg}")
    # 同时打印到 stderr
    print(f"[CRASH] {msg}", file=sys.stderr, flush=True)


sys.excepthook = _global_excepthook


# ── Windows 控制台编码修复 ──────────────────────────────────
# Windows 默认控制台编码为 GBK，遇到 AI 回复中的 emoji (👋🌟) 时
# print() 会抛出 OSError: [Errno 22] Invalid argument，导致 500。
# 强制将 stdout/stderr 设为 UTF-8 编码可彻底解决。
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ── Windows 控制台关闭信号防护 ──────────────────────────────
# 用户误点终端窗口"×"或 VS Code 终端垃圾桶时，Windows 会向子进程发送
# CTRL_CLOSE_EVENT，Python 默认行为是退出（退出码 0）。
# 安装一个自定义处理器忽略该信号，让服务器在终端关闭后仍继续运行。
# 用户仍需按 Ctrl+C 或用 taskkill 来真正停服。
if sys.platform == "win32":
    import ctypes
    _CTRL_CLOSE_EVENT = 2
    _CTRL_LOGOFF_EVENT = 5
    _CTRL_SHUTDOWN_EVENT = 6

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)
    def _ignore_console_close(ctrl_type):
        if ctrl_type in (_CTRL_CLOSE_EVENT, _CTRL_LOGOFF_EVENT, _CTRL_SHUTDOWN_EVENT):
            # 返回 True 表示"已处理"，系统不会再终止进程
            print(f"[INFO] 收到控制台关闭信号({ctrl_type})，服务器继续运行", flush=True)
            return True
        # CTRL_C_EVENT / CTRL_BREAK_EVENT = 返回 False → 走默认行为（允许 Ctrl+C 退出）
        return False

    _kernel32 = ctypes.windll.kernel32
    if not _kernel32.SetConsoleCtrlHandler(_ignore_console_close, True):
        print("[WARN] 无法安装控制台关闭信号处理器", flush=True)

# 将项目根目录和 src 目录添加到 Python 路径
# 这样 config.py 在根目录，app 在 src/ 目录
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from config import settings
from src.app.dao.redis_dao import init_redis, get_redis_client

# 导入路由
from src.app.api.rag import router as rag_router
from src.app.api.conversations import router as conversation_router
from src.app.api.orchestrator import router as orchestrator_router  # LangGraph 统一入口
from src.app.api.plans import router as plans_router  # 计划库管理

# 性能监控中间件和服务（已删除 middleware/ 和 metrics_service.py，注释掉）
# from src.app.middleware.metrics_middleware import MetricsMiddleware
# from src.app.service.metrics_service import MetricsService

# ─── Lifespan 事件处理器（FastAPI 0.100+ 推荐方式）────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化所有服务"""
    # 1. Redis
    if settings.use_redis_bool:
        init_redis()
        print("[INFO] Redis 初始化完成")

    # 2. RAG 索引
    try:
        from src.app.api.rag import init_document_indices, init_vector_store
        init_vector_store()
        init_document_indices()
        print("[INFO] RAG 索引初始化完成")
    except Exception as e:
        print(f"[WARN] RAG 初始化失败: {e}")

    # 3. 降级服务
    try:
        from src.app.service.fallback_service import FallbackService
        from src.app.dao.redis_dao import get_redis_client
        redis_client = get_redis_client()
        fallback_service = FallbackService(redis_client)
        fallback_service.load_state()
        print("[INFO] 降级服务初始化完成")
    except Exception as e:
        print(f"[WARN] 降级服务初始化失败: {e}")

    # 4. MySQL 数据库 + 通知系统
    try:
        from src.app.service.plan_store import init_db
        await init_db()
        from src.app.service.notifier import init_notifications
        init_notifications()
        print("[INFO] MySQL 数据库和通知系统初始化完成")
    except Exception as e:
        print(f"[WARN] 数据库/通知初始化失败: {e}")

    # 5. MCP 工具适配器
    try:
        from src.app.mcp.mcp_client import get_mcp_adapter
        mcp_adapter = await get_mcp_adapter()
        if mcp_adapter.is_connected:
            print(f"[INFO] MCP 工具适配器初始化完成，已加载 {len(mcp_adapter.tool_names)} 个工具")
        else:
            print("[WARN] MCP 工具适配器连接失败（非关键，agent 仍可使用内置工具）")
    except Exception as e:
        print(f"[WARN] MCP 初始化失败（非关键）: {e}")

    # 6. 清理过期的计划预览文件
    try:
        from src.app.service.plan_html_generator import cleanup_old_previews
        cleanup_old_previews(max_age_hours=24)
        print("[INFO] 计划预览文件清理完成")
    except Exception as e:
        print(f"[WARN] 预览文件清理失败: {e}")

    print("[INFO] PlanHub AI 服务启动完成")

    # 启动后台任务：定期清理过期预览文件
    cleanup_task = None
    try:
        from src.app.service.plan_html_generator import cleanup_old_previews
        import asyncio

        async def _periodic_cleanup():
            while True:
                await asyncio.sleep(3600)  # 每小时检查一次
                try:
                    cleanup_old_previews(max_age_hours=24)
                except Exception:
                    pass

        cleanup_task = asyncio.create_task(_periodic_cleanup())
        print("[INFO] 预览文件定时清理任务已启动")
    except Exception as e:
        print(f"[WARN] 定时清理任务启动失败: {e}")

    yield  # 应用运行中...

    # 取消定时清理任务
    if cleanup_task:
        cleanup_task.cancel()

    # 关闭时的清理（可选）
    print("[INFO] PlanHub AI 服务关闭")


# 创建 FastAPI 应用（类似 Spring Boot 的 @SpringBootApplication）
app = FastAPI(
    title="PlanHub AI 服务（内部）",
    description="PlanHub 的 AI 内部服务，仅接受 Java 后端的转发请求",
    version="1.1.0",
    lifespan=lifespan,
)

# 添加 CORS 中间件
# 独立模式（无 Java 后端）：允前端 Vite 开发服务器 (5173) 和本机 Web 直接访问
# 安全说明：服务只监听 127.0.0.1，外部无法直连，CORS 放开不影响安全
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
if settings.ALLOWED_ORIGINS_EXTRA:
    ALLOWED_ORIGINS.extend(settings.ALLOWED_ORIGINS_EXTRA)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化性能监控服务（已删除 metrics_service.py，注释掉）
metrics_service = None
# if settings.use_redis_bool:
#     try:
#         redis_client = get_redis_client()
#         metrics_service = MetricsService(redis_client)
#         print("[INFO] 性能监控服务初始化完成")
#     except Exception as e:
#         print(f"[WARN] 性能监控服务初始化失败: {e}")

# 添加性能监控中间件（已删除 middleware/，注释掉）
# if metrics_service:
#     app.add_middleware(MetricsMiddleware, metrics_service=metrics_service)
#     print("[INFO] 性能监控中间件已注册")


# ─── 内部鉴权中间件 ─────────────────────────────────────────────
# 默认启用：要求请求携带 X-Internal-Api-Secret Header（供 Java 后端调用）
# 独立模式（STANDALONE_MODE=true）：关闭鉴权，前端可直接访问（服务仅监听 127.0.0.1，安全可控）
if not settings.standalone_mode_bool:
    @app.middleware("http")
    async def internal_auth_middleware(request: Request, call_next):
        """内部 API 鉴权中间件

        所有请求必须携带正确的 X-Internal-Api-Secret Header
        只有 Java 后端知道这个密钥，因此可以确保请求来自可信来源
        """
        # 放行健康检查和根路径（便于调试，但仍建议在生产中限制
        path = request.url.path
        if path in ["/", "/health"]:
            return await call_next(request)

        # 验证内部密钥
        provided_secret = request.headers.get(settings.AI_INTERNAL_SECRET_HEADER)

        if not provided_secret:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing internal API secret header"}
            )

        if provided_secret != settings.AI_INTERNAL_SECRET:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid internal API secret"}
            )

        return await call_next(request)
else:
    print("[INFO] 独立模式：内部鉴权中间件已关闭，前端可直接访问")


# 注册路由（类似 @RequestMapping）
app.include_router(rag_router)
app.include_router(conversation_router)
app.include_router(orchestrator_router)  # LangGraph 统一入口
app.include_router(plans_router)  # 计划库管理


# 应用启动时的初始化（类似 @PostConstruct 或 ApplicationRunner）
# 注意：旧的 @app.on_event("startup") 已迁移到上方 lifespan 函数


@app.get("/")
async def root():
    mode = "独立模式（前端直连）" if settings.standalone_mode_bool else "内部模式（仅 Java 后端）"
    return {
        "message": "PlanHub AI 服务已启动",
        "version": "1.1.0",
        "mode": mode,
        "endpoints": {
            "rag": "/rag",
            "conversations": "/conversations",
            "orchestrator": "/orchestrator (LangGraph统一入口)"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "planhub-ai-internal"}


@app.get("/mcp/tools")
async def list_mcp_tools():
    """列出所有可用的 MCP 工具（供调试/前端展示）"""
    try:
        from src.app.mcp.mcp_client import get_mcp_adapter
        adapter = await get_mcp_adapter()
        if not adapter.is_connected:
            return {"connected": False, "tools": [], "error": "MCP 未连接"}

        tools = adapter.get_tools_schema()
        return {
            "connected": True,
            "count": len(tools),
            "tools": [
                {
                    "name": t["function"]["name"],
                    "description": t["function"]["description"],
                    "parameters": t["function"]["parameters"],
                }
                for t in tools
            ]
        }
    except Exception as e:
        return {"connected": False, "tools": [], "error": str(e)}


@app.post("/mcp/call/{tool_name}")
async def call_mcp_tool_endpoint(tool_name: str, params: dict):
    """直接调用一个 MCP 工具（调试用）"""
    try:
        from src.app.mcp.mcp_client import call_mcp_tool
        result = await call_mcp_tool(tool_name, params)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 性能指标接口 ─────────────────────────────────────────────
@app.get("/metrics")
async def get_metrics(hours: int = 24):
    """获取性能指标统计

    Args:
        hours: 统计最近 N 小时，默认 24 小时

    Returns:
        性能指标
    """
    if not metrics_service:
        return {"error": "性能监控服务未初始化"}

    stats = await metrics_service.get_statistics(hours)
    return stats


@app.get("/metrics/requests")
async def get_recent_requests(limit: int = 10):
    """获取最近的请求列表

    Args:
        limit: 返回数量，默认 10

    Returns:
        请求列表
    """
    if not metrics_service:
        return {"requests": []}

    requests = await metrics_service.get_recent_requests(limit)
    return {"requests": requests}


@app.get("/metrics/slow")
async def get_slow_requests(threshold: float = 5.0, hours: int = 24):
    """获取慢请求列表

    Args:
        threshold: 耗时阈值（秒），默认 5 秒
        hours: 时间范围（小时），默认 24 小时

    Returns:
        慢请求列表
    """
    if not metrics_service:
        return {"slow_requests": []}

    slow_requests = await metrics_service.get_slow_requests(threshold, hours)
    return {"slow_requests": slow_requests}


@app.get("/metrics/errors")
async def get_error_requests(hours: int = 24):
    """获取错误请求列表

    Args:
        hours: 时间范围（小时），默认 24 小时

    Returns:
        错误请求列表
    """
    if not metrics_service:
        return {"error_requests": []}

    error_requests = await metrics_service.get_error_requests(hours)
    return {"error_requests": error_requests}


if __name__ == "__main__":
    import uvicorn
    print(f"[INFO] PlanHub AI 服务启动于 http://{settings.HOST}:{settings.PORT}")
    print(f"[INFO] 此服务只监听 127.0.0.1，不直接暴露给外部")
    if settings.standalone_mode_bool:
        print("[INFO] 独立模式：前端可直接访问（鉴权已关闭）")
    else:
        print(f"[INFO] 内部模式：所有请求必须携带 Header: {settings.AI_INTERNAL_SECRET_HEADER}: <内部密钥>")

    # reload=True 在 Windows 上会导致崩溃：
    # 1. __pycache__ 更新触发文件变更事件
    # 2. uvicorn 误杀进程重启
    # 3. 请求处理中被中断 → 服务器挂起
    # 开发时如需热重载，命令行加 --reload：python main.py --reload
    enable_reload = "--reload" in sys.argv

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=enable_reload
    )
