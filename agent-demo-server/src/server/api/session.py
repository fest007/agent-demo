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
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from server.models.session import SessionResponse, SessionSummarizeRequest, SessionUpdate
from server.db.models import Session as SessionModel, Conversation
from server.db.database import get_session
from server.deps import get_current_user, UserContext
from server.agent_import import ensure_agent_on_path

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_GENERIC_TITLES = {"新对话", "对话", "聊天", "项目介绍", "会话标题", "标题"}
_ASCII_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#._-]*|[0-9]+")
_TITLE_PREFIX_RE = re.compile(r"^(标题|会话标题|主题|话题)\s*[:：-]?\s*")
_LEADING_FILLER_RE = re.compile(
    r"^(请|帮我|麻烦|你能|可以|给我|帮忙|想要|需要|如何|怎么|关于|有关|写一个|写个|做一个|做个|生成一个|生成个)+"
)
_TRAILING_FILLER_RE = re.compile(r"(一下|一下吧|吗|么|嘛|呢|呀)+$")


def _clean_title_source(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = _TITLE_PREFIX_RE.sub("", text)
    text = text.strip("`'\"“”‘’[](){}<>:：-，,。！？!? ")
    text = _LEADING_FILLER_RE.sub("", text)
    text = _TRAILING_FILLER_RE.sub("", text)
    return text.strip()


def _fit_title(text: str, max_units: int = 8) -> str:
    cleaned = _clean_title_source(text)
    if not cleaned:
        return ""

    tokens: list[tuple[str, int]] = []
    i = 0
    while i < len(cleaned):
        match = _ASCII_TOKEN_RE.match(cleaned, i)
        if match:
            token = match.group(0)
            tokens.append((token, 2))
            i = match.end()
            continue
        char = cleaned[i]
        i += 1
        if char.isspace():
            continue
        if re.match(r"[，,。！？!?、:：;；/\\|]+", char):
            continue
        tokens.append((char, 1))

    if not tokens:
        return ""

    title_parts: list[str] = []
    units = 0
    for token, cost in tokens:
        if units + cost > max_units:
            break
        title_parts.append(token)
        units += cost

    if not title_parts:
        first_token, _ = tokens[0]
        return first_token[:12] if first_token.isascii() else first_token[:max_units]

    title = "".join(title_parts).strip()
    title = title.strip("`'\"“”‘’[](){}<>:：-，,。！？!? ")
    return "" if title in _GENERIC_TITLES else title


def _build_local_summary(user_msg: str, assistant_msg: str) -> str:
    primary = _fit_title(user_msg)
    if primary:
        return primary
    backup = _fit_title(assistant_msg)
    return backup or "新对话"


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
    body: SessionSummarizeRequest | None = None,
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

    def local_summary() -> str:
        return _build_local_summary(user_msg, assistant_msg)

    body = body or SessionSummarizeRequest()

    # 调用 LLM 生成总结；失败时使用本地规则兜底，避免历史列表长期停留在“新对话”。
    try:
        ensure_agent_on_path()
        from agent.config import get_settings
        from agent.model_providers import resolve_model_config
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        settings = get_settings()
        model_config = resolve_model_config(
            provider_id=body.model_provider,
            model_id=body.model,
            key_id=body.api_key_id,
            purpose="fast",
        )
        base_url = body.custom_base_url or model_config.base_url
        api_key = body.custom_api_key or model_config.api_key
        llm = ChatOpenAI(
            model=model_config.model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.3,
            max_tokens=80,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

        from server.utils import strip_markdown

        prompt = (
            "根据以下对话内容，生成一个简短的会话标题。\n"
            "要求：\n"
            "1. 优先输出 4 到 8 个汉字的简洁短语\n"
            "2. 如果必须包含英文技术词，请保留完整单词，不要截断成半个词，例如写 Python，不要写 Pytho\n"
            "3. 只输出标题本身，不要任何解释、标点或引号\n"
            "4. 避免使用“帮我”“请”“写一个”这类动作前缀，直接概括主题\n\n"
            f"对话内容：\n用户：{user_msg}\n助手：{assistant_msg}"
        )
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        summary = _fit_title(strip_markdown(resp.content).strip())
        if not summary:
            summary = local_summary()
        if summary:
            sess.name = summary
            await session.commit()
            await session.refresh(sess)
    except Exception:
        summary = local_summary()
        if summary and summary != "新对话":
            sess.name = summary
            await session.commit()
            await session.refresh(sess)

    return sess
