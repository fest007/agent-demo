"""
知识库入库模块

提供文档入库的核心逻辑：
1. 加载文档（文件/URL/纯文本）
2. 分割成小块
3. 转为向量嵌入
4. 存入向量数据库（开发 Chroma，生产可切 Qdrant）

这是 RAG 系统的"写入"路径。
"""
from agent.rag.embedder import get_embedder
from agent.rag.splitter import get_splitter
from agent.rag.vector_store import get_vector_collection

_documents_cache: dict | None = None


def _get_collection():
    """获取知识库向量集合（与 retriever.py 中相同）"""
    return get_vector_collection("knowledge")


def _invalidate_documents_cache() -> None:
    global _documents_cache
    _documents_cache = None


def ingest_text(text: str, metadata: dict | None = None) -> str:
    """
    将纯文本存入知识库

    完整流程：
    1. 文本分割 → 多个小块
    2. 每个小块 → 嵌入向量
    3. 向量 + 文本 + 元数据 → 向量数据库

    Args:
        text: 要入库的文本内容
        metadata: 元数据（如来源 URL、文件名等）

    Returns:
        入库结果信息
    """
    # 第一步：分割文本
    splitter = get_splitter()
    docs = splitter.split_text(text)

    # 第二步：获取集合和嵌入模型
    collection = _get_collection()
    embedder = get_embedder()

    # 第三步：为每个块创建元数据和唯一 ID
    # ID 格式：doc_{当前数量}_{序号}，确保唯一
    base_count = collection.count()
    ids = [f"doc_{base_count + i}" for i in range(len(docs))]
    metadatas = [{**(metadata or {}), "chunk_id": ids[i], "chunk_index": i + 1} for i in range(len(docs))]

    # 第四步：批量生成嵌入向量
    embeddings = embedder.embed_documents(docs)

    # 第五步：存入向量数据库
    collection.add(
        documents=docs,       # 原始文本
        metadatas=metadatas,  # 元数据
        ids=ids,              # 唯一标识
        embeddings=embeddings, # 向量
    )
    _invalidate_documents_cache()

    return f"已入库 {len(docs)} 个文档片段"


def ingest_file(file_path: str) -> str:
    """
    将文件存入知识库

    流程：文件 → Document → 分割 → 向量化 → 向量数据库

    Args:
        file_path: 文件路径

    Returns:
        入库结果信息
    """
    from agent.rag.loader import load_file

    # 加载文件为 Document 列表
    docs = load_file(file_path)

    splitter = get_splitter()
    collection = _get_collection()
    embedder = get_embedder()

    # 将所有 Document 分割成小块
    all_chunks = []
    all_metas = []
    for doc in docs:
        chunks = splitter.split_text(doc.page_content)
        all_chunks.extend(chunks)
        # 每个块都继承其父 Document 的元数据
        all_metas.extend([doc.metadata for _ in chunks])

    # 生成 ID、向量，存入数据库
    base_count = collection.count()
    ids = [f"doc_{base_count + i}" for i in range(len(all_chunks))]
    all_metas = [
        {**meta, "chunk_id": ids[i], "chunk_index": i + 1}
        for i, meta in enumerate(all_metas)
    ]
    embeddings = embedder.embed_documents(all_chunks)
    collection.add(
        documents=all_chunks,
        metadatas=all_metas,
        ids=ids,
        embeddings=embeddings,
    )
    _invalidate_documents_cache()

    return f"已入库 {len(all_chunks)} 个文档片段，来源: {file_path}"


def ingest_url(url: str) -> str:
    """
    将网页内容存入知识库

    流程：URL → 网页抓取 → Document → 分割 → 向量化 → 向量数据库

    Args:
        url: 网页 URL

    Returns:
        入库结果信息
    """
    from agent.rag.loader import load_url

    docs = load_url(url)
    splitter = get_splitter()
    collection = _get_collection()
    embedder = get_embedder()

    all_chunks = []
    all_metas = []
    for doc in docs:
        chunks = splitter.split_text(doc.page_content)
        all_chunks.extend(chunks)
        all_metas.extend([doc.metadata for _ in chunks])

    base_count = collection.count()
    ids = [f"doc_{base_count + i}" for i in range(len(all_chunks))]
    all_metas = [
        {**meta, "chunk_id": ids[i], "chunk_index": i + 1}
        for i, meta in enumerate(all_metas)
    ]
    embeddings = embedder.embed_documents(all_chunks)
    collection.add(
        documents=all_chunks,
        metadatas=all_metas,
        ids=ids,
        embeddings=embeddings,
    )
    _invalidate_documents_cache()

    content_length = sum(len(doc.page_content) for doc in docs)
    title = docs[0].metadata.get("title", url) if docs else url
    return f"已提取网页正文 {content_length} 字符，入库 {len(all_chunks)} 个文档片段，标题: {title}"


def list_documents() -> list[dict]:
    """
    列出知识库中的所有文档来源

    注意：向量数据库中存储的是文档片段，同一个文件会被分成多个片段。
    这里按 source 去重，返回唯一的文档来源列表。

    Returns:
        文档来源列表，每项包含 source 和 type
    """
    global _documents_cache
    collection = _get_collection()
    total_count = collection.count()
    if total_count == 0:
        return []
    if _documents_cache and _documents_cache.get("count") == total_count:
        return _documents_cache["docs"]

    # 获取所有元数据
    results = collection.get(include=["metadatas"])

    # 按 source 去重，并汇总片段数量
    seen: dict[str, dict] = {}
    docs = []
    for meta in results["metadatas"]:
        source = meta.get("source", "未知")
        if source not in seen:
            seen[source] = {
                "source": source,
                "type": meta.get("type", "未知"),
                "title": meta.get("title") or meta.get("filename") or source,
                "content_length": meta.get("content_length"),
                "extraction_quality": meta.get("extraction_quality"),
                "extraction_note": meta.get("extraction_note"),
                "chunks": 0,
            }
            docs.append(seen[source])
        seen[source]["chunks"] += 1

    _documents_cache = {"count": total_count, "docs": docs}
    return docs


def get_document_chunks(source: str) -> list[dict]:
    """返回某个来源下的所有知识库片段，用于前端预览和引用跳转。"""
    collection = _get_collection()
    results = collection.get(
        where={"source": source},
        include=["documents", "metadatas"],
    )

    chunks = []
    for index, (chunk_id, content, meta) in enumerate(
        zip(results["ids"], results["documents"], results["metadatas"]),
        1,
    ):
        chunks.append(
            {
                "chunk_id": meta.get("chunk_id") or chunk_id,
                "chunk_index": meta.get("chunk_index") or index,
                "content": content,
                "source": meta.get("source", source),
                "title": meta.get("title") or meta.get("filename") or source,
                "type": meta.get("type", "未知"),
                "extraction_quality": meta.get("extraction_quality"),
                "extraction_note": meta.get("extraction_note"),
            }
        )

    return sorted(chunks, key=lambda item: item["chunk_index"])


def delete_document(source: str) -> str:
    """
    按来源删除知识库中的文档

    删除某个来源的所有文档片段。

    Args:
        source: 文档来源（文件路径或 URL）

    Returns:
        删除结果信息
    """
    collection = _get_collection()

    # 查找所有来自该 source 的片段
    results = collection.get(where={"source": source})

    if results["ids"]:
        collection.delete(ids=results["ids"])
        _invalidate_documents_cache()
        return f"已删除 {len(results['ids'])} 个片段，来源: {source}"
    return f"未找到来源为 {source} 的文档"
