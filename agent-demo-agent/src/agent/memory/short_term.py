"""
短期记忆模块

使用 LangGraph 的 Checkpointer 机制实现会话级别的记忆。

工作原理：
- Checkpointer 会在每次 Agent 执行后，自动将当前状态（包括所有消息）保存到 SQLite
- 下次用同一个 thread_id 调用时，自动加载之前的状态
- LLM 就能看到之前的对话历史，实现"记住上下文"

数据流：
  第1轮: 用户: "我叫张三" → Agent: "你好张三" → Checkpointer 保存
  第2轮: 用户: "我叫什么？"
         → Checkpointer 加载第1轮的历史
         → LLM 看到: [用户: "我叫张三", Agent: "你好张三", 用户: "我叫什么？"]
         → Agent: "你叫张三"

隔离机制：
- 不同的 thread_id 对应不同的对话历史
- thread_id 格式: "{user_id}_{session_id}"，如 "default_abc123"
"""
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agent.config import get_settings

# 全局单例，整个应用共用一个 checkpointer
_checkpointer = None
_cm = None  # 保持上下文管理器引用，防止被 GC


async def get_checkpointer() -> AsyncSqliteSaver:
    """
    获取异步 SQLite Checkpointer 单例

    Checkpointer 是 LangGraph 的核心概念：
    - 每次 Agent 执行后，自动保存当前状态到数据库
    - 下次执行时，自动加载上次的状态（包含所有对话历史）
    - 不同的 thread_id 对应不同的对话历史

    Returns:
        AsyncSqliteSaver 实例
    """
    global _checkpointer, _cm
    if _checkpointer is None:
        settings = get_settings()
        # AsyncSqliteSaver.from_conn_string() 返回异步上下文管理器
        # 需要 __aenter__ 获取实际的 saver 实例
        _cm = AsyncSqliteSaver.from_conn_string(settings.short_term_db)
        _checkpointer = await _cm.__aenter__()
    return _checkpointer
