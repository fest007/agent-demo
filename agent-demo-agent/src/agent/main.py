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
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from agent.config import get_settings
from agent.graph import build_agent
from agent.prompts import SYSTEM_PROMPT
from agent.emotion.analyzer import analyze_emotion
from agent.emotion.feedback import build_emotion_context
from agent.rag.retriever import knowledge_search
from agent.memory.manager import MemoryManager
from agent.memory.short_term import get_checkpointer


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
    system_content = SYSTEM_PROMPT.format(
        rag_context=rag_context,
        memory_context=memory_context,
        skill_context="",
    )
    system_content += build_emotion_context(emotion)
    return system_content


def _get_memory_context(user_id: str = "default") -> str:
    """
    从长期记忆中读取用户信息

    长期记忆存储的是跨会话持久化的信息：
    - 用户偏好（如"喜欢简洁回复"）
    - 用户事实（如"公司名叫 XX 科技"）

    这些信息在每次对话时都会注入到系统提示词中，
    让 LLM 能"记住"用户。
    """
    try:
        manager = MemoryManager(user_id=user_id)
        all_memories = manager.get_all_memories()

        if not all_memories:
            return ""

        lines = ["以下是关于这个用户的已知信息，请在回复时参考："]
        for mem in all_memories:
            ns = mem.get("namespace", "")
            key = mem.get("key", "")
            value = mem.get("value", "")
            if ns == "preferences":
                lines.append(f"- 偏好：{key} = {value}")
            elif ns == "facts":
                lines.append(f"- 事实：{key} = {value}")
            else:
                lines.append(f"- {ns}：{key} = {value}")

        return "\n".join(lines)
    except Exception:
        return ""


def _get_rag_context(query: str) -> str:
    """从 RAG 知识库中检索相关内容"""
    try:
        result = knowledge_search.invoke({"query": query})
        if "为空" in result or "未找到" in result:
            return ""
        return f"\n相关知识库内容:\n{result}"
    except Exception:
        return ""


async def chat(message: str, thread_id: str = "default", user_id: str = "default") -> dict:
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
    settings = get_settings()

    llm = ChatOpenAI(
        model=settings.mimo_model,
        api_key=settings.mimo_api_key,
        base_url=settings.mimo_base_url,
        temperature=0.7,
    )

    # 并行获取上下文
    emotion, rag_context, memory_context = await asyncio.gather(
        analyze_emotion(llm, message),
        asyncio.to_thread(_get_rag_context, message),
        asyncio.to_thread(_get_memory_context, user_id),
    )

    # 组装系统提示词（长期记忆 + RAG + 情绪）
    system_content = _build_system_prompt(rag_context, memory_context, emotion)

    # 获取短期记忆 Checkpointer
    checkpointer = await get_checkpointer()

    # 构建 Agent（传入 checkpointer 启用短期记忆）
    agent = await build_agent(llm, checkpointer=checkpointer)

    # 调用 Agent
    # config 中的 thread_id 是短期记忆的关键：
    # - Checkpointer 会自动加载该 thread_id 的历史消息
    # - LLM 能看到之前的对话轮次
    # - 执行完成后自动保存新的状态
    config = {"configurable": {"thread_id": thread_id}}

    result = await agent.ainvoke(
        {
            "messages": [
                SystemMessage(content=system_content),  # 带上下文的系统提示词
                ("human", message),                      # 当前用户消息
            ]
        },
        config=config,  # 关键：传入 thread_id
    )

    last_msg = result["messages"][-1]
    return {
        "content": last_msg.content,
        "emotion": emotion,
        "thread_id": thread_id,
    }


async def chat_stream(message: str, thread_id: str = "default", user_id: str = "default"):
    """
    流式对话函数（生成器）

    与 chat() 类似，但逐 token 返回。
    短期记忆同样生效：Checkpointer 自动加载历史消息。
    """
    settings = get_settings()

    llm = ChatOpenAI(
        model=settings.mimo_model,
        api_key=settings.mimo_api_key,
        base_url=settings.mimo_base_url,
        temperature=0.7,
        streaming=True,
    )

    # 并行获取上下文
    emotion, rag_context, memory_context = await asyncio.gather(
        analyze_emotion(llm, message),
        asyncio.to_thread(_get_rag_context, message),
        asyncio.to_thread(_get_memory_context, user_id),
    )

    yield {"type": "emotion", "data": emotion}

    system_content = _build_system_prompt(rag_context, memory_context, emotion)

    checkpointer = await get_checkpointer()
    agent = await build_agent(llm, checkpointer=checkpointer)

    # 短期记忆：通过 config 传入 thread_id
    config = {"configurable": {"thread_id": thread_id}}

    async for event in agent.astream_events(
        {
            "messages": [
                SystemMessage(content=system_content),
                ("human", message),
            ]
        },
        config=config,  # 关键：传入 thread_id
        version="v2",
    ):
        kind = event.get("event", "")
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                yield {"type": "token", "data": content}
        elif kind == "on_tool_start":
            yield {
                "type": "tool_start",
                "data": {
                    "name": event.get("name", ""),
                    "input": event.get("data", {}).get("input", ""),
                },
            }
        elif kind == "on_tool_end":
            yield {
                "type": "tool_end",
                "data": {"output": str(event.get("data", {}).get("output", ""))[:500]},
            }

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
