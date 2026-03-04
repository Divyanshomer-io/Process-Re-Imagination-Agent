from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TypeVar

from process_reimagination_agent.config import Settings

T = TypeVar("T")


@dataclass
class JobEnvelope:
    job_id: str
    payload: dict[str, Any]
    attempts: int = 0
    created_at_epoch: int = field(default_factory=lambda: int(time.time()))


class InMemoryJobQueue:
    def __init__(self) -> None:
        self._jobs: list[JobEnvelope] = []

    def enqueue(self, envelope: JobEnvelope) -> None:
        self._jobs.append(envelope)

    def dequeue(self) -> JobEnvelope | None:
        if not self._jobs:
            return None
        return self._jobs.pop(0)

    def size(self) -> int:
        return len(self._jobs)


def execute_with_retry(
    fn: Callable[[], T],
    *,
    settings: Settings,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(settings.max_job_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt >= settings.max_job_retries:
                break
            if on_retry:
                on_retry(attempt + 1, exc)
            time.sleep(settings.job_retry_backoff_sec * (2**attempt))
    assert last_exc is not None
    raise last_exc


def write_dead_letter(settings: Settings, *, thread_id: str, reason: str, payload: dict[str, Any]) -> Path:
    dead_dir = settings.durable_artifact_root / "dead_letters"
    dead_dir.mkdir(parents=True, exist_ok=True)
    dead_path = dead_dir / f"{thread_id}.json"
    body = {"thread_id": thread_id, "reason": reason, "payload": payload, "created_at_epoch": int(time.time())}
    dead_path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return dead_path


def persist_artifact(settings: Settings, *, thread_id: str, name: str, payload: dict[str, Any]) -> Path:
    root = settings.durable_artifact_root / thread_id
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
