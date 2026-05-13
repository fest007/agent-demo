# Agent Demo

一个支持 OpenAI 兼容模型供应商的多模态 Agent 应用，采用三层架构：React 前端 + FastAPI 后端 + LangGraph Agent 核心。

项目最初以小米 MiMo 为默认模型接入，现在已经扩展为供应商可配置架构：只要供应商提供 OpenAI 兼容的 Chat Completions 返回格式，就可以在设置页或环境变量中接入。当前内置支持 MiMo、火山方舟，也支持用户自定义 Base URL、API Key 和模型 ID。

## 系统架构

```text
┌──────────────────────────────────────────────┐
│          前端 (React + TypeScript)            │
│          agent-demo-web (port 3000)           │
│  对话界面 · 模型设置 · 知识库 · 图片/视频组件  │
└───────────────────┬──────────────────────────┘
                    │ HTTP / SSE
┌───────────────────┴──────────────────────────┐
│             后端 (FastAPI)                     │
│          agent-demo-server (port 8000)         │
│ API 路由 · 会话管理 · 异步媒体任务 · SQLAdmin  │
└───────────────────┬──────────────────────────┘
                    │ Python 内部调用
┌───────────────────┴──────────────────────────┐
│          Agent 核心 (LangGraph)                │
│          agent-demo-agent                      │
│  ┌─────────┐ ┌────────┐ ┌───────┐ ┌────────┐ │
│  │ Agent 图 │ │ RAG 引擎│ │ 工具集 │ │ 记忆系统│ │
│  └─────────┘ └────────┘ └───────┘ └────────┘ │
│  ┌─────────┐ ┌────────┐ ┌───────┐ ┌────────┐ │
│  │ 意图路由 │ │ TTS 语音│ │ Skills│ │  MCP   │ │
│  └─────────┘ └────────┘ └───────┘ └────────┘ │
└──────────────────────────────────────────────┘
                    │
         ┌──────────┼──────────┬──────────────┐
         ▼          ▼          ▼              ▼
 OpenAI-compatible Chroma/Qdrant SQLite   Media APIs
```

## 核心能力

- **多供应商模型接入**：支持 MiMo、火山方舟和自定义 OpenAI 兼容供应商，可在设置页切换供应商、API Key、Base URL 和模型。
- **智能对话**：LangGraph Agent 多轮对话，支持 SSE 流式输出、思考态展示、工具调用展示和错误透出。
- **意图路由**：简单问答、图片生成、视频生成等请求先经过 Agent 层意图判断，再进入对应通路。
- **RAG 知识库**：支持文件上传、文本入库和 URL 网页正文提取入库；回答可携带引用并跳转到知识库片段。
- **向量库可切换**：开发默认 Chroma，生产可通过 `VECTOR_STORE=qdrant` 切换到 Qdrant。
- **双层记忆**：短期记忆使用 SQLite Checkpointer，长期记忆使用 SQLite 权威存储 + 向量库语义检索。
- **图片/视频生成**：支持文生图、图生图、文生视频、图生视频、图文生视频；媒体任务异步轮询，不阻塞当前会话。
- **工具与 Skills**：内置搜索、计算、文件、RAG、技能等工具，支持 MCP 扩展外部工具。
- **会话管理**：多会话隔离、自动总结命名、历史恢复、媒体任务完成通知。
- **发版自动化**：修改版本号后推送到 GitHub，可自动打包并上传 GitHub Releases。
- **桌面安装包**：Release 使用 Tauri + Python sidecar 产出 macOS `.dmg` 和 Windows `.exe`。

## 快速开始

本地分终端启动优先查看 [STARTUP.md](STARTUP.md)，里面包含三个子项目的一键启动脚本和注意事项。

### 前置条件

- Python >= 3.11
- Node.js 23（本项目本机统一使用 `nvm use 23`）
- Rust stable（仅桌面调试/打包需要）
- pnpm
- uv

### 1. 准备 Agent 配置

```bash
cd agent-demo-agent
uv sync
cp .env.example .env
```

至少配置一个 OpenAI 兼容模型供应商。例如 MiMo：

```bash
DEFAULT_MODEL_PROVIDER=mimo
MIMO_API_KEY=your_api_key
MIMO_BASE_URL=https://api.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5-pro
MIMO_MODEL_FAST=mimo-v2-flash
```

火山方舟：

```bash
DEFAULT_MODEL_PROVIDER=volcengine
ARK_API_KEY=your_ark_api_key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=your_chat_model_or_endpoint_id
```

自定义 OpenAI 兼容供应商可以通过设置页保存，也可以用 `MODEL_PROVIDERS` JSON 配置。注意：当前通用对话链路要求供应商返回 OpenAI Chat Completions 兼容格式；图片和视频生成按各供应商实际 API 单独适配。

### 2. 启动后端

```bash
cd agent-demo-server
uv sync
cp .env.example .env
python -m server.main
```

后端默认端口：`8000`。

### 3. 启动前端

```bash
cd agent-demo-web
source ~/.nvm/nvm.sh
nvm use 23
pnpm install
pnpm dev
```

访问：http://localhost:3000

### 分终端启动脚本

根目录提供了三个脚本，每个脚本只启动一个项目，方便后续调试：

```text
scripts/start-server.sh      FastAPI 后端
scripts/start-web.sh         Vite 前端
scripts/start-agent-cli.sh   Agent CLI 调试
```

## Docker Compose

```bash
docker compose up --build
```

Docker Compose 会启动 Qdrant、后端和前端。容器化部署默认让后端使用：

```bash
VECTOR_STORE=qdrant
QDRANT_URL=http://qdrant:6333
```

本地开发默认使用 Chroma：

```bash
VECTOR_STORE=chroma
CHROMA_PERSIST_DIR=./data/chroma
```

## 项目结构

```text
agentDemo/
├── docker-compose.yml
├── STARTUP.md
├── RELEASE.md
├── VERSION
├── 技术方案.md
├── scripts/
│   ├── start-server.sh
│   ├── start-web.sh
│   ├── start-agent-cli.sh
│   ├── bump-version.mjs
│   └── prepare-release-bundle.mjs
│
├── agent-demo-agent/
│   └── src/agent/
│       ├── main.py
│       ├── model_providers.py
│       ├── intent/
│       ├── tools/
│       ├── rag/
│       ├── memory/
│       ├── emotion/
│       ├── tts/
│       ├── skills/
│       └── mcp/
│
├── agent-demo-server/
│   └── src/server/
│       ├── api/
│       ├── db/
│       ├── models/
│       ├── services/
│       └── main.py
│
└── agent-demo-web/
    └── src/
        ├── components/
        ├── pages/
        ├── stores/
        ├── api/
        ├── hooks/
        └── utils/
```

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | LangGraph + LangChain |
| 模型接入 | OpenAI 兼容 Chat Completions，内置 MiMo / 火山方舟 / 自定义供应商 |
| 多模态生成 | 火山方舟图片/视频任务接口，后续可扩展其他供应商 |
| 向量数据库 | Chroma（开发）/ Qdrant（生产） |
| 嵌入模型 | BAAI/bge-base-zh-v1.5 |
| 后端 | FastAPI + SQLAlchemy + SSE |
| 前端 | React 19 + TypeScript + Vite + Ant Design |
| 状态管理 | Zustand |
| TTS | MiMo TTS + Edge-TTS |
| 包管理 | uv (Python) / pnpm (Node) |
| 发版 | GitHub Actions + GitHub Releases |
| 桌面壳 | Tauri + Python sidecar |

## 发版

```bash
source ~/.nvm/nvm.sh
nvm use 23
node scripts/bump-version.mjs 0.2.0
git add VERSION agent-demo-web/package.json agent-demo-agent/pyproject.toml agent-demo-server/pyproject.toml
git commit -m "chore: release v0.2.0"
git push origin main
```

推送后 GitHub Actions 会构建前端、打包 Python sidecar、生成 Tauri `.dmg` / `.exe`，并上传到 GitHub Releases。更多说明见 [RELEASE.md](RELEASE.md)。

## 许可证

[Apache License 2.0](LICENSE)
