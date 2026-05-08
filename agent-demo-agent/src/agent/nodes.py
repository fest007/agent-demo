"""
图节点模块

定义了 LangGraph 图中的各个处理节点。
每个节点是一个异步函数，接收当前状态，返回状态更新。

节点执行流程：
1. rag_node: 先从知识库检索相关内容
2. emotion_node: 分析用户情绪
3. think_node: LLM 思考并决定是否调用工具
"""
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT
from agent.emotion.analyzer import analyze_emotion
from agent.emotion.feedback import build_emotion_context
from agent.rag.retriever import knowledge_search
from agent.memory.manager import MemoryManager, format_memories_for_prompt


async def think_node(state: AgentState, llm: BaseChatModel, tools: list) -> dict:
    """
    思考节点 - Agent 的核心推理节点

    这个节点做以下事情：
    1. 从状态中获取 RAG 上下文和情绪信息
    2. 组装完整的系统提示词（基础提示 + RAG 上下文 + 情绪风格）
    3. 将系统提示词和对话历史一起发送给 LLM
    4. LLM 会自动决定是直接回答还是调用工具

    Args:
        state: 当前 Agent 状态，包含消息历史、情绪、RAG 上下文等
        llm: 大语言模型实例
        tools: 可用的工具列表

    Returns:
        状态更新：追加 LLM 的响应消息
    """
    # 从状态中取出对话消息历史
    messages = state["messages"]

    # 获取 RAG 知识库检索到的上下文（可能为空字符串）
    rag_context = state.get("rag_context", "")

    # 获取长期记忆上下文（用户偏好、事实）
    memory_context = state.get("memory_context", "")

    # 获取当前用户情绪，用于调整回复风格
    emotion = state.get("emotion", "neutral")
    emotion_ctx = build_emotion_context(emotion)  # 生成情绪风格指令

    # 组装系统提示词：基础提示 + 记忆上下文 + RAG 上下文 + 情绪风格
    system_content = SYSTEM_PROMPT.format(
        rag_context=rag_context,
        memory_context=memory_context,
    ) + emotion_ctx

    # 将系统提示词放在消息列表最前面
    # LangChain 的消息格式：[SystemMessage, HumanMessage, AIMessage, ...]
    full_messages = [SystemMessage(content=system_content)] + messages

    # 将工具绑定到 LLM，这样 LLM 就知道有哪些工具可用
    # bind_tools 会让 LLM 在回复中生成 tool_call 指令
    llm_with_tools = llm.bind_tools(tools)

    # 调用 LLM 进行推理
    response = await llm_with_tools.ainvoke(full_messages)

    # 返回状态更新：将 LLM 的响应追加到消息列表
    return {"messages": [response]}


async def emotion_node(state: AgentState, llm: BaseChatModel) -> dict:
    """
    情绪分析节点

    从对话历史中找到最后一条用户消息，让 LLM 分析其情绪。
    情绪标签会用于调整 Agent 的回复风格。

    Args:
        state: 当前 Agent 状态
        llm: 大语言模型实例

    Returns:
        状态更新：设置 emotion 字段
    """
    # 从消息列表末尾向前搜索，找到最近的一条用户消息
    last_human = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_human = msg
            break

    # 调用情绪分析器（使用 LLM 进行结构化输出）
    if last_human:
        emotion = await analyze_emotion(llm, last_human.content)
    else:
        emotion = "neutral"  # 没有用户消息时默认为平静

    return {"emotion": emotion}


async def rag_node(state: AgentState) -> dict:
    """
    RAG 知识库检索节点

    根据用户的最新消息，在 ChromaDB 向量数据库中检索相关知识。
    检索到的内容会被注入到系统提示词中，增强 LLM 的回答质量。

    Args:
        state: 当前 Agent 状态

    Returns:
        状态更新：设置 rag_context 字段（检索到的内容或空字符串）
    """
    # 找到最近的用户消息作为检索查询
    last_human = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_human = msg
            break

    if not last_human:
        return {"rag_context": ""}

    try:
        # 使用向量相似度检索知识库
        result = knowledge_search.invoke({"query": last_human.content})
        # 如果知识库为空或未找到相关内容，返回空字符串
        if "为空" in result or "未找到" in result:
            return {"rag_context": ""}
        # 将检索到的内容格式化后注入状态
        return {"rag_context": f"\n相关知识库内容:\n{result}"}
    except Exception:
        # 检索失败不影响对话，降级为无 RAG 模式
        return {"rag_context": ""}


async def memory_node(state: AgentState, user_id: str = "default") -> dict:
    """
    长期记忆检索节点

    从长期记忆中语义检索与当前用户消息相关的记忆，
    注入到系统提示词中，让 LLM 能"记住"用户。

    检索策略：
    1. 语义搜索：通过向量相似度找到最相关的记忆（top-5）
    2. 核心偏好：preferences 始终注入（不按相关性过滤）

    Args:
        state: 当前 Agent 状态
        user_id: 用户标识

    Returns:
        状态更新：设置 memory_context 字段
    """
    try:
        # 从消息中提取用户查询（与 rag_node 相同模式）
        last_human = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                last_human = msg
                break

        if not last_human:
            return {"memory_context": ""}

        manager = MemoryManager(user_id=user_id)
        semantic_results, core_results = manager.search_with_core(last_human.content)
        return {"memory_context": format_memories_for_prompt(semantic_results, core_results)}
    except Exception:
        return {"memory_context": ""}
