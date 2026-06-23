"""
计划生成协调器 - 根据用户意图调用对应的 MCP + Skills

提供以下功能：
1. detect_plan_type: 意图识别 + 多意图冲突处理
2. PlanInfoCollector: 状态机 + Redis 持久化
3. PlanInfoCollectorManager: 管理器（支持状态恢复）
4. API 选择策略: 智能选择 2-4 个 API
5. extract_info_from_input: LLM JSON mode + 规则 fallback
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

# 导入 MCP 工具
from app.common.mcp_tools import *

# 导入 Skills
from app.skills.plan_templates import (
    generate_learning_plan,
    generate_health_plan,
    generate_travel_plan,
    generate_work_plan,
    generate_finance_plan
)

# ─── 意图识别 ──────────────────────────────────────────────────

# 优先级列表（从高到低，长关键词优先）
PRIORITY_KEYWORDS = [
    # 学习计划
    ("学习计划", "learning"),
    ("学习", "learning"),
    ("编程", "learning"),
    ("python", "learning"),
    ("英语", "learning"),

    # 健康计划
    ("健康计划", "health"),
    ("减肥计划", "health"),
    ("健身计划", "health"),
    ("运动计划", "health"),
    ("饮食计划", "health"),
    ("健康", "health"),
    ("运动", "health"),
    ("减肥", "health"),
    ("健身", "health"),
    ("饮食", "health"),

    # 旅行计划
    ("旅行计划", "travel"),
    ("旅游计划", "travel"),
    ("旅行", "travel"),
    ("旅游", "travel"),
    ("出行", "travel"),
    ("度假", "travel"),

    # 财务计划
    ("财务计划", "finance"),
    ("存钱计划", "finance"),
    ("理财计划", "finance"),
    ("投资计划", "finance"),
    ("财务", "finance"),
    ("存钱", "finance"),
    ("理财", "finance"),
    ("投资", "finance"),

    # 工作计划（优先级最低）
    ("工作计划", "work"),
    ("项目计划", "work"),
    ("工作", "work"),
    ("项目", "work"),
    # 注意：不再使用通用关键词"计划"，避免与其他类型冲突
]

def detect_plan_type(message: str) -> Optional[str]:
    """检测用户想要创建的计划类型

    处理逻辑：
    1. 先检查是否是序号输入（1-5）
    2. 收集所有命中的类型
    3. 如果只有一个命中，直接返回
    4. 如果有多个命中，返回特殊标记（需要追问确认）
    5. 如果没有命中，返回 None（由调用方触发 LLM fallback）
    """
    if not message or not isinstance(message, str):
        return None

    message_lower = message.lower().strip()

    # 序号映射
    number_map = {
        "1": "learning",
        "2": "health",
        "3": "travel",
        "4": "work",
        "5": "finance",
    }

    # 检查是否是序号输入
    if message_lower in number_map:
        return number_map[message_lower]

    # 1. 收集所有命中的类型（按类型去重，保留最高优先级的关键词）
    matched_types: List[Tuple[str, str]] = []
    seen_plan_types = set()  # 用于去重
    for keyword, plan_type in PRIORITY_KEYWORDS:
        if keyword in message_lower and plan_type not in seen_plan_types:
            matched_types.append((keyword, plan_type))
            seen_plan_types.add(plan_type)

    # 2. 根据匹配结果决定下一步
    if len(matched_types) == 0:
        # 没有命中任何规则，返回 None（由调用方触发 LLM fallback）
        return None

    elif len(matched_types) == 1:
        # 只有一个命中，直接返回
        return matched_types[0][1]

    else:
        # 多个命中，需要追问用户确认
        # 提取所有命中的类型名称
        type_names = [t[1] for t in matched_types]

        # 返回特殊标记，表示需要追问
        return _create_ambiguous_result(type_names, matched_types)

def _create_ambiguous_result(type_names: List[str], matched_types: List[Tuple[str, str]]) -> str:
    """创建模糊匹配结果

    返回特殊格式的字符串，调用方检测到后应该追问用户
    """
    # 类型名称映射（中文）
    type_name_map = {
        "learning": "学习计划",
        "health": "健康计划",
        "travel": "旅行计划",
        "work": "工作计划",
        "finance": "财务计划",
    }

    # 构建追问文本
    type_names_cn = [type_name_map.get(t, t) for t in type_names]
    ambiguous_types = "、".join(type_names_cn)

    # 返回特殊标记（调用方需要检测这个格式）
    return f"__AMBIGUOUS__:{ambiguous_types}"

def handle_ambiguous_plan_type(message: str, session_id: str) -> str:
    """处理模糊的计划类型（需要追问用户）"""

    # 检测计划类型
    result = detect_plan_type(message)

    # 检查是否是模糊匹配
    if result and result.startswith("__AMBIGUOUS__:"):
        # 提取模糊类型
        ambiguous_types = result.split(":")[1]

        # 追问用户确认
        question = f"您好！我检测到您可能想制定多种计划：{ambiguous_types}。请问您想制定哪一种计划呢？"

        return question

    elif result is None:
        # 规则无法匹配，使用 LLM fallback
        return _detect_plan_type_with_llm(message, session_id)

    else:
        # 单一类型，直接返回
        return result

def _detect_plan_type_with_llm(message: str, session_id: str) -> str:
    """使用 LLM 做意图分类（fallback，仅在规则无法匹配时调用）"""

    # 构建提示词
    prompt = f"""用户说："{message}"

请判断用户想制定哪种计划类型。可选类型：
- learning（学习计划）：如学习编程、语言、技能等
- health（健康计划）：如减肥、健身、饮食等
- travel（旅行计划）：如旅游、出行、度假等
- work（工作计划）：如项目、任务、工作目标等
- finance（财务计划）：如存钱、理财、投资等

只返回类型名称（如 learning），不要其他内容。如果无法判断，返回 unknown。
"""

    try:
        # 调用 LLM（简化版，实际需要调用 LLM）
        # 这里返回 unknown，由调用方处理
        return "unknown"

    except Exception as e:
        # LLM 调用失败，返回 None
        print(f"[ERROR] LLM intent classification failed: {e}")
        return "unknown"

# ─── 信息收集器（状态机）──────────────────────────────────────

class PlanInfoCollector:
    """计划信息收集器（带序列化和时间戳）"""

    def __init__(self, plan_type: str):
        self.plan_type = plan_type
        self.required_fields = self._get_required_fields()
        self.optional_fields = self._get_optional_fields()
        self.collected_info: Dict[str, Any] = {}
        self.current_field_index = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.rag_context: Optional[str] = None  # RAG 上下文（知识库内容）
        self.context_summary: Optional[str] = None  # 上下文历史摘要
        self.selected_optional_apis: Optional[List[int]] = None  # 用户选择的可选API序号

    def _get_required_fields(self) -> List[str]:
        """获取必填字段（用于生成详细计划的核心信息 + API 所需参数）"""
        fields = {
            # 学习计划：5 个问题
            "learning": ["topic", "goal", "duration", "daily_hours", "level"],

            # 健康计划：8 个问题（需要身高体重计算 BMI，需要城市查天气）
            "health": ["goal", "duration", "activity_level", "height", "weight", "age", "gender", "location"],

            # 旅行计划：7 个问题（需要查询天气、汇率）
            "travel": ["destination", "days", "budget", "interests", "departure_date", "city", "target_currency"],

            # 工作计划：4 个问题
            "work": ["task", "duration", "team_size", "deadline"],

            # 财务计划：5 个问题（需要查询汇率）
            "finance": ["goal", "duration", "monthly_income", "current_savings", "target_currency"],
        }
        return fields.get(self.plan_type, [])

    def _get_optional_fields(self) -> List[str]:
        """获取可选字段"""
        fields = {
            "learning": [],
            "health": ["diet_preference", "medical_conditions"],
            "travel": ["accommodation_preference"],
            "work": [],
            "finance": ["investment_preference"],
        }
        return fields.get(self.plan_type, [])

    def get_next_question(self) -> Optional[str]:
        """获取下一个问题（单个字段）"""
        if self.current_field_index < len(self.required_fields):
            field = self.required_fields[self.current_field_index]
            return self._generate_question(field)
        return None  # 信息收集完毕

    def get_all_questions_once(self) -> Optional[str]:
        """一次性生成所有必填字段的问题"""
        if not self.required_fields:
            return None

        questions = []
        for i, field in enumerate(self.required_fields, 1):
            questions.append(f"{i}. {self._generate_question(field)}")

        return "\n\n".join(questions)

    def get_missing_fields(self) -> List[str]:
        """获取尚未收集的必填字段"""
        return self.required_fields[self.current_field_index:]

    def get_missing_questions(self) -> Optional[str]:
        """生成缺失字段的问题"""
        missing = self.get_missing_fields()
        if not missing:
            return None

        questions = []
        for i, field in enumerate(missing, 1):
            questions.append(f"{i}. {self._generate_question(field)}")

        return "\n\n".join(questions)

    def get_collected_summary(self) -> str:
        """生成已收集信息的摘要（用于用户确认）"""
        if not self.collected_info:
            return "还没有收集到任何信息。"

        field_names = {
            "topic": "学习主题",
            "goal": "目标",
            "duration": "时长",
            "daily_hours": "每天学习时间",
            "level": "基础水平",
            "activity_level": "运动强度",
            "height": "身高",
            "weight": "体重",
            "age": "年龄",
            "gender": "性别",
            "city": "所在城市",
            "location": "所在城市",
            "destination": "目的地",
            "days": "天数",
            "budget": "预算",
            "interests": "兴趣",
            "departure_date": "出发日期",
            "target_currency": "目标币种",
            "task": "任务",
            "team_size": "团队规模",
            "deadline": "截止日期",
            "monthly_income": "月收入",
            "current_savings": "当前存款",
        }

        summary_parts = []
        for field, value in self.collected_info.items():
            field_name = field_names.get(field, field)
            summary_parts.append(f"- {field_name}：{value}")

        return "\n".join(summary_parts)

    def update_field(self, field: str, value: str) -> bool:
        """更新某个字段的值（用于用户修改）"""
        if field in self.collected_info:
            self.collected_info[field] = value
            return True
        return False

    def _generate_question(self, field: str) -> str:
        """生成问题（带 API 引导提示）"""
        # 使用带前缀的键名，避免不同计划类型的相同字段名冲突
        question_key = f"{self.plan_type}_{field}"

        questions = {
            # ─── 学习计划 ───────────────────────────────────────
            "learning_topic": "你想学习什么主题？例如：Python、英语、编程、设计\n\n💡 提示：提到特定主题会调用不同的资源\n  - 编程/Python/Java → 搜索编程书籍\n  - 英语/单词 → 搜索英语学习资源\n  - 论文/学术 → 搜索学术文章",
            "learning_goal": "你的学习目标？例如：入门、进阶、项目实战、考试准备",
            "learning_duration": "计划学习多长时间？例如：1个月、3个月、半年",
            "learning_daily_hours": "每天能投入多少时间学习？例如：1小时、2小时、4小时",
            "learning_level": "你当前的基础水平？例如：零基础、初学者、有一定基础",

            # ─── 健康计划 ───────────────────────────────────────
            "health_goal": "你的健康目标？例如：减肥、增肌、保持健康、改善睡眠\n\n💡 提示：\n  - 减肥/饮食 → 查询营养数据库\n  - 户外/跑步/运动 → 查询天气情况\n  - 增肌 → 查询蛋白质摄入建议",
            "health_duration": "计划多长时间？例如：1个月、3个月、半年",
            "health_activity_level": "运动强度偏好？\n  - 低：散步、瑜伽\n  - 中：跑步、游泳\n  - 高：HIIT、力量训练\n\n💡 提示：选择中/高强度会查询天气，推荐户外运动",
            "health_height": "你的身高（cm）？例如：170",
            "health_weight": "你的体重（kg）？例如：65",
            "health_age": "你的年龄？例如：25",
            "health_gender": "你的性别？男/女",
            "health_location": "你所在的城市？例如：北京、上海\n\n💡 提示：用于查询当地天气，推荐适合的运动",
            "health_diet_preference": "饮食偏好（可选）？例如：素食、低碳水、无特殊要求",
            "health_medical_conditions": "是否有健康问题或特殊需求（可选）？例如：膝盖受伤、高血压",

            # ─── 旅行计划 ───────────────────────────────────────
            "travel_destination": "你想去哪里？例如：北京、上海、日本、欧洲\n\n💡 提示：提到国外目的地会自动查询汇率",
            "travel_city": "你从哪个城市出发？例如：北京、上海",
            "travel_days": "计划旅行几天？例如：3天、5天、7天",
            "travel_budget": "预算大概多少？例如：1000元、5000元、1万元\n\n💡 提示：提到预算会自动查询汇率换算",
            "travel_target_currency": "目标币种？例如：人民币(CNY)、美元(USD)、欧元(EUR)、日元(JPY)\n\n💡 提示：用于查询汇率，如美元、欧元、日元等",
            "travel_interests": "对什么感兴趣？例如：文化、美食、自然、购物、历史\n\n💡 提示：\n  - 美食/啤酒 → 搜索当地精酿啤酒\n  - 骑行/单车 → 搜索共享单车\n  - 文化/历史 → 搜索当地景点",
            "travel_departure_date": "出发日期？例如：2026-07-01（用于查询天气）",
            "travel_accommodation_preference": "住宿偏好（可选）？例如：酒店、民宿、青旅",

            # ─── 工作计划 ───────────────────────────────────────
            "work_task": "任务名称是什么？例如：项目开发、产品设计、市场推广\n\n💡 提示：提到团队人数会查询更多协作资源",
            "work_duration": "计划多长时间？例如：2周、1个月、3个月\n\n💡 提示：会自动查询中国节假日，排除非工作日",
            "work_team_size": "团队人数？例如：1人、5人、10人",
            "work_deadline": "截止日期？例如：2026-08-01（用于计算工作日）",

            # ─── 财务计划 ───────────────────────────────────────
            "finance_goal": "你的财务目标？例如：存5万、理财、投资、还债\n\n💡 提示：\n  - 存钱/预算 → 查询汇率换算\n  - 投资/股票/基金 → 查询上市公司财报\n  - 理财/经济 → 查询宏观经济数据",
            "finance_duration": "计划多长时间？例如：1年、2年、5年",
            "finance_monthly_income": "月收入大概多少？例如：5000元、1万元",
            "finance_current_savings": "当前存款？例如：1万元、5万元",
            "finance_target_currency": "主要币种？例如：人民币(CNY)、美元(USD)\n\n💡 提示：用于查询汇率，如美元、欧元等",
            "finance_investment_preference": "投资风险偏好（可选）？例如：保守型、稳健型、激进型\n\n💡 提示：会影响投资组合建议",
        }

        # 首先尝试获取带前缀的问题
        if question_key in questions:
            return questions[question_key]

        # 如果没有带前缀的，尝试获取通用问题（向后兼容）
        if field in questions:
            return questions[field]

        # 默认返回
        return f"请告诉我{field}"

    def add_info(self, field: str, value: str):
        """添加收集到的信息"""
        self.collected_info[field] = value
        self.current_field_index += 1
        self.updated_at = datetime.now()  # 更新时间戳

    def is_complete(self) -> bool:
        """信息是否收集完毕"""
        return self.current_field_index >= len(self.required_fields)

    def get_collected_info(self) -> Dict[str, Any]:
        """获取收集到的信息"""
        return self.collected_info

    def set_rag_context(self, rag_context: Optional[str], context_summary: Optional[str] = None):
        """设置 RAG 上下文和上下文历史摘要

        Args:
            rag_context: 知识库查询结果
            context_summary: 上下文历史摘要（从对话历史中提取）
        """
        self.rag_context = rag_context
        self.context_summary = context_summary

    def get_rag_context(self) -> Optional[str]:
        """获取 RAG 上下文"""
        return self.rag_context

    def get_context_summary(self) -> Optional[str]:
        """获取上下文历史摘要"""
        return self.context_summary

    def set_selected_optional_apis(self, selected: List[int]):
        """设置用户选择的可选API"""
        self.selected_optional_apis = selected

    def get_selected_optional_apis(self) -> Optional[List[int]]:
        """获取用户选择的可选API"""
        return self.selected_optional_apis

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "plan_type": self.plan_type,
            "collected_info": self.collected_info,
            "current_field_index": self.current_field_index,
            "required_fields": self.required_fields,
            "optional_fields": self.optional_fields,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "rag_context": self.rag_context,
            "context_summary": self.context_summary,
            "selected_optional_apis": self.selected_optional_apis,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanInfoCollector":
        """从字典反序列化"""
        collector = cls(data["plan_type"])
        collector.collected_info = data.get("collected_info", {})
        collector.current_field_index = data.get("current_field_index", 0)
        collector.required_fields = data.get("required_fields", [])
        collector.optional_fields = data.get("optional_fields", [])

        # 恢复时间戳
        if data.get("created_at"):
            try:
                collector.created_at = datetime.fromisoformat(data["created_at"])
            except:
                collector.created_at = datetime.now()
        if data.get("updated_at"):
            try:
                collector.updated_at = datetime.fromisoformat(data["updated_at"])
            except:
                collector.updated_at = datetime.now()

        # 恢复 RAG 上下文和上下文历史摘要
        collector.rag_context = data.get("rag_context")
        collector.context_summary = data.get("context_summary")
        collector.selected_optional_apis = data.get("selected_optional_apis")

        return collector

# ─── 信息收集器管理器（Redis 持久化）──────────────────────────

class PlanInfoCollectorManager:
    """计划信息收集器管理器（支持状态持久化）"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = timedelta(minutes=30)  # 30分钟过期
        self._memory_cache: Dict[str, PlanInfoCollector] = {}  # 内存缓存

    def get_collector(self, session_id: str) -> Optional[PlanInfoCollector]:
        """获取计划信息收集器（优先从内存获取）"""
        # 1. 先尝试从内存获取
        if session_id in self._memory_cache:
            print(f"[DEBUG] Found collector in memory cache: {session_id}")
            return self._memory_cache[session_id]

        # 2. 再尝试从 Redis 获取
        if self.redis:
            redis_key = f"plan:collector:{session_id}"
            try:
                data = self.redis.get(redis_key)
                if data:
                    print(f"[DEBUG] Found collector in Redis: {redis_key}")
                    collector_dict = json.loads(data)
                    collector = PlanInfoCollector.from_dict(collector_dict)
                    self._memory_cache[session_id] = collector  # 缓存到内存
                    return collector
                else:
                    print(f"[DEBUG] No collector found in Redis: {redis_key}")
            except Exception as e:
                print(f"[ERROR] Failed to get collector from Redis: {e}")
        else:
            print(f"[WARNING] Redis client is None, cannot get collector")

        return None

    def save_collector(self, session_id: str, collector: PlanInfoCollector):
        """保存计划信息收集器到 Redis"""
        # 1. 保存到内存
        self._memory_cache[session_id] = collector
        print(f"[DEBUG] Saved collector to memory cache: {session_id}")

        # 2. 保存到 Redis（带 TTL）
        if self.redis:
            redis_key = f"plan:collector:{session_id}"
            try:
                collector_dict = collector.to_dict()
                self.redis.setex(redis_key, self.ttl, json.dumps(collector_dict))
                print(f"[DEBUG] Saved collector to Redis: {redis_key}, TTL: {self.ttl}")
            except Exception as e:
                print(f"[ERROR] Failed to save collector to Redis: {e}")
        else:
            print(f"[WARNING] Redis client is None, cannot save collector")

    def delete_collector(self, session_id: str):
        """删除计划信息收集器"""
        # 1. 从内存删除
        if session_id in self._memory_cache:
            del self._memory_cache[session_id]

        # 2. 从 Redis 删除
        if self.redis:
            redis_key = f"plan:collector:{session_id}"
            try:
                self.redis.delete(redis_key)
            except Exception as e:
                print(f"[ERROR] Failed to delete collector from Redis: {e}")

    def restore_collector(self, session_id: str) -> Optional[PlanInfoCollector]:
        """恢复计划信息收集器（带时效性校验）"""
        collector = self.get_collector(session_id)

        if collector is None:
            return None

        # 校验已收集信息的时效性
        if self._is_collector_expired(collector):
            print(f"[INFO] Collector for session {session_id} is expired, deleting")
            self.delete_collector(session_id)
            return None

        return collector

    def _is_collector_expired(self, collector: PlanInfoCollector) -> bool:
        """校验收集器是否过期（可自定义逻辑）"""
        # 如果收集器创建时间超过 20 分钟，视为过期
        created_at = collector.created_at
        if created_at:
            now = datetime.now()
            if (now - created_at).total_seconds() > 1200:  # 20分钟
                return True
        return False

# ─── API 选择策略 ──────────────────────────────────────────────

def select_learning_apis(plan_info: Dict[str, Any]) -> List:
    """根据计划信息选择学习计划 API（5 个 API）

    策略：
    - 基础 API（始终调用）：Open Library + Gutendex
    - 如果用户没有明确指定主题，默认调用所有 API（最全面）
    - 如果用户指定了主题，根据关键词选择相关 API
    """
    apis = [search_open_library, search_gutendex]  # 基础 API，始终调用

    # 从 plan_info 中提取关键词
    topic = plan_info.get("topic", "")
    goal = plan_info.get("goal", "")
    combined_text = f"{topic} {goal}".lower()

    print(f"[DEBUG] select_learning_apis - topic: '{topic}', goal: '{goal}', combined_text: '{combined_text}'")

    # 如果主题是通用的（如"知识库内容"、"学习"等），默认调用所有 API
    generic_topics = ["知识库", "学习", "考试", "内容", "通用", "综合"]
    is_generic = any(kw in combined_text for kw in generic_topics) or not topic or topic == "知识库内容"

    if is_generic:
        # 通用主题：调用所有 API（最全面）
        apis.extend([search_poetrydb, search_crossref, search_quran])
        print(f"[DEBUG] Generic topic detected, adding all APIs")
    else:
        # 特定主题：根据关键词选择
        # 扩展 API 1：英语/诗歌/文学相关
        poetry_keywords = ["单词", "诗歌", "英语", "英文", "文学", "诗词", "古诗", "现代诗"]
        if any(kw in combined_text for kw in poetry_keywords):
            apis.append(search_poetrydb)
            print(f"[DEBUG] Added search_poetrydb (matched keywords: {[kw for kw in poetry_keywords if kw in combined_text]})")

        # 扩展 API 2：学术/研究相关
        academic_keywords = ["论文", "学术", "研究", "科学", "科研", "期刊", "文献", "毕业"]
        if any(kw in combined_text for kw in academic_keywords):
            apis.append(search_crossref)
            print(f"[DEBUG] Added search_crossref (matched keywords: {[kw for kw in academic_keywords if kw in combined_text]})")

        # 扩展 API 3：宗教/古兰经相关
        religion_keywords = ["quran", "古兰经", "宗教", "伊斯兰教", "圣经", "佛经"]
        if any(kw in combined_text for kw in religion_keywords):
            apis.append(search_quran)
            print(f"[DEBUG] Added search_quran (matched keywords: {[kw for kw in religion_keywords if kw in combined_text]})")

    print(f"[DEBUG] select_learning_apis returned {len(apis)} APIs: {[api.__name__ for api in apis]}")
    return apis  # 最多 5 个

def select_health_apis(plan_info: Dict[str, Any]) -> List:
    """根据计划信息选择健康计划 API（3 个 API）

    关键词匹配规则：
    - 户外运动/跑步/中高强度 → Open-Meteo（天气）
    - 减肥/饮食/营养/增肌 → Open Food Facts + Fruityvice（营养）
    - 默认：全部调用
    """
    apis = []

    # 天气相关（户外运动、跑步等）
    goal = plan_info.get("goal", "")
    activity_level = plan_info.get("activity_level", "")
    location = plan_info.get("location", "")
    combined_text = f"{goal} {activity_level} {location}".lower()

    # 触发天气 API 的关键词
    weather_keywords = ["户外", "跑步", "运动", "天气", "游泳", "骑行", "徒步", "登山", "中", "高"]
    if any(kw in combined_text for kw in weather_keywords):
        apis.append(get_weather_forecast)

    # 营养相关（减肥、饮食等）
    nutrition_keywords = ["减肥", "饮食", "营养", "餐", "增肌", "健康", "瘦身", "体重", "蛋白质", "卡路里"]
    if any(kw in combined_text for kw in nutrition_keywords):
        apis.append(get_food_nutrition)
        apis.append(get_fruit_nutrition)

    # 如果都没有匹配到，默认调用全部（因为健康计划通常需要天气+营养）
    if not apis:
        apis = [get_weather_forecast, get_food_nutrition, get_fruit_nutrition]

    return apis  # 最多 3 个

def select_travel_apis(plan_info: Dict[str, Any]) -> List:
    """根据计划信息选择旅行计划 API（6 个 API）

    关键词匹配规则：
    - 天气：始终调用 Open-Meteo
    - 预算/汇率/国外 → ExchangeRate-API
    - 骑行/单车 → City Bikes
    - 美食/啤酒/精酿 → Open Brewery DB
    - 定位/位置 → ip-api
    - 时区/时差/国外 → WorldTimeAPI
    """
    apis = [get_weather_forecast]  # 天气是基础，始终调用

    # 从 plan_info 中提取关键词
    destination = plan_info.get("destination", "")
    budget = plan_info.get("budget", "")
    interests = plan_info.get("interests", "")
    target_currency = plan_info.get("target_currency", "")
    combined_text = f"{destination} {budget} {interests} {target_currency}".lower()

    # 扩展 API 1：汇率相关
    exchange_keywords = ["预算", "钱", "汇率", "美元", "欧元", "国外", "日本", "欧洲", "美国", "外汇", "兑换", "外币"]
    if any(kw in combined_text for kw in exchange_keywords):
        apis.append(get_exchange_rates)

    # 扩展 API 2：骑行相关
    bike_keywords = ["骑行", "单车", "自行车", "骑车", "脚踏车"]
    if any(kw in combined_text for kw in bike_keywords):
        apis.append(get_city_bikes)

    # 扩展 API 3：美食/啤酒相关
    food_keywords = ["啤酒", "精酿", "美食", "文化", "当地特色", "小吃", "餐厅"]
    if any(kw in combined_text for kw in food_keywords):
        apis.append(get_open_brewery)

    # 扩展 API 4：定位相关
    location_keywords = ["定位", "位置", "当地", "本地", "周边", "附近"]
    if any(kw in combined_text for kw in location_keywords):
        apis.append(get_ip_location)

    # 扩展 API 5：时区相关
    timezone_keywords = ["时间", "时差", "国外", "日本", "欧洲", "时区", "当地时间"]
    if any(kw in combined_text for kw in timezone_keywords):
        apis.append(get_world_time)

    return apis  # 最多 6 个

def select_work_apis(plan_info: Dict[str, Any]) -> List:
    """根据计划信息选择工作计划 API（5 个 API）

    关键词匹配规则：
    - 节假日/工作日：始终调用 timor.tech + WorldTimeAPI
    - 测试/问答/培训 → Open Trivia
    - 团队/多人/协作 → JSONPlaceholder + Random Data
    """
    apis = []

    # 节假日相关（始终调用，因为工作计划需要考虑工作日）
    apis.append(get_china_holidays)
    apis.append(get_world_time)

    task = plan_info.get("task", "")
    duration = plan_info.get("duration", "")
    combined_text = f"{task} {duration}".lower()

    # 扩展 API 1：测试/问答相关
    trivia_keywords = ["测试", "问答", "知识", "学习", "培训", "考试", "考核", "练习"]
    if any(kw in combined_text for kw in trivia_keywords):
        apis.append(get_open_trivia)

    # 扩展 API 2：团队项目相关
    team_keywords = ["团队", "多人", "协作", "合作", "小组", "部门"]
    team_size = plan_info.get("team_size", "1")
    is_team_project = any(kw in combined_text for kw in team_keywords)

    # 如果团队人数 > 1 或提到团队关键词
    if is_team_project or (isinstance(team_size, (int, float)) and team_size > 1):
        apis.append(get_json_placeholder)
        apis.append(get_random_data)
    elif isinstance(team_size, str) and any(kw in team_size for kw in ["团队", "多人", "5", "10"]):
        apis.append(get_json_placeholder)
        apis.append(get_random_data)

    return apis  # 最多 5 个

def select_finance_apis(plan_info: Dict[str, Any]) -> List:
    """根据计划信息选择财务计划 API（5 个 API）

    关键词匹配规则：
    - 存钱/预算/汇率/外汇 → ExchangeRate-API
    - 理财/经济/宏观/通胀 → Econdb
    - 投资/股票/基金/财报 → SEC EDGAR + Portfolio Optimizer
    - 转账/国际/IBAN → IBANforge
    """
    apis = []

    goal = plan_info.get("goal", "")
    target_currency = plan_info.get("target_currency", "")
    monthly_income = plan_info.get("monthly_income", "")
    combined_text = f"{goal} {target_currency} {monthly_income}".lower()

    # 扩展 API 1：汇率相关
    exchange_keywords = ["存钱", "预算", "汇率", "美元", "欧元", "外汇", "出国", "旅行", "外币", "兑换", "人民币"]
    if any(kw in combined_text for kw in exchange_keywords):
        apis.append(get_exchange_rates)

    # 扩展 API 2：经济数据相关
    economic_keywords = ["理财", "经济", "宏观", "趋势", "通胀", "利率", "市场", "行情", "GDP"]
    if any(kw in combined_text for kw in economic_keywords):
        apis.append(get_economic_data)

    # 扩展 API 3：投资相关
    investment_keywords = ["投资", "股票", "基金", "财报", "证券", "债券", "期货", "期权", "理财"]
    if any(kw in combined_text for kw in investment_keywords):
        apis.append(get_sec_edgar)
        apis.append(get_portfolio_optimizer)

    # 扩展 API 4：国际转账相关
    transfer_keywords = ["转账", "国际", "iban", "海外", "汇款", "跨境"]
    if any(kw in combined_text for kw in transfer_keywords):
        apis.append(get_ibanforge)

    # 默认：汇率+经济（如果没有任何匹配）
    if not apis:
        apis = [get_exchange_rates, get_economic_data]

    return apis  # 最多 5 个

def get_optional_apis_for_plan(plan_type: str, required_fields: list) -> List[Dict[str, str]]:
    """获取计划类型的可选 API 列表（委婉描述，不直接提 API 名称）

    Args:
        plan_type: 计划类型
        required_fields: 必填字段列表

    Returns:
        可选 API 列表，每个包含 name（委婉描述）和 description（功能说明）
    """
    optional_apis = {
        # 学习计划：默认调用 Open Library + Gutendex
        "learning": [
            {"name": "📜 古诗词推荐", "description": "根据时节智能推荐古诗词"},
            {"name": "💬 随机名句", "description": "获取一言名句，激励学习"},
            {"name": "📄 学术论文", "description": "搜索学术论文"},
            {"name": "📝 英文诗歌库", "description": "搜索英文诗歌（PoetryDB）"},
        ],
        # 健康计划：默认调用 Open-Meteo + TheMealDB
        "health": [
            {"name": "🏃 运动动作库", "description": "获取专业运动动作指导"},
            {"name": "💪 肌肉群信息", "description": "了解各肌肉群，科学锻炼"},
            {"name": "🌤️ 国内天气", "description": "高德天气（更精准）"},
            {"name": "📍 地理位置", "description": "获取当前位置信息"},
            {"name": "🥗 食物营养数据", "description": "查询食物卡路里和营养成分"},
            {"name": "🍎 水果营养数据", "description": "查询水果营养信息"},
        ],
        # 旅行计划：默认调用 Open-Meteo
        "travel": [
            {"name": "💱 汇率查询", "description": "查询目标币种汇率"},
            {"name": "📅 节假日", "description": "查询中国节假日安排"},
            {"name": "📍 地理位置", "description": "获取当前位置信息"},
            {"name": "🌤️ 国内天气", "description": "高德天气（更精准）"},
            {"name": "🍜 当地美食", "description": "搜索目的地特色美食食谱"},
            {"name": "🚲 城市单车租赁点", "description": "查询城市共享单车分布"},
            {"name": "🍺 当地特色饮品店", "description": "查询当地精酿酒吧"},
            {"name": "🕐 当地时间", "description": "查询目的地时区时间"},
        ],
        # 工作计划：默认调用 timor.tech
        "work": [
            {"name": "💬 随机名句", "description": "获取激励名句"},
            {"name": "📜 古诗词", "description": "古诗词推荐"},
            {"name": "❓ 知识问答", "description": "获取知识问答题目"},
            {"name": "🏃 运动建议", "description": "工作间隙运动建议"},
            {"name": "📋 任务模板示例", "description": "获取任务数据模板参考"},
        ],
        # 财务计划：默认调用 ExchangeRate-API
        "finance": [
            {"name": "📍 地理位置", "description": "获取当前位置信息"},
            {"name": "🌤️ 天气", "description": "高德天气"},
            {"name": "📅 节假日", "description": "查询中国节假日安排"},
            {"name": "📈 上市公司财报", "description": "查询美股公司财报"},
            {"name": "💼 投资组合分析", "description": "投资组合优化建议"},
        ],
    }

    return optional_apis.get(plan_type, [])


def get_suggestions_for_plan(plan_type: str) -> str:
    """获取计划类型的委婉建议（用于询问用户是否需要额外信息）

    Args:
        plan_type: 计划类型

    Returns:
        委婉的建议文本，包含可用的功能列表（带编号，方便用户选择）
    """
    # 每种计划类型的默认功能 + 可选功能说明（委婉描述）
    suggestions = {
        "learning": """📚 默认会为您推荐相关书籍和电子书资源。

💡 是否还需要以下支撑？
  1. 📜 古诗词推荐 - 根据时节智能推荐古诗词
  2. 💬 随机名句 - 获取激励名句
  3. 📄 学术论文 - 搜索相关学术论文
  4. 📝 英文诗歌库 - 搜索英文诗歌

回复"是"调用全部，或回复序号如"1,2"选择特定功能，回复"否"跳过。""",
        "health": """🏃 默认会为您查询天气和推荐健康食谱。

💡 是否还需要以下支撑？
  1. 🏃 运动动作库 - 获取专业运动动作指导
  2. 💪 肌肉群信息 - 了解各肌肉群，科学锻炼
  3. 🌤️ 国内天气 - 高德天气（更精准）
  4. 📍 地理位置 - 获取当前位置信息
  5. 🥗 食物营养数据 - 查询食物卡路里
  6. 🍎 水果营养数据 - 查询水果营养信息

回复"是"调用全部，或回复序号如"1,2"选择特定功能，回复"否"跳过。""",
        "travel": """🗺️ 默认会为您查询目的地天气。

💡 是否还需要以下支撑？
  1. 💱 汇率查询 - 查询目标币种汇率
  2. 📅 节假日 - 查询中国节假日安排
  3. 📍 地理位置 - 获取当前位置信息
  4. 🌤️ 国内天气 - 高德天气（更精准）
  5. 🍜 当地美食 - 搜索目的地特色美食食谱
  6. 🚲 城市单车租赁点 - 查询城市共享单车分布
  7. 🍺 当地特色饮品店 - 查询当地精酿酒吧
  8. 🕐 当地时间 - 查询目的地时区时间

回复"是"调用全部，或回复序号如"1,3"选择特定功能，回复"否"跳过。""",
        "work": """💼 默认会为您查询中国节假日安排。

💡 是否还需要以下支撑？
  1. 💬 随机名句 - 获取激励名句
  2. 📜 古诗词 - 古诗词推荐
  3. ❓ 知识问答 - 获取知识问答题目
  4. 🏃 运动建议 - 工作间隙运动建议
  5. 📋 任务模板示例 - 获取任务数据模板参考

回复"是"调用全部，或回复序号如"1"选择特定功能，回复"否"跳过。""",
        "finance": """💰 默认会为您查询汇率信息。

💡 是否还需要以下支撑？
  1. 📍 地理位置 - 获取当前位置信息
  2. 🌤️ 天气 - 高德天气
  3. 📅 节假日 - 查询中国节假日安排
  4. 📈 上市公司财报 - 查询美股公司财报
  5. 💼 投资组合分析 - 投资组合优化建议

回复"是"调用全部，或回复序号如"1"选择特定功能，回复"否"跳过。""",
    }

    return suggestions.get(plan_type, "")


def _get_api_function_by_name(api_name: str, plan_type: str):
    """根据委婉描述名称获取对应的 API 函数"""
    # 委婉描述 → API 函数的映射
    api_mapping = {
        # 学习计划可选 API
        "📜 古诗词推荐": get_jinrishici,
        "📜 古诗词": get_jinrishici,
        "💬 随机名句": get_hitokoto,
        "📄 学术论文": search_crossref,
        "📝 英文诗歌库": search_poetrydb,
        # 健康计划可选 API
        "🏃 运动动作库": get_wger_exercises,
        "🏃 运动建议": get_wger_exercises,
        "💪 肌肉群信息": get_wger_muscles,
        "🌤️ 国内天气": get_amap_weather,
        "📍 地理位置": get_ip_location,
        "🥗 食物营养数据": get_food_nutrition,
        "🍎 水果营养数据": get_fruit_nutrition,
        # 旅行计划可选 API
        "💱 汇率查询": get_exchange_rates,
        "📅 节假日": get_china_holidays,
        "🍜 当地美食": get_themealdb,
        "🚲 城市单车租赁点": get_city_bikes,
        "🍺 当地特色饮品店": get_open_brewery,
        "🕐 当地时间": get_world_time,
        # 工作计划可选 API
        "❓ 知识问答": get_open_trivia,
        "📋 任务模板示例": get_json_placeholder,
        # 财务计划可选 API
        "🌤️ 天气": get_amap_weather,
        "📈 上市公司财报": get_sec_edgar,
        "💼 投资组合分析": get_portfolio_optimizer,
    }

    return api_mapping.get(api_name)


def preview_apis_to_call(
    plan_type: str,
    plan_info: Dict[str, Any],
    selected_optional_apis: Optional[List[int]] = None
) -> str:
    """预览将要调用的 API（用于展示给用户）

    Args:
        plan_type: 计划类型
        plan_info: 用户填写的信息
        selected_optional_apis: 用户选择的可选 API 序号列表（从 1 开始）
    """

    # 1. 获取默认 API（始终调用）
    default_apis = _get_default_apis(plan_type)

    # 2. 获取用户选择的可选 API
    optional_apis = []
    if selected_optional_apis:
        all_optional = get_optional_apis_for_plan(plan_type, [])
        for idx in selected_optional_apis:
            if 1 <= idx <= len(all_optional):
                api_info = all_optional[idx - 1]
                api_func = _get_api_function_by_name(api_info.get("name", ""), plan_type)
                if api_func:
                    optional_apis.append(api_func)

    # 3. 生成 API 描述（委婉描述，不直接提 API 名称）
    api_descriptions = {
        # 学习计划
        "search_open_library": "📚 书籍推荐 - 搜索相关书籍",
        "search_gutendex": "📖 电子书 - 搜索免费电子书",
        "get_jinrishici": "📜 古诗词推荐 - 根据时节智能推荐",
        "get_hitokoto": "💬 随机名句 - 获取激励名句",
        "search_crossref": "📄 学术论文 - 搜索学术论文",
        "search_poetrydb": "📝 英文诗歌库 - 搜索英文诗歌",
        # 健康计划
        "get_weather_forecast": "🌤️ 天气预报 - 查询天气",
        "get_themealdb": "🍜 健康食谱 - 推荐健康美食",
        "get_wger_exercises": "🏃 运动动作库 - 专业运动指导",
        "get_wger_muscles": "💪 肌肉群信息 - 科学锻炼参考",
        "get_amap_weather": "🌤️ 国内天气 - 高德天气（更精准）",
        "get_ip_location": "📍 地理位置 - 获取当前位置",
        "get_food_nutrition": "🥗 食物营养数据 - 查询食物卡路里",
        "get_fruit_nutrition": "🍎 水果营养数据 - 查询水果营养信息",
        # 旅行计划
        "get_exchange_rates": "💱 汇率查询 - 查询目标币种汇率",
        "get_china_holidays": "📅 节假日 - 查询中国节假日安排",
        "get_city_bikes": "🚲 城市单车租赁点 - 查询共享单车分布",
        "get_open_brewery": "🍺 当地特色饮品店 - 查询当地精酿酒吧",
        "get_world_time": "🕐 当地时间 - 查询目的地时区",
        # 工作计划
        "get_open_trivia": "❓ 知识问答 - 获取知识问答题目",
        "get_json_placeholder": "📋 任务模板示例 - 获取任务数据模板",
        # 财务计划
        "get_economic_data": "📊 经济数据 - 查询经济指标",
        "get_sec_edgar": "📈 上市公司财报 - 查询美股公司财报",
        "get_portfolio_optimizer": "💼 投资组合分析 - 投资组合优化建议",
    }

    # 4. 构建预览文本
    default_names = [api.__name__ for api in default_apis]
    optional_names = [api.__name__ for api in optional_apis]

    lines = []
    if default_names:
        lines.append("📌 默认调用：")
        for name in default_names:
            lines.append(f"  {api_descriptions.get(name, name)}")

    if optional_names:
        lines.append("\n✅ 你选择的额外资源：")
        for name in optional_names:
            lines.append(f"  {api_descriptions.get(name, name)}")
    else:
        # 如果没有用户选择的可选 API，提示用户可以选择
        lines.append("\n💡 目前只调用默认资源，如需额外资源请回复序号（如\"1,2\"）")

    if not lines:
        return ""

    return "🔍 将调用以下外部资源：\n" + "\n".join(lines)


def _get_default_apis(plan_type: str) -> List:
    """获取计划类型的默认 API（始终调用）"""

    default_apis = {
        "learning": [search_open_library, search_gutendex],
        "health": [get_weather_forecast, get_themealdb],
        "travel": [get_weather_forecast],
        "work": [get_china_holidays],
        "finance": [get_exchange_rates],
    }

    return default_apis.get(plan_type, [])


def call_apis_for_plan(
    plan_type: str,
    plan_info: Dict[str, Any],
    selected_optional_apis: Optional[List[int]] = None
) -> Dict[str, Any]:
    """统一调度器：根据计划类型和收集到的信息调用 API

    Args:
        plan_type: 计划类型
        plan_info: 用户填写的信息
        selected_optional_apis: 用户选择的可选API序号列表
    """

    print(f"[DEBUG] call_apis_for_plan called - plan_type: {plan_type}, plan_info: {plan_info}")
    print(f"[DEBUG] selected_optional_apis: {selected_optional_apis}")

    # 1. 选择要调用的 API（复用 preview 逻辑）
    if plan_type == "learning":
        apis = select_learning_apis(plan_info)
    elif plan_type == "health":
        apis = select_health_apis(plan_info)
    elif plan_type == "travel":
        apis = select_travel_apis(plan_info)
    elif plan_type == "work":
        apis = select_work_apis(plan_info)
    elif plan_type == "finance":
        apis = select_finance_apis(plan_info)
    else:
        print(f"[WARN] Unknown plan_type: {plan_type}")
        return {}

    print(f"[DEBUG] Selected {len(apis)} APIs: {[api.__name__ for api in apis]}")

    # 2. 如果用户选择了可选API，添加到调用列表
    if selected_optional_apis:
        print(f"[DEBUG] Processing optional APIs: {selected_optional_apis}")
        optional_apis = get_optional_apis_for_plan(plan_type, [])
        print(f"[DEBUG] Available optional APIs: {len(optional_apis)}")
        # 过滤掉超出范围的索引（防止前端传来无效值如 2026, 15000）
        max_idx = len(optional_apis)
        valid_indices = [idx for idx in selected_optional_apis if isinstance(idx, int) and 1 <= idx <= max_idx]
        if valid_indices != selected_optional_apis:
            print(f"[WARN] Filtered invalid optional API indices: {selected_optional_apis} -> {valid_indices}")
        for idx in valid_indices:
            if 1 <= idx <= len(optional_apis):
                api_info = optional_apis[idx - 1]
                # 根据名称找到对应的API函数
                api_func = _get_api_function_by_name(api_info.get("name", ""), plan_type)
                if api_func and api_func not in apis:
                    apis.append(api_func)
                    print(f"[INFO] Added optional API: {api_info.get('name')}")

    print(f"[DEBUG] Final API list ({len(apis)} total): {[api.__name__ for api in apis]}")

    # ─── 为每个 API 计算最佳查询词 ──────────────────────────────
    topic = plan_info.get("topic", "")
    goal = plan_info.get("goal", "")
    rag_context = plan_info.get("_rag_context")  # 从 plan_info 中获取知识库上下文

    # 根据 plan_type + topic + plan_info 生成精准查询词
    api_queries = _generate_api_queries(plan_type, topic, goal, rag_context, plan_info)

    # 3. 调用选中的 API（简化版，实际应该并行调用）
    results = {}
    for api in apis:
        try:
            api_name = api.__name__
            # 获取该 API 对应的查询词
            query = api_queries.get(api_name, topic)  # 默认用 topic
            print(f"[DEBUG] Calling API: {api_name} with query: '{query}'")

            # 根据 API 名称传递参数
            if api_name == "search_open_library":
                result = api(query)
            elif api_name == "search_gutendex":
                result = api(query)
            elif api_name == "search_crossref":
                result = api(query)
            elif api_name == "search_poetrydb":
                result = api(query)
            elif api_name == "search_quran":
                result = api(query)
            elif api_name == "get_weather_forecast":
                # 优先用 _generate_api_queries 返回的查询词（已映射城市名），否则用 plan_info
                city = api_queries.get("get_weather_forecast") or plan_info.get("location") or plan_info.get("city") or plan_info.get("destination", "北京")
                result = api(city)
            elif api_name == "get_food_nutrition":
                # 从 _generate_api_queries 获取食物查询词，不再硬编码
                food_query = api_queries.get("get_food_nutrition", "healthy food nutrition")
                result = api(food_query)
            elif api_name == "get_fruit_nutrition":
                fruit_query = api_queries.get("get_fruit_nutrition", "fruit nutrition")
                result = api(fruit_query)
            elif api_name == "get_exchange_rates":
                # 使用用户指定的目标币种
                target_currency = plan_info.get("target_currency", "CNY")
                # 提取币种代码（如 "美元(USD)" → "USD"）
                if "(" in target_currency:
                    target_currency = target_currency.split("(")[1].rstrip(")")
                result = api(target_currency)
            elif api_name == "get_city_bikes":
                # 优先用 _generate_api_queries（已映射目的地→城市名），否则 fallback
                city = api_queries.get("get_city_bikes") or plan_info.get("destination") or plan_info.get("city") or "London"
                result = api(city)
            elif api_name == "get_open_brewery":
                city = api_queries.get("get_open_brewery") or plan_info.get("destination") or plan_info.get("city") or "London"
                result = api(city)
            elif api_name == "get_world_time":
                city = api_queries.get("get_world_time") or plan_info.get("destination") or plan_info.get("city") or ""
                result = api(city) if city else api()
            elif api_name == "get_open_trivia":
                trivia_query = api_queries.get("get_open_trivia", "knowledge training")
                result = api(trivia_query)
            elif api_name == "get_economic_data":
                econ_query = api_queries.get("get_economic_data", "investment finance economy")
                result = api(econ_query)
            elif api_name == "get_sec_edgar":
                sec_query = api_queries.get("get_sec_edgar", "investment finance")
                result = api(sec_query)
            elif api_name == "get_ip_location":
                result = api()
            elif api_name == "get_china_holidays":
                now = datetime.now()
                result = api(now.year, now.month)
            elif api_name == "get_json_placeholder":
                result = api()
            elif api_name == "get_random_data":
                result = api()
            elif api_name == "get_portfolio_optimizer":
                result = api()
            # 新增国内免费 API
            elif api_name == "get_jinrishici":
                result = api()  # 今日诗词无需参数
            elif api_name == "get_hitokoto":
                result = api()  # 一言无需参数
            elif api_name == "get_themealdb":
                # 食谱搜索：用 goal 或 topic 作为关键词
                meal_query = api_queries.get("get_themealdb", goal or topic or "healthy")
                result = api(query=meal_query)
            elif api_name == "get_wger_exercises":
                result = api(limit=5)  # 运动动作库
            elif api_name == "get_wger_muscles":
                result = api()  # 肌肉群信息
            elif api_name == "get_amap_weather":
                # 高德天气：用 location 或 destination
                city = plan_info.get("location") or plan_info.get("destination") or plan_info.get("city", "北京")
                result = api(city)
            else:
                result = {}

            print(f"[DEBUG] API {api_name} returned: {type(result).__name__}, keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            results[api_name] = result
        except Exception as e:
            print(f"[ERROR] Failed to call {api.__name__}: {e}")
            import traceback
            print(traceback.format_exc())
            results[api.__name__] = {"error": str(e)}

    print(f"[DEBUG] call_apis_for_plan completed, returned {len(results)} results")
    return results


def _generate_api_queries(
    plan_type: str,
    topic: str,
    goal: str,
    rag_context: Optional[str] = None,
    plan_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    为所有 5 种计划类型的外部 API 生成最合适的查询词。

    核心策略（对所有类型通用）：
    1. 知识库有内容 → 取片段第一段有意义文字（30-60字）作为查询词
    2. 无知识库 → 用 plan_info 中的相关字段
    3. 各 API 拼不同后缀，提高命中率
    """
    queries = {}

    def _base_from_rag() -> Optional[str]:
        """从 rag_context 提取第一段有意义的内容作为 base 查询词"""
        if not rag_context or len(rag_context) < 30:
            return None
        lines = rag_context.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped and "来源:" not in stripped and len(stripped) > 10:
                return stripped[:60].strip("：:。. ，,")
        return None

    def _fallback(topic_val: str, goal_val: str, default: str) -> str:
        """Fallback: topic > goal > default"""
        if topic_val and topic_val not in ["知识库内容", "学习", "计划", "考试", "准备"]:
            return topic_val
        if goal_val:
            return goal_val
        return default

    # ═══════════════════════════════════════════════════════════
    # 学习计划 — 搜书/电子书/学术论文
    # ═══════════════════════════════════════════════════════════
    if plan_type == "learning":
        base = _base_from_rag() or _fallback(topic, goal, "study guide")
        queries["search_open_library"] = f"{base} textbook study guide"
        queries["search_gutendex"] = base
        queries["search_crossref"] = f"{base} education textbook"
        queries["search_poetrydb"] = base
        queries["search_quran"] = base
        print(f"[DEBUG] learning → Open Library: '{queries['search_open_library']}'")

    # ═══════════════════════════════════════════════════════════
    # 健康计划 — 天气/食谱/运动
    # 新增：TheMealDB 食谱、wger 运动动作库
    # ═══════════════════════════════════════════════════════════
    elif plan_type == "health":
        # 目标词 → 英文食物名映射（TheMealDB 需要英文关键词）
        goal_to_food = {
            "减肥": ["chicken", "salad", "vegetable"],
            "减脂": ["chicken", "fish", "vegetable"],
            "增肌": ["beef", "chicken", "protein"],
            "增重": ["rice", "pasta", "beef"],
            "健康": ["salad", "fish", "vegetable"],
            "瘦身": ["salad", "chicken", "vegetable"],
            "塑形": ["chicken", "fish", "egg"],
        }
        
        # 从 goal 提取目标词
        goal_text = goal or ""
        meal_query = "healthy"  # 默认
        
        # 用目标词找英文食物关键词
        for cn_key, en_foods in goal_to_food.items():
            if cn_key in goal_text:
                meal_query = en_foods[0]
                print(f"[DEBUG] health → 目标词'{cn_key}'映射到食谱关键词: '{meal_query}'")
                break
        
        # TheMealDB 食谱查询
        queries["get_themealdb"] = meal_query
        
        # 天气查询（健康计划可能需要户外运动天气）
        location = plan_info.get("location", "北京")
        queries["get_weather_forecast"] = location
        
        # 食物营养数据（open food facts）和 水果营养（fruityvice）
        food_query = meal_query if meal_query != "healthy" else "chicken"
        fruit_query = "apple" if meal_query in ["chicken", "beef", "rice", "pasta"] else meal_query
        queries["get_food_nutrition"] = food_query
        queries["get_fruit_nutrition"] = fruit_query
        
        print(f"[DEBUG] health → themealdb: '{meal_query}', weather: '{location}', nutrition: '{food_query}/{fruit_query}'")

    # ═══════════════════════════════════════════════════════════
    # 旅行计划 — 天气/汇率/骑行/美食
    # 关键修复：destination="日本"不是城市名 → 映射到主要城市
    #           city_bikes/brewery 需要实际城市名（如 Tokyo/London）
    # ═══════════════════════════════════════════════════════════
    elif plan_type == "travel":
        # 目的地 → 主要城市映射（用于 city_bikes/brewery/world_time）
        dest = plan_info.get("destination", topic or "")
        
        # 目的地到城市的映射
        city_name_map = {
            "日本": "Tokyo", "东京": "Tokyo",
            "京都": "Kyoto", "大阪": "Osaka", "北海道": "Sapporo",
            "韩国": "Seoul", "首尔": "Seoul",
            "泰国": "Bangkok", "曼谷": "Bangkok",
            "法国": "Paris", "巴黎": "Paris",
            "英国": "London", "伦敦": "London",
            "美国": "New York", "纽约": "New York",
            "澳大利亚": "Sydney", "悉尼": "Sydney",
            "新加坡": "Singapore",
            "中国": "Shanghai", "上海": "Shanghai",
            "香港": "Hong Kong",
            "澳门": "Macau",
            "台湾": "Taipei",
        }
        
        # 尝试直接匹配，否则检查是否包含关键词
        travel_city = city_name_map.get(dest)
        if not travel_city:
            # 尝试从复合地名中提取城市（如"日本京都"→"京都"）
            for city_key, city_val in city_name_map.items():
                if city_key in dest:
                    travel_city = city_val
                    break
        
        # 如果还是找不到，用原始值（API会尝试使用）
        travel_city = travel_city or dest
        
        queries["get_weather_forecast"] = travel_city
        queries["get_city_bikes"] = travel_city
        queries["get_open_brewery"] = travel_city
        queries["get_world_time"] = travel_city
        # 当地美食：用 travel_city 或 通用美食词如 pasta/rice
        queries["get_themealdb"] = travel_city if travel_city in ["Tokyo", "Kyoto", "Osaka", "Bangkok"] else "pasta"
        print(f"[DEBUG] travel → dest='{dest}' → travel_city='{travel_city}'")

    # ═══════════════════════════════════════════════════════════
    # 工作计划 — 节假日/测试问答（不依赖 rag_context，默认够用）
    # ═══════════════════════════════════════════════════════════
    elif plan_type == "work":
        # Open Trivia 基于 task/goal
        work_base = _fallback(topic, goal, "knowledge test training")
        queries["get_open_trivia"] = work_base
        print(f"[DEBUG] work → trivia query: '{work_base}'")

    # ═══════════════════════════════════════════════════════════
    # 财务计划 — 经济数据/投资（不依赖 rag_context）
    # ═══════════════════════════════════════════════════════════
    elif plan_type == "finance":
        # economic_data / sec_edgar 基于 goal
        finance_base = _fallback(topic, goal, "investment finance economy")
        queries["get_economic_data"] = finance_base
        queries["get_sec_edgar"] = finance_base
        print(f"[DEBUG] finance → economic query: '{finance_base}'")

    return queries


def _extract_keywords_from_text(text: str, max_keywords: int = 3) -> List[str]:
    """
    从文本中提取最关键的关键词（基于词频和语义）。
    简单实现：统计出现次数多的中文字符组合。
    """
    import re
    from collections import Counter

    if not text or len(text) < 10:
        return []

    # 提取 2-6 字的中文词
    words = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
    # 过滤停用词
    stopwords = {"的", "是", "在", "有", "和", "与", "了", "对", "为", "以及", "可以", "或者", "以及"}
    words = [w for w in words if w not in stopwords]

    # 按词频取 top
    counter = Counter(words)
    top = [w for w, _ in counter.most_common(max_keywords * 2)]

    # 去重且最多返回 max_keywords 个
    seen = set()
    result = []
    for w in top:
        # 避免包含关系（如"教育学"和"教育"保留更长的）
        if not any(w in other and w != other for other in result):
            result.append(w)
            seen.add(w)
        if len(result) >= max_keywords:
            break

    return result


# ─── 计划生成（LLM 智能生成）────────────────────────────────────

def generate_plan_with_llm(
    plan_type: str,
    plan_info: Dict[str, Any],
    api_results: Dict[str, Any],
    rag_context: Optional[str] = None
) -> str:
    """使用 LLM 生成完整的计划文本（替代硬编码模板）

    Args:
        plan_type: 计划类型（learning/health/travel/work/finance）
        plan_info: 用户填写的信息
        api_results: API 调用结果
        rag_context: RAG 知识库内容

    Returns:
        完整的计划文本
    """
    from app.common.llm_factory import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    # 1. 构建系统提示词
    system_prompt = _get_plan_system_prompt(plan_type)

    # 2. 构建用户提示词（包含所有信息）
    user_prompt = _build_plan_user_prompt(plan_type, plan_info, api_results, rag_context)

    # 3. 调用 LLM 生成计划
    try:
        llm = get_llm(temperature=0.7, force_ollama=True)  # 稍高温度，更有创意
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        result = llm.invoke(messages)

        if hasattr(result, 'content'):
            response = result.content
        else:
            response = str(result)

        # 清理响应
        response = response.strip()

        # 如果响应为空，fallback 到模板
        if not response or len(response) < 50:
            print(f"[WARN] LLM generated empty response, falling back to template")
            return _generate_plan_with_template(plan_type, plan_info, api_results, rag_context)

        print(f"[INFO] LLM generated plan: {len(response)} chars")
        return response

    except Exception as e:
        print(f"[ERROR] LLM plan generation failed: {e}, falling back to template")
        return _generate_plan_with_template(plan_type, plan_info, api_results, rag_context)


def _get_plan_system_prompt(plan_type: str) -> str:
    """获取计划生成的系统提示词（强制来源标注版）"""
    prompts = {
        "learning": """你是一个专业的学习规划师。请根据用户提供的信息，制定一个详细、可执行的学习计划。

要求：
1. 计划要具体、可操作，包含每天/每周的学习任务
2. 时间安排要合理，符合用户的时间预算
3. 如果提供了知识库内容，要结合知识库内容制定计划
4. 如果提供了外部资源（如书籍、课程），要在计划中引用
5. 使用清晰的格式，包含：目标、时间安排、学习内容、练习任务、资源推荐
6. 用中文回答

【强制格式要求 - 必须遵守】
- 只有当你确实从【知识库参考】或【外部资源查询结果】中看到了具体数据时，才标注来源
- 来源标注格式：[来源: API名称] 或 [来源: 文档名#编号]
- 绝对禁止编造来源：如 [来源: 文档名称]、[来源: 模板]、[来源: 未知]、[来源: 用户提供] 等都是不允许的
- 如果某条信息没有对应数据来源，不要写任何来源标注，直接写内容即可
- 禁止在结尾写任何"未获取到资源"/"无法获取数据"等免责声明，这与上文已引用的来源自相矛盾
- 示例：《Python Crash Course》- Eric Matthes [来源: Open Library]
- 示例：北京明天中雨，建议室内运动 [来源: Open-Meteo 天气预报]
- 示例：计划每天学习2小时（无来源，直接写即可，不需要任何说明）""",

        "health": """你是一个专业的健康顾问。请根据用户提供的信息，制定一个科学、健康的健康计划。

要求：
1. 计划要科学、安全，考虑用户的身体状况
2. 包含运动方案、饮食建议、作息安排
3. 如果提供了天气信息，要根据天气调整运动建议
4. 如果提供了营养数据，要在饮食建议中引用
5. 使用清晰的格式，包含：目标、运动计划、饮食方案、注意事项
6. 用中文回答

【强制格式要求 - 必须遵守】
- 只有当你确实从【知识库参考】或【外部资源查询结果】中看到了具体数据时，才标注来源
- 来源标注格式：[来源: API名称] 或 [来源: 文档名#编号]
- 绝对禁止编造来源：如 [来源: 文档名称]、[来源: 模板]、[来源: 用户提供]、[来源: 健康笔记.pdf] 等都是不允许的
- 如果某条信息没有对应数据来源（如用户的性别/年龄/目标等基础信息），不要写任何来源标注，直接写内容即可
- 禁止在结尾写任何"未获取到资源"/"无法获取数据"等免责声明，这与上文已引用的来源自相矛盾
- 示例：建议每天摄入2000大卡 [来源: Open Food Facts]
- 示例：苹果每100g含52大卡 [来源: Fruityvice]
- 示例：每周进行3次运动，每次30分钟（无来源，直接写即可，不需要任何说明）""",

        "travel": """你是一个专业的旅行规划师。请根据用户提供的信息，制定一个详细的旅行计划。

要求：
1. 行程要合理，时间安排要充裕
2. 包含景点推荐、交通建议、住宿推荐、美食推荐
3. 如果提供了天气信息，要根据天气调整行程
4. 如果提供了汇率信息，要在预算中引用
5. 使用清晰的格式，包含：行程概览、每日安排、预算估算、注意事项
6. 用中文回答

【强制格式要求 - 必须遵守】
- 只有当你确实从【知识库参考】或【外部资源查询结果】中看到了具体数据时，才标注来源
- 来源标注格式：[来源: API名称] 或 [来源: 文档名#编号]
- 绝对禁止编造来源：如 [来源: 文档名称]、[来源: 模板]、[来源: 旅行攻略.pdf] 等都是不允许的
- 如果某条信息没有对应数据来源，不要写任何来源标注，直接写内容即可
- 禁止在结尾写任何"未获取到资源"/"无法获取数据"等免责声明，这与上文已引用的来源自相矛盾
- 示例：东京明日天气：晴，26°C [来源: Open-Meteo 天气预报]
- 示例：1万预算约兑换1400美元 [来源: ExchangeRate-API 汇率]""",

        "work": """你是一个专业的项目管理顾问。请根据用户提供的信息，制定一个高效的工作计划。

要求：
1. 任务分解要合理，时间安排要现实
2. 包含里程碑、任务列表、时间线
3. 如果提供了节假日信息，要避开节假日安排工作
4. 如果提供了团队信息，要考虑团队协作
5. 使用清晰的格式，包含：项目目标、任务分解、时间安排、资源需求
6. 用中文回答

【强制格式要求 - 必须遵守】
- 只有当你确实从【知识库参考】或【外部资源查询结果】中看到了具体数据时，才标注来源
- 来源标注格式：[来源: API名称] 或 [来源: 文档名#编号]
- 绝对禁止编造来源：如 [来源: 文档名称]、[来源: 模板]、[来源: 项目计划.pdf] 等都是不允许的
- 如果某条信息没有对应数据来源，不要写任何来源标注，直接写内容即可
- 禁止在结尾写任何"未获取到资源"/"无法获取数据"等免责声明，这与上文已引用的来源自相矛盾
- 示例：8月有3个休息日，建议避开 [来源: timor.tech 中国节假日]
- 示例：建议每周召开1次进度会议（无来源，直接写即可，不需要任何说明）""",

        "finance": """你是一个专业的财务顾问。请根据用户提供的信息，制定一个合理的财务计划。

要求：
1. 计划要量入为出，符合用户的收入情况
2. 包含储蓄计划、支出预算，投资建议
3. 如果提供了汇率信息，要在计划中引用
4. 如果提供了经济数据，要在投资建议中参考
5. 使用清晰的格式，包含：财务目标、月度计划、储蓄策略，投资建议
6. 用中文回答

【强制格式要求 - 必须遵守】
- 只有当你确实从【知识库参考】或【外部资源查询结果】中看到了具体数据时，才标注来源
- 来源标注格式：[来源: API名称] 或 [来源: 文档名#编号]
- 绝对禁止编造来源：如 [来源: 文档名称]、[来源: 模板]、[来源: 财务计划.pdf] 等都是不允许的
- 如果某条信息没有对应数据来源，不要写任何来源标注，直接写内容即可
- 禁止在结尾写任何"未获取到资源"/"无法获取数据"等免责声明，这与上文已引用的来源自相矛盾
- 示例：当前汇率 1 USD = 7.25 CNY [来源: ExchangeRate-API 汇率]
- 示例：建议每月储蓄收入的20%（无来源，直接写即可，不需要任何说明）""",
    }

    return prompts.get(plan_type, prompts["learning"])


def _build_plan_user_prompt(
    plan_type: str,
    plan_info: Dict[str, Any],
    api_results: Dict[str, Any],
    rag_context: Optional[str]
) -> str:
    """构建计划生成的用户提示词（带来源标注版）"""

    # 1. 用户填写的信息
    info_text = "【用户信息】\n"
    for key, value in plan_info.items():
        if value and key != "_api_data":
            field_names = {
                "topic": "学习主题", "goal": "目标", "duration": "时长",
                "daily_hours": "每天学习时间", "level": "当前水平",
                "destination": "目的地", "days": "天数", "budget": "预算",
                "interests": "兴趣", "task": "任务", "team_size": "团队人数",
                "monthly_income": "月收入", "current_savings": "当前储蓄",
                "activity_level": "运动强度", "height": "身高", "weight": "体重",
                "age": "年龄", "gender": "性别", "location": "所在城市",
                "departure_date": "出发日期", "city": "出发城市",
                "target_currency": "目标币种", "deadline": "截止日期",
            }
            field_name = field_names.get(key, key)
            info_text += f"- {field_name}: {value}\n"

    # 2. RAG 知识库内容（强制带文档来源）
    rag_text = ""
    if rag_context and len(rag_context.strip()) > 10:
        # 如果 rag_context 中已有来源标注，保持原样；否则追加通用标注
        if "[来源:" not in rag_context:
            rag_text = f"\n【知识库参考】（来自您上传的文档）\n{rag_context}\n"
        else:
            rag_text = f"\n【知识库参考】\n{rag_context}\n"

    # 3. API 数据（每个 API 必须标注来源）
    api_text = ""
    if api_results:
        api_text = "\n【外部资源查询结果】\n"

        # API 名称 → 中文显示名 + 来源标注
        api_source_map = {
            # 学习计划 API
            "search_open_library": ("书籍推荐", "Open Library（openlibrary.org）"),
            "search_gutendex": ("电子书搜索", "Gutendex（gutendex.com）"),
            "search_crossref": ("学术论文搜索", "Crossref（crossref.org）"),
            "get_jinrishici": ("古诗词推荐", "今日诗词（jinrishici.com）"),
            "get_hitokoto": ("随机名句", "一言（hitokoto.cn）"),
            "search_poetrydb": ("英文诗歌库", "PoetryDB（poetrydb.org）"),
            # 健康计划 API
            "get_weather_forecast": ("天气预报", "Open-Meteo（open-meteo.com）"),
            "get_themealdb": ("健康食谱", "TheMealDB（themealdb.com）"),
            "get_wger_exercises": ("运动动作库", "wger（wger.de）"),
            "get_wger_muscles": ("肌肉群信息", "wger（wger.de）"),
            "get_amap_weather": ("国内天气", "高德天气（amap.com）"),
            "get_ip_location": ("地理位置", "ip-api（ip-api.com）"),
            "get_food_nutrition": ("食物营养数据", "Open Food Facts（openfoodfacts.org）"),
            "get_fruit_nutrition": ("水果营养数据", "Fruityvice（fruityvice.com）"),
            # 旅行计划 API
            "get_exchange_rates": ("汇率查询", "ExchangeRate-API"),
            "get_china_holidays": ("中国节假日", "timor.tech"),
            "get_city_bikes": ("城市单车租赁点", "City Bikes（citybik.es）"),
            "get_open_brewery": ("当地特色饮品店", "Open Brewery DB（openbrewerydb.org）"),
            "get_world_time": ("当地时间", "WorldTimeAPI（worldtimeapi.org）"),
            # 工作计划 API
            "get_open_trivia": ("知识问答", "Open Trivia（opentdb.com）"),
            "get_json_placeholder": ("任务模板示例", "JSONPlaceholder（jsonplaceholder.typicode.com）"),
            # 财务计划 API
            "get_economic_data": ("经济数据", "Econdb（econdb.com）"),
            "get_sec_edgar": ("上市公司财报", "SEC EDGAR（sec.gov）"),
            "get_portfolio_optimizer": ("投资组合分析", "Portfolio Optimizer"),
        }

        for api_name, result in api_results.items():
            if "error" in result:
                api_text += f"【{api_name}】查询失败：{result['error']}\n"
                continue

            api_display, source_label = api_source_map.get(
                api_name, (api_name, f"{api_name} API")
            )
            api_text += f"\n■ {api_display} [来源: {source_label}]\n"

            # 根据 API 类型提取有意义的数据片段
            if api_name == "search_open_library" and "books" in result:
                books = result.get("books", [])[:3]
                if books:
                    api_text += "推荐书籍：\n"
                    for book in books:
                        title = book.get("title", "未知")
                        author = book.get("author", "未知")
                        year = book.get("year", "")
                        url = book.get("url", "")
                        api_text += f"  - 《{title}》- {author}（{year}）{f' {url}' if url else ''} [来源: Open Library]\n"

            elif api_name == "search_gutendex" and "books" in result:
                books = result.get("books", [])[:3]
                if books:
                    api_text += "免费电子书：\n"
                    for book in books:
                        title = book.get("title", "未知")
                        author = book.get("author", "未知")
                        api_text += f"  - 《{title}》- {author}\n"

            elif api_name == "get_weather_forecast":
                forecast = result.get("forecast", [])[:5]
                current = result.get("current", {})
                if current:
                    temp = current.get("temperature", "N/A")
                    weather = current.get("weather", "N/A")
                    api_text += f"当前天气：{temp}°C，{weather}\n"
                if forecast:
                    api_text += "预报：\n"
                    for day in forecast:
                        date = day.get("date", day.get("time", ""))
                        max_t = day.get("max_temp", day.get("temperature_2m_max", ""))
                        min_t = day.get("min_temp", day.get("temperature_2m_min", ""))
                        weather = day.get("weather", "")
                        api_text += f"  - {date}: {min_t}°C ~ {max_t}°C，{weather}\n"

            elif api_name == "get_exchange_rates" and "rates" in result:
                rates = result.get("rates", {})
                currencies = list(rates.keys())[:5]
                for curr in currencies:
                    api_text += f"  1 CNY = {rates.get(curr, 'N/A')} {curr}\n"

            elif api_name == "get_food_nutrition" and "product" in result:
                prod = result.get("product", {})
                name = prod.get("product_name", "未知")
                cal = prod.get("nutriments", {}).get("energy-kcal_100g", "N/A")
                api_text += f"  {name}: {cal}大卡/100g\n"

            elif api_name == "get_fruit_nutrition":
                if isinstance(result, dict) and "nutritions" in result:
                    for item in result.get("nutritions", [])[:3]:
                        name = item.get("name", "")
                        cal = item.get("calories", "")
                        api_text += f"  {name}: {cal}大卡/100g\n"
                elif "name" in result:
                    api_text += f"  {result.get('name', '')}: {result.get('calories', '')}大卡/100g\n"

            elif api_name == "get_china_holidays":
                holidays = result.get("holidays", [])[:5]
                if holidays:
                    api_text += "节假日：\n"
                    for h in holidays:
                        name = h.get("name", h.get("holidayName", ""))
                        date = h.get("date", "")
                        if name:
                            api_text += f"  - {date} {name}\n"

            elif api_name == "get_world_time":
                tz = result.get("timezone", "")
                now = result.get("datetime", "")
                api_text += f"  时区: {tz}，当前时间: {now}\n"

            elif api_name == "get_ip_location":
                city = result.get("city", "")
                country = result.get("country", "")
                api_text += f"  位置: {city}, {country}\n"
            
            # 新增国内免费 API 数据解析
            elif api_name == "get_jinrishici":
                content = result.get("content", "")
                title = result.get("title", "")
                author = result.get("author", "")
                dynasty = result.get("dynasty", "")
                if content:
                    api_text += f"  「{content}」\n"
                    if title and author:
                        api_text += f"  —— {author}《{title}》{f'（{dynasty}）' if dynasty else ''}\n"
            
            elif api_name == "get_hitokoto":
                content = result.get("content", "")
                author = result.get("author", "")
                source_name = result.get("source_name", "")
                if content:
                    api_text += f"  「{content}」\n"
                    if author or source_name:
                        api_text += f"  —— {author or source_name}\n"
            
            elif api_name == "get_themealdb" and "meals" in result:
                meals = result.get("meals", [])[:3]
                if meals:
                    api_text += "推荐食谱：\n"
                    for meal in meals:
                        name = meal.get("name", "未知")
                        category = meal.get("category", "")
                        area = meal.get("area", "")
                        ingredients = meal.get("ingredients", [])[:5]
                        api_text += f"  - {name}（{category}/{area}）\n"
                        if ingredients:
                            api_text += f"    食材: {', '.join(ingredients)}\n"
            
            elif api_name == "get_wger_exercises" and "exercises" in result:
                exercises = result.get("exercises", [])[:5]
                if exercises:
                    api_text += "运动动作推荐：\n"
                    for ex in exercises:
                        name = ex.get("name", "未知")
                        desc = ex.get("description", "")[:100] if ex.get("description") else ""
                        api_text += f"  - {name}\n"
                        if desc:
                            api_text += f"    {desc}...\n"
            
            elif api_name == "get_wger_muscles" and "muscles" in result:
                muscles = result.get("muscles", [])[:10]
                if muscles:
                    api_text += "肌肉群列表：\n"
                    for m in muscles:
                        name = m.get("name", "")
                        name_en = m.get("name_en", "")
                        api_text += f"  - {name}（{name_en}）\n"
            
            elif api_name == "get_amap_weather" and "weather" in result:
                weather_list = result.get("weather", [])[:5]
                city = result.get("city", "")
                if weather_list:
                    api_text += f"{city}天气预报：\n"
                    for w in weather_list:
                        date = w.get("date", "")
                        day_weather = w.get("day_weather", "")
                        night_weather = w.get("night_weather", "")
                        day_temp = w.get("day_temp", "")
                        night_temp = w.get("night_temp", "")
                        api_text += f"  - {date}: 白天{day_weather}{day_temp}°C，夜间{night_weather}{night_temp}°C\n"

            elif api_name == "get_city_bikes":
                networks = result.get("networks", [])[:3]
                if networks:
                    api_text += "可用共享单车：\n"
                    for n in networks:
                        name = n.get("name", n.get("location", {}).get("city", ""))
                        api_text += f"  - {name}\n"

            elif api_name == "get_open_brewery":
                breweries = result.get("breweries", [])[:3]
                if breweries:
                    api_text += "附近精酿啤酒：\n"
                    for b in breweries:
                        name = b.get("name", "")
                        city = b.get("city", "")
                        api_text += f"  - {name}（{city}）\n"

            elif api_name == "get_open_trivia":
                results = result.get("results", [])[:3]
                if results:
                    api_text += "知识问答示例：\n"
                    for q in results:
                        cat = q.get("category", "")
                        diff = q.get("difficulty", "")
                        api_text += f"  - [{cat}][{diff}] {q.get('question', '')[:50]}...\n"

            elif api_name == "get_economic_data":
                data = result.get("data", {})
                api_text += f"  经济数据: {str(data)[:200]}\n"

            elif api_name == "get_sec_edgar":
                company = result.get("company_name", "")
                sic = result.get("sic", "")
                api_text += f"  公司: {company}, 行业代码: {sic}\n"

            elif api_name == "get_ibanforge":
                valid = result.get("valid", False)
                api_text += f"  IBAN验证: {'有效' if valid else '无效'}\n"

            elif api_name == "get_portfolio_optimizer":
                api_text += f"  投资组合优化数据: {str(result)[:200]}\n"

            elif api_name == "get_json_placeholder":
                posts = result.get("posts", [])[:2]
                if posts:
                    api_text += "模拟任务示例：\n"
                    for p in posts:
                        api_text += f"  - {p.get('title', '')[:40]}\n"

            elif api_name == "get_random_data":
                api_text += f"  随机数据: {str(result)[:200]}\n"

            elif api_name == "search_poetrydb":
                poems = result.get("poems", [])[:2]
                if poems:
                    api_text += "诗歌：\n"
                    for p in poems:
                        title = p.get("title", "")
                        author = p.get("author", "")
                        lines = (p.get("lines", []) or [""])[:2]
                        api_text += f"  - 《{title}》- {author}: {' / '.join(lines)}\n"

            elif api_name == "search_crossref":
                items = result.get("items", [])[:2]
                if items:
                    api_text += "学术论文：\n"
                    for item in items:
                        title = item.get("title", [""])[0]
                        doi = item.get("DOI", "")
                        api_text += f"  - {title[:60]}... DOI: {doi}\n"

            elif api_name == "search_gutendex" and "books" in result:
                books = result.get("books", [])[:3]
                if books:
                    api_text += "免费电子书：\n"
                    for book in books:
                        title = book.get("title", "未知")
                        author = book.get("author", "未知")
                        formats = book.get("formats", [])
                        readable = [f for f in formats if "text" in f.lower() or "application" in f.lower()]
                        readable_str = f"（{'/'.join(readable[:2])})" if readable else ""
                        api_text += f"  - 《{title}》- {author} {readable_str} [来源: Gutendex]\n"

            elif api_name == "search_crossref" and "articles" in result:
                articles = result.get("articles", [])[:3]
                if articles:
                    api_text += "学术论文：\n"
                    for art in articles:
                        title = art.get("title", "未知")
                        authors = art.get("authors", [])
                        author_str = "、".join(authors[:2]) + ("等" if len(authors) > 2 else "")
                        year = art.get("year", "")
                        doi = art.get("doi", "")
                        api_text += f"  - {title[:60]}{'...' if len(title) > 60 else ''}\n    作者: {author_str}（{year}）DOI: {doi}\n"
                else:
                    api_text += "  （未检索到相关学术论文，可能需要更具体的关键词）\n"

            elif api_name == "search_poetrydb" and "poems" in result:
                poems = result.get("poems", [])[:2]
                if poems:
                    api_text += "诗歌：\n"
                    for p in poems:
                        title = p.get("title", "")
                        author = p.get("author", "")
                        lines = (p.get("lines") or [])[:3]
                        api_text += f"  - 《{title}》- {author}: {' / '.join(lines)}\n"
                else:
                    api_text += "  （未检索到相关诗歌，可尝试更具体的关键词）\n"

            elif api_name == "search_quran":
                results_list = result.get("results", [])[:2]
                if results_list:
                    api_text += "古兰经相关章节：\n"
                    for r in results_list:
                        surah = r.get("surah", "")
                        text = r.get("text", "")[:60]
                        api_text += f"  - {surah}: {text}...\n"

            else:
                # 兜底：先检查是否真的没有数据（可能是 API 返回空）
                non_error_keys = [k for k, v in result.items() if k != "error" and v]
                if not non_error_keys:
                    api_text += f"  （{api_name} 本次未返回有效数据，可忽略此来源）\n"
                else:
                    # 有数据但没匹配到上面的格式，截取显示
                    result_str = str(result)
                    if len(result_str) > 300:
                        result_str = result_str[:300] + "..."
                    api_text += f"  {result_str}\n"

    # 4. 生成指令（强调必须标注来源）
    instruction = f"""
请根据以上信息，制定一个详细的{plan_type}计划。

【重要】请在计划中引用每一条外部数据，格式示例：
- 《Python编程》- 作者 [来源: Open Library]
- 北京明天中雨 [来源: Open-Meteo 天气预报]
- 广州2026-08-01为工作日 [来源: timor.tech 中国节假日]

如果没有某类数据，也请直接说明"本次未查询到XX数据"，不要捏造。
"""
    return info_text + rag_text + api_text + instruction


def _generate_plan_with_template(
    plan_type: str,
    plan_info: Dict[str, Any],
    api_results: Dict[str, Any],
    rag_context: Optional[str]
) -> str:
    """Fallback: 使用模板生成计划（当 LLM 失败时）"""
    # 导入模板函数
    from app.skills.plan_templates import (
        generate_learning_plan,
        generate_health_plan,
        generate_travel_plan,
        generate_work_plan,
        generate_finance_plan
    )

    # 添加 API 数据到 plan_info
    plan_info["_api_data"] = api_results

    # 调用对应的模板函数
    if plan_type == "learning":
        return generate_learning_plan(plan_info, rag_context)
    elif plan_type == "health":
        return generate_health_plan(plan_info, rag_context)
    elif plan_type == "travel":
        return generate_travel_plan(plan_info, rag_context)
    elif plan_type == "work":
        return generate_work_plan(plan_info, rag_context)
    elif plan_type == "finance":
        return generate_finance_plan(plan_info, rag_context)
    else:
        return "生成计划失败，请稍后重试。"

# ─── 信息提取 ──────────────────────────────────────────────────

def extract_info_from_input(user_input: str, plan_type: str) -> Dict[str, Any]:
    """从用户输入中提取信息（智能版）

    优先使用 LLM JSON mode 提取，失败时 fallback 到规则提取。
    """
    info = {}

    if not user_input or not isinstance(user_input, str):
        return info

    # 尝试使用 LLM 提取（更智能）
    try:
        llm_result = _extract_with_llm(user_input, plan_type)
        if llm_result and len(llm_result) > 0:
            print(f"[DEBUG] LLM extraction successful: {llm_result}")
            return llm_result
    except Exception as e:
        print(f"[WARNING] LLM extraction failed, falling back to rules: {e}")

    # Fallback 到规则提取
    # 检查是否是逗号分隔的列表格式
    if "," in user_input and len(user_input.split(",")) >= 3:
        return _extract_from_comma_separated(user_input, plan_type)

    # 否则使用自然语言提取
    return _extract_from_natural_language(user_input, plan_type)


def _extract_with_llm(user_input: str, plan_type: str) -> Dict[str, Any]:
    """使用 LLM JSON mode 提取信息（更智能）"""
    from app.common.llm_factory import get_llm

    # 构建提取提示词
    field_definitions = _get_field_definitions(plan_type)

    prompt = f"""从用户输入中提取计划相关信息，返回 JSON 格式。

计划类型：{plan_type}
用户输入："{user_input}"

需要提取的字段：
{field_definitions}

规则：
1. 只返回 JSON，不要其他内容
2. 如果某个字段没有提到，不要包含在 JSON 中
3. 尽量理解用户的意图，而不是死板匹配关键词
4. 支持中文量词（如"一个星期"、"两个月"）
5. 支持口语化表达（如"每天俩小时"、"完全没基础"）

示例输出格式：
{{"topic": "Python", "goal": "入门", "duration": "1个月", "daily_hours": 2, "level": "零基础"}}
"""

    try:
        llm = get_llm(temperature=0.1, force_ollama=True)  # 低温度，更精确

        # 使用 invoke 方法（LangChain 标准接口）
        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content=prompt)]
        result = llm.invoke(messages)

        # 提取响应内容
        if hasattr(result, 'content'):
            response = result.content
        else:
            response = str(result)

        # 解析 JSON
        import json
        # 清理可能的 markdown 代码块
        response = response.strip()
        if response.startswith("```"):
            # 移除 ```json 和 ```
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        extracted = json.loads(response)

        # 验证字段是否合法
        valid_fields = _get_valid_fields(plan_type)
        validated = {}
        for field, value in extracted.items():
            if field in valid_fields and value:
                validated[field] = value

        return validated

    except Exception as e:
        print(f"[ERROR] LLM extraction error: {e}")
        return {}


def _get_field_definitions(plan_type: str) -> str:
    """获取字段定义（用于 LLM 提示词）"""
    definitions = {
        "learning": """
- topic: 学习主题（如 Python、英语、编程、设计、知识库内容）
- goal: 学习目标（如 入门、进阶、实战、考试准备）
- duration: 学习时长（如 1个月、3个月、一个星期、半年）
- daily_hours: 每天学习时间（如 1小时、2小时、每天俩小时）
- level: 基础水平（如 零基础、初学者、有一定基础、完全没基础）
""",
        "health": """
- goal: 健康目标（如 减肥、增肌、保持健康、改善睡眠）
- duration: 计划时长（如 1个月、3个月、半年）
- activity_level: 运动强度（低/中/高）
- height: 身高（cm）
- weight: 体重（kg）
- age: 年龄
- gender: 性别（男/女）
- location: 所在城市
""",
        "travel": """
- destination: 目的地（如 北京、上海、日本、欧洲）
- days: 旅行天数（如 3天、5天、一个星期）
- budget: 预算（如 1000元、5000元、1万元）
- interests: 兴趣（如 文化、美食、自然、购物）
- departure_date: 出发日期
- city: 出发城市
- target_currency: 目标币种
""",
        "work": """
- task: 任务名称（如 项目开发、产品设计、市场推广）
- duration: 计划时长（如 2周、1个月、3个月）
- team_size: 团队人数
- deadline: 截止日期
""",
        "finance": """
- goal: 财务目标（如 存5万、理财、投资、还债）
- duration: 计划时长（如 1年、2年、5年）
- monthly_income: 月收入
- current_savings: 当前存款
- target_currency: 主要币种
""",
    }
    return definitions.get(plan_type, "")


def _get_valid_fields(plan_type: str) -> List[str]:
    """获取合法的字段名"""
    fields = {
        "learning": ["topic", "goal", "duration", "daily_hours", "level"],
        "health": ["goal", "duration", "activity_level", "height", "weight", "age", "gender", "location"],
        "travel": ["destination", "days", "budget", "interests", "departure_date", "city", "target_currency"],
        "work": ["task", "duration", "team_size", "deadline"],
        "finance": ["goal", "duration", "monthly_income", "current_savings", "target_currency"],
    }
    return fields.get(plan_type, [])


def _extract_from_comma_separated(user_input: str, plan_type: str) -> Dict[str, Any]:
    """从逗号分隔的输入中提取信息（智能版）

    格式：value1,value2,value3,...
    根据值的特征智能匹配字段，而不是简单按顺序赋值
    """
    info = {}
    parts = [p.strip() for p in user_input.split(",")]

    if plan_type == "learning":
        # 学习计划：智能识别每个值的类型
        for value in parts:
            value_lower = value.lower()

            # 1. 识别时长（包含数字+时间单位，或量词+时间单位）
            if re.search(r"(\d+)(个月|周|天|年|小时|分钟)", value) and "duration" not in info:
                info["duration"] = value
            elif re.search(r"(一|两|二|三|四|五|六|七|八|九|十)(个)?(月|周|天|年|小时|分钟)", value) and "duration" not in info:
                info["duration"] = value

            # 2. 识别每天学习时间（包含"每天"或"小时"）
            elif re.search(r"每天|(\d+)小时", value) and "daily_hours" not in info:
                # 提取小时数
                hours_match = re.search(r"(\d+)小时", value)
                if hours_match:
                    info["daily_hours"] = int(hours_match.group(1))
                else:
                    info["daily_hours"] = value

            # 3. 识别目标（关键词匹配，但要排除"学习"开头的短语）
            elif any(kw in value for kw in ["入门", "进阶", "实战", "考试", "基础", "提高"]) and "goal" not in info:
                # 排除以"学习"开头的短语（如"学习知识库内容"应该被识别为topic）
                if not value.startswith("学习"):
                    info["goal"] = value

            # 4. 识别基础水平
            elif any(kw in value for kw in ["零基础", "初学者", "新手", "有一定基础", "基础"]) and "level" not in info:
                info["level"] = value

            # 5. 识别主题（如果还没找到主题，且不是其他类型）
            elif "topic" not in info and not any(kw in value_lower for kw in ["小时", "天", "周", "月", "年"]):
                # 检查是否是主题关键词
                topic_keywords = ["python", "英语", "编程", "java", "javascript", "设计", "ai", "知识库", "内容"]
                if any(kw in value_lower for kw in topic_keywords):
                    info["topic"] = value

        # 6. 如果还没找到 goal，检查是否有考试相关关键词
        if "goal" not in info:
            for value in parts:
                if any(kw in value for kw in ["考试", "考研", "考证", "认证"]):
                    info["goal"] = "考试准备"
                    break

        # 7. 如果还没找到 topic，且第一个值不是其他类型，则作为 topic
        if "topic" not in info and parts:
            first_value = parts[0]
            # 如果第一个值不是时长、目标或水平，则作为主题
            if not re.search(r"(\d+)(个月|周|天|年|小时|分钟)", first_value) and \
               not any(kw in first_value for kw in ["入门", "进阶", "实战", "考试", "零基础", "初学者"]):
                info["topic"] = first_value

    elif plan_type == "health":
        # 健康计划：智能识别
        for value in parts:
            # 1. 识别时长
            if re.search(r"(\d+)(个月|周|天|年)", value) and "duration" not in info:
                info["duration"] = value

            # 2. 识别身高（数字+cm/厘米）
            elif re.search(r"(\d+)(cm|厘米)", value) and "height" not in info:
                height_match = re.search(r"(\d+)", value)
                if height_match:
                    info["height"] = int(height_match.group(1))

            # 3. 识别体重（数字+kg/公斤/千克）
            elif re.search(r"(\d+)(kg|公斤|千克)", value) and "weight" not in info:
                weight_match = re.search(r"(\d+)", value)
                if weight_match:
                    info["weight"] = int(weight_match.group(1))

            # 4. 识别年龄（纯数字，且在合理范围内）
            elif re.match(r"^\d+$", value) and "age" not in info:
                age = int(value)
                if 1 <= age <= 120:  # 合理的年龄范围
                    info["age"] = age

            # 5. 识别性别
            elif value in ["男", "女", "男性", "女性"] and "gender" not in info:
                info["gender"] = value

            # 6. 识别城市
            elif any(city in value for city in ["北京", "上海", "广州", "深圳", "成都", "杭州", "武汉", "西安", "南京", "重庆"]) and "location" not in info:
                info["location"] = value

            # 7. 识别运动强度
            elif any(kw in value for kw in ["高强度", "HIIT", "中强度", "低强度", "中等"]) and "activity_level" not in info:
                if "高" in value or "HIIT" in value:
                    info["activity_level"] = "高"
                elif "中" in value:
                    info["activity_level"] = "中"
                elif "低" in value:
                    info["activity_level"] = "低"

            # 8. 识别目标（最后，因为目标关键词可能比较通用）
            elif any(kw in value for kw in ["减肥", "增肌", "健康", "瘦身", "减脂"]) and "goal" not in info:
                info["goal"] = value

    elif plan_type == "travel":
        # 旅行计划：智能识别
        for value in parts:
            # 1. 识别天数（数字+天/日）
            if re.search(r"(\d+)(天|日)", value) and "days" not in info:
                days_match = re.search(r"(\d+)", value)
                if days_match:
                    info["days"] = int(days_match.group(1))

            # 2. 识别预算（数字+万/千/元）
            elif re.search(r"(\d+)(万|千|元)", value) and "budget" not in info:
                info["budget"] = value

            # 3. 识别目的地
            elif any(dest in value for dest in ["北京", "上海", "广州", "深圳", "成都", "杭州", "日本", "韩国", "泰国", "欧洲", "美国"]) and "destination" not in info:
                info["destination"] = value

            # 4. 识别兴趣
            elif any(kw in value for kw in ["文化", "美食", "自然", "购物", "历史"]) and "interests" not in info:
                info["interests"] = value

    elif plan_type == "work":
        # 工作计划：智能识别
        for value in parts:
            # 1. 识别时长
            if re.search(r"(\d+)(个月|周|天)", value) and "duration" not in info:
                info["duration"] = value

            # 2. 识别团队人数（数字+人/团队/多人）
            elif re.search(r"(\d+)(人|团队|多人)", value) and "team_size" not in info:
                team_match = re.search(r"(\d+)", value)
                if team_match:
                    info["team_size"] = int(team_match.group(1))

            # 3. 识别截止日期（日期格式）
            elif re.search(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}", value) and "deadline" not in info:
                info["deadline"] = value

            # 4. 识别任务
            elif any(kw in value for kw in ["项目", "产品", "开发", "设计", "推广"]) and "task" not in info:
                info["task"] = value

    elif plan_type == "finance":
        # 财务计划：智能识别
        for value in parts:
            # 1. 识别时长
            if re.search(r"(\d+)(年|个月|周)", value) and "duration" not in info:
                info["duration"] = value

            # 2. 识别金额（数字+万/千/元）
            elif re.search(r"(\d+)(万|千|元)", value) and "goal" not in info:
                info["goal"] = f"存{value}"

            # 3. 识别月收入
            elif "月" in value and re.search(r"\d+", value) and "monthly_income" not in info:
                info["monthly_income"] = value

            # 4. 识别当前存款
            elif "存款" in value or "存" in value and "current_savings" not in info:
                info["current_savings"] = value

            # 5. 识别目标
            elif any(kw in value for kw in ["存钱", "理财", "投资", "还债"]) and "goal" not in info:
                info["goal"] = value

    return info


def _extract_from_natural_language(user_input: str, plan_type: str) -> Dict[str, Any]:
    """从自然语言输入中提取信息"""
    info = {}

    if plan_type == "learning":
        # 提取主题（扩展关键词）
        topic_keywords = {
            "python": ["python", "py", "django", "flask"],
            "英语": ["英语", "英文", "english", "单词", "词汇"],
            "编程": ["编程", "代码", "开发", "程序", "coding", "programming"],
            "java": ["java", "spring", "springboot"],
            "javascript": ["javascript", "js", "vue", "react", "node"],
            "设计": ["设计", "ui", "ux", "photoshop", "ps"],
            "ai": ["ai", "人工智能", "机器学习", "深度学习", "ml", "dl"],
        }
        for topic_key, keywords in topic_keywords.items():
            if any(kw in user_input.lower() for kw in keywords):
                info["topic"] = topic_key
                break

        # 提取时长（支持更多格式）
        duration_match = re.search(r"(\d+)(个月|周|天|年|小时|分钟)", user_input)
        if duration_match:
            info["duration"] = duration_match.group(0)

        # 提取目标
        goal_keywords = {
            "入门": ["入门", "基础", "初学", "新手", "零基础"],
            "进阶": ["进阶", "提高", "提升", "中级", "高级"],
            "实战": ["实战", "项目", "实践", "应用", "开发"],
            "考试": ["考试", "考研", "考证", "认证", "面试"],
        }
        for goal_key, keywords in goal_keywords.items():
            if any(kw in user_input for kw in keywords):
                info["goal"] = goal_key
                break

    elif plan_type == "health":
        # 提取目标（扩展关键词）
        goal_keywords = {
            "减肥": ["减肥", "瘦身", "减脂", "减重", "瘦"],
            "增肌": ["增肌", "增重", "肌肉", "力量", "健身"],
            "保持健康": ["健康", "养生", "保健", "调理"],
            "改善睡眠": ["睡眠", "失眠", "早睡", "休息"],
            "提升运动能力": ["运动", "体能", "耐力", "跑步", "游泳"],
        }
        for goal_key, keywords in goal_keywords.items():
            if any(kw in user_input for kw in keywords):
                info["goal"] = goal_key
                break

        # 提取时长（支持更多格式）
        duration_match = re.search(r"(\d+)(个月|周|天|年)", user_input)
        if duration_match:
            info["duration"] = duration_match.group(0)

        # 提取运动强度（扩展关键词）
        if any(kw in user_input for kw in ["高强度", "HIIT", "高强度间歇", "剧烈"]):
            info["activity_level"] = "高"
        elif any(kw in user_input for kw in ["中强度", "跑步", "游泳", "中等"]):
            info["activity_level"] = "中"
        elif any(kw in user_input for kw in ["低强度", "散步", "瑜伽", "拉伸", "轻松"]):
            info["activity_level"] = "低"

        # 提取身高体重（如果有）
        height_match = re.search(r"(\d+)(cm|厘米)", user_input)
        if height_match:
            info["height"] = height_match.group(1)

        weight_match = re.search(r"(\d+)(kg|公斤|千克)", user_input)
        if weight_match:
            info["weight"] = weight_match.group(1)

        # 提取城市（如果有）
        city_keywords = ["北京", "上海", "广州", "深圳", "成都", "杭州", "武汉", "西安", "南京", "重庆"]
        for city in city_keywords:
            if city in user_input:
                info["location"] = city
                break

    elif plan_type == "travel":
        # 提取目的地（简化版）
        destinations = ["北京", "上海", "广州", "深圳", "成都", "杭州", "日本", "韩国", "泰国", "欧洲", "美国"]
        for dest in destinations:
            if dest in user_input:
                info["destination"] = dest
                break

        # 提取天数
        days_match = re.search(r"(\d+)(天|日)", user_input)
        if days_match:
            info["days"] = int(days_match.group(1))

        # 提取预算
        budget_match = re.search(r"(\d+)(万|千|元)", user_input)
        if budget_match:
            info["budget"] = budget_match.group(0)

    elif plan_type == "work":
        # 提取任务
        if "项目" in user_input:
            info["task"] = "项目开发"
        elif "产品" in user_input:
            info["task"] = "产品设计"
        else:
            info["task"] = "工作任务"

        # 提取时长
        duration_match = re.search(r"(\d+)(个月|周|天)", user_input)
        if duration_match:
            info["duration"] = duration_match.group(0)

    elif plan_type == "finance":
        # 提取目标
        if "存钱" in user_input or "存" in user_input:
            info["goal"] = "存钱"
        elif "理财" in user_input:
            info["goal"] = "理财"
        elif "投资" in user_input:
            info["goal"] = "投资"

        # 提取金额
        amount_match = re.search(r"(\d+)(万|千|元)", user_input)
        if amount_match:
            info["goal"] = f"存{amount_match.group(0)}"

        # 提取时长
        duration_match = re.search(r"(\d+)(年|个月|周)", user_input)
        if duration_match:
            info["duration"] = duration_match.group(0)

    return info

# ─── 计划生成主函数 ────────────────────────────────────────────

def generate_plan(plan_type: str, plan_info: Dict[str, Any], api_results: Dict[str, Any],
                  rag_context: Optional[str] = None, context_summary: Optional[str] = None) -> str:
    """生成计划的主函数

    Args:
        plan_type: 计划类型（learning/health/travel/work/finance）
        plan_info: 用户填写的字段信息
        api_results: 外部 API 调用结果
        rag_context: 知识库查询结果（来自 RAG）
        context_summary: 上下文历史摘要（从对话历史中提取）
    """

    # 1. 将 API 结果传递给模板（用于展示原始数据）
    plan_info["_api_data"] = api_results

    # 2. 构建完整的上下文（知识库 + 上下文历史）
    # 这样 LLM 在生成计划时，可以参考：
    # - 知识库中的相关内容（如用户上传的学习笔记）
    # - 对话历史中的相关信息（如用户之前提到的目标、偏好）
    full_context = ""
    if rag_context:
        full_context += f"\n\n【知识库参考】\n{rag_context}"
    if context_summary:
        full_context += f"\n\n【对话历史摘要】\n{context_summary}"

    # 3. 根据类型调用对应的 Skill 模板
    if plan_type == "learning":
        # 从 API 结果中提取书籍
        books = []
        if "search_open_library" in api_results and "books" in api_results["search_open_library"]:
            books.extend(api_results["search_open_library"]["books"])
        if "search_gutendex" in api_results and "books" in api_results["search_gutendex"]:
            books.extend(api_results["search_gutendex"]["books"])
        plan_info["books"] = books[:3]  # 最多3本书

        return generate_learning_plan(plan_info, full_context)

    elif plan_type == "health":
        # 从 API 结果中提取天气
        if "get_weather_forecast" in api_results:
            plan_info["weather"] = api_results["get_weather_forecast"]

        return generate_health_plan(plan_info, full_context)

    elif plan_type == "travel":
        # 从 API 结果中提取天气
        if "get_weather_forecast" in api_results:
            plan_info["weather"] = api_results["get_weather_forecast"]

        return generate_travel_plan(plan_info, full_context)

    elif plan_type == "work":
        # 从 API 结果中提取节假日
        if "get_china_holidays" in api_results:
            plan_info["holidays"] = api_results["get_china_holidays"]

        return generate_work_plan(plan_info, full_context)

    elif plan_type == "finance":
        # 从 API 结果中提取汇率
        if "get_exchange_rates" in api_results:
            plan_info["rates"] = api_results["get_exchange_rates"]

        return generate_finance_plan(plan_info, full_context)

    else:
        return "抱歉，暂不支持该类型的计划生成。"

# ─── 导出 ──────────────────────────────────────────────────────

__all__ = [
    "detect_plan_type",
    "handle_ambiguous_plan_type",
    "PlanInfoCollector",
    "PlanInfoCollectorManager",
    "select_learning_apis",
    "select_health_apis",
    "select_travel_apis",
    "select_work_apis",
    "select_finance_apis",
    "preview_apis_to_call",
    "call_apis_for_plan",
    "extract_info_from_input",
    "generate_plan"
]
