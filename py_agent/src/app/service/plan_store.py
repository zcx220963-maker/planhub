"""
计划本地存储 —— SQLite 存储计划 + 打卡记录

数据模型：
- plans: 计划基本信息（含 HTML 预览路径）
- plan_checkins: 每日打卡记录（plan_id + date + status）
"""

import os
import sqlite3
from datetime import datetime, date
from typing import Optional, Dict, Any, List

_DB_PATH = os.environ.get("PLAN_DB_PATH", "./data/plans.db")
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表（不存在时创建）"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'PERSONAL',
            priority TEXT DEFAULT 'MEDIUM',
            visibility TEXT DEFAULT 'PUBLIC',
            start_date TEXT,
            target_date TEXT,
            estimated_duration_hours INTEGER,
            user_id TEXT,
            html_path TEXT DEFAULT '',
            plan_text TEXT DEFAULT '',
            session_id TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plan_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            checkin_date TEXT NOT NULL,
            status TEXT DEFAULT 'done',
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
            UNIQUE(plan_id, checkin_date)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_checkins_plan_date
        ON plan_checkins(plan_id, checkin_date)
    """)
    conn.commit()
    conn.close()
    print(f"[PlanStore] 数据库初始化完成: {_DB_PATH}")


def save_plan(
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
    保存计划到本地 SQLite，返回创建的计划信息。

    Returns:
        {"id": int, "title": str, "description": str, ...}
    """
    now = datetime.now().isoformat()
    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO plans
           (title, description, category, priority, visibility,
            start_date, target_date, estimated_duration_hours,
            user_id, html_path, plan_text, session_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, description, category, priority, visibility,
         start_date, target_date, estimated_duration_hours,
         user_id, html_path, plan_text, session_id, now, now),
    )
    conn.commit()
    plan_id = cursor.lastrowid
    conn.close()

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


def update_plan(plan_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    """更新计划字段"""
    allowed = {"title", "description", "category", "priority", "visibility",
               "start_date", "target_date", "estimated_duration_hours",
               "html_path", "plan_text"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return get_plan(plan_id)

    fields["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [plan_id]

    conn = _get_conn()
    conn.execute(f"UPDATE plans SET {set_clause} WHERE id=?", values)
    conn.commit()
    conn.close()
    return get_plan(plan_id)


def get_plan(plan_id: int) -> Optional[Dict[str, Any]]:
    """根据 ID 获取计划"""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_plans(user_id: Optional[str] = None, limit: int = 50) -> list:
    """列出计划（可选按 user_id 过滤），附带打卡统计"""
    conn = _get_conn()
    if user_id:
        rows = conn.execute(
            "SELECT * FROM plans WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM plans ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()

    result = []
    for row in rows:
        plan = dict(row)
        plan["checkin_count"] = _get_checkin_count(plan["id"])
        result.append(plan)
    return result


def delete_plan(plan_id: int) -> bool:
    """删除计划（级联删除打卡记录）"""
    conn = _get_conn()
    conn.execute("DELETE FROM plan_checkins WHERE plan_id=?", (plan_id,))
    conn.execute("DELETE FROM plans WHERE id=?", (plan_id,))
    conn.commit()
    conn.close()
    return True


def _get_checkin_count(plan_id: int) -> int:
    """获取计划的总打卡天数"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM plan_checkins WHERE plan_id=? AND status='done'",
        (plan_id,)
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ===== 打卡相关 =====

def add_checkin(plan_id: int, checkin_date: str = None, status: str = "done", note: str = "") -> Dict[str, Any]:
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
    now = datetime.now().isoformat()

    conn = _get_conn()
    # UPSERT: 存在则更新，不存在则插入
    conn.execute("""
        INSERT INTO plan_checkins (plan_id, checkin_date, status, note, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(plan_id, checkin_date)
        DO UPDATE SET status=excluded.status, note=excluded.note
    """, (plan_id, checkin_date, status, note, now))
    conn.commit()
    conn.close()

    print(f"[PlanStore] 打卡: plan_id={plan_id}, date={checkin_date}, status={status}")
    return {
        "plan_id": plan_id,
        "checkin_date": checkin_date,
        "status": status,
        "note": note,
    }


def remove_checkin(plan_id: int, checkin_date: str = None) -> bool:
    """删除打卡记录"""
    if not checkin_date:
        checkin_date = date.today().isoformat()
    conn = _get_conn()
    conn.execute(
        "DELETE FROM plan_checkins WHERE plan_id=? AND checkin_date=?",
        (plan_id, checkin_date)
    )
    conn.commit()
    conn.close()
    return True


def get_checkins(plan_id: int, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
    """获取打卡记录

    Args:
        plan_id: 计划 ID
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        打卡记录列表
    """
    conn = _get_conn()
    if start_date and end_date:
        rows = conn.execute(
            """SELECT * FROM plan_checkins
               WHERE plan_id=? AND checkin_date BETWEEN ? AND ?
               ORDER BY checkin_date ASC""",
            (plan_id, start_date, end_date)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM plan_checkins WHERE plan_id=? ORDER BY checkin_date ASC",
            (plan_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_checkin_calendar(plan_id: int, year: int = None, month: int = None) -> Dict[str, Any]:
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

    checkins = get_checkins(plan_id, start, end)
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
            # skip/fail 不算 streak 但也不中断（可选：中断）
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


def get_today_checkin(plan_id: int) -> Optional[Dict[str, Any]]:
    """获取今天的打卡状态"""
    today = date.today().isoformat()
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM plan_checkins WHERE plan_id=? AND checkin_date=?",
        (plan_id, today)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
