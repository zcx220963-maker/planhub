from pydantic_settings import BaseSettings
from typing import ClassVar
import os


class Settings(BaseSettings):
    # ── 读取优先级 ──────────────────────────────────────
    # 1. 环境变量（最高）
    # 2. py_agent/.env 文件
    # 3. 此处定义的默认值（仅用于开发/演示，生产请覆盖）
    #
    # 注意：所有 API key 和密码默认都为空，不会泄露到 git
    # 请在 py_agent/.env 或系统环境变量中配置真实值

    # ── LLM 配置 ─────────────────────────────────────────────
    # 云端模型（阿里云百炼 / 任何 OpenAI 兼容接口）
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_MODEL: str = os.getenv("DASHSCOPE_MODEL", "qwen-max")
    DASHSCOPE_API_BASE: str = os.getenv("DASHSCOPE_API_BASE",
                                        "https://dashscope.aliyuncs.com/compatible-mode/v1")
    DASHSCOPE_EMBEDDING_MODEL: str = os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v2")
    # "true" 使用百炼模型, "false" 强制使用本地 Ollama
    # 改为 false，使用本地 qwen3:1.7b（支持 Tool Calling）
    USE_DASHSCOPE: str = os.getenv("USE_DASHSCOPE", "false")

    # 本地 Ollama（对话机器人 & RAG 默认使用此模型）
    OLLAMA_API_URL: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
    OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    # ── 服务配置 ─────────────────────────────────────────────
    HOST: str = os.getenv("AI_HOST", "127.0.0.1")  # 只监听本地，防止外部直接访问
    PORT: int = int(os.getenv("AI_PORT", "8000"))
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    PLANHUB_API_BASE: str = os.getenv("PLANHUB_API_BASE", "http://localhost:8080/api")
    TEST_MODE: bool = os.getenv("TEST_MODE", "false").lower() in ("true", "1", "yes")
    PLANHUB_USERNAME: str = os.getenv("PLANHUB_USERNAME", "admin")
    PLANHUB_PASSWORD: str = os.getenv("PLANHUB_PASSWORD", "")

    # ── Redis 配置 ───────────────────────────────────────────
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    USE_REDIS: str = os.getenv("USE_REDIS", "true")

    # ── 内部鉴权密钥 ─────────────────────────────────────────
    # Java 后端调用 Python AI 服务时使用的内部密钥
    # 必须和 Java application.yml 的 ai.service.internal-secret 一致
    AI_INTERNAL_SECRET: str = os.getenv(
        "AI_INTERNAL_SECRET",
        "planhub-internal-secret-change-in-production"
    )
    # 内部请求的 Header 名称
    AI_INTERNAL_SECRET_HEADER: str = os.getenv(
        "AI_INTERNAL_SECRET_HEADER", "X-Internal-Api-Secret"
    )

    # ── 外部 API 配置 ──────────────────────────────────────
    # OpenWeatherMap - 天气 API
    OPENWEATHERMAP_API_KEY: str = os.getenv("OPENWEATHERMAP_API_KEY", "")
    OPENWEATHERMAP_BASE_URL: str = "https://api.openweathermap.org/data/2.5"

    # NewsAPI - 新闻 API
    NEWSAPI_API_KEY: str = os.getenv("NEWSAPI_API_KEY", "")
    NEWSAPI_BASE_URL: str = "https://newsapi.org/v2"

    # ExchangeRate-API - 汇率 API（免费版无需 key）
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "latest")

    # ip-api.com - IP 查询（免费，无需 key）
    IP_API_URL: str = "http://ip-api.com/json"

    # WorldTimeAPI - 时间查询（免费，无需 key）
    WORLD_TIME_API_URL: str = "http://worldtimeapi.org/api"

    # JokeAPI - 笑话查询（免费，无需 key）
    JOKE_API_URL: str = "https://v2.jokeapi.dev/joke"

    @property
    def use_redis_bool(self):
        return str(self.USE_REDIS).lower() in ("true", "1", "yes", "t", "y")

    @property
    def use_dashscope_bool(self):
        return str(self.USE_DASHSCOPE).lower() in ("true", "1", "yes", "t", "y")

    model_config: ClassVar = {
        "env_file": ".env",
        "extra": "allow",
    }


settings = Settings()
