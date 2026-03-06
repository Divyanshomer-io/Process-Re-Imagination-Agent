from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from api.schemas import FileInfo, UploadedFileResponse
from core.file_manager import save_file, delete_file
from core.session_manager import session_manager

router = APIRouter(prefix="/api/engagements/{engagement_id}/files", tags=["files"])


@router.post("", response_model=UploadedFileResponse)
async def upload_file(
    engagement_id: str,
    file: UploadFile = File(...),
    category: str = Form("as_is"),
    tag: str = Form(""),
):
    session = await session_manager.get(engagement_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    lock = await session_manager.lock(engagement_id)
    async with lock:
        uploaded = await save_file(engagement_id, file, category, tag)
        session.files.append(uploaded)

    return UploadedFileResponse(
        id=uploaded.id,
        name=uploaded.name,
        date=uploaded.date,
    )


@router.get("", response_model=list[FileInfo])
async def list_files(engagement_id: str):
    session = await session_manager.get(engagement_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return [
        FileInfo(
            id=f.id,
            name=f.name,
            date=f.date,
            category=f.category,
            tag=f.tag,
        )
        for f in session.files
    ]


@router.delete("/{file_id}")
async def remove_file(engagement_id: str, file_id: str):
    session = await session_manager.get(engagement_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    lock = await session_manager.lock(engagement_id)
    async with lock:
        removed = delete_file(engagement_id, file_id, session.files)
        if removed is None:
            raise HTTPException(status_code=404, detail="File not found")
        session.files = [f for f in session.files if f.id != file_id]

    return {"status": "deleted", "id": file_id}
