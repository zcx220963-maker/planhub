"""
外部 API 工具模块

提供各种免费外部 API 的调用功能，可在智能助手的 tool calling 中使用。
"""

import requests
import json
from config import settings
from typing import Optional, Dict, Any


# ─── 天气 API ───────────────────────────────────────────────

def get_weather(city: str) -> Dict[str, Any]:
    """
    获取指定城市的天气信息
    
    参数：
    - city: 城市名称（如 "Beijing", "Shanghai"）
    
    返回：
    - 天气信息字典
    """
    api_key = settings.OPENWEATHERMAP_API_KEY
    if not api_key:
        return {
            "error": "OpenWeatherMap API Key 未配置",
            "message": "请在 config.py 中配置 OPENWEATHERMAP_API_KEY"
        }
    
    try:
        url = f"{settings.OPENWEATHERMAP_BASE_URL}/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",  # 摄氏度
            "lang": "zh_cn"     # 中文
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            return {
                "city": data.get("name"),
                "temperature": data["main"].get("temp"),
                "feels_like": data["main"].get("feels_like"),
                "humidity": data["main"].get("humidity"),
                "description": data["weather"][0].get("description"),
                "wind_speed": data["wind"].get("speed"),
                "icon": data["weather"][0].get("icon")
            }
        else:
            return {"error": data.get("message", "获取天气失败")}
    except Exception as e:
        return {"error": str(e)}


# ─── 新闻 API ───────────────────────────────────────────────

def get_news(country: str = "cn", category: str = "general") -> Dict[str, Any]:
    """
    获取新闻资讯
    
    参数：
    - country: 国家代码（如 "cn", "us", "jp"）
    - category: 新闻类别（business, entertainment, general, health, science, sports, technology）
    
    返回：
    - 新闻列表
    """
    api_key = settings.NEWSAPI_API_KEY
    if not api_key:
        return {
            "error": "NewsAPI API Key 未配置",
            "message": "请在 config.py 中配置 NEWSAPI_API_KEY"
        }
    
    try:
        url = f"{settings.NEWSAPI_BASE_URL}/top-headlines"
        params = {
            "country": country,
            "category": category,
            "apiKey": api_key,
            "pageSize": 5
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title"),
                    "source": article["source"].get("name"),
                    "url": article.get("url"),
                    "publishedAt": article.get("publishedAt"),
                    "description": article.get("description")
                })
            return {"articles": articles}
        else:
            return {"error": data.get("message", "获取新闻失败")}
    except Exception as e:
        return {"error": str(e)}


# ─── 汇率 API ───────────────────────────────────────────────

def get_exchange_rates(base_currency: str = "CNY") -> Dict[str, Any]:
    """
    获取货币汇率
    
    参数：
    - base_currency: 基准货币代码（如 "CNY", "USD", "EUR"）
    
    返回：
    - 汇率信息
    """
    try:
        url = f"{settings.EXCHANGERATE_API_URL}/{settings.EXCHANGERATE_API_KEY}/{base_currency}"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            return {
                "base": data.get("base_code"),
                "rates": data.get("conversion_rates", {}),
                "updated_at": data.get("time_last_update_utc")
            }
        else:
            return {"error": data.get("error-type", "获取汇率失败")}
    except Exception as e:
        return {"error": str(e)}


# ─── IP 查询 API ───────────────────────────────────────────

def get_ip_info(ip: Optional[str] = None) -> Dict[str, Any]:
    """
    获取 IP 地址的地理位置信息
    
    参数：
    - ip: IP 地址（可选，不传则查询请求者的 IP）
    
    返回：
    - IP 地理位置信息
    """
    try:
        url = f"{settings.IP_API_URL}/{ip or ''}"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get("status") == "success":
            return {
                "ip": data.get("query"),
                "country": data.get("country"),
                "countryCode": data.get("countryCode"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "zip": data.get("zip"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "timezone": data.get("timezone"),
                "isp": data.get("isp")
            }
        else:
            return {"error": data.get("message", "查询失败")}
    except Exception as e:
        return {"error": str(e)}


# ─── 时间 API ───────────────────────────────────────────────

def get_time(timezone: Optional[str] = None) -> Dict[str, Any]:
    """
    获取指定时区的当前时间
    
    参数：
    - timezone: 时区（如 "Asia/Shanghai", "America/New_York"）
    
    返回：
    - 当前时间信息
    """
    try:
        if timezone:
            url = f"{settings.WORLD_TIME_API_URL}/timezone/{timezone}"
        else:
            # 获取请求者所在时区的时间
            url = f"{settings.WORLD_TIME_API_URL}/ip"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            return {
                "datetime": data.get("datetime"),
                "date": data.get("date"),
                "time": data.get("time"),
                "timezone": data.get("timezone"),
                "day_of_week": data.get("day_of_week"),
                "day_of_year": data.get("day_of_year"),
                "week_number": data.get("week_number"),
                "utc_offset": data.get("utc_offset")
            }
        else:
            return {"error": data.get("error", "获取时间失败")}
    except Exception as e:
        return {"error": str(e)}


# ─── 笑话 API ───────────────────────────────────────────────

def get_joke(category: str = "Any") -> Dict[str, Any]:
    """
    获取随机笑话
    
    参数：
    - category: 笑话类别（Any, Programming, Miscellaneous, Dark, Pun, Spooky, Christmas）
    
    返回：
    - 笑话内容
    """
    try:
        url = f"{settings.JOKE_API_URL}/{category}"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("error") == False:
            if data.get("type") == "single":
                return {
                    "type": "single",
                    "joke": data.get("joke"),
                    "category": data.get("category")
                }
            else:
                return {
                    "type": "twopart",
                    "setup": data.get("setup"),
                    "delivery": data.get("delivery"),
                    "category": data.get("category")
                }
        else:
            return {"error": data.get("message", "获取笑话失败")}
    except Exception as e:
        return {"error": str(e)}


# ─── 工具描述（用于 LangChain Tool Calling）──────────────────

def get_external_tool_descriptions():
    """
    获取外部工具的描述列表，用于 LangChain Tool Calling
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取指定城市的天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称，如 Beijing, Shanghai, Tokyo"
                        }
                    },
                    "required": ["city"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_news",
                "description": "获取最新新闻资讯",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "country": {
                            "type": "string",
                            "description": "国家代码，如 cn, us, jp"
                        },
                        "category": {
                            "type": "string",
                            "description": "新闻类别：business, entertainment, general, health, science, sports, technology"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_exchange_rates",
                "description": "获取货币汇率信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "base_currency": {
                            "type": "string",
                            "description": "基准货币代码，如 CNY, USD, EUR"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_ip_info",
                "description": "获取 IP 地址的地理位置信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ip": {
                            "type": "string",
                            "description": "IP 地址，不传则查询请求者的 IP"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "获取指定时区的当前时间",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "时区，如 Asia/Shanghai, America/New_York"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_joke",
                "description": "获取随机笑话",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "笑话类别：Any, Programming, Miscellaneous, Dark, Pun, Spooky, Christmas"
                        }
                    },
                    "required": []
                }
            }
        }
    ]
    return tools
