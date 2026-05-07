"""
Agent 图构建模块

这个文件负责组装完整的 Agent，包括：
1. 注册所有内置工具
2. 加载 MCP 外部工具
3. 加载内置技能和持久化技能
4. 使用 LangGraph 的 create_react_agent 创建 ReAct Agent

短期记忆（Checkpointer）：
- create_react_agent 的 checkpointer 参数启用自动状态持久化
- 每次执行后自动保存消息历史到 SQLite
- 下次用同一个 thread_id 执行时自动加载历史
"""
from langgraph.prebuilt import create_react_agent
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.messages import SystemMessage
from agent.tools import register_all_tools
from agent.rag.retriever import knowledge_search
from agent.mcp.client import load_mcp_tools
from agent.skills.registry import skill_registry, load_builtin_skills, load_persisted_skills
from agent.prompts import SYSTEM_PROMPT


async def build_agent(
    llm: BaseChatModel,
    checkpointer: BaseCheckpointSaver | None = None,
    skill_name: str | None = None,
    memory_context: str = "",
    rag_context: str = "",
):
    """
    构建完整的 Agent 实例

    Args:
        llm: 大语言模型实例
        checkpointer: 短期记忆存储
        skill_name: 可选，激活的技能名称
        memory_context: 记忆上下文
        rag_context: RAG 检索上下文

    Returns:
        编译好的 LangGraph Agent
    """
    # 注册所有内置工具
    tools = register_all_tools()
    tools.append(knowledge_search)

    # 尝试加载 MCP 外部工具
    try:
        mcp_tools = await load_mcp_tools()
        tools.extend(mcp_tools)
    except Exception:
        pass

    # 加载技能（内置 + 持久化）
    _load_all_skills()

    # 构建系统提示词
    skill_context = ""
    if skill_name:
        skill = skill_registry.get(skill_name)
        if skill:
            skill_context = f"\n\n当前激活技能：{skill.name}\n{skill.content}"

    system_prompt = SYSTEM_PROMPT.format(
        memory_context=memory_context,
        rag_context=rag_context,
        skill_context=skill_context,
    )

    # 创建 ReAct Agent
    agent = create_react_agent(
        llm,
        tools,
        checkpointer=checkpointer,
        prompt=SystemMessage(content=system_prompt),
    )
    return agent


def _load_all_skills():
    """加载所有技能（幂等操作，已加载的不会重复加载）"""
    if not skill_registry.list_all():
        load_builtin_skills()
        load_persisted_skills()
