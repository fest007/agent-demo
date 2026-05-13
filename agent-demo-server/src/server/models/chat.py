from pydantic import BaseModel, Field
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"
    enable_tts: bool = False
    images: list[str] = []
    model_provider: str | None = None
    model: str | None = None
    image_model: str | None = None
    video_model: str | None = None
    api_key_id: str | None = None
    custom_base_url: str | None = None
    custom_api_key: str | None = None


class ChatResponse(BaseModel):
    content: str
    emotion: str
    thread_id: str
    tools_used: list[str] = []


class ChatStreamEvent(BaseModel):
    type: str  # "emotion", "thought", "citation", "token", "tool_start", "tool_end", "media_task", "done"
    data: str | dict = ""


class ChatHistoryItem(BaseModel):
    id: str | None = None
    role: str
    content: str
    timestamp: datetime
    emotion: str | None = None
    thoughts: list[dict] = Field(default_factory=list)
    toolCalls: list[dict] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)
    mediaTasks: list[dict] = Field(default_factory=list)
