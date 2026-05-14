"""
Agent 主入口模块

提供两种使用方式：
1. 作为库调用：from agent.main import chat, chat_stream
2. 命令行对话：python -m agent.main

双层记忆系统：
┌─────────────────────────────────────────────────┐
│                  系统提示词                       │
│  ┌───────────────────────────────────────────┐  │
│  │ 基础人设                                   │  │
│  │ 长期记忆（用户偏好、事实）    ← LTM         │  │
│  │ RAG 知识库上下文                           │  │
│  │ 情绪风格指令                               │  │
│  └───────────────────────────────────────────┘  │
│                  +                              │
│  ┌───────────────────────────────────────────┐  │
│  │ 短期记忆（对话历史）        ← STM          │  │
│  │ 由 Checkpointer 自动管理，按 thread_id 隔离│  │
│  │ LLM 自动看到之前的对话轮次                  │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
"""
import asyncio
import re
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from agent.config import get_settings
from agent.graph import build_agent
from agent.model_providers import resolve_model_config
from agent.prompts import SYSTEM_PROMPT
from agent.emotion.analyzer import analyze_emotion
from agent.emotion.feedback import build_emotion_context
from agent.rag.retriever import knowledge_search
from agent.rag.retriever import search_knowledge
from agent.memory.manager import MemoryManager, format_memories_for_prompt
from agent.memory.short_term import get_checkpointer


_GREETING_RE = re.compile(r"^(你好|您好|hello|hi|hey|嗨|哈喽)[!！。.\s]*$", re.IGNORECASE)
_THANKS_RE = re.compile(r"^(谢谢|感谢|thanks|thank you|thx)[!！。.\s]*$", re.IGNORECASE)
_BYE_RE = re.compile(r"^(再见|拜拜|bye|goodbye|see you)[!！。.\s]*$", re.IGNORECASE)
_HOTSPOT_RE = re.compile(r"(今天|今日|最新|热点|热搜|新闻|发生什么事)", re.IGNORECASE)


def _classify_fast_intent(message: str, images: list[str] | None = None) -> str:
    """用轻量规则识别无需 Agent loop 的意图。"""
    if images:
        return "agent"

    text = message.strip()
    lowered = text.lower()
    if _GREETING_RE.match(text):
        return "greeting"
    if _THANKS_RE.match(text):
        return "thanks"
    if _BYE_RE.match(text):
        return "bye"
    if lowered.startswith(("translate ", "translation:")):
        return "direct_llm"
    if text.startswith(("翻译", "请翻译", "帮我翻译")) or "翻译成" in text or "翻译为" in text:
        return "direct_llm"
    return "agent"


async def _get_short_term_messages(thread_id: str, limit: int = 8) -> list:
    """从 LangGraph checkpointer 读取最近会话消息，供轻量模型直连使用。"""
    try:
        checkpointer = await get_checkpointer()
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if not checkpoint_tuple:
            return []
        channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])
        return messages[-limit:]
    except Exception:
        return []


def _direct_llm_messages(
    message: str,
    intent: str,
    memory_context: str = "",
    history_messages: list | None = None,
) -> list:
    """构建绕过工具/记忆/RAG 的直连模型消息。"""
    if intent in {"greeting", "thanks", "bye"}:
        system = (
            "你是一个轻量直达助手。用户当前是简单寒暄、感谢或告别。"
            "请自然、简短地回应，不调用工具，不展开长篇说明。"
        )
    else:
        system = (
            "你是一个轻量直达助手。只完成用户当前这条简单请求，不调用工具，不扩展任务。"
            "如果是翻译，保持原意、语气和格式，直接输出译文；如果用户指定目标语言，严格遵守。"
        )
    if memory_context:
        system += f"\n\n可用的长期记忆:\n{memory_context}"
    return [SystemMessage(content=system), *(history_messages or []), HumanMessage(content=message)]


async def _save_direct_turn(thread_id: str, user_message: str, assistant_message: str) -> None:
    """把轻量直连回复追加进 LangGraph checkpointer，避免简单请求丢失会话上下文。"""
    try:
        checkpointer = await get_checkpointer()
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if checkpoint_tuple:
            checkpoint = checkpoint_tuple.checkpoint
            messages = list(checkpoint.get("channel_values", {}).get("messages", []))
            checkpoint["channel_values"]["messages"] = [
                *messages,
                HumanMessage(content=user_message),
                AIMessage(content=assistant_message),
            ]
            await checkpointer.aput(
                config,
                checkpoint,
                {"source": "direct_llm", "step": len(messages) + 2},
                {},
            )
    except Exception:
        pass


def _build_llm(
    model: str | None = None,
    streaming: bool = False,
    temperature: float = 0.7,
    provider_id: str | None = None,
    api_key_id: str | None = None,
    custom_base_url: str | None = None,
    custom_api_key: str | None = None,
    purpose: str = "chat",
) -> ChatOpenAI:
    settings = get_settings()
    selected_model = (model or "").strip()
    if custom_api_key:
        if not custom_base_url:
            raise ValueError("使用自定义 API Key 时必须提供 Base URL")
        if not selected_model:
            raise ValueError("使用自定义 API Key/Base URL 时必须提供模型 ID 或推理接入点 ID")
        return ChatOpenAI(
            model=selected_model,
            api_key=custom_api_key,
            base_url=custom_base_url,
            temperature=temperature,
            streaming=streaming,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    config = resolve_model_config(
        provider_id=provider_id,
        model_id=model,
        key_id=api_key_id,
        purpose=purpose,
    )
    base_url = (custom_base_url or "").strip() or config.base_url
    return ChatOpenAI(
        model=config.model,
        api_key=config.api_key,
        base_url=base_url,
        temperature=temperature,
        streaming=streaming,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


def _content_to_text(content) -> str:
    """把 LangChain 可能返回的字符串/多模态片段统一成文本。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content or "")


def _build_tool_fallback_answer(user_message: str, tool_results: list[str], error: Exception | None = None) -> str:
    """模型最终生成失败时，用工具结果提取一个可展示的摘要，避免正文空白。"""
    stop_words = {
        "今日热榜", "首页", "日报", "动态", "追踪", "榜中榜", "热文库", "话题", "日历",
        "综合", "科技", "娱乐", "社区", "购物", "财经", "开发", "简报", "更多", "登录",
        "关于我们", "App 下载", "使用指南", "API 开放平台", "网页", "新闻", "贴吧", "知道",
        "音乐", "图片", "视频", "地图", "文库", "帮助", "新闻全文", "新闻标题",
    }
    candidates: list[str] = []
    for result in tool_results:
        text = result
        text = re.sub(r"^工具\s+.+?返回:\s*", "", text, flags=re.S)
        text = text.replace("content='", "").replace('content="', "")
        for raw_line in re.split(r"[\n\r]+", text):
            line = raw_line.strip().strip("'\"")
            line = re.sub(r"\\[a-z]\w*", "", line)
            line = re.sub(r"\s+", " ", line)
            if not line or line in stop_words:
                continue
            if line.isdigit() or line.startswith(("搜索失败:", "链接:", "热搜指数：")):
                continue
            if len(line) < 4 or len(line) > 80:
                continue
            if line not in candidates:
                candidates.append(line)
            if len(candidates) >= 12:
                break
        if len(candidates) >= 12:
            break

    if candidates:
        items = "\n".join(f"{idx}. {item}" for idx, item in enumerate(candidates, 1))
        suffix = "\n\n注：模型最终生成阶段未返回正文，以上为根据工具结果提取的热点摘要。"
        if error:
            suffix += f" 失败原因：{type(error).__name__}。"
        return f"根据当前可获取的工具结果，{user_message} 的相关热点可以先概括为：\n\n{items}{suffix}"

    if error:
        return f"抱歉，这次工具/模型调用未能生成有效正文。失败原因：{type(error).__name__}。"
    return "抱歉，这次没有生成有效正文。请稍后重试，或换一个更具体的问题。"


def _sanitize_error_text(value: str) -> str:
    text = re.sub(r"(sk|ark|tp)-[A-Za-z0-9_-]{12,}", r"\1-***", value or "")
    text = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer ***", text)
    return text[:1200]


def _build_model_error_answer(
    error: Exception,
    model_provider: str | None = None,
    model: str | None = None,
    custom_base_url: str | None = None,
) -> str:
    raw = _sanitize_error_text(str(error) or type(error).__name__)
    lowered = raw.lower()
    reasons: list[str] = []
    is_model_not_open = (
        "modelnotopen" in lowered
        or "not activated the model" in lowered
        or "activate the model service" in lowered
    )
    is_api_not_supported = (
        "does not support this api" in lowered
        or "not support this api" in lowered
        or "unsupported api" in lowered
    )
    if is_model_not_open:
        reasons.append("账号尚未在火山方舟控制台开通该模型服务，请先在 Ark Console 激活该模型，或改用已开通的模型/推理接入点")
    elif is_api_not_supported:
        reasons.append("当前模型不是聊天对话模型，不能调用 OpenAI-compatible Chat Completions；请在设置页选择文本/代码对话模型")
    elif "api key" in lowered or "unauthorized" in lowered or "401" in lowered or "authentication" in lowered:
        reasons.append("API Key 无效、未生效或没有该模型权限")
    if (
        not is_model_not_open
        and not is_api_not_supported
        and ("model" in lowered or "endpoint" in lowered or "404" in lowered or "not found" in lowered)
    ):
        reasons.append("模型 ID / 火山方舟推理接入点 ID 可能填写错误")
    if not is_model_not_open and not is_api_not_supported and ("base url" in lowered or "connection" in lowered or "connect" in lowered):
        reasons.append("Base URL 可能不是 OpenAI-compatible Chat Completions 地址")
    if not is_model_not_open and not is_api_not_supported and ("quota" in lowered or "insufficient" in lowered or "429" in lowered or "rate" in lowered):
        reasons.append("额度不足、限流或并发限制")
    if not model:
        reasons.append("当前设置未提供模型 ID / 推理接入点 ID")
    if not reasons:
        reasons.append("模型服务返回了异常，需检查供应商配置和服务端日志")

    return (
        "模型调用失败，当前回答无法生成。\n\n"
        f"- 供应商：{model_provider or '默认供应商'}\n"
        f"- 模型/推理接入点：{model or '未填写'}\n"
        f"- Base URL：{custom_base_url or '使用后端配置'}\n"
        f"- 可能原因：{'；'.join(dict.fromkeys(reasons))}\n"
        f"- 原始错误：{raw}\n\n"
        "请到设置页检查 API Key、Base URL，以及火山方舟的模型 ID 或推理接入点 ID。"
    )


async def _load_hotspot_tool_results(message: str) -> list[str]:
    """实时热点兜底：当模型在调用工具前失败时，直接抓取公开热点页。"""
    if not _HOTSPOT_RE.search(message):
        return []
    try:
        from agent.tools.web_scraper import web_scraper
    except Exception:
        return []

    results: list[str] = []
    for url in ("https://top.baidu.com/board", "https://news.baidu.com"):
        try:
            output = await asyncio.to_thread(web_scraper.invoke, {"url": url})
            if output:
                results.append(f"工具 web_scraper 返回:\n{str(output)[:4000]}")
        except Exception:
            continue
    return results


def _build_system_prompt(
    rag_context: str = "",
    memory_context: str = "",
    emotion: str = "neutral",
) -> str:
    """
    组装完整的系统提示词

    注入内容：
    1. memory_context: 长期记忆（跨会话的用户偏好、事实）
    2. rag_context: RAG 知识库检索结果
    3. emotion_ctx: 情绪风格指令

    注意：短期记忆（对话历史）不在这里注入，
    由 LangGraph Checkpointer 自动管理，LLM 通过消息历史自动看到。
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    system_content = SYSTEM_PROMPT.format(
        rag_context=rag_context,
        memory_context=memory_context,
        skill_context="",
    )
    system_content += (
        f"\n\n当前日期：{current_date}。"
        "当用户询问“今天、今日、最新、热点、新闻”等实时信息时，必须以这个日期为准；"
        "构造搜索关键词时不得使用其他年份。"
    )
    if rag_context:
        system_content += (
            "\n\n引用要求：如果回答使用了知识库内容，请在对应句子后标注 [引用1]、[引用2] 等编号。"
            "编号必须和上方知识库片段编号一致，不要编造不存在的引用。"
        )
    system_content += build_emotion_context(emotion)
    return system_content


def _get_memory_context(query: str, user_id: str = "default") -> str:
    """
    从长期记忆中检索与当前 query 相关的用户信息

    采用混合检索策略：
    1. 语义搜索：通过向量相似度找到与 query 最相关的记忆（top-5）
    2. 核心偏好：preferences 命名空间下的记忆始终注入（不按相关性过滤）

    两者去重合并后注入系统提示词。
    """
    try:
        manager = MemoryManager(user_id=user_id)
        semantic_results, core_results = manager.search_with_core(query)
        return format_memories_for_prompt(semantic_results, core_results)
    except Exception:
        return ""


def _get_rag(query: str) -> tuple[str, list[dict]]:
    """从 RAG 知识库中检索相关内容和引用元数据。"""
    try:
        citations = search_knowledge(query, top_k=3)
        if not citations:
            return "", []
        blocks = []
        for i, item in enumerate(citations, 1):
            blocks.append(
                f"[引用{i}] 来源: {item['source']}\n"
                f"标题: {item.get('title') or item['source']}\n"
                f"片段: {item.get('chunk_index')}\n"
                f"{item['content']}"
            )
        return "\n相关知识库内容:\n" + "\n\n".join(blocks), citations
    except Exception:
        return "", []


def _get_rag_context(query: str) -> str:
    """从 RAG 知识库中检索相关内容"""
    context, _ = _get_rag(query)
    return context


def _select_used_citations(answer: str, citations: list[dict]) -> list[dict]:
    """Only expose citations that the final answer explicitly references."""
    if not answer or not citations:
        return []
    used_indexes = []
    for match in re.finditer(r"\[引用(\d+)\]", answer):
        index = int(match.group(1))
        if 1 <= index <= len(citations) and index not in used_indexes:
            used_indexes.append(index)
    return [citations[index - 1] for index in used_indexes]


async def chat(
    message: str,
    thread_id: str = "default",
    user_id: str = "default",
    images: list[str] | None = None,
    model_provider: str | None = None,
    model: str | None = None,
    api_key_id: str | None = None,
    custom_base_url: str | None = None,
    custom_api_key: str | None = None,
) -> dict:
    """
    同步对话函数

    完整流程：
    1. 创建 LLM 实例
    2. 并行获取：情绪分析 + RAG 检索 + 长期记忆
    3. 组装系统提示词（注入长期记忆 + RAG + 情绪）
    4. 构建 Agent（带短期记忆 Checkpointer）
    5. 调用 Agent，传入 thread_id（短期记忆按此隔离）
    6. Checkpointer 自动加载该 thread_id 的历史消息
    7. LLM 看到：系统提示词 + 历史消息 + 当前消息
    8. 返回结果

    Args:
        message: 用户输入的消息文本
        thread_id: 会话线程 ID（短期记忆隔离键）
        user_id: 用户 ID（长期记忆隔离键）

    Returns:
        dict: {"content": "...", "emotion": "...", "thread_id": "..."}
    """
    fast_intent = _classify_fast_intent(message, images)

    if fast_intent in {"greeting", "thanks", "bye", "direct_llm"}:
        llm = _build_llm(
            model=model,
            temperature=0.4,
            provider_id=model_provider,
            api_key_id=api_key_id,
            custom_base_url=custom_base_url,
            custom_api_key=custom_api_key,
            purpose="fast",
        )
        memory_context, history_messages = await asyncio.gather(
            asyncio.to_thread(_get_memory_context, message, user_id),
            _get_short_term_messages(thread_id),
        )
        result = await llm.ainvoke(
            _direct_llm_messages(message, fast_intent, memory_context, history_messages)
        )
        await _save_direct_turn(thread_id, message, result.content)
        return {
            "content": result.content,
            "emotion": "neutral",
            "thread_id": thread_id,
        }

    llm = _build_llm(
        model=model,
        provider_id=model_provider,
        api_key_id=api_key_id,
        custom_base_url=custom_base_url,
        custom_api_key=custom_api_key,
        purpose="omni" if images else "chat",
    )

    # 并行获取上下文
    emotion, rag_result, memory_context = await asyncio.gather(
        analyze_emotion(llm, message),
        asyncio.to_thread(_get_rag, message),
        asyncio.to_thread(_get_memory_context, message, user_id),
    )
    rag_context, _citations = rag_result

    # 组装系统提示词（长期记忆 + RAG + 情绪）
    system_content = _build_system_prompt(rag_context, memory_context, emotion)

    # 获取短期记忆 Checkpointer
    checkpointer = await get_checkpointer()

    # 构建 Agent（传入 checkpointer 启用短期记忆）
    agent = await build_agent(llm, checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}

    # 构造用户消息：有图片时使用多模态格式
    if images:
        human_content = [{"type": "text", "text": message}]
        for img in images:
            human_content.append({"type": "image_url", "image_url": {"url": img}})
        human_msg = HumanMessage(content=human_content)
    else:
        human_msg = ("human", message)

    result = await agent.ainvoke(
        {
            "messages": [
                SystemMessage(content=system_content),
                human_msg,
            ]
        },
        config=config,
    )

    last_msg = result["messages"][-1]
    return {
        "content": last_msg.content,
        "emotion": emotion,
        "thread_id": thread_id,
    }


async def chat_stream(
    message: str,
    thread_id: str = "default",
    user_id: str = "default",
    images: list[str] | None = None,
    model_provider: str | None = None,
    model: str | None = None,
    api_key_id: str | None = None,
    custom_base_url: str | None = None,
    custom_api_key: str | None = None,
):
    """
    流式对话函数（生成器）

    与 chat() 类似，但逐 token 返回。
    短期记忆同样生效：Checkpointer 自动加载历史消息。
    """
    fast_intent = _classify_fast_intent(message, images)

    if fast_intent in {"greeting", "thanks", "bye", "direct_llm"}:
        llm = _build_llm(
            model=model,
            streaming=True,
            temperature=0.4,
            provider_id=model_provider,
            api_key_id=api_key_id,
            custom_base_url=custom_base_url,
            custom_api_key=custom_api_key,
            purpose="fast",
        )
        yield {"type": "emotion", "data": "neutral"}
        if fast_intent == "direct_llm":
            yield {"type": "thought", "data": "识别为简单翻译/改写任务，读取记忆后使用轻量模型生成。"}
        else:
            yield {"type": "thought", "data": "识别为轻量对话，读取记忆后使用轻量模型生成。"}
        memory_context, history_messages = await asyncio.gather(
            asyncio.to_thread(_get_memory_context, message, user_id),
            _get_short_term_messages(thread_id),
        )
        full_content = ""
        async for chunk in llm.astream(
            _direct_llm_messages(message, fast_intent, memory_context, history_messages)
        ):
            if chunk.content:
                full_content += chunk.content
                yield {"type": "token", "data": chunk.content}
        await _save_direct_turn(thread_id, message, full_content)
        yield {"type": "done", "data": ""}
        return

    llm = _build_llm(
        model=model,
        streaming=True,
        provider_id=model_provider,
        api_key_id=api_key_id,
        custom_base_url=custom_base_url,
        custom_api_key=custom_api_key,
        purpose="omni" if images else "chat",
    )

    yield {"type": "thought", "data": "正在识别情绪、检索知识库和读取长期记忆。"}
    # 并行获取上下文
    try:
        emotion, rag_result, memory_context = await asyncio.gather(
            analyze_emotion(llm, message),
            asyncio.to_thread(_get_rag, message),
            asyncio.to_thread(_get_memory_context, message, user_id),
        )
    except Exception as exc:
        yield {"type": "thought", "data": "模型调用失败，正在展示错误详情。"}
        error_answer = _build_model_error_answer(exc, model_provider, model, custom_base_url)
        yield {"type": "error", "data": {"message": error_answer}}
        yield {"type": "token", "data": error_answer}
        yield {"type": "done", "data": ""}
        return
    rag_context, citations = rag_result

    yield {"type": "emotion", "data": emotion}
    if rag_context:
        yield {"type": "thought", "data": "已检索到候选知识库内容，正在交给模型判断是否采用。"}
    if memory_context:
        yield {"type": "thought", "data": "已读取相关长期记忆，准备进入 Agent 推理。"}

    system_content = _build_system_prompt(rag_context, memory_context, emotion)

    yield {"type": "thought", "data": "正在构建 Agent 执行环境。"}
    checkpointer = await get_checkpointer()
    agent = await build_agent(llm, checkpointer=checkpointer)

    # 短期记忆：通过 config 传入 thread_id
    config = {"configurable": {"thread_id": thread_id}}

    # 构造用户消息：有图片时使用多模态格式
    if images:
        human_content = [{"type": "text", "text": message}]
        for img in images:
            human_content.append({"type": "image_url", "image_url": {"url": img}})
        human_msg = HumanMessage(content=human_content)
    else:
        human_msg = ("human", message)

    yield {"type": "thought", "data": "Agent 已开始生成回复。"}
    streamed_content = ""
    final_content = ""
    tool_results: list[str] = []
    stream_error: Exception | None = None
    try:
        async for event in agent.astream_events(
            {
                "messages": [
                    SystemMessage(content=system_content),
                    human_msg,
                ]
            },
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            if kind == "on_chat_model_stream":
                content = _content_to_text(event["data"]["chunk"].content)
                if content:
                    streamed_content += content
                    yield {"type": "token", "data": content}
            elif kind == "on_chat_model_end":
                output = event.get("data", {}).get("output")
                content = _content_to_text(getattr(output, "content", ""))
                if content:
                    final_content = content
            elif kind in {"on_chain_end", "on_graph_end"}:
                output = event.get("data", {}).get("output")
                if isinstance(output, dict):
                    messages = output.get("messages") or []
                    for item in reversed(messages):
                        if isinstance(item, AIMessage) and item.content:
                            final_content = _content_to_text(item.content)
                            break
            elif kind == "on_tool_start":
                tool_name = event.get("name", "")
                yield {"type": "thought", "data": f"正在调用工具：{tool_name}"}
                yield {
                    "type": "tool_start",
                    "data": {
                        "name": tool_name,
                        "input": event.get("data", {}).get("input", ""),
                    },
                }
            elif kind == "on_tool_end":
                tool_name = event.get("name", "")
                tool_output = str(event.get("data", {}).get("output", ""))
                if tool_output:
                    tool_results.append(f"工具 {tool_name} 返回:\n{tool_output[:4000]}")
                yield {
                    "type": "tool_end",
                    "data": {
                        "name": tool_name,
                        "output": tool_output[:500],
                    },
                }
    except Exception as exc:
        stream_error = exc
        error_answer = _build_model_error_answer(exc, model_provider, model, custom_base_url)
        yield {"type": "thought", "data": "模型调用失败，正在展示错误详情。"}
        yield {"type": "error", "data": {"message": error_answer}}
        if not streamed_content:
            yield {"type": "token", "data": error_answer}
        yield {"type": "done", "data": ""}
        return

    answer_text = final_content or streamed_content

    if not streamed_content and final_content:
        yield {"type": "token", "data": final_content}
        answer_text = final_content
    elif not streamed_content and tool_results:
        yield {"type": "thought", "data": "未捕获到模型正文流，正在根据工具结果生成兜底摘要。"}
        answer_text = _build_tool_fallback_answer(message, tool_results, stream_error)
        yield {"type": "token", "data": answer_text}
    elif not streamed_content:
        answer_text = _build_tool_fallback_answer(message, tool_results, stream_error)
        yield {"type": "token", "data": answer_text}

    used_citations = _select_used_citations(answer_text, citations)
    if used_citations:
        yield {"type": "thought", "data": "回答已引用知识库内容，正在附加引用来源。"}
        for citation in used_citations:
            yield {"type": "citation", "data": citation}

    yield {"type": "done", "data": ""}


def main():
    """
    命令行对话入口

    同一个 thread_id 下的对话会保持上下文。
    输入 quit/exit/q 退出。
    """
    print("智能 Agent 已启动，输入消息开始对话（输入 quit 退出）")
    print("-" * 50)

    # 命令行模式使用固定的 thread_id，保持上下文
    thread_id = "cli_session"

    while True:
        try:
            user_input = input("\n你: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("再见！")
                break
            result = asyncio.run(chat(user_input, thread_id=thread_id))
            print(f"\n[情绪: {result['emotion']}]")
            print(f"Agent: {result['content']}")
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n错误: {e}")


if __name__ == "__main__":
    main()
