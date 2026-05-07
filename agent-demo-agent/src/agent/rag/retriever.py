"""
RAG 检索器模块

将知识库检索封装为 LangChain 工具，LLM 可以通过 Function Calling 调用。

工作原理：
1. 用户提问 → LLM 判断是否需要查知识库
2. 如果需要 → 调用 knowledge_search 工具
3. 工具将查询文本转为向量，在 ChromaDB 中做相似度搜索
4. 返回最相关的文档片段
5. LLM 基于检索结果生成回答
"""
from langchain_core.tools import tool
import chromadb
from agent.rag.embedder import get_embedder
from agent.config import get_settings

# 全局单例，缓存 ChromaDB 客户端和集合
_client = None
_collection = None


def _get_collection():
    """
    获取 ChromaDB 集合单例

    ChromaDB 是一个开源的向量数据库，专门用于存储和检索向量嵌入。
    PersistentClient 会将数据持久化到磁盘，重启后数据不丢失。

    Returns:
        ChromaDB Collection 对象
    """
    global _client, _collection
    if _collection is None:
        settings = get_settings()
        # PersistentClient: 数据持久化到指定目录
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        # get_or_create_collection: 如果集合不存在则创建
        # hnsw:space=cosine: 使用余弦相似度作为距离度量
        _collection = _client.get_or_create_collection(
            name="knowledge",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


@tool
def knowledge_search(query: str, top_k: int = 3) -> str:
    """
    检索知识库中的相关内容。

    工作流程：
    1. 将查询文本转为向量（使用 bge-base-zh 嵌入模型）
    2. 在 ChromaDB 中做余弦相似度搜索
    3. 返回最相关的 top_k 个文档片段

    Args:
        query: 用户的查询文本
        top_k: 返回的最大结果数，默认 3

    Returns:
        格式化的检索结果，包含来源和内容
    """
    try:
        collection = _get_collection()

        # 如果知识库为空，直接返回提示
        if collection.count() == 0:
            return "知识库为空，请先上传文档或添加网址"

        # 将查询文本转为向量
        embedder = get_embedder()
        query_embedding = embedder.embed_query(query)

        # 在 ChromaDB 中做相似度搜索
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),  # 不超过实际文档数
        )

        if not results["documents"][0]:
            return "未找到相关内容"

        # 格式化检索结果
        formatted = []
        for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0]), 1):
            source = meta.get("source", "未知来源")
            formatted.append(f"[{i}] 来源: {source}\n{doc}")

        return "\n\n".join(formatted)
    except Exception as e:
        return f"知识库检索失败: {str(e)}"
