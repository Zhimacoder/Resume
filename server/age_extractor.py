"""
年龄提取模块
在脱敏前从原始简历文本中精确提取出生日期，计算年龄。
仅从身份证号和明确的出生日期字段提取，不从毕业年份/工作年限估算。
"""

import re
from datetime import date, datetime
from typing import Optional, Dict, Any, Tuple


ID_CARD_PATTERN = re.compile(r'[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]')

BIRTHDAY_FIELD_PATTERNS = [
    re.compile(r'(?:出生年月|出生日期|生日|出生)\s*[：:]\s*((?:19|20)\d{2})\s*[-/.年]\s*(\d{1,2})(?:\s*[-/.月]\s*(\d{1,2})\s*日?)?'),
    re.compile(r'((?:19|20)\d{2})\s*年\s*(\d{1,2})\s*月\s*(?:(\d{1,2})\s*日)?\s*出生'),
]

STANDALONE_DATE_PATTERN = re.compile(
    r'(?<![\d])(?:19|20)\d{2}\s*[-/.]\s*(?:0?[1-9]|1[0-2])\s*[-/.]\s*(?:0?[1-9]|[12]\d|3[01])(?![\d])'
)

YEAR_MONTH_PATTERN = re.compile(
    r'(?<![\d])(?:19|20)\d{2}\s*[-/.]\s*(?:0?[1-9]|1[0-2])(?![\d])'
)


def _calc_age(birth_date: date, today: Optional[date] = None) -> int:
    if today is None:
        today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def _parse_date(year: int, month: int, day: Optional[int]) -> Optional[date]:
    try:
        if day is None:
            day = 15
        return date(year, month, day)
    except ValueError:
        return None


def _extract_from_id_card(text: str) -> Optional[Tuple[date, str]]:
    matches = ID_CARD_PATTERN.findall(text)
    if not matches:
        return None
    for id_card in matches:
        try:
            year = int(id_card[6:10])
            month = int(id_card[10:12])
            day = int(id_card[12:14])
            bd = _parse_date(year, month, day)
            if bd:
                return bd, "id_card"
        except (ValueError, IndexError):
            continue
    return None


def _extract_from_birthday_field(text: str) -> Optional[Tuple[date, str]]:
    for pattern in BIRTHDAY_FIELD_PATTERNS:
        for m in pattern.finditer(text):
            try:
                year = int(m.group(1))
                month = int(m.group(2))
                day = int(m.group(3)) if m.group(3) else None
                bd = _parse_date(year, month, day)
                if bd:
                    source = "birthday_field" if day else "birthday_field_year_month"
                    return bd, source
            except (ValueError, IndexError):
                continue
    return None


def _is_in_personal_info_context(text: str, match_start: int, match_end: int) -> bool:
    window_start = max(0, match_start - 30)
    window = text[window_start:match_start + (match_end - match_start) + 30]
    personal_keywords = ['姓名', '性别', '年龄', '出生', '生日', '籍贯', '民族', '政治', '婚否',
                         '学历', '电话', '手机', '邮箱', '住址', '身高', '体重', '健康',
                         '名', '性别：', '出生年月', '出生日期']
    edu_exp_keywords = ['就读', '毕业', '大学', '学院', '高中', '初中', '小学', '专科', '本科', '硕士', '博士']
    work_exp_keywords = ['公司', '任职', '职位', '工作', '入职', '离职', '经验', '项目']

    for kw in edu_exp_keywords + work_exp_keywords:
        if kw in window:
            return False

    for kw in personal_keywords:
        if kw in window:
            return True

    return match_start < 200


def _extract_standalone_date(text: str) -> Optional[Tuple[date, str]]:
    full_date_matches = list(STANDALONE_DATE_PATTERN.finditer(text))
    for m in full_date_matches:
        date_str = m.group(0)
        if not _is_in_personal_info_context(text, m.start(), m.end()):
            continue
        parts = re.split(r'[-/.]', date_str)
        if len(parts) == 3:
            try:
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                bd = _parse_date(year, month, day)
                if bd and 18 <= _calc_age(bd) <= 70:
                    return bd, "birthday_field"
            except (ValueError, IndexError):
                continue

    ym_matches = list(YEAR_MONTH_PATTERN.finditer(text))
    for m in ym_matches:
        ym_str = m.group(0)
        if not _is_in_personal_info_context(text, m.start(), m.end()):
            continue
        parts = re.split(r'[-/.]', ym_str)
        if len(parts) == 2:
            try:
                year, month = int(parts[0]), int(parts[1])
                bd = _parse_date(year, month, 15)
                if bd and 18 <= _calc_age(bd) <= 70:
                    return bd, "birthday_field_year_month"
            except (ValueError, IndexError):
                continue

    return None


def extract_age(text: str) -> Dict[str, Any]:
    """
    从原始简历文本（未脱敏）中提取年龄信息。

    Returns:
        {
            "age": int | None,       # 周岁年龄，无法提取时为None
            "birth_year": int | None, # 出生年份，无法提取时为None
            "source": str | None     # 提取来源："id_card" | "birthday_field" | "birthday_field_year_month" | None
        }
    """
    result = {"age": None, "birth_year": None, "source": None}

    bd_and_source = (
        _extract_from_id_card(text) or
        _extract_from_birthday_field(text) or
        _extract_standalone_date(text)
    )

    if bd_and_source is None:
        return result

    birth_date, source = bd_and_source
    age = _calc_age(birth_date)

    if age < 16 or age > 80:
        return result

    result["age"] = age
    result["birth_year"] = birth_date.year
    result["source"] = source
    return result
