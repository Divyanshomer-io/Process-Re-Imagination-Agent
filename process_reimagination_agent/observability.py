from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any


LOGGER_NAME = "process_reimagination_agent"


def get_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    return logger


class MetricsCollector:
    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._timers: dict[str, list[float]] = {}

    def incr(self, key: str, value: int = 1) -> None:
        self._counters[key] = self._counters.get(key, 0) + value

    def timing(self, key: str, seconds: float) -> None:
        self._timers.setdefault(key, []).append(max(0.0, seconds))

    def snapshot(self) -> dict[str, Any]:
        avg_timers = {f"{name}_avg_sec": round(sum(values) / len(values), 4) for name, values in self._timers.items() if values}
        return {"counters": dict(self._counters), "timers": avg_timers, "generated_at_epoch": int(time.time())}

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")


def render_slo_dashboard(snapshot: dict[str, Any]) -> str:
    counters = snapshot.get("counters", {})
    timers = snapshot.get("timers", {})
    success = int(counters.get("jobs_succeeded", 0)) + int(counters.get("resume_succeeded", 0))
    failed = int(counters.get("jobs_failed", 0)) + int(counters.get("resume_failed", 0))
    total = success + failed
    success_rate = (success / total * 100.0) if total else 100.0
    return "\n".join(
        [
            "# SLO Dashboard",
            "",
            f"- Job success rate: {success_rate:.2f}%",
            f"- Successful jobs: {success}",
            f"- Failed jobs: {failed}",
            f"- Avg run latency (sec): {timers.get('run_workflow_avg_sec', 0.0)}",
            f"- Avg resume latency (sec): {timers.get('resume_workflow_avg_sec', 0.0)}",
            "",
            "## Raw Counters",
            f"```json\n{json.dumps(counters, indent=2)}\n```",
        ]
    )
