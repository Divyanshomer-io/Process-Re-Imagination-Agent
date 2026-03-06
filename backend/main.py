from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_AGENT_ROOT = Path(__file__).resolve().parent.parent / "Process-Re-Imagination-Agent"
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

_agent_env = _AGENT_ROOT / ".env"
if _agent_env.exists():
    load_dotenv(_agent_env, override=False)

from api.routes.engagements import router as engagements_router  # noqa: E402
from api.routes.files import router as files_router  # noqa: E402
from api.routes.runs import router as runs_router  # noqa: E402
from api.routes.results import router as results_router  # noqa: E402
from api.routes.approve import router as approve_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="CPRE Backend",
    description="Cognitive Process Re-imagination Engine — FastAPI bridge to the LangGraph agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(engagements_router)
app.include_router(files_router)
app.include_router(runs_router)
app.include_router(results_router)
app.include_router(approve_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
