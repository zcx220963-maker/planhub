"""
外部 API 工具模块 - 合并所有外部 API

包含：
1. 需要 API Key 的服务（天气、新闻）
2. 免费无需 Key 的服务（学习、健康、旅行、工作、财务、通用）

所有 API 均通过 Tool Calling 调用，统一返回格式。
"""

import requests
import json
import re
from typing import Optional, Dict, Any, List
from functools import lru_cache
from datetime import datetime
from urllib.parse import quote
from config import settings


# ─── 需要 API Key 的服务 ─────────────────────────────────────────


def get_weather(city: str) -> Dict[str, Any]:
    """获取指定城市的天气信息（OpenWeatherMap，需 API Key）"""
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
            "units": "metric",
            "lang": "zh_cn"
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


def get_news(country: str = "cn", category: str = "general") -> Dict[str, Any]:
    """获取新闻资讯（NewsAPI，需 API Key）"""
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


# ─── 学习计划 API（免费）────────────────────────────────────────


def search_open_library(query: str, limit: int = 3) -> Dict[str, Any]:
    """搜索 Open Library 获取书籍推荐（免费，无需 Key）"""
    try:
        url = "https://openlibrary.org/search.json"
        params = {"q": query, "limit": limit}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            books = []
            for doc in data.get("docs", [])[:limit]:
                books.append({
                    "title": doc.get("title", "未知书名"),
                    "author": doc.get("author_name", ["未知"])[0] if doc.get("author_name") else "未知",
                    "year": doc.get("first_publish_year", "未知"),
                    "url": f"https://openlibrary.org{doc.get('key', '')}"
                })
            return {"books": books, "total": data.get("numFound", 0)}
        return {"error": "获取书籍失败", "books": [], "total": 0}
    except Exception as e:
        return {"error": f"获取书籍失败: {str(e)}", "books": [], "total": 0}


def search_gutendex(query: str, limit: int = 3) -> Dict[str, Any]:
    """搜索 Gutenberg 电子书（免费，无需 Key）"""
    try:
        url = "https://gutendex.com/"
        params = {"search": query, "languages": "zh,en"}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            books = []
            for book in data.get("results", [])[:limit]:
                books.append({
                    "title": book.get("title", "未知书名"),
                    "author": book.get("authors", [{}])[0].get("name", "未知") if book.get("authors") else "未知",
                    "formats": list(book.get("formats", {}).keys())
                })
            return {"books": books, "count": data.get("count", 0)}
        return {"error": "获取电子书失败", "books": [], "count": 0}
    except Exception as e:
        return {"error": f"获取电子书失败: {str(e)}", "books": [], "count": 0}


def search_crossref(query: str, limit: int = 3) -> Dict[str, Any]:
    """搜索 Crossref 学术文章（免费，无需 Key）"""
    try:
        url = "https://api.crossref.org/works"
        params = {"query": query, "rows": limit}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            articles = []
            for item in data.get("message", {}).get("items", [])[:limit]:
                articles.append({
                    "title": item.get("title", ["未知标题"])[0] if item.get("title") else "未知标题",
                    "authors": [a.get("name", "未知") for a in (item.get("author", []) or [])[:3]],
                    "year": item.get("published-print", {}).get("date-parts", [[0]])[0][0] if item.get("published-print") else "未知",
                    "doi": item.get("DOI", ""),
                    "url": item.get("URL", "")
                })
            return {"articles": articles, "total": data.get("message", {}).get("total-results", 0)}
        return {"error": "获取学术文章失败", "articles": [], "total": 0}
    except Exception as e:
        return {"error": f"获取学术文章失败: {str(e)}", "articles": [], "total": 0}


def search_poetrydb(query: str, limit: int = 3) -> Dict[str, Any]:
    """搜索 PoetryDB 诗歌（免费，无需 Key）"""
    try:
        url = "https://poetrydb.org/title/search"
        params = {"title": query}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            poems = []
            for poem in data[:limit]:
                poems.append({
                    "title": poem.get("title", "未知标题"),
                    "author": poem.get("author", "未知作者"),
                    "lines": poem.get("lines", [])[:5],
                    "linecount": poem.get("linecount", 0)
                })
            return {"poems": poems, "count": len(data)}
        return {"error": "获取诗歌失败", "poems": [], "count": 0}
    except Exception as e:
        return {"error": f"获取诗歌失败: {str(e)}", "poems": [], "count": 0}


def search_quran(query: str, limit: int = 3) -> Dict[str, Any]:
    """搜索 Quran Cloud 宗教文本（免费，无需 Key）"""
    try:
        url = "https://api.alquran.cloud/v1/search"
        params = {"q": query, "size": limit}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            verses = []
            for verse in data.get("data", {}).get("matches", [])[:limit]:
                verses.append({
                    "text": verse.get("text", ""),
                    "surah": verse.get("surah", {}).get("name", "未知"),
                    "number": verse.get("number", 0),
                    "translation": verse.get("translation", "")
                })
            return {"verses": verses, "count": data.get("data", {}).get("count", 0)}
        return {"error": "获取宗教文本失败", "verses": [], "count": 0}
    except Exception as e:
        return {"error": f"获取宗教文本失败: {str(e)}", "verses": [], "count": 0}


def get_jinrishici() -> Dict[str, Any]:
    """获取今日诗词推荐（免费，无需 Key）- jinrishici.com"""
    try:
        url = "https://v2.jinrishici.com/one.json"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 PlanHubAI/1.0"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            content = data.get("data", {})
            origin = content.get("origin", {})
            return {
                "content": content.get("content", ""),
                "title": origin.get("title", "未知"),
                "author": origin.get("author", "未知"),
                "dynasty": origin.get("dynasty", ""),
                "category": data.get("category", ""),
                "source": "今日诗词 (jinrishici.com)"
            }
        return {"error": "获取诗词失败", "source": "今日诗词"}
    except Exception as e:
        return {"error": f"获取诗词失败: {str(e)}", "source": "今日诗词"}


def get_hitokoto(category: str = "") -> Dict[str, Any]:
    """获取一言随机名句（免费，无需 Key）- hitokoto.cn"""
    try:
        url = "https://v1.hitokoto.cn"
        params = {}
        if category:
            params["c"] = category
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "content": data.get("hitokoto", ""),
                "author": data.get("from_who", "未知"),
                "source_name": data.get("from", "未知"),
                "category": data.get("type", ""),
                "uuid": data.get("uuid", ""),
                "source": "一言 (hitokoto.cn)"
            }
        return {"error": "获取名句失败", "source": "一言"}
    except Exception as e:
        return {"error": f"获取名句失败: {str(e)}", "source": "一言"}


def get_wikipedia_summary(query: str, lang: str = "zh") -> Dict[str, Any]:
    """获取维基百科词条摘要（免费，无需 Key）"""
    try:
        encoded_query = quote(query, safe="")
        wiki_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
        headers = {
            "User-Agent": "PlanHubAI/1.0 (https://github.com/planhub)"
        }
        response = requests.get(wiki_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "extract": data.get("extract", ""),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "thumbnail": data.get("thumbnail", {}).get("source", ""),
                "lang": lang
            }
        elif response.status_code == 404:
            if lang == "zh":
                return get_wikipedia_summary(query, lang="en")
            return {"error": f"未找到词条: {query}"}
        return {"error": f"获取百科失败（HTTP {response.status_code}）"}
    except Exception as e:
        return {"error": f"获取维基百科失败: {str(e)}"}


def get_quotable_quote(category: Optional[str] = None) -> Dict[str, Any]:
    """获取随机英文名人名言（免费，无需 Key）- Quotable"""
    try:
        url = "https://api.quotable.io/random"
        params = {}
        if category:
            params["tags"] = category
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "content": data.get("content", ""),
                "author": data.get("author", ""),
                "tags": data.get("tags", []),
                "length": data.get("length", 0),
                "id": data.get("_id", "")
            }
        return {"error": "获取名言失败"}
    except Exception as e:
        return {"error": f"获取名言失败: {str(e)}"}


# ─── 健康计划 API（免费）────────────────────────────────────────


def _parse_weather_code(code: int) -> str:
    """解析天气代码"""
    weather_map = {
        0: "晴", 1: "大部晴", 2: "多云", 3: "阴天",
        45: "雾", 48: "雾凇", 51: "小毛毛雨", 53: "毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨", 71: "小雪",
        73: "中雪", 75: "大雪", 77: "雪粒", 80: "小阵雨",
        81: "中阵雨", 82: "大阵雨", 85: "小阵雪", 86: "大阵雪",
        95: "雷阵雨", 96: "雷阵雨", 99: "雷阵雨"
    }
    return weather_map.get(code, "未知")


def get_weather_forecast(city: str, days: int = 7) -> Dict[str, Any]:
    """获取天气预报（免费，无需 Key）- Open-Meteo"""
    try:
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": city, "count": 1, "language": "zh"}
        geo_response = requests.get(geo_url, params=geo_params, timeout=15)

        if geo_response.status_code != 200:
            return {"error": f"城市定位失败（HTTP {geo_response.status_code}）", "forecast": []}

        geo_data = geo_response.json().get("results", [])
        if not geo_data:
            geo_params["language"] = "en"
            geo_response = requests.get(geo_url, params=geo_params, timeout=15)
            if geo_response.status_code == 200:
                geo_data = geo_response.json().get("results", [])

        if not geo_data:
            return {"error": f"未找到城市 '{city}' 的坐标", "forecast": []}

        lat = geo_data[0].get("latitude")
        lon = geo_data[0].get("longitude")
        city_name = geo_data[0].get("name", city)

        if not lat or not lon:
            return {"error": "无法获取城市坐标", "forecast": []}

        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,weathercode",
            "timezone": "Asia/Shanghai",
            "forecast_days": days
        }
        weather_response = requests.get(weather_url, params=weather_params, timeout=15)

        if weather_response.status_code == 200:
            data = weather_response.json()
            daily = data.get("daily", {})
            forecast = []
            for i in range(len(daily.get("time", []))):
                forecast.append({
                    "date": daily["time"][i],
                    "max_temp": daily["temperature_2m_max"][i],
                    "min_temp": daily["temperature_2m_min"][i],
                    "weather": _parse_weather_code(daily["weathercode"][i])
                })
            return {"city": city_name, "forecast": forecast}
        return {"error": "获取天气失败", "forecast": []}
    except Exception as e:
        return {"error": f"获取天气失败: {str(e)}", "forecast": []}


def get_food_nutrition(food: str) -> Dict[str, Any]:
    """获取食物营养数据（免费，无需 Key）- Open Food Facts"""
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": food,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 10,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 PlanHubAI/1.0"
        }
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            products = data.get("products", [])
            for product in products:
                name = product.get("product_name", "")
                if name and len(name) < 60:
                    nutriments = product.get("nutriments", {})
                    cal = nutriments.get("energy-kcal_100g", 0)
                    if cal and cal > 0:
                        return {
                            "name": name,
                            "calories": cal,
                            "fat": nutriments.get("fat_100g", 0),
                            "carbs": nutriments.get("carbohydrates_100g", 0),
                            "protein": nutriments.get("proteins_100g", 0),
                            "salt": nutriments.get("salt_100g", 0),
                            "sugar": nutriments.get("sugars_100g", 0),
                        }
            return {"error": f"未在营养库中找到「{food}」的数据"}
        return {"error": f"Open Food Facts 服务异常（{response.status_code}），请稍后再试"}
    except Exception as e:
        return {"error": f"获取食物营养失败: {str(e)}"}


def get_fruit_nutrition(fruit: str) -> Dict[str, Any]:
    """获取水果营养数据（免费，无需 Key）"""
    try:
        url = f"https://www.fruityvice.com/api/fruit/{fruit}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "name": data.get("name", fruit),
                "calories": data.get("nutritions", {}).get("calories", 0),
                "sugar": data.get("nutritions", {}).get("sugar", 0),
                "fat": data.get("nutritions", {}).get("fat", 0),
                "protein": data.get("nutritions", {}).get("protein", 0),
                "carbohydrates": data.get("nutritions", {}).get("carbohydrates", 0)
            }
        return {"error": "获取水果营养失败"}
    except Exception as e:
        return {"error": f"获取水果营养失败: {str(e)}"}


def get_themealdb(query: str = "", random: bool = False) -> Dict[str, Any]:
    """获取食谱信息（免费，测试 Key）- TheMealDB"""
    try:
        api_key = "1"
        if not query and not random:
            return {"error": "请提供搜索关键词或启用随机", "meals": [], "source": "TheMealDB"}
        if random:
            url = f"https://www.themealdb.com/api/json/v1/{api_key}/random.php"
        else:
            url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php"
        
        params = {}
        if not random and query:
            params["s"] = query
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            meals = data.get("meals", [])
            if isinstance(meals, str):
                return {"error": meals, "meals": [], "source": "TheMealDB"}
            if meals:
                result_meals = []
                for meal in meals[:3]:
                    ingredients = []
                    for i in range(1, 21):
                        ing = meal.get(f"strIngredient{i}")
                        measure = meal.get(f"strMeasure{i}")
                        if ing and ing.strip():
                            ingredients.append(f"{ing.strip()} ({measure.strip() if measure else '适量'})")
                    
                    result_meals.append({
                        "name": meal.get("strMeal", "未知"),
                        "category": meal.get("strCategory", ""),
                        "area": meal.get("strArea", ""),
                        "instructions": meal.get("strInstructions", "")[:500] if meal.get("strInstructions") else "",
                        "ingredients": ingredients[:10],
                        "image": meal.get("strMealThumb", ""),
                        "youtube": meal.get("strYoutube", ""),
                        "source": meal.get("strSource", ""),
                    })
                return {"meals": result_meals, "count": len(result_meals), "source": "TheMealDB (themealdb.com)"}
            return {"error": "未找到相关食谱", "meals": [], "source": "TheMealDB"}
        return {"error": "获取食谱失败", "meals": [], "source": "TheMealDB"}
    except Exception as e:
        return {"error": f"获取食谱失败: {str(e)}", "meals": [], "source": "TheMealDB"}


def get_wger_exercises(muscle: int = None, category: int = None, limit: int = 5) -> Dict[str, Any]:
    """获取运动动作库（免费，无需认证）- wger.de"""
    try:
        url = "https://wger.de/api/v2/exerciseinfo/"
        params = {"language": 2, "limit": limit}
        
        if muscle:
            params["muscles"] = muscle
        if category:
            params["category"] = category
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            exercises = []
            for ex in data.get("results", []):
                name = "未知"
                desc = ""
                for t in ex.get("translations", []):
                    if t.get("language") == 2:
                        name = t.get("name", "未知")
                        desc = t.get("description", "")[:200] if t.get("description") else ""
                        break
                if name == "未知" and ex.get("translations"):
                    name = ex["translations"][0].get("name", "未知")

                cat_name = ""
                if ex.get("category") and isinstance(ex["category"], dict):
                    cat_name = ex["category"].get("name", "")

                exercises.append({
                    "name": name,
                    "description": desc,
                    "category": cat_name,
                    "muscles": [m.get("name", "") for m in ex.get("muscles", [])[:2]],
                    "id": ex.get("id", ""),
                })
            return {
                "exercises": exercises,
                "count": len(exercises),
                "total": data.get("count", 0),
                "source": "wger 运动库 (wger.de)"
            }
        return {"error": "获取运动动作失败", "exercises": [], "source": "wger"}
    except Exception as e:
        return {"error": f"获取运动动作失败: {str(e)}", "exercises": [], "source": "wger"}


def get_wger_muscles() -> Dict[str, Any]:
    """获取肌肉群信息（免费，无需认证）- wger.de"""
    try:
        url = "https://wger.de/api/v2/muscle/"
        params = {"limit": 20}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            muscles = []
            for m in data.get("results", []):
                muscles.append({
                    "id": m.get("id"),
                    "name": m.get("name", ""),
                    "name_en": m.get("name_en", ""),
                    "is_front": m.get("is_front", False),
                })
            return {"muscles": muscles, "count": len(muscles), "source": "wger 肌肉群 (wger.de)"}
        return {"error": "获取肌肉群失败", "muscles": [], "source": "wger"}
    except Exception as e:
        return {"error": f"获取肌肉群失败: {str(e)}", "muscles": [], "source": "wger"}


def get_amap_weather(city: str = "北京") -> Dict[str, Any]:
    """获取高德天气（需要 API Key）- 高德地图"""
    try:
        import os
        api_key = os.environ.get("AMAP_API_KEY", "")
        if not api_key:
            return {"error": "未配置高德 API Key，请设置环境变量 AMAP_API_KEY", "source": "高德天气"}
        
        geo_url = "https://restapi.amap.com/v3/config/district"
        geo_params = {"key": api_key, "keywords": city, "subdistrict": 0}
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        
        if geo_resp.status_code == 200:
            geo_data = geo_resp.json()
            districts = geo_data.get("districts", [])
            if districts:
                adcode = districts[0].get("adcode", "")
                
                weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
                weather_params = {"key": api_key, "city": adcode, "extensions": "all"}
                weather_resp = requests.get(weather_url, params=weather_params, timeout=10)
                
                if weather_resp.status_code == 200:
                    weather_data = weather_resp.json()
                    forecasts = weather_data.get("forecasts", [])
                    if forecasts:
                        casts = forecasts[0].get("casts", [])
                        weather_list = []
                        for cast in casts[:7]:
                            weather_list.append({
                                "date": cast.get("date", ""),
                                "week": cast.get("week", ""),
                                "day_weather": cast.get("dayWeather", ""),
                                "night_weather": cast.get("nightWeather", ""),
                                "day_temp": cast.get("dayTemp", ""),
                                "night_temp": cast.get("nightTemp", ""),
                                "day_wind": cast.get("dayWind", ""),
                                "night_wind": cast.get("nightWind", ""),
                            })
                        return {
                            "city": forecasts[0].get("city", city),
                            "weather": weather_list,
                            "source": "高德天气 (amap.com)"
                        }
        
        return {"error": "获取天气失败", "source": "高德天气"}
    except Exception as e:
        return {"error": f"获取天气失败: {str(e)}", "source": "高德天气"}


# ─── 旅行计划 API（免费）────────────────────────────────────────


def get_exchange_rates(base_currency: str = "CNY") -> Dict[str, Any]:
    """获取汇率（免费，无需 Key）"""
    try:
        url = f"https://v6.exchangerate-api.com/v6/latest/{base_currency}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("result") == "success":
                return {
                    "base": data.get("base_code", base_currency),
                    "rates": data.get("conversion_rates", {}),
                    "updated": data.get("time_last_update_utc", "")
                }
            return {"error": data.get("error-type", "获取汇率失败")}
        return {"error": "获取汇率失败"}
    except Exception as e:
        return {"error": f"获取汇率失败: {str(e)}"}


def get_ip_location(ip: Optional[str] = None) -> Dict[str, Any]:
    """获取 IP 地理位置（免费，无需 Key）"""
    try:
        url = f"http://ip-api.com/json/{ip or ''}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return {
                    "ip": data.get("query", ""),
                    "country": data.get("country", "未知"),
                    "region": data.get("regionName", "未知"),
                    "city": data.get("city", "未知"),
                    "timezone": data.get("timezone", "未知"),
                    "lat": data.get("lat", 0),
                    "lon": data.get("lon", 0)
                }
            return {"error": data.get("message", "获取位置失败")}
        return {"error": "获取位置失败"}
    except Exception as e:
        return {"error": f"获取位置失败: {str(e)}"}


def get_city_bikes(city: str) -> Dict[str, Any]:
    """获取城市共享单车信息（免费，无需 Key）"""
    try:
        url = "https://api.citybik.es/v2/networks"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            networks = data.get("networks", [])
            matching = [n for n in networks if city.lower() in n.get("location", {}).get("city", "").lower()]
            if matching:
                network = matching[0]
                return {
                    "name": network.get("name", "未知"),
                    "city": network.get("location", {}).get("city", city),
                    "country": network.get("location", {}).get("country", "未知"),
                    "stations": len(network.get("stations", [])),
                    "free_bikes": sum(s.get("free_bikes", 0) for s in network.get("stations", [])[:10]),
                    "empty_slots": sum(s.get("empty_slots", 0) for s in network.get("stations", [])[:10])
                }
            return {"error": f"未找到 {city} 的共享单车信息"}
        return {"error": "获取共享单车信息失败"}
    except Exception as e:
        return {"error": f"获取共享单车信息失败: {str(e)}"}


def get_open_brewery(city: str) -> Dict[str, Any]:
    """获取城市精酿啤酒厂信息（免费，无需 Key）"""
    try:
        url = "https://api.openbrewerydb.org/breweries"
        params = {"by_city": city, "per_page": 5}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            breweries = []
            for brewery in data:
                breweries.append({
                    "name": brewery.get("name", "未知"),
                    "type": brewery.get("brewery_type", "未知"),
                    "address": brewery.get("street", "未知"),
                    "city": brewery.get("city", city),
                    "website": brewery.get("website_url", "")
                })
            return {"breweries": breweries, "count": len(data)}
        return {"error": "获取精酿啤酒厂信息失败"}
    except Exception as e:
        return {"error": f"获取精酿啤酒厂信息失败: {str(e)}"}


# ─── 工作计划 API（免费）────────────────────────────────────────


@lru_cache(maxsize=12)
def get_china_holidays(year: int, month: int) -> Dict[str, Any]:
    """获取中国节假日（免费，无需 Key）"""
    try:
        url = f"https://timor.tech/api/holiday/info/{year}-{month:02d}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            holidays = []
            if isinstance(data, dict) and "holidays" in data:
                for h in data.get("holidays", []):
                    holidays.append({
                        "date": h.get("date", "未知"),
                        "name": h.get("name", "节假日"),
                        "type": h.get("type", {}).get("name", "未知") if isinstance(h.get("type"), dict) else "未知"
                    })
            elif isinstance(data, dict) and "type" in data:
                holidays.append({
                    "date": f"{year}-{month:02d}-01",
                    "name": data.get("name", "未知"),
                    "type": data.get("type", {}).get("name", "未知") if isinstance(data.get("type"), dict) else "未知"
                })
            return {"holidays": holidays, "year": year, "month": month}
        return {"error": "获取节假日失败", "holidays": [], "year": year, "month": month}
    except Exception as e:
        return {"error": f"获取节假日失败: {str(e)}", "holidays": [], "year": year, "month": month}


def get_world_time(timezone: str = "Asia/Shanghai") -> Dict[str, Any]:
    """获取世界时间（免费，无需 Key）"""
    try:
        url = f"http://worldtimeapi.org/api/timezone/{timezone}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "timezone": data.get("timezone", timezone),
                "datetime": data.get("datetime", ""),
                "utc_datetime": data.get("utc_datetime", ""),
                "day_of_week": data.get("day_of_week", 0),
                "day_of_year": data.get("day_of_year", 0)
            }
        return {"error": "获取时间失败"}
    except Exception as e:
        return {"error": f"获取时间失败: {str(e)}"}


def get_json_placeholder(resource: str = "todos", limit: int = 5) -> Dict[str, Any]:
    """获取模拟任务数据（免费，无需 Key）"""
    try:
        url = f"https://jsonplaceholder.typicode.com/{resource}"
        params = {"_limit": limit}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {"data": data, "count": len(data)}
        return {"error": "获取模拟数据失败"}
    except Exception as e:
        return {"error": f"获取模拟数据失败: {str(e)}"}


def get_random_data(type: str = "address", size: int = 5) -> Dict[str, Any]:
    """获取随机数据（免费，无需 Key）"""
    try:
        url = f"https://random-data-api.com/api/{type}/random"
        params = {"size": size}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {"data": data, "count": len(data)}
        return {"error": "获取随机数据失败"}
    except Exception as e:
        return {"error": f"获取随机数据失败: {str(e)}"}


def get_open_trivia(category: int = 9, amount: int = 3) -> Dict[str, Any]:
    """获取知识问答（免费，无需 Key）"""
    try:
        url = "https://opentdb.com/api.php"
        params = {"amount": amount, "category": category, "type": "multiple"}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("response_code") == 0:
                questions = []
                for q in data.get("results", []):
                    questions.append({
                        "question": q.get("question", ""),
                        "correct_answer": q.get("correct_answer", ""),
                        "incorrect_answers": q.get("incorrect_answers", []),
                        "difficulty": q.get("difficulty", "medium")
                    })
                return {"questions": questions, "count": len(questions)}
            return {"error": "获取问答失败"}
        return {"error": "获取问答失败"}
    except Exception as e:
        return {"error": f"获取问答失败: {str(e)}"}


# ─── 财务计划 API（免费）────────────────────────────────────────


def get_economic_data(country: str = "CN", indicator: str = "GDP") -> Dict[str, Any]:
    """获取全球经济数据（免费，无需 Key）"""
    try:
        url = f"https://www.econdb.com/api/series/?ticker={indicator}&country={country}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {"data": data, "country": country, "indicator": indicator}
        return {"error": "获取经济数据失败"}
    except Exception as e:
        return {"error": f"获取经济数据失败: {str(e)}"}


def get_sec_edgar(company: str = "AAPL") -> Dict[str, Any]:
    """获取上市公司财报（免费，无需 Key，需 User-Agent）"""
    try:
        headers = {
            "User-Agent": "PlanHub AI Service (contact@example.com)"
        }
        url = f"https://data.sec.gov/submissions/CIK{company}.json"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "cik": data.get("cik", ""),
                "name": data.get("name", company),
                "filings": data.get("filings", {}).get("recent", {}),
                "sic": data.get("sic", ""),
                "stateOfIncorporation": data.get("stateOfIncorporation", "")
            }
        return {"error": "获取财报失败", "company": company, "note": "SEC EDGAR 需要 CIK 编号"}
    except Exception as e:
        return {"error": f"获取财报失败: {str(e)}", "company": company}


def get_portfolio_optimizer(risk_level: str = "medium") -> Dict[str, Any]:
    """获取投资组合建议（免费，无需 Key）"""
    portfolios = {
        "low": {
            "stocks": 20,
            "bonds": 60,
            "cash": 20,
            "expected_return": "3-5%",
            "risk": "低"
        },
        "medium": {
            "stocks": 50,
            "bonds": 40,
            "cash": 10,
            "expected_return": "5-8%",
            "risk": "中"
        },
        "high": {
            "stocks": 80,
            "bonds": 15,
            "cash": 5,
            "expected_return": "8-12%",
            "risk": "高"
        }
    }
    return portfolios.get(risk_level, portfolios["medium"])


def get_ibanforge(iban: str) -> Dict[str, Any]:
    """验证 IBAN（免费，无需 Key）"""
    try:
        iban = iban.replace(" ", "").upper()
        if len(iban) < 15 or len(iban) > 34:
            return {"valid": False, "reason": "IBAN 长度无效"}
        if not iban[:2].isalpha():
            return {"valid": False, "reason": "IBAN 国家代码无效"}
        if not iban[2:4].isdigit():
            return {"valid": False, "reason": "IBAN 校验位无效"}
        return {
            "valid": True,
            "iban": iban,
            "country": iban[:2],
            "check_digits": iban[2:4],
            "note": "基本验证通过，完整验证需要调用外部 API"
        }
    except Exception as e:
        return {"valid": False, "reason": f"IBAN 验证失败: {str(e)}"}


# ─── 通用与趣味工具 API（免费）────────────────────────────────────────


def get_bored_activity(activity_type: Optional[str] = None) -> Dict[str, Any]:
    """获取随机休闲活动推荐（免费，无需 Key）- Bored API"""
    try:
        url = "https://www.boredapi.com/api/activity"
        params = {}
        if activity_type:
            params["type"] = activity_type
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "activity" in data:
                return {
                    "activity": data.get("activity", ""),
                    "type": data.get("type", ""),
                    "participants": data.get("participants", 1),
                    "price": data.get("price", 0),
                    "link": data.get("link", ""),
                    "accessibility": data.get("accessibility", 0)
                }
            return {"error": "未获取到活动建议"}
        return {"error": "获取休闲活动失败"}
    except Exception as e:
        return {"error": f"获取休闲活动失败: {str(e)}"}


def get_agify_prediction(name: str) -> Dict[str, Any]:
    """根据名字预测年龄（免费，无需 Key）- Agify"""
    try:
        url = "https://api.agify.io"
        params = {"name": name}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("age"):
                return {
                    "name": data.get("name", name),
                    "age": data.get("age", 0),
                    "count": data.get("count", 0),
                    "country_id": data.get("country_id", "")
                }
            return {"error": f"无法预测名字 '{name}' 的年龄"}
        return {"error": "获取年龄预测失败"}
    except Exception as e:
        return {"error": f"获取年龄预测失败: {str(e)}"}


def calculate_bmi(weight: str, height: str) -> Dict[str, Any]:
    """计算BMI（身体质量指数）"""
    try:
        weight = str(weight).strip().lower()
        weight_kg = 0.0

        w_match = re.match(r'([\d.]+)\s*(kg|公斤|斤|g|磅|lb)?', weight)
        if w_match:
            w_val = float(w_match.group(1))
            w_unit = w_match.group(2) or "kg"
            if w_unit in ["斤"]:
                weight_kg = w_val / 2
            elif w_unit in ["g"]:
                weight_kg = w_val / 1000
            elif w_unit in ["磅", "lb", "lbs"]:
                weight_kg = w_val * 0.4536
            else:
                weight_kg = w_val

        height = str(height).strip().lower()
        height_m = 0.0

        h_match = re.match(r'([\d.]+)\s*(cm|米|m|毫米|mm)?', height)
        if h_match:
            h_val = float(h_match.group(1))
            h_unit = h_match.group(2) or "cm"
            if h_unit in ["米", "m"]:
                height_m = h_val
            elif h_unit in ["毫米", "mm"]:
                height_m = h_val / 1000
            else:
                if h_val < 3:
                    height_m = h_val
                else:
                    height_m = h_val / 100

        if weight_kg <= 0 or height_m <= 0:
            return {"error": "无法解析体重或身高，请确保输入正确"}

        bmi = weight_kg / (height_m * height_m)

        if bmi < 18.5:
            status = "偏瘦"
            suggestion = "建议增加营养摄入，适当力量训练增肌"
        elif bmi < 24:
            status = "正常"
            suggestion = "体重正常，保持健康饮食和规律运动即可"
        elif bmi < 28:
            status = "超重"
            suggestion = "建议控制饮食热量，增加有氧运动，避免剧烈运动伤膝盖"
        else:
            status = "肥胖"
            suggestion = "建议低冲击运动（游泳/快走），严格控制热量，必要时咨询医生"

        return {
            "bmi": round(bmi, 1),
            "weight_kg": round(weight_kg, 1),
            "height_m": round(height_m, 2),
            "status": status,
            "suggestion": suggestion,
            "standard": "中国成人BMI标准"
        }
    except Exception as e:
        return {"error": f"计算BMI失败: {str(e)}"}


# ─── 工具描述（用于 LangChain Tool Calling）──────────────────────


def get_external_tool_descriptions():
    """获取外部工具的描述列表，用于 LangChain Tool Calling"""
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
                "name": "get_ip_location",
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
                "name": "get_world_time",
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


# ─── 导出所有 API 函数 ─────────────────────────────────────────


__all__ = [
    # 需要 API Key
    "get_weather",
    "get_news",
    # 学习计划
    "search_open_library",
    "search_gutendex",
    "search_crossref",
    "search_poetrydb",
    "search_quran",
    "get_jinrishici",
    "get_hitokoto",
    "get_wikipedia_summary",
    "get_quotable_quote",
    # 健康计划
    "get_weather_forecast",
    "get_food_nutrition",
    "get_fruit_nutrition",
    "get_themealdb",
    "get_wger_exercises",
    "get_wger_muscles",
    "get_amap_weather",
    # 旅行计划
    "get_exchange_rates",
    "get_ip_location",
    "get_city_bikes",
    "get_open_brewery",
    # 工作计划
    "get_china_holidays",
    "get_world_time",
    "get_json_placeholder",
    "get_random_data",
    "get_open_trivia",
    # 财务计划
    "get_economic_data",
    "get_sec_edgar",
    "get_portfolio_optimizer",
    "get_ibanforge",
    # 通用与趣味工具
    "get_bored_activity",
    "get_agify_prediction",
    "calculate_bmi",
    # 工具描述
    "get_external_tool_descriptions",
]