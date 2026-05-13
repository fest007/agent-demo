from pydantic import BaseModel
from datetime import datetime


class SessionResponse(BaseModel):
    session_id: str
    name: str
    created_at: datetime
    updated_at: datetime


class SessionUpdate(BaseModel):
    name: str


class SessionSummarizeRequest(BaseModel):
    model_provider: str | None = None
    model: str | None = None
    api_key_id: str | None = None
    custom_base_url: str | None = None
    custom_api_key: str | None = None
