"""
大模型调用模块
支持多种大模型的API调用
"""

import json
import re
import time
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

from logger_config import logger


MAX_RETRIES = 2
RETRY_DELAY = 1.0


def _should_retry(status_code: int, error_msg: str = "") -> bool:
    """判断是否需要重试"""
    if status_code in {429, 500, 502, 503, 504}:
        return True
    if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
        return True
    if "connection" in error_msg.lower() and "error" in error_msg.lower():
        return True
    return False


def _retry_call(func, *args, **kwargs):
    """带重试的调用封装"""
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES and _should_retry(0, str(e)):
                wait = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"第 {attempt + 1} 次调用失败，{wait:.1f}s 后重试: {e}")
                time.sleep(wait)
                continue
            raise
    raise last_error


# 简历分析Prompt模板（支持自定义匹配维度）
RESUME_ANALYSIS_PROMPT = """你是一个专业的HR简历筛选助手。请根据以下岗位JD和简历内容，进行分析并输出结构化的匹配结果。

## 岗位JD（Job Description）：
{jd_content}

## 简历内容（已脱敏）：
{resume_content}

{dimension_instructions}

请严格按照以下JSON格式输出分析结果，不要输出其他内容：

```json
{{
  "summary": "简历核心信息摘要，50-100字",
  "matching_points": ["匹配点1", "匹配点2", "匹配点3"],
  "shortcomings": ["不足点1", "不足点2"],
  "interview_questions": ["面试问题1", "面试问题2", "面试问题3"],
  "score": 85
}}
```

要求：
1. matching_points：列出简历中与岗位JD匹配的技能、经验、经历等
2. shortcomings：列出简历中与岗位JD要求不匹配的方面
3. interview_questions：针对简历与岗位的匹配情况，提出3个最合适的面试问题
4. score：0-100的匹配度评分，{score_instruction}
5. 只输出JSON，不要输出其他解释性文字
"""

DEFAULT_SCORE_INSTRUCTION = "考虑技能匹配度、工作经验、项目经历等因素"

DEFAULT_DIMENSION_INSTRUCTIONS = ""


def build_dimension_instructions(dimensions: Optional[Dict[str, Any]]) -> tuple:
    """根据自定义维度构建Prompt补充说明和评分说明"""
    if not dimensions:
        return DEFAULT_DIMENSION_INSTRUCTIONS, DEFAULT_SCORE_INSTRUCTION

    parts = []
    score_parts = []

    work_years = dimensions.get("work_years", "")
    if work_years:
        parts.append(f"- 工作年限要求：{work_years}")
        score_parts.append(f"工作年限要求（{work_years}）")

    education = dimensions.get("education", "")
    if education:
        parts.append(f"- 学历要求：{education}")
        score_parts.append(f"学历要求（{education}）")

    skill_weights = dimensions.get("skill_weights", "")
    if skill_weights:
        parts.append(f"- 核心技能权重说明：{skill_weights}（请在评分时重点考虑这些技能的匹配程度）")
        score_parts.append(f"核心技能匹配（{skill_weights}）")

    extra = dimensions.get("extra", "")
    if extra:
        parts.append(f"- 其他要求：{extra}")

    if not parts:
        return DEFAULT_DIMENSION_INSTRUCTIONS, DEFAULT_SCORE_INSTRUCTION

    dimension_text = "## 自定义匹配维度（请在分析和评分中重点参考）：\n" + "\n".join(parts)
    score_instruction = "综合考虑" + "、".join(score_parts) if score_parts else DEFAULT_SCORE_INSTRUCTION

    return dimension_text, score_instruction


class LLMCaller:
    """大模型调用基类"""

    def __init__(self, api_key: str, endpoint: str, model_name: str = ""):
        self.api_key = api_key
        self.endpoint = endpoint
        self.model_name = model_name
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })

    def call(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """调用大模型接口"""
        raise NotImplementedError

    def test_connection(self) -> Dict[str, Any]:
        """测试API连通性，发送一个简单的探测请求"""
        test_messages = [{"role": "user", "content": "你好，请回复 OK"}]
        try:
            result = self.call(test_messages)
            if result is not None:
                return {"success": True, "message": "连接成功，API Key 有效"}
            else:
                return {"success": False, "message": "API 返回空响应，请检查 Key 和 Endpoint"}
        except Exception as e:
            return {"success": False, "message": f"连接失败：{str(e)}"}

    def list_models(self) -> List[str]:
        """
        获取该平台可用的模型列表。
        默认实现返回空列表；支持动态拉取的子类重写此方法。
        不支持动态拉取的子类直接返回硬编码的常用模型列表。
        """
        return []

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """解析大模型响应，优先提取 markdown 代码块中的 JSON"""
        # 策略1: 提取 markdown 代码块中的 JSON
        md_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', response_text)
        if md_match:
            try:
                return json.loads(md_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 策略2: 精确匹配第一个完整 JSON 对象（非贪婪）
        json_match = re.search(r'\{(?:[^{}]|"[^"]*"|\{[^{}]*\})*\}', response_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # 策略3: 回退到贪婪匹配
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        return None


class DoubaoCaller(LLMCaller):
    """字节豆包API调用
    豆包使用「推理接入点 endpoint_id」概念，格式为 ep-xxxxxxxx-xxxxx
    没有公开的 list models 接口，提供常用版本供参考
    """

    def list_models(self) -> List[str]:
        # 豆包无 list models 接口，返回常用接入点版本提示
        return [
            "doubao-pro-32k-240928",
            "doubao-pro-128k-240928",
            "doubao-lite-32k-240828",
            "doubao-lite-128k-240828",
            "doubao-pro-4k-240515",
        ]

    def call(self, messages: List[Dict[str, str]]) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        model = self.model_name if self.model_name else "doubao-pro-32k-240928"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7
        }

        try:
            response = self.session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"豆包API调用失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"豆包API调用异常: {e}")
            return None


class WenxinCaller(LLMCaller):
    """百度文心API调用
    使用 AK/SK 先换取 access_token，再调用模型接口
    """

    def __init__(self, api_key: str, endpoint: str, model_name: str = "", api_secret: str = ""):
        super().__init__(api_key, endpoint, model_name)
        self.api_secret = api_secret

    def list_models(self) -> List[str]:
        # 文心需要 AK/SK 换取 token 才能调 list，改造成本高；硬编码常用版本
        return [
            "ernie-4.0-8k",
            "ernie-4.0-turbo-8k",
            "ernie-3.5-8k",
            "ernie-3.5-128k",
            "ernie-lite-8k",
            "ernie-speed-128k",
            "ernie-tiny-8k",
        ]

    def call(self, messages: List[Dict[str, str]]) -> Optional[str]:
        try:
            if not self.api_secret:
                logger.error("文心API调用失败: 缺少 API Secret (SK)，请在配置页填写")
                return None

            token_url = "https://aip.baidubce.com/oauth/2.0/token"
            token_response = self.session.post(
                token_url,
                params={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.api_secret
                },
                timeout=10
            )

            if token_response.status_code != 200:
                logger.error(f"文心获取token失败: {token_response.status_code} - {token_response.text}")
                return None

            token_data = token_response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                error_msg = token_data.get("error_description", "未知错误")
                logger.error(f"文心获取token失败: {error_msg}")
                return None

            model = self.model_name if self.model_name else "ernie-4.0-8k"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.7
            }

            full_endpoint = f"{self.endpoint}?access_token={access_token}"
            response = self.session.post(
                full_endpoint,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result['result']
            else:
                logger.error(f"文心API调用失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"文心API调用异常: {e}")
            return None


class QianwenCaller(LLMCaller):
    """阿里千问API调用"""

    def list_models(self) -> List[str]:
        # DashScope 无稳定的公开 list models 接口，硬编码常用模型
        return [
            "qwen-plus",
            "qwen-max",
            "qwen-turbo",
            "qwen-long",
            "qwen-max-longcontext",
            "qwen2.5-72b-instruct",
            "qwen2.5-32b-instruct",
            "qwen2.5-14b-instruct",
            "qwen2.5-7b-instruct",
        ]

    def call(self, messages: List[Dict[str, str]]) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if self.model_name:
            model = self.model_name
        elif "qwen-turbo" in self.endpoint:
            model = "qwen-turbo"
        elif "qwen-max" in self.endpoint:
            model = "qwen-max"
        else:
            model = "qwen-plus"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7
        }

        try:
            response = self.session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"千问API调用失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"千问API调用异常: {e}")
            return None


class ZhipuCaller(LLMCaller):
    """智谱GLM API调用"""

    def list_models(self) -> List[str]:
        """调用智谱 /models 接口动态获取模型列表"""
        try:
            # 智谱 endpoint 格式: https://open.bigmodel.cn/api/paas/v4/chat/completions
            # models 接口: https://open.bigmodel.cn/api/paas/v4/models
            base = self.endpoint.split("/chat/completions")[0].split("/v4")[0]
            models_url = f"{base}/v4/models"
            resp = self.session.get(
                models_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                models = [item["id"] for item in data.get("data", []) if "id" in item]
                if models:
                    return sorted(models)
        except Exception as e:
            logger.warning(f"智谱获取模型列表失败: {e}")
        # 降级到硬编码
        return ["glm-4", "glm-4-flash", "glm-4-air", "glm-4-airx", "glm-3-turbo", "glm-4v"]

    def call(self, messages: List[Dict[str, str]]) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        model = self.model_name if self.model_name else "glm-4"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7
        }

        try:
            response = self.session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"智谱API调用失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"智谱API调用异常: {e}")
            return None


class MinmaxCaller(LLMCaller):
    """MinMax API调用"""

    def list_models(self) -> List[str]:
        # MinMax 无公开 list models 接口，硬编码常用模型
        return [
            "MiniMax-Text-01",
            "abab6.5s-chat",
            "abab6.5-chat",
            "abab5.5s-chat",
            "abab5.5-chat",
        ]

    def call(self, messages: List[Dict[str, str]]) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        model = self.model_name if self.model_name else "abab6.5s-chat"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7
        }

        try:
            response = self.session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"MinMax API调用失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"MinMax API调用异常: {e}")
            return None


class DeepSeekCaller(LLMCaller):
    """DeepSeek API调用
    接口文档: https://api-docs.deepseek.com/zh-cn/
    Endpoint: https://api.deepseek.com/chat/completions
    Auth: Authorization: Bearer <api_key>
    响应: choices[0].message.content
    """

    def list_models(self) -> List[str]:
        """调用 DeepSeek /models 接口动态获取模型列表（OpenAI 兼容格式）"""
        try:
            models_url = "https://api.deepseek.com/models"
            resp = self.session.get(
                models_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                models = [item["id"] for item in data.get("data", []) if "id" in item]
                if models:
                    return sorted(models)
        except Exception as e:
            logger.warning(f"DeepSeek获取模型列表失败: {e}")
        return ["deepseek-chat", "deepseek-reasoner"]

    def call(self, messages: List[Dict[str, str]]) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 默认使用 deepseek-chat (DeepSeek-V3)，可通过 model_version 指定
        model = self.model_name if self.model_name else "deepseek-chat"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 1.0,  # DeepSeek 默认温度为 1，范围 0~2
            "stream": False
        }

        try:
            response = self.session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"DeepSeek API调用失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {e}")
            return None


class CustomCaller(LLMCaller):
    """自定义模型API调用"""

    def call(self, messages: List[Dict[str, str]]) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "messages": messages,
            "temperature": 0.7
        }

        if self.model_name:
            payload["model"] = self.model_name

        try:
            response = self.session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result:
                    return result['choices'][0]['message']['content']
                elif 'result' in result:
                    return result['result']
                elif 'content' in result:
                    return result['content']
            else:
                logger.error(f"自定义API调用失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"自定义API调用异常: {e}")
            return None


def get_llm_caller(model_type: str, api_key: str, endpoint: str,
                   model_name: str = "", api_secret: str = "") -> Optional[LLMCaller]:
    """获取对应的大模型调用器"""
    if model_type == "wenxin":
        return WenxinCaller(api_key, endpoint, model_name, api_secret)

    callers = {
        "doubao": DoubaoCaller,
        "qianwen": QianwenCaller,
        "zhipu": ZhipuCaller,
        "minmax": MinmaxCaller,
        "deepseek": DeepSeekCaller,
        "custom": CustomCaller
    }

    caller_class = callers.get(model_type, CustomCaller)
    return caller_class(api_key, endpoint, model_name)


def test_connection(model_type: str, api_key: str, endpoint: str,
                    model_name: str = "", api_secret: str = "") -> Dict[str, Any]:
    """测试大模型API连通性，同时返回可用模型列表"""
    caller = get_llm_caller(model_type, api_key, endpoint, model_name, api_secret)
    if not caller:
        return {"success": False, "message": "无法创建模型调用器", "models": []}
    result = caller.test_connection()
    # 连通成功后，附带拉取模型列表
    if result.get("success"):
        try:
            result["models"] = caller.list_models()
        except Exception:
            result["models"] = []
    else:
        result["models"] = []
    return result


def analyze_resume(model_type: str, api_key: str, endpoint: str,
                   jd_content: str, resume_content: str,
                   resume_name: str, model_name: str = "",
                   dimensions: Optional[Dict[str, Any]] = None,
                   api_secret: str = "") -> Optional[Dict[str, Any]]:
    """
    分析简历与JD的匹配度

    Args:
        model_type: 模型类型
        api_key: API密钥
        endpoint: API端点
        jd_content: 岗位JD内容
        resume_content: 简历内容（已脱敏）
        resume_name: 简历文件名
        model_name: 具体模型名称（可选）
        dimensions: 自定义匹配维度（可选）

    Returns:
        包含分析结果的字典
    """
    caller = get_llm_caller(model_type, api_key, endpoint, model_name, api_secret)
    if not caller:
        return None

    dimension_text, score_instruction = build_dimension_instructions(dimensions)

    prompt = RESUME_ANALYSIS_PROMPT.format(
        jd_content=jd_content,
        resume_content=resume_content,
        dimension_instructions=dimension_text,
        score_instruction=score_instruction
    )

    messages = [
        {"role": "user", "content": prompt}
    ]

    response_text = caller.call(messages)
    if not response_text:
        return None

    result = caller._parse_response(response_text)
    if not result:
        return {
            "resume_name": resume_name,
            "summary": "简历分析失败，请稍后重试",
            "matching_points": [],
            "shortcomings": [],
            "interview_questions": [],
            "score": 0,
            "error": "大模型响应解析失败"
        }

    result["resume_name"] = resume_name

    result.setdefault("summary", "")
    result.setdefault("matching_points", [])
    result.setdefault("shortcomings", [])
    result.setdefault("interview_questions", [])
    result.setdefault("score", 0)

    return result


__all__ = [
    'analyze_resume',
    'test_connection',
    'get_llm_caller',
    'LLMCaller',
    'DoubaoCaller',
    'WenxinCaller',
    'QianwenCaller',
    'ZhipuCaller',
    'MinmaxCaller',
    'DeepSeekCaller',
    'CustomCaller'
]
