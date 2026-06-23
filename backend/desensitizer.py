"""
信息脱敏模块
对简历中的敏感信息进行脱敏处理
"""

import re
from typing import Dict, List, Tuple


PHONE_PATTERNS = [
    r'1[3-9]\d{9}',
    r'\d{3,4}[-\s]?\d{7,8}',
    r'\+86[-\s]?1[3-9]\d{9}',
]

EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

ID_CARD_PATTERN = r'[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]'

NAME_PATTERNS = [
    r'姓名[：:]\s*([\u4e00-\u9fa5]{2,4})',
    r'姓\s*名[：:]\s*([\u4e00-\u9fa5]{2,4})',
    r'我叫([\u4e00-\u9fa5]{2,4})',
]

WECHAT_PATTERNS = [
    r'(?:微信|微信号|WeChat|wx|VX)[：:]\s*([a-zA-Z0-9_-]{5,20})',
    r'(?:微信|微信号|WeChat|wx|VX)\s*[：:]\s*([a-zA-Z0-9_-]{5,20})',
]

QQ_PATTERNS = [
    r'(?:QQ|qq|扣扣)[：:]\s*([1-9]\d{4,11})',
    r'(?:QQ|qq|扣扣)\s*[：:]\s*([1-9]\d{4,11})',
]

LINKEDIN_PATTERNS = [
    r'(?:LinkedIn|领英|linkedin)[：:]\s*(\S+)',
    r'linkedin\.com/in/([\w-]+)',
]

BIRTHDAY_PATTERNS = [
    r'(?:出生年月|出生日期|生日|出生)[：:]\s*(\d{4}[-/.年]\d{1,2}[-/.月]?(?:\d{1,2}日?)?)',
    r'(\d{4})年(\d{1,2})月\s*(?:\d{1,2}日)?\s*出生',
]

SALARY_PATTERNS = [
    r'(?:期望薪资|期望待遇|薪资要求|待遇要求)[：:]\s*([\d,.\-~至KkW万\s元]+(?:/月|/年|元/月|万/年|K/月)?)',
    r'(?:当前薪资|目前薪资|现薪资)[：:]\s*([\d,.\-~至KkW万\s元]+(?:/月|/年|元/月|万/年|K/月)?)',
]


def desensitize_phone(text: str) -> Tuple[str, List[str]]:
    """脱敏手机号"""
    found_phones = []

    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, text)
        found_phones.extend(matches)

    found_phones = list(set(found_phones))

    for phone in found_phones:
        if len(phone) == 11 and phone.isdigit():
            desensitized = phone[:3] + '****' + phone[7:]
        elif '-' in phone or len(phone) > 8:
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
        desensitized = id_card[:6] + '********' + id_card[-4:]
        text = text.replace(id_card, desensitized)

    return text, found_ids


def desensitize_name(text: str) -> Tuple[str, List[str]]:
    """脱敏姓名"""
    found_names = []

    for pattern in NAME_PATTERNS:
        matches = re.findall(pattern, text)
        found_names.extend(matches)

    found_names = _dedupe_names(found_names)

    for name in found_names:
        desensitized = _mask_name(name)
        text = text.replace(f'姓名：{name}', f'姓名：{desensitized}')
        text = text.replace(f'姓名:{name}', f'姓名:{desensitized}')
        text = text.replace(f'姓  名：{name}', f'姓  名：{desensitized}')
        text = text.replace(f'姓  名:{name}', f'姓  名:{desensitized}')
        text = text.replace(f'我叫{name}', f'我叫{desensitized}')

    text, header_names = desensitize_header_name(text)
    found_names.extend(header_names)
    found_names = _dedupe_names(found_names)

    return text, found_names


def _dedupe_names(names: List[str]) -> List[str]:
    return list(set(n for n in names if n and len(n) >= 2))


def _mask_name(name: str) -> str:
    if len(name) == 2:
        return name[0] + '*'
    elif len(name) >= 3:
        return name[0] + '*' * (len(name) - 2) + name[-1]
    else:
        return '*'


def desensitize_header_name(text: str) -> Tuple[str, List[str]]:
    """脱敏简历首行/头部的姓名（简历开头直接写姓名的常见形式）"""
    found_names = []
    lines = text.strip().split('\n')

    for i in range(min(3, len(lines))):
        line = lines[i].strip()
        if not line:
            continue
        if re.match(r'^[\u4e00-\u9fa5]{2,4}$', line):
            name = line
            if not any(k in name for k in ['简历', '求职', '个人', '姓名', '专业', '学校', '公司']):
                desensitized = _mask_name(name)
                lines[i] = desensitized
                found_names.append(name)
                break

        m = re.match(r'^([\u4e00-\u9fa5]{2,4})\s*[|｜\s]', line)
        if m:
            name = m.group(1)
            if not any(k in name for k in ['简历', '求职', '个人', '姓名']):
                desensitized = _mask_name(name)
                lines[i] = desensitized + line[len(name):]
                found_names.append(name)
                break

    return '\n'.join(lines), found_names


def desensitize_wechat(text: str) -> Tuple[str, List[str]]:
    """脱敏微信号"""
    found = []
    for pattern in WECHAT_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            wx_id = m.group(1)
            found.append(wx_id)
            if len(wx_id) > 4:
                masked = wx_id[:2] + '****' + wx_id[-2:]
            else:
                masked = '*' * len(wx_id)
            text = text[:m.start(1)] + masked + text[m.end(1):]
    return text, list(set(found))


def desensitize_qq(text: str) -> Tuple[str, List[str]]:
    """脱敏QQ号"""
    found = []
    for pattern in QQ_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            qq = m.group(1)
            found.append(qq)
            if len(qq) > 4:
                masked = qq[:2] + '****' + qq[-2:]
            else:
                masked = '*' * len(qq)
            text = text[:m.start(1)] + masked + text[m.end(1):]
    return text, list(set(found))


def desensitize_linkedin(text: str) -> Tuple[str, List[str]]:
    """脱敏LinkedIn/领英账号"""
    found = []
    for pattern in LINKEDIN_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            account = m.group(1)
            found.append(account)
            if len(account) > 4:
                masked = account[:2] + '****' + account[-2:]
            else:
                masked = '*' * len(account)
            text = text[:m.start(1)] + masked + text[m.end(1):]
    return text, list(set(found))


def desensitize_birthday(text: str) -> Tuple[str, List[str]]:
    """脱敏出生日期"""
    found = []
    for pattern in BIRTHDAY_PATTERNS:
        for m in re.finditer(pattern, text):
            birthday = m.group(0)
            found.append(birthday)
            masked = re.sub(r'\d', '*', birthday)
            text = text[:m.start()] + masked + text[m.end():]
    return text, list(set(found))


def desensitize_salary(text: str) -> Tuple[str, List[str]]:
    """脱敏薪资信息"""
    found = []
    for pattern in SALARY_PATTERNS:
        for m in re.finditer(pattern, text):
            salary = m.group(1)
            found.append(salary)
            masked = '****'
            text = text[:m.start(1)] + masked + text[m.end(1):]
    return text, list(set(found))


def desensitize_address(text: str) -> Tuple[str, List[str]]:
    """脱敏地址"""
    address_keywords = ['地址：', '住址：', '家庭住址：', '现居地：', '籍贯：', '户籍：']

    found_addresses = []

    for keyword in address_keywords:
        lines = text.split('\n')
        new_lines = []
        for line in lines:
            if keyword in line and len(line) > len(keyword) + 5:
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
    """
    text, _ = desensitize_phone(text)
    text, _ = desensitize_email(text)
    text, _ = desensitize_id_card(text)
    text, _ = desensitize_name(text)
    text, _ = desensitize_wechat(text)
    text, _ = desensitize_qq(text)
    text, _ = desensitize_linkedin(text)
    text, _ = desensitize_birthday(text)
    text, _ = desensitize_salary(text)
    text, _ = desensitize_address(text)

    return text


def get_sensitive_info(text: str) -> Dict[str, List[str]]:
    """获取原始敏感信息（不脱敏，仅识别）"""
    info = {}

    _, info['phones'] = desensitize_phone(text)
    _, info['emails'] = desensitize_email(text)
    _, info['id_cards'] = desensitize_id_card(text)
    _, info['names'] = desensitize_name(text)
    _, info['wechats'] = desensitize_wechat(text)
    _, info['qqs'] = desensitize_qq(text)
    _, info['linkedins'] = desensitize_linkedin(text)
    _, info['birthdays'] = desensitize_birthday(text)
    _, info['salaries'] = desensitize_salary(text)
    _, info['addresses'] = desensitize_address(text)

    return info


__all__ = ['desensitize_resume', 'get_sensitive_info', 'desensitize_phone', 'desensitize_email']
