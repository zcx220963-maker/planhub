"""
Create Plan To Platform节点 - 调用 create_plan 工具创建计划到平台

直接复用 langchain_tools.py 中的 create_plan 工具
"""

import re
from datetime import date, timedelta


def extract_plan_dates_and_hours(plan_text: str) -> dict:
    """
    从计划文本中提取时间信息

    返回:
        {
            "start_date": "YYYY-MM-DD",
            "target_date": "YYYY-MM-DD",
            "estimated_duration_hours": None  # 不传递，让后端根据日期自动计算
        }
    """
    result = {
        "start_date": None,
        "target_date": None,
        "estimated_duration_hours": None  # 不传递，后端会自动计算
    }

    if not plan_text:
        return result

    # 提取计划总天数
    # 匹配：1个月、2周、30天、N个月、N周、N天
    total_days = None

    # 先尝试匹配"X个月"
    month_match = re.search(r"(\d+)\s*个月", plan_text)
    if month_match:
        months = int(month_match.group(1))
        total_days = months * 30  # 每月按30天估算

    # 再尝试匹配"X周"
    if total_days is None:
        week_match = re.search(r"(\d+)\s*周", plan_text)
        if week_match:
            weeks = int(week_match.group(1))
            total_days = weeks * 7

    # 再尝试匹配"X天"
    if total_days is None:
        day_match = re.search(r"(\d+)\s*天", plan_text)
        if day_match:
            total_days = int(day_match.group(1))

    # 计算日期
    if total_days is not None:
        # 开始日期 = 今天
        start_date = date.today()
        result["start_date"] = start_date.strftime("%Y-%m-%d")

        # 目标日期 = 开始日期 + 总天数
        target_date = start_date + timedelta(days=total_days)
        result["target_date"] = target_date.strftime("%Y-%m-%d")

    return result


async def create_plan_to_platform_node(state) -> dict:
    """Create Plan To Platform节点：调用 create_plan 工具创建计划"""

    print(f"[DEBUG] create_plan_to_platform: entering node")

    plan_title = state.get("plan_title", "")
    plan_text = state.get("plan_text_cache", "")
    plan_type = state.get("plan_type", "learning")

    print(f"[DEBUG] create_plan_to_platform: plan_title={plan_title}, plan_text length={len(plan_text)}, plan_type={plan_type}")

    # 确保标题和文本存在
    if not plan_title:
        plan_title = "计划"

    # 从计划文本中提取时间信息
    date_info = extract_plan_dates_and_hours(plan_text)
    print(f"[DEBUG] create_plan_to_platform: extracted date_info = {date_info}")

    # 提取描述（从计划文本中提取）
    description = plan_text

    # 延迟导入，避免模块加载时的路径问题
    def create_plan(
        title: str,
        description: str = "",
        start_date: str = None,
        target_date: str = None
    ) -> str:
        """直接调用 langchain_tools 中的 create_plan"""
        # 在函数内部导入，避免模块加载时的路径问题
        from app.common.langchain_tools import create_plan as _create_plan

        # _create_plan 是 StructuredTool 对象，需要使用 .invoke() 调用
        invoke_args = {"title": title, "description": description}
        if start_date:
            invoke_args["start_date"] = start_date
        if target_date:
            invoke_args["target_date"] = target_date

        if hasattr(_create_plan, 'invoke'):
            return _create_plan.invoke(invoke_args)
        else:
            # 备用：如果是普通函数，直接调用
            return _create_plan(**invoke_args)

    # 调用已实现的 create_plan 工具
    try:
        result = create_plan(
            title=plan_title,
            description=description,
            start_date=date_info["start_date"],
            target_date=date_info["target_date"]
        )

        # 检查是否成功
        if "成功" in result or "创建成功" in result:
            return {
                "final_response": f"✅ {result}",
                "agent_output": f"✅ {result}",
                "tools_called": ["create_plan"],
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "create_plan_to_platform",
                        "plan_title": plan_title,
                        "plan_type": plan_type,
                        "description_length": len(description),
                        "start_date": date_info["start_date"],
                        "target_date": date_info["target_date"],
                        "success": True
                    }
                ]
            }
        else:
            # 创建失败
            return {
                "final_response": f"计划创建失败：{result}\n\n您可以手动复制以下计划内容：\n\n{plan_text[:500]}...",
                "agent_output": f"计划创建失败：{result}",
                "execution_trace": [
                    *state.get("execution_trace", []),
                    {
                        "node": "create_plan_to_platform",
                        "plan_title": plan_title,
                        "success": False,
                        "error": result
                    }
                ]
            }

    except Exception as e:
        return {
            "final_response": f"计划创建失败：{str(e)}\n\n您可以手动复制以下计划内容到平台：\n\n{plan_text[:500]}...",
            "agent_output": f"计划创建失败：{str(e)}",
            "error": str(e),
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "create_plan_to_platform",
                    "error": str(e),
                    "success": False
                }
            ]
        }
