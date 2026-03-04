from pathlib import Path

from process_reimagination_agent.config import Settings
from process_reimagination_agent.diagram_extraction import extract_canonical_document


def test_extract_canonical_document_from_diagram_like_text() -> None:
    fixture = Path("sample_inputs/diagram_flow_sample.txt").resolve()
    text = fixture.read_text(encoding="utf-8")
    doc = extract_canonical_document(
        file_path=fixture,
        mime_type="text/plain",
        extracted_text=text,
        settings=Settings(),
        source_id="DOC1",
    )
    assert doc.graph is not None
    assert doc.graph.nodes
    assert doc.graph.extraction_confidence > 0.0
    assert any(page.page_type in {"diagram", "mixed"} for page in doc.pages)
