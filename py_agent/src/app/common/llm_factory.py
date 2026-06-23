"""
LLM 工厂类（P3-1 工程化升级）

核心特性：
1. 优先使用阿里云百炼（支持 Tool Calling），失败时自动降级到本地 Ollama
2. 每次 LLM 调用后打印 Token 成本统计（prompt_tokens / completion_tokens / total_tokens）
3. 运行轨迹记录：每一次 invoke 都会汇总到"累计成本"，便于调试
"""

import os
import time
import requests
from config import settings

# ─── 请求上下文 token 管理 ──────────────────────────────────────────
_current_request_token: str | None = None
_jwt_token: str | None = None

# ─── Token 成本与运行轨迹 ───────────────────────────────────────────
# 简化模型：按 "字符数 ≈ 1 token / 中文字符 ≈ 4 token / 英文字符" 近似估算
# 实际调用时使用 AIMessage.response_metadata 中返回的 usage
_total_tokens: int = 0
_total_prompt_tokens: int = 0
_total_completion_tokens: int = 0
_total_llm_calls: int = 0
_total_latency_ms: float = 0.0


def set_request_token(token: str | None):
    """设置当前请求的 token"""
    global _current_request_token
    _current_request_token = token


def get_request_token() -> str | None:
    """获取当前请求的 token"""
    global _current_request_token
    return _current_request_token


def reset_token_stats():
    """清零累计 Token 统计（常用于一次会话/一次评估开始时）"""
    global _total_tokens, _total_prompt_tokens, _total_completion_tokens
    global _total_llm_calls, _total_latency_ms
    _total_tokens = 0
    _total_prompt_tokens = 0
    _total_completion_tokens = 0
    _total_llm_calls = 0
    _total_latency_ms = 0.0


def get_token_stats() -> dict:
    """获取累计 Token 统计（用于评估脚本 / 日志汇总）"""
    return {
        "llm_calls": _total_llm_calls,
        "total_tokens": _total_tokens,
        "prompt_tokens": _total_prompt_tokens,
        "completion_tokens": _total_completion_tokens,
        "avg_latency_ms": round(_total_latency_ms / max(_total_llm_calls, 1), 2),
    }


def _estimate_tokens_from_text(text: str) -> int:
    """粗略估算文本长度对应的 token 数（兜底用，response_metadata 缺失时使用）"""
    if not text:
        return 0
    cn = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    en = max(0, len(text) - cn)
    return cn + max(1, en // 4)


def _record_usage(ai_message, prompt_text: str, latency_ms: float):
    """把本次 LLM 调用的 Token 用量记录到运行轨迹中"""
    global _total_tokens, _total_prompt_tokens, _total_completion_tokens
    global _total_llm_calls, _total_latency_ms

    usage = None
    # 优先从 response_metadata 读取（OpenAI 协议 / DashScope 协议都会写入）
    metadata = getattr(ai_message, "response_metadata", None) or {}
    if isinstance(metadata, dict):
        usage = metadata.get("token_usage") or metadata.get("usage")
        if not usage and isinstance(metadata.get("model_response"), dict):
            usage = metadata["model_response"].get("usage")

    if isinstance(usage, dict) and usage:
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
    else:
        # 回退：用文本长度近似估算
        content = getattr(ai_message, "content", "") or ""
        prompt_tokens = _estimate_tokens_from_text(prompt_text)
        completion_tokens = _estimate_tokens_from_text(content if isinstance(content, str) else "")
        total_tokens = prompt_tokens + completion_tokens

    _total_prompt_tokens += prompt_tokens
    _total_completion_tokens += completion_tokens
    _total_tokens += total_tokens
    _total_llm_calls += 1
    _total_latency_ms += latency_ms

    print(
        f"[LLM Token] step#{_total_llm_calls} "
        f"prompt={prompt_tokens} completion={completion_tokens} "
        f"total={total_tokens} latency={round(latency_ms, 1)}ms"
    )


def get_llm(temperature: float = 0.7, force_ollama: bool = False):
    """
    获取 LLM 实例。

    优先使用阿里云百炼 ChatOpenAI（支持 Tool Calling）。
    如果 DASHSCOPE_API_KEY 未配置或调用失败，自动降级到本地 Ollama。

    返回的模型对象已经被包装：每次 invoke 后会打印 Token 统计与耗时。
    """
    # 检查是否启用阿里云百炼（支持 Tool Calling）
    use_dashscope = settings.use_dashscope_bool and settings.DASHSCOPE_API_KEY

    if not force_ollama and use_dashscope:
        try:
            from langchain_openai import ChatOpenAI
            base_llm = ChatOpenAI(
                model=settings.DASHSCOPE_MODEL,
                api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_API_BASE,
                temperature=temperature,
            )
            print(f"[INFO] 使用阿里云百炼模型: {settings.DASHSCOPE_MODEL}")
            return _wrap_with_token_stats(base_llm, fallback_model=_build_ollama_llm(temperature))
        except Exception as e:
            print(f"[WARN] 阿里云百炼初始化失败: {e}，降级到 Ollama")
            return _wrap_with_token_stats(_build_ollama_llm(temperature), fallback_model=None)
    else:
        print(f"[INFO] 使用本地 Ollama 模型: {settings.OLLAMA_MODEL}")
        return _wrap_with_token_stats(_build_ollama_llm(temperature), fallback_model=None)


def _build_ollama_llm(temperature: float = 0.7):
    """构建一个纯 Ollama LLM 实例（不带包装）
    使用 ChatOllama 而不是 OllamaLLM，因为 ChatOllama 支持 Tool Calling
    """
    from langchain_ollama import ChatOllama
    return ChatOllama(
        base_url=settings.OLLAMA_API_URL,
        model=settings.OLLAMA_MODEL,
        temperature=temperature,
    )


def _wrap_with_token_stats(base_llm, fallback_model):
    """
    使用一个轻量包装：
    - 调用前计时，调用后累计 token 与耗时
    - 若 primary 抛出异常且 fallback_model 存在，则自动切换到 fallback
    """

    class TokenStatsWrapper:
        def __init__(self, primary, fallback):
            self._primary = primary
            self._fallback = fallback
            # 转发常用属性，保证下游 create_agent 能识别到工具调用能力
            self.__class__.__name__ = type(primary).__name__ + "WithTokenStats"

        def invoke(self, messages, *args, **kwargs):
            t0 = time.perf_counter()
            try:
                result = self._primary.invoke(messages, *args, **kwargs)
            except Exception as primary_err:
                if self._fallback is not None:
                    print(f"[LLM Fallback] primary 失败: {primary_err}；降级到 Ollama")
                    t0 = time.perf_counter()
                    try:
                        result = self._fallback.invoke(messages, *args, **kwargs)
                    except Exception as fallback_err:
                        print(f"[LLM Fallback] ollama 也失败: {fallback_err}")
                        raise
                else:
                    raise

            latency_ms = (time.perf_counter() - t0) * 1000.0
            prompt_text = ""
            if isinstance(messages, list):
                prompt_text = "\n".join(
                    [str(getattr(m, "content", "")) for m in messages if hasattr(m, "content")]
                )
            _record_usage(result, prompt_text, latency_ms)
            return result

        def stream(self, *args, **kwargs):
            # 兼容流式场景：直接交给底层，不在这里做 token 汇总
            return self._primary.stream(*args, **kwargs)

        def bind_tools(self, tools, **kwargs):
            """绑定工具（支持 Tool Calling）- 透传给 primary LLM"""
            print(f"[DEBUG] TokenStatsWrapper.bind_tools 被调用，工具数: {len(tools)}", flush=True)
            bound_llm = self._primary.bind_tools(tools, **kwargs)
            print(f"[DEBUG] bind_tools 完成，返回类型: {type(bound_llm)}", flush=True)
            # 返回新的包装器，保持 token 统计功能
            return TokenStatsWrapper(bound_llm, self._fallback)

        # 把未定义的属性访问交给 primary，避免破坏 langchain 的鸭子类型检查
        def __getattr__(self, item):
            return getattr(self._primary, item)

    return TokenStatsWrapper(base_llm, fallback_model)


def get_embeddings(force_ollama: bool = False):
    """
    获取嵌入模型实例。
    
    RAG 直接使用本地 Ollama 嵌入模型（bge-m3）。
    智能社区助手使用阿里云模型进行 Tool Calling。
    
    Args:
        force_ollama: 强制使用 Ollama（即使有阿里云配置）
    """
    # RAG 直接使用本地 Ollama 嵌入模型，跳过阿里云
    from langchain_ollama import OllamaEmbeddings
    
    # 使用配置的嵌入模型（bge-m3）
    embed_model = settings.OLLAMA_EMBEDDING_MODEL or "bge-m3"
    print(f"[INFO] 使用本地 Ollama 嵌入模型: {embed_model}")
    
    return OllamaEmbeddings(
        base_url=settings.OLLAMA_API_URL,
        model=embed_model,
    )


# ─── 阿里云百炼嵌入模型包装器 ──────────────────────────────────────

class DashScopeEmbeddings:
    """
    阿里云百炼嵌入模型包装器
    
    解决阿里云嵌入API与OpenAI格式不完全兼容的问题
    """
    
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        # 使用OpenAI客户端但做特殊处理
        from langchain_openai import OpenAIEmbeddings
        self._embeddings = OpenAIEmbeddings(
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        为多个文档生成嵌入向量
        
        阿里云API要求：
        1. 输入必须是非空字符串列表
        2. 单次输入不能超过 2048 tokens（约 6000-8000 字符）
        3. 批次大小建议不超过 10
        """
        # 过滤空字符串
        valid_texts = [t for t in texts if isinstance(t, str) and t.strip()]
        
        if not valid_texts:
            return []
        
        # 截断过长的文本（阿里云 text-embedding-v2 限制 2048 tokens）
        # 保守按 2000 字符截断，确保不超过 token 限制
        MAX_CHARS = 2000
        processed_texts = []
        for t in valid_texts:
            if len(t) > MAX_CHARS:
                # 截断时尽量在句子边界断开
                truncated = t[:MAX_CHARS]
                # 尝试找到最后一个句号、问号或感叹号
                for sep in ["。", "！", "？", "\n", ".", "!", "?"]:
                    last_idx = truncated.rfind(sep)
                    if last_idx > MAX_CHARS * 0.7:  # 至少保留 70% 内容
                        truncated = truncated[:last_idx + 1]
                        break
                processed_texts.append(truncated)
            else:
                processed_texts.append(t)
        
        print(f"[DEBUG] DashScopeEmbeddings.embed_documents: {len(processed_texts)} documents")
        
        # 分批处理，避免单次请求过大
        BATCH_SIZE = 10
        all_embeddings = []
        
        try:
            for i in range(0, len(processed_texts), BATCH_SIZE):
                batch = processed_texts[i:i + BATCH_SIZE]
                print(f"[DEBUG] 处理批次 {i//BATCH_SIZE + 1}: {len(batch)} 个文档")
                batch_embeddings = self._embeddings.embed_documents(batch)
                all_embeddings.extend(batch_embeddings)
            return all_embeddings
        except Exception as e:
            print(f"[ERROR] DashScopeEmbeddings.embed_documents failed: {e}")
            print(f"[ERROR] 输入样本(前200字符): {processed_texts[0][:200] if processed_texts else 'N/A'}")
            
            # 自动回退到本地 Ollama 嵌入
            print("[INFO] 尝试回退到本地 Ollama 嵌入...")
            return self._fallback_to_ollama(processed_texts)
    
    def _fallback_to_ollama(self, texts: list[str]) -> list[list[float]]:
        """回退到本地 Ollama 嵌入模型"""
        from langchain_ollama import OllamaEmbeddings
        import requests
        
        # 常用的本地嵌入模型列表（按优先级尝试）
        ollama_embedding_models = [
            settings.OLLAMA_EMBEDDING_MODEL,  # 配置的嵌入模型（如果有）
            "nomic-embed-text",
            "mxbai-embed-large",
            "all-minilm",
            "snowflake-arctic-embed",
        ]
        
        # 去除空值和重复
        ollama_embedding_models = list(dict.fromkeys(m for m in ollama_embedding_models if m))
        
        # 尝试不同的嵌入模型
        for model in ollama_embedding_models:
            try:
                # 先检查模型是否存在
                resp = requests.get(f"{settings.OLLAMA_API_URL}/api/tags", timeout=5)
                if resp.status_code == 200:
                    available_models = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
                    model_base = model.split(":")[0]
                    if model_base not in available_models:
                        print(f"[DEBUG] Ollama 模型 {model} 不可用，跳过")
                        continue
                
                print(f"[INFO] 尝试使用 Ollama 嵌入模型: {model}")
                fallback = OllamaEmbeddings(
                    base_url=settings.OLLAMA_API_URL,
                    model=model,
                )
                # 尝试生成嵌入
                embeddings = fallback.embed_documents(texts)
                if embeddings and len(embeddings) == len(texts):
                    print(f"[INFO] Ollama 嵌入模型 {model} 调用成功")
                    return embeddings
            except Exception as e:
                print(f"[WARN] Ollama 模型 {model} 调用失败: {e}")
                continue
        
        # 所有模型都失败，抛出原始错误
        raise RuntimeError("阿里云和本地 Ollama 嵌入模型都不可用")
    
    def embed_query(self, text: str) -> list[float]:
        """
        为单个查询生成嵌入向量
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("查询文本不能为空")
        
        print(f"[DEBUG] DashScopeEmbeddings.embed_query: {len(text)} chars")
        
        try:
            return self._embeddings.embed_query(text)
        except Exception as e:
            print(f"[ERROR] DashScopeEmbeddings.embed_query failed: {e}")
            
            # 尝试回退到本地 Ollama 嵌入模型
            print("[INFO] 尝试回退到本地 Ollama 嵌入...")
            return self._fallback_to_ollama_query(text)
    
    def _fallback_to_ollama_query(self, text: str) -> list[float]:
        """回退到本地 Ollama 嵌入模型（单个查询）"""
        from langchain_ollama import OllamaEmbeddings
        import requests
        
        # 常用的本地嵌入模型列表（按优先级尝试）
        ollama_embedding_models = [
            settings.OLLAMA_EMBEDDING_MODEL,
            "nomic-embed-text",
            "mxbai-embed-large",
            "all-minilm",
            "snowflake-arctic-embed",
            "bge-m3",
        ]
        
        ollama_embedding_models = list(dict.fromkeys(m for m in ollama_embedding_models if m))
        
        for model in ollama_embedding_models:
            try:
                # 先检查模型是否存在
                resp = requests.get(f"{settings.OLLAMA_API_URL}/api/tags", timeout=5)
                if resp.status_code == 200:
                    available_models = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
                    model_base = model.split(":")[0]
                    if model_base not in available_models:
                        print(f"[DEBUG] Ollama 模型 {model} 不可用，跳过")
                        continue
                
                print(f"[INFO] 尝试使用 Ollama 嵌入模型: {model}")
                fallback = OllamaEmbeddings(
                    base_url=settings.OLLAMA_API_URL,
                    model=model,
                )
                embedding = fallback.embed_query(text)
                if embedding:
                    print(f"[INFO] Ollama 嵌入模型 {model} 调用成功")
                    return embedding
            except Exception as e:
                print(f"[WARN] Ollama 模型 {model} 调用失败: {e}")
                continue
        
        raise RuntimeError("阿里云和本地 Ollama 嵌入模型都不可用")


# ─── PlanHub API 调用 ────────────────────────────────────────────────


def login(username: str, password: str) -> dict:
    """登录并获取 JWT token"""
    global _jwt_token
    url = settings.PLANHUB_API_BASE + "/auth/login"
    try:
        resp = requests.post(url, json={"username": username, "password": password}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("data"):
                _jwt_token = data["data"].get("accessToken")
                return {"success": True, "data": data["data"]}
        return {"success": False, "message": "Login failed"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def call_planhub_api(endpoint: str, method: str = "POST", data: dict | None = None, token: str | None = None) -> dict:
    """调用 PlanHub Java 后端 API"""
    if settings.TEST_MODE:
        return {"success": True, "message": "Mock call successful", "data": {}}

    url = settings.PLANHUB_API_BASE + endpoint
    headers = {}
    # 优先使用传入的 token，然后是请求上下文的 token，最后是全局 token
    tok = token or get_request_token() or _jwt_token
    if tok:
        headers["Authorization"] = f"Bearer {tok}"

    try:
        if method.upper() == "GET":
            resp = requests.get(url, params=data, headers=headers, timeout=10)
        elif method.upper() == "POST":
            resp = requests.post(url, json=data, headers=headers, timeout=10)
        elif method.upper() == "PUT":
            resp = requests.put(url, json=data, headers=headers, timeout=10)
        elif method.upper() == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=10)
        else:
            return {"success": False, "message": "Unsupported method"}

        if resp.status_code in (200, 201):
            return {"success": True, "data": resp.json()}
        # 尝试解析后端返回的错误信息
        try:
            error_data = resp.json()
            error_msg = error_data.get("message", f"API error: {resp.status_code}")
            return {"success": False, "message": error_msg, "data": error_data}
        except:
            return {"success": False, "message": f"API error: {resp.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}
