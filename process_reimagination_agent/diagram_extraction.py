from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib import error, request

from process_reimagination_agent.config import Settings
from process_reimagination_agent.diagram_models import CanonicalDocumentModel, DiagramPage
from process_reimagination_agent.process_graph import build_process_graph


def _is_diagram_text(text: str) -> bool:
    lower = text.lower()
    diagram_tokens = [
        "gateway",
        "what is the order type",
        "failure?",
        "yes",
        "no",
        "start",
        "end",
        "->",
        "bpmn",
        "task",
        "subprocess",
    ]
    token_hits = sum(1 for token in diagram_tokens if token in lower)
    short_lines = [line for line in text.splitlines() if 0 < len(line.strip()) <= 32]
    return token_hits >= 2 or len(short_lines) >= 10


def _extract_node_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip(" -\t")
        if not line or len(line) < 3:
            continue
        if re.match(r"^\d+(\.\d+)+$", line):
            continue
        lines.append(line)
    return lines


def _infer_edges(lines: list[str]) -> list[tuple[str, str, str | None, float]]:
    edges: list[tuple[str, str, str | None, float]] = []
    gateway_indexes: set[int] = set()
    for i, line in enumerate(lines):
        lower = line.lower()
        if "what is" in lower or "?" in line:
            gateway_indexes.add(i)
            if i + 1 < len(lines):
                edges.append((line, lines[i + 1], "Yes", 0.6))
            if i + 2 < len(lines):
                edges.append((line, lines[i + 2], "No", 0.55))
    for i in range(len(lines) - 1):
        if i in gateway_indexes:
            continue
        # Avoid a noisy sequential edge immediately after a gateway branch fan-out.
        if (i - 1) in gateway_indexes:
            continue
        edges.append((lines[i], lines[i + 1], None, 0.72))
    return edges


def _azure_layout_extract(file_path: Path, settings: Settings, warnings: list[str]) -> list[str]:
    if not settings.azure_document_intelligence_enabled:
        return []
    endpoint = settings.azure_document_intelligence_endpoint.rstrip("/")
    api_key = settings.azure_document_intelligence_api_key
    model_id = settings.azure_document_intelligence_model
    if not endpoint or not api_key:
        return []

    url = (
        f"{endpoint}/documentintelligence/documentModels/{model_id}:analyze"
        f"?api-version={settings.azure_document_intelligence_api_version}"
        "&outputContentFormat=text"
    )
    try:
        payload = file_path.read_bytes()
        req = request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/octet-stream")
        req.add_header("Ocp-Apim-Subscription-Key", api_key)
        with request.urlopen(req, timeout=settings.document_parse_timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        body = json.loads(raw)
    except (error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        warnings.append(f"{file_path}: Azure layout extraction unavailable ({exc})")
        return []

    text_pages: list[str] = []
    pages = body.get("analyzeResult", {}).get("pages", [])
    full_content = str(body.get("analyzeResult", {}).get("content", "")).strip()
    if not pages and full_content:
        text_pages.append(full_content)
        return text_pages
    for page in pages:
        lines = page.get("lines", [])
        text_pages.append("\n".join(str(line.get("content", "")).strip() for line in lines if line.get("content")))
    return [page for page in text_pages if page.strip()]


def extract_canonical_document(
    *,
    file_path: Path,
    mime_type: str,
    extracted_text: str,
    settings: Settings,
    source_id: str,
    warnings: list[str] | None = None,
) -> CanonicalDocumentModel:
    warnings_out = list(warnings or [])
    pages_text = _azure_layout_extract(file_path, settings, warnings_out)
    if not pages_text:
        pages_text = [extracted_text] if extracted_text.strip() else []

    pages: list[DiagramPage] = []
    node_candidates: list[tuple[str, int, float, str | None]] = []
    edge_candidates: list[tuple[str, str, str | None, float]] = []
    for page_index, page_text in enumerate(pages_text, start=1):
        page_type = "diagram" if _is_diagram_text(page_text) else "text"
        method = "azure_layout" if settings.azure_document_intelligence_enabled and pages_text != [extracted_text] else "text_layer"
        confidence = 0.86 if method == "azure_layout" else 0.68
        lines = _extract_node_lines(page_text)
        if page_type == "diagram":
            for line in lines[:80]:
                node_candidates.append((line, page_index, confidence, None))
            edge_candidates.extend(_infer_edges(lines[:80]))
        pages.append(
            DiagramPage(
                source_id=source_id,
                page_number=page_index,
                page_type=page_type,  # type: ignore[arg-type]
                text_content=page_text,
                extraction_method=method,
                confidence=confidence,
            )
        )

    graph = build_process_graph(
        graph_id=f"{source_id}-graph",
        node_candidates=node_candidates,
        edge_candidates=edge_candidates,
        warnings=warnings_out,
    )
    extraction_confidence = graph.extraction_confidence if pages else 0.0
    return CanonicalDocumentModel(
        source_id=source_id,
        path=str(file_path),
        mime_type=mime_type,
        pages=pages,
        graph=graph,
        extraction_confidence=extraction_confidence,
        warnings=warnings_out,
    )
