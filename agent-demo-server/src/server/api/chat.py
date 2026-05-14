"""
对话 API 模块

提供三个端点：
- POST /api/chat: 同步对话（等待完整回复）
- POST /api/chat/stream: 流式对话（SSE，逐 token 返回）
- GET /api/chat/history/{thread_id}: 获取会话历史

同步 vs 流式：
- 同步：简单，适合后端调用、测试
- 流式：用户体验好，适合前端实时展示
"""
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from server.models.chat import ChatRequest, ChatResponse, ChatHistoryItem
from server.deps import get_current_user, UserContext
from sqlalchemy.ext.asyncio import AsyncSession
from server.db import database
from server.db.database import get_session
from server.db.models import Conversation, MediaTask
from server.services.media_tasks import (
    classify_media_intent,
    create_media_task,
    schedule_media_task,
    task_to_response,
)
from server.agent_import import ensure_agent_on_path
from sqlalchemy import select
import json
import re
from datetime import datetime, timezone

# 创建路由器，所有路由都以 /api/chat 开头
router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_agent():
    """
    动态导入 Agent 模块

    因为 agent-demo-agent 是独立的子项目，
    需要将其 src 目录加入 Python 路径才能导入。
    这种方式避免了硬编码路径。
    """
    ensure_agent_on_path()
    from agent.main import chat, chat_stream
    return chat, chat_stream


def _json_dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def _json_loads(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_error_text(value: str) -> str:
    text = re.sub(r"(sk|ark|tp)-[A-Za-z0-9_-]{12,}", r"\1-***", value or "")
    text = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer ***", text)
    return text[:1200]


def _format_model_error(exc: Exception, request: ChatRequest) -> str:
    raw = _sanitize_error_text(str(exc) or type(exc).__name__)
    lowered = raw.lower()
    reasons = []
    is_model_not_open = (
        "modelnotopen" in lowered
        or "not activated the model" in lowered
        or "activate the model service" in lowered
    )
    is_api_not_supported = (
        "does not support this api" in lowered
        or "not support this api" in lowered
        or "unsupported api" in lowered
    )
    if is_model_not_open:
        reasons.append("账号尚未在火山方舟控制台开通该模型服务，请先在 Ark Console 激活该模型，或改用已开通的模型/推理接入点")
    elif is_api_not_supported:
        reasons.append("当前模型不是聊天对话模型，不能调用 OpenAI-compatible Chat Completions；请在设置页选择文本/代码对话模型")
    elif "timed out" in lowered or "timeout" in lowered or "readtimeout" in lowered:
        reasons.append("模型服务响应超时，供应商侧延迟波动或本地超时配置过短都可能触发")
    elif "api key" in lowered or "unauthorized" in lowered or "401" in lowered or "authentication" in lowered:
        reasons.append("API Key 无效、未生效或没有该模型权限")
    if (
        not is_model_not_open
        and not is_api_not_supported
        and ("model" in lowered or "endpoint" in lowered or "404" in lowered or "not found" in lowered)
    ):
        reasons.append("模型 ID / 火山方舟推理接入点 ID 可能填写错误")
    if not is_model_not_open and not is_api_not_supported and ("base url" in lowered or "connection" in lowered or "connect" in lowered or "404" in lowered):
        reasons.append("Base URL 可能不是 OpenAI-compatible Chat Completions 地址")
    if not is_model_not_open and not is_api_not_supported and ("quota" in lowered or "insufficient" in lowered or "429" in lowered or "rate" in lowered):
        reasons.append("额度不足、限流或并发限制")
    if not request.model:
        reasons.append("当前设置未提供模型 ID / 推理接入点 ID")
    if not reasons:
        reasons.append("模型服务返回了异常，需检查供应商配置和服务端日志")

    provider = request.model_provider or "默认供应商"
    model = request.model or "未填写"
    base_url = request.custom_base_url or "使用后端配置"
    reason_text = "；".join(dict.fromkeys(reasons))
    return (
        "模型调用失败，当前回答无法生成。\n\n"
        f"- 供应商：{provider}\n"
        f"- 模型/推理接入点：{model}\n"
        f"- Base URL：{base_url}\n"
        f"- 可能原因：{reason_text}\n"
        f"- 原始错误：{raw}\n\n"
        "请到设置页检查 API Key、Base URL，以及火山方舟的模型 ID 或推理接入点 ID。"
    )


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    同步对话端点

    流程：
    1. 接收用户消息
    2. 调用 Agent 获取回复
    3. 将用户消息和 Agent 回复都保存到数据库
    4. 返回回复内容

    Args:
        request: 包含 message, thread_id, enable_tts
        user: 当前用户上下文（通过依赖注入）
        session: 数据库会话（通过依赖注入）

    Returns:
        ChatResponse: 包含 content, emotion, thread_id
    """
    chat_fn, _ = _get_agent()

    # 组合 thread_id：用户ID_会话ID，用于隔离不同用户的对话
    thread_id = f"{user.user_id}_{request.thread_id}"

    # 调用 Agent
    # thread_id: 短期记忆隔离键（Checkpointer 按此加载对话历史）
    # user_id: 长期记忆隔离键（按用户读取偏好和事实）
    try:
        result = await chat_fn(
            request.message,
            thread_id=thread_id,
            user_id=user.user_id,
            images=request.images,
            model_provider=request.model_provider,
            model=request.model,
            api_key_id=request.api_key_id,
            custom_base_url=request.custom_base_url,
            custom_api_key=request.custom_api_key,
        )
    except Exception as exc:
        result = {
            "content": _format_model_error(exc, request),
            "emotion": "neutral",
        }

    # 保存对话记录到数据库
    # 先保存用户消息，再保存 Agent 回复
    for role, content, emotion in [
        ("user", request.message, None),
        ("assistant", result["content"], result["emotion"]),
    ]:
        conv = Conversation(
            thread_id=thread_id,
            user_id=user.user_id,
            role=role,
            content=content,
            emotion=emotion,
        )
        session.add(conv)
    await session.commit()

    return ChatResponse(
        content=result["content"],
        emotion=result["emotion"],
        thread_id=request.thread_id,
    )


@router.post("/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    user: UserContext = Depends(get_current_user),
):
    """
    流式对话端点（SSE）

    使用 Server-Sent Events (SSE) 实现流式输出。
    SSE 是一种服务器向客户端推送数据的技术，
    比 WebSocket 更轻量，适合单向数据流。

    事件类型：
    - emotion: 情绪分析结果
    - token: LLM 生成的文本片段
    - tool_start: 工具开始调用
    - tool_end: 工具调用完成
    - done: 对话结束
    """
    thread_id = f"{user.user_id}_{request.thread_id}"

    async def event_generator():
        """
        SSE 事件生成器

        将 Agent 的流式输出转换为 SSE 格式。
        SSE 格式：event: {type}\ndata: {json}\n\n
        """
        full_content = ""
        emotion = None
        thoughts: list[dict] = []
        tool_calls: list[dict] = []
        citations: list[dict] = []
        media_tasks: list[dict] = []

        async def save_turn():
            if not full_content:
                return
            try:
                assistant_metadata = {
                    "thoughts": thoughts,
                    "toolCalls": tool_calls,
                    "citations": citations,
                    "mediaTasks": media_tasks,
                }
                async with database.async_session() as db:
                    for role, content, emo, metadata in [
                        ("user", request.message, None, None),
                        ("assistant", full_content, emotion, _json_dumps(assistant_metadata)),
                    ]:
                        db.add(Conversation(
                            thread_id=thread_id,
                            user_id=user.user_id,
                            role=role,
                            content=content,
                            emotion=emo,
                            message_metadata=metadata,
                        ))
                    await db.commit()
            except Exception:
                pass

        try:
            media_intent = await classify_media_intent(request)
            if media_intent:
                emotion = "neutral"
                full_content = "已创建媒体生成任务。生成期间你可以继续在当前会话里提问，我会在完成后通知你。"
                thoughts.append({"text": "小模型已识别为媒体生成请求，正在创建异步任务。", "timestamp": _now_iso()})
                async with database.async_session() as db:
                    user_conv = Conversation(
                        thread_id=thread_id,
                        user_id=user.user_id,
                        role="user",
                        content=request.message,
                    )
                    assistant_conv = Conversation(
                        thread_id=thread_id,
                        user_id=user.user_id,
                        role="assistant",
                        content=full_content,
                        emotion=emotion,
                    )
                    db.add(user_conv)
                    db.add(assistant_conv)
                    await db.flush()
                    task = await create_media_task(
                        db,
                        request=request,
                        user_id=user.user_id,
                        full_thread_id=thread_id,
                        conversation_id=assistant_conv.id,
                        detected=media_intent,
                    )
                    task_dict = task_to_response(task, user.user_id).model_dump(mode="json")
                    media_tasks.append(task_dict)
                    assistant_conv.message_metadata = _json_dumps({
                        "thoughts": thoughts,
                        "toolCalls": tool_calls,
                        "citations": citations,
                        "mediaTasks": media_tasks,
                    })
                    await db.commit()

                schedule_media_task(task.id)
                yield {"event": "emotion", "data": json.dumps(emotion, ensure_ascii=False)}
                yield {
                    "event": "thought",
                    "data": json.dumps("媒体生成任务已创建，后台正在处理。", ensure_ascii=False),
                }
                yield {
                    "event": "media_task",
                    "data": json.dumps(task_dict, ensure_ascii=False),
                }
                yield {"event": "token", "data": json.dumps(full_content, ensure_ascii=False)}
                yield {"event": "done", "data": json.dumps("", ensure_ascii=False)}
                return

            _, chat_stream_fn = _get_agent()
            async for event in chat_stream_fn(
                request.message,
                thread_id=thread_id,
                user_id=user.user_id,
                images=request.images,
                model_provider=request.model_provider,
                model=request.model,
                api_key_id=request.api_key_id,
                custom_base_url=request.custom_base_url,
                custom_api_key=request.custom_api_key,
            ):
                # 收到 done 事件时，先保存再 yield
                if event["type"] == "done" and full_content:
                    await save_turn()

                yield {
                    "event": event["type"],
                    "data": json.dumps(event["data"], ensure_ascii=False),
                }
                if event["type"] == "token":
                    full_content += event["data"]
                elif event["type"] == "emotion":
                    emotion = event["data"]
                elif event["type"] == "thought":
                    thoughts.append({"text": str(event["data"]), "timestamp": _now_iso()})
                elif event["type"] == "citation" and isinstance(event["data"], dict):
                    chunk_id = event["data"].get("chunk_id")
                    if chunk_id and not any(item.get("chunk_id") == chunk_id for item in citations):
                        citations.append(event["data"])
                elif event["type"] == "tool_start" and isinstance(event["data"], dict):
                    tool_input = event["data"].get("input", "")
                    if isinstance(tool_input, (dict, list)):
                        tool_input = json.dumps(tool_input, ensure_ascii=False, indent=2)
                    tool_calls.append({
                        "name": event["data"].get("name", ""),
                        "input": str(tool_input or ""),
                    })
                elif event["type"] == "tool_end" and isinstance(event["data"], dict):
                    tool_name = event["data"].get("name")
                    output = str(event["data"].get("output", ""))
                    target = None
                    for item in reversed(tool_calls):
                        if not tool_name or item.get("name") == tool_name:
                            target = item
                            break
                    if target is None:
                        target = {"name": str(tool_name or ""), "input": ""}
                        tool_calls.append(target)
                    target["output"] = output
        except Exception as exc:
            error_text = _format_model_error(exc, request)
            full_content = full_content or error_text
            thoughts.append({"text": "模型调用失败，已将错误信息写入回答正文。", "timestamp": _now_iso()})
            if not emotion:
                emotion = "neutral"
            yield {
                "event": "thought",
                "data": json.dumps("模型调用失败，正在展示错误详情。", ensure_ascii=False),
            }
            yield {
                "event": "error",
                "data": json.dumps({"message": error_text}, ensure_ascii=False),
            }
            yield {
                "event": "token",
                "data": json.dumps(error_text, ensure_ascii=False),
            }
            await save_turn()
            yield {
                "event": "done",
                "data": json.dumps("", ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())


@router.get("/history/{thread_id}", response_model=list[ChatHistoryItem])
async def get_history(
    thread_id: str,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    获取会话历史

    从数据库中查询指定会话的所有消息，按时间排序返回。

    Args:
        thread_id: 会话线程 ID
        user: 当前用户
        session: 数据库会话

    Returns:
        消息历史列表
    """
    # 组合完整的 thread_id
    full_thread_id = f"{user.user_id}_{thread_id}"

    # 查询数据库
    result = await session.execute(
        select(Conversation)
        .where(Conversation.thread_id == full_thread_id)
        .order_by(Conversation.created_at)  # 按时间正序
    )
    rows = result.scalars().all()
    media_by_conversation: dict[int, list[dict]] = {}
    conversation_ids = [row.id for row in rows if row.role == "assistant"]
    if conversation_ids:
        media_result = await session.execute(
            select(MediaTask).where(
                MediaTask.user_id == user.user_id,
                MediaTask.thread_id == full_thread_id,
                MediaTask.conversation_id.in_(conversation_ids),
            )
        )
        for task in media_result.scalars().all():
            if task.conversation_id is None:
                continue
            media_by_conversation.setdefault(task.conversation_id, []).append(
                task_to_response(task, user.user_id).model_dump(mode="json")
            )

    # 转换为 API 响应格式
    history_items = []
    for r in rows:
        # message_metadata 是可选结构化展示信息；旧消息没有也应正常展示。
        metadata = _json_loads(r.message_metadata)
        history_items.append(ChatHistoryItem(
            id=str(r.id),
            role=r.role,
            content=r.content,
            timestamp=r.created_at,
            emotion=r.emotion,
            thoughts=metadata.get("thoughts", []),
            toolCalls=metadata.get("toolCalls", []),
            citations=metadata.get("citations", []),
            mediaTasks=media_by_conversation.get(r.id, metadata.get("mediaTasks", [])),
        ))
    return history_items
