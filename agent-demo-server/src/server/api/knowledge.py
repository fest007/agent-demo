"""
知识库管理 API 模块

提供知识库的增删查接口：
- POST /api/knowledge/upload: 上传文件到知识库
- POST /api/knowledge/ingest-url: URL 抓取并入库
- POST /api/knowledge/ingest-text: 文本直接入库
- GET /api/knowledge/list: 列出已入库文档
- DELETE /api/knowledge: 按来源删除知识库文档

知识库存储在 ChromaDB 向量数据库中，
文件会被分割成小块、转为向量后存储。
"""
from fastapi import APIRouter, UploadFile, File, Depends, Query
from server.models.knowledge import (
    KnowledgeUploadResponse, KnowledgeIngestURLRequest,
    KnowledgeIngestTextRequest, KnowledgeDocument,
)
from server.deps import get_current_user, UserContext
from server.agent_import import ensure_agent_on_path
import asyncio
import tempfile
from pathlib import Path

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _get_rag():
    """
    动态导入 RAG 模块

    与 chat.py 中的 _get_agent() 类似，
    将 agent-demo-agent/src 加入 Python 路径。
    """
    ensure_agent_on_path()
    from agent.rag.ingest import (
        delete_document,
        get_document_chunks,
        ingest_file,
        ingest_text,
        ingest_url,
        list_documents,
    )
    return ingest_file, ingest_url, ingest_text, list_documents, delete_document, get_document_chunks


@router.post("/upload", response_model=KnowledgeUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user: UserContext = Depends(get_current_user),
):
    """
    上传文件到知识库

    流程：
    1. 接收上传的文件
    2. 保存到临时目录
    3. 调用 RAG 的 ingest_file 函数入库
    4. 删除临时文件

    Args:
        file: 上传的文件（PDF/Word/MD/TXT）
        user: 当前用户

    Returns:
        上传结果（成功/失败信息）
    """
    ingest_file_fn, _, _, _, _, _ = _get_rag()

    # 获取文件扩展名
    suffix = Path(file.filename).suffix

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 调用 RAG 入库函数
        result = ingest_file_fn(tmp_path)
        return KnowledgeUploadResponse(filename=file.filename, status="success", message=result)
    except Exception as e:
        return KnowledgeUploadResponse(filename=file.filename, status="error", message=str(e))
    finally:
        # 无论成功失败，都删除临时文件
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/ingest-url")
async def ingest_url_endpoint(
    request: KnowledgeIngestURLRequest,
    user: UserContext = Depends(get_current_user),
):
    """
    URL 抓取并入库

    流程：
    1. 抓取 URL 网页内容
    2. 提取正文文本
    3. 分割、向量化、存入 ChromaDB

    Args:
        request: 包含 url 字段

    Returns:
        入库结果
    """
    _, ingest_url_fn, _, _, _, _ = _get_rag()
    try:
        result = ingest_url_fn(request.url)
        return {"status": "success", "message": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/ingest-text")
async def ingest_text_endpoint(
    request: KnowledgeIngestTextRequest,
    user: UserContext = Depends(get_current_user),
):
    """
    文本直接入库

    将用户直接输入的文本存入知识库。
    适合手动录入知识的场景。
    """
    _, _, ingest_text_fn, _, _, _ = _get_rag()
    try:
        result = ingest_text_fn(request.text, metadata={"source": request.source, "type": "text"})
        return {"status": "success", "message": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/list")
async def list_docs(user: UserContext = Depends(get_current_user)):
    """列出知识库中的所有文档来源"""
    _, _, _, list_documents_fn, _, _ = _get_rag()
    return await asyncio.to_thread(list_documents_fn)


@router.get("/preview")
async def preview_doc(source: str, user: UserContext = Depends(get_current_user)):
    """预览某个知识库文档的所有片段。"""
    _, _, _, _, _, get_document_chunks_fn = _get_rag()
    return await asyncio.to_thread(get_document_chunks_fn, source)


@router.delete("")
async def delete_doc(
    source: str = Query(..., description="文档来源，通常是文件路径或 URL"),
    user: UserContext = Depends(get_current_user),
):
    """按来源删除知识库文档"""
    _, _, _, _, delete_document_fn, _ = _get_rag()
    try:
        result = delete_document_fn(source)
        return {"status": "success", "message": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
