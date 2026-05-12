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
from server.db.models import Conversation
from server.agent_import import ensure_agent_on_path
from sqlalchemy import select
import json

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
    result = await chat_fn(request.message, thread_id=thread_id, user_id=user.user_id, images=request.images)

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
    _, chat_stream_fn = _get_agent()
    thread_id = f"{user.user_id}_{request.thread_id}"

    async def event_generator():
        """
        SSE 事件生成器

        将 Agent 的流式输出转换为 SSE 格式。
        SSE 格式：event: {type}\ndata: {json}\n\n
        """
        full_content = ""
        emotion = None
        async for event in chat_stream_fn(request.message, thread_id=thread_id, user_id=user.user_id, images=request.images):
            # 收到 done 事件时，先保存再 yield
            if event["type"] == "done" and full_content:
                try:
                    async with database.async_session() as db:
                        for role, content, emo in [
                            ("user", request.message, None),
                            ("assistant", full_content, emotion),
                        ]:
                            db.add(Conversation(
                                thread_id=thread_id,
                                user_id=user.user_id,
                                role=role,
                                content=content,
                                emotion=emo,
                            ))
                        await db.commit()
                except Exception:
                    pass

            yield {
                "event": event["type"],
                "data": json.dumps(event["data"], ensure_ascii=False),
            }
            if event["type"] == "token":
                full_content += event["data"]
            elif event["type"] == "emotion":
                emotion = event["data"]

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

    # 转换为 API 响应格式
    return [
        ChatHistoryItem(
            role=r.role,
            content=r.content,
            timestamp=r.created_at,
            emotion=r.emotion,
        )
        for r in rows
    ]
