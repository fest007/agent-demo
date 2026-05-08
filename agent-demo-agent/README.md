# Agent Demo - Agent 核心层

基于 LangGraph 的智能代理系统核心层，集成 LLM 对话、RAG 知识库、工具调用、向量化记忆系统、情绪分析、TTS 语音、技能系统和 MCP 协议。

这是一个练手项目，文档力求详细，适合学习 LangGraph Agent 的完整开发流程。

## 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| **Agent 框架** | LangGraph | LangChain 官方 Agent 编排框架，基于有向图的状态机 |
| **LLM** | 小米 MiMo v2.5-pro | OpenAI 兼容 API，通过 `langchain-openai` 调用 |
| **向量数据库** | ChromaDB | 知识库（`knowledge` 集合）+ 用户记忆（`user_memory` 集合） |
| **嵌入模型** | BAAI/bge-base-zh-v1.5 | 768 维中文向量，本地运行，约 400MB |
| **短期记忆** | LangGraph Checkpointer + SQLite | 会话级对话历史，按 thread_id 隔离 |
| **长期记忆** | SQLite + ChromaDB 双写 | 权威存储 SQLite，语义检索 ChromaDB |
| **TTS** | MiMo TTS（主）+ Edge-TTS（备） | 统一 TTSEngine 抽象接口 |
| **MCP** | langchain-mcp-adapters | 支持 stdio / streamable_http / sse 传输 |
| **Python** | >= 3.11 | 使用 `uv` 管理依赖 |

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

### 三层系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          前端 (Web)                                  │
│  React 19 + TypeScript + Ant Design + Zustand                       │
│  - 对话界面（SSE 流式展示）                                            │
│  - 知识库管理 / 技能管理 / 工具管理 / 设置                               │
│  - 3000 端口，Vite 开发服务器                                         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP / SSE
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          后端 (Server)                               │
│  FastAPI + SQLAlchemy + aiosqlite                                    │
│  - /api/chat（同步 + SSE 流式）                                       │
│  - /api/sessions, /api/knowledge, /api/skills, /api/tools, /api/tts │
│  - 用户认证（JWT）/ 会话管理 / 对话持久化                                │
│  - 8000 端口                                                         │
│  - 通过 import agent.main.chat 调用 Agent 核心层                      │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ Python import
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Agent 核心层 (本项目)                          │
│  LangGraph + LangChain                                              │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ memory/  │  │  rag/    │  │ emotion/ │  │  tools/  │            │
│  │ 双层记忆  │  │ RAG知识库│  │ 情绪分析  │  │ 工具中心  │            │
│  │          │  │          │  │          │  │  14个工具  │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                           │
│  │ skills/  │  │  tts/    │  │  mcp/    │                           │
│  │ 技能系统  │  │ 语音合成  │  │ MCP协议   │                           │
│  └──────────┘  └──────────┘  └──────────┘                           │
│                                                                      │
│  main.py    ← 入口，提供 chat() / chat_stream() 函数                 │
│  graph.py   ← LangGraph StateGraph 定义与编译                        │
│  state.py   ← AgentState 状态定义                                    │
│  prompts.py ← System Prompt 模板                                     │
│  config.py  ← 配置管理（pydantic-settings）                          │
└─────────────────────────────────────────────────────────────────────┘
```

### 数据存储一览

| 存储 | 技术 | 路径 | 用途 |
|------|------|------|------|
| 短期记忆 | SQLite (AsyncSqliteSaver) | `data/memory.db` | 会话级对话历史，按 thread_id 隔离 |
| 长期记忆（权威） | SQLite | `data/long_term.db` | 用户偏好/事实的 CRUD 存储 |
| 长期记忆（向量） | ChromaDB `user_memory` | `data/chroma` | 用户记忆的语义检索 |
| 知识库 | ChromaDB `knowledge` | `data/chroma` | RAG 文档的语义检索 |
| 服务端对话记录 | SQLAlchemy + SQLite | `data/server.db` | 对话历史持久化（服务层） |

注意：ChromaDB 的 `user_memory` 和 `knowledge` 两个集合共享同一个持久化目录 `data/chroma`，但数据互不干扰。

---

## 核心执行流程

这是整个系统最核心的部分。用户发送一条消息后，Agent 内部发生了什么？

### 流程总览

```
用户消息 "帮我写个项目方案"
    │
    │  ┌───────────── 阶段 1: 并行预处理 ─────────────┐
    │  │  三个任务同时执行 (asyncio.gather)              │
    │  │                                               │
    ├──→  analyze_emotion(llm, message)  → "neutral"   │
    ├──→  _get_rag_context(message)      → RAG 内容    │
    └──→  _get_memory_context(msg, uid)  → 记忆上下文   │
    │  └──────────────────────────────────────────────┘
    │
    │  ┌───────────── 阶段 2: 组装系统提示词 ──────────┐
    │  │  _build_system_prompt(rag, memory, emotion)   │
    │  │  将所有上下文注入 SYSTEM_PROMPT 模板             │
    │  └──────────────────────────────────────────────┘
    │
    │  ┌───────────── 阶段 3: Agent ReAct 循环 ────────┐
    │  │  create_react_agent 内部:                      │
    │  │                                               │
    │  │  SystemMessage + HumanMessage                  │
    │  │       │                                       │
    │  │       ▼                                       │
    │  │  LLM 推理 → 返回 tool_calls？                  │
    │  │    ├─ 是 → 执行工具 → 结果作为 ToolMessage      │
    │  │    │       → 将结果反馈给 LLM → 再次推理        │
    │  │    └─ 否 → 返回最终文本回复                     │
    │  │                                               │
    │  │  (循环直到 LLM 不再调用工具)                     │
    │  └──────────────────────────────────────────────┘
    │
    ▼
    返回 {content, emotion, thread_id}
```

### 三个文件各自负责什么

| 文件 | 职责 | 在哪个阶段生效 |
|------|------|--------------|
| `main.py` | **入口**：接收用户消息，并行获取上下文，组装提示词，调用 Agent，返回结果 | 阶段 1 + 2 + 3 的编排 |
| `graph.py` | **图构建**：创建 `create_react_agent` 实例，注册工具，设置 checkpointer | 阶段 3 的基础设施 |
| `state.py` | **状态定义**：定义 `AgentState` 的字段结构 | 阶段 3 的数据载体 |
| `prompts.py` | **提示词模板**：`SYSTEM_PROMPT`、`EMOTION_PROMPT`、`SKILL_GENERATION_PROMPT` | 阶段 2 的模板来源 |

### `main.py` 逐函数解析

#### `chat(message, thread_id, user_id)` — 同步对话入口

这是最核心的函数，完整走一遍上述三个阶段：

```python
async def chat(message, thread_id, user_id):
    # 1. 创建 LLM
    llm = ChatOpenAI(model=..., api_key=..., base_url=..., temperature=0.7)

    # 2. 并行获取三个上下文
    emotion, rag_context, memory_context = await asyncio.gather(
        analyze_emotion(llm, message),           # 情绪分析（调 LLM）
        asyncio.to_thread(_get_rag_context, message),      # RAG 检索（ChromaDB，放线程池）
        asyncio.to_thread(_get_memory_context, message, user_id),  # 记忆检索（SQLite+ChromaDB，放线程池）
    )

    # 3. 组装系统提示词
    system_content = _build_system_prompt(rag_context, memory_context, emotion)

    # 4. 获取短期记忆 checkpointer
    checkpointer = await get_checkpointer()

    # 5. 构建 Agent
    agent = await build_agent(llm, checkpointer=checkpointer)

    # 6. 调用 Agent（传入 thread_id，checkpointer 自动加载历史）
    result = await agent.ainvoke(
        {"messages": [SystemMessage(content=system_content), ("human", message)]},
        config={"configurable": {"thread_id": thread_id}},
    )

    # 7. 返回结果
    return {"content": result["messages"][-1].content, "emotion": emotion, "thread_id": thread_id}
```

#### `chat_stream(message, thread_id, user_id)` — 流式对话入口

与 `chat()` 流程完全相同，区别在于：
- 使用 `agent.astream_events(..., version="v2")` 逐 token 返回
- 通过 `yield` 返回事件流，前端可以实时展示打字效果
- 事件类型：`emotion`（情绪标签）→ `token`（逐字输出）→ `tool_start`/`tool_end`（工具调用）→ `done`

#### `_get_memory_context(query, user_id)` — 记忆检索

采用混合检索策略：
1. **语义搜索**：将 query 向量化，在 ChromaDB `user_memory` 集合中找 top-5 最相关记忆
2. **核心偏好**：从 SQLite 加载所有 `preferences` 命名空间的记忆（始终注入，不按相关性过滤）
3. 两者去重合并后格式化为文本

#### `_get_rag_context(query)` — RAG 知识库检索

调用 `knowledge_search` 工具（ChromaDB 向量检索），返回 top-3 相关文档片段。

#### `_build_system_prompt(rag, memory, emotion)` — 提示词组装

将所有上下文注入 `SYSTEM_PROMPT` 模板的占位符：
```python
system_content = SYSTEM_PROMPT.format(
    rag_context=rag_context,
    memory_context=memory_context,
    skill_context="",
)
system_content += build_emotion_context(emotion)  # 追加情绪风格指令
```

### `graph.py` 解析

```python
async def build_agent(llm, checkpointer=None, skill_name=None, ...):
    tools = register_all_tools()       # 14 个内置工具
    tools.append(knowledge_search)     # RAG 检索工具
    tools.extend(await load_mcp_tools())  # MCP 外部工具
    _load_all_skills()                 # 加载技能

    agent = create_react_agent(        # LangGraph 预构建的 ReAct Agent
        llm,
        tools,
        checkpointer=checkpointer,     # 短期记忆（自动保存/加载对话历史）
        prompt=SystemMessage(content=system_prompt),
    )
    return agent
```

`create_react_agent` 是 LangGraph 提供的开箱即用 Agent，内部自动实现了：
- LLM 调用 → 解析 tool_calls → 执行工具 → 将结果反馈给 LLM → 循环
- 通过 checkpointer 自动保存/加载对话历史（按 thread_id 隔离）

### `state.py` 解析

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # 消息列表，新消息自动追加
    emotion: str           # 情绪标签 (happy/sad/angry/anxious/confused/neutral/excited)
    tools_used: list[str]  # 本轮使用过的工具名
    active_skill: str | None  # 当前激活的技能
    rag_context: str       # RAG 检索结果
    memory_context: str    # 长期记忆上下文
    should_use_tts: bool   # 是否启用 TTS
```

关键点：`Annotated[list[BaseMessage], add_messages]` 是 LangGraph 的消息追加注解。当节点返回 `{"messages": [new_msg]}` 时，`new_msg` 会自动追加到已有列表，而不是替换。

---

## 记忆系统

### 短期记忆（Session-level）

基于 LangGraph 的 `AsyncSqliteSaver` Checkpointer。

- **存储**：SQLite `data/memory.db`
- **隔离键**：`thread_id`（格式 `{user_id}_{session_id}`）
- **机制**：每次 Agent 执行后自动保存完整消息列表；下次用同一 `thread_id` 执行时自动加载
- **生命周期**：会话级，同一 thread_id 的对话保持上下文

```
Round 1: "你好" → Agent 回复 → 自动保存 [user_msg, ai_msg] 到 memory.db
Round 2: "帮我写代码" → 自动加载 history → Agent 看到完整上下文 → 回复 → 保存
```

### 长期记忆（Cross-session）

跨会话持久化的用户信息，采用 **SQLite + ChromaDB 双写架构**。

#### 为什么需要双写？

- **SQLite**：权威存储，支持精确的 CRUD 操作（按 user_id + namespace + key 唯一约束）
- **ChromaDB**：向量检索，根据用户当前提问语义搜索相关记忆

单靠 SQLite 只能全量加载记忆（记多了浪费 token），单靠 ChromaDB 无法保证精确的 key-value 操作。双写兼得两者优势。

#### SQLite 表结构（权威存储）

```sql
CREATE TABLE memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,      -- 用户标识
    namespace   TEXT NOT NULL,      -- 记忆分类: facts / preferences
    key         TEXT NOT NULL,      -- 记忆键: 如 "公司名称"
    value       TEXT NOT NULL,      -- 记忆值: 如 "XX科技"
    created_at  TEXT NOT NULL,      -- 创建时间
    updated_at  TEXT NOT NULL,      -- 更新时间
    UNIQUE(user_id, namespace, key) -- 同一用户下 key 唯一
)
```

#### ChromaDB 集合设计（向量检索）

```
集合名: user_memory
距离度量: cosine
文档 ID: "{user_id}_{namespace}_{key}"  (确定性 ID，支持 upsert)
文档文本: "{key}: {value}"              (用于生成嵌入向量)
元数据:  {user_id, namespace, key, value}
```

#### 写入流程（双写）

```python
manager.save_fact("公司名称", "XX科技")
  │
  ├── SQLite: INSERT OR REPLACE INTO memories ...
  │
  └── ChromaDB: collection.upsert(
          id="default_facts_公司名称",
          document="公司名称: XX科技",
          embedding=bge-base-zh("公司名称: XX科技"),
          metadata={user_id, namespace, key, value}
      )
```

ChromaDB 写入失败时 try/except 降级，不影响 SQLite 主路径。

#### 检索流程（混合检索）

```python
memory_context = _get_memory_context("帮我写个项目方案", "default")
  │
  ├── 语义搜索 (ChromaDB)
  │   embed("帮我写个项目方案") → 向量
  │   collection.query(where={user_id: "default"}, top_k=5)
  │   → [公司名称=XX科技, 项目背景=AI开发, ...]
  │
  └── 核心偏好 (SQLite)
      SELECT * FROM memories WHERE namespace="preferences"
      → [回复风格=简洁, 语言=中文, ...]
  │
  ▼
  去重合并（偏好优先）→ 格式化文本 → 注入系统提示词
```

**设计决策**：
- `preferences` 始终注入（"回复风格简洁"这类偏好每次都应生效）
- `facts` 通过语义搜索（只注入与当前问题相关的记忆）
- 记忆少时效果接近全量加载；记忆多时（几十条以上）语义检索优势明显

---

## RAG 知识库

基于 ChromaDB 向量数据库的文档检索增强生成系统。

### 入库流程

```
文档输入
  ├─ 文件 (.txt/.md/.pdf/.docx) → loader.py → list[Document]
  ├─ URL                       → loader.py (httpx + BeautifulSoup) → list[Document]
  └─ 纯文本                    → 直接使用
  │
  ▼
splitter.py RecursiveCharacterTextSplitter
  │  chunk_size=500, overlap=50
  │  中文友好分隔符: \n\n → \n → 。！？ → .!? → 空格
  ▼
embedder.py bge-base-zh-v1.5
  │  768 维向量，normalize_embeddings=True
  │  单例模式（双重检查锁），CPU 推理
  ▼
ChromaDB "knowledge" 集合
  │  cosine 距离，持久化到 data/chroma
  │  collection.add(documents, metadatas, ids, embeddings)
```

### 检索流程

```
用户查询 "什么是 RAG"
  → embed_query("什么是 RAG") → 768 维向量
  → ChromaDB collection.query(top_k=3, cosine)
  → 返回最相关的 3 个文档片段 + 来源元数据
  → 格式化为 "[1] 来源: xxx\n内容..."
  → 注入系统提示词的 {rag_context} 占位符
```

### 检索触发方式

| 方式 | 入口 | 说明 |
|------|------|------|
| **预处理阶段** | `_get_rag_context()` in main.py | 每次对话开始前自动检索，结果注入系统提示词 |
| **Agent 自主调用** | `knowledge_search` @tool | LLM 通过 Function Calling 自主决定是否需要检索 |

两种方式同时存在：预处理确保 LLM 一定有知识库上下文；Agent 自主调用允许 LLM 在对话中途主动检索。

---

## 工具系统

内置 14 个工具，LLM 根据任务自主决策调用。

| 工具 | 函数名 | 说明 | 实现文件 |
|------|--------|------|---------|
| 网络搜索 | `web_search` | DuckDuckGo 搜索 | `tools/search.py` |
| 维基百科 | `wikipedia_query` | Wikipedia 查询 | `tools/wikipedia.py` |
| 网页抓取 | `web_scraper` | 抓取网页正文（BeautifulSoup） | `tools/web_scraper.py` |
| 计算器 | `calculator` | 数学表达式计算（eval 安全沙箱） | `tools/calculator.py` |
| 日期时间 | `get_datetime` | 获取当前日期时间 | `tools/datetime_tool.py` |
| 读文件 | `read_file` | 读取文件内容 | `tools/file_ops.py` |
| 写文件 | `write_file` | 写入文件内容 | `tools/file_ops.py` |
| 列目录 | `list_files` | 列出目录文件 | `tools/file_ops.py` |
| Shell | `run_shell` | 执行 Shell 命令 | `tools/shell.py` |
| Python | `python_repl` | 执行 Python 代码 | `tools/python_repl.py` |
| JSON | `json_parse` | JSON 解析与查询 | `tools/json_tool.py` |
| CSV | `csv_query` | CSV 数据查询 | `tools/csv_tool.py` |
| HTTP | `http_request` | HTTP 请求 | `tools/http_tool.py` |
| URL 入库 | `url_to_knowledge` | 抓取 URL 内容存入知识库 | `tools/url_to_knowledge.py` |

### 工具注册中心 (`tools/registry.py`)

```python
class ToolRegistry:
    _tools: dict[str, BaseTool]     # 已注册的工具
    _disabled: set[str]             # 被禁用的工具名

    def register(tool)      # 注册
    def get_all()           # 获取所有已启用工具
    def get(name)           # 按名获取
    def enable(name)        # 启用
    def disable(name)       # 禁用（LLM 将看不到）
    def list_status()       # 列出所有工具的启用状态
```

所有工具使用 LangChain 的 `@tool` 装饰器定义，自动转换为 `BaseTool` 对象，支持 Function Calling。

---

## 情绪分析

实时分析用户情绪，动态调整 Agent 回复风格。

### 完整流程

```
用户消息 "这个 bug 气死我了"
    │
    ▼
analyze_emotion(llm, message)
    │  填充 EMOTION_PROMPT 模板:
    │  "分析以下用户消息的情绪状态，只返回一个情绪标签词..."
    │
    ▼
LLM 返回 "angry"
    │  验证: "angry" ∈ VALID_EMOTIONS? → 是
    ▼
情绪标签: "angry"
    │
    ▼
build_emotion_context("angry")
    │  查表 EMOTION_STYLES:
    │  "angry" → "用冷静、理性的语气回应，承认问题并提供解决方案。"
    ▼
注入系统提示词末尾:
    "\n当前用户情绪: angry。用冷静、理性的语气回应，承认问题并提供解决方案。"
```

### 情绪 → 风格映射表

| 情绪标签 | 中文含义 | 回复风格指令 |
|---------|---------|------------|
| happy | 开心 | 用积极、轻松的语气回应，适当表达认同和赞赏 |
| sad | 难过 | 用温和、共情的语气回应，表达理解和支持 |
| angry | 生气 | 用冷静、理性的语气回应，承认问题并提供解决方案 |
| anxious | 焦虑 | 用耐心、确定的语气回应，提供清晰的信息和步骤 |
| confused | 困惑 | 用简单、逐步引导的方式回应，避免复杂表述 |
| neutral | 平静（默认） | 用专业、清晰的语气回应 |
| excited | 兴奋 | 用同频、积极的语气回应，支持用户的想法 |

---

## 技能系统

技能（Skill）是 Markdown 格式的行为规范文档，用于指导 Agent 在特定场景下的行为。

### 工具 vs 技能

| | 工具 (Tool) | 技能 (Skill) |
|---|---|---|
| **本质** | 可执行代码（Python 函数） | Markdown 规范文档 |
| **作用** | 单个原子操作（搜索、计算、文件读写） | 指导 Agent 的行为模式（"给 AI 写的 SOP"） |
| **调用方式** | LLM 通过 Function Calling 调用 | 注入系统提示词，影响 Agent 整体行为 |
| **示例** | `calculator("1+1")` | "你是研究助手，回答要引用来源" |

### 内置技能

| 技能 | 文件 | 说明 |
|------|------|------|
| research | `skills/builtin/research.md` | 研究助手：强调引用来源、多角度分析 |
| coding | `skills/builtin/coding.md` | 编程助手：强调代码质量、测试、文档 |
| data_analyst | `skills/builtin/data_analyst.md` | 数据分析：强调数据可视化、统计方法 |
| writer | `skills/builtin/writer.md` | 写作助手：强调结构清晰、用词精准 |

### 技能生命周期

```
用户: "帮我创建一个翻译技能"
    │
    ▼
SKILL_GENERATION_PROMPT + 用户描述 → LLM
    │
    ▼
LLM 生成 Markdown 规范文档
    │  包含: # 技能名称、适用场景、核心规则、示例、禁止事项
    ▼
generator.py 解析 → Skill 数据类
    │
    ├── 注册到 SkillRegistry（内存）
    └── 持久化到 skills/store/{name}.md（磁盘）
    │
    ▼
下次 build_agent() 时自动加载到系统提示词
```

---

## TTS 语音合成

### 架构

```
TTSEngine (抽象基类, tts/engine.py)
  │  abstract synthesize(text, voice) -> bytes (MP3)
  │  abstract get_name() -> str
  │
  ├── MiMoTTSEngine (tts/mimo_tts.py)
  │   MiMo API，OpenAI 兼容接口
  │   主选引擎
  │
  └── EdgeTTSEngine (tts/edge_tts.py)
      微软 Neural 引擎，免费
      备选引擎，默认语音 zh-CN-XiaoxiaoNeural
```

- **策略**：主引擎失败时自动降级到备选引擎
- **输出**：MP3 格式的 bytes 数据

---

## MCP 协议集成

通过 `langchain-mcp-adapters` 支持 Model Context Protocol，可连接外部工具服务器扩展 Agent 能力。

### 配置文件 `mcp_servers/config.json`

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

| 传输方式 | 说明 | 典型场景 |
|---------|------|---------|
| `stdio` | 本地子进程 | npx 启动的 MCP 服务器 |
| `streamable_http` | 远程 HTTP 服务 | 云端 MCP 服务 |
| `sse` | Server-Sent Events | 旧版兼容 |

MCP 工具在 `graph.py` 的 `build_agent()` 中加载，与内置工具合并后传给 `create_react_agent`。加载失败不影响核心功能。

---

## 项目结构

```
src/agent/
├── main.py           # 入口：chat() / chat_stream() / CLI
│                     #   - 并行获取情绪+RAG+记忆上下文
│                     #   - 组装系统提示词
│                     #   - 调用 Agent，返回结果
│
├── graph.py          # Agent 构建：build_agent()
│                     #   - 注册工具（内置 + MCP + 知识库检索）
│                     #   - 加载技能
│                     #   - 创建 create_react_agent 实例
│
├── state.py          # AgentState 类型定义
│                     #   - messages, emotion, rag_context, memory_context 等
│
├── prompts.py        # 提示词模板
│                     #   - SYSTEM_PROMPT: Agent 人设（含 {memory_context} {rag_context} {skill_context} 占位符）
│                     #   - EMOTION_PROMPT: 情绪分析提示词
│                     #   - SKILL_GENERATION_PROMPT: 技能生成提示词
│
├── config.py         # 配置管理（pydantic-settings，读 .env）
│
├── memory/           # 双层记忆系统
│   ├── short_term.py # 短期记忆：AsyncSqliteSaver，按 thread_id 隔离
│   ├── long_term.py  # 长期记忆：SQLite CRUD + ChromaDB 向量同步
│   └── manager.py    # 记忆管理器：统一接口 + search_with_core + 格式化
│
├── rag/              # RAG 知识库引擎
│   ├── embedder.py   # 嵌入模型：bge-base-zh-v1.5 单例
│   ├── retriever.py  # 向量检索：knowledge_search @tool
│   ├── ingest.py     # 文档入库：text/file/URL → ChromaDB
│   ├── splitter.py   # 文本分割：RecursiveCharacterTextSplitter
│   └── loader.py     # 文档加载：PDF/Word/MD/TXT/URL
│
├── tools/            # 工具中心（14 个内置工具）
│   ├── registry.py   # ToolRegistry：注册/启用/禁用/查询
│   ├── search.py     # DuckDuckGo 搜索
│   ├── calculator.py # 数学计算
│   ├── file_ops.py   # 文件操作（read/write/list）
│   ├── shell.py      # Shell 命令执行
│   ├── python_repl.py# Python REPL
│   ├── json_tool.py  # JSON 解析
│   ├── csv_tool.py   # CSV 查询
│   ├── http_tool.py  # HTTP 请求
│   ├── web_scraper.py# 网页抓取
│   ├── wikipedia.py  # Wikipedia 查询
│   ├── datetime_tool.py # 日期时间
│   └── url_to_knowledge.py # URL 入库
│
├── emotion/          # 情绪分析
│   ├── analyzer.py   # analyze_emotion(): LLM 结构化输出 → 情绪标签
│   └── feedback.py   # EMOTION_STYLES 映射表 + build_emotion_context()
│
├── skills/           # 技能系统
│   ├── registry.py   # SkillRegistry + Skill 数据类
│   ├── generator.py  # LLM 自动生成 Markdown 技能文档
│   ├── executor.py   # 技能执行器
│   ├── builtin/      # 内置技能（.md 文件）
│   │   ├── research.md
│   │   ├── coding.md
│   │   ├── data_analyst.md
│   │   └── writer.md
│   └── store/        # 用户生成技能（持久化目录）
│
├── tts/              # TTS 语音合成
│   ├── engine.py     # TTSEngine 抽象基类
│   ├── mimo_tts.py   # MiMo TTS 实现（主选）
│   └── edge_tts.py   # Edge-TTS 实现（备选）
│
└── mcp/              # MCP 协议支持
    └── client.py     # MultiServerMCPClient，加载外部工具
```

---

## 环境变量

参考 `.env.example`：

```bash
# ===== MiMo API（必填）=====
MIMO_API_KEY=your_api_key_here
MIMO_BASE_URL=https://api.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5-pro         # 主模型
MIMO_MODEL_FAST=mimo-v2-flash    # 快速模型（用于情绪分析等轻量任务）

# ===== TTS =====
TTS_ENGINE=mimo-tts              # 主选: mimo-tts | 备选: edge-tts
TTS_MIMO_MODEL=mimo-v2.5-tts
TTS_FALLBACK_ENGINE=edge-tts
TTS_VOICE=zh-CN-XiaoxiaoNeural   # Edge-TTS 默认语音

# ===== 向量库 =====
CHROMA_PERSIST_DIR=./data/chroma  # ChromaDB 持久化目录（知识库 + 用户记忆共用）

# ===== 嵌入模型 =====
EMBEDDING_MODEL=BAAI/bge-base-zh-v1.5  # 首次运行自动下载，约 400MB

# ===== 记忆 =====
SHORT_TERM_DB=./data/memory.db    # 短期记忆（对话历史）
LONG_TERM_DB=./data/long_term.db  # 长期记忆（用户偏好/事实）

# ===== MCP =====
MCP_CONFIG_PATH=./mcp_servers/config.json
```

---

## 开发命令

```bash
python -m agent.main    # 交互式 CLI 测试
pytest                  # 运行测试
ruff check src/         # 代码检查（Ruff linter）
```

---

## 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 架构 | `create_react_agent` 预构建 | 开箱即用的 ReAct 循环，内置 tool calling + checkpointer，比手动 StateGraph 简单可靠 |
| 长期记忆存储 | SQLite 作为权威存储 | ACID 事务保证，无外部依赖，key-value 操作简单 |
| 记忆向量检索 | ChromaDB `user_memory` 集合 | 复用已有 ChromaDB 基础设施，与知识库共享持久化目录 |
| 记忆双写 | SQLite + ChromaDB 同步写入 | ChromaDB 故障时 SQLite 仍可用，系统优雅降级 |
| 记忆 ID | `{user_id}_{namespace}_{key}` | 确定性 ID，支持 upsert，无需查询即可防重复 |
| 偏好始终注入 | preferences 命名空间绕过语义搜索 | "回复风格简洁"这类偏好每次都应生效 |
| 嵌入模型 | bge-base-zh-v1.5 本地运行 | 中文质量优秀，无 API 成本，数据隐私 |
| 距离度量 | cosine | bge 模型输出归一化向量，cosine 是标准选择 |
| 并行预处理 | `asyncio.gather` | 情绪分析、RAG 检索、记忆检索三者无依赖，并行执行减少延迟 |
| RAG 双触发 | 预处理 + Agent 自主调用 | 预处理确保一定有上下文；自主调用允许 Agent 在对话中途主动检索 |
