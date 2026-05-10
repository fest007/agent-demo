from pydantic import BaseModel
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"
    enable_tts: bool = False
    images: list[str] = []


class ChatResponse(BaseModel):
    content: str
    emotion: str
    thread_id: str
    tools_used: list[str] = []


class ChatStreamEvent(BaseModel):
    type: str  # "emotion", "token", "tool_start", "tool_end", "done"
    data: str | dict = ""


class ChatHistoryItem(BaseModel):
    role: str
    content: str
    timestamp: datetime
    emotion: str | None = None
