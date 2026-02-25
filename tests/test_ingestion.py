from pathlib import Path

from process_reimagination_agent.ingestion import ingest_manifest
from process_reimagination_agent.models import InputManifest


def test_ingest_manifest_with_text_file() -> None:
    fixture = Path("sample_inputs/order_intake_notes.txt").resolve()
    manifest = InputManifest(
        process_name="Order Intake",
        context_region="ANZ",
        pain_points=["Manual entry"],
        files=[str(fixture)],
    )
    result = ingest_manifest(manifest)
    assert result["documents"]
    assert "combined_text" in result
    assert "Manual email and PDF order entry" in result["combined_text"]

