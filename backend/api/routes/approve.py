from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from api.schemas import ApproveRequest, ApproveResponse
from core.agent_bridge import execute_agent_resume
from core.session_manager import session_manager

router = APIRouter(prefix="/api/engagements/{engagement_id}", tags=["approve"])


@router.post("/approve", response_model=ApproveResponse)
async def approve_engagement(engagement_id: str, body: ApproveRequest):
    session = await session_manager.get(engagement_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if session.status not in ("pending_approval",):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve — current status is '{session.status}'. Expected 'pending_approval'.",
        )

    task = asyncio.create_task(
        execute_agent_resume(session, body.approver, body.notes)
    )

    return ApproveResponse(
        status="approved",
        message=f"Approval recorded. Blueprint generation started by {body.approver}.",
    )
