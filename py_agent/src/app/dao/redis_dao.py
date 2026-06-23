import redis
import json
from datetime import datetime
from config import settings

# 初始化 Redis 连接（兼容旧版本 Redis）
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
    protocol=2  # 使用 RESP2 协议，兼容旧版本 Redis
)


def init_redis():
    """初始化 Redis，检查连接是否正常"""
    try:
        # 使用 PING 命令测试连接（兼容所有 Redis 版本）
        redis_client.ping()
        print("✓ Redis 连接成功")
        return True
    except redis.exceptions.ConnectionError as e:
        print(f"✗ Redis 连接失败: {e}")
        print("  请检查：")
        print("  1. Redis 服务是否已启动")
        print("  2. Redis 端口是否正确（默认 6379）")
        print("  3. Redis 是否需要密码")
        return False
    except redis.exceptions.ResponseError as e:
        # 旧版本 Redis 可能不支持某些命令
        print(f"✗ Redis 版本兼容性问题: {e}")
        return False
    except Exception as e:
        print(f"✗ Redis 未知错误: {e}")
        return False


def is_redis_available():
    try:
        redis_client.ping()
        return True
    except:
        return False


def get_redis_client():
    """获取 Redis 客户端实例

    Returns:
        redis.Redis: Redis 客户端实例
    """
    return redis_client


def save_session(session_id, session_data, expire_seconds=86400, user_id=None, module=None):
    if not is_redis_available():
        return False
    try:
        session_data["updated_at"] = datetime.now().isoformat()
        if "created_at" not in session_data:
            session_data["created_at"] = session_data["updated_at"]
        
        if user_id:
            session_data["user_id"] = user_id
        if module:
            session_data["module"] = module
        
        redis_client.setex(
            "session:" + session_id,
            expire_seconds,
            json.dumps(session_data, ensure_ascii=False)
        )
        
        session_data["session_id"] = session_id
        index_key = "conversation:" + session_id
        redis_client.setex(
            index_key,
            expire_seconds,
            json.dumps(session_data, ensure_ascii=False)
        )
        
        return True
    except Exception as e:
        print("Save session failed:", e)
        return False


def get_session(session_id):
    if not is_redis_available():
        return None
    try:
        data = redis_client.get("session:" + session_id)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print("Get session failed:", e)
        return None


def get_chat_history(session_id):
    session = get_session(session_id)
    if session and "history" in session:
        return session["history"]
    return []


def add_chat_message(session_id, role, content, max_history=20, user_id=None, module=None):
    session = get_session(session_id) or {}
    if "history" not in session:
        session["history"] = []
    
    session["history"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    
    if len(session["history"]) > max_history:
        session["history"] = session["history"][-max_history:]
    
    save_session(session_id, session, user_id=user_id, module=module)
    return session["history"]


def clear_session(session_id):
    if is_redis_available():
        try:
            redis_client.delete("session:" + session_id)
            redis_client.delete("conversation:" + session_id)
            return True
        except Exception as e:
            print("Clear session failed:", e)
            return False
    return False


def list_conversations(user_id=None, limit=20, offset=0, module=None):
    if not is_redis_available():
        return []
    try:
        # 先获取所有对话，然后在内存中过滤
        # 使用 session:* 前缀（兼容旧数据也支持 conversation:*）
        pattern = "session:*"
        
        keys = redis_client.keys(pattern)
        keys.sort(reverse=True)
        print(f"[DEBUG] list_conversations: 找到 {len(keys)} 个 keys")
        
        # 先获取所有对话
        all_conversations = []
        for key in keys:
            data = redis_client.get(key)
            if data:
                try:
                    conv = json.loads(data)
                    # 直接使用完整的 session_id 格式
                    conv["session_id"] = key.replace("session:", "")
                    
                    print(f"[DEBUG] 处理 key={key}, module={conv.get('module')}, user_id={conv.get('user_id')}")
                    
                    # 兼容旧数据：从 key 推断 module 和 user_id
                    if not conv.get("module"):
                        session_parts = conv["session_id"].split(":")
                        if len(session_parts) >= 1:
                            # 尝试从 session_id 推断 module
                            possible_module = session_parts[0]
                            if possible_module in ["chat", "assistant", "rag", "orchestrator"]:
                                conv["module"] = possible_module
                    
                    # 在内存中过滤
                    if module and conv.get("module") != module:
                        print(f"[DEBUG] 过滤: module 不匹配, conv.module={conv.get('module')}, 请求 module={module}")
                        continue
                    if user_id:
                        # 如果有 user_id 但 conv 没有，尝试推断或暂不筛选
                        if conv.get("user_id") is None:
                            # 旧数据没有 user_id，尝试从 key 推断
                            session_parts = conv["session_id"].split(":")
                            if len(session_parts) >= 2:
                                conv["user_id"] = session_parts[1]
                        # 如果还是没有 user_id，我们暂不筛选，先让旧数据能显示出来
                        print(f"[DEBUG] user_id 比较: conv.user_id={conv.get('user_id')}, 请求 user_id={user_id}")
                        if conv.get("user_id") and str(conv.get("user_id", "")) != str(user_id):
                            print(f"[DEBUG] 过滤: user_id 不匹配")
                            continue
                    
                    if conv.get("history"):
                        first_msg = conv["history"][0]
                        last_msg = conv["history"][-1]
                        conv["preview"] = last_msg.get("content", "")[:50] + "..." if len(last_msg.get("content", "")) > 50 else last_msg.get("content", "")
                        conv["first_message"] = first_msg.get("content", "")[:30] + "..." if len(first_msg.get("content", "")) > 30 else first_msg.get("content", "")
                        conv["message_count"] = len(conv["history"])
                    else:
                        conv["preview"] = "无消息"
                        conv["first_message"] = ""
                        conv["message_count"] = 0
                    
                    print(f"[DEBUG] 添加会话: {conv['session_id']}")
                    all_conversations.append(conv)
                except Exception as e:
                    print(f"Parse conversation {key} failed:", e)
                    continue
        
        # 按更新时间排序（最新的在前）
        all_conversations.sort(key=lambda x: x.get("updated_at", "") or x.get("created_at", ""), reverse=True)
        
        # 分页
        start = offset
        end = offset + limit
        conversations = all_conversations[start:end]
        
        print(f"[DEBUG] 最终返回 {len(conversations)} 个会话")
        return conversations
    except Exception as e:
        print("List conversations failed:", e)
        return []


def get_conversation_count(user_id=None, module=None):
    if not is_redis_available():
        return 0
    try:
        # 先获取所有对话，然后在内存中过滤
        # 使用 session:* 前缀（与 list_conversations 保持一致）
        pattern = "session:*"
        keys = redis_client.keys(pattern)
        
        count = 0
        for key in keys:
            data = redis_client.get(key)
            if data:
                try:
                    conv = json.loads(data)
                    # 兼容旧数据
                    if not conv.get("module"):
                        session_parts = key.replace("session:", "").split(":")
                        if len(session_parts) >= 1 and session_parts[0] in ["chat", "assistant", "rag"]:
                            conv["module"] = session_parts[0]
                    
                    if module and conv.get("module") != module:
                        continue
                    if user_id:
                        if conv.get("user_id") is None:
                            session_parts = key.replace("session:", "").split(":")
                            if len(session_parts) >= 2:
                                conv["user_id"] = session_parts[1]
                        if conv.get("user_id") and str(conv.get("user_id", "")) != str(user_id):
                            continue
                    count += 1
                except:
                    continue
        
        return count
    except Exception as e:
        print("Get conversation count failed:", e)
        return 0


def get_conversation_detail(session_id):
    return get_session(session_id)


def search_conversations(keyword, user_id=None, limit=20):
    if not is_redis_available():
        return []
    try:
        # 使用 session:* 前缀（与 list_conversations 保持一致）
        pattern = "session:*"
        if user_id:
            pattern = f"session:*"  # 简化：先获取所有，后续内存过滤
        
        keys = redis_client.keys(pattern)
        results = []
        
        for key in keys:
            data = redis_client.get(key)
            if data:
                try:
                    conv = json.loads(data)
                    conv["session_id"] = key.replace("session:", "")
                    
                    history = conv.get("history", [])
                    found = False
                    
                    # 搜索历史记录中的内容
                    for msg in history:
                        if keyword.lower() in str(msg.get("content", "")).lower():
                            found = True
                            break
                    
                    if found:
                        if history:
                            first_msg = history[0]
                            last_msg = history[-1]
                            conv["preview"] = last_msg.get("content", "")[:50] + "..." if len(last_msg.get("content", "")) > 50 else last_msg.get("content", "")
                            conv["first_message"] = first_msg.get("content", "")[:30] + "..." if len(first_msg.get("content", "")) > 30 else first_msg.get("content", "")
                        results.append(conv)
                        if len(results) >= limit:
                            break
                except:
                    continue
        
        return sorted(results, key=lambda x: x.get("updated_at", ""), reverse=True)
    except Exception as e:
        print("Search conversations failed:", e)
        return []
