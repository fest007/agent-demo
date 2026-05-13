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
from agent.rag.embedder import get_embedder
from agent.rag.vector_store import get_vector_collection
import sqlite3
from datetime import datetime


# 用户记忆向量集合单例
_user_memory_collection = None


def _get_user_memory_collection():
    """获取用户记忆向量集合单例（与知识库集合独立）"""
    global _user_memory_collection
    if _user_memory_collection is None:
        _user_memory_collection = get_vector_collection("user_memory")
    return _user_memory_collection


def _memory_id(user_id: str, namespace: str, key: str) -> str:
    """生成确定性记忆 ID，支持 upsert 语义"""
    return f"{user_id}_{namespace}_{key}"


def _sync_to_vector_store(action: str, user_id: str, namespace: str, key: str, value: str = None):
    """同步记忆到向量库，失败不影响 SQLite 主路径"""
    try:
        collection = _get_user_memory_collection()
        doc_id = _memory_id(user_id, namespace, key)

        if action == "upsert" and value is not None:
            doc_text = f"{key}: {value}"
            embedder = get_embedder()
            embedding = embedder.embed_documents([doc_text])
            collection.upsert(
                ids=[doc_id],
                documents=[doc_text],
                embeddings=embedding,
                metadatas=[{"user_id": user_id, "namespace": namespace, "key": key, "value": value}],
            )
        elif action == "delete":
            collection.delete(ids=[doc_id])
    except Exception:
        pass  # 向量库故障不阻塞 SQLite 操作


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

        # 同步到向量库
        _sync_to_vector_store("upsert", user_id, namespace, key, value)

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

        if cursor.rowcount > 0:
            # 同步删除向量库中的向量
            _sync_to_vector_store("delete", user_id, namespace, key)
            return True
        return False

    def search(self, user_id: str, query: str, top_k: int = 5) -> list[dict]:
        """
        语义搜索用户记忆

        通过向量相似度在向量库中检索与 query 最相关的记忆。

        Args:
            user_id: 用户标识
            query: 搜索查询文本
            top_k: 返回的最大结果数

        Returns:
            按相关性排序的记忆列表
        """
        try:
            collection = _get_user_memory_collection()
            if collection.count() == 0:
                return []

            embedder = get_embedder()
            query_embedding = embedder.embed_query(query)

            results = collection.query(
                query_embedding=query_embedding,
                top_k=top_k,
                where={"user_id": user_id},
            )

            if not results:
                return []

            memories = []
            for item in results:
                meta = item.metadata
                memories.append({
                    "namespace": meta.get("namespace", ""),
                    "key": meta.get("key", ""),
                    "value": meta.get("value", ""),
                })
            return memories
        except Exception:
            return []


# 全局单例
_long_term = None


def get_long_term_memory() -> LongTermMemory:
    """获取长期记忆管理器单例"""
    global _long_term
    if _long_term is None:
        _long_term = LongTermMemory()
    return _long_term
