"""
RAG 检索器模块

将知识库检索封装为 LangChain 工具，LLM 可以通过 Function Calling 调用。

工作原理：
1. 用户提问 → LLM 判断是否需要查知识库
2. 如果需要 → 调用 knowledge_search 工具
3. 工具将查询文本转为向量，在向量数据库中做相似度搜索
4. 返回最相关的文档片段
5. LLM 基于检索结果生成回答
"""
from langchain_core.tools import tool
from agent.rag.embedder import get_embedder
from agent.rag.vector_store import get_vector_collection

# 全局单例，缓存向量集合
_collection = None


def _get_collection():
    """
    获取知识库向量集合单例。

    Returns:
        向量集合对象
    """
    global _collection
    if _collection is None:
        _collection = get_vector_collection("knowledge")
    return _collection


@tool
def knowledge_search(query: str, top_k: int = 3) -> str:
    """
    检索知识库中的相关内容。

    工作流程：
    1. 将查询文本转为向量（使用 bge-base-zh 嵌入模型）
    2. 在向量数据库中做余弦相似度搜索
    3. 返回最相关的 top_k 个文档片段

    Args:
        query: 用户的查询文本
        top_k: 返回的最大结果数，默认 3

    Returns:
        格式化的检索结果，包含来源和内容
    """
    try:
        citations = search_knowledge(query, top_k)
        if not citations:
            return "知识库为空，请先上传文档或添加网址"

        # 格式化检索结果
        formatted = []
        for i, item in enumerate(citations, 1):
            formatted.append(
                f"[引用{i}] 来源: {item['source']}\n"
                f"标题: {item.get('title') or item['source']}\n"
                f"片段: {item.get('chunk_index')}\n"
                f"{item['content']}"
            )

        return "\n\n".join(formatted)
    except Exception as e:
        return f"知识库检索失败: {str(e)}"


def search_knowledge(query: str, top_k: int = 3) -> list[dict]:
    """结构化检索知识库，返回可用于引用跳转的片段信息。"""
    collection = _get_collection()

    if collection.count() == 0:
        return []

    embedder = get_embedder()
    query_embedding = embedder.embed_query(query)

    results = collection.query(
        query_embedding=query_embedding,
        top_k=top_k,
    )
    if not results:
        return []

    citations = []
    for i, item in enumerate(results, 1):
        doc = item.document
        meta = item.metadata
        source = meta.get("source", "未知来源")
        content = doc.strip()
        citations.append(
            {
                "id": f"ref-{i}",
                "source": source,
                "title": meta.get("title") or meta.get("filename") or source,
                "type": meta.get("type", "未知"),
                "chunk_id": meta.get("chunk_id") or item.id,
                "chunk_index": meta.get("chunk_index") or i,
                "excerpt": content[:220],
                "content": content,
                "score": item.score if item.score is not None else (
                    1 - item.distance if item.distance is not None else None
                ),
            }
        )
    return citations
