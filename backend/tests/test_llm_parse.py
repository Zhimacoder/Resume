"""
LLM 模块单元测试（JSON 解析部分）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from llm import LLMCaller


@pytest.fixture
def analyzer():
    return LLMCaller("", "", "")


class TestParseResponse:
    def test_clean_json(self, analyzer):
        text = '{"summary": "test", "score": 85}'
        result = analyzer._parse_response(text)
        assert result is not None
        assert result["summary"] == "test"
        assert result["score"] == 85

    def test_json_in_markdown_code_block(self, analyzer):
        text = '''```json
{"summary": "test", "score": 90}
```'''
        result = analyzer._parse_response(text)
        assert result is not None
        assert result["score"] == 90

    def test_json_with_extra_text(self, analyzer):
        text = '''好的，我来分析这份简历。

```json
{
  "summary": "候选人经验丰富",
  "score": 75,
  "matching_points": ["点1", "点2"]
}
```

以上是分析结果。'''
        result = analyzer._parse_response(text)
        assert result is not None
        assert result["summary"] == "候选人经验丰富"
        assert result["score"] == 75
        assert len(result["matching_points"]) == 2

    def test_invalid_json(self, analyzer):
        text = "这不是有效的JSON"
        result = analyzer._parse_response(text)
        assert result is None

    def test_empty_string(self, analyzer):
        result = analyzer._parse_response("")
        assert result is None

    def test_none_input(self, analyzer):
        try:
            result = analyzer._parse_response(None)
            assert result is None
        except TypeError:
            pass

    def test_json_with_arrays(self, analyzer):
        text = '''```json
{
  "summary": "测试",
  "matching_points": ["匹配点1", "匹配点2", "匹配点3"],
  "shortcomings": ["不足1"],
  "interview_questions": ["问题1", "问题2"],
  "score": 80
}
```'''
        result = analyzer._parse_response(text)
        assert result is not None
        assert len(result["matching_points"]) == 3
        assert len(result["shortcomings"]) == 1
        assert len(result["interview_questions"]) == 2

    def test_score_is_preserved(self, analyzer):
        text = '{"summary": "test", "score": 85}'
        result = analyzer._parse_response(text)
        assert result is not None
        assert result["score"] == 85

    def test_score_string_preserved(self, analyzer):
        text = '{"summary": "test", "score": "85"}'
        result = analyzer._parse_response(text)
        assert result is not None
        assert result["score"] == "85"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
