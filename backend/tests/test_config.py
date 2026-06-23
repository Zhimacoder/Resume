"""
配置模块单元测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from config import (
    _is_model_config_valid,
    _is_masked,
    _mask_secret,
)


class TestIsModelConfigValid:
    def test_doubao_valid(self):
        assert _is_model_config_valid("doubao", {"api_key": "xxx", "endpoint": "yyy"}) is True

    def test_doubao_missing_key(self):
        assert _is_model_config_valid("doubao", {"api_key": "", "endpoint": "yyy"}) is False

    def test_doubao_missing_endpoint(self):
        assert _is_model_config_valid("doubao", {"api_key": "xxx", "endpoint": ""}) is False

    def test_wenxin_valid(self):
        assert _is_model_config_valid("wenxin", {
            "api_key": "ak", "endpoint": "ep", "api_secret": "sk"
        }) is True

    def test_wenxin_missing_secret(self):
        assert _is_model_config_valid("wenxin", {
            "api_key": "ak", "endpoint": "ep"
        }) is False

    def test_wenxin_empty_secret(self):
        assert _is_model_config_valid("wenxin", {
            "api_key": "ak", "endpoint": "ep", "api_secret": ""
        }) is False


class TestIsMasked:
    def test_masked_value(self):
        assert _is_masked("sk-****abcd") is True

    def test_plain_value(self):
        assert _is_masked("sk-abc123def456") is False

    def test_empty_value(self):
        assert _is_masked("") is False


class TestMaskSecret:
    def test_long_secret(self):
        result = _mask_secret("abcdefghijklmnop")
        assert result == "abcd****mnop"
        assert len(result) == len("abcd****mnop")

    def test_short_secret(self):
        result = _mask_secret("12345")
        assert result == "*****"

    def test_empty_secret(self):
        result = _mask_secret("")
        assert result == ""

    def test_medium_secret(self):
        result = _mask_secret("123456789012")
        assert result == "1234****9012"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
