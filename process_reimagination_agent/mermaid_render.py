"""Mermaid diagram to SVG rendering. Shared by CLI and backend."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from process_reimagination_agent.config import Settings


def render_mermaid_to_svg(
    settings: Settings,
    *,
    output_dir: Path,
    mermaid_code: str,
) -> dict[str, Any]:
    """Render mermaid code to SVG using mmdc or npx/@mermaid-js/mermaid-cli."""
    artifact: dict[str, Any] = {
        "mmd_path": str(output_dir / "process_blueprint.mmd"),
        "svg_path": str(output_dir / "process_blueprint.svg"),
        "renderer": "",
        "status": "skipped",
        "warning": "",
    }
    mmd_path = output_dir / "process_blueprint.mmd"
    svg_path = output_dir / "process_blueprint.svg"
    mmd_path.write_text(mermaid_code, encoding="utf-8")

    if not settings.render_blueprint_image:
        artifact["warning"] = "Image render disabled via RENDER_BLUEPRINT_IMAGE."
        return artifact

    mmdc = shutil.which("mmdc")
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    command: list[str] | None = None

    if mmdc:
        artifact["renderer"] = "mmdc"
        command = [mmdc, "-i", str(mmd_path), "-o", str(svg_path), "-b", "transparent"]
    elif npx:
        artifact["renderer"] = "npx:@mermaid-js/mermaid-cli"
        command = [
            npx,
            "--yes",
            "@mermaid-js/mermaid-cli",
            "-i",
            str(mmd_path),
            "-o",
            str(svg_path),
            "-b",
            "transparent",
        ]
    else:
        artifact["warning"] = "No Mermaid renderer found (mmdc/npx)."
        return artifact

    chrome_candidates = [
        os.getenv("CHROME_PATH", ""),
        os.getenv("GOOGLE_CHROME_BIN", ""),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path(os.getenv("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"),
    ]
    chrome_path = next((path for path in chrome_candidates if path and Path(path).exists()), "")
    command_env = os.environ.copy()
    command_env["PUPPETEER_SKIP_DOWNLOAD"] = "true"
    if chrome_path:
        command_env["PUPPETEER_EXECUTABLE_PATH"] = chrome_path

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=settings.mermaid_render_timeout_sec,
            env=command_env,
        )
    except subprocess.TimeoutExpired:
        artifact["warning"] = (
            f"Render timed out after {settings.mermaid_render_timeout_sec}s "
            f"using renderer {artifact.get('renderer', 'unknown')}."
        )
        return artifact
    except OSError as exc:
        artifact["warning"] = f"Render failed to start: {exc}"
        return artifact
    if svg_path.exists() and svg_path.stat().st_size > 0:
        artifact["status"] = "created"
        if completed.returncode != 0:
            artifact["warning"] = (
                f"Renderer exited {completed.returncode} but SVG was created successfully."
            )
        return artifact

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        artifact["warning"] = f"Render failed (exit {completed.returncode}): {stderr or stdout}"
        return artifact

    artifact["warning"] = "Renderer completed but SVG was not created."
    return artifact
