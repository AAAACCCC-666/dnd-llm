# D&D 聊天机器人后端

这是一个基于 FastAPI + LangChain 的龙与地下城（D&D）辅助聊天机器人后端项目。

## 环境要求

- Python 3.12+
- uv 包管理器

## 快速开始

### 1. 安装 uv 包管理器（如果还没装的话）

参考 uv [官方文档](https://docs.astral.sh/uv/getting-started/installation/)

### 2. 克隆项目并安装依赖
```bash
git clone git@github.com:WallBreakerNO4/FYP-demo-BackEnd.git
cd backend
uv sync
```

### 3. 配置环境变量
```bash
cp .env.example .env
# 然后编辑 .env 文件，配置必要的API密钥
```

### 4. 启动开发服务器
```bash
uv run main.py
```

服务器将在 http://localhost:8000 启动，支持热重载。

## 环境配置详解

编辑 `.env` 文件，配置以下关键变量：

### 必需配置
```bash
# OpenAI API 配置（必须）
OPENAI_API_KEY="你的API密钥"                    # 必填
OPENAI_BASE_URL="https://api.deepseek.com/v1"  # DeepSeek API地址
OPENAI_MODEL="deepseek-chat"                    # 使用的模型

# 数据库配置
DATABASE_URL="sqlite:///data/data.db"          # 默认使用SQLite，未来生产环境需要使用 PostgreSQL

# CORS 配置
CORS_ORIGINS="http://localhost:3000"           # 前端地址
```

### 可选配置
```bash
# 应用端口
PORT=8080

# 日志配置
LOG_LEVEL="INFO"
LOG_PATH="logs/"

# 提示词配置
SYSTEM_PROMPT_FILE_PATH="assets/system_rule.json"
OPTIONS_PROMPT_FILE_PATH="assets/options_prompt.json"

# 功能开关
SUGGEST_OPTIONS_ENABLED=True                   # 选项建议功能
USE_LANGCHAIN_MEMORY=False                     # LangChain内存系统（实验性）
```

## 开发命令

```bash
# 启动开发服务器
uv run main.py

# 安装新依赖
uv add <包名>

# 同步依赖
uv sync

# 启动服务器（替代方式）
uv run uvicorn main:app --reload
```

## 项目架构

```
backend/
├── app/                    # 应用主目录
│   ├── api/               # API路由
│   │   ├── sessions.py    # 会话管理
│   │   ├── chat.py        # 聊天接口
│   │   └── characters.py  # 角色管理
│   ├── db/                # 数据库相关
│   │   ├── models.py      # 数据模型
│   │   ├── crud.py        # 数据库操作
│   │   └── database.py    # 数据库连接
│   ├── services/          # 业务逻辑
│   │   ├── langchain_service.py      # LangChain服务
│   │   ├── langchain_tools/          # 工具系统
│   │   └── memory/                   # 内存管理
│   └── utils/             # 工具函数
├── assets/                # 数据与提示词
│   ├── dnd_data.json     # D&D规则数据
│   ├── system_rule.json  # 主流程系统提示词
│   └── options_prompt.json # 对话建议系统提示词
├── logs/                 # 日志文件
└── main.py              # 应用入口
```

## API 接口

服务启动后访问 http://localhost:8000/docs 查看完整的API文档（Swagger UI）。

建议使用如 postman 之类的工具对接口进行开发/测试。

主要接口：
- `POST /api/sessions` - 创建聊天会话
- `POST /api/chat/stream` - 流式聊天
- `POST /api/characters` - 创建D&D角色

## 开发注意事项

1. **数据库自动初始化**：首次启动时会自动创建数据库表并导入D&D静态数据
2. **热重载**：代码修改后会自动重启服务器
3. **日志查看**：日志文件在 `logs/` 目录，按日期自动命名
4. **工具系统**：支持骰子投掷、角色属性修改等D&D工具
5. **流式响应**：聊天接口支持Server-Sent Events流式输出

## 故障排除

### 常见问题

**1. 启动失败：ModuleNotFoundError**
```bash
# 确保依赖已安装
uv sync
```

**2. API密钥错误**
- 检查 `.env` 文件中的 `OPENAI_API_KEY` 是否正确
- 确认 `OPENAI_BASE_URL` 与你的API提供商匹配

**3. 数据库错误**
```bash
# 删除数据库文件重新初始化
rm data/data.db
# 重新启动应用
uv run main.py
```

**4. 端口被占用**
```bash
# 修改 .env 文件中的 PORT 配置
PORT=8081
```

**5. CORS错误**
- 检查 `.env` 文件中的 `CORS_ORIGINS` 配置
- 确保包含你的前端地址

### 获取帮助

- 检查 `documents/` 目录下的技术文档（详见下方文档说明）
- 查看日志文件排查具体错误

## 技术文档

`documents/` 目录包含详细的技术文档：

### API 文档 (`documents/api.md`)
- **完整的 REST API 接口说明**
- 包含所有端点的请求/响应格式和示例
- 聊天会话管理、流式聊天、角色管理接口详解
- 工具调用和流式响应事件格式说明
- 数据模型（Schemas）完整定义

### 数据库设计 (`documents/db.md`)
- **完整的数据库结构设计**
- 所有表结构、字段类型、约束关系说明
- 包含 ER 图（实体关系图）
- 静态数据表和关联表详解
- LangChain 消息存储机制说明

### 工具系统实现 (`documents/function_call.md`)
- **LangChain 工具系统详细实现说明**
- 工具定义、注册、执行的完整流程
- 所有可用工具的参数和用法说明（骰子、角色属性修改等）
- 流式工具执行和错误处理机制
- 与 OpenAI Function Calling 兼容性说明

**建议阅读顺序**：
1. 新手先看 API 文档了解接口使用
2. 需要理解数据结构时查看数据库设计文档  
3. 开发工具调用功能时参考工具系统实现文档

## 开发状态

🚧 **项目正在开发中** 🚧

当前功能：
- ✅ 基础聊天功能
- ✅ D&D角色创建和管理  
- ✅ 工具调用系统（掷骰子、属性修改等）
- ✅ 流式响应
- ✅ LangChain集成

计划功能：
- 🔄 剧情梗概/大纲生成
- 🔄 对话记忆优化
- 🔄 D&D 规则书 RAG
