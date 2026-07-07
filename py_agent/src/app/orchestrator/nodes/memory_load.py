"""
Memory Load 节点 - 加载短期和长期记忆

核心设计：
- 只在需要记忆的节点（plan_generator、plan_writer）前调用
- 短期记忆：从 Redis 取最近 10 轮（20 条消息）
- 长期记忆：用用户原话语义检索 Chroma 向量库 top-K
- 避免每轮都加载，减少不必要的 IO 和 Token 消耗
"""

from typing import Dict, Any, List


async def memory_load_node(state) -> dict:
    """
    记忆加载节点：加载短期记忆和长期记忆到 State

    调用时机：
    - plan_generator 节点执行前（多轮询问需要上下文）
    - plan_writer 节点执行前（生成计划需要用户偏好/历史）

    不调用的节点（节省资源）：
    - supervisor（路由不需要记忆）
    - assistant / chat（各自有自己的历史管理）
    - tool_executor / doc_retriever / parameter_extractor（纯功能节点）
    """
    try:
        session_id = state.get("session_id", "")
        user_id = state.get("user_id") or "anonymous"
        user_input = state.get("user_input", "")

        print(f"[DEBUG] memory_load: 开始加载记忆, session_id={session_id[:8]}..., user_id={user_id}")

        # 加载短期记忆（Redis，最近 10 轮 = 20 条消息）
        short_term_memory = []
        try:
            from src.app.orchestrator.memory_bridge import MemoryBridge
            bridge = MemoryBridge()
            mem_result = await bridge.load_memory(session_id, user_id)
            short_term_memory = mem_result.get("short_term_memory", [])
            print(f"[DEBUG] memory_load: 短期记忆 {len(short_term_memory)} 条")
        except Exception as e:
            print(f"[WARN] memory_load: 短期记忆加载失败: {e}")

        # 长期记忆不由 memory_load_node 加载，
        # 而是由 memory_load_for_writer 单独检索并注入 plan_writer（作为结构化参考数据）
        return {
            "short_term_memory": short_term_memory,
            "execution_trace": [
                {
                    "node": "memory_load",
                    "short_term_count": len(short_term_memory),
                    "success": True
                }
            ]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] memory_load: {e}")
        return {
            "short_term_memory": [],
            "execution_trace": [
                {
                    "node": "memory_load",
                    "error": str(e),
                    "success": False
                }
            ]
        }
