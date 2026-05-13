from pydantic import BaseModel


class KnowledgeUploadResponse(BaseModel):
    filename: str
    status: str
    message: str


class KnowledgeIngestURLRequest(BaseModel):
    url: str


class KnowledgeIngestTextRequest(BaseModel):
    text: str
    source: str = "manual"


class KnowledgeDocument(BaseModel):
    source: str
    type: str
    title: str | None = None
    content_length: int | None = None
    extraction_quality: str | None = None
    extraction_note: str | None = None
    chunks: int | None = None


class KnowledgeChunk(BaseModel):
    chunk_id: str
    chunk_index: int
    content: str
    source: str
    title: str
    type: str
    extraction_quality: str | None = None
    extraction_note: str | None = None
