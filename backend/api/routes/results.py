from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.schemas import (
    BlueprintResponse,
    FrictionItemResponse,
    PathItemResponse,
    StrategyReportResponse,
    UseCaseResponse,
)
from core.session_manager import session_manager
from core.transformers import (
    transform_blueprint,
    transform_friction_logs,
    transform_path_decisions,
    transform_strategy_report,
    transform_use_cases,
)

router = APIRouter(prefix="/api/engagements/{engagement_id}/results", tags=["results"])


def _require_state(session):
    if session is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if session.agent_state is None:
        raise HTTPException(status_code=409, detail="No results available yet — run has not completed")
    return session.agent_state


@router.get("/friction", response_model=list[FrictionItemResponse])
async def get_friction(engagement_id: str):
    session = await session_manager.get(engagement_id)
    state = _require_state(session)
    return transform_friction_logs(
        state.get("cognitive_friction_logs", []),
        state.get("evidence_references"),
        state.get("pain_points"),
        state.get("path_decisions"),
    )


@router.get("/paths", response_model=list[PathItemResponse])
async def get_paths(engagement_id: str):
    session = await session_manager.get(engagement_id)
    state = _require_state(session)
    return transform_path_decisions(state.get("path_decisions", []))


@router.get("/strategy", response_model=StrategyReportResponse)
async def get_strategy(engagement_id: str):
    session = await session_manager.get(engagement_id)
    state = _require_state(session)
    return StrategyReportResponse(markdown=transform_strategy_report(state))


@router.get("/blueprint", response_model=BlueprintResponse)
async def get_blueprint(engagement_id: str):
    session = await session_manager.get(engagement_id)
    state = _require_state(session)
    return transform_blueprint(state)


@router.get("/use-cases", response_model=list[UseCaseResponse])
async def get_use_cases(engagement_id: str):
    session = await session_manager.get(engagement_id)
    state = _require_state(session)
    return transform_use_cases(state)


@router.get("/outputs/{filename}")
async def download_output(engagement_id: str, filename: str):
    session = await session_manager.get(engagement_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    from process_reimagination_agent.config import get_settings
    settings = get_settings()
    file_path = settings.output_root / session.thread_id / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Output file '{filename}' not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )
