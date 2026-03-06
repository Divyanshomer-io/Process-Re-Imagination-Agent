from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.schemas import RunStatusResponse
from core.agent_bridge import execute_agent_run
from core.session_manager import session_manager

router = APIRouter(prefix="/api/engagements/{engagement_id}/run", tags=["runs"])

_active_tasks: dict[str, asyncio.Task] = {}


@router.post("", response_model=RunStatusResponse)
async def start_run(engagement_id: str):
    session = await session_manager.get(engagement_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if session.status == "running":
        p1, p2, p3 = session.get_step_statuses()
        return RunStatusResponse(
            status=session.status,
            progress=session.progress,
            current_phase=session.current_phase,
            phase1_steps=p1,
            phase2_steps=p2,
            phase3_steps=p3,
            confidence_score=session.confidence_score,
            quality_gate_result=session.quality_gate_result,
        )

    if session.status in ("ready", "pending_approval"):
        raise HTTPException(status_code=409, detail="Run already completed or awaiting approval")

    if not session.files:
        raise HTTPException(status_code=422, detail="At least one file must be uploaded before starting a run")

    task = asyncio.create_task(execute_agent_run(session))
    _active_tasks[engagement_id] = task

    p1, p2, p3 = session.get_step_statuses()
    return RunStatusResponse(
        status="running",
        progress=0.0,
        current_phase=1,
        phase1_steps=p1,
        phase2_steps=p2,
        phase3_steps=p3,
    )


@router.get("/status", response_model=RunStatusResponse)
async def get_run_status(engagement_id: str, request: Request):
    session = await session_manager.get(engagement_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept:
        return StreamingResponse(
            _sse_stream(engagement_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    p1, p2, p3 = session.get_step_statuses()
    return RunStatusResponse(
        status=session.status,
        progress=session.progress,
        current_phase=session.current_phase,
        phase1_steps=p1,
        phase2_steps=p2,
        phase3_steps=p3,
        error=session.run_error,
        confidence_score=session.confidence_score,
        quality_gate_result=session.quality_gate_result,
    )


async def _sse_stream(engagement_id: str):
    """Server-Sent Events stream for real-time run progress."""
    while True:
        session = await session_manager.get(engagement_id)
        if session is None:
            yield f"data: {json.dumps({'error': 'session not found'})}\n\n"
            return

        p1, p2, p3 = session.get_step_statuses()
        payload = RunStatusResponse(
            status=session.status,
            progress=session.progress,
            current_phase=session.current_phase,
            phase1_steps=p1,
            phase2_steps=p2,
            phase3_steps=p3,
            error=session.run_error,
            confidence_score=session.confidence_score,
            quality_gate_result=session.quality_gate_result,
        )
        yield f"data: {payload.model_dump_json()}\n\n"

        if session.status in ("ready", "error", "pending_approval"):
            return

        await asyncio.sleep(1.5)
