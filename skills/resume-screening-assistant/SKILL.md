---
name: resume-screening-assistant
description: 智能简历筛选项目助手。何时使用：当用户需要理解、维护、排障、扩展或二次开发 Resume_screening / 智能简历筛选工具项目时使用，包括梳理业务流程、定位前后端模块、修改简历解析/OCR/脱敏/大模型匹配/Excel导出/API配置/部署相关功能、编写测试和做发布前检查。
---

# 智能简历筛选项目助手

用于协助处理 Resume_screening 智能简历筛选工具的业务理解、代码维护、功能迭代、排障与测试验证。

## 使用指南

1. 先确认用户意图属于业务理解、功能迭代、缺陷排查、测试验证、部署发布或文档沉淀中的哪一类。
2. 涉及代码修改前，先读取相关文件，避免只凭项目记忆改代码。
3. 需要项目上下文时，读取 `references/project-guide.md`，其中包含业务流程、架构、关键模块、接口、隐私约束和验证清单。
4. 严禁读取或输出项目中的密钥、API Key、加密配置、运行时日志里的敏感内容；涉及配置时只说明字段含义和流程，不展示真实值。
5. 修改后优先运行与变更相关的轻量测试；后端核心逻辑优先验证 `backend/tests/` 中的配置、脱敏和 LLM 解析测试。
6. 交付时说明改动影响范围、验证结果和未覆盖风险。

## 常见任务入口

- 业务/产品理解：读取项目说明和 `references/project-guide.md` 的业务流程章节。
- 后端接口或流程修改：优先检查 `backend/main.py`、`backend/llm.py`、`backend/parser.py`、`backend/ocr.py`、`backend/desensitizer.py`、`backend/config.py`。
- 前端交互修改：优先检查 `frontend/index.html`、`frontend/result.html`、`frontend/config.html` 及 `frontend/js/` 下对应模块。
- 测试与回归：优先运行后端单元测试，必要时补充接口级或前端手工验证清单。
- 部署检查：检查 `Dockerfile`、`docker-compose.yml`、`deploy/` 和启动脚本，但不要提交运行时配置、密钥或日志。

## 参考资料

- **项目业务与架构指南**：见 `references/project-guide.md`。
