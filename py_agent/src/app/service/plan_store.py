"""
计划存储 —— MySQL 存储计划 + 打卡记录

数据模型：
- plans: 计划基本信息（含 HTML 预览路径）
- plan_checkins: 每日打卡记录（plan_id + date + status）
"""

import os
import asyncio
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from .db_pool import get_pool, _query_one, _query_all, _execute, _execute_rowcount


async def init_db():
    """初始化数据库表（不存在时创建）"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    category VARCHAR(50) DEFAULT 'PERSONAL',
                    priority VARCHAR(20) DEFAULT 'MEDIUM',
                    visibility VARCHAR(20) DEFAULT 'PUBLIC',
                    start_date VARCHAR(20),
                    target_date VARCHAR(20),
                    estimated_duration_hours INT,
                    user_id VARCHAR(100),
                    html_path TEXT,
                    plan_text TEXT,
                    session_id VARCHAR(100) DEFAULT '',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS plan_checkins (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    plan_id INT NOT NULL,
                    checkin_date VARCHAR(20) NOT NULL,
                    status VARCHAR(20) DEFAULT 'done',
                    note TEXT,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
                    UNIQUE KEY uk_plan_date (plan_id, checkin_date),
                    INDEX idx_checkin_date (checkin_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
    # 同时初始化 rag_documents 表（知识库文档）
    try:
        from .document_store import init_document_store
        await init_document_store()
    except Exception as e:
        print(f"[WARN] rag_documents 表初始化失败: {e}")

    from .db_pool import DB_HOST, DB_PORT, DB_NAME
    print(f"[PlanStore] MySQL 数据库初始化完成: {DB_HOST}:{DB_PORT}/{DB_NAME}")


async def close_pool():
    """关闭连接池（应用退出时调用）"""
    from .db_pool import close_pool as _close
    await _close()


# ===== 计划 CRUD =====

async def save_plan(
    title: str,
    description: str = "",
    category: str = "PERSONAL",
    priority: str = "MEDIUM",
    visibility: str = "PUBLIC",
    start_date: Optional[str] = None,
    target_date: Optional[str] = None,
    estimated_duration_hours: Optional[int] = None,
    user_id: Optional[str] = None,
    html_path: str = "",
    plan_text: str = "",
    session_id: str = "",
) -> Dict[str, Any]:
    """
    保存计划到 MySQL，返回创建的计划信息。

    Returns:
        {"id": int, "title": str, "description": str, ...}
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plan_id = await _execute(
        """INSERT INTO plans
           (title, description, category, priority, visibility,
            start_date, target_date, estimated_duration_hours,
            user_id, html_path, plan_text, session_id, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (title, description, category, priority, visibility,
         start_date, target_date, estimated_duration_hours,
         user_id, html_path, plan_text, session_id, now, now),
    )

    print(f"[PlanStore] 计划已保存: id={plan_id}, title={title}")
    return {
        "id": plan_id,
        "title": title,
        "description": description,
        "category": category,
        "priority": priority,
        "visibility": visibility,
        "start_date": start_date,
        "target_date": target_date,
        "estimated_duration_hours": estimated_duration_hours,
        "user_id": user_id,
        "html_path": html_path,
        "plan_text": plan_text,
        "session_id": session_id,
        "created_at": now,
    }


async def update_plan(plan_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    """更新计划字段"""
    allowed = {"title", "description", "category", "priority", "visibility",
               "start_date", "target_date", "estimated_duration_hours",
               "html_path", "plan_text"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return await get_plan(plan_id)

    fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_clause = ", ".join(f"{k}=%s" for k in fields)
    values = list(fields.values()) + [plan_id]

    await _execute_rowcount(f"UPDATE plans SET {set_clause} WHERE id=%s", tuple(values))
    return await get_plan(plan_id)


async def get_plan(plan_id: int) -> Optional[Dict[str, Any]]:
    """根据 ID 获取计划"""
    return await _query_one("SELECT * FROM plans WHERE id=%s", (plan_id,))


async def list_plans(user_id: Optional[str] = None, limit: int = 50) -> list:
    """列出计划（可选按 user_id 过滤），附带打卡统计"""
    if user_id:
        rows = await _query_all(
            "SELECT * FROM plans WHERE user_id=%s ORDER BY created_at DESC LIMIT %s",
            (user_id, limit),
        )
    else:
        rows = await _query_all(
            "SELECT * FROM plans ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )

    result = []
    for row in rows:
        plan = dict(row)
        plan["checkin_count"] = await _get_checkin_count(plan["id"])
        result.append(plan)
    return result


async def delete_plan(plan_id: int) -> bool:
    """删除计划（级联删除打卡记录）"""
    await _execute_rowcount("DELETE FROM plan_checkins WHERE plan_id=%s", (plan_id,))
    await _execute_rowcount("DELETE FROM plans WHERE id=%s", (plan_id,))
    return True


async def _get_checkin_count(plan_id: int) -> int:
    """获取计划的总打卡天数"""
    row = await _query_one(
        "SELECT COUNT(*) as cnt FROM plan_checkins WHERE plan_id=%s AND status='done'",
        (plan_id,)
    )
    return row["cnt"] if row else 0


# ===== 打卡相关 =====

async def add_checkin(plan_id: int, checkin_date: str = None, status: str = "done", note: str = "") -> Dict[str, Any]:
    """添加或更新打卡记录

    Args:
        plan_id: 计划 ID
        checkin_date: 打卡日期 (YYYY-MM-DD)，默认今天
        status: 状态 (done=完成, skip=跳过, fail=未完成)
        note: 备注

    Returns:
        打卡记录
    """
    if not checkin_date:
        checkin_date = date.today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # MySQL UPSERT: ON DUPLICATE KEY UPDATE
    await _execute(
        """INSERT INTO plan_checkins (plan_id, checkin_date, status, note, created_at)
           VALUES (%s, %s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE status=VALUES(status), note=VALUES(note)""",
        (plan_id, checkin_date, status, note, now),
    )

    print(f"[PlanStore] 打卡: plan_id={plan_id}, date={checkin_date}, status={status}")
    return {
        "plan_id": plan_id,
        "checkin_date": checkin_date,
        "status": status,
        "note": note,
    }


async def remove_checkin(plan_id: int, checkin_date: str = None) -> bool:
    """删除打卡记录"""
    if not checkin_date:
        checkin_date = date.today().isoformat()
    await _execute_rowcount(
        "DELETE FROM plan_checkins WHERE plan_id=%s AND checkin_date=%s",
        (plan_id, checkin_date),
    )
    return True


async def get_checkins(plan_id: int, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
    """获取打卡记录

    Args:
        plan_id: 计划 ID
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        打卡记录列表
    """
    if start_date and end_date:
        rows = await _query_all(
            """SELECT * FROM plan_checkins
               WHERE plan_id=%s AND checkin_date BETWEEN %s AND %s
               ORDER BY checkin_date ASC""",
            (plan_id, start_date, end_date),
        )
    else:
        rows = await _query_all(
            "SELECT * FROM plan_checkins WHERE plan_id=%s ORDER BY checkin_date ASC",
            (plan_id,),
        )
    return [dict(r) for r in rows]


async def get_checkin_calendar(plan_id: int, year: int = None, month: int = None) -> Dict[str, Any]:
    """获取日历格式的打卡数据

    Returns:
        {
            "year": 2026,
            "month": 7,
            "days": {
                "2026-07-01": {"status": "done", "note": ""},
                "2026-07-02": {"status": "skip", "note": "下雨"},
                ...
            },
            "total_days": 31,
            "checked_days": 15,
            "streak": 7
        }
    """
    if year is None:
        year = date.today().year
    if month is None:
        month = date.today().month

    # 计算当月天数
    import calendar
    _, total_days = calendar.monthrange(year, month)
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-{total_days:02d}"

    checkins = await get_checkins(plan_id, start, end)
    days = {}
    for c in checkins:
        days[c["checkin_date"]] = {
            "status": c["status"],
            "note": c.get("note", ""),
        }

    # 计算连续打卡天数（streak）
    streak = 0
    today = date.today()
    check_date = today
    while True:
        date_str = check_date.isoformat()
        if date_str in days and days[date_str]["status"] == "done":
            streak += 1
            check_date = date.fromordinal(check_date.toordinal() - 1)
        elif date_str in days and days[date_str]["status"] in ("skip", "fail"):
            check_date = date.fromordinal(check_date.toordinal() - 1)
        else:
            break

    checked_days = sum(1 for d in days.values() if d["status"] == "done")

    return {
        "year": year,
        "month": month,
        "days": days,
        "total_days": total_days,
        "checked_days": checked_days,
        "streak": streak,
    }


async def get_today_checkin(plan_id: int) -> Optional[Dict[str, Any]]:
    """获取今天的打卡状态"""
    today = date.today().isoformat()
    return await _query_one(
        "SELECT * FROM plan_checkins WHERE plan_id=%s AND checkin_date=%s",
        (plan_id, today),
    )
