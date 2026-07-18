"""
FastMCP Server — 将所有外部 API 封装为 MCP Tools

启动：
  python -m src.app.mcp.mcp_server

默认监听：http://127.0.0.1:8001/sse

MCP 客户端（agent）通过 SSE 协议连接，动态发现以下工具：

学习类：
  - search_books: 搜索 Open Library 书籍
  - search_ebooks: 搜索 Gutenberg 电子书
  - search_papers: 搜索 Crossref 学术文章
  - get_wikipedia: 搜索 Wikipedia 摘要

健康/生活类：
  - get_weather: 获取城市天气预报（Open-Meteo，免 Key）
  - get_nutrition: 查询食物营养成分
  - get_exercises: 查询健身动作
  - calculate_bmi: 计算 BMI

旅行/实用类：
  - get_exchange_rates: 获取汇率
  - get_world_time: 获取世界时间
  - get_holidays: 获取中国节假日
  - get_city_bikes: 查询城市共享单车
  - get_brewery: 查询城市精酿啤酒厂

娱乐类：
  - get_hitokoto: 获取一言
  - get_daily_poem: 获取今日古诗
  - get_quote: 获取名人名言
  - get_trivia: 获取趣味问答
  - get_bored_activity: 获取随机活动建议
"""

import sys
import os

# 项目根目录加入 path（从 src/app/mcp/mcp_server.py 向上4级）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastmcp import FastMCP

mcp = FastMCP("PlanHub API Tools")


# ─── 学习类工具 ────────────────────────────────────────────────────────

@mcp.tool()
def search_books(query: str, limit: int = 3) -> dict:
    """搜索 Open Library 获取书籍推荐。query: 书名或主题关键词，limit: 返回数量（默认3）"""
    from src.app.common.mcp_tools import search_open_library
    return search_open_library(query, limit)


@mcp.tool()
def search_ebooks(query: str, limit: int = 3) -> dict:
    """搜索 Gutenberg 公共领域电子书。query: 书名或主题关键词，limit: 返回数量"""
    from src.app.common.mcp_tools import search_gutendex
    return search_gutendex(query, limit)


@mcp.tool()
def search_papers(query: str, limit: int = 3) -> dict:
    """搜索 Crossref 学术文章/论文。query: 学术关键词，limit: 返回数量"""
    from src.app.common.mcp_tools import search_crossref
    return search_crossref(query, limit)


@mcp.tool()
def get_wikipedia(query: str, lang: str = "zh") -> dict:
    """搜索 Wikipedia 获取主题摘要。query: 词条名称，lang: 语言代码（zh/en）"""
    from src.app.common.mcp_tools import get_wikipedia_summary
    return get_wikipedia_summary(query, lang)


# ─── 健康/生活类工具 ──────────────────────────────────────────────────

@mcp.tool()
def get_weather(city: str, days: int = 7) -> dict:
    """获取城市天气预报（Open-Meteo，无需 API Key）。city: 城市英文名或中文（如 Beijing、Shanghai），days: 预报天数（默认7天）"""
    from src.app.common.mcp_tools import get_weather_forecast
    return get_weather_forecast(city, days)


@mcp.tool()
def get_nutrition(food: str) -> dict:
    """查询食物的营养成分信息。food: 食物名称（英文效果更好，如 rice、apple）"""
    from src.app.common.mcp_tools import get_food_nutrition
    return get_food_nutrition(food)


@mcp.tool()
def get_exercises(muscle: int = 0, category: int = 0, limit: int = 5) -> dict:
    """查询健身动作推荐。muscle: 肌肉部位ID（见 get_exercises_muscles），category: 器械类型ID，limit: 返回数量"""
    from src.app.common.mcp_tools import get_wger_exercises
    return get_wger_exercises(muscle if muscle else None, category if category else None, limit)


@mcp.tool()
def get_exercises_muscles() -> dict:
    """获取所有可用的肌肉部位ID列表，用于 get_exercises 的 muscle 参数"""
    from src.app.common.mcp_tools import get_wger_muscles
    return get_wger_muscles()


@mcp.tool()
def calculate_bmi(weight: str, height: str) -> dict:
    """计算 BMI 指数。weight: 体重（如 "70kg"），height: 身高（如 "175cm"）"""
    from src.app.common.mcp_tools import calculate_bmi
    return calculate_bmi(weight, height)


# ─── 旅行/实用类工具 ──────────────────────────────────────────────────

@mcp.tool()
def get_exchange_rates(base_currency: str = "CNY") -> dict:
    """获取实时汇率。base_currency: 基准货币（默认 CNY）"""
    from src.app.common.mcp_tools import get_exchange_rates
    return get_exchange_rates(base_currency)


@mcp.tool()
def get_world_time(timezone: str = "Asia/Shanghai") -> dict:
    """获取世界各时区当前时间。timezone: 时区名（如 Asia/Shanghai、America/New_York）"""
    from src.app.common.mcp_tools import get_world_time
    return get_world_time(timezone)


@mcp.tool()
def get_holidays(year: int = 2026, month: int = 7) -> dict:
    """获取中国节假日信息。year: 年份，month: 月份"""
    from src.app.common.mcp_tools import get_china_holidays
    return get_china_holidays(year, month)


@mcp.tool()
def get_city_bikes(city: str) -> dict:
    """查询城市共享单车实时数据。city: 城市英文名（如 Beijing、Shanghai）"""
    from src.app.common.mcp_tools import get_city_bikes
    return get_city_bikes(city)


@mcp.tool()
def get_brewery(city: str) -> dict:
    """查询城市的精酿啤酒厂。city: 城市英文名"""
    from src.app.common.mcp_tools import get_open_brewery
    return get_open_brewery(city)


@mcp.tool()
def get_ip_location(ip: str = "") -> dict:
    """查询 IP 地址的地理位置信息。ip: IP 地址（不传则查询本机）"""
    from src.app.common.mcp_tools import get_ip_location
    return get_ip_location(ip if ip else None)


# ─── 娱乐类工具 ────────────────────────────────────────────────────────

@mcp.tool()
def get_hitokoto(category: str = "") -> dict:
    """获取一言（随机句子）。category: 分类（a-动画 b-漫画 c-游戏 d-文学 e-原创 f-来自网络 g-其他 h-影视 i-诗词 j-网易云 k-哲学 l-抖机灵，不传则随机）"""
    from src.app.common.mcp_tools import get_hitokoto
    return get_hitokoto(category)


@mcp.tool()
def get_daily_poem() -> dict:
    """获取今日古诗推荐（今日诗词 API）"""
    from src.app.common.mcp_tools import get_jinrishici
    return get_jinrishici()


@mcp.tool()
def get_quote(category: str = "") -> dict:
    """获取名人名言。category: 分类（如 wisdom、inspirational，不传则随机）"""
    from src.app.common.mcp_tools import get_quotable_quote
    return get_quotable_quote(category if category else None)


@mcp.tool()
def get_trivia(category: int = 9, amount: int = 3) -> dict:
    """获取趣味问答题目。category: 类别ID（9-常识 10-娱乐 11-艺术 12-运动等，见 https://opentdb.com/api_config.php），amount: 题目数量"""
    from src.app.common.mcp_tools import get_open_trivia
    return get_open_trivia(category, amount)


@mcp.tool()
def get_bored_activity(activity_type: str = "") -> dict:
    """获取随机活动建议（解决无聊）。activity_type: 类型（education、recreational、social、diy、charity、cooking、relaxation、music、busywork，不传则随机）"""
    from src.app.common.mcp_tools import get_bored_activity
    return get_bored_activity(activity_type if activity_type else None)


@mcp.tool()
def get_random_meal(query: str = "", random: bool = False) -> dict:
    """搜索菜谱或获取随机菜品。query: 菜名关键词，random: 是否随机返回"""
    from src.app.common.mcp_tools import get_themealdb
    return get_themealdb(query, random)


# ─── 启动入口 ──────────────────────────────────────────────────────────

def create_mcp_server() -> FastMCP:
    """创建并返回 FastMCP 实例（用于挂载到 FastAPI app）"""
    return mcp


def run_standalone(host: str = "127.0.0.1", port: int = 8001):
    """独立运行 MCP server（SSE 协议）"""
    print(f"[MCP] Starting PlanHub API Tools server on http://{host}:{port}/sse")
    mcp.run(host=host, port=port, transport="sse")


if __name__ == "__main__":
    run_standalone()
