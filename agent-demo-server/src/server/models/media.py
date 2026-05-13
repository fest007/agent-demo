from datetime import datetime

from pydantic import BaseModel, Field


class MediaTaskResponse(BaseModel):
    id: str
    thread_id: str
    conversation_id: int | None = None
    provider: str
    model: str
    task_type: str
    mode: str
    prompt: str
    status: str
    progress: int = 0
    external_task_id: str | None = None
    input_images: list[str] = Field(default_factory=list)
    result_urls: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None


class MediaTaskListResponse(BaseModel):
    tasks: list[MediaTaskResponse] = Field(default_factory=list)
