# Resume_screening 项目业务与架构指南

本指南沉淀智能简历筛选工具的业务、架构和维护要点，用于后续快速理解和处理项目任务。

## 1. 产品定位

Resume_screening 是一个本地运行的智能简历筛选工具，面向企业 HR、招聘专员和需要快速筛选候选人的业务人员。核心价值是把“人工读 JD、逐份看简历、主观判断、手工整理结果”的流程，压缩为“输入 JD、批量上传简历、自动匹配评分、导出结果”。

核心能力：

- 支持批量上传简历，典型限制为一次最多 10 份。
- 支持 PDF、DOCX、DOC、TXT、RTF 和图片简历解析；图片走 OCR。
- 在调用大模型前对简历文本做隐私脱敏。
- 调用多种大模型或 OpenAI 兼容接口，输出匹配评分、匹配点、不足点、面试问题。
- 支持按工作年限、学历、核心技能、其他要求等自定义匹配维度影响评分。
- 支持结果按分数排序展示，并导出 Excel。
- API Key 本地加密存储，配置状态全局校验，未配置时拦截核心筛选操作。

## 2. 典型用户流程

1. 用户进入产品首页或应用页。
2. 系统检查当前大模型配置是否有效。
3. 用户输入岗位 JD。
4. 用户上传候选人简历。
5. 用户可选填写自定义匹配维度：工作年限、学历、核心技能权重、额外要求。
6. 点击智能筛选：
   - 未配置 API Key 或 endpoint 时，前端展示提醒并拦截提交。
   - 配置有效时，提交 JD、文件和维度到后端。
7. 后端对每份简历执行：读取文件 → 文档解析或 OCR → 信息脱敏 → 大模型分析。
8. 后端聚合结果，按 score 降序返回。
9. 前端结果页展示简历列表和详情，支持导出 Excel。

## 3. 技术架构

### 后端

后端是 Python FastAPI 服务，关键文件：

- `backend/main.py`：应用入口、页面路由、API 路由、筛选主流程、Excel 导出、健康检查。
- `backend/config.py`：模型配置加载、保存、校验、脱敏展示和加密存储。
- `backend/parser.py`：PDF、DOCX、DOC、TXT、RTF 文档解析。
- `backend/ocr.py`：图片简历 OCR 识别。
- `backend/desensitizer.py`：简历敏感信息识别与脱敏。
- `backend/llm.py`：多模型调用、连通性测试、提示词构造和模型响应 JSON 解析。
- `backend/logger_config.py`：日志配置。
- `backend/tests/`：配置、脱敏和 LLM 响应解析单元测试。

### 前端

前端是原生 HTML/CSS/JavaScript：

- `frontend/landing.html`：产品介绍页。
- `frontend/index.html`：应用主页，负责 JD 输入、维度设置、文件上传和筛选触发。
- `frontend/result.html`：结果页，展示排序后的候选人分析和 Excel 导出入口。
- `frontend/config.html`：API 配置页，配置模型、endpoint、API Key/Secret、模型版本并测试连通。
- `frontend/js/state.js`：全局配置状态管理。
- `frontend/js/cache.js`：页面跳转期间的数据保活。
- `frontend/js/api.js`：后端 API 封装。
- `frontend/js/index.js`：主页交互逻辑。
- `frontend/js/result.js`：结果页交互和导出逻辑。
- `frontend/js/config.js`：配置页交互逻辑。
- `frontend/js/toast.js`：提示组件。

### 部署

- `start.sh`：本地启动脚本。
- `Dockerfile`：Python 3.9 slim 镜像，安装 OCR 依赖和 Python 依赖，启动 uvicorn。
- `docker-compose.yml`：容器编排，挂载配置、日志和密钥目录，配置 CORS 和外部网络。
- `deploy/nginx-resume.conf`：Nginx 部署配置。

## 4. 后端接口地图

主要接口：

- `GET /`：产品介绍页。
- `GET /app`：应用主页。
- `GET /result`：结果页。
- `GET /config`：API 配置页。
- `GET /api/config/status`：获取配置状态。
- `GET /api/config`：获取已脱敏配置。
- `POST /api/config`：保存配置。
- `POST /api/test-connection`：测试模型连通性，并尝试返回可用模型列表。
- `POST /api/screening`：批量简历筛选主接口。
- `POST /api/parse-resume`：单份简历解析预览。
- `POST /api/export`：导出筛选结果为 Excel。
- `GET /api/health`：健康检查。

注意：README 中可能出现旧接口名 `/api/export-excel`，当前后端实现为 `/api/export`，处理问题时以代码实现为准。

## 5. 核心业务链路

### 5.1 筛选主链路

`backend/main.py` 中 `/api/screening` 是主链路入口：

1. 加载本地配置。
2. 检查 `is_config_valid`。
3. 读取当前模型配置，包括 `api_key`、`endpoint`、`model_version`、`api_secret`。
4. 解析可选维度 JSON。
5. 使用 `asyncio.Semaphore` 控制简历并发处理数量。
6. 每份简历进入 `_process_single_resume`：
   - 图片扩展名走 `process_image`。
   - 其他文档走 `parse_document`。
   - 文本解析失败时返回该文件错误。
   - 成功后调用 `desensitize_resume`。
   - 调用 `analyze_resume` 得到结构化分析。
7. 分离成功结果和错误，成功结果按 score 降序排序返回。

### 5.2 文档解析

`backend/parser.py` 使用后缀分发：

- `.pdf` → `PyPDF2.PdfReader`。
- `.docx` → `python-docx`。
- `.doc` → 先尝试 DOCX 方式，失败后尝试 `antiword`。
- `.txt` → 多编码尝试解码。
- `.rtf` → 优先 `striprtf`，缺失时尝试简易文本提取。
- 不支持格式返回明确错误文本。

### 5.3 OCR

图片扩展名包括 `.jpg`、`.jpeg`、`.png`、`.bmp`、`.gif`、`.tiff`、`.webp`。图片简历进入 OCR 模块，部署时需要系统 OCR 能力及相关语言包。

### 5.4 脱敏

`backend/desensitizer.py` 负责在调用大模型前保护候选人隐私。覆盖类型包括：

- 手机号、座机、+86 手机号。
- 邮箱。
- 身份证。
- 姓名，包括显式“姓名：”和简历头部姓名。
- 微信号、QQ、LinkedIn/领英。
- 出生日期。
- 期望薪资、当前薪资。
- 地址、住址、籍贯、户籍等。

修改脱敏逻辑时必须补充或运行 `backend/tests/test_desensitizer.py`。

### 5.5 大模型调用

`backend/llm.py` 抽象了 `LLMCaller` 基类，并包含：

- 豆包。
- 文心。
- 千问。
- 智谱 GLM。
- MinMax。
- DeepSeek。
- 自定义 OpenAI 兼容接口。

核心函数：

- `get_llm_caller`：按模型类型创建调用器。
- `test_connection`：发送轻量探测请求并尝试返回模型列表。
- `build_dimension_instructions`：把自定义维度转换为提示词和评分说明。
- `analyze_resume`：构建 JD + 脱敏简历 + 维度要求的分析请求。
- `LLMCaller._parse_response`：从模型输出中提取 JSON，支持 markdown code block、局部 JSON 和贪婪回退。

修改模型响应解析时必须运行 `backend/tests/test_llm_parse.py`。

## 6. 前端关键交互

### 6.1 配置状态

前端通过 `GlobalState` 与后端配置接口保持状态同步。未配置时：

- 主页顶部显示 API Key 配置提醒。
- 点击智能筛选前先拦截，不应执行 OCR、解析或大模型调用。
- 用户可以继续填写 JD 和上传简历。

### 6.2 数据保活

`CacheManager` 使用 `sessionStorage` 缓存：

- JD 内容。
- 简历文件列表和可恢复数据。
- 页面跳转到配置页再返回时，恢复用户已输入/上传内容。

修改缓存逻辑时要特别验证：去配置页、返回主页、取消弹框、清空内容、完成筛选后的缓存行为。

### 6.3 筛选结果

结果页从 `sessionStorage` 读取 `screening_results`，展示：

- 左侧按匹配度排序的简历列表。
- 右侧当前简历详情：概述、匹配点、不足点、建议面试问题、评分展示。
- Excel 导出按钮调用后端导出接口。

## 7. 隐私与安全约束

处理项目时必须遵守：

1. 不读取、不展示、不提交真实 API Key、API Secret、加密配置和密钥文件。
2. 不把 `config/.key`、`config/models.json.enc`、`logs/`、`.env*`、运行时 PID 等加入提交。
3. 说明配置流程时只描述字段和校验规则，不输出真实值。
4. 简历内容属于个人信息；调试时尽量使用脱敏样例，不在回复中复述真实候选人敏感信息。
5. 大模型请求只能发送脱敏后的简历文本，这是本项目的重要业务安全约束。

## 8. 常见修改场景

### 新增模型接入

1. 在 `backend/llm.py` 中新增 Caller 或扩展 `CustomCaller` 能力。
2. 更新 `get_llm_caller` 的模型类型映射。
3. 更新配置默认值和校验逻辑。
4. 更新 `frontend/config.html` 和 `frontend/js/config.js` 的配置页字段、测试连通和保存逻辑。
5. 增加或更新测试，至少覆盖配置校验和基本调用参数构造。

### 调整匹配维度

1. 修改 `frontend/index.html` 的维度输入项。
2. 修改 `frontend/js/index.js` 中维度收集和提交逻辑。
3. 修改 `backend/llm.py` 的 `build_dimension_instructions`。
4. 验证模型提示词包含新增维度，并检查结果排序不受异常 score 影响。

### 优化解析能力

1. 修改 `backend/parser.py` 或 `backend/ocr.py`。
2. 为新增格式或边界情况添加测试或手工验证样例。
3. 确保解析失败返回可理解错误，不进入模型分析。

### 优化脱敏能力

1. 修改 `backend/desensitizer.py`。
2. 为新增敏感字段增加测试。
3. 确保脱敏不会误伤关键技能、公司、项目经历等匹配信息。

### 修复导出问题

1. 后端接口是 `POST /api/export`。
2. 前端导出逻辑在 `frontend/js/result.js`，API 封装在 `frontend/js/api.js`。
3. 导出字段包括排名、简历文件名、匹配度评分、简历概述、匹配点、不足点、建议面试问题。
4. 注意中文文件名和浏览器下载兼容性。

### 部署问题排查

1. 检查 Docker 镜像是否安装 OCR 系统依赖。
2. 检查 `backend/requirements.txt` 是否覆盖运行所需 Python 包。
3. 检查容器挂载的配置、日志和密钥目录是否可写。
4. 检查 CORS 和 Nginx 路径前缀是否与前端 `<base href>`、API 请求路径一致。
5. 不要把运行时配置或密钥提交到仓库。

## 9. 测试建议

优先级从轻到重：

1. 针对后端纯逻辑变更，运行相关单测：
   - 配置：`backend/tests/test_config.py`
   - 脱敏：`backend/tests/test_desensitizer.py`
   - LLM JSON 解析：`backend/tests/test_llm_parse.py`
2. 对接口修改，补充 FastAPI TestClient 或手工 curl 验证。
3. 对前端交互修改，手工验证：未配置拦截、配置保存、返回保活、上传限制、筛选成功、结果展示、Excel 导出。
4. 对部署修改，验证容器启动、健康检查和静态资源访问。

## 10. 已知注意点

- 项目中存在运行时敏感文件和加密配置路径，必须保持忽略和不泄露。
- 当前 README 和代码可能存在接口命名差异：导出接口以代码中的 `/api/export` 为准。
- 部分文档可能包含过时内容，处理实际问题时以当前代码实现和测试为准。
- 产品介绍页包含外部展示链接；修改公开链接前需确认用户意图。
- `.comate/`、`.trae/`、`.claude/` 等目录通常属于开发辅助上下文，不应默认纳入产品发布。
