from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from api.schemas import StepStatus

SessionStatus = Literal["draft", "running", "ready", "error", "pending_approval"]

PHASE1_STEPS = [
    "Read As-Is maps",
    "Read pain points & regional nuances",
    "Read KPIs & guardrails",
    "Read benchmarks",
    "Identify cognitive friction",
]

PHASE2_STEPS = [
    "Compare As-Is vs benchmarks",
    "Suitability assessment",
    "Classify into Path A/B/C",
]

PHASE3_STEPS = [
    "Produce Strategy Report (Markdown)",
    "Generate Process Blueprint (XML/Mermaid)",
]


@dataclass
class UploadedFile:
    id: str
    name: str
    disk_path: str
    date: datetime
    category: str  # "as_is" | "pain_point" | "benchmark"
    tag: str = ""


@dataclass
class EngagementSession:
    id: str
    thread_id: str
    process_name: str
    region: str
    status: SessionStatus = "draft"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Input data
    pain_points: str = ""
    pain_points_list: list[str] = field(default_factory=list)
    regional_variations: bool = False
    regional_nuances: str = ""
    strategic_guardrails: str = ""
    kpis: list[dict[str, str]] = field(default_factory=list)
    channel: str = ""
    order_status: str = "open"

    # Uploaded files
    files: list[UploadedFile] = field(default_factory=list)

    # Run progress tracking
    current_phase: int = 0
    progress: float = 0.0
    phase1_steps: list[dict[str, str]] = field(default_factory=list)
    phase2_steps: list[dict[str, str]] = field(default_factory=list)
    phase3_steps: list[dict[str, str]] = field(default_factory=list)
    run_error: str | None = None

    # Agent state cache (populated after run completes)
    agent_state: dict[str, Any] | None = None
    confidence_score: float | None = None
    quality_gate_result: str | None = None

    def init_progress(self) -> None:
        self.phase1_steps = [{"label": s, "status": "pending"} for s in PHASE1_STEPS]
        self.phase2_steps = [{"label": s, "status": "pending"} for s in PHASE2_STEPS]
        self.phase3_steps = [{"label": s, "status": "pending"} for s in PHASE3_STEPS]
        self.progress = 0.0
        self.current_phase = 1

    def get_step_statuses(self) -> tuple[list[StepStatus], list[StepStatus], list[StepStatus]]:
        return (
            [StepStatus(**s) for s in self.phase1_steps],
            [StepStatus(**s) for s in self.phase2_steps],
            [StepStatus(**s) for s in self.phase3_steps],
        )


class SessionManager:
    """Thread-safe in-memory store for engagement sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, EngagementSession] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _get_lock(self, session_id: str) -> asyncio.Lock:
        async with self._global_lock:
            if session_id not in self._locks:
                self._locks[session_id] = asyncio.Lock()
            return self._locks[session_id]

    async def create(self, process_name: str, region: str) -> EngagementSession:
        session_id = str(uuid4())
        thread_id = str(uuid4())
        session = EngagementSession(
            id=session_id,
            thread_id=thread_id,
            process_name=process_name,
            region=region,
        )
        lock = await self._get_lock(session_id)
        async with lock:
            self._sessions[session_id] = session
        return session

    async def get(self, session_id: str) -> EngagementSession | None:
        return self._sessions.get(session_id)

    async def update(self, session_id: str, **kwargs: Any) -> EngagementSession | None:
        lock = await self._get_lock(session_id)
        async with lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            for key, value in kwargs.items():
                if hasattr(session, key) and value is not None:
                    setattr(session, key, value)
            return session

    async def lock(self, session_id: str) -> asyncio.Lock:
        return await self._get_lock(session_id)


session_manager = SessionManager()
