"""
Skills 包 - 计划模板和协调器

提供 5 种计划类型的模板生成功能：
- LearningPlan (学习计划)
- HealthPlan (健康计划)
- TravelPlan (旅行计划)
- WorkPlan (工作计划)
- FinancePlan (财务计划)
"""

from .plan_templates import (
    generate_learning_plan,
    generate_health_plan,
    generate_travel_plan,
    generate_work_plan,
    generate_finance_plan
)

from .plan_generator import (
    detect_plan_type,
    handle_ambiguous_plan_type,
    PlanInfoCollector,
    PlanInfoCollectorManager,
    generate_plan,
    call_apis_for_plan,
    preview_apis_to_call,
    extract_info_from_input
)

__all__ = [
    # 计划模板
    "generate_learning_plan",
    "generate_health_plan",
    "generate_travel_plan",
    "generate_work_plan",
    "generate_finance_plan",
    # 协调器
    "detect_plan_type",
    "handle_ambiguous_plan_type",
    "PlanInfoCollector",
    "PlanInfoCollectorManager",
    "generate_plan",
    "call_apis_for_plan",
    "extract_info_from_input"
]
