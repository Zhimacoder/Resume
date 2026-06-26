"""
年龄提取模块单元测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'server'))

import pytest
from datetime import date
from unittest.mock import patch
from age_extractor import extract_age, _calc_age, _extract_from_id_card, _extract_from_birthday_field


class TestCalcAge:
    def test_age_before_birthday(self):
        with patch('age_extractor.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 15)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            assert _calc_age(date(1990, 6, 20)) == 35

    def test_age_after_birthday(self):
        with patch('age_extractor.date') as mock_date:
            mock_date.today.return_value = date(2026, 6, 20)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            assert _calc_age(date(1990, 6, 20)) == 36

    def test_age_on_birthday(self):
        with patch('age_extractor.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 26)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            assert _calc_age(date(2000, 3, 26)) == 26

    def test_age_newborn(self):
        with patch('age_extractor.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 26)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            assert _calc_age(date(2026, 3, 25)) == 0


class TestExtractFromIdCard:
    def test_18_digit_id_card(self):
        text = "身份证号：110101199003151234"
        result = _extract_from_id_card(text)
        assert result is not None
        birth_date, source = result
        assert birth_date == date(1990, 3, 15)
        assert source == "id_card"

    def test_id_card_in_text(self):
        text = "本人身份证号码为320101198505120015，现住南京市"
        result = _extract_from_id_card(text)
        assert result is not None
        birth_date, source = result
        assert birth_date.year == 1985
        assert birth_date.month == 5
        assert birth_date.day == 12

    def test_invalid_id_card_ignored(self):
        text = "身份证：110101189003151234"
        result = _extract_from_id_card(text)
        assert result is None

    def test_x_suffix_id_card(self):
        text = "身份证号码：44030119951225123X"
        result = _extract_from_id_card(text)
        assert result is not None
        birth_date, _ = result
        assert birth_date == date(1995, 12, 25)


class TestExtractFromBirthdayField:
    def test_birth_date_with_chinese_label(self):
        text = "出生日期：1990年3月15日"
        result = _extract_from_birthday_field(text)
        assert result is not None
        birth_date, source = result
        assert birth_date == date(1990, 3, 15)

    def test_birth_with_slash_format(self):
        text = "生日：1990/03/15"
        result = _extract_from_birthday_field(text)
        assert result is not None
        birth_date, _ = result
        assert birth_date == date(1990, 3, 15)

    def test_birth_with_dash_format(self):
        text = "出生年月：1990-03-15"
        result = _extract_from_birthday_field(text)
        assert result is not None

    def test_birth_with_dot_format(self):
        text = "出生：1990.03.15"
        result = _extract_from_birthday_field(text)
        assert result is not None

    def test_no_birth_date(self):
        text = "工作经历：2020年至今在ABC公司"
        result = _extract_from_birthday_field(text)
        assert result is None


class TestExtractAge:
    def test_extract_age_from_id_card(self):
        text = """
        姓名：张三
        身份证号：110101199003151234
        学历：本科
        工作年限：5年
        """
        with patch('age_extractor.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 26)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = extract_age(text)
            assert result["age"] == 36
            assert result["birth_year"] == 1990
            assert result["source"] == "id_card"

    def test_extract_age_from_birthday(self):
        text = """
        姓名：李四
        出生日期：1995年6月20日
        学历：硕士
        """
        with patch('age_extractor.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 26)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = extract_age(text)
            assert result["age"] == 30
            assert result["birth_year"] == 1995

    def test_no_age_info(self):
        text = """
        姓名：王五
        学历：本科
        工作年限：3年
        技能：Python, Java
        """
        result = extract_age(text)
        assert result["age"] is None
        assert result["birth_year"] is None
        assert result["source"] is None

    def test_unreasonable_age_rejected(self):
        text = "出生日期：2020年1月1日"
        with patch('age_extractor.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 26)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = extract_age(text)
            assert result["age"] is None

    def test_work_experience_date_not_misidentified(self):
        text = """
        工作经历：2015年3月至2020年5月在XX公司
        教育经历：2011年9月至2015年6月某大学
        出生日期：1992年8月10日
        """
        with patch('age_extractor.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 26)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = extract_age(text)
            assert result["age"] == 33
            assert result["birth_year"] == 1992

    def test_education_date_not_misidentified_as_age(self):
        text = """
        2018.09-2022.06 北京大学 计算机科学 本科
        工作经验：3年
        """
        result = extract_age(text)
        assert result["age"] is None
