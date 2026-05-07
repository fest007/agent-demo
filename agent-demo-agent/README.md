# Agent Demo - Agent 核心层

基于 LangGraph 的智能代理系统核心层，集成 LLM 对话、RAG 知识库、工具调用、记忆系统、情绪分析、TTS 语音、技能系统和 MCP 协议。

## 技术栈

- **Agent 框架**: LangGraph（LangChain 官方 Agent 编排框架）
- **LLM**: 小米 MiMo v2.5-pro（OpenAI 兼容 API）
- **向量数据库**: ChromaDB
- **嵌入模型**: BAAI/bge-base-zh-v1.5（本地运行，约 400MB）
- **短期记忆**: LangGraph Checkpointer + SQLite（会话级隔离）
- **长期记忆**: LangGraph Store + langmem（跨会话，自动事实提取）
- **TTS**: MiMo TTS（主）+ Edge-TTS（备）
- **MCP**: langchain-mcp-adapters

## 快速开始

```bash
# 安装依赖
uv sync

# 复制环境变量
cp .env.example .env
# 编辑 .env，填入你的 MiMo API Key

# 运行（交互式测试）
python -m agent.main
```

首次运行会自动下载嵌入模型（BAAI/bge-base-zh-v1.5，约 400MB）。

## 核心模块

### Agent 图 (Graph)

LangGraph StateGraph 编排的 Agent 执行流程：

```
用户输入 → 情绪分析 → 思考节点 → [工具调用] → 回复生成 → 情绪反馈
                            ↕
                        工具执行节点
```

- `graph.py` — StateGraph 定义与编译
- `nodes.py` — 图节点实现（思考、工具调用、情绪分析）
- `state.py` — AgentState 状态定义
- `prompts.py` — System Prompt 模板

### 工具中心 (Tools)

内置 13 个工具，LLM 根据任务自主决策调用：

| 工具 | 说明 |
|------|------|
| `search` | DuckDuckGo 网络搜索 |
| `wikipedia` | Wikipedia 查询 |
| `web_scraper` | 网页内容抓取 |
| `calculator` | 数学计算（支持表达式） |
| `datetime_tool` | 日期时间查询 |
| `file_ops` | 文件读写操作 |
| `shell` | Shell 命令执行 |
| `python_repl` | Python 代码执行 |
| `json_tool` | JSON 解析与查询 |
| `csv_tool` | CSV 读取与查询 |
| `http_tool` | HTTP 请求 |
| `url_to_knowledge` | URL 内容入库 |

工具通过 `tools/registry.py` 统一注册管理，支持动态注册/发现。

### RAG 知识库 (RAG)

- `loader.py` — 文档加载器（PDF/Word/MD/TXT/URL）
- `splitter.py` — 文本分割
- `embedder.py` — 嵌入模型封装（bge-base-zh-v1.5）
- `retriever.py` — 向量检索器（封装为 Agent Tool）
- `ingest.py` — 知识库入库脚本

### 记忆系统 (Memory)

**短期记忆** — 基于 LangGraph Checkpointer + SQLite
- 会话级别隔离（按 thread_id）
- 自动保存对话历史

**长期记忆** — 基于 LangGraph Store + langmem
- 跨会话持久化
- 自动从对话中提取用户偏好和事实
- 按 user_id 隔离

### 情绪分析 (Emotion)

- 实时分析用户情绪（happy/sad/angry/neutral 等）
- 情绪影响 Agent 回复风格（System Prompt 注入）
- 情绪标签随回复返回前端展示

### TTS 语音 (TTS)

- **主选**: MiMo TTS（`mimo-v2.5-tts`，限时免费）
- **备选**: Edge-TTS（微软 Neural 引擎，`zh-CN-XiaoxiaoNeural`）
- 统一的 `TTSEngine` 抽象接口，可随时切换

### 技能系统 (Skills)

- 内置技能：研究助手、编程助手、数据分析、写作助手（Markdown 定义）
- LLM 自动生成新技能（`generator.py`）
- 技能注册中心统一管理（`registry.py`）
- 生成的技能持久化到 `skills/store/`

### MCP 协议

通过 `langchain-mcp-adapters` 支持 Model Context Protocol，可连接外部工具服务器。

配置文件：`mcp_servers/config.json`

## 项目结构

```
src/agent/
├── main.py           # 入口 & 快速启动
├── config.py         # 配置管理（pydantic-settings）
├── graph.py          # LangGraph StateGraph 定义
├── nodes.py          # 图节点实现
├── state.py          # AgentState 类型定义
├── prompts.py        # System Prompt 模板
├── tools/            # 工具中心
├── rag/              # RAG 知识库引擎
├── memory/           # 双层记忆系统
├── emotion/          # 情绪分析
├── tts/              # TTS 语音合成
├── skills/           # Skills 技能系统
└── mcp/              # MCP 协议支持
```

## 环境变量

参考 `.env.example`：

```bash
# MiMo API（必填）
MIMO_API_KEY=your_api_key_here
MIMO_BASE_URL=https://api.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5-pro
MIMO_MODEL_FAST=mimo-v2-flash

# TTS
TTS_ENGINE=mimo-tts
TTS_MIMO_MODEL=mimo-v2.5-tts
TTS_FALLBACK_ENGINE=edge-tts
TTS_VOICE=zh-CN-XiaoxiaoNeural

# 向量库
CHROMA_PERSIST_DIR=./data/chroma

# 嵌入模型
EMBEDDING_MODEL=BAAI/bge-base-zh-v1.5

# 记忆
SHORT_TERM_DB=./data/memory.db
LONG_TERM_DB=./data/long_term.db

# MCP
MCP_CONFIG_PATH=./mcp_servers/config.json
```

## 开发命令

```bash
python -m agent.main    # 交互式测试
pytest                  # 运行测试
ruff check src/         # 代码检查
```
