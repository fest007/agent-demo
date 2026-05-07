"""
会话管理 API 模块

提供会话的 CRUD 和 LLM 总结命名接口：
- POST /api/sessions: 创建新会话
- GET /api/sessions: 列出所有会话
- PUT /api/sessions/{session_id}: 更新会话名称
- DELETE /api/sessions/{session_id}: 删除会话及关联对话
- POST /api/sessions/{session_id}/summarize: LLM 总结命名
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from server.models.session import SessionResponse, SessionUpdate
from server.db.models import Session as SessionModel, Conversation
from server.db.database import get_session
from server.deps import get_current_user, UserContext

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
async def create_session(
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """创建新会话，自动生成 UUID，名称默认为"新对话" """
    session_id = str(uuid.uuid4())
    new_session = SessionModel(
        session_id=session_id,
        user_id=user.user_id,
        name="新对话",
    )
    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)
    return new_session


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """列出当前用户所有会话，按更新时间倒序"""
    result = await session.execute(
        select(SessionModel)
        .where(SessionModel.user_id == user.user_id)
        .order_by(SessionModel.updated_at.desc())
    )
    return result.scalars().all()


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    body: SessionUpdate,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """更新会话名称"""
    result = await session.execute(
        select(SessionModel)
        .where(SessionModel.session_id == session_id, SessionModel.user_id == user.user_id)
    )
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="会话不存在")
    sess.name = body.name
    await session.commit()
    await session.refresh(sess)
    return sess


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """删除会话及其所有关联对话记录"""
    result = await session.execute(
        select(SessionModel)
        .where(SessionModel.session_id == session_id, SessionModel.user_id == user.user_id)
    )
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 删除关联的对话记录
    full_thread_id = f"{user.user_id}_{session_id}"
    await session.execute(
        delete(Conversation).where(Conversation.thread_id == full_thread_id)
    )

    await session.delete(sess)
    await session.commit()
    return {"status": "success"}


@router.post("/{session_id}/summarize", response_model=SessionResponse)
async def summarize_session(
    session_id: str,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    用 LLM 总结第一轮对话，生成 ≤8 字的会话名称

    流程：
    1. 查询该会话的前 2 条消息（用户 + 助手）
    2. 调用 LLM 生成简短概括
    3. 更新会话名称
    """
    # 查找会话
    result = await session.execute(
        select(SessionModel)
        .where(SessionModel.session_id == session_id, SessionModel.user_id == user.user_id)
    )
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 查询前 2 条消息
    full_thread_id = f"{user.user_id}_{session_id}"
    msg_result = await session.execute(
        select(Conversation)
        .where(Conversation.thread_id == full_thread_id)
        .order_by(Conversation.created_at)
        .limit(2)
    )
    messages = msg_result.scalars().all()

    if len(messages) == 0:
        return sess

    # 构建总结提示词
    user_msg = ""
    assistant_msg = ""
    for m in messages:
        if m.role == "user":
            user_msg = m.content[:200]
        elif m.role == "assistant":
            assistant_msg = m.content[:200]

    # 调用 LLM 生成总结
    try:
        import sys
        from pathlib import Path
        sys.path.insert(
            0,
            str(
                Path(__file__).resolve().parent.parent.parent.parent.parent
                / "agent-demo-agent"
                / "src"
            ),
        )
        from agent.config import get_settings
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        settings = get_settings()
        llm = ChatOpenAI(
            model=settings.mimo_model_fast,
            api_key=settings.mimo_api_key,
            base_url=settings.mimo_base_url,
            temperature=0.3,
            max_tokens=2000,  # 模型需要较多 reasoning tokens
        )

        from server.utils import strip_markdown

        prompt = (
            "根据以下对话内容，生成一个简短的会话标题。\n"
            "要求：\n"
            "1. 严格不超过8个汉字（2到8个字）\n"
            "2. 只输出标题本身，不要任何解释、标点或引号\n"
            "3. 用简洁的名词或短语概括对话主题\n\n"
            f"对话内容：\n用户：{user_msg}\n助手：{assistant_msg}"
        )
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        summary = strip_markdown(resp.content).strip()
        # 安全截断：仅在 LLM 未遵守指令时兜底
        if len(summary) > 8:
            summary = summary[:8]
        if summary:
            sess.name = summary
            await session.commit()
            await session.refresh(sess)
    except Exception:
        pass  # 总结失败时保持原名

    return sess
