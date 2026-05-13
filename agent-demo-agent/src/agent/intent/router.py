from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from agent.model_providers import list_model_providers


@dataclass
class IntentRoutingRequest:
    message: str
    images: list[str] | None = None
    model_provider: str | None = None
    model: str | None = None
    api_key_id: str | None = None
    custom_base_url: str | None = None
    custom_api_key: str | None = None


@dataclass
class IntentRoute:
    task_type: str
    mode: str

    def as_dict(self) -> dict[str, str]:
        return {"task_type": self.task_type, "mode": self.mode}


def detect_media_request(message: str, images: list[str] | None = None) -> IntentRoute | None:
    text = (message or "").strip()
    lowered = text.lower()
    has_images = bool(images)
    capability_question = (
        any(mark in text for mark in ["吗", "么", "嘛", "？", "?"])
        and any(word in text for word in ["能", "可以", "会", "支持", "具备"])
        and any(word in text for word in ["图片", "视频", "image", "video"])
        and not any(word in text for word in ["生成图片：", "生成视频：", "画一张：", "做个视频："])
    )
    if capability_question:
        return None

    image_hit = any(word in text for word in ["生成图片", "画一张", "画个", "出一张图", "做一张图", "图片生成", "文生图", "图生图"])
    video_hit = any(word in text for word in ["生成视频", "做个视频", "出个视频", "文生视频", "图生视频", "视频生成", "短视频"])
    image_hit = image_hit and not any(word in text for word in ["能生成图片", "可以生成图片", "支持生成图片"])
    video_hit = video_hit and not any(word in text for word in ["能生成视频", "可以生成视频", "支持生成视频"])
    if "image" in lowered and any(word in lowered for word in ["generate", "create", "edit"]) and "can you" not in lowered:
        image_hit = True
    if "video" in lowered and any(word in lowered for word in ["generate", "create"]) and "can you" not in lowered:
        video_hit = True
    if video_hit:
        if has_images and text:
            mode = "image_text_to_video"
        elif has_images:
            mode = "image_to_video"
        else:
            mode = "text_to_video"
        return IntentRoute("video", mode)
    if image_hit:
        mode = "image_to_image" if has_images else "text_to_image"
        return IntentRoute("image", mode)
    return None


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _resolve_chat_provider(request: IntentRoutingRequest) -> dict[str, str]:
    provider_id = request.model_provider or "volcengine"
    if request.custom_base_url and request.custom_api_key:
        return {
            "provider_id": provider_id,
            "model": request.model or "",
            "api_key": request.custom_api_key,
            "base_url": request.custom_base_url.rstrip("/"),
        }

    for provider in list_model_providers():
        if provider.id != provider_id:
            continue
        key = None
        for candidate in provider.keys:
            if request.api_key_id and candidate.id == request.api_key_id:
                key = candidate
                break
        key = key or (provider.keys[0] if provider.keys else None)
        if not key:
            break
        return {
            "provider_id": provider.id,
            "model": provider.fast_model or request.model or provider.default_model,
            "api_key": key.key,
            "base_url": provider.base_url.rstrip("/"),
        }

    return {
        "provider_id": provider_id,
        "model": request.model or "",
        "api_key": request.custom_api_key or "",
        "base_url": (request.custom_base_url or "").rstrip("/"),
    }


async def classify_media_intent(request: IntentRoutingRequest) -> IntentRoute | None:
    fallback = detect_media_request(request.message, request.images)
    resolved = _resolve_chat_provider(request)
    if not resolved["api_key"] or not resolved["base_url"] or not resolved["model"]:
        return fallback

    user_text = (request.message or "").strip()
    has_images = bool(request.images)
    system_prompt = (
        "你是一个严格的意图分类器，只输出 JSON。"
        "判断用户是否在明确请求创建图片或视频生成任务。"
        "能力咨询、用法咨询、是否支持、闲聊、翻译、总结、写提示词都不是生成任务。"
        "只有用户明确要求现在生成/画/做/出图片或视频时才判定为任务。"
        "输出格式：{\"intent\":\"none|image|video\",\"mode\":\"none|text_to_image|image_to_image|text_to_video|image_to_video|image_text_to_video\"}。"
    )
    content = (
        f"用户输入：{user_text}\n"
        f"是否带图片：{has_images}\n"
        "请只输出 JSON。"
    )
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            resp = await client.post(
                f"{resolved['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {resolved['api_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": resolved["model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content},
                    ],
                    "temperature": 0,
                    "max_tokens": 80,
                },
            )
            if resp.status_code >= 400:
                return fallback
            data = resp.json()
    except Exception:
        return fallback

    answer = str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
    parsed = _extract_json_object(answer)
    intent = str(parsed.get("intent") or "none").lower()
    mode = str(parsed.get("mode") or "none").lower()
    if intent not in {"image", "video"}:
        return None
    valid_modes = {
        "image": {"text_to_image", "image_to_image"},
        "video": {"text_to_video", "image_to_video", "image_text_to_video"},
    }
    if mode not in valid_modes[intent]:
        if intent == "image":
            mode = "image_to_image" if has_images else "text_to_image"
        else:
            mode = "image_text_to_video" if has_images and user_text else ("image_to_video" if has_images else "text_to_video")
    return IntentRoute(intent, mode)
