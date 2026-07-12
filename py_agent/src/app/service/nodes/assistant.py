"""
Assistant节点 - 通用工具调用Agent
包装现有的AgentService

优化：
- 如果 LLM tool calling 失败（返回原始 JSON），走关键词兜底逻辑
- 对明确的搜索、打卡等意图，直接用关键词匹配调用工具
"""

import json
import re

# 引导提示模板
GUIDANCE_TEMPLATES = {
    "search": """您可以这样搜索：
• "搜索学习计划"
• "搜索健身计划"
• "搜索+关键词"  """,

    "checkin": """您可以这样打卡：
• "我要打卡" - 查看未打卡计划并选择
• "今日打卡" - 快速打卡
• "打卡+计划名" - 直接打卡指定计划  """,

    "post": """您可以这样发帖：
• "帮我发帖，内容：今天完成了健身"
• "发帖，标题：学习心得，内容：今天学习了Python"  """,

    "activity": """您可以查看：
• "查看我的活动" - 查看最近的打卡和发帖记录
• "查看我的计划" - 查看创建的所有计划  """,

    "default": """我不确定您的意思，您可以说：
• "搜索XXX" - 搜索计划或帖子
• "我要打卡" - 进行打卡
• "帮我发帖，内容：XXX" - 发布帖子
• "查看我的活动" - 查看活动记录
• 或直接告诉我您想做什么！"""
}


def is_tool_call_json(text: str) -> bool:
    """判断文本是否是工具调用的 JSON 格式（LLM tool calling 失败的标志）"""
    if not text:
        return False
    text = text.strip()
    # 检查是否以 { 开头并包含 name/arguments 等关键词
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and ("name" in data or "tool" in data):
                return True
        except json.JSONDecodeError:
            pass
    # 检查是否是工具调用数组格式
    if text.startswith("[") and text.endswith("]"):
        if '"name"' in text and '"arguments"' in text:
            return True
    return False


def extract_search_keyword(user_input: str) -> str:
    """从用户输入中提取搜索关键词"""
    user_input = user_input.strip()
    # 去掉"搜索"、"搜"、"找"等前缀
    patterns = [
        r'^(搜索|搜|找|查找|查询)(一下|下)?(.+)$',
        r'^(.+?)(搜索|搜|找)$',
    ]
    for pattern in patterns:
        match = re.match(pattern, user_input)
        if match:
            keyword = match.group(match.lastindex).strip()
            # 去掉"计划"、"帖子"等后缀如果太泛
            if keyword and keyword not in ["计划", "帖子", ""]:
                return keyword
    # 如果没有明确关键词，返回空
    return ""


def get_guidance_for_input(user_input: str) -> str:
    """根据用户输入返回对应的引导提示"""
    user_input_lower = user_input.lower().strip()

    # 搜索相关
    if "搜索" in user_input_lower or user_input_lower in ["搜索", "搜", "找"]:
        return GUIDANCE_TEMPLATES["search"]

    # 打卡相关（包括纯数字输入，可能是选择序号）
    if "打卡" in user_input_lower or user_input_lower in ["打卡", "打卡", "今日打卡"]:
        return GUIDANCE_TEMPLATES["checkin"]

    # 纯数字输入 → 可能是选择计划序号，不追加引导
    if user_input_lower.isdigit():
        return ""

    # 发帖相关
    if "发帖" in user_input_lower or user_input_lower in ["发帖", "发帖子", "发布"]:
        return GUIDANCE_TEMPLATES["post"]

    # 活动相关
    if "活动" in user_input_lower or "查看" in user_input_lower:
        return GUIDANCE_TEMPLATES["activity"]

    # 默认引导
    return GUIDANCE_TEMPLATES["default"]


async def direct_search(keyword: str) -> str:
    """直接调用搜索工具，不走 LLM"""
    try:
        from src.app.common.langchain_tools import search_plans
        result = search_plans.invoke({"keyword": keyword})
        return result
    except Exception as e:
        return f"搜索失败：{str(e)}"


async def _direct_checkin(index: int) -> str:
    """直接调用打卡工具（绕过LLM）"""
    try:
        from src.app.common.langchain_tools import check_in_plan
        result = check_in_plan.invoke({"plan_id": str(index)})
        return result
    except Exception as e:
        return f"打卡失败：{str(e)}"


async def assistant_node(state) -> dict:
    """Assistant节点：通用工具调用助手
    
    优化：打卡流程中，用户输入序号后直接调用check_in_plan，不经过LLM判断
    """
    try:
        # 延迟导入，避免循环依赖
        from ..agent_runner import get_agent_runner

        # 使用全局单例，确保 MemorySaver 持久化对话历史
        agent_runner = get_agent_runner()

        # 准备输入
        user_input = state.get("user_input", "")
        session_id = state.get("session_id", "default")
        user_id = state.get("user_id")
        
        # 从 state 中获取 action_type 和 action_params（supervisor 已经解析好）
        action_type = state.get("action_type", "none")
        action_params = state.get("action_params", {})
        print(f"[DEBUG] assistant_node: action_type={action_type}, action_params={action_params}")

        # ===== 特殊处理：打卡流程中用户输入序号 =====
        # 如果action_type是checkin且有index参数，直接调用打卡工具，不经过LLM
        if action_type == "checkin" and action_params.get("index"):
            index = action_params["index"]
            print(f"[DEBUG] assistant_node: 直接调用打卡工具，序号={index}")
            result = await _direct_checkin(index)
            # 更新状态
            return {
                "intent": "assistant",
                "agent_output": result,
                "tools_called": [
                    *state.get("tools_called", []),
                    "check_in_plan"
                ],
                "execution_trace": [
                    {
                        "node": "assistant",
                        "success": True,
                        "response_length": len(result) if result else 0,
                        "direct_tool_call": "check_in_plan"
                    }
                ]
            }

        # 执行Agent，传入 action_type 和 action_params
        result = await agent_runner.run_async(
            user_input=user_input,
            session_id=session_id,
            user_id=user_id,
            action_type=action_type,
            action_params=action_params
        )

        # ===== 后置：校验结果，如果是工具调用 JSON（说明 LLM tool calling 失败），走兜底 =====
        if is_tool_call_json(result):
            print(f"[DEBUG] assistant_node: LLM 返回工具调用 JSON，走兜底逻辑")
            # 根据用户输入返回对应的引导
            guidance = get_guidance_for_input(user_input)
            if guidance:
                result = guidance
            else:
                result = GUIDANCE_TEMPLATES["default"]

        # 检查结果是否太短或像是默认回复，如果是则添加引导
        # 打卡成功消息约40-50字符，不应追加引导；只有真正需要引导时才追加
        if result and len(result) < 30:
            # 可能需要添加引导
            guidance = get_guidance_for_input(user_input)
            if guidance:
                result = result + "\n\n" + guidance

        # 更新状态
        return {
            "intent": "assistant",
            "agent_output": result,
            "tools_called": [
                *state.get("tools_called", []),
                "agent_runner"
            ],
            "execution_trace": [
                {
                    "node": "assistant",
                    "success": True,
                    "response_length": len(result) if result else 0
                }
            ]
        }

    except Exception as e:
        return {
            "intent": "assistant",
            "agent_output": f"抱歉，助手执行失败：{str(e)}",
            "error": str(e),
            "execution_trace": [
                {
                    "node": "assistant",
                    "error": str(e),
                    "success": False
                }
            ]
        }
