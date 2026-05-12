# Agent Demo

基于小米 MiMo 大模型的智能代理系统，采用三层架构：React 前端 + FastAPI 后端 + LangGraph Agent 核心。

## 系统架构

```
┌──────────────────────────────────────────────┐
│          前端 (React + TypeScript)            │
│          agent-demo-web (port 3000)           │
│   对话界面 · 语音播放 · 情绪展示 · 管理中台    │
└───────────────────┬──────────────────────────┘
                    │ HTTP / SSE
┌───────────────────┴──────────────────────────┐
│             后端 (FastAPI)                     │
│          agent-demo-server (port 8000)         │
│      API 路由 · 会话管理 · SQLAdmin 面板       │
└───────────────────┬──────────────────────────┘
                    │ Python 内部调用
┌───────────────────┴──────────────────────────┐
│          Agent 核心 (LangGraph)                │
│          agent-demo-agent                      │
│  ┌─────────┐ ┌────────┐ ┌───────┐ ┌────────┐ │
│  │ Agent 图 │ │ RAG 引擎│ │ 工具集 │ │ 记忆系统│ │
│  └─────────┘ └────────┘ └───────┘ └────────┘ │
│  ┌─────────┐ ┌────────┐ ┌───────┐ ┌────────┐ │
│  │ 情绪分析 │ │ TTS 语音│ │ Skills│ │  MCP   │ │
│  └─────────┘ └────────┘ └───────┘ └────────┘ │
└──────────────────────────────────────────────┘
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
    MiMo API    ChromaDB    SQLite
```

## 核心功能

- **智能对话** — 基于 MiMo v2.5-pro 的多轮对话，支持流式输出（SSE）
- **RAG 知识库** — 支持文件上传（PDF/Word/MD/TXT）和网址抓取，基于 ChromaDB 向量检索
- **工具调用** — 内置搜索、计算、文件操作、代码执行等 10+ 工具，LLM 自主决策调度
- **双层记忆** — 短期记忆（会话级，SQLite Checkpointer）+ 长期记忆（跨会话，langmem 自动事实提取）
- **情绪分析** — 实时分析对话情绪（开心/难过/生气等），影响 Agent 回复风格
- **TTS 语音** — MiMo TTS（主）+ Edge-TTS（备），支持语音播放回复
- **Skills 技能** — 内置研究助手、编程助手等技能，支持 LLM 自动生成新技能
- **MCP 协议** — 通过 Model Context Protocol 扩展外部工具
- **会话管理** — 多会话隔离、LLM 自动总结命名、批量删除

## 快速开始

本地分终端启动请优先查看 [STARTUP.md](STARTUP.md)，其中包含三个子项目的一键启动脚本和注意事项。

### 前置条件

- Python >= 3.11
- Node.js >= 18
- pnpm（前端包管理）
- uv（Python 包管理）

### 1. 准备 Agent 核心层配置

```bash
cd agent-demo-agent
uv sync
cp .env.example .env
# 编辑 .env，填入你的 MiMo API Key
```

> 当前后端以 Python 包方式直接调用 `agent-demo-agent`，不需要单独启动 Agent HTTP 服务。
> 如需命令行调试 Agent，可在该目录运行 `python -m agent.main`。

### 2. 启动后端服务

```bash
cd agent-demo-server
uv sync
cp .env.example .env
python -m server.main
```

### 3. 启动前端

```bash
cd agent-demo-web
pnpm install
pnpm dev
```

访问 http://localhost:3000

### Docker Compose（一键启动）

```bash
# 确保各子项目 .env 已配置
docker-compose up --build
```

## 项目结构

```
agentDemo/
├── docker-compose.yml           # Docker 编排
├── 技术方案.md                   # 详细技术设计文档
│
├── agent-demo-agent/            # Agent 核心层
│   ├── src/agent/
│   │   ├── graph.py             # LangGraph ReAct Agent 构建
│   │   ├── tools/               # 内置工具集
│   │   ├── rag/                 # RAG 知识库引擎
│   │   ├── memory/              # 双层记忆系统
│   │   ├── emotion/             # 情绪分析
│   │   ├── tts/                 # TTS 语音合成
│   │   ├── skills/              # Skills 技能系统
│   │   └── mcp/                 # MCP 协议支持
│   └── knowledge/               # 知识库源文件
│
├── agent-demo-server/           # 后端服务层
│   └── src/server/
│       ├── api/                 # API 路由（chat, knowledge, skills, tts, session）
│       ├── db/                  # 数据库模型与连接
│       └── main.py              # FastAPI 入口
│
└── agent-demo-web/              # 前端界面层
    └── src/
        ├── components/          # UI 组件
        ├── stores/              # Zustand 状态管理
        ├── api/                 # API 调用封装
        └── hooks/               # React Hooks
```

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | LangGraph + LangChain |
| LLM | 小米 MiMo v2.5-pro（OpenAI 兼容 API） |
| 向量数据库 | ChromaDB |
| 嵌入模型 | BAAI/bge-base-zh-v1.5 |
| 后端 | FastAPI + SQLAlchemy + SSE |
| 前端 | React 19 + TypeScript + Vite + Ant Design |
| 状态管理 | Zustand |
| TTS | MiMo TTS + Edge-TTS |
| 包管理 | uv (Python) / pnpm (Node) |

## 许可证

[Apache License 2.0](LICENSE)
