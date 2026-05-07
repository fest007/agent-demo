# Agent Demo - 后端服务层

基于 FastAPI 的后端服务，提供 REST API 和 SSE 流式输出，连接前端界面与 Agent 核心层。

## 技术栈

- **框架**: FastAPI + Uvicorn
- **流式输出**: SSE (Server-Sent Events) via sse-starlette
- **数据库**: SQLAlchemy + aiosqlite (异步 SQLite)
- **管理面板**: SQLAdmin
- **配置管理**: pydantic-settings + python-dotenv

## 快速开始

```bash
# 安装依赖
uv sync

# 复制环境变量
cp .env.example .env

# 启动服务
python -m server.main
```

服务启动在 http://localhost:8000，Swagger 文档：http://localhost:8000/docs

## API 接口

### 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 同步对话（等待完整回复） |
| POST | `/api/chat/stream` | 流式对话（SSE，逐 token 返回） |
| GET | `/api/chat/history/{thread_id}` | 获取会话历史 |

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/sessions` | 创建新会话 |
| GET | `/api/sessions` | 列出所有会话 |
| PUT | `/api/sessions/{session_id}` | 更新会话名称 |
| DELETE | `/api/sessions/{session_id}` | 删除会话及关联对话 |
| POST | `/api/sessions/{session_id}/summarize` | LLM 总结命名 |

### 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/knowledge/upload` | 上传文件到知识库 |
| POST | `/api/knowledge/ingest-url` | URL 抓取并入库 |
| GET | `/api/knowledge/list` | 列出知识库文档 |
| DELETE | `/api/knowledge/{doc_id}` | 删除文档 |

### 技能

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skills/list` | 列出所有技能 |
| POST | `/api/skills/generate` | AI 生成新技能 |

### TTS

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tts` | 文本转语音 |

### 管理面板

访问 http://localhost:8000/admin 查看 SQLAdmin 管理界面。

## 项目结构

```
src/server/
├── main.py           # FastAPI 入口，注册路由、CORS、生命周期
├── config.py         # 配置管理（pydantic-settings）
├── deps.py           # 依赖注入（用户认证）
├── utils.py          # 工具函数（Markdown 清理等）
├── api/
│   ├── chat.py       # 对话 API（同步 + 流式 + 历史）
│   ├── session.py    # 会话管理 API（CRUD + LLM 总结）
│   ├── knowledge.py  # 知识库 API
│   ├── skills.py     # 技能 API
│   └── tts.py        # TTS API
├── db/
│   ├── database.py   # 数据库连接与会话管理
│   └── models.py     # SQLAlchemy 模型（Conversation, Session, Knowledge 等）
└── models/
    ├── chat.py       # 对话 Pydantic 模型
    └── session.py    # 会话 Pydantic 模型
```

## 环境变量

参考 `.env.example`：

```bash
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DATABASE_URL=sqlite+aiosqlite:///./data/server.db
AGENT_MODULE_PATH=../agent-demo-agent
```

## 开发命令

```bash
python -m server.main    # 启动服务
pytest                   # 运行测试
ruff check src/          # 代码检查
