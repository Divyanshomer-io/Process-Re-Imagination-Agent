"""Render Mermaid diagrams: mmdc first, Kroki fallback. Returns JSON errors for iframe fallback."""

from __future__ import annotations

import asyncio
import base64
import json
import tempfile
import zlib
from pathlib import Path

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["mermaid"])
KROKI_URL = "https://kroki.io/mermaid/svg"
MERMAID_LIVE_BASE = "https://mermaid.live/view#pako:"


class MermaidRenderRequest(BaseModel):
    code: str


class MermaidRenderResponse(BaseModel):
    svg: str | None = None
    error: str | None = None
    fallback: str | None = None


class MermaidLiveUrlRequest(BaseModel):
    code: str


class MermaidLiveUrlResponse(BaseModel):
    url: str


def _is_valid_svg(text: str) -> bool:
    """Check if response is valid SVG, not HTML error page."""
    t = text.strip()
    return t.startswith("<svg") and "</svg>" in t


@router.post("/render-mermaid", response_model=MermaidRenderResponse)
async def render_mermaid(req: MermaidRenderRequest):
    """Try mmdc first (same as agent runs), fallback to Kroki. Return JSON error for iframe fallback."""
    if not req.code or not req.code.strip():
        return MermaidRenderResponse(error="Mermaid code is required", fallback="iframe")

    code = req.code.strip()

    # 1. Try mmdc / npx mermaid-cli (same as agent runs)
    try:
        from process_reimagination_agent.config import get_settings
        from process_reimagination_agent.mermaid_render import render_mermaid_to_svg

        settings = get_settings()
        with tempfile.TemporaryDirectory(prefix="mermaid_render_") as tmpdir:
            out_dir = Path(tmpdir)
            artifact = await asyncio.to_thread(
                render_mermaid_to_svg,
                settings,
                output_dir=out_dir,
                mermaid_code=code,
            )
            if artifact.get("status") == "created":
                svg_path = Path(artifact["svg_path"])
                if svg_path.exists():
                    svg = svg_path.read_text(encoding="utf-8")
                    if _is_valid_svg(svg):
                        return MermaidRenderResponse(svg=svg)
    except ImportError:
        pass  # Fall through to Kroki
    except Exception:
        pass  # Fall through to Kroki

    # 2. Fallback: Kroki.io
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                KROKI_URL,
                content=code,
                headers={"Content-Type": "text/plain"},
            )
            resp.raise_for_status()
            svg = resp.text
            if svg and _is_valid_svg(svg):
                return MermaidRenderResponse(svg=svg)
            # Kroki returned HTML error page — do not pass through
    except (httpx.HTTPStatusError, httpx.RequestError):
        pass

    return MermaidRenderResponse(
        error="Render failed",
        fallback="iframe",
    )


def _encode_pako(code: str) -> str:
    """Encode Mermaid code for mermaid.live URL (zlib + base64 + URL-safe)."""
    payload = json.dumps({"code": code, "mermaid": {}})
    compressed = zlib.compress(payload.encode("utf-8"), level=9)
    b64 = base64.b64encode(compressed).decode("ascii")
    url_safe = b64.replace("+", "-").replace("/", "_").rstrip("=")
    return url_safe


@router.post("/mermaid-live-url", response_model=MermaidLiveUrlResponse)
async def get_mermaid_live_url(req: MermaidLiveUrlRequest):
    """Return mermaid.live view URL for iframe fallback."""
    if not req.code or not req.code.strip():
        return MermaidLiveUrlResponse(url=f"{MERMAID_LIVE_BASE}eJxLzs8tyEkFAApTAvo=")
    encoded = _encode_pako(req.code.strip())
    return MermaidLiveUrlResponse(url=f"{MERMAID_LIVE_BASE}{encoded}")
