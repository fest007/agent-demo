"""
设置相关 API

用于列出已配置的模型供应商、API Key，并查询支持供应商的剩余额度。
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends

from server.agent_import import ensure_agent_on_path
from server.deps import UserContext, get_current_user
from server.models.settings import (
    ApiKeyInfo,
    ModelListRequest,
    ModelListResponse,
    ModelInfo,
    ModelProviderInfo,
    QuotaRequest,
    QuotaResponse,
)


router = APIRouter(prefix="/api/settings", tags=["settings"])


VOLCENGINE_KNOWN_MODELS: dict[str, tuple[str, str, bool, str]] = {
    "doubao-seed3d-2-0-260328": ("Doubao-Seed3D-2.0", "3D 资产生成", False, "3D 模型生成专用，不适用于聊天对话"),
    "hitem3d-2-0-251223": ("Hitem3D-2.0", "3D 资产生成", False, "3D 模型生成专用，不适用于聊天对话"),
    "hyper3d-gen2-260112": ("Hyper3D-Gen2", "3D 资产生成", False, "3D 模型生成专用，不适用于聊天对话"),
    "doubao-seedance-2-0-260128": ("Doubao-Seedance-2.0", "视频生成", False, "视频生成专用，不适用于聊天对话"),
    "doubao-seedance-2-0-fast-260128": ("Doubao-Seedance-2.0-fast", "视频生成", False, "视频生成专用，不适用于聊天对话"),
    "doubao-seedance-1-5-pro-251215": ("Doubao-Seedance-1.5-Pro", "视频生成", False, "视频生成专用，不适用于聊天对话"),
    "doubao-seedream-5-0-260128": ("Doubao-Seedream-5.0-lite", "图像生成", False, "图像生成专用，不适用于聊天对话"),
    "doubao-seed-2-0-code-preview-260215": ("Doubao-Seed-2.0-Code", "代码/文本对话", True, "可用于当前聊天对话"),
    "doubao-seed-tts-2-0": ("Doubao-语音合成-2.0", "语音合成", False, "语音合成专用，不适用于聊天对话"),
    "doubao-seed-podcast": ("Doubao-语音播客", "音频生成", False, "播客音频生成专用，不适用于聊天对话"),
    "doubao-seed-voice-design": ("Doubao-音色设计", "音色设计", False, "音色设计专用，不适用于聊天对话"),
}


def _model_capabilities(model_id: str, capability: str, chat_supported: bool) -> dict[str, bool]:
    lowered = f"{model_id} {capability}".lower()
    return {
        "chat_supported": chat_supported,
        "image_supported": "seedream" in lowered or "图像" in capability or "图片" in capability,
        "video_supported": "seedance" in lowered or "视频" in capability,
    }


def _agent_settings():
    ensure_agent_on_path()
    from agent.config import get_settings

    return get_settings()


def _provider_helpers():
    ensure_agent_on_path()
    from agent.model_providers import list_model_providers, mask_key

    return list_model_providers, mask_key


def _configured_providers():
    list_model_providers, _ = _provider_helpers()
    return list_model_providers()


def _resolve_key(provider_id: str, key_id: str):
    for provider in _configured_providers():
        if provider.id != provider_id:
            continue
        for key in provider.keys:
            if key.id == key_id:
                return provider, key
    return None


@router.get("/api-keys", response_model=list[ApiKeyInfo])
async def list_api_keys(user: UserContext = Depends(get_current_user)):
    _, mask_key = _provider_helpers()
    keys: list[ApiKeyInfo] = []
    for provider in _configured_providers():
        keys.extend(
            ApiKeyInfo(
                id=key.id,
                label=key.label,
                masked=mask_key(key.key),
                provider=provider.id,
            )
            for key in provider.keys
        )
    return keys


@router.get("/model-providers", response_model=list[ModelProviderInfo])
async def list_providers(user: UserContext = Depends(get_current_user)):
    _, mask_key = _provider_helpers()
    return [
        ModelProviderInfo(
            id=provider.id,
            label=provider.label,
            base_url=provider.base_url,
            keys=[
                ApiKeyInfo(
                    id=key.id,
                    label=key.label,
                    masked=mask_key(key.key),
                    provider=provider.id,
                )
                for key in provider.keys
            ],
            models=[
                ModelInfo(id=model.id, label=model.label, purpose=model.purpose)
                for model in provider.models
            ],
            default_model=provider.default_model,
            fast_model=provider.fast_model,
            omni_model=provider.omni_model,
            quota_supported=provider.quota_supported,
        )
        for provider in _configured_providers()
    ]


def _root_from_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return "https://api.xiaomimimo.com"
    return f"{parsed.scheme}://{parsed.netloc}"


def _models_url(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise ValueError("Base URL 不能为空")
    parsed = urlparse(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Base URL 必须是 http 或 https 地址")
    return f"{base}/models"


def _classify_remote_model(model_id: str, label: str = "") -> dict[str, str | bool]:
    known = VOLCENGINE_KNOWN_MODELS.get(model_id)
    if known:
        known_label, capability, chat_supported, note = known
        flags = _model_capabilities(model_id, capability, chat_supported)
        return {
            "id": model_id,
            "label": label or known_label,
            "capability": capability,
            **flags,
            "note": note,
        }

    lowered = model_id.lower()
    non_chat_rules = [
        ("seedream", "图像生成", "图像生成专用，不适用于聊天对话"),
        ("seedance", "视频生成", "视频生成专用，不适用于聊天对话"),
        ("seed3d", "3D 资产生成", "3D 模型生成专用，不适用于聊天对话"),
        ("hitem3d", "3D 资产生成", "3D 模型生成专用，不适用于聊天对话"),
        ("hyper3d", "3D 资产生成", "3D 模型生成专用，不适用于聊天对话"),
        ("tts", "语音合成", "语音合成专用，不适用于聊天对话"),
        ("podcast", "音频生成", "音频生成专用，不适用于聊天对话"),
        ("voice-design", "音色设计", "音色设计专用，不适用于聊天对话"),
    ]
    for keyword, capability, note in non_chat_rules:
        if keyword in lowered:
            return {
                "id": model_id,
                "label": label or model_id,
                "capability": capability,
                "chat_supported": False,
                "image_supported": capability == "图像生成",
                "video_supported": capability == "视频生成",
                "note": note,
            }

    capability = "代码/文本对话" if "code" in lowered else "文本对话"
    return {
        "id": model_id,
        "label": label or model_id,
        "capability": capability,
        "chat_supported": True,
        "image_supported": False,
        "video_supported": False,
        "note": "可用于当前聊天对话",
    }


def _parse_models_payload(data: Any) -> list[dict[str, str | bool]]:
    if isinstance(data, dict):
        raw_items = data.get("data") or data.get("models") or data.get("items") or []
    elif isinstance(data, list):
        raw_items = data
    else:
        raw_items = []

    models: list[dict[str, str | bool]] = []
    seen: set[str] = set()
    for item in raw_items:
        if isinstance(item, str):
            model_id = item
            label = item
        elif isinstance(item, dict):
            model_id = str(item.get("id") or item.get("model") or item.get("name") or "").strip()
            label = str(item.get("label") or item.get("display_name") or item.get("name") or model_id).strip()
        else:
            continue
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        models.append(_classify_remote_model(model_id, label))
    return models


async def _fetch_openai_compatible_models(base_url: str, api_key: str) -> list[dict[str, str | bool]]:
    url = _models_url(base_url)
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code >= 400:
            detail = resp.text[:300]
            raise RuntimeError(f"{url} -> HTTP {resp.status_code}: {detail}")
        return _parse_models_payload(resp.json())


@router.post("/models", response_model=ModelListResponse)
async def list_remote_models(
    request: ModelListRequest,
    user: UserContext = Depends(get_current_user),
):
    custom_base_url = (request.custom_base_url or "").strip()
    custom_api_key = (request.custom_api_key or "").strip()
    provider_id = request.provider or "custom"

    if custom_base_url and custom_api_key:
        base_url = custom_base_url
        api_key = custom_api_key
    else:
        resolved = _resolve_key(provider_id, request.key_id)
        if not resolved:
            return ModelListResponse(
                provider=provider_id,
                base_url=custom_base_url,
                status="error",
                message="未找到可用于拉取模型列表的 API Key，请填写 API Key 或检查后端配置。",
            )
        provider, key = resolved
        base_url = custom_base_url or provider.base_url
        api_key = key.key

    try:
        models = await _fetch_openai_compatible_models(base_url, api_key)
        if not models:
            return ModelListResponse(
                provider=provider_id,
                base_url=base_url,
                status="empty",
                message="接口返回成功，但未解析到模型列表，可继续手动输入模型 ID。",
                models=[],
            )
        return ModelListResponse(
            provider=provider_id,
            base_url=base_url,
            message=f"已获取 {len(models)} 个模型。",
            models=models,
        )
    except Exception as exc:
        return ModelListResponse(
            provider=provider_id,
            base_url=base_url,
            status="error",
            message=f"获取模型列表失败：{exc}。可继续手动输入模型 ID。",
            models=[],
        )


def _as_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _first_number(data: dict, names: tuple[str, ...]) -> float | None:
    for name in names:
        if name in data:
            value = _as_number(data.get(name))
            if value is not None:
                return value
    for value in data.values():
        if isinstance(value, dict):
            nested = _first_number(value, names)
            if nested is not None:
                return nested
    return None


def _parse_quota_payload(data: dict) -> tuple[float | None, float | None, float | None, str]:
    total = _first_number(data, ("total", "total_quota", "quota", "hard_limit_usd", "total_granted"))
    used = _first_number(data, ("used", "used_quota", "usage", "total_used"))
    remaining = _first_number(data, ("remaining", "remain", "available", "available_quota", "balance", "total_available"))
    unit = str(data.get("unit") or data.get("quota_unit") or "credit")

    if remaining is None and total is not None and used is not None:
        remaining = max(total - used, 0)
    if used is None and total is not None and remaining is not None:
        used = max(total - remaining, 0)
    if total is None and used is not None and remaining is not None:
        total = used + remaining
    return total, used, remaining, unit


async def _query_mimo_quota(api_key: str) -> tuple[dict, str]:
    settings = _agent_settings()
    root = _root_from_base_url(settings.mimo_base_url)
    endpoints = [
        f"{root}/v1/dashboard/billing/credit_grants",
        f"{root}/dashboard/billing/credit_grants",
        f"{root}/v1/billing/usage",
        "https://token-plan-sgp.xiaomimimo.com/api/usage",
        "https://token-plan-sgp.xiaomimimo.com/api/quota",
        "https://token-plan-sgp.xiaomimimo.com/api/balance",
    ]
    headers = {"Authorization": f"Bearer {api_key}"}
    errors = []
    async with httpx.AsyncClient(timeout=12) as client:
        for url in endpoints:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code >= 400:
                    errors.append(f"{url} -> HTTP {resp.status_code}")
                    continue
                data = resp.json()
                if isinstance(data, dict):
                    return data, url
                errors.append(f"{url} -> 非 JSON 对象")
            except Exception as exc:
                errors.append(f"{url} -> {type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(errors[-3:]) or "未找到可用额度接口")


async def _query_generic_quota(base_url: str, api_key: str) -> tuple[dict, str]:
    root = _root_from_base_url(base_url)
    base = base_url.rstrip("/")
    endpoints = [
        f"{base}/dashboard/billing/credit_grants",
        f"{base}/billing/usage",
        f"{root}/dashboard/billing/credit_grants",
        f"{root}/v1/dashboard/billing/credit_grants",
        f"{root}/billing/usage",
        f"{root}/v1/billing/usage",
        f"{root}/quota",
        f"{root}/balance",
    ]
    headers = {"Authorization": f"Bearer {api_key}"}
    errors = []
    seen: set[str] = set()
    async with httpx.AsyncClient(timeout=12) as client:
        for url in endpoints:
            if url in seen:
                continue
            seen.add(url)
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code >= 400:
                    errors.append(f"{url} -> HTTP {resp.status_code}")
                    continue
                data = resp.json()
                if isinstance(data, dict):
                    return data, url
                errors.append(f"{url} -> 非 JSON 对象")
            except Exception as exc:
                errors.append(f"{url} -> {type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(errors[-3:]) or "未找到可用额度接口")


def _quota_response_from_payload(
    data: dict,
    source: str,
    provider_id: str,
    key_id: str,
    key_label: str,
) -> QuotaResponse:
    total, used, remaining, unit = _parse_quota_payload(data)
    percent_remaining = None
    if total and total > 0 and remaining is not None:
        percent_remaining = max(0, min(100, remaining / total * 100))
    return QuotaResponse(
        provider=provider_id,
        key_id=key_id,
        key_label=key_label,
        total=total,
        used=used,
        remaining=remaining,
        percent_remaining=percent_remaining,
        unit=unit,
        message=f"查询成功：{source}",
        raw=data,
    )


@router.post("/quota", response_model=QuotaResponse)
async def query_quota(
    request: QuotaRequest,
    user: UserContext = Depends(get_current_user),
):
    custom_base_url = (request.custom_base_url or "").strip()
    custom_api_key = (request.custom_api_key or "").strip()
    provider_id = request.provider or "custom"

    if custom_base_url and custom_api_key:
        try:
            data, source = await _query_generic_quota(custom_base_url, custom_api_key)
            return _quota_response_from_payload(
                data,
                source,
                provider_id,
                request.key_id or "custom",
                "页面自定义 Key",
            )
        except Exception as exc:
            return QuotaResponse(
                provider=provider_id,
                key_id=request.key_id or "custom",
                key_label="页面自定义 Key",
                supported=False,
                status="unsupported",
                message=f"当前 Key 未返回可解析额度信息：{exc}",
            )

    resolved = _resolve_key(provider_id, request.key_id)
    if not resolved:
        return QuotaResponse(
            provider=provider_id,
            key_id=request.key_id,
            key_label="未知 Key",
            supported=False,
            status="error",
            message="未找到对应 API Key，请检查模型供应商的 API Key 配置。",
        )

    provider, key = resolved
    if not provider.quota_supported:
        try:
            data, source = await _query_generic_quota(custom_base_url or provider.base_url, key.key)
            return _quota_response_from_payload(data, source, provider.id, key.id, key.label)
        except Exception:
            pass
        return QuotaResponse(
            provider=provider.id,
            key_id=key.id,
            key_label=key.label,
            supported=False,
            status="unsupported",
            message=f"{provider.label} 暂未配置可用的额度查询接口，仍可正常用于模型调用。",
        )

    try:
        data, source = await _query_mimo_quota(key.key)
        return _quota_response_from_payload(data, source, provider.id, request.key_id, key.label)
    except Exception as exc:
        return QuotaResponse(
            provider=provider.id,
            key_id=request.key_id,
            key_label=key.label,
            supported=False,
            status="error",
            message=f"当前服务未返回可解析额度信息：{exc}",
        )
