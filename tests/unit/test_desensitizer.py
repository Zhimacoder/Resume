"""
脱敏模块单元测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'server'))

import pytest
from desensitizer import (
    desensitize_phone,
    desensitize_email,
    desensitize_id_card,
    desensitize_name,
    desensitize_wechat,
    desensitize_qq,
    desensitize_linkedin,
    desensitize_birthday,
    desensitize_salary,
    desensitize_resume,
    get_sensitive_info,
)


class TestDesensitizePhone:
    def test_mobile_phone(self):
        text = "联系电话：13812345678"
        result, phones = desensitize_phone(text)
        assert "138****5678" in result
        assert "13812345678" not in result
        assert "13812345678" in phones

    def test_landline(self):
        text = "座机：010-12345678"
        result, phones = desensitize_phone(text)
        assert "010-****5678" in result

    def test_international_format(self):
        text = "+8613812345678"
        result, phones = desensitize_phone(text)
        assert len(phones) > 0


class TestDesensitizeEmail:
    def test_basic_email(self):
        text = "邮箱：test@example.com"
        result, emails = desensitize_email(text)
        assert "t**t@example.com" in result
        assert "test@example.com" not in result
        assert "test@example.com" in emails

    def test_short_username(self):
        text = "a@b.com"
        result, emails = desensitize_email(text)
        assert "a**@b.com" in result


class TestDesensitizeIdCard:
    def test_id_card(self):
        text = "身份证：110101199001011234"
        result, ids = desensitize_id_card(text)
        assert "110101********1234" in result
        assert "110101199001011234" not in result


class TestDesensitizeName:
    def test_name_with_label(self):
        text = "姓名：张三"
        result, names = desensitize_name(text)
        assert "姓名：张*" in result
        assert "张三" not in result
        assert "张三" in names

    def test_three_char_name(self):
        text = "姓名：王小明"
        result, names = desensitize_name(text)
        assert "姓名：王*明" in result

    def test_header_name(self):
        text = "李四\n求职意向：产品经理"
        result, names = desensitize_name(text)
        assert "李*" in result
        assert "李四" not in result


class TestDesensitizeWechat:
    def test_wechat_id(self):
        text = "微信：zhangsan123"
        result, found = desensitize_wechat(text)
        assert "zh****23" in result
        assert "zhangsan123" not in result


class TestDesensitizeQQ:
    def test_qq_number(self):
        text = "QQ：123456789"
        result, found = desensitize_qq(text)
        assert "12****89" in result
        assert "123456789" not in result


class TestDesensitizeLinkedin:
    def test_linkedin_account(self):
        text = "LinkedIn：zhangsan-profile"
        result, found = desensitize_linkedin(text)
        assert len(found) > 0


class TestDesensitizeBirthday:
    def test_birthday(self):
        text = "出生年月：1990年1月"
        result, found = desensitize_birthday(text)
        assert len(found) > 0


class TestDesensitizeSalary:
    def test_expected_salary(self):
        text = "期望薪资：20-30K/月"
        result, found = desensitize_salary(text)
        assert "****" in result
        assert "20-30K/月" not in result


class TestDesensitizeResume:
    def test_full_resume(self):
        text = """姓名：张三
电话：13812345678
邮箱：zhangsan@example.com
微信：zhangsan_wx
QQ：123456789
身份证：110101199001011234
期望薪资：20-30K/月
出生年月：1990年1月
地址：北京市朝阳区xxx路xxx号
"""
        result = desensitize_resume(text)
        assert "张三" not in result
        assert "13812345678" not in result
        assert "zhangsan@example.com" not in result
        assert "zhangsan_wx" not in result
        assert "123456789" not in result
        assert "110101199001011234" not in result

    def test_empty_text(self):
        result = desensitize_resume("")
        assert result == ""


class TestGetSensitiveInfo:
    def test_get_info(self):
        text = "姓名：张三\n电话：13812345678\n邮箱：test@example.com"
        info = get_sensitive_info(text)
        assert "phones" in info
        assert "emails" in info
        assert "names" in info
        assert "wechats" in info
        assert "qqs" in info
        assert len(info["phones"]) > 0
        assert len(info["emails"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
