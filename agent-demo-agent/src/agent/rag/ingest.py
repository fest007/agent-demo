"""
知识库入库模块

提供文档入库的核心逻辑：
1. 加载文档（文件/URL/纯文本）
2. 分割成小块
3. 转为向量嵌入
4. 存入 ChromaDB

这是 RAG 系统的"写入"路径。
"""
import chromadb
from agent.rag.embedder import get_embedder
from agent.rag.splitter import get_splitter
from agent.config import get_settings


def _get_collection():
    """获取 ChromaDB 集合（与 retriever.py 中相同）"""
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return client.get_or_create_collection(
        name="knowledge",
        metadata={"hnsw:space": "cosine"},
    )


def ingest_text(text: str, metadata: dict | None = None) -> str:
    """
    将纯文本存入知识库

    完整流程：
    1. 文本分割 → 多个小块
    2. 每个小块 → 嵌入向量
    3. 向量 + 文本 + 元数据 → ChromaDB

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
    metadatas = [metadata or {} for _ in docs]
    # ID 格式：doc_{当前数量}_{序号}，确保唯一
    ids = [f"doc_{collection.count() + i}" for i in range(len(docs))]

    # 第四步：批量生成嵌入向量
    embeddings = embedder.embed_documents(docs)

    # 第五步：存入 ChromaDB
    collection.add(
        documents=docs,       # 原始文本
        metadatas=metadatas,  # 元数据
        ids=ids,              # 唯一标识
        embeddings=embeddings, # 向量
    )

    return f"已入库 {len(docs)} 个文档片段"


def ingest_file(file_path: str) -> str:
    """
    将文件存入知识库

    流程：文件 → Document → 分割 → 向量化 → ChromaDB

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
    ids = [f"doc_{collection.count() + i}" for i in range(len(all_chunks))]
    embeddings = embedder.embed_documents(all_chunks)
    collection.add(
        documents=all_chunks,
        metadatas=all_metas,
        ids=ids,
        embeddings=embeddings,
    )

    return f"已入库 {len(all_chunks)} 个文档片段，来源: {file_path}"


def ingest_url(url: str) -> str:
    """
    将网页内容存入知识库

    流程：URL → 网页抓取 → Document → 分割 → 向量化 → ChromaDB

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

    ids = [f"doc_{collection.count() + i}" for i in range(len(all_chunks))]
    embeddings = embedder.embed_documents(all_chunks)
    collection.add(
        documents=all_chunks,
        metadatas=all_metas,
        ids=ids,
        embeddings=embeddings,
    )

    return f"已入库 {len(all_chunks)} 个文档片段，来源: {url}"


def list_documents() -> list[dict]:
    """
    列出知识库中的所有文档来源

    注意：ChromaDB 中存储的是文档片段，同一个文件会被分成多个片段。
    这里按 source 去重，返回唯一的文档来源列表。

    Returns:
        文档来源列表，每项包含 source 和 type
    """
    collection = _get_collection()
    if collection.count() == 0:
        return []

    # 获取所有元数据
    results = collection.get(include=["metadatas"])

    # 按 source 去重
    seen = set()
    docs = []
    for meta in results["metadatas"]:
        source = meta.get("source", "未知")
        if source not in seen:
            seen.add(source)
            docs.append({"source": source, "type": meta.get("type", "未知")})

    return docs


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
        return f"已删除 {len(results['ids'])} 个片段，来源: {source}"
    return f"未找到来源为 {source} 的文档"
