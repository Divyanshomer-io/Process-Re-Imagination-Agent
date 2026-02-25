from __future__ import annotations

from pathlib import Path
from typing import Any

from process_reimagination_agent.models import InputManifest


def detect_mime_type(file_path: Path) -> str:
    try:
        import magic  # type: ignore[import-not-found]

        mime = magic.Magic(mime=True)
        return str(mime.from_file(str(file_path)))
    except Exception:
        suffix = file_path.suffix.lower()
        fallback = {
            ".pdf": "application/pdf",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".json": "application/json",
            ".xml": "application/xml",
        }
        return fallback.get(suffix, "application/octet-stream")


def extract_text(file_path: Path, mime_type: str) -> str:
    if mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(file_path)
    if (
        mime_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        or file_path.suffix.lower() == ".pptx"
    ):
        return extract_text_from_pptx(file_path)
    if mime_type.startswith("text/") or file_path.suffix.lower() in {".txt", ".md", ".csv", ".json", ".xml"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    return ""


def extract_text_from_pdf(file_path: Path) -> str:
    from pypdf import PdfReader  # type: ignore[import-not-found]

    reader = PdfReader(str(file_path))
    parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        parts.append(page_text)
    return "\n".join(parts).strip()


def extract_text_from_pptx(file_path: Path) -> str:
    from pptx import Presentation  # type: ignore[import-not-found]

    presentation = Presentation(str(file_path))
    chunks: list[str] = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text = str(shape.text).strip()
                if text:
                    chunks.append(text)
    return "\n".join(chunks).strip()


def ingest_manifest(manifest: InputManifest) -> dict[str, Any]:
    documents: list[dict[str, Any]] = []
    extraction_errors: list[str] = []
    combined_text_parts: list[str] = []

    for file_name in manifest.files:
        file_path = Path(file_name).expanduser()
        record: dict[str, Any] = {"path": str(file_path), "mime_type": "", "content": "", "error": ""}

        if not file_path.exists():
            record["error"] = "File does not exist"
            extraction_errors.append(f"{file_path}: not found")
            documents.append(record)
            continue

        try:
            mime_type = detect_mime_type(file_path)
            record["mime_type"] = mime_type
            content = extract_text(file_path, mime_type)
            record["content"] = content
            if content:
                combined_text_parts.append(content)
            else:
                record["error"] = "No text could be extracted"
                extraction_errors.append(f"{file_path}: empty extraction")
        except Exception as exc:
            record["error"] = f"Extraction failed: {exc}"
            extraction_errors.append(f"{file_path}: {exc}")

        documents.append(record)

    combined_text = "\n\n".join(combined_text_parts).strip()
    return {
        "manifest": manifest.model_dump(),
        "documents": documents,
        "combined_text": combined_text,
        "extraction_errors": extraction_errors,
    }

