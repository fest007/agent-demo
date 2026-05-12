"""
记忆管理 API 模块

提供记忆查询接口：
- GET /api/memory/long-term/{user_id}: 查询用户的长期记忆

长期记忆包括：
- facts: 用户告诉我们的事实
- preferences: 用户的偏好
"""
from fastapi import APIRouter, Depends
from server.deps import get_current_user, UserContext
from server.agent_import import ensure_agent_on_path

router = APIRouter(prefix="/api/memory", tags=["memory"])


def _get_memory():
    """动态导入记忆管理器"""
    ensure_agent_on_path()
    from agent.memory.manager import MemoryManager
    return MemoryManager


@router.get("/long-term/{user_id}")
async def get_long_term_memories(
    user_id: str,
    user: UserContext = Depends(get_current_user),
):
    """
    获取用户的长期记忆

    Args:
        user_id: 目标用户 ID

    Returns:
        记忆列表，每项包含 namespace, key, value, updated_at
    """
    MemoryManager = _get_memory()
    manager = MemoryManager(user_id=user_id)
    return manager.get_all_memories()
