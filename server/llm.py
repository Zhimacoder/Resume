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


# 简历分析Prompt模板（支持自定义匹配维度，零幻觉约束）
RESUME_ANALYSIS_PROMPT = """你是一个严谨的HR简历筛选助手。你的核心原则是：**只基于简历原文中明确存在的事实做判断，绝对禁止猜测、推断、脑补或编造简历中没有的内容**。

## 岗位JD（Job Description）：
{jd_content}

## 简历内容（已脱敏）：
{resume_content}

{dimension_instructions}

{age_info_section}

## 铁律（违反任何一条即为失败）：
1. **零幻觉原则**：所有写入 matching_points 的技能、经验、经历，必须能在简历原文中找到明确的关键词或描述。如果简历中没有提到，绝对不能写入匹配点。
2. **证据要求**：每条 matching_points 和 shortcomings 必须在括号内标注简历原文中的对应关键词，格式为："具体描述（原文关键词：xxx）"或"具体描述（简历未提及：xxx）"。
3. **宁缺勿滥**：如果某方面简历没有提及，宁可在 shortcomings 中注明"简历未提及xxx"，也不要在 matching_points 中编造。
4. **诚实评分**：评分时只给简历中明确存在的匹配项加分；简历未提及的技能不得作为加分依据，也不得因"可能有"而扣分。
5. **禁止推断**：不能因为简历提到"软件开发"就推断"会Linux"，不能因为提到"使用Git"就推断"熟悉CI/CD"。任何没有直接文字证据的推断都属于幻觉。

### 反例（绝对禁止）：
- ❌ "熟练掌握Linux操作系统" —— 如果简历全文没有"Linux"、"Unix"、"Shell"、"CentOS"、"Ubuntu"等相关字样，这就是幻觉。
- ❌ "具备良好的团队协作能力" —— 如果简历没有相关描述、项目经历或自我评价支撑，不得凭空写入。
- ❌ "有3年Python开发经验" —— 如果简历写的是"熟悉Python"而没有明确年限，不得编造年限。

### 正例（正确做法）：
- ✅ "3年Python后端开发经验（原文关键词：3年Python开发经验）"
- ✅ "熟悉Django框架（原文关键词：Django）"
- ✅ "Linux经验未在简历中提及（简历未提及：Linux）"

请严格按照以下JSON格式输出分析结果，不要输出其他内容：

```json
{{
  "summary": "简历核心信息摘要，50-100字，只陈述简历中明确存在的事实，不做推断",
  "matching_points": ["匹配点描述（原文关键词：xxx）", "匹配点描述（原文关键词：xxx）"],
  "shortcomings": ["不足点描述（简历未提及：xxx）", "不足点描述（原文显示：xxx）"],
  "interview_questions": [
    {{"question": "基于简历实际内容的面试问题1", "focus": "该问题旨在考察候选人的哪方面能力/经验/技能，用简洁语言说明，便于非技术背景HR理解"}},
    {{"question": "基于简历实际内容的面试问题2", "focus": "考察能力说明"}},
    {{"question": "基于简历实际内容的面试问题3", "focus": "考察能力说明"}}
  ],
  "score": 85
}}
```

要求：
1. matching_points：列出简历中**明确存在**的与岗位JD匹配的技能、经验、经历，每条必须附带原文关键词
2. shortcomings：列出简历中与JD不匹配的方面，或简历未提及的JD要求项，标注"简历未提及"或引用原文
3. interview_questions：针对简历中实际提到的内容提出3个有针对性的面试问题，不要问简历未涉及的技术点；每个问题必须附带focus字段，用通俗易懂的语言说明该问题想要考察候选人的什么能力/经验/技能，帮助非技术背景HR理解提问目的
4. score：0-100的匹配度评分，{score_instruction}；严格依据简历事实评分，不加分给未提及的"潜在能力"
5. 只输出JSON，不要输出其他解释性文字
"""

DEFAULT_SCORE_INSTRUCTION = "严格依据简历中明确存在的事实，考虑技能匹配度、工作经验、项目经历等因素，简历未提及的内容不加分"

DEFAULT_DIMENSION_INSTRUCTIONS = ""

DEFAULT_AGE_INFO_SECTION = ""


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

    age_min = dimensions.get("age_min")
    age_max = dimensions.get("age_max")
    if age_min is not None or age_max is not None:
        try:
            age_min_i = int(age_min) if age_min not in (None, "", "none") else None
            age_max_i = int(age_max) if age_max not in (None, "", "none") else None
            if age_min_i is not None and age_max_i is not None:
                parts.append(f"- 年龄段要求：{age_min_i}-{age_max_i}岁")
                score_parts.append(f"年龄是否在{age_min_i}-{age_max_i}岁范围内（年龄信息由系统精确提取，非大模型推断）")
            elif age_min_i is not None:
                parts.append(f"- 年龄要求：{age_min_i}岁以上")
                score_parts.append(f"年龄是否满足{age_min_i}岁以上要求")
            elif age_max_i is not None:
                parts.append(f"- 年龄要求：{age_max_i}岁以下")
                score_parts.append(f"年龄是否满足{age_max_i}岁以下要求")
        except (ValueError, TypeError):
            pass

    extra = dimensions.get("extra", "")
    if extra:
        parts.append(f"- 其他要求：{extra}")

    if not parts:
        return DEFAULT_DIMENSION_INSTRUCTIONS, DEFAULT_SCORE_INSTRUCTION

    dimension_text = "## 自定义匹配维度（请在分析和评分中重点参考）：\n" + "\n".join(parts)
    if score_parts:
        score_instruction = "严格依据简历中明确存在的事实，综合考虑" + "、".join(score_parts) + "，简历未提及的内容不加分"
    else:
        score_instruction = DEFAULT_SCORE_INSTRUCTION

    return dimension_text, score_instruction


def build_age_info_section(age_info: Optional[Dict[str, Any]],
                           age_min: Any = None, age_max: Any = None) -> str:
    """
    构建年龄信息段，作为系统精确提取的事实信息注入Prompt。
    age_info 来自 age_extractor.extract_age() 的返回结果。
    """
    try:
        age_min_i = int(age_min) if age_min not in (None, "", "none") else None
        age_max_i = int(age_max) if age_max not in (None, "", "none") else None
    except (ValueError, TypeError):
        age_min_i = None
        age_max_i = None

    if age_min_i is None and age_max_i is None:
        return DEFAULT_AGE_INFO_SECTION

    has_age_requirement = age_min_i is not None or age_max_i is not None
    if not has_age_requirement:
        return DEFAULT_AGE_INFO_SECTION

    age = age_info.get("age") if age_info else None
    source = age_info.get("source") if age_info else None

    lines = ["## 候选人年龄信息（系统在脱敏前从简历中精确提取，属于事实信息，非大模型推断）："]

    if age is not None:
        source_label = {
            "id_card": "身份证号",
            "birthday_field": "出生日期字段",
            "birthday_field_year_month": "出生年月字段"
        }.get(source, "简历信息")
        lines.append(f"- 候选人年龄：{age}岁（从{source_label}提取）")

        if age_min_i is not None and age_max_i is not None:
            in_range = age_min_i <= age <= age_max_i
            if in_range:
                lines.append(f"- 年龄是否符合{age_min_i}-{age_max_i}岁要求：是")
            else:
                lines.append(f"- 年龄是否符合{age_min_i}-{age_max_i}岁要求：否（候选人{age}岁，不在要求范围内）")
        elif age_min_i is not None:
            in_range = age >= age_min_i
            lines.append(f"- 年龄是否满足{age_min_i}岁以上要求：{'是' if in_range else f'否（候选人{age}岁，不满足）'}")
        elif age_max_i is not None:
            in_range = age <= age_max_i
            lines.append(f"- 年龄是否满足{age_max_i}岁以下要求：{'是' if in_range else f'否（候选人{age}岁，不满足）'}")
    else:
        lines.append("- 简历中未提供明确的出生日期或身份证号，无法确定候选人年龄")
        if age_min_i is not None and age_max_i is not None:
            lines.append(f"- 无法判断候选人是否符合{age_min_i}-{age_max_i}岁的年龄段要求")
        elif age_min_i is not None:
            lines.append(f"- 无法判断候选人是否满足{age_min_i}岁以上要求")
        elif age_max_i is not None:
            lines.append(f"- 无法判断候选人是否满足{age_max_i}岁以下要求")

    lines.append("- 注意：以上年龄信息为系统精确提取结果，你可以直接引用但不要猜测具体出生日期")

    return "\n".join(lines)


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
            "temperature": 0.1
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
                "temperature": 0.1
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
            "temperature": 0.1
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
            "temperature": 0.1
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
            "temperature": 0.1
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
            "temperature": 0.1,
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
            "temperature": 0.1
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
                   api_secret: str = "",
                   age_info: Optional[Dict[str, Any]] = None,
                   age_min: Any = None, age_max: Any = None) -> Optional[Dict[str, Any]]:
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
        api_secret: 文心模型需要的SK（可选）
        age_info: extract_age() 返回的年龄信息（可选）
        age_min: 最小年龄要求（可选）
        age_max: 最大年龄要求（可选）

    Returns:
        包含分析结果的字典
    """
    caller = get_llm_caller(model_type, api_key, endpoint, model_name, api_secret)
    if not caller:
        return None

    dimension_text, score_instruction = build_dimension_instructions(dimensions)
    age_info_section = build_age_info_section(age_info, age_min, age_max)

    prompt = RESUME_ANALYSIS_PROMPT.format(
        jd_content=jd_content,
        resume_content=resume_content,
        dimension_instructions=dimension_text,
        age_info_section=age_info_section,
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

    # 兼容处理：interview_questions 可能是旧格式（字符串数组）或新格式（对象数组）
    # 统一转换为 [{question, focus}] 格式
    normalized_questions = []
    for q in result.get("interview_questions", []):
        if isinstance(q, dict):
            question_text = q.get("question", str(q))
            focus_text = q.get("focus", "")
            normalized_questions.append({
                "question": question_text,
                "focus": focus_text
            })
        elif isinstance(q, str):
            normalized_questions.append({
                "question": q,
                "focus": ""
            })
    result["interview_questions"] = normalized_questions

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
