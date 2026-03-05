from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()


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
    azure_document_intelligence_endpoint: str | None = None
    azure_document_intelligence_api_key: str | None = None
    azure_document_intelligence_api_version: str = "2024-11-30"
    azure_document_intelligence_model: str = "prebuilt-layout"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    daia_base_url: str = "https://daia.privatelink.azurewebsites.net"
    daia_client_id: str | None = None
    daia_client_secret: str | None = None
    daia_model: str = "gpt-5"
    daia_ca_bundle: str | None = None
    model_temperature: float = Field(default=0.0, ge=0.0, le=1.0)

    confidence_threshold: float = Field(default=0.95, gt=0.0, lt=1.0)
    max_refinement_loops: int = Field(default=3, ge=1, le=10)
    min_report_words: int = Field(default=2000, ge=500)
    report_mode: Literal["FULL", "DEMO"] = "FULL"
    trust_gap_default_phase: Literal["Shadow", "Co-Pilot", "Autopilot"] = "Shadow"
    output_root: Path = Path("outputs")
    durable_artifact_root: Path = Path("artifacts")
    render_blueprint_image: bool = True
    mermaid_render_timeout_sec: int = Field(default=180, ge=30, le=600)
    document_parse_timeout_sec: int = Field(default=60, ge=5, le=300)
    max_job_retries: int = Field(default=3, ge=0, le=10)
    job_retry_backoff_sec: float = Field(default=1.5, ge=0.0, le=30.0)
    enable_json_metrics: bool = True

    @property
    def azure_enabled(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def daia_enabled(self) -> bool:
        return bool(self.daia_client_id and self.daia_client_secret)

    @property
    def daia_verify_ssl(self) -> str | bool:
        """Return the CA bundle path for DAIA SSL verification, or False to skip."""
        if self.daia_ca_bundle:
            bundle_path = Path(self.daia_ca_bundle)
            if bundle_path.exists():
                return str(bundle_path)
        return False

    @property
    def azure_document_intelligence_enabled(self) -> bool:
        return bool(self.azure_document_intelligence_endpoint and self.azure_document_intelligence_api_key)

    @property
    def any_llm_configured(self) -> bool:
        return self.daia_enabled or self.azure_enabled or self.openai_enabled

    def validate_llm_available(self) -> None:
        """Raise with actionable instructions if no LLM backend is configured."""
        if self.any_llm_configured:
            return
        raise RuntimeError(
            "\n"
            "================================================================\n"
            "  ERROR: No LLM backend is configured.\n"
            "================================================================\n"
            "\n"
            "  The pipeline REQUIRES at least one LLM backend to generate\n"
            "  industry-level output. Without it, only static templates run.\n"
            "\n"
            "  Set ONE of these in your .env file or environment:\n"
            "\n"
            "  Option 1 - DAIA (McCain primary):\n"
            "    DAIA_CLIENT_ID=<your-client-id>\n"
            "    DAIA_CLIENT_SECRET=<your-client-secret>\n"
            "\n"
            "  Option 2 - Azure OpenAI:\n"
            "    AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com\n"
            "    AZURE_OPENAI_API_KEY=<your-key>\n"
            "\n"
            "  Option 3 - OpenAI:\n"
            "    OPENAI_API_KEY=sk-...\n"
            "\n"
            "================================================================\n"
        )

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
            azure_document_intelligence_endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
            azure_document_intelligence_api_key=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY"),
            azure_document_intelligence_api_version=os.getenv(
                "AZURE_DOCUMENT_INTELLIGENCE_API_VERSION", "2024-11-30"
            ),
            azure_document_intelligence_model=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_MODEL", "prebuilt-layout"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            daia_base_url=os.getenv("DAIA_BASE_URL", "https://daia.privatelink.azurewebsites.net"),
            daia_client_id=os.getenv("DAIA_CLIENT_ID") or os.getenv("CLIENT_ID"),
            daia_client_secret=os.getenv("DAIA_CLIENT_SECRET") or os.getenv("CLIENT_SECRET"),
            daia_model=os.getenv("DAIA_MODEL", "gpt-5"),
            daia_ca_bundle=os.getenv("DAIA_CA_BUNDLE"),
            model_temperature=float(os.getenv("MODEL_TEMPERATURE", "0.0")),
            confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.95")),
            max_refinement_loops=int(os.getenv("MAX_REFINEMENT_LOOPS", "3")),
            min_report_words=int(os.getenv("MIN_REPORT_WORDS", "2000")),
            report_mode=os.getenv("REPORT_MODE", "FULL"),  # type: ignore[arg-type]
            trust_gap_default_phase=os.getenv("TRUST_GAP_DEFAULT_PHASE", "Shadow"),  # type: ignore[arg-type]
            output_root=Path(os.getenv("OUTPUT_ROOT", "outputs")),
            durable_artifact_root=Path(os.getenv("DURABLE_ARTIFACT_ROOT", "artifacts")),
            render_blueprint_image=_env_bool("RENDER_BLUEPRINT_IMAGE", True),
            mermaid_render_timeout_sec=int(os.getenv("MERMAID_RENDER_TIMEOUT_SEC", "180")),
            document_parse_timeout_sec=int(os.getenv("DOCUMENT_PARSE_TIMEOUT_SEC", "60")),
            max_job_retries=int(os.getenv("MAX_JOB_RETRIES", "3")),
            job_retry_backoff_sec=float(os.getenv("JOB_RETRY_BACKOFF_SEC", "1.5")),
            enable_json_metrics=_env_bool("ENABLE_JSON_METRICS", True),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
