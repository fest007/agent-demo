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


class SkillUpdateRequest(BaseModel):
    description: str | None = None
    content: str | None = None
