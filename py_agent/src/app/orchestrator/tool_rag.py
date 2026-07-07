"""
Tool RAG - 工具检索增强生成

核心设计：把每个外部 API 当作一个"文档"做 RAG。
每个工具构建包含【功能】【触发词】【适用场景】【参数格式】的语义索引文档。

检索策略：双路召回 + LLM Rerank
1. 向量检索（Chroma + embedding）
2. BM25 关键词检索
3. 融合排序后用 LLM Rerank 精排

降级策略：
- 向量检索失败 → 降级为关键词匹配（triggers 字段）
- LLM 返回空/解析失败 → ranked_tools=[] → tool_executor 不执行任何工具
"""

import math
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
from langchain_chroma import Chroma
from langchain_core.documents import Document

# ─── 工具文档定义 ──────────────────────────────────────────────────
# 每个工具一个 Document，page_content 是语义描述（用于 embedding 检索）
# metadata 包含工具名、参数 Schema、触发词等

TOOL_DOCS: List[Document] = [
    Document(
        page_content="""
        【功能】查询指定城市未来7天天气预报，包括温度、天气状况、降水概率，基于 Open-Meteo 免费API
        【触发词】天气、气温、温度、下雨、晴天、阴天、目的地、旅行、旅游、出行、气候
        【适用场景】任何涉及城市/地点的计划都应该调用此工具，旅行计划必备
        【注意】即使用户没提"天气"，只要涉及目的地/地点/城市，天气就是必要信息
        【参数】city(必填,城市名,如"杭州")
        """,
        metadata={
            "tool_name": "get_weather_forecast",
            "required_slots": ["city"],
            "optional_slots": [],
            "triggers": ["天气", "气温", "温度", "下雨", "晴天", "阴天", "目的地", "旅行", "旅游", "出行", "气候"],
        },
    ),
    Document(
        page_content="""
        【功能】获取货币汇率信息，基于 Frankfurter 免费API，支持常用货币对照
        【触发词】汇率、兑换、人民币、美元、日元、欧元、旅行费用、货币
        【适用场景】旅行计划中涉及外币兑换、费用预算，或用户直接问汇率
        【参数】base_currency(可选,基准货币代码,默认"CNY")
        """,
        metadata={
            "tool_name": "get_exchange_rates",
            "required_slots": [],
            "optional_slots": ["base_currency"],
            "triggers": ["汇率", "兑换", "人民币", "美元", "日元", "欧元", "货币", "费用"],
        },
    ),
    Document(
        page_content="""
        【功能】获取国家法定节假日信息，基于 Nager.Date 免费API，支持多国节假日查询
        【触发词】节假日、放假、假期、国庆、春节、中秋、端午、周末、法定假日
        【适用场景】旅行/学习/工作计划中需要考虑节假日安排
        【参数】country(可选,国家代码,默认"CN"), year(可选,年份,默认今年)
        """,
        metadata={
            "tool_name": "get_holidays",
            "required_slots": [],
            "optional_slots": ["country", "year"],
            "triggers": ["节假日", "放假", "假期", "国庆", "春节", "中秋", "端午", "周末", "法定假日"],
        },
    ),
    Document(
        page_content="""
        【功能】查询食物营养成分（热量、蛋白质、脂肪、碳水等），基于 Open Food Facts 免费数据库
        【触发词】热量、卡路里、营养、蛋白质、脂肪、碳水、食物、饮食、减肥、健身餐
        【适用场景】健康/减肥/健身类计划中需要计算食物热量或营养摄入
        【注意】食物名需要是具体的食物名称（如"鸡胸肉"、"西兰花"），不能是泛化描述
        【参数】query(必填,食物名称,如"鸡胸肉")
        """,
        metadata={
            "tool_name": "get_food_nutrition",
            "required_slots": ["query"],
            "optional_slots": [],
            "triggers": ["热量", "卡路里", "营养", "蛋白质", "脂肪", "碳水", "食物", "饮食", "减肥", "健身餐", "饮食计划"],
        },
    ),
    Document(
        page_content="""
        【功能】从 wger 运动数据库搜索运动/锻炼动作，包含动作描述、肌肉群等信息，免费API
        【触发词】运动、锻炼、健身、训练、动作、肌肉、胸肌、腹肌、深蹲、俯卧撑
        【适用场景】健身/运动类计划中需要推荐具体训练动作
        【参数】query(必填,运动名称或肌肉群,如"胸肌"或"俯卧撑")
        """,
        metadata={
            "tool_name": "get_wger_exercises",
            "required_slots": ["query"],
            "optional_slots": [],
            "triggers": ["运动", "锻炼", "健身", "训练", "动作", "肌肉", "胸肌", "腹肌", "深蹲", "俯卧撑", "跑步"],
        },
    ),
    Document(
        page_content="""
        【功能】搜索 Open Library 图书数据库，获取书名、作者、出版信息，免费图书API
        【触发词】图书、书籍、读书、阅读、学习、教材、参考书、考研
        【适用场景】学习/阅读类计划中需要推荐相关书籍
        【参数】query(必填,书名或主题关键词,如"Python编程")
        """,
        metadata={
            "tool_name": "search_open_library",
            "required_slots": ["query"],
            "optional_slots": [],
            "triggers": ["图书", "书籍", "读书", "阅读", "学习", "教材", "参考书", "考研", "英语", "数学"],
        },
    ),
    Document(
        page_content="""
        【功能】计算 BMI 身体质量指数，评估体重是否健康
        【触发词】BMI、体重、身高、肥胖、健康体重、减肥
        【适用场景】健康/减肥类计划中需要评估用户体重状况
        【参数】height_cm(必填,身高厘米), weight_kg(必填,体重公斤)
        """,
        metadata={
            "tool_name": "calculate_bmi",
            "required_slots": ["height_cm", "weight_kg"],
            "optional_slots": [],
            "triggers": ["BMI", "体重", "身高", "肥胖", "健康体重", "减肥"],
        },
    ),
    Document(
        page_content="""
        【功能】获取城市介绍和背景知识，基于 Wikipedia 免费API
        【触发词】城市介绍、城市简介、目的地介绍、旅游攻略、城市背景
        【适用场景】旅行计划中了解目的地城市基本情况
        【参数】city(必填,城市名,如"北京")
        """,
        metadata={
            "tool_name": "get_city_intro",
            "required_slots": ["city"],
            "optional_slots": [],
            "triggers": ["城市介绍", "城市简介", "目的地介绍", "旅游攻略", "城市背景", "景点", "游玩"],
        },
    ),
    Document(
        page_content="""
        【功能】获取指定时区的当前日期和时间
        【触发词】时间、日期、几点、现在、时区、几号
        【适用场景】用户问当前时间、需要确定计划开始日期、旅行日期
        【参数】timezone(可选,时区,如"Asia/Shanghai")
        """,
        metadata={
            "tool_name": "get_time",
            "required_slots": [],
            "optional_slots": ["timezone"],
            "triggers": ["时间", "日期", "几点", "现在", "时区", "几号", "今天"],
        },
    ),
    Document(
        page_content="""
        【功能】获取 Wikipedia 摘要信息，用于查询人物、地点、概念的介绍，免费百科API
        【触发词】百科、介绍、是什么、简介、Wikipedia、了解
        【适用场景】用户想了解某个概念/人物/地点的背景知识
        【参数】query(必填,查询主题)
        """,
        metadata={
            "tool_name": "get_wikipedia_summary",
            "required_slots": ["query"],
            "optional_slots": [],
            "triggers": ["百科", "介绍", "是什么", "简介", "了解", "Wikipedia", "维基"],
        },
    ),
    Document(
        page_content="""
        【功能】搜索 TheMealDB 食谱数据库，获取菜品做法和食材，免费食谱API
        【触发词】食谱、菜谱、做法、烹饪、做菜、美食、料理
        【适用场景】美食/烹饪类计划中需要推荐具体菜品做法
        【参数】query(必填,菜品名称或食材,如"红烧肉")
        """,
        metadata={
            "tool_name": "get_themealdb",
            "required_slots": ["query"],
            "optional_slots": [],
            "triggers": ["食谱", "菜谱", "做法", "烹饪", "做菜", "美食", "料理", "菜"],
        },
    ),
    Document(
        page_content="""
        【功能】获取每日活动建议（来自 Bored API），适合推荐休闲娱乐活动，免费API
        【触发词】活动、娱乐、休闲、玩、周末、放松、兴趣、无聊
        【适用场景】休闲娱乐类计划中推荐活动
        【参数】activity_type(可选,活动类型如"education","recreational","social")
        """,
        metadata={
            "tool_name": "get_bored_activity",
            "required_slots": [],
            "optional_slots": ["activity_type"],
            "triggers": ["活动", "娱乐", "休闲", "玩", "周末", "放松", "兴趣", "无聊"],
        },
    ),
    Document(
        page_content="""
        【功能】获取随机笑话，支持按类别筛选，来自 JokeAPI 免费接口
        【触发词】笑话、搞笑、幽默、开心、无聊、段子
        【适用场景】用户说无聊、想开心一下、定制娱乐类计划
        【参数】category(可选,笑话类别,默认"Any")
        """,
        metadata={
            "tool_name": "get_joke",
            "required_slots": [],
            "optional_slots": ["category"],
            "triggers": ["笑话", "搞笑", "幽默", "开心", "无聊", "段子"],
        },
    ),
    Document(
        page_content="""
        【功能】获取随机名言警句，来自 Quotable 免费名言API
        【触发词】名言、警句、格言、励志、鸡汤、金句、座右铭
        【适用场景】学习/励志类计划中加入每日名言，或用户直接要名言
        【参数】tags(可选,标签如"inspirational","life","love")
        """,
        metadata={
            "tool_name": "get_quote",
            "required_slots": [],
            "optional_slots": ["tags"],
            "triggers": ["名言", "警句", "格言", "励志", "鸡汤", "金句", "座右铭"],
        },
    ),
    Document(
        page_content="""
        【功能】获取国家详细信息（首都、人口、面积、语言、货币等），来自 REST Countries 免费API
        【触发词】国家、首都、人口、国旗、国家介绍、国情
        【适用场景】旅行/学习计划中了解国家基本信息
        【参数】country(必填,国家名称,如"中国"或"Japan")
        """,
        metadata={
            "tool_name": "get_country_info",
            "required_slots": ["country"],
            "optional_slots": [],
            "triggers": ["国家", "首都", "人口", "国旗", "国家介绍", "国情"],
        },
    ),
    Document(
        page_content="""
        【功能】搜索鸡尾酒配方，获取配料和调制方法，来自 TheCocktailDB 免费API
        【触发词】鸡尾酒、调酒、饮品、酒吧、调酒配方
        【适用场景】娱乐/休闲类计划中推荐鸡尾酒
        【参数】query(必填,鸡尾酒名称,如"Margarita")
        """,
        metadata={
            "tool_name": "get_cocktail",
            "required_slots": ["query"],
            "optional_slots": [],
            "triggers": ["鸡尾酒", "调酒", "饮品", "酒吧", "调酒配方"],
        },
    ),
    Document(
        page_content="""
        【功能】获取 IP 地址对应的地理位置信息（国家、城市、经纬度、时区、ISP等），免费API
        【触发词】IP地址、IP查询、定位、地理位置、查IP
        【适用场景】用户查询IP归属地或网络相关问题
        【参数】ip(可选,IP地址,不传则查询请求者IP)
        """,
        metadata={
            "tool_name": "get_ip_info",
            "required_slots": [],
            "optional_slots": ["ip"],
            "triggers": ["IP", "ip", "地址", "定位", "查IP", "IP地址"],
        },
    ),
    Document(
        page_content="""
        【功能】获取随机狗狗图片，来自 Dog CEO 免费API
        【触发词】狗狗、小狗、狗、宠物、汪星人、dog
        【适用场景】娱乐休闲、宠物相关计划，用户想看狗狗图片
        【参数】breed(可选,犬种,如"husky")
        """,
        metadata={
            "tool_name": "get_dog_image",
            "required_slots": [],
            "optional_slots": ["breed"],
            "triggers": ["狗狗", "小狗", "狗", "宠物", "汪星人", "dog"],
        },
    ),
    Document(
        page_content="""
        【功能】获取猫咪冷知识趣闻，来自 Cat Facts 免费API
        【触发词】猫咪、猫、小猫、宠物、喵星人、cat、冷知识
        【适用场景】娱乐休闲、宠物相关计划，用户想了解猫咪知识
        """,
        metadata={
            "tool_name": "get_cat_fact",
            "required_slots": [],
            "optional_slots": [],
            "triggers": ["猫咪", "猫", "小猫", "宠物", "喵星人", "cat", "冷知识"],
        },
    ),
    Document(
        page_content="""
        【功能】获取 Hacker News 科技头条新闻，来自 Firebase 官方免费API
        【触发词】科技新闻、HN、黑客新闻、技术头条、科技资讯、IT新闻
        【适用场景】用户想了解最新科技动态、技术类资讯
        【参数】limit(可选,返回条数,默认5)
        """,
        metadata={
            "tool_name": "get_hn_top_stories",
            "required_slots": [],
            "optional_slots": ["limit"],
            "triggers": ["科技新闻", "HN", "黑客新闻", "技术头条", "科技资讯", "IT新闻", "科技"],
        },
    ),
    Document(
        page_content="""
        【功能】获取随机狐狸图片，来自 RandomFox 免费API
        【触发词】狐狸、fox、小狐狸、动物图片、萌宠
        【适用场景】娱乐休闲、宠物相关，用户想看狐狸图片
        【参数】无
        """,
        metadata={
            "tool_name": "get_fox_image",
            "required_slots": [],
            "optional_slots": [],
            "triggers": ["狐狸", "fox", "小狐狸", "动物", "萌宠", "图片"],
        },
    ),
    Document(
        page_content="""
        【功能】获取随机鸭子图片，来自 RandomDuck 免费API
        【触发词】鸭子、duck、小鸭、动物图片、萌宠
        【适用场景】娱乐休闲、宠物相关，用户想看鸭子图片
        【参数】无
        """,
        metadata={
            "tool_name": "get_duck_image",
            "required_slots": [],
            "optional_slots": [],
            "triggers": ["鸭子", "duck", "小鸭", "动物", "萌宠", "图片"],
        },
    ),
    Document(
        page_content="""
        【功能】获取随机猫咪图片，支持按标签筛选和GIF，来自 Cataas 免费API
        【触发词】猫咪、猫、小猫、cat、猫咪图片、猫图
        【适用场景】娱乐休闲、宠物相关，用户想看猫咪图片
        【参数】tag(可选,标签如"cute"), gif(可选,是否GIF)
        """,
        metadata={
            "tool_name": "get_cat_image",
            "required_slots": [],
            "optional_slots": ["tag", "gif"],
            "triggers": ["猫咪", "猫", "小猫", "cat", "喵星人", "宠物", "图片"],
        },
    ),
    Document(
        page_content="""
        【功能】获取狗狗冷知识趣闻，来自 Dog Facts 免费API
        【触发词】狗狗、狗、小狗、dog、狗狗趣闻、宠物知识
        【适用场景】娱乐休闲、宠物相关，用户想了解狗狗知识
        【参数】无
        """,
        metadata={
            "tool_name": "get_dog_fact",
            "required_slots": [],
            "optional_slots": [],
            "triggers": ["狗狗", "狗", "小狗", "dog", "汪星人", "宠物", "冷知识", "趣闻"],
        },
    ),
    Document(
        page_content="""
        【功能】获取随机柴犬/猫咪/小鸟图片，来自 Shibe.Online 免费API
        【触发词】柴犬、shiba、柴犬图片、鸟、小鸟、鹦鹉
        【适用场景】娱乐休闲、宠物相关，用户想看柴犬或小鸟图片
        【参数】animal(可选,动物类型:shibes/cats/birds,默认shibes), count(可选,数量)
        """,
        metadata={
            "tool_name": "get_shibe_image",
            "required_slots": [],
            "optional_slots": ["animal", "count"],
            "triggers": ["柴犬", "shiba", "狗狗", "鸟", "小鸟", "鹦鹉", "宠物", "图片"],
        },
    ),
    Document(
        page_content="""
        【功能】获取随机动漫名言，包含动漫名、角色和台词，来自 AnimeChan 免费API
        【触发词】动漫、动画、anime、动漫名言、台词、二次元
        【适用场景】动漫爱好者、娱乐休闲、二次元相关计划
        【参数】无
        """,
        metadata={
            "tool_name": "get_anime_quote",
            "required_slots": [],
            "optional_slots": [],
            "triggers": ["动漫", "动画", "anime", "名言", "台词", "二次元", "番剧"],
        },
    ),
    Document(
        page_content="""
        【功能】获取吉卜力工作室电影信息，包括龙猫、千与千寻等经典动画，来自 Studio Ghibli API 免费接口
        【触发词】吉卜力、宫崎骏、龙猫、千与千寻、动画电影、studio ghibli
        【适用场景】动漫/电影爱好者计划、推荐经典动画电影
        【参数】query(可选,搜索关键词,不传则返回全部)
        """,
        metadata={
            "tool_name": "get_studio_ghibli_films",
            "required_slots": [],
            "optional_slots": ["query"],
            "triggers": ["吉卜力", "宫崎骏", "龙猫", "千与千寻", "动画", "电影", "ghibli"],
        },
    ),
    Document(
        page_content="""
        【功能】获取动漫风格女生图片，来自 Waifu.pics 免费API
        【触发词】动漫图片、waifu、二次元、动漫壁纸、动漫头像
        【适用场景】动漫爱好者、娱乐休闲、二次元相关
        【参数】category(可选,分类,默认waifu), nsfw(可选,是否NSFW,默认false)
        """,
        metadata={
            "tool_name": "get_waifu_image",
            "required_slots": [],
            "optional_slots": ["category", "nsfw"],
            "triggers": ["动漫图片", "waifu", "二次元", "壁纸", "头像", "动漫"],
        },
    ),
    Document(
        page_content="""
        【功能】自动生成配色方案，包含5种颜色的RGB和HEX值，来自 Colormind 免费API
        【触发词】配色、颜色、色彩、palette、设计、UI配色
        【适用场景】设计相关计划、需要配色方案、UI/UX设计
        【参数】model(可选,配色模型,默认default)
        """,
        metadata={
            "tool_name": "get_color_palette",
            "required_slots": [],
            "optional_slots": ["model"],
            "triggers": ["配色", "颜色", "色彩", "palette", "设计", "UI", "色板"],
        },
    ),
    Document(
        page_content="""
        【功能】生成占位图片，支持自定义尺寸、文字、颜色，来自 DummyImage 免费服务
        【触发词】占位图、placeholder、占位图片、设计原型、mockup
        【适用场景】设计/开发计划中需要占位图片
        【参数】width(可选,宽度,默认300), height(可选,高度,默认200), text(可选,文字), bg_color(可选,背景色), text_color(可选,文字色)
        """,
        metadata={
            "tool_name": "get_placeholder_image",
            "required_slots": [],
            "optional_slots": ["width", "height", "text", "bg_color", "text_color"],
            "triggers": ["占位图", "placeholder", "占位", "设计", "原型", "mockup", "图片"],
        },
    ),
    Document(
        page_content="""
        【功能】搜索芝加哥艺术学院馆藏艺术品，获取作品名、艺术家、年代和图片，免费API
        【触发词】艺术、艺术品、芝加哥艺术学院、油画、名画、艺术欣赏
        【适用场景】艺术相关计划、艺术欣赏、博物馆游览
        【参数】query(可选,搜索关键词), limit(可选,返回数量,默认3)
        """,
        metadata={
            "tool_name": "get_art_institute_chicago",
            "required_slots": [],
            "optional_slots": ["query", "limit"],
            "triggers": ["艺术", "艺术品", "名画", "油画", "博物馆", "艺术欣赏", "画作"],
        },
    ),
    Document(
        page_content="""
        【功能】搜索古腾堡计划免费公版图书，包含大量经典文学作品，Gutendex 免费API
        【触发词】古腾堡、公版书、免费图书、经典文学、免费电子书、gutenberg
        【适用场景】学习/阅读计划中推荐免费经典书籍
        【参数】query(必填,搜索关键词)
        """,
        metadata={
            "tool_name": "search_gutendex",
            "required_slots": ["query"],
            "optional_slots": [],
            "triggers": ["古腾堡", "公版书", "免费图书", "经典文学", "电子书", "gutenberg", "免费书"],
        },
    ),
    Document(
        page_content="""
        【功能】查询圣经经文，支持多种译本，来自 Bible API 免费接口
        【触发词】圣经、bible、经文、基督教、诗篇、箴言
        【适用场景】宗教学习、心灵成长相关计划
        【参数】reference(可选,经文参考,默认John 3:16), translation(可选,译本,默认bbe)
        """,
        metadata={
            "tool_name": "get_bible_verse",
            "required_slots": [],
            "optional_slots": ["reference", "translation"],
            "triggers": ["圣经", "bible", "经文", "基督教", "诗篇", "箴言", "信仰"],
        },
    ),
    Document(
        page_content="""
        【功能】查询 GitHub 用户信息，获取粉丝、仓库、简介等公开数据，GitHub 公开API无需Key
        【触发词】github、GitHub用户、开发者、程序员、开源
        【适用场景】开发者相关计划、了解某位开发者
        【参数】username(必填,GitHub用户名)
        """,
        metadata={
            "tool_name": "get_github_user",
            "required_slots": ["username"],
            "optional_slots": [],
            "triggers": ["github", "GitHub", "开发者", "程序员", "开源", "用户", "github用户"],
        },
    ),
    Document(
        page_content="""
        【功能】搜索 npm 包，获取包名、版本、描述等信息，npm 官方免费API
        【触发词】npm、node.js、前端包、javascript包、js库
        【适用场景】前端/Node.js开发计划中查找相关包
        【参数】query(必填,搜索关键词)
        """,
        metadata={
            "tool_name": "search_npm_packages",
            "required_slots": ["query"],
            "optional_slots": [],
            "triggers": ["npm", "node.js", "前端", "javascript", "js库", "包", "nodejs"],
        },
    ),
    Document(
        page_content="""
        【功能】获取任意网站的 favicon 图标，来自 Icon Horse 免费API
        【触发词】favicon、网站图标、网站logo、图标
        【适用场景】开发/设计相关计划中需要网站图标
        【参数】domain(必填,网站域名,如google.com)
        """,
        metadata={
            "tool_name": "get_favicon",
            "required_slots": ["domain"],
            "optional_slots": [],
            "triggers": ["favicon", "网站图标", "图标", "logo", "网站"],
        },
    ),
    Document(
        page_content="""
        【功能】搜索歌曲歌词，输入歌手和歌名即可获取歌词，Lyrics.ovh 免费API
        【触发词】歌词、lyrics、歌曲歌词、找歌词、音乐歌词
        【适用场景】音乐相关计划、用户想找某首歌的歌词
        【参数】artist(必填,歌手名), title(必填,歌曲名)
        """,
        metadata={
            "tool_name": "search_lyrics",
            "required_slots": ["artist", "title"],
            "optional_slots": [],
            "triggers": ["歌词", "lyrics", "歌曲", "音乐", "找歌词", "歌"],
        },
    ),
    Document(
        page_content="""
        【功能】搜索 iTunes 音乐库，获取歌曲、专辑、歌手信息，Apple 官方免费API
        【触发词】音乐、歌曲、itunes、苹果音乐、找歌、音乐搜索
        【适用场景】音乐相关计划、推荐歌曲、查找音乐
        【参数】query(必填,搜索关键词)
        """,
        metadata={
            "tool_name": "search_itunes_music",
            "required_slots": ["query"],
            "optional_slots": [],
            "triggers": ["音乐", "歌曲", "itunes", "苹果音乐", "找歌", "音乐搜索", "歌"],
        },
    ),
    Document(
        page_content="""
        【功能】生成随机用户信息，包含姓名、邮箱、电话、地址、头像等完整信息，RandomUser.me 免费API
        【触发词】随机用户、测试数据、假数据、生成用户、mock数据
        【适用场景】开发测试需要mock数据、生成测试用户
        【参数】nationality(可选,国籍), gender(可选,性别)
        """,
        metadata={
            "tool_name": "get_random_user",
            "required_slots": [],
            "optional_slots": ["nationality", "gender"],
            "triggers": ["随机用户", "测试数据", "假数据", "mock", "生成用户", "测试"],
        },
    ),
    Document(
        page_content="""
        【功能】根据名字预测年龄，基于海量统计数据，Agify.io 免费API
        【触发词】年龄预测、猜年龄、名字年龄、agify
        【适用场景】趣味娱乐、根据名字猜年龄
        【参数】name(必填,名字)
        """,
        metadata={
            "tool_name": "get_age_by_name",
            "required_slots": ["name"],
            "optional_slots": [],
            "triggers": ["年龄", "猜年龄", "预测年龄", "名字", "agify", "趣味"],
        },
    ),
    Document(
        page_content="""
        【功能】根据名字预测性别和概率，基于海量统计数据，Genderize.io 免费API
        【触发词】性别预测、猜性别、名字性别、genderize
        【适用场景】趣味娱乐、根据名字猜性别
        【参数】name(必填,名字)
        """,
        metadata={
            "tool_name": "get_gender_by_name",
            "required_slots": ["name"],
            "optional_slots": [],
            "triggers": ["性别", "猜性别", "预测性别", "名字", "genderize", "趣味"],
        },
    ),
    Document(
        page_content="""
        【功能】根据名字预测国籍和概率，基于海量统计数据，Nationalize.io 免费API
        【触发词】国籍预测、猜国籍、名字国籍、nationalize
        【适用场景】趣味娱乐、根据名字猜国籍
        【参数】name(必填,名字)
        """,
        metadata={
            "tool_name": "get_nationality_by_name",
            "required_slots": ["name"],
            "optional_slots": [],
            "triggers": ["国籍", "猜国籍", "预测国籍", "名字", "nationalize", "趣味"],
        },
    ),
    Document(
        page_content="""
        【功能】获取 Kanye West 随机名言，Kanye.rest 免费API
        【触发词】kanye、侃爷、坎耶、名人名言、kanye west
        【适用场景】娱乐、趣味、名人名言
        【参数】无
        """,
        metadata={
            "tool_name": "get_kanye_quote",
            "required_slots": [],
            "optional_slots": [],
            "triggers": ["kanye", "侃爷", "坎耶", "名人名言", "kanye west", "趣味"],
        },
    ),
    Document(
        page_content="""
        【功能】获取 Chuck Norris 经典笑话，支持按类别筛选，Chuck Norris API 免费接口
        【触发词】chuck norris、查克·诺里斯、笑话、冷笑话、搞笑
        【适用场景】娱乐休闲、想找笑话开心一下
        【参数】category(可选,笑话类别)
        """,
        metadata={
            "tool_name": "get_chuck_norris_joke",
            "required_slots": [],
            "optional_slots": ["category"],
            "triggers": ["chuck norris", "查克", "笑话", "冷笑话", "搞笑", "幽默"],
        },
    ),
    Document(
        page_content="""
        【功能】获取随机生活建议/人生建议，支持关键词搜索，Advice Slip 免费API
        【触发词】建议、advice、生活建议、人生建议、忠告、建议搜索
        【适用场景】用户需要建议、生活/人生规划类问题
        【参数】query(可选,搜索关键词,不传则随机)
        """,
        metadata={
            "tool_name": "get_advice_slip",
            "required_slots": [],
            "optional_slots": ["query"],
            "triggers": ["建议", "advice", "生活建议", "人生建议", "忠告", "建议搜索"],
        },
    ),
]

# ─── 向量检索 ──────────────────────────────────────────────────────

_tool_vector_store: Optional[Chroma] = None


def _get_tool_vector_store() -> Chroma:
    """获取或创建工具文档的向量库（单例）"""
    global _tool_vector_store
    if _tool_vector_store is not None:
        return _tool_vector_store

    from app.common.llm_factory import get_embeddings
    import os

    db_path = "./chroma_db"
    os.makedirs(db_path, exist_ok=True)

    store = Chroma(
        collection_name="tool_rag_docs",
        persist_directory=db_path,
        embedding_function=get_embeddings(),
    )

    # 如果集合为空，初始化工具文档
    try:
        existing = store.get()
        if not existing or not existing.get("ids"):
            ids = [f"tool_{i}" for i in range(len(TOOL_DOCS))]
            store.add_documents(documents=TOOL_DOCS, ids=ids)
            print(f"[Tool RAG] 初始化 {len(TOOL_DOCS)} 个工具文档到向量库")
    except Exception as e:
        print(f"[WARN] Tool RAG 初始化失败: {e}")
        # 尝试直接添加
        try:
            ids = [f"tool_{i}" for i in range(len(TOOL_DOCS))]
            store.add_documents(documents=TOOL_DOCS, ids=ids)
        except Exception:
            pass

    _tool_vector_store = store
    return store


# ─── BM25 索引 ──────────────────────────────────────────────────

_bm25_index: Optional[Dict[str, Any]] = None


def _tokenize(text: str) -> List[str]:
    """简单中文分词：按字符 + 关键词提取"""
    text = text.lower()
    chars = list(re.sub(r'[^\w\u4e00-\u9fff]', '', text))
    words = re.findall(r'[\u4e00-\u9fff]{2,4}|[a-zA-Z]+', text)
    return list(set(chars + words))


def _build_bm25_index():
    """构建 BM25 索引"""
    global _bm25_index
    if _bm25_index is not None:
        return _bm25_index

    docs = []
    for i, doc in enumerate(TOOL_DOCS):
        text = doc.page_content + " " + " ".join(doc.metadata.get("triggers", []))
        tokens = _tokenize(text)
        docs.append({
            "id": i,
            "tokens": tokens,
            "doc": doc,
            "len": len(tokens)
        })

    N = len(docs)
    avgdl = sum(d["len"] for d in docs) / max(N, 1)

    df = defaultdict(int)
    for d in docs:
        for token in set(d["tokens"]):
            df[token] += 1

    idf = {}
    for token, freq in df.items():
        idf[token] = math.log((N - freq + 0.5) / (freq + 0.5) + 1)

    _bm25_index = {
        "docs": docs,
        "N": N,
        "avgdl": avgdl,
        "idf": idf,
        "k1": 1.5,
        "b": 0.75
    }
    return _bm25_index


def _bm25_search(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """BM25 关键词检索"""
    try:
        index = _build_bm25_index()
    except Exception:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scores = {}
    for i, doc in enumerate(index["docs"]):
        score = 0.0
        dl = doc["len"]
        for token in query_tokens:
            if token not in index["idf"]:
                continue
            tf = doc["tokens"].count(token)
            idf = index["idf"][token]
            k1 = index["k1"]
            b = index["b"]
            avgdl = index["avgdl"]
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * dl / max(avgdl, 1))
            score += idf * numerator / max(denominator, 1e-9)
        if score > 0:
            scores[i] = score

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    results = []
    for idx, score in ranked:
        doc = index["docs"][idx]["doc"]
        results.append({
            "doc": doc,
            "score": score,
            "rank": len(results) + 1
        })
    return results


# ─── 双路召回 + LLM Rerank ──────────────────────────────────────

def _hybrid_search(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """双路召回：向量 + BM25，按倒数融合法（RRF）融合"""
    vector_results = []
    try:
        store = _get_tool_vector_store()
        docs = store.similarity_search(query, k=top_k)
        for i, doc in enumerate(docs):
            vector_results.append({
                "doc": doc,
                "score": 1.0 / (i + 1),
                "rank": i + 1,
                "source": "vector"
            })
    except Exception as e:
        print(f"[WARN] Tool RAG 向量检索失败: {e}")

    bm25_results = _bm25_search(query, top_k=top_k)
    for r in bm25_results:
        r["score"] = 1.0 / (r["rank"] + 60)
        r["source"] = "bm25"

    fused = defaultdict(lambda: {"doc": None, "score": 0.0, "sources": []})
    for r in vector_results + bm25_results:
        name = r["doc"].metadata.get("tool_name", "")
        fused[name]["doc"] = r["doc"]
        fused[name]["score"] += r["score"]
        fused[name]["sources"].append(r["source"])

    sorted_tools = sorted(fused.values(), key=lambda x: x["score"], reverse=True)[:top_k]
    return sorted_tools


async def _llm_rerank(query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """LLM Rerank 精排：用 LLM 判断工具与计划摘要的相关性"""
    if not candidates:
        return []

    try:
        from app.common.llm_factory import get_llm
        llm = get_llm()
    except Exception as e:
        print(f"[WARN] Tool RAG LLM 不可用，跳过 rerank: {e}")
        return [_format_tool_result(c["doc"], c["score"]) for c in candidates[:top_k]]

    tools_desc = []
    for i, c in enumerate(candidates):
        doc = c["doc"]
        tools_desc.append(f"[{i+1}] {doc.metadata.get('tool_name')}\n    描述: {doc.page_content.strip()[:150]}")

    prompt = f"""你是一个工具选择专家。请根据用户的计划需求，从以下候选工具中选出最相关的 {min(top_k, len(candidates))} 个。

【计划需求】
{query}

【候选工具】
{chr(10).join(tools_desc)}

【输出要求】
只输出 JSON 数组，包含选中的工具编号（1-based）和相关性评分（0-10分），格式如下：
[{{"index": 1, "score": 9.5}}, {{"index": 3, "score": 8.2}}]

按相关性从高到低排序。只输出 JSON，不要其他文字。"""

    try:
        resp = await llm.ainvoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)

        import json
        results = json.loads(text)
        if not isinstance(results, list):
            raise ValueError("返回不是列表")

        reranked = []
        for item in results:
            idx = int(item.get("index", 0)) - 1
            if 0 <= idx < len(candidates):
                score = float(item.get("score", 0))
                reranked.append({
                    "doc": candidates[idx]["doc"],
                    "score": score,
                    "source": "llm_rerank"
                })

        reranked.sort(key=lambda x: x["score"], reverse=True)
        print(f"[Tool RAG] LLM Rerank 完成: {len(reranked)}/{len(candidates)} 个工具")
        return reranked[:top_k]

    except Exception as e:
        print(f"[WARN] Tool RAG LLM Rerank 失败，用双路召回结果: {e}")
        return candidates[:top_k]


def _format_tool_result(doc: Document, score: float = 0.0) -> Dict[str, Any]:
    """格式化工具结果"""
    return {
        "tool_name": doc.metadata.get("tool_name", ""),
        "required_slots": doc.metadata.get("required_slots", []),
        "optional_slots": doc.metadata.get("optional_slots", []),
        "triggers": doc.metadata.get("triggers", []),
        "description": doc.page_content.strip()[:200],
        "score": score,
    }


async def retrieve_relevant_tools(plan_summary: str, top_k: int = 7) -> List[Dict[str, Any]]:
    """
    从工具文档中检索与计划相关的工具（双路召回 + LLM Rerank）

    Args:
        plan_summary: 计划需求摘要
        top_k: 返回工具数量

    Returns:
        工具信息列表 [{tool_name, required_slots, optional_slots, triggers, score}]
    """
    if not plan_summary:
        return []

    try:
        # 1. 双路召回（向量 + BM25）
        candidates = _hybrid_search(plan_summary, top_k=max(top_k * 2, 10))
        print(f"[Tool RAG] 双路召回 {len(candidates)} 个候选工具")

        if not candidates:
            return []

        # 2. LLM Rerank 精排
        reranked = await _llm_rerank(plan_summary, candidates, top_k=top_k)

        # 3. 格式化输出
        tools = [_format_tool_result(r["doc"], r["score"]) for r in reranked]
        print(f"[Tool RAG] 最终返回 {len(tools)} 个相关工具")
        return tools

    except Exception as e:
        print(f"[WARN] Tool RAG 检索失败，降级为关键词匹配: {e}")
        return _fallback_keyword_match(plan_summary, top_k)


def _fallback_keyword_match(plan_summary: str, top_k: int = 7) -> List[Dict[str, Any]]:
    """
    降级方案：用触发词关键词匹配检索工具
    """
    if not plan_summary:
        return []

    text = plan_summary.lower()
    scored_tools = []

    for doc in TOOL_DOCS:
        triggers = doc.metadata.get("triggers", [])
        score = sum(1 for t in triggers if t in text)
        if score > 0:
            scored_tools.append({
                "tool_name": doc.metadata.get("tool_name", ""),
                "required_slots": doc.metadata.get("required_slots", []),
                "optional_slots": doc.metadata.get("optional_slots", []),
                "triggers": triggers,
                "description": doc.page_content.strip()[:200],
                "keyword_score": score,
            })

    scored_tools.sort(key=lambda x: x.get("keyword_score", 0), reverse=True)
    return scored_tools[:top_k]
