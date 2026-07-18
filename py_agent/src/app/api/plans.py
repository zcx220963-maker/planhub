"""
计划库管理 API

提供计划列表、详情、HTML 预览、打卡记录等功能。
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List

from ..service import plan_store

router = APIRouter(prefix="/plans", tags=["计划库"])


# ===== 请求模型 =====

class CreatePlanRequest(BaseModel):
    title: str
    description: str = ""
    category: str = "PERSONAL"
    priority: str = "MEDIUM"
    visibility: str = "PUBLIC"
    start_date: Optional[str] = None
    target_date: Optional[str] = None
    estimated_duration_hours: Optional[int] = None
    user_id: Optional[str] = None
    html_path: str = ""
    plan_text: str = ""
    session_id: str = ""


class UpdatePlanRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    html_path: Optional[str] = None
    plan_text: Optional[str] = None


class CheckinRequest(BaseModel):
    plan_id: int
    checkin_date: Optional[str] = None  # YYYY-MM-DD，默认今天
    status: str = "done"  # done / skip / fail
    note: str = ""


# ===== 计划 CRUD =====

@router.post("")
async def create_plan(body: CreatePlanRequest):
    """创建计划"""
    result = await plan_store.save_plan(**body.dict())
    return {"success": True, "plan": result}


@router.get("")
async def list_plans(user_id: Optional[str] = None, limit: int = 50):
    """列出所有计划"""
    plans = await plan_store.list_plans(user_id=user_id, limit=limit)
    return {"plans": plans, "total": len(plans)}


@router.get("/{plan_id}")
async def get_plan(plan_id: int):
    """获取计划详情"""
    plan = await plan_store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    return {"plan": plan}


@router.put("/{plan_id}")
async def update_plan(plan_id: int, body: UpdatePlanRequest):
    """更新计划"""
    plan = await plan_store.update_plan(plan_id, **{k: v for k, v in body.dict().items() if v is not None})
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    return {"success": True, "plan": plan}


@router.delete("/{plan_id}")
async def delete_plan(plan_id: int):
    """删除计划"""
    await plan_store.delete_plan(plan_id)
    return {"success": True, "message": "计划已删除"}


# ===== HTML 预览 =====

@router.get("/{plan_id}/preview")
async def get_plan_preview(plan_id: int):
    """获取计划的 HTML 预览文件"""
    plan = await plan_store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    html_path = plan.get("html_path", "")
    if not html_path or not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="预览文件不存在")
    return FileResponse(html_path, media_type="text/html")


# ===== 打卡管理 =====

@router.post("/checkin")
async def add_checkin(body: CheckinRequest):
    """添加打卡记录"""
    result = await plan_store.add_checkin(
        plan_id=body.plan_id,
        checkin_date=body.checkin_date,
        status=body.status,
        note=body.note,
    )
    return {"success": True, "checkin": result}


@router.delete("/{plan_id}/checkin/{checkin_date}")
async def remove_checkin(plan_id: int, checkin_date: str):
    """删除打卡记录"""
    await plan_store.remove_checkin(plan_id, checkin_date)
    return {"success": True, "message": "打卡记录已删除"}


@router.get("/{plan_id}/checkins")
async def get_checkins(
    plan_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """获取打卡记录"""
    checkins = await plan_store.get_checkins(plan_id, start_date, end_date)
    return {"checkins": checkins}


@router.get("/{plan_id}/calendar")
async def get_calendar(plan_id: int, year: Optional[int] = None, month: Optional[int] = None):
    """获取日历格式的打卡数据

    用法: GET /plans/1/calendar?year=2026&month=7
    """
    calendar = await plan_store.get_checkin_calendar(plan_id, year, month)
    return calendar


@router.get("/{plan_id}/today")
async def get_today_checkin(plan_id: int):
    """获取今天的打卡状态"""
    checkin = await plan_store.get_today_checkin(plan_id)
    return {"checkin": checkin, "has_checkin": checkin is not None}
