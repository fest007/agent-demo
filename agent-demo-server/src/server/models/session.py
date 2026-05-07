from pydantic import BaseModel
from datetime import datetime


class SessionResponse(BaseModel):
    session_id: str
    name: str
    created_at: datetime
    updated_at: datetime


class SessionUpdate(BaseModel):
    name: str
