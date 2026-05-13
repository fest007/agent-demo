from pydantic import BaseModel, Field


class ApiKeyInfo(BaseModel):
    id: str
    label: str
    masked: str
    provider: str = "mimo"


class ModelInfo(BaseModel):
    id: str
    label: str
    purpose: str = "chat"


class ModelProviderInfo(BaseModel):
    id: str
    label: str
    base_url: str
    keys: list[ApiKeyInfo] = Field(default_factory=list)
    models: list[ModelInfo] = Field(default_factory=list)
    default_model: str = ""
    fast_model: str = ""
    omni_model: str = ""
    quota_supported: bool = False


class QuotaRequest(BaseModel):
    key_id: str = "default"
    provider: str = "mimo"
    custom_base_url: str | None = None
    custom_api_key: str | None = None


class ModelListRequest(BaseModel):
    provider: str = "mimo"
    key_id: str = "default"
    custom_base_url: str | None = None
    custom_api_key: str | None = None


class RemoteModelInfo(BaseModel):
    id: str
    label: str = ""
    capability: str = "chat"
    chat_supported: bool = True
    image_supported: bool = False
    video_supported: bool = False
    note: str = ""


class ModelListResponse(BaseModel):
    provider: str
    base_url: str
    status: str = "ok"
    message: str = ""
    models: list[RemoteModelInfo] = Field(default_factory=list)


class QuotaResponse(BaseModel):
    provider: str = "mimo"
    key_id: str
    key_label: str
    supported: bool = True
    status: str = "ok"
    total: float | None = None
    used: float | None = None
    remaining: float | None = None
    percent_remaining: float | None = None
    unit: str = "credit"
    message: str = ""
    raw: dict = Field(default_factory=dict)
