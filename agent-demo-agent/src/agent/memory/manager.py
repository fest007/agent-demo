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
