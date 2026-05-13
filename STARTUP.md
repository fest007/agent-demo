# Agent Demo 启动指南

本文档说明如何在本地分别启动三个子项目，并提供一组根目录脚本，方便一个终端只跑一个项目。这样后续接入 debugger、看日志或单独重启某一层时更清楚。

## 项目关系

```text
agent-demo-web     React + Vite 前端，端口 3000
        |
        | HTTP / SSE，Vite 代理 /api 到 localhost:8000
        v
agent-demo-server  FastAPI 后端，端口 8000
        |
        | Python 包方式直接调用
        v
agent-demo-agent   LangGraph Agent 核心，默认不需要单独常驻启动
```

当前架构里，`agent-demo-server` 直接以 Python 包方式调用 `agent-demo-agent`，所以日常跑完整 Web 应用时只需要启动后端和前端。`agent-demo-agent` 的启动脚本主要用于命令行调试 Agent。

## 首次准备

在根目录执行：

```bash
cd /Users/szz/Desktop/ai各种测试/agentDemo
```

准备 Agent 配置：

```bash
cd agent-demo-agent
uv sync
cp .env.example .env
```

编辑 `agent-demo-agent/.env`，至少填写：

```bash
MIMO_API_KEY=你的 MiMo API Key
```

如果使用火山方舟模型，可以改为配置：

```bash
DEFAULT_MODEL_PROVIDER=volcengine
ARK_API_KEY=你的火山方舟 API Key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=你的模型 ID 或推理接入点 Endpoint ID
```

方舟兼容 OpenAI Chat Completions，后续也可以用 `MODEL_PROVIDERS` JSON 增加其他 OpenAI 兼容供应商。前端设置页会读取这些配置，并允许切换供应商、模型和 API Key。

向量库开发默认使用 Chroma，零配置即可：

```bash
VECTOR_STORE=chroma
CHROMA_PERSIST_DIR=./data/chroma
```

生产环境推荐切换到 Qdrant：

```bash
VECTOR_STORE=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_PREFIX=agent_demo
QDRANT_VECTOR_SIZE=768
```

准备 Server 配置：

```bash
cd ../agent-demo-server
uv sync
cp .env.example .env
```

准备 Web 依赖：

```bash
cd ../agent-demo-web
nvm use 23
pnpm install
```

## 日常启动顺序

推荐开两个或三个终端，每个终端只跑一个脚本。

### 终端 1：启动后端服务

```bash
cd /Users/szz/Desktop/ai各种测试/agentDemo
./scripts/start-server.sh
```

启动后访问：

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- SQLAdmin: http://localhost:8000/admin

### 终端 2：启动前端服务

```bash
cd /Users/szz/Desktop/ai各种测试/agentDemo
./scripts/start-web.sh
```

启动后访问：

- Web: http://localhost:3000

前端脚本会执行 `nvm use 23`，确保使用本机 Node 23。

### 终端 3：可选，启动 Agent CLI

```bash
cd /Users/szz/Desktop/ai各种测试/agentDemo
./scripts/start-agent-cli.sh
```

这个脚本会进入命令行对话模式，适合单独验证 Agent、工具、RAG、记忆等核心能力。完整 Web 应用不要求它常驻运行。

## 一键启动某一个项目

根目录下提供了三个脚本：

```text
scripts/start-agent-cli.sh  启动 Agent 命令行调试
scripts/start-server.sh     启动 FastAPI 后端
scripts/start-web.sh        启动 Vite 前端
```

它们各自只启动一个项目，故意不做“一条命令拉起全部服务”。后续加 debugger 时，可以在对应终端里单独 attach 或替换启动命令。

## 启动注意事项

- 前端统一使用 Node 23：`nvm use 23`。
- 后端依赖 Agent 的 `.env`，模型供应商、API Key 和模型 ID 应配置在 `agent-demo-agent/.env`。
- 火山方舟的 `ARK_MODEL` 通常不是展示名称，而是模型 ID 或推理接入点 Endpoint ID；设置页切换后，新对话请求会使用当前选择。
- 后端端口默认是 `8000`，前端端口默认是 `3000`。
- 前端 `/api` 请求由 `agent-demo-web/vite.config.ts` 代理到 `http://localhost:8000`。
- 首次使用 RAG/embedding 时，可能需要下载嵌入模型，启动或第一次入库会比较慢。
- 高危工具 `run_shell`、`python_repl`、`write_file` 默认不暴露给 LLM。如本地开发确实需要，在 `agent-demo-agent/.env` 中设置：

```bash
ENABLE_DANGEROUS_TOOLS=true
```

- 文件工具默认限制在项目根目录内，避免 Agent 读写项目外文件。如需调整，可设置：

```bash
TOOL_WORKSPACE_ROOT=/path/to/allowed/workspace
```

- 如果端口被占用，先停掉旧进程，或临时修改对应配置：
  - 后端：`agent-demo-server/.env` 的 `SERVER_PORT`
  - 前端：`agent-demo-web/vite.config.ts` 的 `server.port`

## 常用检查命令

后端/Agent Python 编译检查：

```bash
cd agent-demo-agent
uv run python -m compileall src

cd ../agent-demo-server
uv run python -m compileall src
```

前端构建检查：

```bash
cd agent-demo-web
nvm use 23
pnpm build
```

## Docker Compose

也可以用 Docker Compose 启动 Qdrant、后端和前端：

```bash
docker compose up --build
```

Docker Compose 默认让后端使用 Qdrant：`VECTOR_STORE=qdrant`、`QDRANT_URL=http://qdrant:6333`。当前本地开发更推荐使用上面的分终端脚本。Docker 适合验证容器化部署，不适合后续 debugger 分层调试。
