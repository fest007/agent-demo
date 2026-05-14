from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.agent_import import ensure_agent_on_path
from server.db import database
from server.db.models import MediaTask
from server.models.chat import ChatRequest
from server.models.media import MediaTaskResponse


IMAGE_MODELS = {
    "volcengine": "doubao-seedream-5-0-260128",
}
VIDEO_MODELS = {
    "volcengine": "doubao-seedance-1-5-pro-251215",
}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str | None, fallback: Any):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _sanitize_error_text(value: str) -> str:
    text = re.sub(r"(sk|ark|tp)-[A-Za-z0-9_-]{12,}", r"\1-***", value or "")
    text = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer ***", text)
    return text[:1600]


def _strip_user_prefix(full_thread_id: str, user_id: str) -> str:
    prefix = f"{user_id}_"
    return full_thread_id[len(prefix):] if full_thread_id.startswith(prefix) else full_thread_id


def task_to_response(task: MediaTask, user_id: str) -> MediaTaskResponse:
    return MediaTaskResponse(
        id=task.id,
        thread_id=_strip_user_prefix(task.thread_id, user_id),
        conversation_id=task.conversation_id,
        provider=task.provider,
        model=task.model,
        task_type=task.task_type,
        mode=task.mode,
        prompt=task.prompt,
        status=task.status,
        progress=task.progress or 0,
        external_task_id=task.external_task_id,
        input_images=_json_loads(task.input_images, []),
        result_urls=_json_loads(task.result_urls, []),
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
    )


async def classify_media_intent(request: ChatRequest) -> dict[str, str] | None:
    ensure_agent_on_path()
    from agent.intent import IntentRoutingRequest, classify_media_intent as classify_agent_intent

    route = await classify_agent_intent(IntentRoutingRequest(
        message=request.message,
        images=request.images,
        model_provider=request.model_provider,
        model=request.model,
        api_key_id=request.api_key_id,
        custom_base_url=request.custom_base_url,
        custom_api_key=request.custom_api_key,
    ))
    return route.as_dict() if route else None


def _resolve_provider(request: ChatRequest, task_type: str) -> dict[str, str]:
    ensure_agent_on_path()
    from agent.config import get_settings
    from agent.model_providers import list_model_providers, resolve_model_config

    provider_id = request.model_provider or get_settings().default_model_provider
    requested_model = request.image_model if task_type == "image" else request.video_model
    model = requested_model or request.model or ""
    if task_type == "image" and (not model or "seedance" in model or "code" in model):
        model = IMAGE_MODELS.get(provider_id, model)
    if task_type == "video" and (not model or "seedream" in model or "code" in model):
        model = VIDEO_MODELS.get(provider_id, model)

    if request.custom_base_url and request.custom_api_key:
        return {
            "provider_id": provider_id,
            "model": model,
            "api_key": request.custom_api_key,
            "base_url": request.custom_base_url.rstrip("/"),
        }

    try:
        resolved = resolve_model_config(
            provider_id=provider_id,
            model_id=model,
            key_id=request.api_key_id,
            purpose="chat",
        )
        return {
            "provider_id": resolved.provider_id,
            "model": resolved.model,
            "api_key": resolved.api_key,
            "base_url": resolved.base_url.rstrip("/"),
        }
    except Exception:
        pass

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
            "model": model or (IMAGE_MODELS.get(provider.id) if task_type == "image" else VIDEO_MODELS.get(provider.id) or provider.default_model),
            "api_key": key.key,
            "base_url": provider.base_url.rstrip("/"),
        }

    return {
        "provider_id": provider_id,
        "model": model,
        "api_key": request.custom_api_key or "",
        "base_url": (request.custom_base_url or "").rstrip("/"),
    }


async def create_media_task(
    db: AsyncSession,
    *,
    request: ChatRequest,
    user_id: str,
    full_thread_id: str,
    conversation_id: int | None = None,
    detected: dict[str, str] | None = None,
) -> MediaTask:
    if detected is None:
        detected = await classify_media_intent(request)
    if not detected:
        raise ValueError("不是媒体生成请求")

    resolved = _resolve_provider(request, detected["task_type"])
    task = MediaTask(
        id=uuid.uuid4().hex,
        user_id=user_id,
        thread_id=full_thread_id,
        conversation_id=conversation_id,
        provider=resolved["provider_id"],
        model=resolved["model"],
        task_type=detected["task_type"],
        mode=detected["mode"],
        prompt=(request.message or "").strip() or "根据输入图片生成",
        status="pending",
        progress=1,
        input_images=_json_dumps(request.images or []),
        request_payload=_json_dumps({
            "base_url": resolved["base_url"],
            "api_key": resolved["api_key"],
        }),
    )
    db.add(task)
    await db.flush()
    return task


def schedule_media_task(task_id: str):
    asyncio.create_task(run_media_task(task_id))


async def run_media_task(task_id: str):
    async with database.async_session() as db:
        result = await db.execute(select(MediaTask).where(MediaTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return
        task.status = "running"
        task.progress = max(task.progress or 0, 8)
        await db.commit()

    try:
        async with database.async_session() as db:
            result = await db.execute(select(MediaTask).where(MediaTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return
            payload = _json_loads(task.request_payload, {})
            if task.task_type == "image":
                urls = await _generate_image(task, payload)
            elif task.task_type == "video":
                urls = await _generate_video(task, payload)
            else:
                raise RuntimeError(f"不支持的媒体任务类型：{task.task_type}")
            task.result_urls = _json_dumps(urls)
            task.status = "succeeded"
            task.progress = 100
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception as exc:
        async with database.async_session() as db:
            result = await db.execute(select(MediaTask).where(MediaTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return
            task.status = "failed"
            task.progress = 100
            task.error = _sanitize_error_text(str(exc) or type(exc).__name__)
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()


async def _generate_image(task: MediaTask, auth_payload: dict[str, str]) -> list[str]:
    api_key = auth_payload.get("api_key") or ""
    base_url = (auth_payload.get("base_url") or "").rstrip("/")
    if not api_key or not base_url:
        raise RuntimeError("缺少图片生成 API Key 或 Base URL")

    prompt = task.prompt
    input_images = _json_loads(task.input_images, [])
    if input_images:
        prompt = f"{prompt}\n请参考用户上传的图片，保持主体特征并完成图像生成。"

    payload = {
        "model": task.model,
        "prompt": prompt,
        "size": "2048x2048",
        "response_format": "url",
    }
    if input_images:
        payload["image"] = input_images
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{base_url}/images/generations",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code >= 400:
            raise RuntimeError(resp.text[:1200])
        data = resp.json()
    urls = [item.get("url") for item in data.get("data", []) if isinstance(item, dict) and item.get("url")]
    if not urls:
        raise RuntimeError(f"图片生成完成但未返回图片地址：{str(data)[:600]}")
    return urls


async def _generate_video(task: MediaTask, auth_payload: dict[str, str]) -> list[str]:
    api_key = auth_payload.get("api_key") or ""
    base_url = (auth_payload.get("base_url") or "").rstrip("/")
    if not api_key or not base_url:
        raise RuntimeError("缺少视频生成 API Key 或 Base URL")

    content: list[dict[str, Any]] = [{"type": "text", "text": task.prompt}]
    input_images = _json_loads(task.input_images, [])
    for index, image in enumerate(input_images):
        image_item: dict[str, Any] = {"type": "image_url", "image_url": {"url": image}}
        if len(input_images) == 1:
            image_item["role"] = "first_frame"
        elif index == 0:
            image_item["role"] = "first_frame"
        elif index == 1:
            image_item["role"] = "last_frame"
        else:
            image_item["role"] = "reference_image"
        content.append(image_item)

    async with httpx.AsyncClient(timeout=60) as client:
        create_resp = await client.post(
            f"{base_url}/contents/generations/tasks",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": task.model,
                "content": content,
                "resolution": "720p",
                "ratio": "adaptive",
                "duration": 5,
                "camera_fixed": False,
                "watermark": True,
            },
        )
        if create_resp.status_code >= 400:
            raise RuntimeError(create_resp.text[:1200])
        created = create_resp.json()
        external_id = str(created.get("id") or created.get("task_id") or created.get("data", {}).get("id") or "")
        if not external_id:
            raise RuntimeError(f"视频任务创建成功但未返回任务 ID：{str(created)[:600]}")

        async with database.async_session() as db:
            result = await db.execute(select(MediaTask).where(MediaTask.id == task.id))
            current = result.scalar_one_or_none()
            if current:
                current.external_task_id = external_id
                current.progress = 12
                await db.commit()

        for index in range(120):
            await asyncio.sleep(5)
            query_resp = await client.get(
                f"{base_url}/contents/generations/tasks/{external_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if query_resp.status_code >= 400:
                raise RuntimeError(query_resp.text[:1200])
            data = query_resp.json()
            status = str(data.get("status") or data.get("data", {}).get("status") or "").lower()
            progress = min(95, 12 + index)
            async with database.async_session() as db:
                result = await db.execute(select(MediaTask).where(MediaTask.id == task.id))
                current = result.scalar_one_or_none()
                if current:
                    current.progress = progress
                    await db.commit()
            if status in {"succeeded", "success", "completed", "done"}:
                urls = _extract_video_urls(data)
                if not urls:
                    raise RuntimeError(f"视频生成完成但未返回视频地址：{str(data)[:900]}")
                return urls
            if status in {"failed", "error", "canceled", "cancelled"}:
                raise RuntimeError(str(data.get("error") or data.get("message") or data)[:1200])

    raise RuntimeError("视频生成超时，请稍后刷新查看任务状态")


def _extract_video_urls(data: Any) -> list[str]:
    urls: list[str] = []

    def walk(value: Any):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"url", "video_url", "content_url"} and isinstance(item, str) and item.startswith("http"):
                    urls.append(item)
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(data)
    return list(dict.fromkeys(urls))
