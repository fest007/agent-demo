from pydantic import BaseModel


class SkillInfo(BaseModel):
    name: str
    description: str
    content: str = ""
    is_builtin: bool
    created_at: str


class SkillCreateRequest(BaseModel):
    name: str
    description: str
    content: str = ""


class SkillGenerateRequest(BaseModel):
    description: str
    model_provider: str | None = None
    model: str | None = None
    api_key_id: str | None = None
    custom_base_url: str | None = None
    custom_api_key: str | None = None


class SkillUpdateRequest(BaseModel):
    description: str | None = None
    content: str | None = None
