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
