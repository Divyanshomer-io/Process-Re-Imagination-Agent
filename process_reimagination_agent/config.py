from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deployment: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    model_temperature: float = Field(default=0.0, ge=0.0, le=1.0)

    confidence_threshold: float = Field(default=0.95, gt=0.0, lt=1.0)
    max_refinement_loops: int = Field(default=3, ge=1, le=10)
    min_report_words: int = Field(default=2000, ge=500)
    trust_gap_default_phase: Literal["Shadow", "Co-Pilot", "Autopilot"] = "Shadow"
    output_root: Path = Path("outputs")
    render_blueprint_image: bool = True
    mermaid_render_timeout_sec: int = Field(default=180, ge=30, le=600)

    @property
    def azure_enabled(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            model_temperature=float(os.getenv("MODEL_TEMPERATURE", "0.0")),
            confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.95")),
            max_refinement_loops=int(os.getenv("MAX_REFINEMENT_LOOPS", "3")),
            min_report_words=int(os.getenv("MIN_REPORT_WORDS", "2000")),
            trust_gap_default_phase=os.getenv("TRUST_GAP_DEFAULT_PHASE", "Shadow"),  # type: ignore[arg-type]
            output_root=Path(os.getenv("OUTPUT_ROOT", "outputs")),
            render_blueprint_image=_env_bool("RENDER_BLUEPRINT_IMAGE", True),
            mermaid_render_timeout_sec=int(os.getenv("MERMAID_RENDER_TIMEOUT_SEC", "180")),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
