"""
Tool Executor 节点 - 纯工具调用执行器

流程：
1. 接收 parameter_extractor 输出的 ranked_tools
2. 并行调用各个外部 API（天气、营养、运动等）
3. 实体解析 + 失败降级
4. 格式化输出 tool_data_parts

注意：这是一个纯执行节点，不做任何 LLM 判断。
所有外部 API 均为免费公开接口，无需 API Key。
"""


async def tool_executor_node(state) -> dict:
    """Tool Executor 节点：并行调用 ranked_tools 中的外部 API"""
    import asyncio

    ranked_tools = state.get("ranked_tools", [])

    print(f"[DEBUG] tool_executor: 执行 {len(ranked_tools)} 个工具")

    if not ranked_tools:
        return {
            "tool_call_results": [],
            "tool_data_parts": [],
            "tool_success_count": 0,
            "tool_total_count": 0,
            "tool_fail_log": [],
            "execution_trace": [
                {
                    "node": "tool_executor",
                    "status": "skipped",
                    "reason": "ranked_tools 为空"
                }
            ]
        }

    tasks = []
    for tool_info in ranked_tools:
        tasks.append(_call_single_tool(tool_info))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    tool_call_results = []
    tool_data_parts = []
    tool_fail_log = []
    success_count = 0

    for i, result in enumerate(results):
        tool_info = ranked_tools[i]
        tool_name = tool_info.get("tool", "unknown")

        if isinstance(result, Exception):
            tool_fail_log.append({
                "tool": tool_name,
                "error": str(result)
            })
            continue

        if result.get("success"):
            success_count += 1
            tool_call_results.append({
                "tool": tool_name,
                "data": result.get("data", {})
            })
            formatted = _format_tool_result(tool_name, result.get("data", {}))
            if formatted:
                tool_data_parts.append(formatted)
        else:
            tool_fail_log.append({
                "tool": tool_name,
                "error": result.get("error", "未知错误")
            })

    print(f"[DEBUG] tool_executor: 成功 {success_count}/{len(ranked_tools)} 个工具调用")
    if tool_call_results:
        print(f"[DEBUG] tool_executor: 成功工具: {[r['tool'] for r in tool_call_results]}")
    if tool_fail_log:
        print(f"[DEBUG] tool_executor: 失败工具: {[(f['tool'], f['error']) for f in tool_fail_log]}")

    return {
        "tool_call_results": tool_call_results,
        "tool_data_parts": tool_data_parts,
        "tool_success_count": success_count,
        "tool_total_count": len(ranked_tools),
        "tool_fail_log": tool_fail_log,
        "execution_trace": [
            {
                "node": "tool_executor",
                "total_tools": len(ranked_tools),
                "success_count": success_count,
                "fail_count": len(tool_fail_log),
                "success_tools": [r["tool"] for r in tool_call_results],
                "failed_tools": [f["tool"] for f in tool_fail_log],
                "success": True
            }
        ]
    }


async def _call_single_tool(tool_info: dict) -> dict:
    """调用单个工具"""
    tool_name = tool_info.get("tool", "")
    params = tool_info.get("params", {})

    required = tool_info.get("required_slots", [])
    if required:
        has_value = any(params.get(slot) for slot in required)
        if not has_value:
            return {"success": False, "error": "缺少必填参数"}

    try:
        if tool_name == "get_weather_forecast":
            return await _call_weather(params)
        elif tool_name == "get_exchange_rates":
            return await _call_exchange_rates(params)
        elif tool_name == "get_holidays":
            return await _call_holidays(params)
        elif tool_name == "get_food_nutrition":
            return await _call_food_nutrition(params)
        elif tool_name == "get_wger_exercises":
            return await _call_wger_exercises(params)
        elif tool_name == "search_open_library":
            return await _call_open_library(params)
        elif tool_name == "calculate_bmi":
            return await _call_bmi(params)
        elif tool_name == "get_city_intro":
            return await _call_city_intro(params)
        elif tool_name == "get_time":
            return await _call_time(params)
        elif tool_name == "get_wikipedia_summary":
            return await _call_wikipedia(params)
        elif tool_name == "get_themealdb":
            return await _call_themealdb(params)
        elif tool_name == "get_bored_activity":
            return await _call_bored_activity(params)
        elif tool_name == "get_joke":
            return await _call_joke(params)
        elif tool_name == "get_quote":
            return await _call_quote(params)
        elif tool_name == "get_country_info":
            return await _call_country_info(params)
        elif tool_name == "get_cocktail":
            return await _call_cocktail(params)
        elif tool_name == "get_ip_info":
            return await _call_ip_info(params)
        elif tool_name == "get_dog_image":
            return await _call_dog_image(params)
        elif tool_name == "get_cat_fact":
            return await _call_cat_fact(params)
        elif tool_name == "get_hn_top_stories":
            return await _call_hn_top_stories(params)
        elif tool_name == "get_word_definition":
            return await _call_word_definition(params)
        elif tool_name == "get_number_fact":
            return await _call_number_fact(params)
        elif tool_name == "search_github_repos":
            return await _call_github_repos(params)
        elif tool_name == "get_datamuse_words":
            return await _call_datamuse(params)
        elif tool_name == "get_air_quality":
            return await _call_air_quality(params)
        elif tool_name == "get_crypto_price":
            return await _call_crypto_price(params)
        elif tool_name == "get_city_bikes":
            return await _call_city_bikes(params)
        elif tool_name == "get_breweries":
            return await _call_breweries(params)
        elif tool_name == "get_free_games":
            return await _call_free_games(params)
        elif tool_name == "search_tv_shows":
            return await _call_tv_shows(params)
        elif tool_name == "get_pokemon":
            return await _call_pokemon(params)
        elif tool_name == "generate_qr_code":
            return await _call_qr_code(params)
        elif tool_name == "get_random_poem":
            return await _call_random_poem(params)
        elif tool_name == "get_useless_fact":
            return await _call_useless_fact(params)
        elif tool_name == "get_fox_image":
            return await _call_fox_image(params)
        elif tool_name == "get_duck_image":
            return await _call_duck_image(params)
        elif tool_name == "get_cat_image":
            return await _call_cat_image(params)
        elif tool_name == "get_dog_fact":
            return await _call_dog_fact(params)
        elif tool_name == "get_anime_quote":
            return await _call_anime_quote(params)
        elif tool_name == "get_color_palette":
            return await _call_color_palette(params)
        elif tool_name == "get_placeholder_image":
            return await _call_placeholder_image(params)
        elif tool_name == "search_gutendex":
            return await _call_gutendex(params)
        elif tool_name == "get_bible_verse":
            return await _call_bible_verse(params)
        elif tool_name == "get_github_user":
            return await _call_github_user(params)
        elif tool_name == "search_npm_packages":
            return await _call_npm_packages(params)
        elif tool_name == "get_favicon":
            return await _call_favicon(params)
        elif tool_name == "search_lyrics":
            return await _call_lyrics(params)
        elif tool_name == "search_itunes_music":
            return await _call_itunes_music(params)
        elif tool_name == "get_random_user":
            return await _call_random_user(params)
        elif tool_name == "get_age_by_name":
            return await _call_agify(params)
        elif tool_name == "get_gender_by_name":
            return await _call_genderize(params)
        elif tool_name == "get_nationality_by_name":
            return await _call_nationalize(params)
        elif tool_name == "get_kanye_quote":
            return await _call_kanye_quote(params)
        elif tool_name == "get_art_institute_chicago":
            return await _call_art_institute(params)
        elif tool_name == "get_studio_ghibli_films":
            return await _call_ghibli(params)
        elif tool_name == "get_waifu_image":
            return await _call_waifu_image(params)
        elif tool_name == "get_shibe_image":
            return await _call_shibe_image(params)
        elif tool_name == "get_chuck_norris_joke":
            return await _call_chuck_norris(params)
        elif tool_name == "get_advice_slip":
            return await _call_advice_slip(params)
        else:
            return {"success": False, "error": f"未知工具: {tool_name}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 天气类 ──────────────────────────────────────────────────────

async def _call_weather(params: dict) -> dict:
    """调用 Open-Meteo 天气 API（免费，无需 API Key）"""
    import requests

    city = params.get("city", "")
    if not city:
        return {"success": False, "error": "缺少城市参数"}

    try:
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_resp = requests.get(geo_url, params={
            "name": city,
            "count": 1,
            "language": "zh",
            "format": "json"
        }, timeout=10)
        geo_data = geo_resp.json()
        results = geo_data.get("results", [])
        if not results:
            return {"success": False, "error": f"未找到城市: {city}"}

        loc = results[0]
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        city_name = loc.get("name", city)

        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_resp = requests.get(weather_url, params={
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": 7
        }, timeout=10)
        weather_data = weather_resp.json()
        daily = weather_data.get("daily", {})
        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        weather_codes = daily.get("weather_code", [])
        precip_probs = daily.get("precipitation_probability_max", [])

        weather_text = []
        for i in range(min(len(dates), 7)):
            desc = _weather_code_to_text(weather_codes[i] if i < len(weather_codes) else 0)
            precip = precip_probs[i] if i < len(precip_probs) else 0
            weather_text.append(
                f"{dates[i]}: {desc}, "
                f"{min_temps[i] if i < len(min_temps) else '?'}~"
                f"{max_temps[i] if i < len(max_temps) else '?'}℃"
                f"{f', 降水概率{precip}%' if precip else ''}"
            )

        return {
            "success": True,
            "data": {"city": city_name, "weather": "\n".join(weather_text)}
        }

    except Exception as e:
        return {"success": False, "error": f"天气查询失败: {str(e)}"}


def _weather_code_to_text(code: int) -> str:
    """WMO 天气代码转中文描述"""
    weather_map = {
        0: "晴",
        1: "大部晴朗", 2: "局部多云", 3: "阴",
        45: "雾", 48: "雾凇",
        51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
        56: "冻毛毛雨", 57: "强冻毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        66: "冻雨", 67: "强冻雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        77: "雪粒",
        80: "阵雨", 81: "强阵雨", 82: "暴雨",
        85: "阵雪", 86: "强阵雪",
        95: "雷暴",
        96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹"
    }
    return weather_map.get(code, "未知天气")


# ─── 汇率类 ──────────────────────────────────────────────────────

async def _call_exchange_rates(params: dict) -> dict:
    """调用 Frankfurter 汇率 API（免费，无需 API Key）"""
    import requests

    base = params.get("base_currency", "CNY")
    try:
        url = f"https://api.frankfurter.app/latest"
        resp = requests.get(url, params={"from": base}, timeout=10)
        data = resp.json()
        rates = data.get("rates", {})
        common_currencies = ["USD", "EUR", "JPY", "GBP", "HKD", "KRW", "AUD", "CAD"]
        common = {k: round(v, 4) for k, v in rates.items() if k in common_currencies}
        return {"success": True, "data": {"base": base, "rates": common, "date": data.get("date", "")}}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 节假日类 ──────────────────────────────────────────────────

async def _call_holidays(params: dict) -> dict:
    """调用 Nager.Date 节假日 API（免费，无需 API Key）"""
    import requests

    country = params.get("country", "CN")
    year = params.get("year")
    if not year:
        from datetime import datetime
        year = datetime.now().year

    try:
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            holidays = resp.json()
            result = []
            for h in holidays[:15]:
                result.append({
                    "date": h.get("date", ""),
                    "name": h.get("localName", h.get("name", "")),
                    "global": h.get("global", True)
                })
            return {"success": True, "data": {"country": country, "year": year, "holidays": result}}
        return {"success": False, "error": f"获取节假日失败: HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 食物营养类 ──────────────────────────────────────────────────

async def _call_food_nutrition(params: dict) -> dict:
    """调用 Open Food Facts API（免费，无需 API Key）"""
    import requests

    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "缺少食物名称"}

    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        resp = requests.get(url, params={
            "search_terms": query,
            "json": 1,
            "page_size": 3
        }, timeout=10)
        data = resp.json()
        products = data.get("products", [])
        if products:
            p = products[0]
            nutriments = p.get("nutriments", {})
            result = {
                "name": p.get("product_name", query),
                "calories": nutriments.get("energy-kcal_100g", "未知"),
                "protein": nutriments.get("proteins_100g", "未知"),
                "fat": nutriments.get("fat_100g", "未知"),
                "carbs": nutriments.get("carbohydrates_100g", "未知"),
            }
            return {"success": True, "data": result}
        return {"success": False, "error": f"未找到食物: {query}"}
    except Exception as e:
        return {"success": False, "error": f"营养查询失败: {str(e)}"}


# ─── 运动健身类 ──────────────────────────────────────────────────

async def _call_wger_exercises(params: dict) -> dict:
    """调用 wger 运动 API（免费，无需 API Key）"""
    import requests

    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "缺少运动名称"}

    try:
        url = "https://wger.de/api/v2/exercise/"
        resp = requests.get(url, params={
            "language": 2,
            "limit": 5,
            "search": query
        }, timeout=10)
        data = resp.json()
        exercises = data.get("results", [])
        if exercises:
            result = []
            for ex in exercises[:3]:
                import re
                desc = re.sub(r'<[^>]+>', '', ex.get("description", ""))[:150]
                result.append({
                    "name": ex.get("name", ""),
                    "description": desc,
                    "muscles": [m.get("name", "") for m in ex.get("muscles", [])],
                })
            return {"success": True, "data": {"exercises": result}}
        return {"success": False, "error": f"未找到运动: {query}"}
    except Exception as e:
        return {"success": False, "error": f"运动查询失败: {str(e)}"}


# ─── 书籍学习类 ──────────────────────────────────────────────────

async def _call_open_library(params: dict) -> dict:
    """调用 Open Library API（免费，无需 API Key）"""
    import requests

    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "缺少书名"}

    try:
        url = "https://openlibrary.org/search.json"
        resp = requests.get(url, params={"q": query, "limit": 5}, timeout=10)
        data = resp.json()
        docs = data.get("docs", [])
        if docs:
            result = []
            for doc in docs[:3]:
                result.append({
                    "title": doc.get("title", ""),
                    "author": ", ".join(doc.get("author_name", [])[:2]),
                    "year": doc.get("first_publish_year", ""),
                })
            return {"success": True, "data": {"books": result}}
        return {"success": False, "error": f"未找到图书: {query}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 健康计算类 ──────────────────────────────────────────────────

async def _call_bmi(params: dict) -> dict:
    """计算 BMI（纯计算，无需外部 API）"""
    try:
        height_cm = float(params.get("height_cm", 0))
        weight_kg = float(params.get("weight_kg", 0))
        if not height_cm or not weight_kg:
            return {"success": False, "error": "缺少身高或体重"}

        height_m = height_cm / 100
        bmi = weight_kg / (height_m ** 2)

        if bmi < 18.5:
            category = "偏瘦"
        elif bmi < 24:
            category = "正常"
        elif bmi < 28:
            category = "偏胖"
        else:
            category = "肥胖"

        return {
            "success": True,
            "data": {
                "bmi": round(bmi, 1),
                "category": category,
                "height": height_cm,
                "weight": weight_kg
            }
        }
    except (ValueError, TypeError):
        return {"success": False, "error": "身高体重格式错误"}


# ─── 百科知识类 ──────────────────────────────────────────────────

async def _call_city_intro(params: dict) -> dict:
    """获取城市介绍（使用 Wikipedia API，免费无需 Key）"""
    import requests

    city = params.get("city", "")
    if not city:
        return {"success": False, "error": "缺少城市"}

    try:
        url = f"https://zh.wikipedia.org/api/rest_v1/page/summary/{city}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            extract = data.get("extract", "")
            if extract:
                return {"success": True, "data": {"city": city, "introduction": extract[:500]}}
        url_en = f"https://en.wikipedia.org/api/rest_v1/page/summary/{city}"
        resp_en = requests.get(url_en, timeout=10)
        if resp_en.status_code == 200:
            data = resp_en.json()
            extract = data.get("extract", "")
            if extract:
                return {"success": True, "data": {"city": city, "introduction": extract[:500]}}
        return {"success": False, "error": f"未找到城市介绍: {city}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_wikipedia(params: dict) -> dict:
    """获取 Wikipedia 摘要（免费，无需 API Key）"""
    import requests
    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "缺少查询词"}

    try:
        url = f"https://zh.wikipedia.org/api/rest_v1/page/summary/{query}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            extract = data.get("extract", "")
            if extract:
                return {"success": True, "data": {"title": data.get("title", query), "summary": extract[:500]}}
        url_en = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
        resp_en = requests.get(url_en, timeout=10)
        if resp_en.status_code == 200:
            data = resp_en.json()
            extract = data.get("extract", "")
            if extract:
                return {"success": True, "data": {"title": data.get("title", query), "summary": extract[:500]}}
        return {"success": False, "error": f"未找到: {query}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_country_info(params: dict) -> dict:
    """调用 REST Countries API 获取国家信息（免费，无需 API Key）"""
    import requests

    country = params.get("country", "")
    if not country:
        return {"success": False, "error": "缺少国家名称"}

    try:
        url = f"https://restcountries.com/v3.1/name/{country}"
        resp = requests.get(url, params={"fullText": "true"}, timeout=10)
        if resp.status_code != 200:
            url = f"https://restcountries.com/v3.1/name/{country}"
            resp = requests.get(url, timeout=10)
        data = resp.json()
        if data and isinstance(data, list):
            c = data[0]
            result = {
                "name": c.get("name", {}).get("common", country),
                "capital": c.get("capital", [""])[0] if c.get("capital") else "",
                "region": c.get("region", ""),
                "population": c.get("population", 0),
                "area": c.get("area", 0),
                "languages": list(c.get("languages", {}).values()),
                "currencies": list(c.get("currencies", {}).keys()),
            }
            return {"success": True, "data": result}
        return {"success": False, "error": f"未找到国家: {country}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 食谱餐饮类 ──────────────────────────────────────────────────

async def _call_themealdb(params: dict) -> dict:
    """调用 TheMealDB 获取食谱（免费，无需 API Key）"""
    import requests
    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "缺少菜品名"}

    try:
        url = "https://www.themealdb.com/api/json/v1/1/search.php"
        resp = requests.get(url, params={"s": query}, timeout=10)
        data = resp.json()
        meals = data.get("meals", [])
        if meals:
            meal = meals[0]
            ingredients = []
            for i in range(1, 21):
                ing = meal.get(f"strIngredient{i}", "")
                measure = meal.get(f"strMeasure{i}", "")
                if ing:
                    ingredients.append(f"{ing} {measure}".strip())
            return {
                "success": True,
                "data": {
                    "name": meal.get("strMeal", ""),
                    "category": meal.get("strCategory", ""),
                    "area": meal.get("strArea", ""),
                    "instructions": meal.get("strInstructions", "")[:300],
                    "ingredients": ingredients[:10],
                }
            }
        return {"success": False, "error": f"未找到食谱: {query}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_cocktail(params: dict) -> dict:
    """调用 TheCocktailDB 获取鸡尾酒配方（免费，无需 API Key）"""
    import requests
    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "缺少鸡尾酒名称"}

    try:
        url = "https://www.thecocktaildb.com/api/json/v1/1/search.php"
        resp = requests.get(url, params={"s": query}, timeout=10)
        data = resp.json()
        drinks = data.get("drinks", [])
        if drinks:
            d = drinks[0]
            ingredients = []
            for i in range(1, 16):
                ing = d.get(f"strIngredient{i}", "")
                measure = d.get(f"strMeasure{i}", "")
                if ing:
                    ingredients.append(f"{ing} - {measure}".strip(" -"))
            return {
                "success": True,
                "data": {
                    "name": d.get("strDrink", ""),
                    "category": d.get("strCategory", ""),
                    "alcoholic": d.get("strAlcoholic", ""),
                    "glass": d.get("strGlass", ""),
                    "instructions": d.get("strInstructions", "")[:200],
                    "ingredients": ingredients,
                }
            }
        return {"success": False, "error": f"未找到鸡尾酒: {query}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 时间类 ──────────────────────────────────────────────────────

async def _call_time(params: dict) -> dict:
    """获取当前时间（本地计算）"""
    from datetime import datetime
    timezone = params.get("timezone", "Asia/Shanghai")
    now = datetime.now()
    return {
        "success": True,
        "data": {
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "timezone": timezone
        }
    }


# ─── 娱乐休闲类 ──────────────────────────────────────────────────

async def _call_bored_activity(params: dict) -> dict:
    """调用 Bored API 获取活动建议（免费，无需 API Key）"""
    import requests
    try:
        activity_type = params.get("activity_type", "")
        url = "https://www.boredapi.com/api/activity/"
        req_params = {}
        if activity_type:
            req_params["type"] = activity_type
        resp = requests.get(url, params=req_params if req_params else None, timeout=10)
        data = resp.json()
        if data.get("activity"):
            return {
                "success": True,
                "data": {
                    "activity": data.get("activity", ""),
                    "type": data.get("type", ""),
                    "participants": data.get("participants", ""),
                    "price": data.get("price", ""),
                    "accessibility": data.get("accessibility", ""),
                }
            }
        return {"success": False, "error": "获取活动失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_joke(params: dict) -> dict:
    """调用 JokeAPI 获取笑话（免费，无需 API Key）"""
    import requests
    try:
        category = params.get("category", "Any")
        url = f"https://v2.jokeapi.dev/joke/{category}"
        resp = requests.get(url, params={
            "lang": "en",
            "type": "twopart",
            "safe-mode": ""
        }, timeout=10)
        data = resp.json()
        if data.get("error") is False:
            if data.get("type") == "twopart":
                return {
                    "success": True,
                    "data": {
                        "setup": data.get("setup", ""),
                        "delivery": data.get("delivery", ""),
                        "category": data.get("category", "")
                    }
                }
            else:
                return {
                    "success": True,
                    "data": {
                        "joke": data.get("joke", ""),
                        "category": data.get("category", "")
                    }
                }
        return {"success": False, "error": "获取笑话失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_quote(params: dict) -> dict:
    """调用 Quotable 获取名言（免费，无需 API Key）"""
    import requests
    try:
        tags = params.get("tags", "")
        url = "https://api.quotable.io/random"
        req_params = {}
        if tags:
            req_params["tags"] = tags
        resp = requests.get(url, params=req_params if req_params else None, timeout=10)
        data = resp.json()
        if data.get("content"):
            return {
                "success": True,
                "data": {
                    "content": data.get("content", ""),
                    "author": data.get("author", ""),
                    "tags": data.get("tags", [])
                }
            }
        return {"success": False, "error": "获取名言失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_dog_image(params: dict) -> dict:
    """调用 Dog API 获取随机狗狗图片（免费，无需 API Key）"""
    import requests
    try:
        breed = params.get("breed", "")
        if breed:
            url = f"https://dog.ceo/api/breed/{breed.lower()}/images/random"
        else:
            url = "https://dog.ceo/api/breeds/image/random"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("status") == "success":
            return {
                "success": True,
                "data": {
                    "image_url": data.get("message", ""),
                    "breed": breed or "random"
                }
            }
        return {"success": False, "error": "获取狗狗图片失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_cat_fact(params: dict) -> dict:
    """调用 Cat Facts API 获取猫咪趣闻（免费，无需 API Key）"""
    import requests
    try:
        url = "https://catfact.ninja/fact"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("fact"):
            return {
                "success": True,
                "data": {
                    "fact": data.get("fact", ""),
                    "length": data.get("length", 0)
                }
            }
        return {"success": False, "error": "获取猫咪趣闻失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 科技新闻类 ──────────────────────────────────────────────────

async def _call_hn_top_stories(params: dict) -> dict:
    """调用 Hacker News API 获取科技头条（免费，无需 API Key）"""
    import requests
    try:
        limit = int(params.get("limit", 5))
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        resp = requests.get(url, timeout=10)
        story_ids = resp.json()
        stories = []
        for sid in story_ids[:limit]:
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
            story_resp = requests.get(story_url, timeout=10)
            story = story_resp.json()
            if story:
                stories.append({
                    "title": story.get("title", ""),
                    "url": story.get("url", ""),
                    "score": story.get("score", 0),
                    "by": story.get("by", ""),
                })
        return {"success": True, "data": {"stories": stories}}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 工具查询类 ──────────────────────────────────────────────────

async def _call_ip_info(params: dict) -> dict:
    """调用 ip-api.com 获取 IP 地理位置（免费，无需 API Key）"""
    import requests
    try:
        ip = params.get("ip", "")
        url = f"http://ip-api.com/json/{ip}" if ip else "http://ip-api.com/json/"
        resp = requests.get(url, params={"lang": "zh-CN"}, timeout=10)
        data = resp.json()
        if data.get("status") == "success":
            return {
                "success": True,
                "data": {
                    "ip": data.get("query", ""),
                    "country": data.get("country", ""),
                    "region": data.get("regionName", ""),
                    "city": data.get("city", ""),
                    "zip": data.get("zip", ""),
                    "lat": data.get("lat", ""),
                    "lon": data.get("lon", ""),
                    "timezone": data.get("timezone", ""),
                    "isp": data.get("isp", ""),
                }
            }
        return {"success": False, "error": data.get("message", "IP查询失败")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 学习教育类 ──────────────────────────────────────────────────

async def _call_word_definition(params: dict) -> dict:
    """调用 Dictionary API 获取单词定义（免费，无需 API Key）"""
    import requests
    word = params.get("word", "")
    if not word:
        return {"success": False, "error": "缺少单词"}

    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                entry = data[0]
                phonetic = entry.get("phonetic", "")
                meanings = entry.get("meanings", [])
                result = {
                    "word": entry.get("word", word),
                    "phonetic": phonetic,
                    "meanings": []
                }
                for m in meanings[:3]:
                    defs = [d.get("definition", "") for d in m.get("definitions", [])[:2]]
                    result["meanings"].append({
                        "part_of_speech": m.get("partOfSpeech", ""),
                        "definitions": defs
                    })
                return {"success": True, "data": result}
        return {"success": False, "error": f"未找到单词: {word}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_number_fact(params: dict) -> dict:
    """调用 Numbers API 获取数字趣闻（免费，无需 API Key）"""
    import requests
    number = params.get("number", "")
    fact_type = params.get("type", "trivia")

    try:
        if number:
            url = f"http://numbersapi.com/{number}/{fact_type}"
        else:
            url = f"http://numbersapi.com/random/{fact_type}"
        resp = requests.get(url, params={"json": ""}, timeout=10)
        data = resp.json()
        if data.get("text"):
            return {
                "success": True,
                "data": {
                    "number": data.get("number", ""),
                    "text": data.get("text", ""),
                    "type": data.get("type", fact_type)
                }
            }
        return {"success": False, "error": "获取数字趣闻失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_github_repos(params: dict) -> dict:
    """调用 GitHub API 搜索仓库（免费，公开数据无需 Key）"""
    import requests
    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "缺少搜索关键词"}

    try:
        url = "https://api.github.com/search/repositories"
        resp = requests.get(url, params={
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 5
        }, timeout=10, headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PlanHub-AI"
        })
        data = resp.json()
        items = data.get("items", [])
        if items:
            repos = []
            for item in items[:5]:
                repos.append({
                    "name": item.get("full_name", ""),
                    "description": item.get("description", ""),
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language", ""),
                    "url": item.get("html_url", "")
                })
            return {"success": True, "data": {"repos": repos, "total_count": data.get("total_count", 0)}}
        return {"success": False, "error": "未找到相关仓库"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_datamuse(params: dict) -> dict:
    """调用 Datamuse API 获取单词联想/押韵（免费，无需 API Key）"""
    import requests
    word = params.get("word", "")
    mode = params.get("mode", "means_like")
    if not word:
        return {"success": False, "error": "缺少单词"}

    try:
        param_map = {
            "means_like": "ml",
            "sounds_like": "sl",
            "spelled_like": "sp",
            "rhymes": "rel_rhy",
            "synonyms": "rel_syn",
            "antonyms": "rel_ant",
        }
        param_key = param_map.get(mode, "ml")
        url = f"https://api.datamuse.com/words?{param_key}={word}&max=10"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data:
            words = [{"word": w.get("word", ""), "score": w.get("score", 0)} for w in data[:10]]
            return {"success": True, "data": {"words": words, "mode": mode}}
        return {"success": False, "error": "未找到相关单词"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 健康环境类 ──────────────────────────────────────────────────

async def _call_air_quality(params: dict) -> dict:
    """调用 OpenAQ API 获取空气质量数据（免费，无需 API Key）"""
    import requests
    city = params.get("city", "")
    country = params.get("country", "")
    if not city:
        return {"success": False, "error": "缺少城市"}

    try:
        url = "https://api.openaq.org/v2/latest"
        req_params = {"limit": 5, "order_by": "lastUpdated", "sort": "desc"}
        if city:
            req_params["city"] = city
        if country:
            req_params["country"] = country
        resp = requests.get(url, params=req_params, timeout=10)
        data = resp.json()
        results = data.get("results", [])
        if results:
            measurements = []
            for r in results[:3]:
                for m in r.get("measurements", [])[:3]:
                    measurements.append({
                        "parameter": m.get("parameter", ""),
                        "value": m.get("value", 0),
                        "unit": m.get("unit", ""),
                        "lastUpdated": m.get("lastUpdated", "")
                    })
            return {
                "success": True,
                "data": {
                    "city": city,
                    "measurements": measurements,
                    "location": results[0].get("city", "")
                }
            }
        return {"success": False, "error": f"未找到 {city} 的空气质量数据"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_crypto_price(params: dict) -> dict:
    """调用 CoinGecko API 获取加密货币价格（免费，无需 API Key）"""
    import requests
    ids = params.get("ids", "bitcoin,ethereum")
    vs_currency = params.get("vs_currency", "usd")

    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        resp = requests.get(url, params={
            "ids": ids,
            "vs_currencies": vs_currency,
            "include_24hr_change": "true",
            "include_market_cap": "true"
        }, timeout=10)
        data = resp.json()
        if data:
            prices = []
            for coin_id, info in data.items():
                prices.append({
                    "id": coin_id,
                    "price": info.get(vs_currency, 0),
                    "change_24h": info.get(f"{vs_currency}_24h_change", 0),
                    "market_cap": info.get(f"{vs_currency}_market_cap", 0)
                })
            return {"success": True, "data": {"prices": prices, "vs_currency": vs_currency}}
        return {"success": False, "error": "获取加密货币价格失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 旅行生活类 ──────────────────────────────────────────────────

async def _call_city_bikes(params: dict) -> dict:
    """调用 CityBikes API 获取城市共享单车信息（免费，无需 API Key）"""
    import requests
    city = params.get("city", "")
    if not city:
        return {"success": False, "error": "缺少城市"}

    try:
        url = "https://api.citybik.es/v2/networks"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        networks = data.get("networks", [])
        matching = [n for n in networks if city.lower() in n.get("location", {}).get("city", "").lower()]
        if matching:
            result = []
            for n in matching[:3]:
                result.append({
                    "name": n.get("name", ""),
                    "city": n.get("location", {}).get("city", ""),
                    "country": n.get("location", {}).get("country", ""),
                    "stations_count": n.get("stations", 0)
                })
            return {"success": True, "data": {"networks": result}}
        return {"success": False, "error": f"未找到 {city} 的共享单车信息"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_breweries(params: dict) -> dict:
    """调用 Open Brewery DB 获取精酿啤酒厂信息（免费，无需 API Key）"""
    import requests
    city = params.get("city", "")
    query = params.get("query", "")
    try:
        if city:
            url = "https://api.openbrewerydb.org/v1/breweries"
            resp = requests.get(url, params={"by_city": city, "per_page": 5}, timeout=10)
        elif query:
            url = "https://api.openbrewerydb.org/v1/breweries/search"
            resp = requests.get(url, params={"query": query, "per_page": 5}, timeout=10)
        else:
            return {"success": False, "error": "缺少城市或搜索词"}
        data = resp.json()
        if data and isinstance(data, list):
            breweries = []
            for b in data[:5]:
                breweries.append({
                    "name": b.get("name", ""),
                    "type": b.get("brewery_type", ""),
                    "city": b.get("city", ""),
                    "state": b.get("state", ""),
                    "website": b.get("website_url", "")
                })
            return {"success": True, "data": {"breweries": breweries}}
        return {"success": False, "error": "未找到相关啤酒厂"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 娱乐休闲类 ──────────────────────────────────────────────────

async def _call_free_games(params: dict) -> dict:
    """调用 FreeToGame API 获取免费游戏推荐（免费，无需 API Key）"""
    import requests
    platform = params.get("platform", "")
    genre = params.get("genre", "")
    try:
        url = "https://www.freetogame.com/api/games"
        req_params = {"sort-by": "popularity"}
        if platform:
            req_params["platform"] = platform
        if genre:
            req_params["category"] = genre
        resp = requests.get(url, params=req_params, timeout=10)
        data = resp.json()
        if isinstance(data, list) and data:
            games = []
            for g in data[:5]:
                games.append({
                    "title": g.get("title", ""),
                    "genre": g.get("genre", ""),
                    "platform": g.get("platform", ""),
                    "publisher": g.get("publisher", ""),
                    "description": g.get("short_description", "")[:100]
                })
            return {"success": True, "data": {"games": games}}
        return {"success": False, "error": "获取免费游戏失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_tv_shows(params: dict) -> dict:
    """调用 TVmaze API 搜索电视剧（免费，无需 API Key）"""
    import requests
    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "缺少搜索词"}

    try:
        url = "https://api.tvmaze.com/search/shows"
        resp = requests.get(url, params={"q": query}, timeout=10)
        data = resp.json()
        if isinstance(data, list) and data:
            shows = []
            for item in data[:5]:
                show = item.get("show", {})
                genres = show.get("genres", [])
                summary = show.get("summary", "")
                import re
                summary = re.sub(r'<[^>]+>', '', summary)[:150]
                shows.append({
                    "name": show.get("name", ""),
                    "genres": genres,
                    "status": show.get("status", ""),
                    "premiered": show.get("premiered", ""),
                    "rating": show.get("rating", {}).get("average", ""),
                    "summary": summary
                })
            return {"success": True, "data": {"shows": shows}}
        return {"success": False, "error": f"未找到电视剧: {query}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_pokemon(params: dict) -> dict:
    """调用 PokéAPI 获取宝可梦信息（免费，无需 API Key）"""
    import requests
    name = params.get("name", "")
    if not name:
        return {"success": False, "error": "缺少宝可梦名称"}

    try:
        url = f"https://pokeapi.co/api/v2/pokemon/{name.lower()}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            types = [t.get("type", {}).get("name", "") for t in data.get("types", [])]
            stats = {s.get("stat", {}).get("name", ""): s.get("base_stat", 0) for s in data.get("stats", [])}
            return {
                "success": True,
                "data": {
                    "name": data.get("name", name),
                    "id": data.get("id", ""),
                    "height": data.get("height", 0),
                    "weight": data.get("weight", 0),
                    "types": types,
                    "stats": stats
                }
            }
        return {"success": False, "error": f"未找到宝可梦: {name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 工具与趣味类 ────────────────────────────────────────────────

async def _call_qr_code(params: dict) -> dict:
    """调用 QR Code API 生成二维码（免费，无需 API Key）"""
    import requests
    text = params.get("text", "")
    size = params.get("size", 200)
    if not text:
        return {"success": False, "error": "缺少内容"}

    try:
        url = "https://api.qrserver.com/v1/create-qr-code/"
        resp = requests.get(url, params={
            "data": text,
            "size": f"{size}x{size}",
            "format": "png"
        }, timeout=10)
        if resp.status_code == 200 and resp.content:
            return {
                "success": True,
                "data": {
                    "qr_image_url": f"https://api.qrserver.com/v1/create-qr-code/?data={text}&size={size}x{size}",
                    "content": text,
                    "size": size
                }
            }
        return {"success": False, "error": "生成二维码失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_random_poem(params: dict) -> dict:
    """调用 PoetryDB 获取随机诗歌（免费，无需 API Key）"""
    import requests
    author = params.get("author", "")
    try:
        if author:
            url = f"https://poetrydb.org/author/{author}/random"
        else:
            url = "https://poetrydb.org/random"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if isinstance(data, list) and data:
            poem = data[0]
            lines = poem.get("lines", [])
            return {
                "success": True,
                "data": {
                    "title": poem.get("title", ""),
                    "author": poem.get("author", ""),
                    "lines": lines[:8],
                    "linecount": poem.get("linecount", 0)
                }
            }
        return {"success": False, "error": "获取诗歌失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_useless_fact(params: dict) -> dict:
    """获取随机无用趣闻（免费，无需 API Key）"""
    import requests
    try:
        url = "https://uselessfacts.jsph.pl/api/v2/facts/random"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("text"):
            return {
                "success": True,
                "data": {
                    "text": data.get("text", ""),
                    "source": data.get("source", "")
                }
            }
        return {"success": False, "error": "获取趣闻失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 动物图片类 ──────────────────────────────────────────────────

async def _call_fox_image(params: dict) -> dict:
    """调用 RandomFox 获取随机狐狸图片（免费，无需 API Key）"""
    import requests
    try:
        url = "https://randomfox.ca/floof/"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("image"):
            return {
                "success": True,
                "data": {
                    "image_url": data.get("image", ""),
                    "link": data.get("link", "")
                }
            }
        return {"success": False, "error": "获取狐狸图片失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_duck_image(params: dict) -> dict:
    """调用 RandomDuck 获取随机鸭子图片（免费，无需 API Key）"""
    import requests
    try:
        url = "https://random-d.uk/api/random"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("url"):
            return {
                "success": True,
                "data": {
                    "image_url": data.get("url", ""),
                    "message": data.get("message", "")
                }
            }
        return {"success": False, "error": "获取鸭子图片失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_cat_image(params: dict) -> dict:
    """调用 Cataas 获取随机猫咪图片（免费，无需 API Key）"""
    import requests
    try:
        gif = params.get("gif", False)
        tag = params.get("tag", "")
        url = "https://cataas.com/cat"
        if gif:
            url += "/gif"
        if tag:
            url += f"/{tag}"
        return {
            "success": True,
            "data": {
                "image_url": f"{url}?width=400",
                "tag": tag or "random",
                "gif": gif
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_dog_fact(params: dict) -> dict:
    """调用 Dog Facts API 获取狗狗趣闻（免费，无需 API Key）"""
    import requests
    try:
        url = "https://dogapi.dog/api/v2/facts"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        facts = data.get("data", [])
        if facts:
            return {
                "success": True,
                "data": {
                    "fact": facts[0].get("attributes", {}).get("body", ""),
                    "id": facts[0].get("id", "")
                }
            }
        return {"success": False, "error": "获取狗狗趣闻失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_shibe_image(params: dict) -> dict:
    """调用 Shibe.Online 获取随机柴犬/猫咪/小鸟图片（免费，无需 API Key）"""
    import requests
    try:
        animal = params.get("animal", "shibes")
        count = int(params.get("count", 1))
        url = f"http://shibe.online/api/{animal}"
        resp = requests.get(url, params={"count": count}, timeout=10)
        data = resp.json()
        if isinstance(data, list) and data:
            return {
                "success": True,
                "data": {
                    "image_urls": data,
                    "animal": animal,
                    "count": len(data)
                }
            }
        return {"success": False, "error": "获取图片失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 动漫类 ──────────────────────────────────────────────────────

async def _call_anime_quote(params: dict) -> dict:
    """获取随机动漫名言（免费，无需 API Key）"""
    import requests
    try:
        url = "https://animechan.xyz/api/random"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "data": {
                    "anime": data.get("anime", ""),
                    "character": data.get("character", ""),
                    "quote": data.get("quote", "")
                }
            }
        return {"success": False, "error": "获取动漫名言失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_ghibli(params: dict) -> dict:
    """调用 Studio Ghibli API 获取吉卜力工作室电影信息（免费，无需 API Key）"""
    import requests
    try:
        query = params.get("query", "")
        url = "https://ghibliapi.vercel.app/films"
        resp = requests.get(url, timeout=10)
        films = resp.json()
        if query and films:
            films = [f for f in films if query.lower() in f.get("title", "").lower()]
        if films:
            result = []
            for f in films[:5]:
                result.append({
                    "title": f.get("title", ""),
                    "original_title": f.get("original_title", ""),
                    "director": f.get("director", ""),
                    "release_date": f.get("release_date", ""),
                    "running_time": f.get("running_time", ""),
                    "description": f.get("description", "")[:200]
                })
            return {"success": True, "data": {"films": result, "total": len(result)}}
        return {"success": False, "error": "未找到吉卜力电影"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_waifu_image(params: dict) -> dict:
    """调用 Waifu.pics 获取动漫女生图片（免费，无需 API Key）"""
    import requests
    try:
        category = params.get("category", "waifu")
        nsfw = params.get("nsfw", False)
        url_type = "nsfw" if nsfw else "sfw"
        url = f"https://api.waifu.pics/{url_type}/{category}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("url"):
            return {
                "success": True,
                "data": {
                    "image_url": data.get("url", ""),
                    "category": category,
                    "nsfw": nsfw
                }
            }
        return {"success": False, "error": "获取图片失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 艺术设计类 ──────────────────────────────────────────────────

async def _call_color_palette(params: dict) -> dict:
    """调用 Colormind 生成配色方案（免费，无需 API Key）"""
    import requests
    try:
        model = params.get("model", "default")
        url = "http://colormind.io/api/"
        resp = requests.post(url, json={"model": model}, timeout=10)
        data = resp.json()
        colors = data.get("result", [])
        if colors:
            hex_colors = []
            for rgb in colors:
                hex_color = "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])
                hex_colors.append(hex_color)
            return {
                "success": True,
                "data": {
                    "colors": hex_colors,
                    "rgb_colors": colors,
                    "model": model
                }
            }
        return {"success": False, "error": "生成配色失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_placeholder_image(params: dict) -> dict:
    """生成占位图片（免费，无需 API Key）"""
    import requests
    try:
        width = params.get("width", 300)
        height = params.get("height", 200)
        text = params.get("text", "")
        bg_color = params.get("bg_color", "cccccc")
        text_color = params.get("text_color", "9c9c9c")
        url = f"https://dummyimage.com/{width}x{height}/{bg_color}/{text_color}"
        if text:
            import urllib.parse
            url += f"&text={urllib.parse.quote(text)}"
        return {
            "success": True,
            "data": {
                "image_url": url,
                "width": width,
                "height": height,
                "text": text
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_art_institute(params: dict) -> dict:
    """调用芝加哥艺术学院 API 获取艺术作品（免费，无需 API Key）"""
    import requests
    try:
        query = params.get("query", "")
        limit = int(params.get("limit", 3))
        if query:
            url = "https://api.artic.edu/api/v1/artworks/search"
            resp = requests.get(url, params={"q": query, "limit": limit, "fields": "id,title,artist_display,image_id,medium_display,date_display"}, timeout=10)
        else:
            url = "https://api.artic.edu/api/v1/artworks"
            resp = requests.get(url, params={"limit": limit, "fields": "id,title,artist_display,image_id,medium_display,date_display"}, timeout=10)
        data = resp.json()
        artworks = data.get("data", [])
        if artworks:
            result = []
            iiif_url = data.get("config", {}).get("iiif_url", "")
            for a in artworks:
                image_id = a.get("image_id", "")
                image_url = f"{iiif_url}/{image_id}/full/843,/0/default.jpg" if image_id and iiif_url else ""
                result.append({
                    "title": a.get("title", ""),
                    "artist": a.get("artist_display", ""),
                    "date": a.get("date_display", ""),
                    "medium": a.get("medium_display", ""),
                    "image_url": image_url
                })
            return {"success": True, "data": {"artworks": result, "total": len(result)}}
        return {"success": False, "error": "未找到艺术作品"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 书籍学习类 ──────────────────────────────────────────────────

async def _call_gutendex(params: dict) -> dict:
    """调用 Gutendex 搜索古腾堡计划免费图书（免费，无需 API Key）"""
    import requests
    try:
        query = params.get("query", "")
        if not query:
            return {"success": False, "error": "缺少搜索关键词"}
        url = "https://gutendex.com/books"
        resp = requests.get(url, params={"search": query, "ids": ""}, timeout=10)
        data = resp.json()
        books = data.get("results", [])
        if books:
            result = []
            for b in books[:5]:
                authors = [a.get("name", "") for a in b.get("authors", [])[:2]]
                result.append({
                    "title": b.get("title", ""),
                    "authors": authors,
                    "languages": b.get("languages", []),
                    "download_count": b.get("download_count", 0),
                    "id": b.get("id", "")
                })
            return {"success": True, "data": {"books": result, "total": data.get("count", 0)}}
        return {"success": False, "error": "未找到图书"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_bible_verse(params: dict) -> dict:
    """调用 Bible API 获取圣经经文（免费，无需 API Key）"""
    import requests
    try:
        reference = params.get("reference", "John 3:16")
        translation = params.get("translation", "bbe")
        url = f"https://bible-api.com/{reference}"
        resp = requests.get(url, params={"translation": translation}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            verses = data.get("verses", [])
            text = "\n".join([v.get("text", "").strip() for v in verses])
            return {
                "success": True,
                "data": {
                    "reference": data.get("reference", ""),
                    "text": text,
                    "translation": data.get("translation_name", translation),
                    "translation_id": data.get("translation_id", translation)
                }
            }
        return {"success": False, "error": "获取经文失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 开发工具类 ──────────────────────────────────────────────────

async def _call_github_user(params: dict) -> dict:
    """调用 GitHub API 获取用户信息（免费，公开数据无需 Key）"""
    import requests
    username = params.get("username", "")
    if not username:
        return {"success": False, "error": "缺少用户名"}
    try:
        url = f"https://api.github.com/users/{username}"
        resp = requests.get(url, timeout=10, headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PlanHub-AI"
        })
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "data": {
                    "username": data.get("login", ""),
                    "name": data.get("name", ""),
                    "bio": data.get("bio", ""),
                    "avatar_url": data.get("avatar_url", ""),
                    "followers": data.get("followers", 0),
                    "following": data.get("following", 0),
                    "public_repos": data.get("public_repos", 0),
                    "location": data.get("location", ""),
                    "blog": data.get("blog", ""),
                    "created_at": data.get("created_at", "")
                }
            }
        return {"success": False, "error": f"获取用户失败: HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_npm_packages(params: dict) -> dict:
    """调用 npm API 搜索 npm 包（免费，无需 API Key）"""
    import requests
    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "缺少搜索关键词"}
    try:
        url = "https://registry.npmjs.org/-/v1/search"
        resp = requests.get(url, params={"text": query, "size": 5}, timeout=10)
        data = resp.json()
        packages = data.get("objects", [])
        if packages:
            result = []
            for p in packages[:5]:
                pkg = p.get("package", {})
                result.append({
                    "name": pkg.get("name", ""),
                    "version": pkg.get("version", ""),
                    "description": pkg.get("description", ""),
                    "author": pkg.get("author", {}).get("name", ""),
                    "keywords": pkg.get("keywords", [])[:5],
                    "links": pkg.get("links", {})
                })
            return {"success": True, "data": {"packages": result, "total": data.get("total", 0)}}
        return {"success": False, "error": "未找到相关包"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_favicon(params: dict) -> dict:
    """调用 Icon Horse 获取网站 favicon（免费，无需 API Key）"""
    import requests
    domain = params.get("domain", "")
    if not domain:
        return {"success": False, "error": "缺少域名"}
    try:
        url = f"https://icon.horse/icon/{domain}"
        return {
            "success": True,
            "data": {
                "favicon_url": url,
                "domain": domain
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 音乐娱乐类 ──────────────────────────────────────────────────

async def _call_lyrics(params: dict) -> dict:
    """调用 Lyrics.ovh 搜索歌词（免费，无需 API Key）"""
    import requests
    artist = params.get("artist", "")
    title = params.get("title", "")
    if not artist or not title:
        return {"success": False, "error": "缺少歌手或歌曲名"}
    try:
        url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            lyrics = data.get("lyrics", "")
            if lyrics:
                return {
                    "success": True,
                    "data": {
                        "artist": artist,
                        "title": title,
                        "lyrics": lyrics[:500]
                    }
                }
        return {"success": False, "error": "未找到歌词"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_itunes_music(params: dict) -> dict:
    """调用 iTunes Search API 搜索音乐（免费，无需 API Key）"""
    import requests
    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "缺少搜索关键词"}
    try:
        url = "https://itunes.apple.com/search"
        resp = requests.get(url, params={
            "term": query,
            "media": "music",
            "limit": 5
        }, timeout=10)
        data = resp.json()
        results = data.get("results", [])
        if results:
            songs = []
            for r in results[:5]:
                songs.append({
                    "track_name": r.get("trackName", ""),
                    "artist_name": r.get("artistName", ""),
                    "album_name": r.get("collectionName", ""),
                    "release_date": r.get("releaseDate", ""),
                    "genre": r.get("primaryGenreName", ""),
                    "preview_url": r.get("previewUrl", "")
                })
            return {"success": True, "data": {"songs": songs, "result_count": data.get("resultCount", 0)}}
        return {"success": False, "error": "未找到音乐"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 趣味工具类 ──────────────────────────────────────────────────

async def _call_random_user(params: dict) -> dict:
    """调用 RandomUser.me 生成随机用户信息（免费，无需 API Key）"""
    import requests
    try:
        nationality = params.get("nationality", "")
        gender = params.get("gender", "")
        url = "https://randomuser.me/api/"
        req_params = {}
        if nationality:
            req_params["nat"] = nationality
        if gender:
            req_params["gender"] = gender
        resp = requests.get(url, params=req_params if req_params else None, timeout=10)
        data = resp.json()
        results = data.get("results", [])
        if results:
            user = results[0]
            name = user.get("name", {})
            location = user.get("location", {})
            return {
                "success": True,
                "data": {
                    "name": f"{name.get('title', '')} {name.get('first', '')} {name.get('last', '')}".strip(),
                    "gender": user.get("gender", ""),
                    "email": user.get("email", ""),
                    "phone": user.get("phone", ""),
                    "country": location.get("country", ""),
                    "city": location.get("city", ""),
                    "username": user.get("login", {}).get("username", ""),
                    "dob": user.get("dob", {}).get("date", ""),
                    "age": user.get("dob", {}).get("age", 0),
                    "picture": user.get("picture", {}).get("large", "")
                }
            }
        return {"success": False, "error": "生成随机用户失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_agify(params: dict) -> dict:
    """调用 Agify.io 根据名字预测年龄（免费，无需 API Key）"""
    import requests
    name = params.get("name", "")
    if not name:
        return {"success": False, "error": "缺少名字"}
    try:
        url = "https://api.agify.io"
        resp = requests.get(url, params={"name": name}, timeout=10)
        data = resp.json()
        return {
            "success": True,
            "data": {
                "name": data.get("name", name),
                "age": data.get("age", 0),
                "count": data.get("count", 0),
                "country": data.get("country_id", "")
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_genderize(params: dict) -> dict:
    """调用 Genderize.io 根据名字预测性别（免费，无需 API Key）"""
    import requests
    name = params.get("name", "")
    if not name:
        return {"success": False, "error": "缺少名字"}
    try:
        url = "https://api.genderize.io"
        resp = requests.get(url, params={"name": name}, timeout=10)
        data = resp.json()
        return {
            "success": True,
            "data": {
                "name": data.get("name", name),
                "gender": data.get("gender", "unknown"),
                "probability": data.get("probability", 0),
                "count": data.get("count", 0)
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_nationalize(params: dict) -> dict:
    """调用 Nationalize.io 根据名字预测国籍（免费，无需 API Key）"""
    import requests
    name = params.get("name", "")
    if not name:
        return {"success": False, "error": "缺少名字"}
    try:
        url = "https://api.nationalize.io"
        resp = requests.get(url, params={"name": name}, timeout=10)
        data = resp.json()
        countries = data.get("country", [])
        return {
            "success": True,
            "data": {
                "name": data.get("name", name),
                "countries": [{"country_id": c.get("country_id", ""), "probability": c.get("probability", 0)} for c in countries[:3]],
                "count": data.get("count", 0)
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_kanye_quote(params: dict) -> dict:
    """调用 Kanye.rest 获取 Kanye West 名言（免费，无需 API Key）"""
    import requests
    try:
        url = "https://api.kanye.rest/"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("quote"):
            return {
                "success": True,
                "data": {
                    "quote": data.get("quote", ""),
                    "author": "Kanye West"
                }
            }
        return {"success": False, "error": "获取名言失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_chuck_norris(params: dict) -> dict:
    """调用 Chuck Norris API 获取 Chuck Norris 笑话（免费，无需 API Key）"""
    import requests
    try:
        category = params.get("category", "")
        url = "https://api.chucknorris.io/jokes/random"
        req_params = {}
        if category:
            req_params["category"] = category
        resp = requests.get(url, params=req_params if req_params else None, timeout=10)
        data = resp.json()
        if data.get("value"):
            return {
                "success": True,
                "data": {
                    "joke": data.get("value", ""),
                    "categories": data.get("categories", []),
                    "icon_url": data.get("icon_url", "")
                }
            }
        return {"success": False, "error": "获取笑话失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _call_advice_slip(params: dict) -> dict:
    """调用 Advice Slip API 获取随机建议（免费，无需 API Key）"""
    import requests
    try:
        query = params.get("query", "")
        if query:
            url = "https://api.adviceslip.com/advice/search/" + query
        else:
            url = "https://api.adviceslip.com/advice"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if query:
            slips = data.get("slips", [])
            if slips:
                return {
                    "success": True,
                    "data": {
                        "advice": slips[0].get("advice", ""),
                        "id": slips[0].get("id", ""),
                        "total_results": len(slips)
                    }
                }
        else:
            slip = data.get("slip", {})
            if slip.get("advice"):
                return {
                    "success": True,
                    "data": {
                        "advice": slip.get("advice", ""),
                        "id": slip.get("id", "")
                    }
                }
        return {"success": False, "error": "获取建议失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 结果格式化 ──────────────────────────────────────────────────

def _format_tool_result(tool_name: str, data: dict) -> str:
    """将工具调用结果格式化为文本"""
    if not data:
        return ""

    if tool_name == "get_weather_forecast":
        return f"[天气信息（{data.get('city', '')}）]\n{data.get('weather', '')}"

    elif tool_name == "get_exchange_rates":
        rates = data.get("rates", {})
        parts = [f"[汇率（基准：{data.get('base', '')}，日期：{data.get('date', '')}）]"]
        for currency, rate in rates.items():
            parts.append(f"  {currency}: {rate}")
        return "\n".join(parts)

    elif tool_name == "get_holidays":
        holidays = data.get("holidays", [])
        parts = [f"[节假日（{data.get('country', '')} {data.get('year', '')}）]"]
        for h in holidays[:10]:
            parts.append(f"  {h.get('date', '')}: {h.get('name', '')}")
        return "\n".join(parts)

    elif tool_name == "get_food_nutrition":
        return (
            f"[食物营养（{data.get('name', '')}）]\n"
            f"  热量：{data.get('calories', '')} kcal/100g\n"
            f"  蛋白质：{data.get('protein', '')}g\n"
            f"  脂肪：{data.get('fat', '')}g\n"
            f"  碳水：{data.get('carbs', '')}g"
        )

    elif tool_name == "calculate_bmi":
        return (
            f"[BMI 评估]\n"
            f"  BMI: {data.get('bmi', '')}（{data.get('category', '')}）\n"
            f"  身高: {data.get('height', '')}cm, 体重: {data.get('weight', '')}kg"
        )

    elif tool_name == "get_wger_exercises":
        exercises = data.get("exercises", [])
        parts = [f"[运动推荐]"]
        for ex in exercises:
            parts.append(f"  - {ex.get('name', '')}: {ex.get('description', '')}")
        return "\n".join(parts)

    elif tool_name == "search_open_library":
        books = data.get("books", [])
        parts = [f"[图书推荐]"]
        for b in books:
            parts.append(f"  - 《{b.get('title', '')}》 作者：{b.get('author', '')}（{b.get('year', '')}）")
        return "\n".join(parts)

    elif tool_name == "get_city_intro":
        return f"[城市介绍（{data.get('city', '')}）]\n{data.get('introduction', '')}"

    elif tool_name == "get_wikipedia_summary":
        return f"[百科（{data.get('title', '')}）]\n{data.get('summary', '')}"

    elif tool_name == "get_country_info":
        return (
            f"[国家信息（{data.get('name', '')}）]\n"
            f"  首都：{data.get('capital', '')}\n"
            f"  地区：{data.get('region', '')}\n"
            f"  人口：{data.get('population', 0):,}\n"
            f"  面积：{data.get('area', 0):,} km²\n"
            f"  语言：{', '.join(data.get('languages', []))}\n"
            f"  货币：{', '.join(data.get('currencies', []))}"
        )

    elif tool_name == "get_themealdb":
        ings = data.get("ingredients", [])
        return (
            f"[食谱（{data.get('name', '')}）]\n"
            f"  类别：{data.get('category', '')}，{data.get('area', '')}风味\n"
            f"  食材：{', '.join(ings[:5])}\n"
            f"  做法：{data.get('instructions', '')}"
        )

    elif tool_name == "get_cocktail":
        ings = data.get("ingredients", [])
        return (
            f"[鸡尾酒（{data.get('name', '')}）]\n"
            f"  类别：{data.get('category', '')}，{data.get('alcoholic', '')}\n"
            f"  杯具：{data.get('glass', '')}\n"
            f"  配料：{', '.join(ings)}\n"
            f"  调制：{data.get('instructions', '')}"
        )

    elif tool_name == "get_joke":
        if data.get("setup"):
            return f"[笑话]\n  {data.get('setup', '')}\n  {data.get('delivery', '')}"
        else:
            return f"[笑话]\n  {data.get('joke', '')}"

    elif tool_name == "get_quote":
        return f"[名言]\n  \"{data.get('content', '')}\"\n  —— {data.get('author', '')}"

    elif tool_name == "get_bored_activity":
        return (
            f"[活动建议]\n"
            f"  活动：{data.get('activity', '')}\n"
            f"  类型：{data.get('type', '')}\n"
            f"  人数：{data.get('participants', '')}"
        )

    elif tool_name == "get_hn_top_stories":
        stories = data.get("stories", [])
        parts = ["[Hacker News 科技头条]"]
        for i, s in enumerate(stories, 1):
            parts.append(f"  {i}. {s.get('title', '')}（{s.get('score', 0)}分）")
        return "\n".join(parts)

    elif tool_name == "get_ip_info":
        return (
            f"[IP 信息]\n"
            f"  IP：{data.get('ip', '')}\n"
            f"  位置：{data.get('country', '')} {data.get('region', '')} {data.get('city', '')}\n"
            f"  时区：{data.get('timezone', '')}\n"
            f"  ISP：{data.get('isp', '')}"
        )

    elif tool_name == "get_dog_image":
        return f"[狗狗图片]\n  {data.get('image_url', '')}"

    elif tool_name == "get_cat_fact":
        return f"[猫咪趣闻]\n  {data.get('fact', '')}"

    elif tool_name == "get_fox_image":
        return f"[狐狸图片]\n  {data.get('image_url', '')}"

    elif tool_name == "get_duck_image":
        return f"[鸭子图片]\n  {data.get('image_url', '')}"

    elif tool_name == "get_cat_image":
        return f"[猫咪图片]\n  {data.get('image_url', '')}"

    elif tool_name == "get_dog_fact":
        return f"[狗狗趣闻]\n  {data.get('fact', '')}"

    elif tool_name == "get_shibe_image":
        urls = data.get('image_urls', [])
        return f"[柴犬图片]\n  {urls[0] if urls else ''}"

    elif tool_name == "get_anime_quote":
        return (
            f"[动漫名言]\n"
            f"  「{data.get('quote', '')}」\n"
            f"  —— {data.get('character', '')}（{data.get('anime', '')}）"
        )

    elif tool_name == "get_studio_ghibli_films":
        films = data.get("films", [])
        parts = ["[吉卜力电影]"]
        for f in films[:3]:
            parts.append(f"  - {f.get('title', '')}（{f.get('original_title', '')}） 导演：{f.get('director', '')} {f.get('release_date', '')}年")
        return "\n".join(parts)

    elif tool_name == "get_waifu_image":
        return f"[动漫图片]\n  {data.get('image_url', '')}"

    elif tool_name == "get_color_palette":
        colors = data.get("colors", [])
        return f"[配色方案]\n  {'  '.join(colors)}"

    elif tool_name == "get_placeholder_image":
        return f"[占位图片]\n  {data.get('image_url', '')}（{data.get('width', '')}x{data.get('height', '')}）"

    elif tool_name == "get_art_institute_chicago":
        artworks = data.get("artworks", [])
        parts = ["[芝加哥艺术学院藏品]"]
        for a in artworks[:3]:
            parts.append(f"  - 《{a.get('title', '')}》  {a.get('artist', '')} {a.get('date', '')}")
        return "\n".join(parts)

    elif tool_name == "search_gutendex":
        books = data.get("books", [])
        parts = ["[古腾堡免费图书]"]
        for b in books[:3]:
            authors = ", ".join(b.get("authors", []))
            parts.append(f"  - 《{b.get('title', '')}》 作者：{authors}")
        return "\n".join(parts)

    elif tool_name == "get_bible_verse":
        return (
            f"[圣经经文 - {data.get('reference', '')}]\n"
            f"  {data.get('text', '')}\n"
            f"  （{data.get('translation', '')}）"
        )

    elif tool_name == "get_github_user":
        return (
            f"[GitHub 用户 - {data.get('username', '')}]\n"
            f"  昵称：{data.get('name', '')}\n"
            f"  简介：{data.get('bio', '')}\n"
            f"  粉丝：{data.get('followers', 0)}  关注：{data.get('following', 0)}  仓库：{data.get('public_repos', 0)}\n"
            f"  地点：{data.get('location', '')}"
        )

    elif tool_name == "search_npm_packages":
        packages = data.get("packages", [])
        parts = ["[npm 包搜索]"]
        for p in packages[:3]:
            parts.append(f"  - {p.get('name', '')}@{p.get('version', '')}：{p.get('description', '')[:80]}")
        return "\n".join(parts)

    elif tool_name == "get_favicon":
        return f"[网站 Favicon]\n  {data.get('favicon_url', '')}"

    elif tool_name == "search_lyrics":
        return (
            f"[歌词 - {data.get('artist', '')}《{data.get('title', '')}》]\n"
            f"  {data.get('lyrics', '')[:300]}..."
        )

    elif tool_name == "search_itunes_music":
        songs = data.get("songs", [])
        parts = ["[音乐搜索]"]
        for s in songs[:3]:
            parts.append(f"  - {s.get('artist_name', '')} - {s.get('track_name', '')}（{s.get('album_name', '')}）")
        return "\n".join(parts)

    elif tool_name == "get_random_user":
        return (
            f"[随机用户信息]\n"
            f"  姓名：{data.get('name', '')}\n"
            f"  性别：{data.get('gender', '')}  年龄：{data.get('age', 0)}\n"
            f"  邮箱：{data.get('email', '')}\n"
            f"  位置：{data.get('country', '')} {data.get('city', '')}\n"
            f"  用户名：{data.get('username', '')}"
        )

    elif tool_name == "get_age_by_name":
        return f"[年龄预测]\n  名字：{data.get('name', '')}  预测年龄：{data.get('age', 0)}岁  （样本数：{data.get('count', 0)}）"

    elif tool_name == "get_gender_by_name":
        prob = round(data.get('probability', 0) * 100, 1)
        return f"[性别预测]\n  名字：{data.get('name', '')}  预测性别：{data.get('gender', '')}  概率：{prob}%"

    elif tool_name == "get_nationality_by_name":
        countries = data.get("countries", [])
        parts = [f"[国籍预测 - {data.get('name', '')}]"]
        for c in countries[:3]:
            prob = round(c.get('probability', 0) * 100, 1)
            parts.append(f"  - {c.get('country_id', '')}：{prob}%")
        return "\n".join(parts)

    elif tool_name == "get_kanye_quote":
        return f"[Kanye 名言]\n  「{data.get('quote', '')}」\n  —— {data.get('author', '')}"

    elif tool_name == "get_chuck_norris_joke":
        return f"[Chuck Norris 笑话]\n  {data.get('joke', '')}"

    elif tool_name == "get_advice_slip":
        return f"[生活建议]\n  {data.get('advice', '')}"

    else:
        return f"[{tool_name}]\n{str(data)[:300]}"
