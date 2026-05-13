"""
模型供应商配置解析。

当前对话模型都通过 OpenAI-compatible Chat Completions 接入。
内置 MiMo 与火山方舟，其他供应商可通过 MODEL_PROVIDERS JSON 扩展。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from agent.config import get_settings


@dataclass
class ApiKeyOption:
    id: str
    label: str
    key: str


@dataclass
class ModelOption:
    id: str
    label: str
    purpose: str = "chat"


@dataclass
class ProviderOption:
    id: str
    label: str
    base_url: str
    keys: list[ApiKeyOption]
    models: list[ModelOption]
    default_model: str = ""
    fast_model: str = ""
    omni_model: str = ""
    quota_supported: bool = False


@dataclass
class ResolvedModelConfig:
    provider_id: str
    provider_label: str
    model: str
    api_key: str
    base_url: str
    key_id: str
    key_label: str


def mask_key(value: str) -> str:
    if not value:
        return "未配置"
    if len(value) <= 10:
        return value[:2] + "***" + value[-2:]
    return value[:6] + "..." + value[-4:]


def _parse_key_entries(raw: str, env_prefix: str = "") -> list[ApiKeyOption]:
    entries: list[ApiKeyOption] = []
    raw = (raw or "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for idx, item in enumerate(parsed):
                    if isinstance(item, dict) and item.get("key"):
                        key_id = str(item.get("id") or f"extra_{idx + 1}")
                        label = str(item.get("label") or key_id)
                        entries.append(ApiKeyOption(key_id, label, str(item["key"])))
                    elif isinstance(item, str):
                        entries.append(ApiKeyOption(f"extra_{idx + 1}", f"备用 Key {idx + 1}", item))
            elif isinstance(parsed, dict):
                for key_id, key_value in parsed.items():
                    if key_value:
                        entries.append(ApiKeyOption(str(key_id), str(key_id), str(key_value)))
        except Exception:
            for idx, part in enumerate(raw.split(",")):
                part = part.strip()
                if not part:
                    continue
                if ":" in part:
                    label, key = part.split(":", 1)
                    key_id = label.strip() or f"extra_{idx + 1}"
                    entries.append(ApiKeyOption(key_id, key_id, key.strip()))
                else:
                    entries.append(ApiKeyOption(f"extra_{idx + 1}", f"备用 Key {idx + 1}", part))

    if env_prefix:
        for name, value in os.environ.items():
            if name.startswith(env_prefix) and value:
                entries.append(ApiKeyOption(name.lower(), name, value))
    return entries


def _dedupe_keys(keys: list[ApiKeyOption]) -> list[ApiKeyOption]:
    seen: set[str] = set()
    result: list[ApiKeyOption] = []
    for key in keys:
        if key.id in seen or not key.key:
            continue
        seen.add(key.id)
        result.append(key)
    return result


def _model_option(model_id: str, label: str, purpose: str = "chat") -> ModelOption | None:
    model_id = (model_id or "").strip()
    if not model_id:
        return None
    return ModelOption(id=model_id, label=label or model_id, purpose=purpose)


def _builtin_mimo_provider() -> ProviderOption:
    settings = get_settings()
    keys: list[ApiKeyOption] = []
    if settings.mimo_api_key:
        keys.append(ApiKeyOption("default", "默认 MiMo Key", settings.mimo_api_key))
    keys.extend(_parse_key_entries(settings.mimo_api_keys, "MIMO_API_KEY_"))

    models = [
        item for item in [
            _model_option(settings.mimo_model, "MiMo v2.5 Pro", "chat"),
            _model_option(settings.mimo_model_fast, "MiMo v2 Flash", "fast"),
            _model_option(settings.mimo_model_omni, "MiMo v2 Omni", "omni"),
        ]
        if item is not None
    ]
    return ProviderOption(
        id="mimo",
        label="MiMo",
        base_url=settings.mimo_base_url,
        keys=_dedupe_keys(keys),
        models=models,
        default_model=settings.mimo_model,
        fast_model=settings.mimo_model_fast,
        omni_model=settings.mimo_model_omni,
        quota_supported=True,
    )


def _builtin_ark_provider() -> ProviderOption | None:
    settings = get_settings()
    api_key = settings.ark_api_key or settings.volcengine_api_key
    api_keys = settings.ark_api_keys or settings.volcengine_api_keys
    base_url = settings.volcengine_base_url or settings.ark_base_url
    model = settings.ark_model or settings.volcengine_model
    fast_model = settings.ark_model_fast or settings.volcengine_model_fast or model
    omni_model = settings.ark_model_omni or settings.volcengine_model_omni or model

    keys: list[ApiKeyOption] = []
    if api_key:
        keys.append(ApiKeyOption("default", "默认火山方舟 Key", api_key))
    keys.extend(_parse_key_entries(api_keys, "ARK_API_KEY_"))
    keys.extend(_parse_key_entries("", "VOLCENGINE_API_KEY_"))

    models = [
        item for item in [
            _model_option(model, model or "火山方舟模型", "chat"),
            _model_option(fast_model if fast_model != model else "", fast_model, "fast"),
            _model_option(omni_model if omni_model != model else "", omni_model, "omni"),
        ]
        if item is not None
    ]
    if not keys and not models:
        return None
    return ProviderOption(
        id="volcengine",
        label="火山方舟",
        base_url=base_url or "https://ark.cn-beijing.volces.com/api/v3",
        keys=_dedupe_keys(keys),
        models=models,
        default_model=model,
        fast_model=fast_model,
        omni_model=omni_model,
        quota_supported=False,
    )


def _parse_model_item(item: Any) -> ModelOption | None:
    if isinstance(item, str):
        return ModelOption(id=item, label=item)
    if not isinstance(item, dict):
        return None
    model_id = str(item.get("id") or item.get("model") or "").strip()
    if not model_id:
        return None
    return ModelOption(
        id=model_id,
        label=str(item.get("label") or item.get("name") or model_id),
        purpose=str(item.get("purpose") or "chat"),
    )


def _parse_custom_providers() -> list[ProviderOption]:
    settings = get_settings()
    raw = (settings.model_providers or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []

    providers: list[ProviderOption] = []
    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        provider_id = str(item.get("id") or f"custom_{idx + 1}").strip()
        base_url = str(item.get("base_url") or item.get("baseUrl") or "").strip()
        if not provider_id or not base_url:
            continue

        keys: list[ApiKeyOption] = []
        if item.get("api_key"):
            keys.append(ApiKeyOption("default", "默认 Key", str(item["api_key"])))
        if isinstance(item.get("keys"), list):
            for key_idx, key_item in enumerate(item["keys"]):
                if isinstance(key_item, dict) and key_item.get("key"):
                    keys.append(ApiKeyOption(
                        str(key_item.get("id") or f"extra_{key_idx + 1}"),
                        str(key_item.get("label") or key_item.get("id") or f"备用 Key {key_idx + 1}"),
                        str(key_item["key"]),
                    ))
                elif isinstance(key_item, str):
                    keys.append(ApiKeyOption(f"extra_{key_idx + 1}", f"备用 Key {key_idx + 1}", key_item))

        models = [_parse_model_item(model) for model in item.get("models", [])]
        models = [model for model in models if model is not None]
        default_model = str(item.get("default_model") or item.get("defaultModel") or (models[0].id if models else ""))
        providers.append(ProviderOption(
            id=provider_id,
            label=str(item.get("label") or item.get("name") or provider_id),
            base_url=base_url,
            keys=_dedupe_keys(keys),
            models=models,
            default_model=default_model,
            fast_model=str(item.get("fast_model") or item.get("fastModel") or default_model),
            omni_model=str(item.get("omni_model") or item.get("omniModel") or default_model),
            quota_supported=bool(item.get("quota_supported") or item.get("quotaSupported") or False),
        ))
    return providers


def list_model_providers() -> list[ProviderOption]:
    providers = [_builtin_mimo_provider()]
    ark = _builtin_ark_provider()
    if ark:
        providers.append(ark)

    custom = _parse_custom_providers()
    existing = {provider.id for provider in providers}
    for provider in custom:
        if provider.id in existing:
            providers = [provider if item.id == provider.id else item for item in providers]
        else:
            providers.append(provider)
            existing.add(provider.id)
    return providers


def _pick_provider(provider_id: str | None = None) -> ProviderOption:
    settings = get_settings()
    providers = list_model_providers()
    target_id = provider_id or settings.default_model_provider
    for provider in providers:
        if provider.id == target_id:
            return provider
    for provider in providers:
        if provider.keys and provider.models:
            return provider
    return providers[0]


def resolve_model_config(
    provider_id: str | None = None,
    model_id: str | None = None,
    key_id: str | None = None,
    purpose: str = "chat",
) -> ResolvedModelConfig:
    settings = get_settings()
    provider = _pick_provider(provider_id)
    key = next((item for item in provider.keys if item.id == key_id), None)
    if key is None and provider.keys:
        key = provider.keys[0]
    if key is None:
        raise ValueError(f"模型供应商 {provider.label} 未配置 API Key")

    selected_model = (model_id or "").strip()
    if not selected_model:
        if purpose == "fast":
            selected_model = provider.fast_model
        elif purpose == "omni":
            selected_model = provider.omni_model
        selected_model = selected_model or settings.default_model or provider.default_model
    if not selected_model and provider.models:
        selected_model = provider.models[0].id
    if not selected_model:
        raise ValueError(f"模型供应商 {provider.label} 未配置模型")

    return ResolvedModelConfig(
        provider_id=provider.id,
        provider_label=provider.label,
        model=selected_model,
        api_key=key.key,
        base_url=provider.base_url,
        key_id=key.id,
        key_label=key.label,
    )
