"""
长期记忆模块

使用 SQLite 实现跨会话的持久化记忆。
存储结构：user_id + namespace + key → value

设计思路：
- user_id: 用户标识，支持多用户隔离
- namespace: 记忆分类（如 "facts" 事实、"preferences" 偏好）
- key-value: 具体的记忆条目

使用场景：
- 记住用户的偏好（如"用户喜欢简洁回复"）
- 记住学到的事实（如"用户的公司叫 XX"）
- 跨会话保持上下文
"""
from agent.config import get_settings
import sqlite3
from datetime import datetime


class LongTermMemory:
    """
    长期记忆管理器

    使用 SQLite 存储，支持 CRUD 操作。
    UNIQUE(user_id, namespace, key) 约束确保同一用户下不会重复存储相同的记忆。
    """

    def __init__(self):
        settings = get_settings()
        self.db_path = settings.long_term_db
        self._init_db()  # 启动时自动建表

    def _init_db(self):
        """
        初始化数据库表

        memories 表结构：
        - id: 自增主键
        - user_id: 用户标识
        - namespace: 记忆分类（facts/preferences 等）
        - key: 记忆键
        - value: 记忆值
        - created_at: 创建时间
        - updated_at: 更新时间
        - UNIQUE(user_id, namespace, key): 防止重复
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, namespace, key)
            )
        """)
        conn.commit()
        conn.close()

    def save(self, user_id: str, namespace: str, key: str, value: str) -> None:
        """
        保存或更新一条记忆

        如果 (user_id, namespace, key) 已存在，则更新 value 和 updated_at。
        如果不存在，则插入新记录。
        使用 COALESCE 保留原始的 created_at。

        Args:
            user_id: 用户标识
            namespace: 记忆分类
            key: 记忆键
            value: 记忆值
        """
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT OR REPLACE INTO memories (user_id, namespace, key, value, created_at, updated_at)
               VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM memories WHERE user_id=? AND namespace=? AND key=?), ?), ?)""",
            (user_id, namespace, key, value, user_id, namespace, key, now, now),
        )
        conn.commit()
        conn.close()

    def get(self, user_id: str, namespace: str, key: str) -> str | None:
        """
        获取一条记忆

        Args:
            user_id: 用户标识
            namespace: 记忆分类
            key: 记忆键

        Returns:
            记忆值，如果不存在返回 None
        """
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT value FROM memories WHERE user_id=? AND namespace=? AND key=?",
            (user_id, namespace, key),
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def list_all(self, user_id: str, namespace: str = "") -> list[dict]:
        """
        列出用户的所有记忆

        Args:
            user_id: 用户标识
            namespace: 可选，指定分类。为空则返回所有分类

        Returns:
            记忆列表
        """
        conn = sqlite3.connect(self.db_path)
        if namespace:
            # 指定分类查询
            rows = conn.execute(
                "SELECT key, value, updated_at FROM memories WHERE user_id=? AND namespace=?",
                (user_id, namespace),
            ).fetchall()
        else:
            # 查询所有分类
            rows = conn.execute(
                "SELECT namespace, key, value, updated_at FROM memories WHERE user_id=?",
                (user_id,),
            ).fetchall()
        conn.close()

        if namespace:
            return [{"key": r[0], "value": r[1], "updated_at": r[2]} for r in rows]
        return [{"namespace": r[0], "key": r[1], "value": r[2], "updated_at": r[3]} for r in rows]

    def delete(self, user_id: str, namespace: str, key: str) -> bool:
        """
        删除一条记忆

        Returns:
            是否成功删除（True 表示找到了并删除了）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "DELETE FROM memories WHERE user_id=? AND namespace=? AND key=?",
            (user_id, namespace, key),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0


# 全局单例
_long_term = None


def get_long_term_memory() -> LongTermMemory:
    """获取长期记忆管理器单例"""
    global _long_term
    if _long_term is None:
        _long_term = LongTermMemory()
    return _long_term
