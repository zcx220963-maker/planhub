"""
LangChain 工具定义 — 使用 @tool 装饰器 + Pydantic schema

这些工具会被 create_tool_calling_agent 自动转换成 OpenAI tools schema，
由支持 function calling 的模型（如 qwen-max-latest）决定何时调用。

后端返回格式统一为：
{
  "success": true/false,
  "data": { ... },
  "message": "..."
}
"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
from app.common.llm_factory import call_planhub_api
from app.common.tool_validator import validate_tool_params


def _extract_error_message(result: dict) -> str:
    """从后端返回中提取错误信息"""
    message = result.get('message', '未知错误')
    data = result.get('data', {})
    if isinstance(data, dict):
        if data.get('message'):
            message = data.get('message', message)
        if data.get('errors'):
            errors = data.get('errors', [])
            if errors:
                message += f"，详情: {errors}"
    return message


def _check_backend_success(result: dict) -> tuple[bool, str]:
    """
    检查后端返回是否成功
    返回: (是否成功, 错误信息)
    """
    if not result.get("success"):
        return False, _extract_error_message(result)

    # 检查内部 success 字段
    inner_data = result.get("data", {})
    if isinstance(inner_data, dict) and inner_data.get("success") == False:
        return False, _extract_error_message(result)

    return True, ""


# ─── 参数 Schema ────────────────────────────────────────────────────

class CreatePlanInput(BaseModel):
    title: str = Field(description="计划标题，例如：每天学习英语、健身计划")
    description: str = Field(default="", description="计划描述/计划内容，可以是完整的计划文本（包括日程安排、目标、步骤等），支持多行文本")
    start_date: Optional[str] = Field(default=None, description="计划开始日期，格式 YYYY-MM-DD，例如 2026-06-17。如果没有指定则使用今天。")
    target_date: Optional[str] = Field(default=None, description="计划目标/截止日期，格式 YYYY-MM-DD，例如 2026-07-17。")
    estimated_duration_hours: Optional[int] = Field(default=None, description="预计学习/工作时长（小时），例如 30 表示预计30小时。如果有每天投入时间和计划天数，可以自动计算。")


class CreatePostInput(BaseModel):
    content: str = Field(description="帖子内容，例如：今天完成了健身打卡")
    hashtags: str = Field(default="", description="话题标签，多个用逗号分隔，可选")


class SearchPlansInput(BaseModel):
    keyword: str = Field(description="搜索关键词，例如：学习、健身")


class GetItemDetailInput(BaseModel):
    item_type: str = Field(description="项目类型：plan 或 post")
    display_id: int = Field(description="搜索结果中显示的序号ID（从1开始）")


class GetActivityInput(BaseModel):
    user_id: str = Field(description="用户ID，数字，例如：1")


class CheckInInput(BaseModel):
    plan_id: str = Field(description="要打卡的计划ID，数字，例如：1")


class GetUncheckedPlansInput(BaseModel):
    pass


# ─── 工具函数 ───────────────────────────────────────────────────────

# 全局变量：存储最后一次搜索结果（序号 -> 真实ID的映射）
_last_search_results = {
    "plans": [],  # [{display_id: 1, real_id: 123, title: "计划标题"}, ...]
    "posts": []   # [{display_id: 1, real_id: 456, content: "帖子内容"}, ...]
}

# 全局变量：存储最后一次未打卡计划列表（序号 -> 真实ID的映射）
_last_unchecked_plans = []  # [{display_id: 1, real_id: 123, title: "计划标题"}, ...]

# 全局变量：存储最后一次跳转信息（用于前端跳转）
_last_jump_data = None  # {type: "plan", id: 1, title: "xxx"}


@tool(args_schema=CreatePlanInput)
def create_plan(
    title: str,
    description: str = "",
    start_date: Optional[str] = None,
    target_date: Optional[str] = None,
    estimated_duration_hours: Optional[int] = None
) -> str:
    """
    在 PlanHub 创建一个新的学习/工作/健身计划。

    当用户说"帮我创建计划"、"新建一个计划"、"制定计划"时使用此工具。
    如果用户没有提供标题，必须先询问用户标题是什么。

    description 参数支持：
    - 简短的描述文字
    - 完整的计划文本（包括日程安排、目标、步骤等）
    - 多行文本，AI 会自动将完整的计划内容填入 description

    时间字段会自动识别和计算：
    - 从用户输入中提取"1个月"、"30天"等信息
    - 从计划文本中识别"每天学习4小时"等信息
    """
    # 参数验证
    is_valid, errors, warnings = validate_tool_params("create_plan", {"title": title})
    if not is_valid:
        return f"参数验证失败：{'；'.join(errors)}。请修正后再试。"

    # 检查是否有有效的 token（创建计划需要认证）
    from app.common.llm_factory import get_request_token, _jwt_token
    token = get_request_token() or _jwt_token

    if not token:
        return "创建计划需要先登录。请告诉用户：请先登录后再创建计划。"

    # 准备请求数据
    request_data = {
        "title": title,
        "description": description,
        "category": "PERSONAL",
        "priority": "MEDIUM",
        "visibility": "PUBLIC"
    }

    # 添加时间字段（如果提供了）
    if start_date:
        request_data["startDate"] = start_date
    if target_date:
        request_data["targetDate"] = target_date
    if estimated_duration_hours is not None:
        request_data["estimatedDurationHours"] = estimated_duration_hours

    print(f"[DEBUG] create_plan request: {request_data}, token: {token[:20]}...")

    result = call_planhub_api("/plans", "POST", request_data, token=token)
    print(f"[DEBUG] create_plan result: {result}")

    # 检查后端返回是否成功
    success, error_msg = _check_backend_success(result)
    if not success:
        return f"计划创建失败：{error_msg}"

    # 创建成功，返回带跳转链接的消息（格式与搜索结果一致）
    # 前端正则：/(\d+)\.\s+(.+?)\n\s+\[查看详情\]\(\/(plan|post)\/(\d+)\)/g
    inner_data = result.get("data", {})
    plan_data = inner_data.get("data", {}) if isinstance(inner_data, dict) else {}
    plan_id = plan_data.get("id", "")

    # 使用与搜索结果一致的格式：
    #   1. 标题
    #      [查看详情](/plan/ID)
    msg = "创建成功！"
    if warnings:
        msg += f"（提示：{'；'.join(warnings)}）"
    if plan_id:
        msg += f"\n  1. {title}\n     [查看详情](/plan/{plan_id})"
    return msg


@tool(args_schema=CreatePostInput)
def create_post(content: str, hashtags: str = "") -> str:
    """
    在 PlanHub 发布一条新帖子/动态。

    当用户说"帮我发帖"、"发条动态"、"分享"时使用此工具。
    如果用户没有提供内容，必须先询问用户要发什么。
    """
    # 参数验证
    params = {"content": content}
    if hashtags:
        params["hashtags"] = hashtags
    is_valid, errors, warnings = validate_tool_params("create_post", params)
    if not is_valid:
        return f"参数验证失败：{'；'.join(errors)}。请修正后重试。"

    payload = {
        "content": content,
        "postType": "TEXT",
        "privacy": "PUBLIC"
    }
    if hashtags:
        payload["hashtags"] = [h.strip() for h in hashtags.split(",") if h.strip()]

    # 检查是否有有效的 token（创建帖子需要认证）
    from app.common.llm_factory import get_request_token, _jwt_token
    token = get_request_token() or _jwt_token

    if not token:
        return "发布帖子需要先登录。请告诉用户：请先登录后再发布帖子。"

    result = call_planhub_api("/posts", "POST", payload, token=token)
    print(f"[DEBUG] create_post result: {result}")

    # 检查后端返回是否成功
    success, error_msg = _check_backend_success(result)
    if not success:
        return f"帖子发布失败：{error_msg}"

    # 发布成功，返回带跳转链接的消息（格式与搜索结果一致）
    # 前端正则：/(\d+)\.\s+(.+?)\n\s+\[查看详情\]\(\/(plan|post)\/(\d+)\)/g
    inner_data = result.get("data", {})
    post_data = inner_data.get("data", {}) if isinstance(inner_data, dict) else {}
    post_id = post_data.get("id", "")

    # 使用与搜索结果一致的格式：
    #   1. 标题
    #      [查看详情](/post/ID)
    msg = "发布成功！"
    if warnings:
        msg += f"（提示：{'；'.join(warnings)}）"
    if post_id:
        msg += f"\n  1. {content[:30]}\n     [查看详情](/post/{post_id})"
    return msg


@tool(args_schema=SearchPlansInput)
def search_plans(keyword: str) -> str:
    """
    在 PlanHub 搜索计划或帖子。

    当用户说"搜索计划"、"找一下"、"查找"时使用此工具。
    如果用户没有提供关键词，必须先询问。

    返回结果时会使用序号ID（1, 2, 3...），用户可以选择序号查看详情。
    """
    # 参数验证
    is_valid, errors, warnings = validate_tool_params("search_plans", {"keyword": keyword})
    if not is_valid:
        return f"参数验证失败：{'；'.join(errors)}。请修正后重试。"

    global _last_search_results
    _last_search_results = {"plans": [], "posts": []}  # 重置

    print(f"[DEBUG] search_plans called with keyword: '{keyword}'")
    result = call_planhub_api("/search", "GET", {"q": keyword, "type": "all"})
    print(f"[DEBUG] search_plans API result: {result}")

    if not result.get("success"):
        return f"搜索失败：{result.get('message', '未知错误')}"

    # 注意：Java 后端返回格式是 {success: true, data: {success: true, data: {plans: [], posts: []}}}
    # 所以需要两层 data
    outer_data = result.get("data", {})
    inner_data = outer_data.get("data", {})
    plans = inner_data.get("plans", [])
    posts = inner_data.get("posts", [])

    print(f"[DEBUG] search_plans found {len(plans)} plans, {len(posts)} posts")

    if not plans and not posts:
        return f"没有找到与「{keyword}」相关的计划或帖子"

    lines = []
    display_id = 1

    # 限制返回数量，减少 token 消耗
    MAX_PLANS = 3  # 最多返回3个计划
    MAX_POSTS = 2  # 最多返回2条帖子

    if plans:
        lines.append("计划：")
        for plan in plans[:MAX_PLANS]:
            title = plan.get("title", "无标题")
            real_id = plan.get("id")
            # 直接返回带超链接的格式，前端可以解析
            lines.append(f"  {display_id}. {title}")
            lines.append(f"     [查看详情](/plan/{real_id})")
            _last_search_results["plans"].append({
                "display_id": display_id,
                "real_id": real_id,
                "title": title
            })
            display_id += 1

    if posts:
        lines.append("帖子：")
        for post in posts[:MAX_POSTS]:
            content = post.get("content", "无内容")[:30]  # 缩短内容长度
            real_id = post.get("id")
            # 直接返回带超链接的格式
            lines.append(f"  {display_id}. {content}")
            lines.append(f"     [查看详情](/post/{real_id})")
            _last_search_results["posts"].append({
                "display_id": display_id,
                "real_id": real_id,
                "content": content
            })
            display_id += 1

    # 添加提示信息
    lines.append("\n点击上方链接查看详情，或回复序号获取更多信息")

    return "\n".join(lines)


@tool(args_schema=GetItemDetailInput)
def get_item_detail(item_type: str, display_id: int) -> str:
    """
    获取搜索结果的详细信息并提供跳转链接。

    当用户回复搜索结果中的序号时使用此工具。
    item_type 是 "plan" 或 "post"，display_id 是搜索结果中显示的序号。

    返回格式化的跳转信息，前端可以据此跳转到详情页。
    """
    # 参数验证
    is_valid, errors, warnings = validate_tool_params("get_item_detail", {"display_id": display_id})
    if not is_valid:
        return f"参数验证失败：{'；'.join(errors)}。请修正后重试。"

    global _last_search_results, _last_jump_data
    _last_jump_data = None  # 重置

    print(f"[DEBUG] get_item_detail called: item_type={item_type}, display_id={display_id}")

    # 根据 item_type 选择对应的结果列表
    if item_type == "plan":
        items = _last_search_results.get("plans", [])
        item_name = "计划"
    elif item_type == "post":
        items = _last_search_results.get("posts", [])
        item_name = "帖子"
    else:
        return f"❌ 无效的项目类型：{item_type}，必须是 plan 或 post"

    # 查找对应 display_id 的项目
    target_item = None
    for item in items:
        if item.get("display_id") == display_id:
            target_item = item
            break

    if not target_item:
        # 提供更有用的错误信息
        if item_type == "plan":
            available = [item.get("display_id") for item in _last_search_results.get("plans", [])]
        else:
            available = [item.get("display_id") for item in _last_search_results.get("posts", [])]

        if available:
            return f"❌ 未找到序号为 {display_id} 的{item_name}，当前可用的序号是：{available}"
        else:
            return f"❌ 没有可用的{item_name}，请先进行搜索"

    real_id = target_item.get("real_id")
    title = target_item.get("title") or target_item.get("content", "")

    # 保存跳转信息到全局变量（用于API响应）
    _last_jump_data = {
        "type": item_type,
        "id": real_id,
        "title": title,
        "display_id": display_id
    }

    # 构建跳转链接（统一使用搜索结果的链接格式）
    if item_type == "plan":
        jump_path = f"/plan/{real_id}"
        title = target_item.get('title', '无标题')
        return (
            f"计划详情：\n"
            f"  序号：{display_id}\n"
            f"  标题：{title}\n"
            f"  ID：{real_id}\n"
            f"     [查看详情]({jump_path})"
        )
    else:
        jump_path = f"/post/{real_id}"
        content = target_item.get('content', '')[:50]
        return (
            f"帖子详情：\n"
            f"  序号：{display_id}\n"
            f"  内容：{content}\n"
            f"  ID：{real_id}\n"
            f"     [查看详情]({jump_path})"
        )


@tool(args_schema=GetActivityInput)
def get_user_activity(user_id: str) -> str:
    """
    获取 PlanHub 用户的活动记录。

    当用户说"查看我的活动"、"我的动态"、"最近做了什么"时使用此工具。
    如果用户没有提供 user_id，可以先使用默认值 1 或询问用户。
    """
    # 参数验证
    is_valid, errors, warnings = validate_tool_params("get_user_activity", {"user_id": user_id})
    if not is_valid:
        return f"参数验证失败：{'；'.join(errors)}。请修正后重试。"

    result = call_planhub_api(f"/activities/{user_id}", "GET")

    # 检查后端返回是否成功
    success, error_msg = _check_backend_success(result)
    if not success:
        return f"获取活动记录失败：{error_msg}"

    # 注意：后端返回格式可能是 {success: true, data: [...]} 或 {success: true, data: {records: [...]}}
    inner_data = result.get("data", {})
    if isinstance(inner_data, dict) and "records" in inner_data:
        activities = inner_data.get("records", [])
    elif isinstance(inner_data, list):
        activities = inner_data
    else:
        activities = []

    if not activities:
        return "暂无活动记录"

    lines = []
    for i, act in enumerate(activities[:5], 1):  # 只返回最近5条
        act_type = act.get("type", "未知")
        desc = act.get("description", "")[:40]  # 缩短描述长度
        lines.append(f"  {i}. [{act_type}] {desc}")
    return "活动记录：\n" + "\n".join(lines)


@tool(args_schema=GetUncheckedPlansInput)
def get_unchecked_plans() -> str:
    """
    获取用户今天还未打卡的所有计划列表。

    当用户说"打卡"、"签到"、"我要打卡"时，必须先调用此工具获取未打卡计划列表。
    """
    # 检查是否有有效的 token（获取计划列表需要认证）
    from app.common.llm_factory import get_request_token, _jwt_token
    token = get_request_token() or _jwt_token

    if not token:
        return "获取计划列表需要先登录。请告诉用户：请先登录后再查看计划列表。"

    result = call_planhub_api("/plans", "GET", {}, token=token)

    # DEBUG: 打印后端返回的原始数据
    print(f"[DEBUG] get_unchecked_plans: 后端返回原始数据 = {result}", flush=True)

    # 检查后端返回是否成功
    success, error_msg = _check_backend_success(result)
    if not success:
        return f"获取计划列表失败：{error_msg}"

    # 注意：后端返回格式可能是 {success: true, data: [...]} 或 {success: true, data: {records: [...]}}
    inner_data = result.get("data", {})

    # DEBUG: 打印解析前的数据
    print(f"[DEBUG] get_unchecked_plans: inner_data 类型 = {type(inner_data)}, 内容 = {inner_data}", flush=True)

    if isinstance(inner_data, dict) and "records" in inner_data:
        plans = inner_data.get("records", [])
    elif isinstance(inner_data, dict) and "data" in inner_data:
        # 处理 {data: {data: [...]}} 的情况
        plans = inner_data.get("data", [])
        if isinstance(plans, dict) and "records" in plans:
            plans = plans.get("records", [])
    elif isinstance(inner_data, list):
        plans = inner_data
    else:
        plans = []

    # DEBUG: 打印获取到的计划列表
    print(f"[DEBUG] get_unchecked_plans: 获取到 {len(plans)} 个计划", flush=True)
    for plan in plans:
        print(f"[DEBUG]   - 计划: id={plan.get('id')}, title={plan.get('title')}", flush=True)

    unchecked_plans = []

    # 批量检查打卡状态（带错误处理）
    for plan in plans:
        plan_id = plan.get("id")
        if not plan_id:
            continue

        try:
            checkin_result = call_planhub_api(f"/plans/{plan_id}/checkins/exists", "GET", {}, token=token)

            if checkin_result.get("success"):
                checkin_data = checkin_result.get("data", {})
                if checkin_data.get("success"):
                    exists = checkin_data.get("data", False)
                    if not exists:
                        unchecked_plans.append(plan)
                else:
                    # 打卡检查失败，假设未打卡（让用户自己选择）
                    print(f"[WARN] 计划 {plan_id} 打卡检查失败，假设未打卡", flush=True)
                    unchecked_plans.append(plan)
            else:
                # API 调用失败，假设未打卡
                print(f"[WARN] 计划 {plan_id} API 调用失败，假设未打卡", flush=True)
                unchecked_plans.append(plan)

        except Exception as e:
            # 异常情况，假设未打卡
            print(f"[ERROR] 计划 {plan_id} 打卡检查异常: {e}，假设未打卡", flush=True)
            unchecked_plans.append(plan)

    if not unchecked_plans:
        return "您今天的计划都已经打卡完成了！"

    # 保存到全局变量，方便后续打卡时获取真实ID
    global _last_unchecked_plans
    _last_unchecked_plans = []

    plan_list = []
    for i, plan in enumerate(unchecked_plans, 1):
        plan_id = plan.get("id")
        title = plan.get("title", "无标题")
        plan_list.append(f"{i}. {title} (ID: {plan_id})")
        _last_unchecked_plans.append({
            "display_id": i,
            "real_id": plan_id,
            "title": title
        })

    return "以下是您今天还未打卡的计划：\n" + "\n".join(plan_list) + "\n\n请告诉我要打卡第几个（或直接说计划ID）？"


def _resolve_plan_id(plan_id_or_index: str) -> str:
    """
    解析用户提供的计划ID或序号，返回真实计划ID

    支持格式：
    - 数字ID： "1", "123"
    - 中文序号： "第一个", "第二个", "第三个"
    - 数字序号： "第1个", "第2个"
    """
    import re

    # 中文数字映射
    chinese_numbers = {
        "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
        "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20
    }

    plan_id_or_index = plan_id_or_index.strip()

    # 使用全局变量
    global _last_unchecked_plans

    # 尝试匹配中文序号： "第一个", "第二个"
    for cn_num, index in chinese_numbers.items():
        if plan_id_or_index == f"第{cn_num}个" or plan_id_or_index == f"第{cn_num}":
            # 从全局变量中获取对应的真实ID
            if _last_unchecked_plans and 1 <= index <= len(_last_unchecked_plans):
                return str(_last_unchecked_plans[index - 1]["real_id"])
            return plan_id_or_index

    # 尝试匹配纯中文数字： "一", "二", "三"
    if plan_id_or_index in chinese_numbers:
        index = chinese_numbers[plan_id_or_index]
        if _last_unchecked_plans and 1 <= index <= len(_last_unchecked_plans):
            return str(_last_unchecked_plans[index - 1]["real_id"])

    # 尝试匹配 "第N个" 格式（N是阿拉伯数字）
    match = re.match(r'^第(\d+)个?$', plan_id_or_index)
    if match:
        index = int(match.group(1))
        if _last_unchecked_plans and 1 <= index <= len(_last_unchecked_plans):
            return str(_last_unchecked_plans[index - 1]["real_id"])
        return plan_id_or_index

    # 尝试匹配阿拉伯数字： "1", "2", "123"
    if plan_id_or_index.isdigit():
        index = int(plan_id_or_index)
        # 先尝试作为序号（从1开始）
        if _last_unchecked_plans and 1 <= index <= len(_last_unchecked_plans):
            return str(_last_unchecked_plans[index - 1]["real_id"])
        # 如果超出范围，可能直接是计划ID
        return plan_id_or_index

    # 无法解析，返回原值
    return plan_id_or_index


@tool(args_schema=CheckInInput)
def check_in_plan(plan_id: str) -> str:
    """
    对某个计划进行打卡。

    当用户说"打卡"、"签到"、"我完成了"时使用此工具。
    【重要】在调用此工具前，必须先调用 get_unchecked_plans 获取未打卡计划列表！
    如果用户没有提供 plan_id，必须先询问用户选择第几个计划，或者直接提供计划ID。

    支持用户输入：
    - 计划ID： "1", "123"
    - 中文序号： "第一个", "第二个"
    - 数字序号： "第1个", "第2个"

    【自动流程】如果 _last_unchecked_plans 为空（说明还没有获取过未打卡列表），
    则自动调用 get_unchecked_plans 获取列表并返回，让用户选择。
    """
    # 检查是否已经获取过未打卡计划列表
    global _last_unchecked_plans
    if not _last_unchecked_plans:
        # 还没有获取过列表，自动调用 get_unchecked_plans
        print(f"[DEBUG] check_in_plan: _last_unchecked_plans 为空，自动调用 get_unchecked_plans", flush=True)
        return get_unchecked_plans()

    # 解析用户输入（可能是中文序号或数字）
    original_input = plan_id
    plan_id = _resolve_plan_id(plan_id)

    # 如果解析失败，提示用户
    if plan_id == original_input and not plan_id.isdigit():
        return f"无法识别「{original_input}」，请输入计划序号（如：1、2）或中文序号（如：第一个、第二个）"

    # 参数验证
    is_valid, errors, warnings = validate_tool_params("check_in_plan", {"plan_id": plan_id})
    if not is_valid:
        return f"参数验证失败：{'；'.join(errors)}。请修正后重试。"

    # 检查是否有有效的 token（打卡需要认证）
    from app.common.llm_factory import get_request_token, _jwt_token
    token = get_request_token() or _jwt_token

    if not token:
        return "打卡需要先登录。请告诉用户：请先登录后再打卡。"

    # 使用正确的字段名：notes 而不是 content
    request_data = {"notes": "今日打卡"}
    print(f"[DEBUG] check_in_plan request: endpoint=/plans/{plan_id}/checkins, data={request_data}", flush=True)

    result = call_planhub_api(
        f"/plans/{plan_id}/checkins",
        "POST",
        request_data,
        token=token
    )

    print(f"[DEBUG] check_in_plan result: {result}", flush=True)

    # 检查后端返回是否成功
    success, error_msg = _check_backend_success(result)
    if not success:
        return f"打卡失败：{error_msg}"

    # 打卡成功，返回带跳转链接的消息（格式与搜索结果一致）
    # 前端正则：/(\d+)\.\s+(.+?)\n\s+\[查看详情\]\(\/(plan|post)\/(\d+)\)/g
    inner_data = result.get("data", {})
    checkin_data = inner_data.get("data", {}) if isinstance(inner_data, dict) else {}
    plan_title = checkin_data.get("title", "计划")
    return (
        f"打卡成功！已完成今日打卡\n\n"
        f"  1. {plan_title}\n"
        f"     [查看详情](/plan/{plan_id})"
    )


# ─── 工具列表 ───────────────────────────────────────────────────────

ALL_TOOLS = [
    create_plan,
    create_post,
    search_plans,
    get_item_detail,
    get_user_activity,
    get_unchecked_plans,
    check_in_plan,
]
