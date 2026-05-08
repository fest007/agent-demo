# Agent Demo - Agent 核心层

基于 LangGraph 的智能代理系统核心层，集成 LLM 对话、RAG 知识库、工具调用、向量化记忆系统、情绪分析、TTS 语音、技能系统和 MCP 协议。

## 技术栈

| 类别 | 技术 |
|------|------|
| **Agent 框架** | LangGraph（LangChain 官方 Agent 编排框架） |
| **LLM** | 小米 MiMo v2.5-pro（OpenAI 兼容 API） |
| **向量数据库** | ChromaDB（知识库 + 用户记忆，双集合） |
| **嵌入模型** | BAAI/bge-base-zh-v1.5（768 维，本地运行，约 400MB） |
| **短期记忆** | LangGraph Checkpointer + SQLite（会话级隔离） |
| **长期记忆** | SQLite（权威存储）+ ChromaDB（向量检索），双写架构 |
| **TTS** | MiMo TTS（主）+ Edge-TTS（备） |
| **MCP** | langchain-mcp-adapters |
| **Python** | >= 3.11，使用 `uv` 管理依赖 |

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

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent 核心层                              │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ memory/  │  │  rag/    │  │ emotion/ │  │  tools/  │        │
│  │ 双层记忆  │  │ RAG知识库│  │ 情绪分析  │  │ 工具中心  │        │
│  │          │  │          │  │          │  │  14个工具  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │ skills/  │  │  tts/    │  │  mcp/    │                       │
│  │ 技能系统  │  │ 语音合成  │  │ MCP协议   │                       │
│  └──────────┘  └──────────┘  └──────────┘                       │
│                                                                   │
│  main.py (入口: chat / chat_stream)                              │
│  graph.py (LangGraph create_react_agent)                         │
│  nodes.py (emotion_node / rag_node / memory_node / think_node)  │
│  state.py (AgentState 状态定义)                                   │
│  prompts.py (System Prompt 模板)                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 数据存储

| 存储 | 技术 | 路径 | 用途 |
|------|------|------|------|
| 短期记忆 | SQLite (AsyncSqliteSaver) | `data/memory.db` | 会话级对话历史，按 thread_id 隔离 |
| 长期记忆 | SQLite | `data/long_term.db` | 用户偏好/事实的权威存储 |
| 向量记忆 | ChromaDB | `data/chroma` | 用户记忆的语义检索（`user_memory` 集合） |
| 知识库 | ChromaDB | `data/chroma` | RAG 文档的语义检索（`knowledge` 集合） |

注意：向量记忆和知识库共享同一个 ChromaDB 持久化目录，但使用不同的集合（collection），互不干扰。

---

## 执行流程

用户发送一条消息时，完整的处理流程如下：

```
用户消息 "帮我写个项目方案"
    │
    ├──→ analyze_emotion(llm, message)         → "neutral"
    ├──→ _get_rag_context(message)             → RAG 检索结果
    └──→ _get_memory_context(message, user_id) → 记忆上下文
         │
         │  三个任务并行执行 (asyncio.gather)
         ▼
    _build_system_prompt(rag, memory, emotion)
         │
         │  组装完整系统提示词：
         │  - 基础人设 (prompts.py)
         │  - {memory_context} 用户记忆
         │  - {rag_context} 知识库内容
         │  - {skill_context} 技能指令
         │  - 情绪风格指令
         ▼
    SystemMessage + HumanMessage → create_react_agent
         │
         ▼
    ┌─ ReAct 循环 ──────────────────────────────┐
    │  LLM 推理 → 是否调用工具？                   │
    │    ├─ 是 → 执行工具 → 结果反馈给 LLM → 继续  │
    │    └─ 否 → 生成最终回复                      │
    └────────────────────────────────────────────┘
         │
         ▼
    返回 {content, emotion, thread_id}
```

### 并行预处理

在 Agent 的 ReAct 循环开始前，三个上下文任务通过 `asyncio.gather` 并行执行：

1. **情绪分析** (`analyze_emotion`) — 调用 LLM 判断用户情绪标签
2. **RAG 检索** (`_get_rag_context`) — 在 ChromaDB 知识库中语义搜索相关内容（在线程池中执行）
3. **记忆检索** (`_get_memory_context`) — 语义搜索用户长期记忆 + 加载核心偏好（在线程池中执行）

三者的结果合并注入系统提示词后，才进入 Agent 的 ReAct 循环。

---

## 记忆系统

记忆系统分为短期记忆和长期记忆两层，解决不同时间尺度的上下文需求。

### 短期记忆（Session-level）

基于 LangGraph 的 `AsyncSqliteSaver` Checkpointer 实现。

- **存储**：SQLite，路径 `data/memory.db`
- **隔离**：按 `thread_id`（格式 `{user_id}_{session_id}`）
- **机制**：每次 Agent 执行后，LangGraph 自动保存完整状态（所有消息）；下次用同一 `thread_id` 执行时自动加载
- **生命周期**：会话级别，同一 thread_id 下的对话保持上下文

```
第 1 轮对话: 用户消息 → Agent 处理 → 自动保存到 memory.db
第 2 轮对话: 用户消息 → 自动加载 thread_id 的历史 → Agent 看到完整上下文 → 处理 → 保存
```

### 长期记忆（Cross-session）

跨会话持久化的用户信息，采用 **SQLite + ChromaDB 双写架构**。

#### 存储设计

**SQLite（权威存储）**：
```
memories 表:
├── id          INTEGER  自增主键
├── user_id     TEXT     用户标识
├── namespace   TEXT     记忆分类 (facts / preferences)
├── key         TEXT     记忆键
├── value       TEXT     记忆值
├── created_at  TEXT     创建时间
├── updated_at  TEXT     更新时间
└── UNIQUE(user_id, namespace, key)
```

**ChromaDB（向量检索）**：
```
user_memory 集合:
├── id          "{user_id}_{namespace}_{key}"  确定性 ID，支持 upsert
├── document    "{key}: {value}"               用于生成嵌入的文本
├── embedding   768 维向量 (bge-base-zh-v1.5)
└── metadata    {user_id, namespace, key, value}
```

两个命名空间：
- `preferences`：用户偏好（如回复风格、语言偏好）
- `facts`：用户事实（如公司名称、职位、项目背景）

#### 写入路径（双写）

```
MemoryManager.save_fact("公司名称", "XX科技")
  → LongTermMemory.save(user_id, "facts", "公司名称", "XX科技")
    → SQLite:  INSERT OR REPLACE INTO memories ...
    → ChromaDB: upsert into user_memory
        id: "default_facts_公司名称"
        document: "公司名称: XX科技"
        embedding: bge-base-zh("公司名称: XX科技")
        metadata: {user_id: "default", namespace: "facts", ...}
```

ChromaDB 写入失败不影响 SQLite 主路径（try/except 降级）。

#### 删除路径（双删）

```
MemoryManager 删除记忆
  → SQLite:  DELETE FROM memories WHERE ...
  → ChromaDB: delete ids=["{user_id}_{namespace}_{key}"]
```

#### 检索路径（混合检索）

```
用户提问 "帮我写个项目方案"
  │
  ├── 语义搜索 (ChromaDB)
  │   → embed("帮我写个项目方案")
  │   → collection.query(where={user_id}, top_k=5)
  │   → 返回: [公司名称=XX科技, 项目背景=..., ...]
  │
  └── 核心偏好 (SQLite)
      → SELECT * WHERE namespace="preferences"
      → 返回: [回复风格=简洁, 语言=中文, ...]
  │
  ▼
  去重合并（核心偏好优先）→ 格式化 → 注入系统提示词
```

**设计决策**：
- `preferences` 始终注入（不按相关性过滤），因为"回复风格简洁"这类偏好每次都应生效
- `facts` 通过语义搜索检索，只注入与当前问题相关的记忆
- 当记忆较少时（< 5 条），语义搜索结果与全量加载效果接近；当记忆增长到几十条以上时，语义检索的优势会显现

---

## RAG 知识库

基于 ChromaDB 向量数据库的文档检索增强生成系统。

### 入库流程

```
文档输入
  │
  ├─ 文件 (.txt/.md/.pdf/.docx) → loader.py 加载
  ├─ URL                       → loader.py 抓取
  └─ 纯文本                    → 直接使用
  │
  ▼
splitter.py 文本分割
  │  chunk_size=500, overlap=50
  │  中文友好分隔符: \n\n → \n → 。！？ → .!? → 空格
  ▼
embedder.py 向量化
  │  BAAI/bge-base-zh-v1.5 (768维)
  │  单例模式，双重检查锁
  │  normalize_embeddings=True
  ▼
ChromaDB "knowledge" 集合
  │  cosine 距度量
  │  持久化存储到 data/chroma
```

### 检索流程

```
用户查询
  → embed_query(query) → 768 维向量
  → ChromaDB query(top_k=3, cosine)
  → 返回最相关的 3 个文档片段
  → 格式化为 "[1] 来源: xxx\n内容..."
  → 注入系统提示词
```

### 检索触发方式

- **Agent 自主调用**：`knowledge_search` 封装为 LangChain `@tool`，LLM 通过 Function Calling 自主决定是否检索
- **预处理阶段**：`_get_rag_context()` 在对话开始前自动检索，结果注入系统提示词

---

## 工具系统

内置 14 个工具，LLM 根据任务自主决策调用。

| 工具 | 函数名 | 说明 |
|------|--------|------|
| 网络搜索 | `web_search` | DuckDuckGo 搜索 |
| 维基百科 | `wikipedia_query` | Wikipedia 查询 |
| 网页抓取 | `web_scraper` | 抓取网页正文 |
| 计算器 | `calculator` | 数学表达式计算 |
| 日期时间 | `get_datetime` | 获取当前日期时间 |
| 读文件 | `read_file` | 读取文件内容 |
| 写文件 | `write_file` | 写入文件内容 |
| 列目录 | `list_files` | 列出目录文件 |
| Shell | `run_shell` | 执行 Shell 命令 |
| Python | `python_repl` | 执行 Python 代码 |
| JSON | `json_parse` | JSON 解析与查询 |
| CSV | `csv_query` | CSV 数据查询 |
| HTTP | `http_request` | HTTP 请求 |
| URL 入库 | `url_to_knowledge` | 抓取 URL 内容存入知识库 |

### 工具注册中心

通过 `ToolRegistry` 统一管理（`tools/registry.py`）：

```python
tool_registry.register(tool)    # 注册
tool_registry.disable("shell")  # 禁用（LLM 将看不到）
tool_registry.enable("shell")   # 重新启用
tool_registry.get_all()         # 获取所有已启用工具
```

所有工具使用 LangChain 的 `@tool` 装饰器定义，自动转换为 `BaseTool` 对象。

---

## 情绪分析

实时分析用户情绪，动态调整 Agent 回复风格。

### 流程

```
用户消息
  → analyze_emotion(llm, message)
    → EMOTION_PROMPT 填充用户消息
    → LLM 返回情绪标签
    → 验证标签有效性
  → 情绪标签 (happy/sad/angry/anxious/confused/neutral/excited)
  → build_emotion_context(emotion)
    → 查表 EMOTION_STYLES → 风格指令
  → 注入系统提示词末尾
```

### 情绪 → 风格映射

| 情绪 | 回复风格 |
|------|---------|
| happy | 积极、轻松，表达认同和赞赏 |
| sad | 温和、共情，表达理解和支持 |
| angry | 冷静、理性，承认问题并提供方案 |
| anxious | 耐心、确定，提供清晰信息和步骤 |
| confused | 简单、逐步引导，避免复杂表述 |
| neutral | 专业、清晰（默认） |
| excited | 同频、积极，支持用户想法 |

---

## 技能系统

技能（Skill）是 Markdown 格式的行为规范文档，用于指导 Agent 在特定场景下的行为。

### 与工具的区别

- **工具**：单个原子操作（如搜索、计算），是可执行代码
- **技能**：Markdown 规范文档（如研究助手规范），是"给 AI 写的 SOP"

### 内置技能

| 技能 | 文件 | 说明 |
|------|------|------|
| research | `skills/builtin/research.md` | 研究助手 |
| coding | `skills/builtin/coding.md` | 编程助手 |
| data_analyst | `skills/builtin/data_analyst.md` | 数据分析 |
| writer | `skills/builtin/writer.md` | 写作助手 |

### 技能生命周期

```
用户描述需求 → SKILL_GENERATION_PROMPT → LLM 生成 Markdown
  → generator.py 解析 → Skill 数据类
  → 注册到 SkillRegistry
  → 持久化到 skills/store/{name}.md
  → 下次 build_agent() 时自动加载
```

### 技能注册中心

通过 `SkillRegistry` 管理（`skills/registry.py`）：

```python
skill_registry.register(skill)  # 注册
skill_registry.get("research")  # 获取
skill_registry.list_all()       # 列出所有
skill_registry.remove("research")  # 删除
```

---

## TTS 语音合成

### 架构

```
TTSEngine (抽象基类)
  ├── MiMoTTSEngine   主选，MiMo API（OpenAI 兼容）
  └── EdgeTTSEngine   备选，微软 Neural 引擎（免费）
```

- **统一接口**：`synthesize(text, voice) -> bytes`（MP3 格式）
- **策略**：主引擎失败时自动降级到备选引擎
- **默认语音**：Edge-TTS 使用 `zh-CN-XiaoxiaoNeural`

---

## MCP 协议集成

通过 `langchain-mcp-adapters` 支持 Model Context Protocol，可连接外部工具服务器扩展 Agent 能力。

### 配置

`mcp_servers/config.json`：

```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
    "transport": "stdio"
  }
}
```

### 支持的传输方式

| 传输方式 | 说明 |
|---------|------|
| `stdio` | 本地子进程（如 npx 启动的 MCP 服务器） |
| `streamable_http` | 远程 HTTP 服务 |
| `sse` | Server-Sent Events（旧版兼容） |

MCP 工具在 `graph.py` 的 `build_agent()` 中加载，与内置工具合并后传给 `create_react_agent`。

---

## 项目结构

```
src/agent/
├── main.py           # 入口：chat / chat_stream / CLI
├── config.py         # 配置管理（pydantic-settings，读 .env）
├── graph.py          # Agent 构建（create_react_agent）
├── nodes.py          # 图节点（emotion/rag/memory/think）
├── state.py          # AgentState 类型定义
├── prompts.py        # System Prompt 模板
│
├── memory/           # 双层记忆系统
│   ├── short_term.py # 短期记忆（LangGraph Checkpointer）
│   ├── long_term.py  # 长期记忆（SQLite + ChromaDB 双写）
│   └── manager.py    # 记忆管理器（统一接口 + 格式化）
│
├── rag/              # RAG 知识库引擎
│   ├── embedder.py   # 嵌入模型（bge-base-zh-v1.5，单例）
│   ├── retriever.py  # 向量检索（@tool knowledge_search）
│   ├── ingest.py     # 文档入库（文本/文件/URL）
│   ├── splitter.py   # 文本分割（中文友好）
│   └── loader.py     # 文档加载（PDF/Word/MD/TXT/URL）
│
├── tools/            # 工具中心（14 个内置工具）
│   ├── registry.py   # 工具注册中心
│   ├── search.py     # DuckDuckGo 搜索
│   ├── calculator.py # 计算器
│   ├── file_ops.py   # 文件操作
│   ├── shell.py      # Shell 命令
│   ├── python_repl.py# Python 执行
│   └── ...           # 其他工具
│
├── emotion/          # 情绪分析
│   ├── analyzer.py   # 情绪分析器（LLM 结构化输出）
│   └── feedback.py   # 情绪→风格映射
│
├── skills/           # 技能系统
│   ├── registry.py   # 技能注册中心
│   ├── generator.py  # LLM 自动生成技能
│   ├── executor.py   # 技能执行器
│   ├── builtin/      # 内置技能（.md 文件）
│   └── store/        # 用户生成技能（持久化）
│
├── tts/              # TTS 语音合成
│   ├── engine.py     # TTSEngine 抽象基类
│   ├── mimo_tts.py   # MiMo TTS 实现
│   └── edge_tts.py   # Edge-TTS 实现
│
└── mcp/              # MCP 协议支持
    └── client.py     # MCP 客户端（MultiServerMCPClient）
```

---

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

# 向量库（ChromaDB 持久化目录，知识库和用户记忆共用）
CHROMA_PERSIST_DIR=./data/chroma

# 嵌入模型
EMBEDDING_MODEL=BAAI/bge-base-zh-v1.5

# 记忆
SHORT_TERM_DB=./data/memory.db
LONG_TERM_DB=./data/long_term.db

# MCP
MCP_CONFIG_PATH=./mcp_servers/config.json
```

---

## 开发命令

```bash
python -m agent.main    # 交互式测试
pytest                  # 运行测试
ruff check src/         # 代码检查
```

---

## 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 长期记忆存储 | SQLite 作为权威存储 | ACID 事务保证，无外部依赖，简单可靠 |
| 记忆向量检索 | ChromaDB `user_memory` 集合 | 复用已有的 ChromaDB 基础设施，无需引入新依赖 |
| 记忆双写 | SQLite + ChromaDB 同步写入 | ChromaDB 故障时 SQLite 仍可用，系统优雅降级 |
| 记忆 ID | `{user_id}_{namespace}_{key}` | 确定性 ID，支持 upsert，无需查询即可防重复 |
| 偏好始终注入 | preferences 命名空间绕过语义搜索 | "回复风格简洁"这类偏好每次都应生效 |
| Agent 架构 | `create_react_agent` 预构建 | 简单直接，nodes.py 中的独立节点可用于更复杂的图拓扑 |
| 嵌入模型 | bge-base-zh-v1.5 本地运行 | 中文质量优秀，无 API 成本，数据隐私 |
| 距离度量 | cosine | bge 模型输出归一化向量，cosine 是标准选择 |
