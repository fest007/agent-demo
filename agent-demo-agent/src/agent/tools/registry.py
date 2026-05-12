"""
工具注册中心

提供工具的统一管理，支持：
- 注册新工具
- 按名称获取工具
- 启用/禁用工具（不影响已注册的工具，只是控制是否暴露给 LLM）
- 列出所有工具及其状态

使用方式：
    tool_registry.register(my_tool)   # 注册
    tool_registry.disable("my_tool")  # 禁用（LLM 将看不到这个工具）
    tool_registry.enable("my_tool")   # 重新启用
"""
from langchain_core.tools import BaseTool


class ToolRegistry:
    """工具注册中心，管理所有工具的注册、查询和启停"""

    def __init__(self):
        # 存储所有已注册的工具，key 为工具名称，value 为工具对象
        self._tools: dict[str, BaseTool] = {}
        # 存储被禁用的工具名称集合
        self._disabled: set[str] = set()
        self._default_policy_applied = False

    def register(self, tool: BaseTool) -> None:
        """注册一个工具到注册中心"""
        self._tools[tool.name] = tool

    def get_all(self) -> list[BaseTool]:
        """获取所有已启用的工具列表（过滤掉被禁用的）"""
        return [t for name, t in self._tools.items() if name not in self._disabled]

    def get(self, name: str) -> BaseTool | None:
        """按名称获取工具，如果被禁用则返回 None"""
        if name in self._disabled:
            return None
        return self._tools.get(name)

    def enable(self, name: str) -> None:
        """启用一个工具（从禁用集合中移除）"""
        self._disabled.discard(name)

    def disable(self, name: str) -> None:
        """禁用一个工具（加入禁用集合，LLM 将无法调用）"""
        if name in self._tools:
            self._disabled.add(name)

    def list_names(self) -> list[str]:
        """列出所有已注册的工具名称"""
        return list(self._tools.keys())

    def list_status(self) -> dict[str, bool]:
        """列出所有工具的启用状态，返回 {工具名: 是否启用}"""
        return {name: name not in self._disabled for name in self._tools}

    def apply_default_policy(self, disabled_by_default: set[str]) -> None:
        """首次注册后应用默认禁用策略，不覆盖运行时手动启停。"""
        if self._default_policy_applied:
            return
        self._disabled.update(name for name in disabled_by_default if name in self._tools)
        self._default_policy_applied = True


# 全局单例，整个应用共用一个注册中心
tool_registry = ToolRegistry()
