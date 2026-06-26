# 智能简历筛选工具

一个基于大语言模型的本地简历智能筛选工具，支持多模型接入、简历解析脱敏、智能匹配评分和 Excel 导出。

## 功能特性

- **多模型支持**：字节豆包、百度文心、阿里千问、智谱 GLM、MinMax、DeepSeek、自定义 OpenAI 兼容接口
- **多格式简历解析**：PDF、Word、TXT、RTF、图片（OCR）
- **信息脱敏**：自动识别并脱敏手机号、邮箱、身份证、姓名、微信号、QQ、地址、薪资等敏感信息
- **智能匹配**：基于岗位 JD 的简历匹配度评分、匹配点/不足点分析、面试问题建议
- **自定义维度**：支持工作年限、学历、技能权重等自定义匹配维度
- **Excel 导出**：一键导出筛选结果为 Excel 表格
- **本地运行**：所有数据本地处理，API Key 加密存储

## 项目结构

```
Resume_screening/
├── website/                    # 官网页（产品介绍）
│   └── index.html
├── server/                     # 后端服务（FastAPI）
│   ├── main.py                # 主入口，API 路由
│   ├── config.py              # 配置管理（加密存储）
│   ├── llm.py                 # 大模型调用与解析
│   ├── parser.py              # 简历文档解析
│   ├── ocr.py                 # 图片 OCR 识别
│   ├── desensitizer.py        # 敏感信息脱敏
│   ├── logger_config.py       # 日志配置
│   └── requirements.txt       # Python 依赖
├── frontend/                   # 业务前端页面
│   ├── index.html             # 主页（上传简历、输入JD）
│   ├── result.html            # 结果页（筛选结果展示）
│   ├── config.html            # 配置页（模型配置）
│   ├── css/style.css          # 样式
│   ├── js/                    # JavaScript 模块
│   └── favicon.svg
├── tests/                      # 测试
│   └── unit/                   # 单元测试
│       ├── test_llm_parse.py
│       ├── test_desensitizer.py
│       └── test_config.py
├── deploy/                     # 部署与运维
│   ├── DEPLOY_SOP.md          # 部署操作规程
│   ├── Dockerfile
│   ├── docker-compose.yml     # 生产编排
│   ├── docker-compose.dev.yml # 本地开发编排
│   ├── nginx/nginx-resume.conf
│   ├── scripts/
│   │   ├── start.sh           # 启动/停止/健康检查
│   │   └── deploy.sh          # 生产部署脚本
│   └── envs/.env.example      # 环境变量模板
├── config/                     # 运行时配置（已 gitignore）
├── logs/                       # 运行时日志（已 gitignore）
├── docs/                       # 内部文档（已 gitignore）
└── README.md
```

## 快速开始

### 环境要求

- Python 3.8+
- 现代浏览器（Chrome / Edge / Firefox）

### 安装依赖

```bash
cd server
pip install -r requirements.txt
```

### 启动服务

#### 方式一：使用启动脚本

```bash
bash deploy/scripts/start.sh start
```

#### 方式二：手动启动

```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8000
```

启动后访问：http://localhost:8000

### 配置模型

1. 点击右上角「⚙️ API配置」进入配置页
2. 选择当前使用的模型类型
3. 填写 API Key 和 Endpoint
4. 点击「测试连通」验证配置
5. 选择模型版本（可选）
6. 点击「保存配置」

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config/status` | 获取配置状态 |
| GET | `/api/config` | 获取脱敏后的配置 |
| POST | `/api/config` | 保存配置 |
| POST | `/api/test-connection` | 测试模型连通性 |
| POST | `/api/parse-resume` | 解析单份简历（预览） |
| POST | `/api/screening` | 批量简历筛选 |
| POST | `/api/export` | 导出 Excel |

## 运行测试

```bash
cd server
pip install pytest
python -m pytest ../tests/unit/ -v
```

## 技术栈

- **后端**：FastAPI + uvicorn
- **文档解析**：PyPDF2 / python-docx / antiword / striprtf
- **图片 OCR**：pytesseract（Tesseract OCR，支持 chi_sim + eng）
- **加密存储**：cryptography (Fernet)
- **前端**：原生 HTML + CSS + JavaScript
- **导出**：openpyxl (Excel)

## 隐私说明

- API Key 使用 Fernet 对称加密存储，密钥位于 `~/.config/resume_screening/.key`
- 简历内容仅在本地处理，不会上传至任何第三方服务（除调用大模型 API 外）
- 脱敏后的简历内容才会发送给大模型进行分析

## License

MIT
