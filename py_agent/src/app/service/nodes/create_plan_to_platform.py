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
            "estimated_duration_hours": None
        }
    """
    result = {
        "start_date": None,
        "target_date": None,
        "estimated_duration_hours": None
    }

    if not plan_text:
        return result

    chinese_numbers = {
        "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "半": 0.5,
        "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
        "8": 8, "9": 9, "10": 10
    }

    def parse_number(text: str) -> int:
        text = text.strip()
        if text.isdigit():
            return int(text)
        num = 0
        i = 0
        if "十" in text:
            parts = text.split("十")
            if parts[0] == "":
                num = 10
            else:
                num = chinese_numbers.get(parts[0], 0) * 10
            if len(parts) > 1 and parts[1]:
                num += chinese_numbers.get(parts[1], 0)
            return num
        for ch in text:
            if ch in chinese_numbers:
                num = num * 10 + chinese_numbers[ch]
        return num

    total_days = None

    month_match = re.search(r"([一二两三四五六七八九十0-9]+)\s*个?月", plan_text)
    if month_match:
        months = parse_number(month_match.group(1))
        if months > 0:
            total_days = months * 30

    if total_days is None:
        week_match = re.search(r"([一二两三四五六七八九十0-9]+)\s*周", plan_text)
        if week_match:
            weeks = parse_number(week_match.group(1))
            if weeks > 0:
                total_days = weeks * 7

    if total_days is None:
        day_match = re.search(r"([\d]+)\s*天", plan_text)
        if day_match:
            total_days = int(day_match.group(1))

    if total_days is not None:
        start_date = date.today()
        result["start_date"] = start_date.strftime("%Y-%m-%d")
        target_date = start_date + timedelta(days=total_days)
        result["target_date"] = target_date.strftime("%Y-%m-%d")

    return result


async def create_plan_to_platform_node(state) -> dict:
    """Create Plan To Platform节点：调用 create_plan 工具创建计划"""

    print(f"[DEBUG] create_plan_to_platform: entering node")

    plan_title = state.get("plan_title", "")
    plan_text = state.get("plan_text_cache", "")
    plan_type = state.get("plan_type", "learning")
    plan_info = state.get("plan_info", {}) or {}

    import re
    if "是否要将此计划创建" in plan_text or "计划已生成" in plan_text or "计划已修改" in plan_text or "__DATA_SOURCES__" in plan_text:
        plan_text = re.sub(r'^.*?计划已[生成修改]！\s*\n', '', plan_text, flags=re.DOTALL)
        plan_text = re.sub(r'\n\n__DATA_SOURCES__[\s\S]*?__END_DATA_SOURCES__', '', plan_text)
        plan_text = re.sub(r'\n\s*---\s*\n\s*是否要将此计划创建到[Pp]lan[Hh]ub平台[\s\S]*$', '', plan_text)
        plan_text = plan_text.strip()
        print(f"[DEBUG] create_plan_to_platform: cleaned plan_text, new length={len(plan_text)}")

    print(f"[DEBUG] create_plan_to_platform: plan_title={plan_title}, plan_text length={len(plan_text)}, plan_type={plan_type}, plan_info={plan_info}")

    # 确保标题和文本存在
    if not plan_title:
        plan_title = "计划"

    # 优先从 plan_info 中获取时长计算日期（更准确）
    date_info = {
        "start_date": None,
        "target_date": None,
        "estimated_duration_hours": None
    }
    
    duration = plan_info.get("duration") or plan_info.get("days")
    if duration:
        try:
            from app.common.utils import parse_duration
            total_days = parse_duration(duration)
            if total_days and total_days > 0:
                from datetime import date, timedelta
                start_date = date.today()
                date_info["start_date"] = start_date.strftime("%Y-%m-%d")
                target_date = start_date + timedelta(days=total_days)
                date_info["target_date"] = target_date.strftime("%Y-%m-%d")
                print(f"[DEBUG] create_plan_to_platform: calculated from plan_info duration={duration}, days={total_days}")
        except Exception as e:
            print(f"[WARN] create_plan_to_platform: parse duration failed: {e}")
    
    # 如果 plan_info 里没拿到，再尝试从计划文本中解析（fallback）
    if not date_info["start_date"]:
        date_info = extract_plan_dates_and_hours(plan_text)
    
    print(f"[DEBUG] create_plan_to_platform: date_info = {date_info}")

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
                "final_response": f" {result}",
                "agent_output": f" {result}",
                "tools_called": ["create_plan"],
                # 清空所有计划创建相关状态，防止下次路由又回到 plan_confirmation
                "waiting_for_plan_confirmation": False,
                "waiting_for_plan_mode_confirm": False,
                "plan_text_cache": None,
                "plan_title": None,
                "plan_type": None,
                "user_confirmed_create": False,
                "execution_trace": []
            }
        else:
            # 创建失败
            return {
                "final_response": f"计划创建失败：{result}\n\n您可以手动复制以下计划内容：\n\n{plan_text[:500]}...",
                "agent_output": f"计划创建失败：{result}",
                "execution_trace": [
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
                {
                    "node": "create_plan_to_platform",
                    "error": str(e),
                    "success": False
                }
            ]
        }
