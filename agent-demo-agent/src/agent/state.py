"""
Agent 状态定义

定义了 LangGraph 图在执行过程中传递的状态结构。
每个节点都可以读取和修改这个状态，状态在节点之间流转。
"""
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Agent 的全局状态

    LangGraph 的核心概念：所有节点共享同一个状态对象，
    每个节点返回一个 dict，会自动合并到状态中。

    字段说明：
    - messages: 对话消息列表，使用 add_messages 注解实现消息追加
      （新消息会自动追加到列表末尾，而不是替换）
    - emotion: 当前用户的情绪标签（happy/sad/angry/anxious/confused/neutral/excited）
    - tools_used: 本轮对话中使用过的工具名称列表
    - active_skill: 当前激活的技能名称（如 research/coding/data_analyst/writer）
    - rag_context: RAG 知识库检索到的相关内容，会注入到系统提示词中
    - memory_context: 长期记忆中的用户偏好和事实，会注入到系统提示词中
    - should_use_tts: 是否需要语音合成输出
    """

    # Annotated[list[BaseMessage], add_messages] 表示：
    # 这个字段是消息列表，并且使用 add_messages 函数来合并
    # 当节点返回 {"messages": [new_msg]} 时，new_msg 会追加到已有列表
    messages: Annotated[list[BaseMessage], add_messages]

    # 当前用户情绪，由 emotion_node 分析得出
    emotion: str

    # 本轮使用过的工具，用于统计和展示
    tools_used: list[str]

    # 当前激活的技能，None 表示未使用技能
    active_skill: str | None

    # RAG 检索到的上下文，由 rag_node 注入
    rag_context: str

    # 长期记忆上下文（用户偏好、事实），由 memory_node 注入
    memory_context: str

    # 是否启用 TTS 语音输出
    should_use_tts: bool
