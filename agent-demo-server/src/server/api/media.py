from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.database import get_session
from server.db.models import MediaTask
from server.deps import UserContext, get_current_user
from server.models.media import MediaTaskListResponse, MediaTaskResponse
from server.services.media_tasks import task_to_response


router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("/tasks", response_model=MediaTaskListResponse)
async def list_media_tasks(
    statuses: str = Query("pending,running"),
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    status_list = [item.strip() for item in statuses.split(",") if item.strip()]
    stmt = select(MediaTask).where(MediaTask.user_id == user.user_id).order_by(MediaTask.created_at.desc())
    if status_list:
        stmt = stmt.where(MediaTask.status.in_(status_list))
    result = await session.execute(stmt.limit(50))
    return MediaTaskListResponse(
        tasks=[task_to_response(task, user.user_id) for task in result.scalars().all()]
    )


@router.get("/tasks/{task_id}", response_model=MediaTaskResponse)
async def get_media_task(
    task_id: str,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(MediaTask).where(MediaTask.id == task_id, MediaTask.user_id == user.user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="媒体任务不存在")
    return task_to_response(task, user.user_id)
