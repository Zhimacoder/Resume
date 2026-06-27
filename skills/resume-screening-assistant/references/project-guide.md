# Resume_screening 项目业务与架构指南

本指南沉淀智能简历筛选工具的业务、架构和维护要点，用于后续快速理解和处理项目任务。

## 1. 产品定位

Resume_screening 是一个智能简历筛选工具，面向企业 HR、招聘专员和需要快速筛选候选人的业务人员。支持云端一键使用和本地部署。核心价值是把"人工读 JD、逐份看简历、主观判断、手工整理结果"的流程，压缩为"输入 JD、批量上传简历、自动匹配评分、导出结果"。

核心能力：

- 支持批量上传简历，典型限制为一次最多 10 份。
- 支持 PDF、DOCX、DOC、TXT、RTF 和图片简历解析；图片走 OCR。
- 在调用大模型前对简历文本做隐私脱敏（手机号、邮箱、身份证、姓名、微信号、QQ、地址、薪资等）。
- 内置 DeepSeek 模型推荐，支持自定义接入任意 OpenAI 兼容接口的大模型，输出匹配评分、匹配点、不足点、面试问题。
- 支持按工作年限、学历、核心技能、年龄范围、其他要求等自定义匹配维度影响评分。
- 自动从身份证和出生日期字段精确提取年龄，不通过毕业年份/工作年限推断。
- 支持结果按分数排序展示，并导出 Excel。
- 双模式架构：生产模式（用户自带 API Key，浏览器 localStorage 存储）/ 本地模式（服务器端 Fernet 加密配置）。

## 2. 典型用户流程

1. 用户进入产品首页或应用页。
2. 生产模式下，系统检查浏览器 localStorage 中的 API Key 配置是否有效。
3. 用户输入岗位 JD。
4. 用户上传候选人简历。
5. 用户可选填写自定义匹配维度：工作年限、学历、核心技能权重、年龄范围、额外要求。
6. 点击智能筛选：
   - 未配置 API Key 或 endpoint 时，前端展示提醒并拦截提交。
   - 配置有效时，提交 JD、文件和维度到后端（API Key 随请求上传）。
7. 后端对每份简历执行：读取文件 → 文档解析或 OCR → 提取年龄（脱敏前）→ 信息脱敏 → 大模型分析。
8. 后端聚合结果，按 score 降序返回，年龄不符合范围的标记过滤。
9. 前端结果页展示简历列表和详情，支持导出 Excel。

## 3. 技术架构

### 目录结构（SOP 规范）

```
Resume_screening/
├── server/                     # 后端服务（FastAPI）
│   ├── main.py                # 主入口，API 路由，页面路由，筛选主流程
│   ├── config.py              # 配置管理（加密存储、双模式支持）
│   ├── llm.py                 # 大模型调用与响应解析
│   ├── parser.py              # 简历文档解析
│   ├── ocr.py                 # 图片 OCR 识别
│   ├── desensitizer.py        # 敏感信息脱敏
│   ├── age_extractor.py       # 年龄精确提取
│   ├── logger_config.py       # 日志配置
│   └── requirements.txt       # Python 依赖
├── frontend/                   # 业务前端页面
│   ├── index.html             # 主页（上传简历、输入JD）
│   ├── result.html            # 结果页（筛选结果展示）
│   ├── config.html            # 配置页（DeepSeek / 自定义模型）
│   ├── css/style.css          # 样式
│   └── js/                    # JavaScript 模块
├── website/                    # 官网落地页（产品介绍）
│   └── index.html
├── tests/unit/                 # 单元测试
│   ├── test_llm_parse.py
│   ├── test_desensitizer.py
│   ├── test_config.py
│   ├── test_age_extractor.py
│   └── test_screening_modes.py
├── deploy/                     # 部署与运维
│   ├── Dockerfile
│   ├── docker-compose.yml     # 生产编排
│   ├── nginx/nginx-resume.conf
│   └── scripts/
├── config/                     # 运行时配置（已 gitignore）
├── logs/                       # 运行时日志（已 gitignore）
└── docs/                       # 内部文档（已 gitignore）
```

### 前端模块

前端是原生 HTML/CSS/JavaScript：

- `frontend/index.html`：应用主页，负责 JD 输入、维度设置、年龄筛选、文件上传和筛选触发。
- `frontend/result.html`：结果页，展示排序后的候选人分析和 Excel 导出入口。
- `frontend/config.html`：API 配置页，支持 DeepSeek 和自定义模型两个选项，配置 endpoint、API Key、模型名称（自定义）、模型版本，测试连通。
- `frontend/js/state.js`：全局配置状态管理（双模式支持，localStorage 读写）。
- `frontend/js/cache.js`：页面跳转期间的数据保活（sessionStorage）。
- `frontend/js/api.js`：后端 API 封装（FormData 上传，含 api_key 字段）。
- `frontend/js/index.js`：主页交互逻辑。
- `frontend/js/result.js`：结果页交互和导出逻辑。
- `frontend/js/config.js`：配置页交互逻辑（模型 Tab 切换、连通测试、版本加载）。
- `frontend/js/toast.js`：提示组件。

### 部署

- `deploy/Dockerfile`：Python slim 镜像，安装 OCR 依赖和 Python 依赖，启动 uvicorn（2 worker）。
- `deploy/docker-compose.yml`：容器编排，环境变量 `REQUIRE_USER_API_KEY=true`（生产模式），挂载配置、日志和密钥目录，连接外部 Nginx 网络。
- `deploy/nginx/nginx-resume.conf`：Nginx 反向代理配置（路径前缀 `/resume/server/`）。

## 4. 后端接口地图

主要接口：

- `GET /`：官网落地页（website/index.html）。
- `GET /app`：应用主页。
- `GET /result`：结果页。
- `GET /config`：API 配置页。
- `GET /api/health`：健康检查。
- `GET /api/config/status`：获取配置状态（生产模式下返回 `require_user_api_key: true, models: {}`）。
- `GET /api/config`：获取已脱敏配置（生产模式返回 403）。
- `POST /api/config`：保存配置（生产模式返回 403）。
- `POST /api/test-connection`：测试模型连通性，并尝试返回可用模型列表（生产模式需前端传入 api_key/endpoint）。
- `POST /api/screening`：批量简历筛选主接口（FormData，含 api_key 字段）。
- `POST /api/parse-resume`：单份简历解析预览。
- `POST /api/export`：导出筛选结果为 Excel。

## 5. 核心业务链路

### 5.1 双模式架构

通过环境变量 `REQUIRE_USER_API_KEY` 控制：

- **生产模式（true）**：服务器端不存储任何 API Key。用户在浏览器 localStorage 中配置 Key，筛选时随 FormData 上传。`/api/config` POST 返回 403，`/api/config/status` 返回空 models。
- **本地模式（false，默认）**：沿用 Fernet 加密存储，API Key 保存在服务器端，密钥在 `~/.config/resume_screening/.key`。

### 5.2 筛选主链路

`server/main.py` 中 `/api/screening` 是主链路入口：

1. 确定模型配置来源（生产模式从请求 FormData 获取，本地模式从加密配置获取）。
2. 校验 API Key 和 endpoint。
3. 解析可选维度 JSON（含 age_min、age_max）。
4. 使用 `asyncio.Semaphore(3)` 控制简历并发处理数量。
5. 每份简历进入 `_process_single_resume`：
   - 提取原始文本（图片走 OCR）。
   - 从原始文本（未脱敏）提取年龄信息。
   - 对文本执行脱敏处理。
   - 调用 `analyze_resume` 得到结构化分析。
   - 年龄不符合范围时标记 `age_filtered: true`。
6. 分离成功结果和错误，成功结果按 score 降序排序返回。

### 5.3 年龄提取

`server/age_extractor.py` 精确提取年龄，策略：

1. 从身份证号（18位/15位）提取出生日期，计算周岁。
2. 从显式出生日期字段（"出生"/"生日"/"出生日期"等）提取。
3. 仅接受 16-80 岁的合理范围。
4. 不从毕业年份、工作年限推断年龄（避免误判）。
5. 必须在脱敏前提取，否则身份证号会被脱敏掉。

### 5.4 文档解析

`server/parser.py` 使用后缀分发：

- `.pdf` → `PyPDF2.PdfReader`。
- `.docx` → `python-docx`。
- `.doc` → 先尝试 DOCX 方式，失败后尝试 `antiword`。
- `.txt` → 多编码尝试解码。
- `.rtf` → 优先 `striprtf`，缺失时尝试简易文本提取。
- 不支持格式返回明确错误文本。

### 5.5 OCR

图片扩展名包括 `.jpg`、`.jpeg`、`.png`、`.bmp`、`.gif`、`.tiff`、`.webp`。图片简历进入 OCR 模块，部署时需要 Tesseract OCR 及 `chi_sim+eng` 语言包。

### 5.6 脱敏

`server/desensitizer.py` 负责在调用大模型前保护候选人隐私。覆盖类型包括：

- 手机号、座机、+86 手机号。
- 邮箱。
- 身份证。
- 姓名（显式"姓名："字段和简历头部姓名）。
- 微信号、QQ、LinkedIn/领英。
- 出生日期。
- 期望薪资、当前薪资。
- 地址、住址、籍贯、户籍等。

修改脱敏逻辑时必须补充或运行 `tests/unit/test_desensitizer.py`。

### 5.7 大模型调用

`server/llm.py` 包含多种模型调用器：

- **DeepSeekCaller**：DeepSeek 官方 API（OpenAI 兼容格式）。
- **CustomCaller**：通用 OpenAI 兼容接口调用器，支持任意厂商的兼容接口。
- 其他 Caller（DoubaoCaller、WenxinCaller 等）保留在代码中以兼容，但前端配置页不再提供入口。

核心函数：

- `get_llm_caller`：按模型类型创建调用器（未知类型 fallback 到 CustomCaller）。
- `test_connection`：发送轻量探测请求并尝试返回模型列表。
- `build_dimension_instructions`：把自定义维度（含年龄范围）转换为提示词和评分说明。
- `analyze_resume`：构建 JD + 脱敏简历 + 维度要求的分析请求，传入 age_info/age_min/age_max。
- `LLMCaller._parse_response`：三层降级策略（markdown code block → 精确 JSON 匹配 → 贪婪回退）提取 JSON。

修改模型响应解析时必须运行 `tests/unit/test_llm_parse.py`。

## 6. 前端关键交互

### 6.1 配置状态

前端通过 `GlobalState` 管理双模式配置状态：

- 生产模式：从 localStorage 读写 `UserConfigStore`。
- 本地模式：从后端 `/api/config/status` 和 `/api/config` 同步。
- 未配置时：主页顶部显示 API Key 配置提醒，点击智能筛选前拦截。
- 用户可以继续填写 JD 和上传简历。

### 6.2 配置页模型切换

- 只有两个 Tab：DeepSeek 和自定义。
- DeepSeek 面板：API Key + 模型版本选择（测试连通后自动加载）。
- 自定义面板：模型名称 + Endpoint + API Key + 模型版本。
- 选中的 Tab 决定 `model_type` 字段值（`deepseek` 或 `custom`）。

### 6.3 数据保活

`CacheManager` 使用 `sessionStorage` 缓存：

- JD 内容。
- 简历文件列表和可恢复数据。
- 页面跳转到配置页再返回时，恢复用户已输入/上传内容。

修改缓存逻辑时要特别验证：去配置页、返回主页、取消弹框、清空内容、完成筛选后的缓存行为。

### 6.4 筛选结果

结果页从 `sessionStorage` 读取 `screening_results`，展示：

- 左侧按匹配度排序的简历列表（被年龄过滤的项有标记）。
- 右侧当前简历详情：概述、匹配点、不足点、建议面试问题、评分展示。
- Excel 导出按钮调用后端导出接口。

## 7. 隐私与安全约束

处理项目时必须遵守：

1. 生产模式下不在服务器端持久化存储任何 API Key。
2. 不读取、不展示、不提交真实 API Key、加密配置和密钥文件。
3. 不把 `config/.key`、`config/models.json.enc`、`logs/`、`.env*`、运行时 PID、`deploy/scripts/deploy.sh` 等加入提交。
4. 简历内容属于个人信息；调试时尽量使用脱敏样例，不在回复中复述真实候选人敏感信息。
5. 大模型请求只能发送脱敏后的简历文本，这是本项目的重要业务安全约束。
6. 年龄提取必须在脱敏前执行（身份证号在脱敏后不可用）。
7. `docs/` 目录整个不提交到 Git。

## 8. 常见修改场景

### 新增模型接入

通过自定义模型面板即可接入任意 OpenAI 兼容接口，无需改代码。如需内置新模型推荐：

1. 在 `server/llm.py` 中新增 Caller 或复用 `CustomCaller`。
2. 更新 `get_llm_caller` 的模型类型映射。
3. 更新 `server/config.py` 的 `DEFAULT_MODELS`（本地模式默认配置）。
4. 更新 `frontend/config.html` 添加模型 Tab 和面板。
5. 更新 `frontend/js/config.js` 的 `modelFields` 和 `getModelDisplayName`。
6. 增加或更新测试。

### 调整匹配维度

1. 修改 `frontend/index.html` 的维度输入项。
2. 修改 `frontend/js/index.js` 中维度收集和提交逻辑。
3. 修改 `server/llm.py` 的 `build_dimension_instructions`。
4. 修改 `server/main.py` 中维度解析和过滤逻辑。
5. 验证模型提示词包含新增维度，并检查结果排序不受异常 score 影响。

### 优化解析能力

1. 修改 `server/parser.py` 或 `server/ocr.py`。
2. 为新增格式或边界情况添加测试或手工验证样例。
3. 确保解析失败返回可理解错误，不进入模型分析。

### 优化脱敏能力

1. 修改 `server/desensitizer.py`。
2. 为新增敏感字段增加测试。
3. 确保脱敏不会误伤关键技能、公司、项目经历等匹配信息。

### 修复导出问题

1. 后端接口是 `POST /api/export`。
2. 前端导出逻辑在 `frontend/js/result.js`，API 封装在 `frontend/js/api.js`。
3. 导出字段包括排名、简历文件名、匹配度评分、简历概述、匹配点、不足点、建议面试问题。
4. 注意中文文件名和浏览器下载兼容性。

### 部署问题排查

1. 检查 Docker 镜像是否安装 OCR 系统依赖（tesseract-ocr、tesseract-ocr-chi-sim、antiword 等）。
2. 检查 `server/requirements.txt` 是否覆盖运行所需 Python 包。
3. 检查容器挂载的配置、日志和密钥目录是否可写。
4. 检查外部 Docker 网络名称是否与 Nginx 容器所在网络一致（`zhima-soccer_zhima-soccer-network`）。
5. 检查 CORS 环境变量和 Nginx 路径前缀是否与前端 `<base href>`、API 请求路径一致。
6. 容器重建后需 `docker exec zhima-soccer-nginx nginx -s reload` 刷新 DNS 缓存。
7. 不要把运行时配置、密钥或 `deploy/scripts/deploy.sh`（含服务器信息）提交到仓库。

## 9. 测试建议

优先级从轻到重：

1. 针对后端纯逻辑变更，运行相关单测：
   - 配置：`tests/unit/test_config.py`
   - 脱敏：`tests/unit/test_desensitizer.py`
   - LLM JSON 解析：`tests/unit/test_llm_parse.py`
   - 年龄提取：`tests/unit/test_age_extractor.py`
   - 双模式筛选：`tests/unit/test_screening_modes.py`
2. 对接口修改，补充 FastAPI TestClient 或手工 curl 验证。
3. 对前端交互修改，手工验证：未配置拦截、配置保存、返回保活、上传限制、筛选成功、年龄过滤、结果展示、Excel 导出。
4. 对部署修改，验证容器启动、健康检查（`/api/health`）、静态资源访问、Nginx 代理。

## 10. 已知注意点

- 项目中存在运行时敏感文件和加密配置路径，必须保持忽略和不泄露。
- 生产环境通过 Nginx 路径前缀 `/resume/server/` 访问，本地开发直接 `http://localhost:8000`。
- 前端 `<base href>` 在生产构建时需要与 Nginx 路径前缀一致。
- slim 版 Docker 镜像不含 curl，健康检查需通过外部 Nginx 代理验证。
- Docker 外部网络名称依赖于 Nginx 项目目录名，重建服务器时需同步更新 `deploy/docker-compose.yml`。
- `.comate/`、`.trae/`、`.claude/` 等目录属于开发辅助上下文，不应纳入产品发布。
