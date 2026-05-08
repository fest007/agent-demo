"""
记忆管理器

提供统一的记忆操作接口，封装底层的 LongTermMemory。
按 user_id 隔离不同用户的记忆。

使用方式：
    manager = MemoryManager(user_id="user123")
    manager.save_preference("回复风格", "简洁")
    manager.save_fact("公司名称", "XX科技")
"""
from agent.memory.long_term import get_long_term_memory


class MemoryManager:
    """
    记忆管理器

    将长期记忆按语义分为两类：
    - facts: 用户告诉我们的事实（如公司名、职位等）
    - preferences: 用户的偏好（如回复风格、语言等）
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.ltm = get_long_term_memory()

    def save_fact(self, key: str, value: str) -> None:
        """保存一条事实记忆"""
        self.ltm.save(self.user_id, "facts", key, value)

    def save_preference(self, key: str, value: str) -> None:
        """保存一条偏好记忆"""
        self.ltm.save(self.user_id, "preferences", key, value)

    def get_facts(self) -> list[dict]:
        """获取所有事实记忆"""
        return self.ltm.list_all(self.user_id, "facts")

    def get_preferences(self) -> list[dict]:
        """获取所有偏好记忆"""
        return self.ltm.list_all(self.user_id, "preferences")

    def get_all_memories(self) -> list[dict]:
        """获取所有记忆（包括事实和偏好）"""
        return self.ltm.list_all(self.user_id)

    def search_memories(self, query: str, top_k: int = 5) -> list[dict]:
        """语义搜索与 query 最相关的记忆"""
        return self.ltm.search(self.user_id, query, top_k)

    def get_core_memories(self, namespace: str = "preferences") -> list[dict]:
        """获取核心记忆（始终注入，不按相关性过滤）"""
        return self.ltm.list_all(self.user_id, namespace)

    def search_with_core(
        self, query: str, top_k: int = 5, core_namespace: str = "preferences"
    ) -> tuple[list[dict], list[dict]]:
        """
        语义搜索 + 核心记忆

        Returns:
            (semantic_results, core_results) 元组
        """
        semantic = self.search_memories(query, top_k)
        core = self.get_core_memories(core_namespace)
        return semantic, core


def format_memories_for_prompt(
    semantic_results: list[dict], core_results: list[dict]
) -> str:
    """
    将记忆格式化为系统提示词注入文本。

    core_results 始终排在前面，semantic_results 去重后追加。
    """
    seen = set()
    combined = []

    for mem in core_results:
        ns = mem.get("namespace", "")
        key = mem.get("key", "")
        mid = f"{ns}_{key}"
        if mid not in seen:
            seen.add(mid)
            combined.append(mem)

    for mem in semantic_results:
        ns = mem.get("namespace", "")
        key = mem.get("key", "")
        mid = f"{ns}_{key}"
        if mid not in seen:
            seen.add(mid)
            combined.append(mem)

    if not combined:
        return ""

    lines = ["以下是关于这个用户的已知信息，请在回复时参考："]
    for mem in combined:
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
