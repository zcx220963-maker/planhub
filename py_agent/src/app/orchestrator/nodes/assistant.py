"""
Assistant节点 - 通用工具调用Agent
包装现有的AgentService
"""

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


def get_guidance_for_input(user_input: str) -> str:
    """根据用户输入返回对应的引导提示"""
    user_input_lower = user_input.lower().strip()

    # 搜索相关
    if "搜索" in user_input_lower or user_input_lower in ["搜索", "搜", "找"]:
        return GUIDANCE_TEMPLATES["search"]

    # 打卡相关
    if "打卡" in user_input_lower or user_input_lower in ["打卡", "打卡", "今日打卡"]:
        return GUIDANCE_TEMPLATES["checkin"]

    # 发帖相关
    if "发帖" in user_input_lower or user_input_lower in ["发帖", "发帖子", "发布"]:
        return GUIDANCE_TEMPLATES["post"]

    # 活动相关
    if "活动" in user_input_lower or "查看" in user_input_lower:
        return GUIDANCE_TEMPLATES["activity"]

    # 默认引导
    return GUIDANCE_TEMPLATES["default"]


async def assistant_node(state) -> dict:
    """Assistant节点：通用工具调用助手"""
    try:
        # 延迟导入，避免循环依赖
        from src.app.service.agent_service import get_agent_service

        # 使用全局单例，确保 MemorySaver 持久化对话历史
        agent_service = get_agent_service()

        # 准备输入
        user_input = state.get("user_input", "")
        session_id = state.get("session_id", "default")
        user_id = state.get("user_id")

        # 执行Agent
        result = await agent_service.run_async(
            user_input=user_input,
            session_id=session_id,
            user_id=user_id
        )

        # 检查结果是否太短或像是默认回复，如果是则添加引导
        if result and len(result) < 50:
            # 可能需要添加引导
            result = result + "\n\n" + get_guidance_for_input(user_input)

        # 更新状态
        return {
            "agent_output": result,
            "tools_called": [
                *state.get("tools_called", []),
                "agent_service"
            ],
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "assistant",
                    "success": True,
                    "response_length": len(result) if result else 0
                }
            ]
        }

    except Exception as e:
        return {
            "agent_output": f"抱歉，助手执行失败：{str(e)}",
            "error": str(e),
            "execution_trace": [
                *state.get("execution_trace", []),
                {
                    "node": "assistant",
                    "error": str(e),
                    "success": False
                }
            ]
        }
