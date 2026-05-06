"""
信息脱敏模块
对简历中的敏感信息进行脱敏处理
"""

import re
from typing import Dict, List, Tuple


# 手机号正则（中国大陆手机号）
PHONE_PATTERNS = [
    r'1[3-9]\d{9}',  # 11位手机号
    r'\d{3,4}[-\s]?\d{7,8}',  # 固定电话
    r'\+86[-\s]?1[3-9]\d{9}',  # 国际格式
]

# 邮箱正则
EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

# 身份证号正则
ID_CARD_PATTERN = r'[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]'

# 姓名识别模式（常见姓名格式）
NAME_PATTERNS = [
    r'姓名[：:]\s*([\u4e00-\u9fa5]{2,4})',
    r'姓\s*名[：:]\s*([\u4e00-\u9fa5]{2,4})',
    r'我叫([\u4e00-\u9fa5]{2,4})',
]


def desensitize_phone(text: str) -> Tuple[str, List[str]]:
    """脱敏手机号"""
    found_phones = []

    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, text)
        found_phones.extend(matches)

    # 去重
    found_phones = list(set(found_phones))

    # 脱敏处理
    for phone in found_phones:
        if len(phone) == 11 and phone.isdigit():  # 手机号
            # 138****1234
            desensitized = phone[:3] + '****' + phone[7:]
        elif '-' in phone or len(phone) > 8:  # 固定电话
            # 010-1234****
            parts = phone.replace('-', ' ').split()
            if len(parts) >= 2:
                desensitized = parts[0] + '-****' + parts[-1][-4:]
            else:
                desensitized = '****' + phone[-4:]
        else:
            desensitized = '****'

        text = text.replace(phone, desensitized)

    return text, found_phones


def desensitize_email(text: str) -> Tuple[str, List[str]]:
    """脱敏邮箱"""
    matches = re.findall(EMAIL_PATTERN, text)
    found_emails = list(set(matches))

    for email in found_emails:
        # test@example.com -> t**t@e******.com
        parts = email.split('@')
        if len(parts) == 2:
            username = parts[0]
            domain = parts[1]
            if len(username) > 2:
                desensitized = username[0] + '**' + username[-1] + '@' + domain
            elif len(username) > 0:
                desensitized = username[0] + '**@' + domain
            else:
                desensitized = '****@' + domain
            text = text.replace(email, desensitized)

    return text, found_emails


def desensitize_id_card(text: str) -> Tuple[str, List[str]]:
    """脱敏身份证号"""
    matches = re.findall(ID_CARD_PATTERN, text)
    found_ids = list(set(matches))

    for id_card in found_ids:
        # 110101199001011234 -> 110101********1234
        desensitized = id_card[:6] + '********' + id_card[-4:]
        text = text.replace(id_card, desensitized)

    return text, found_ids


def desensitize_name(text: str) -> Tuple[str, List[str]]:
    """脱敏姓名"""
    found_names = []

    for pattern in NAME_PATTERNS:
        matches = re.findall(pattern, text)
        found_names.extend(matches)

    found_names = list(set(found_names))

    for name in found_names:
        # 姓名 -> 张三 -> 张*
        if len(name) == 2:
            desensitized = name[0] + '*'
        elif len(name) >= 3:
            desensitized = name[0] + '*' * (len(name) - 2) + name[-1]
        else:
            desensitized = '*'

        # 替换 "姓名：张三" 格式
        text = text.replace(f'姓名：{name}', f'姓名：{desensitized}')
        text = text.replace(f'姓名:{name}', f'姓名:{desensitized}')
        text = text.replace(f'姓  名：{name}', f'姓  名：{desensitized}')
        text = text.replace(f'姓  名:{name}', f'姓  名:{desensitized}')
        text = text.replace(f'我叫{name}', f'我叫{desensitized}')

    return text, found_names


def desensitize_address(text: str) -> Tuple[str, List[str]]:
    """脱敏地址（识别常见地址关键词）"""
    # 常见地址关键词
    address_keywords = ['地址：', '住址：', '家庭住址：']

    found_addresses = []

    for keyword in address_keywords:
        # 简单处理：标记可能包含地址的行
        lines = text.split('\n')
        new_lines = []
        for line in lines:
            if keyword in line and len(line) > len(keyword) + 5:
                # 保留关键词，后面的地址做部分脱敏
                address_part = line[len(keyword):].strip()
                if len(address_part) > 4:
                    desensitized = address_part[:2] + '***' + address_part[-2:]
                    new_line = keyword + desensitized
                    found_addresses.append(address_part)
                    line = new_line
            new_lines.append(line)

        text = '\n'.join(new_lines)

    return text, found_addresses


def desensitize_resume(text: str) -> str:
    """
    简历脱敏主函数
    返回脱敏后的文本和原始敏感信息（用于记录）
    """
    original_text = text

    # 依次脱敏各种敏感信息
    text, phones = desensitize_phone(text)
    text, emails = desensitize_email(text)
    text, id_cards = desensitize_id_card(text)
    text, names = desensitize_name(text)
    text, addresses = desensitize_address(text)

    return text


def get_sensitive_info(text: str) -> Dict[str, List[str]]:
    """获取原始敏感信息（不脱敏，仅识别）"""
    info = {}

    _, info['phones'] = desensitize_phone(text)
    _, info['emails'] = desensitize_email(text)
    _, info['id_cards'] = desensitize_id_card(text)
    _, info['names'] = desensitize_name(text)
    _, info['addresses'] = desensitize_address(text)

    return info


__all__ = ['desensitize_resume', 'get_sensitive_info', 'desensitize_phone', 'desensitize_email']