"""
文档存储 —— MySQL 存储知识库文档（替换原来的磁盘文件系统）

数据模型：
- rag_documents: 文档内容（按 user_id 隔离，content 存 LONGTEXT）

原来的磁盘存储 (./original_docs/{user_id}/{doc_id}.txt) 已废弃，
所有文档内容只允许存在于 MySQL / Redis / 向量库。
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from .db_pool import _query_one, _query_all, _execute, _execute_rowcount  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════════
# 初始化
# ══════════════════════════════════════════════════════════════════════════════

async def init_document_store():
    """初始化 rag_documents 表（不存在时创建）"""
    await _execute("""
        CREATE TABLE IF NOT EXISTS rag_documents (
            id INT PRIMARY KEY AUTO_INCREMENT,
            doc_id VARCHAR(64) NOT NULL,
            user_id VARCHAR(100) NOT NULL,
            filename VARCHAR(500) NOT NULL,
            content LONGTEXT NOT NULL,
            chunk_count INT DEFAULT 0,
            length INT DEFAULT 0,
            created_at DATETIME NOT NULL,
            UNIQUE KEY uk_doc_user (doc_id, user_id),
            INDEX idx_user_id (user_id),
            INDEX idx_doc_id (doc_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("[DocumentStore] rag_documents 表就绪")


# ══════════════════════════════════════════════════════════════════════════════
# CRUD
# ══════════════════════════════════════════════════════════════════════════════

def _strip_disk_format(content: str) -> str:
    """
    清洗旧磁盘格式残留：
    旧格式以 "=== filename ===" 标题行开头，第二行空行，第三行起才是正文。
    如果检测到这种格式，去掉前两行。
    """
    if content.startswith("==="):
        lines = content.split("\n")
        # 第二行应当是空行（或不存在），才视为旧格式
        if len(lines) >= 2 and lines[1].strip() == "":
            return "\n".join(lines[2:])
        elif len(lines) >= 1:
            # 只有一行标题也去掉
            return "\n".join(lines[1:])
    return content


async def save_document(
    doc_id: str,
    user_id: str,
    filename: str,
    content: str,
    chunk_count: int = 0,
) -> int:
    """
    保存文档内容到 MySQL。
    如果 (doc_id, user_id) 已存在则覆盖内容（更新 filename / content / chunk_count）。

    自动清洗旧磁盘格式残留的 "=== filename ===" 标题行。

    返回: 行 id
    """
    # 清洗内容
    content = content.strip()
    content = _strip_disk_format(content)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 先看有没有 → 有就 UPDATE，没有就 INSERT
    existing = await _query_one(
        "SELECT id FROM rag_documents WHERE doc_id=%s AND user_id=%s",
        (doc_id, user_id),
    )
    if existing:
        await _execute_rowcount(
            "UPDATE rag_documents SET filename=%s, content=%s, chunk_count=%s, length=%s, created_at=%s "
            "WHERE doc_id=%s AND user_id=%s",
            (filename, content, chunk_count, len(content), now, doc_id, user_id),
        )
        return existing["id"]
    else:
        return await _execute(
            "INSERT INTO rag_documents (doc_id, user_id, filename, content, chunk_count, length, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (doc_id, user_id, filename, content, chunk_count, len(content), now),
        )


async def get_document(doc_id: str, user_id: str) -> Optional[Dict]:
    """
    获取单个文档（含完整 content）。
    找不到返回 None。
    """
    return await _query_one(
        "SELECT id, doc_id, user_id, filename, content, chunk_count, length, created_at "
        "FROM rag_documents WHERE doc_id=%s AND user_id=%s",
        (doc_id, user_id),
    )


async def get_documents_by_user(user_id: str) -> List[Dict]:
    """
    获取某用户的全部文档列表（不含 content，仅元数据 + 预览）。
    用于文档列表接口。
    """
    rows = await _query_all(
        "SELECT id, doc_id, user_id, filename, chunk_count, length, created_at "
        "FROM rag_documents WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,),
    )
    # 附上前 500 字符预览
    for r in rows:
        full = await _query_one(
            "SELECT content FROM rag_documents WHERE doc_id=%s AND user_id=%s",
            (r["doc_id"], user_id),
        )
        content = full["content"] if full else ""
        r["content"] = content[:500] + ("..." if len(content) > 500 else "")
        r["full_content"] = content
    return rows


async def delete_document(doc_id: str, user_id: str) -> bool:
    """删除某用户的指定文档。返回是否真的删了行。"""
    affected = await _execute_rowcount(
        "DELETE FROM rag_documents WHERE doc_id=%s AND user_id=%s",
        (doc_id, user_id),
    )
    return affected > 0


async def count_documents(user_id: str) -> int:
    """统计某用户的文档数"""
    row = await _query_one(
        "SELECT COUNT(*) AS cnt FROM rag_documents WHERE user_id=%s",
        (user_id,),
    )
    return row["cnt"] if row else 0


async def get_all_documents() -> List[Dict]:
    """
    全量拉取所有用户文档（启动时一次性加载到内存索引用）。
    返回含 content 的完整记录。
    """
    return await _query_all(
        "SELECT id, doc_id, user_id, filename, content, chunk_count, length, created_at "
        "FROM rag_documents ORDER BY user_id, created_at"
    )
