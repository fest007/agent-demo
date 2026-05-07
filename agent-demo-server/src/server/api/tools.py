"""
工具管理 API 模块

提供工具的查询和启停接口：
- GET /api/tools/list: 列出所有工具及其启用状态
- PUT /api/tools/{tool_name}/toggle: 启用/禁用工具

禁用的工具不会暴露给 LLM，相当于"软删除"。
"""
from fastapi import APIRouter, Depends
from server.deps import get_current_user, UserContext

router = APIRouter(prefix="/api/tools", tags=["tools"])


def _get_tools():
    """动态导入工具注册中心"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / "agent-demo-agent" / "src"))
    from agent.tools import tool_registry
    return tool_registry


@router.get("/list")
async def list_tools(user: UserContext = Depends(get_current_user)):
    """
    列出所有工具的启用状态

    Returns:
        dict: {工具名: 是否启用}，如 {"web_search": true, "run_shell": false}
    """
    registry = _get_tools()
    return registry.list_status()


@router.put("/{tool_name}/toggle")
async def toggle_tool(
    tool_name: str,
    enable: bool = True,
    user: UserContext = Depends(get_current_user),
):
    """
    启用或禁用指定工具

    Args:
        tool_name: 工具名称
        enable: true=启用, false=禁用

    Returns:
        操作结果
    """
    registry = _get_tools()
    if enable:
        registry.enable(tool_name)
    else:
        registry.disable(tool_name)
    return {"tool": tool_name, "enabled": enable}
