"""
通用工具函数
"""

import re


def parse_duration(duration: str) -> int:
    """解析时长字符串，返回天数

    支持格式：
    - 数字+单位：1个月、2周、3天
    - 中文数字：一个星期、两个月、半年
    """
    chinese_numbers = {
        "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        "半": 0.5
    }

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

    if "半年" in duration:
        return 180
    if "一年" in duration:
        return 365

    return 7
