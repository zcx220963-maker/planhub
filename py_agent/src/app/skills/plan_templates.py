"""
计划模板 Skills - 根据类型生成结构化计划

提供 5 种计划类型的模板生成功能，所有变量都有默认值（空值安全）。
支持 RAG 上下文整合，将知识库内容嵌入计划中。
"""

import json
from typing import Dict, Any, List, Optional

# ─── 辅助函数 ──────────────────────────────────────────────────

def _parse_duration(duration: str) -> int:
    """解析时长字符串，返回天数

    支持格式：
    - 数字+单位：1个月、2周、3天
    - 中文数字：一个星期、两个月、半年
    """
    import re

    # 中文数字映射
    chinese_numbers = {
        "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        "半": 0.5
    }

    # 1. 先尝试匹配阿拉伯数字+单位
    match = re.search(r"(\d+)", duration)
    if match:
        num = int(match.group(1))
        if "年" in duration:
            return int(num * 365)
        elif "月" in duration:
            return int(num * 30)
        elif "周" in duration or "星期" in duration:
            return int(num * 7)
        elif "天" in duration or "日" in duration:
            return int(num)
        else:
            return int(num)

    # 2. 尝试匹配中文数字+单位
    for chinese_num, value in chinese_numbers.items():
        if chinese_num in duration:
            if "年" in duration:
                return int(value * 365)
            elif "月" in duration:
                return int(value * 30)
            elif "周" in duration or "星期" in duration:
                return int(value * 7)
            elif "天" in duration or "日" in duration:
                return int(value)

    # 3. 特殊关键词
    if "半年" in duration:
        return 180
    if "一年" in duration or "一年" in duration:
        return 365

    # 4. 默认返回7天（而不是30天）
    return 7

def _parse_amount(goal: str) -> float:
    """解析金额字符串"""
    import re
    match = re.search(r"(\d+)", goal)
    if not match:
        return 10000
    num = int(match.group(1))
    if "万" in goal:
        return num * 10000
    elif "千" in goal:
        return num * 1000
    else:
        return num

def _build_rag_section(rag_context: Optional[str]) -> str:
    """构建 RAG 上下文段落（带容错）"""
    if rag_context and isinstance(rag_context, str) and len(rag_context.strip()) > 0:
        return f"""

【知识库参考】
根据你的知识库内容，以下是相关信息：
{rag_context}
"""
    return ""

def _build_api_data_section(api_data: Dict[str, Any], plan_type: str) -> str:
    """构建 API 数据展示段落（提高可信度）"""
    if not api_data:
        return ""

    sections = []

    # 学习计划：展示 API 数据（使用国内 API）
    if plan_type == "learning":
        # 今日诗词
        if "get_jinrishici" in api_data and "error" not in api_data["get_jinrishici"]:
            jinrishici = api_data["get_jinrishici"]
            content = jinrishici.get("content", "")
            title = jinrishici.get("title", "")
            author = jinrishici.get("author", "")
            dynasty = jinrishici.get("dynasty", "")
            if content:
                sections.append(f"【今日诗词】\n推荐诗词：《{title}》- {author}（{dynasty}）\n{content}\n")

        # 一言
        if "get_hitokoto" in api_data and "error" not in api_data["get_hitokoto"]:
            hitokoto = api_data["get_hitokoto"]
            content = hitokoto.get("content", "")
            author = hitokoto.get("author", "")
            if content:
                sections.append(f"【每日一句】\n{content} —— {author}\n")

        # 天气
        if "get_weather_forecast" in api_data and "error" not in api_data["get_weather_forecast"]:
            weather = api_data["get_weather_forecast"]
            city = weather.get("city", "")
            forecast = weather.get("forecast", [])
            if forecast:
                sections.append(f"【{city}天气预报】\n")
                for day in forecast[:5]:
                    date = day.get("date", "")
                    max_temp = day.get("max_temp", "")
                    min_temp = day.get("min_temp", "")
                    description = day.get("description", "")
                    sections.append(f"  {date}: {min_temp}°C ~ {max_temp}°C，{description}")
                sections.append("")

    # 健康计划：展示 API 数据
    elif plan_type == "health":
        books = []
        for api_name in ["search_open_library", "search_gutendex"]:
            if api_name in api_data and "books" in api_data[api_name]:
                books.extend(api_data[api_name]["books"])
        if books:
            sources = []
            for book in books[:3]:
                if isinstance(book, dict):
                    title = book.get("title", "未知")
                    author = book.get("author", "未知")
                    sources.append(f"《{title}》- {author}")
            if sources:
                sections.append(f"📚 书籍来源：\n  " + "\n  ".join(sources))

    # 健康计划：展示天气和营养来源
    elif plan_type == "health":
        # 显示天气 API 调用结果
        if "get_weather_forecast" in api_data:
            weather = api_data["get_weather_forecast"]
            if "error" in weather:
                sections.append(f"🌤️ 天气查询（Open-Meteo）：查询失败 - {weather['error']}")
            elif "forecast" in weather and len(weather["forecast"]) > 0:
                forecast = weather["forecast"][0]
                date = forecast.get("date", "未知")
                max_temp = forecast.get("max_temp", "未知")
                min_temp = forecast.get("min_temp", "未知")
                weather_desc = forecast.get("weather", "未知")
                city = weather.get("city", "未知")
                sections.append(f"🌤️ 天气来源（Open-Meteo）：\n  城市：{city}\n  首日预报：{date}\n  温度：{min_temp}°C ~ {max_temp}°C\n  天气：{weather_desc}")
            else:
                sections.append("🌤️ 天气查询（Open-Meteo）：无数据返回")

        # 显示营养 API 调用结果
        nutrition_apis = []
        if "get_food_nutrition" in api_data:
            food_data = api_data["get_food_nutrition"]
            if "error" not in food_data:
                nutrition_apis.append("Open Food Facts")
        if "get_fruit_nutrition" in api_data:
            fruit_data = api_data["get_fruit_nutrition"]
            if "error" not in fruit_data:
                nutrition_apis.append("Fruityvice")

        if nutrition_apis:
            sections.append(f"🥗 营养数据来源：{'、'.join(nutrition_apis)}")
        elif "get_food_nutrition" in api_data or "get_fruit_nutrition" in api_data:
            sections.append("🥗 营养数据来源：Open Food Facts、Fruityvice（查询失败）")

    # 旅行计划：展示天气和汇率来源
    elif plan_type == "travel":
        if "get_weather_forecast" in api_data:
            weather = api_data["get_weather_forecast"]
            if "city" in weather:
                sections.append(f"🌤️ 天气来源（Open-Meteo）：{weather['city']}")

        if "get_exchange_rates" in api_data:
            rates = api_data["get_exchange_rates"]
            if "base" in rates and "rates" in rates:
                base = rates["base"]
                rate_count = len(rates["rates"])
                sections.append(f"💱 汇率来源（ExchangeRate-API）：基准货币 {base}，共 {rate_count} 种货币")

    # 工作计划：展示节假日来源
    elif plan_type == "work":
        if "get_china_holidays" in api_data:
            holidays = api_data["get_china_holidays"]
            if "holidays" in holidays:
                holiday_count = len(holidays["holidays"])
                sections.append(f"📅 节假日来源（timor.tech）：共 {holiday_count} 个节假日")

        if "get_world_time" in api_data:
            sections.append("⏰ 时区来源：WorldTimeAPI")

    # 财务计划：展示汇率和经济数据来源
    elif plan_type == "finance":
        if "get_exchange_rates" in api_data:
            rates = api_data["get_exchange_rates"]
            if "base" in rates:
                sections.append(f"💱 汇率来源（ExchangeRate-API）：基准货币 {rates['base']}")

        if "get_economic_data" in api_data:
            sections.append("📊 经济数据来源：Econdb")

    if sections:
        return "\n\n【数据来源】\n" + "\n\n".join(sections)
    return ""

def _safe_get(data: Dict, key: str, default: Any = None) -> Any:
    """安全获取字典值，处理 None 情况"""
    if data is None:
        return default
    return data.get(key, default)

# ─── 学习计划模板 ──────────────────────────────────────────────

def generate_learning_plan(params: Dict[str, Any], rag_context: Optional[str] = None) -> str:
    """生成学习计划模板

    params:
        - topic: 学习主题（如 "Python"）
        - duration: 学习时长（如 "1个月"）
        - goal: 学习目标（如 "入门"）
        - books: 推荐书籍列表
        - daily_hours: 每天学习小时数
        - level: 当前水平（可选）
    """
    # ✅ 安全：所有变量都有默认值
    topic = _safe_get(params, "topic", "未指定主题")
    duration = _safe_get(params, "duration", "未指定时长")
    goal = _safe_get(params, "goal", "未指定目标")
    books = _safe_get(params, "books", []) or []  # 确保是列表，即使 API 返回 None
    daily_hours = _safe_get(params, "daily_hours", 2)
    level = _safe_get(params, "level", "未指定")

    # 解析时长（简单版）
    days = _parse_duration(duration)

    # 生成书籍推荐文本（带容错）
    book_text = ""
    if books and isinstance(books, list) and len(books) > 0:
        book_text = "\n\n推荐书籍："
        for i, book in enumerate(books[:3], 1):
            # ✅ 安全：每个字段都有默认值
            if isinstance(book, dict):
                title = book.get("title", "未知书名")
                author = book.get("author", "未知作者")
            else:
                title = str(book)
                author = "未知作者"
            book_text += f"\n  {i}. 《{title}》- {author}"
    else:
        # ✅ 兜底：API 返回空结果时的默认文本
        book_text = "\n\n推荐书籍：暂无推荐书籍，建议手动搜索或稍后再试"

    # 生成周计划
    weeks = days // 7 if days >= 7 else 1
    weekly_plan = ""
    for week in range(1, min(weeks + 1, 5)):
        weekly_plan += f"\n\n第{week}周："
        if week == 1:
            weekly_plan += f"\n  重点：基础概念学习"
            weekly_plan += f"\n  任务：每天学习{daily_hours}小时，完成入门教程"
        elif week == 2:
            weekly_plan += f"\n  重点：实践练习"
            weekly_plan += f"\n  任务：完成基础练习题和小项目"
        elif week == 3:
            weekly_plan += f"\n  重点：项目实战"
            weekly_plan += f"\n  任务：开始小型项目，巩固所学知识"
        else:
            weekly_plan += f"\n  重点：巩固提升"
            weekly_plan += f"\n  任务：复习总结，准备进阶学习"

    # RAG 上下文（带容错）
    rag_section = _build_rag_section(rag_context)

    # API 数据展示（提高可信度）
    api_data = _safe_get(params, "_api_data", {})
    api_section = _build_api_data_section(api_data, "learning")

    # 处理 daily_hours 的显示（避免重复"小时"）
    daily_hours_display = daily_hours
    if isinstance(daily_hours, (int, float)):
        daily_hours_display = f"{daily_hours}小时"
    elif isinstance(daily_hours, str):
        # 如果已经包含"小时"或"h"，不再添加
        if "小时" not in daily_hours and "h" not in daily_hours.lower():
            daily_hours_display = f"{daily_hours}小时"

    # ✅ 安全：使用 f-string 渲染，所有变量都已确保有值
    return f"""
{topic} 学习计划（{duration}）

目标：{goal}
当前水平：{level}
每天学习：{daily_hours_display}
总天数：{days}天
{book_text}
{weekly_plan}
{rag_section}
{api_section}
---
已生成学习计划！您可以根据此计划在 PlanHub 中创建计划。
"""

# ─── 健康计划模板 ──────────────────────────────────────────────

def _get_weather_advice(temp: float) -> str:
    """根据温度给出运动建议"""
    if temp < 5:
        return "天气较冷，建议室内运动或做好保暖"
    elif temp < 15:
        return "天气凉爽，适合户外运动"
    elif temp < 25:
        return "天气舒适，非常适合户外运动"
    else:
        return "天气较热，注意防暑，建议早晚运动"

def _get_exercise_plan(level: str, duration: str) -> str:
    """根据强度生成运动计划"""
    if level == "低":
        return """  - 周一/三/五：散步30分钟
  - 周二/四：瑜伽或拉伸20分钟
  - 周末：轻松户外活动"""
    elif level == "中":
        return """  - 周一/三/五：跑步或快走30-45分钟
  - 周二/四：力量训练30分钟
  - 周末：游泳或骑行1小时"""
    else:
        return """  - 周一/三/五：HIIT训练45分钟
  - 周二/四：重量训练1小时
  - 周末：长跑或登山"""

def _get_diet_plan(goal: str) -> str:
    """根据目标生成饮食建议"""
    if "减肥" in goal or "瘦身" in goal:
        return """  - 早餐：燕麦+水果+鸡蛋（约300卡）
  - 午餐：鸡胸肉+蔬菜+糙米（约500卡）
  - 晚餐：鱼肉+蔬菜（约400卡）
  - 建议：多喝水，少油少糖"""
    elif "增肌" in goal:
        return """  - 早餐：全麦面包+鸡蛋+牛奶（约400卡）
  - 午餐：牛肉+米饭+蔬菜（约600卡）
  - 晚餐：鸡肉+红薯+蔬菜（约500卡）
  - 建议：增加蛋白质摄入"""
    else:
        return """  - 早餐：均衡搭配（约350卡）
  - 午餐：主食+蛋白质+蔬菜（约550卡）
  - 晚餐：清淡为主（约400卡）
  - 建议：营养均衡，定时定量"""

def generate_health_plan(params: Dict[str, Any], rag_context: Optional[str] = None) -> str:
    """生成健康计划模板

    params:
        - goal: 健康目标（如 "减肥5公斤"）
        - duration: 计划时长（如 "1个月"）
        - weather: 天气信息
        - activity_level: 运动强度（低/中/高）
        - height: 身高（可选）
        - weight: 体重（可选）
    """
    # ✅ 所有变量都有默认值
    goal = _safe_get(params, "goal", "未指定目标")
    duration = _safe_get(params, "duration", "未指定时长")
    weather = _safe_get(params, "weather", {}) or {}
    activity_level = _safe_get(params, "activity_level", "中")
    height = _safe_get(params, "height", 170)
    weight = _safe_get(params, "weight", 65)

    # 计算 BMI
    bmi = weight / ((height / 100) ** 2) if height > 0 else 0
    bmi_status = "偏瘦" if bmi < 18.5 else ("正常" if bmi < 24 else ("偏胖" if bmi < 28 else "肥胖"))

    # 天气分析（带容错）
    weather_text = ""
    if weather and isinstance(weather, dict) and "forecast" in weather:
        forecast = weather["forecast"]
        if forecast and len(forecast) > 0:
            try:
                avg_temp = sum(day.get("max_temp", 20) for day in forecast) / len(forecast)
                weather_text = f"\n\n天气条件：\n  平均温度：{avg_temp:.1f}°C\n  建议：{_get_weather_advice(avg_temp)}"
            except:
                weather_text = "\n\n天气条件：暂无天气数据"

    # 运动方案
    exercise_plan = _get_exercise_plan(activity_level, duration)

    # 饮食方案
    diet_plan = _get_diet_plan(goal)

    # RAG 上下文
    rag_section = _build_rag_section(rag_context)

    # API 数据展示（提高可信度）
    api_data = _safe_get(params, "_api_data", {})
    api_section = _build_api_data_section(api_data, "health")

    return f"""
健康计划（{duration}）

目标：{goal}
身高：{height}cm
体重：{weight}kg
BMI：{bmi:.1f}（{bmi_status}）
{weather_text}

运动方案：
{exercise_plan}

饮食建议：
{diet_plan}
{rag_section}
{api_section}
---
已生成健康计划！您可以根据此计划在 PlanHub 中创建计划。
"""

# ─── 旅行计划模板 ──────────────────────────────────────────────

def _generate_itinerary(destination: str, days: int, interests: list) -> str:
    """生成行程（简化版）"""
    itinerary = ""
    for day in range(1, days + 1):
        itinerary += f"\n\n第{day}天："
        if day == 1:
            itinerary += f"\n  上午：抵达{destination}，入住酒店"
            itinerary += f"\n  下午：游览市中心景点"
            itinerary += f"\n  晚上：品尝当地美食"
        elif day == days:
            itinerary += f"\n  上午：购买纪念品"
            itinerary += f"\n  下午：返程"
        else:
            itinerary += f"\n  上午：游览主要景点"
            itinerary += f"\n  下午：体验当地文化"
            itinerary += f"\n  晚上：自由活动"
    return itinerary

def generate_travel_plan(params: Dict[str, Any], rag_context: Optional[str] = None) -> str:
    """生成旅行计划模板

    params:
        - destination: 目的地（如 "北京"）
        - days: 旅行天数
        - weather: 天气信息
        - budget: 预算
        - interests: 兴趣点列表
    """
    destination = _safe_get(params, "destination", "未知目的地")
    days = _safe_get(params, "days", 3)
    weather = _safe_get(params, "weather", {}) or {}
    budget = _safe_get(params, "budget", "中等")
    interests = _safe_get(params, "interests", ["文化", "美食"]) or ["文化", "美食"]

    # 天气分析
    weather_text = ""
    if weather and isinstance(weather, dict) and "forecast" in weather:
        forecast = weather["forecast"][:days] if len(weather["forecast"]) >= days else weather["forecast"]
        if forecast:
            weather_text = "\n\n天气预报："
            for day in forecast:
                date = day.get("date", "未知")
                max_temp = day.get("max_temp", 0)
                min_temp = day.get("min_temp", 0)
                weather_desc = day.get("weather", "未知")
                weather_text += f"\n  {date}：{min_temp}°C ~ {max_temp}°C，{weather_desc}"

    # 生成行程
    itinerary = _generate_itinerary(destination, days, interests)

    # RAG 上下文
    rag_section = _build_rag_section(rag_context)

    # API 数据展示（提高可信度）
    api_data = _safe_get(params, "_api_data", {})
    api_section = _build_api_data_section(api_data, "travel")

    return f"""
{destination} {days}日游计划

预算：{budget}
兴趣：{'、'.join(interests) if interests else '未知'}
{weather_text}

行程安排：
{itinerary}
{rag_section}
{api_section}
---
已生成旅行计划！您可以根据此计划在 PlanHub 中创建计划。
"""

# ─── 工作计划模板 ──────────────────────────────────────────────

def _generate_gantt(task: str, duration: str) -> str:
    """生成文本版甘特图"""
    # 简化版：假设 duration 是 "2周"
    weeks = 2
    gantt = ""
    for week in range(1, weeks + 1):
        gantt += f"\n  第{week}周："
        if week == 1:
            gantt += f"\n    [需求分析] ████████ 100%"
            gantt += f"\n    [设计阶段] ██████░░ 60%"
        else:
            gantt += f"\n    [开发阶段] ████████ 100%"
            gantt += f"\n    [测试阶段] ██████░░ 60%"
    return gantt

def generate_work_plan(params: Dict[str, Any], rag_context: Optional[str] = None) -> str:
    """生成工作计划模板

    params:
        - task: 任务名称（如 "项目开发"）
        - duration: 时长（如 "2周"）
        - holidays: 节假日信息
        - team_size: 团队人数
    """
    task = _safe_get(params, "task", "工作任务")
    duration = _safe_get(params, "duration", "1个月")
    holidays = _safe_get(params, "holidays", {}) or {}
    team_size = _safe_get(params, "team_size", 1)

    # 节假日分析
    holiday_text = ""
    if holidays and isinstance(holidays, dict) and "holidays" in holidays:
        holiday_list = holidays["holidays"]
        if holiday_list and len(holiday_list) > 0:
            holiday_text = "\n\n节假日安排："
            for h in holiday_list[:5]:  # 最多显示5个
                if isinstance(h, dict):
                    date = h.get("date", "未知")
                    name = h.get("name", "节假日")
                    holiday_text += f"\n  {date}：{name}"

    # 生成甘特图（文本版）
    gantt = _generate_gantt(task, duration)

    # RAG 上下文
    rag_section = _build_rag_section(rag_context)

    # API 数据展示（提高可信度）
    api_data = _safe_get(params, "_api_data", {})
    api_section = _build_api_data_section(api_data, "work")

    return f"""
工作计划（{duration}）

任务：{task}
团队规模：{team_size}人
{holiday_text}

甘特图：
{gantt}
{rag_section}
{api_section}
---
已生成工作计划！您可以根据此计划在 PlanHub 中创建计划。
"""

# ─── 财务计划模板 ──────────────────────────────────────────────

def generate_finance_plan(params: Dict[str, Any], rag_context: Optional[str] = None) -> str:
    """生成财务计划模板

    params:
        - goal: 财务目标（如 "存5万"）
        - duration: 时长（如 "1年"）
        - monthly_income: 月收入
        - rates: 汇率信息
    """
    goal = _safe_get(params, "goal", "存钱")
    duration = _safe_get(params, "duration", "1年")
    monthly_income = _safe_get(params, "monthly_income", 10000)
    rates = _safe_get(params, "rates", {}) or {}

    # 解析目标金额
    target_amount = _parse_amount(goal)

    # 计算月储蓄目标
    months = _parse_duration(duration) // 30
    monthly_savings = target_amount / months if months > 0 else 0

    # 计算储蓄率
    savings_rate = (monthly_savings / monthly_income * 100) if monthly_income > 0 else 0

    # 汇率信息
    rate_text = ""
    if rates and isinstance(rates, dict) and "rates" in rates:
        rates_data = rates["rates"]
        usd_rate = rates_data.get("USD", 1)
        eur_rate = rates_data.get("EUR", 1)
        jpy_rate = rates_data.get("JPY", 1)
        rate_text = f"\n\n汇率参考（仅供参考）：\n  1 CNY = {usd_rate:.4f} USD\n  1 CNY = {eur_rate:.4f} EUR\n  1 CNY = {jpy_rate:.2f} JPY"

    # RAG 上下文
    rag_section = _build_rag_section(rag_context)

    # API 数据展示（提高可信度）
    api_data = _safe_get(params, "_api_data", {})
    api_section = _build_api_data_section(api_data, "finance")

    return f"""
财务计划（{duration}）

目标：{goal}
目标金额：{target_amount:.0f}元
月收入：{monthly_income}元
月储蓄目标：{monthly_savings:.0f}元
储蓄率：{savings_rate:.1f}%

月度计划：
  第1-3月：基础存钱
    - 月存：{monthly_savings * 0.8:.0f}元
    - 重点：养成习惯，控制支出

  第4-6月：增加收入
    - 月存：{monthly_savings:.0f}元
    - 重点：副业或加班，增加收入来源

  第7-9月：稳定存钱
    - 月存：{monthly_savings * 1.1:.0f}元
    - 重点：保持节奏，避免大额支出

  第10-12月：冲刺目标
    - 月存：{monthly_savings * 1.2:.0f}元
    - 重点：完成目标，适当奖励自己
{rate_text}
{rag_section}
{api_section}
---
已生成财务计划！您可以根据此计划在 PlanHub 中创建计划。
"""

# ─── 导出所有模板函数 ──────────────────────────────────────────

__all__ = [
    "generate_learning_plan",
    "generate_health_plan",
    "generate_travel_plan",
    "generate_work_plan",
    "generate_finance_plan"
]
