"""
工具参数验证器

在工具调用前验证参数，确保必填参数存在且格式正确。
避免AI生成错误参数导致工具调用失败。
"""

import re
from typing import Any, Dict, List, Optional, Tuple


class ValidationResult:
    """验证结果"""

    def __init__(self, is_valid: bool, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def __bool__(self):
        return self.is_valid

    def __str__(self):
        if self.is_valid:
            return "验证通过"
        return f"验证失败: {'; '.join(self.errors)}"


class ToolValidator:
    """工具参数验证器"""

    @staticmethod
    def validate_title(title: str) -> ValidationResult:
        """验证计划/帖子标题"""
        errors = []
        warnings = []

        if not title or not title.strip():
            errors.append("标题不能为空")
            return ValidationResult(False, errors)

        title = title.strip()

        if len(title) < 2:
            errors.append("标题太短，至少需要2个字符")

        if len(title) > 100:
            errors.append("标题太长，最多100个字符")

        if len(title) < 5:
            warnings.append("标题较短，建议更具体一些（如'每天背单词30个'）")

        return ValidationResult(len(errors) == 0, errors, warnings)

    @staticmethod
    def validate_content(content: str, min_length: int = 5, max_length: int = 2000) -> ValidationResult:
        """验证内容（帖子、计划描述等）"""
        errors = []
        warnings = []

        if not content or not content.strip():
            errors.append("内容不能为空")
            return ValidationResult(False, errors)

        content = content.strip()

        if len(content) < min_length:
            errors.append(f"内容太短，至少需要{min_length}个字符")

        if len(content) > max_length:
            errors.append(f"内容太长，最多{max_length}个字符")

        return ValidationResult(len(errors) == 0, errors, warnings)

    @staticmethod
    def validate_keyword(keyword: str) -> ValidationResult:
        """验证搜索关键词"""
        errors = []
        warnings = []

        if not keyword or not keyword.strip():
            errors.append("搜索关键词不能为空")
            return ValidationResult(False, errors)

        keyword = keyword.strip()

        if len(keyword) < 1:
            errors.append("关键词太短")

        if len(keyword) > 50:
            errors.append("关键词太长，最多50个字符")

        # 检查是否只包含特殊字符
        if not re.search(r'[一-龥a-zA-Z0-9]', keyword):
            errors.append("关键词必须包含中文、字母或数字")

        return ValidationResult(len(errors) == 0, errors, warnings)

    @staticmethod
    def validate_plan_id(plan_id: str) -> ValidationResult:
        """验证计划ID"""
        errors = []
        warnings = []

        if not plan_id or not str(plan_id).strip():
            errors.append("计划ID不能为空")
            return ValidationResult(False, errors)

        plan_id = str(plan_id).strip()

        # 检查是否为数字
        try:
            pid = int(plan_id)
            if pid <= 0:
                errors.append("计划ID必须是正整数")
        except ValueError:
            errors.append("计划ID必须是数字")

        return ValidationResult(len(errors) == 0, errors, warnings)

    @staticmethod
    def validate_display_id(display_id: int, max_id: int = 10) -> ValidationResult:
        """验证搜索结果序号"""
        errors = []
        warnings = []

        if not isinstance(display_id, int):
            errors.append("序号必须是整数")
            return ValidationResult(False, errors)

        if display_id < 1:
            errors.append("序号必须大于0")

        if display_id > max_id:
            errors.append(f"序号太大，最大可选{max_id}")

        return ValidationResult(len(errors) == 0, errors, warnings)

    @staticmethod
    def validate_user_id(user_id: str) -> ValidationResult:
        """验证用户ID"""
        errors = []
        warnings = []

        if not user_id or not str(user_id).strip():
            errors.append("用户ID不能为空")
            return ValidationResult(False, errors)

        user_id = str(user_id).strip()

        try:
            uid = int(user_id)
            if uid <= 0:
                errors.append("用户ID必须是正整数")
        except ValueError:
            errors.append("用户ID必须是数字")

        return ValidationResult(len(errors) == 0, errors, warnings)

    @staticmethod
    def validate_hashtags(hashtags: str) -> ValidationResult:
        """验证标签"""
        errors = []
        warnings = []

        if not hashtags:
            return ValidationResult(True)  # 标签是可选的

        hashtags = hashtags.strip()

        # 检查数量
        tag_list = [t.strip() for t in hashtags.split(",") if t.strip()]
        if len(tag_list) > 10:
            errors.append("标签太多，最多10个")

        # 检查每个标签长度
        for tag in tag_list:
            if len(tag) > 20:
                errors.append(f"标签'{tag}'太长，最多20个字符")
            if not re.match(r'^[一-龥a-zA-Z0-9_]+$', tag):
                errors.append(f"标签'{tag}'包含非法字符，只支持中文、字母、数字和下划线")

        return ValidationResult(len(errors) == 0, errors, warnings)

    @staticmethod
    def validate_category(category: str) -> ValidationResult:
        """验证计划类别"""
        valid_categories = ["LEARNING", "FITNESS", "HABIT", "CAREER", "PERSONAL", "HEALTH", "CREATIVE", "OTHER",
                           "学习", "健身", "习惯", "职业", "个人", "健康", "创意", "其他"]
        errors = []
        warnings = []

        if not category or not category.strip():
            errors.append("类别不能为空")
            return ValidationResult(False, errors)

        category = category.strip().upper()

        if category not in valid_categories and category.lower() not in [c.lower() for c in valid_categories]:
            errors.append(f"无效的类别，支持: {', '.join(valid_categories[:8])}")

        return ValidationResult(len(errors) == 0, errors, warnings)

    @staticmethod
    def validate_priority(priority: str) -> ValidationResult:
        """验证优先级"""
        valid_priorities = ["LOW", "MEDIUM", "HIGH", "URGENT", "低", "中", "高", "紧急"]
        errors = []
        warnings = []

        if not priority or not priority.strip():
            return ValidationResult(True)  # 优先级有默认值，可以为空

        priority = priority.strip().upper()

        if priority not in valid_priorities and priority.lower() not in [p.lower() for p in valid_priorities]:
            errors.append(f"无效的优先级，支持: {', '.join(valid_priorities[:4])}")

        return ValidationResult(len(errors) == 0, errors, warnings)


def validate_tool_params(tool_name: str, params: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    验证工具参数的主函数

    Args:
        tool_name: 工具名称
        params: 参数字典

    Returns:
        (是否通过, 错误列表, 警告列表)
    """
    validator = ToolValidator()

    if tool_name == "create_plan":
        title = params.get("title", "")
        result = validator.validate_title(title)
        return result.is_valid, result.errors, result.warnings

    elif tool_name == "create_post":
        content = params.get("content", "")
        result = validator.validate_content(content)
        if not result.is_valid:
            return result.is_valid, result.errors, result.warnings

        hashtags = params.get("hashtags", "")
        if hashtags:
            result = validator.validate_hashtags(hashtags)

        return result.is_valid, result.errors, result.warnings

    elif tool_name == "search_plans":
        keyword = params.get("keyword", "")
        result = validator.validate_keyword(keyword)
        return result.is_valid, result.errors, result.warnings

    elif tool_name == "get_item_detail":
        display_id = params.get("display_id", 0)
        result = validator.validate_display_id(display_id)
        return result.is_valid, result.errors, result.warnings

    elif tool_name == "check_in_plan":
        plan_id = params.get("plan_id", "")
        result = validator.validate_plan_id(plan_id)
        return result.is_valid, result.errors, result.warnings

    elif tool_name == "get_user_activity":
        user_id = params.get("user_id", "")
        result = validator.validate_user_id(user_id)
        return result.is_valid, result.errors, result.warnings

    # 其他工具不需要验证
    return True, [], []
