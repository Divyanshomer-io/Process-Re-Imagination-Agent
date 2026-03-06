from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import (
    CreateEngagementRequest,
    EngagementMeta,
    UpdateEngagementRequest,
)
from core.session_manager import session_manager

router = APIRouter(prefix="/api/engagements", tags=["engagements"])


@router.post("", response_model=EngagementMeta)
async def create_engagement(body: CreateEngagementRequest):
    session = await session_manager.create(body.process_name, body.context_region)
    return EngagementMeta(
        id=session.id,
        thread_id=session.thread_id,
        process_name=session.process_name,
        region=session.region,
        status=session.status,
        created_at=session.created_at,
    )


@router.get("/{engagement_id}", response_model=EngagementMeta)
async def get_engagement(engagement_id: str):
    session = await session_manager.get(engagement_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return EngagementMeta(
        id=session.id,
        thread_id=session.thread_id,
        process_name=session.process_name,
        region=session.region,
        status=session.status,
        created_at=session.created_at,
    )


@router.patch("/{engagement_id}", response_model=EngagementMeta)
async def update_engagement(engagement_id: str, body: UpdateEngagementRequest):
    updates = body.model_dump(exclude_none=True)
    if "kpis" in updates:
        updates["kpis"] = [k.model_dump() if hasattr(k, "model_dump") else k for k in updates["kpis"]]

    session = await session_manager.update(engagement_id, **updates)
    if session is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return EngagementMeta(
        id=session.id,
        thread_id=session.thread_id,
        process_name=session.process_name,
        region=session.region,
        status=session.status,
        created_at=session.created_at,
    )
