from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from core.session_manager import UploadedFile

UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"


def _ensure_dir(engagement_id: str) -> Path:
    dest = UPLOAD_ROOT / engagement_id
    dest.mkdir(parents=True, exist_ok=True)
    return dest


async def save_file(
    engagement_id: str,
    file: UploadFile,
    category: str,
    tag: str = "",
) -> UploadedFile:
    dest_dir = _ensure_dir(engagement_id)
    file_id = str(uuid4())
    safe_name = file.filename or f"upload-{file_id}"
    disk_path = dest_dir / f"{file_id}_{safe_name}"

    content = await file.read()
    disk_path.write_bytes(content)

    return UploadedFile(
        id=file_id,
        name=safe_name,
        disk_path=str(disk_path),
        date=datetime.now(timezone.utc),
        category=category,
        tag=tag,
    )


def delete_file(engagement_id: str, file_id: str, files: list[UploadedFile]) -> UploadedFile | None:
    target = next((f for f in files if f.id == file_id), None)
    if target is None:
        return None
    disk = Path(target.disk_path)
    if disk.exists():
        disk.unlink()
    return target


def get_file_paths(files: list[UploadedFile]) -> list[str]:
    return [f.disk_path for f in files]


def cleanup_engagement_files(engagement_id: str) -> None:
    dest = UPLOAD_ROOT / engagement_id
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
