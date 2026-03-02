import sys
import types
from pathlib import Path

from process_reimagination_agent import ingestion as ing
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


def test_extract_text_routes_image_mime_to_ocr(monkeypatch) -> None:
    monkeypatch.setattr(ing, "extract_text_from_image", lambda _path: "image ocr text")
    text = ing.extract_text(Path("diagram.png"), "image/png")
    assert text == "image ocr text"


def test_extract_text_from_pdf_uses_ocr_for_short_pages(monkeypatch) -> None:
    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakePdfReader:
        def __init__(self, _path: str) -> None:
            self.pages = [
                FakePage(""),
                FakePage("This page already contains enough text to skip OCR."),
            ]

    fake_pypdf = types.SimpleNamespace(PdfReader=FakePdfReader)
    fake_pdf2image = types.SimpleNamespace(convert_from_path=lambda _path: ["img-1", "img-2"])
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    monkeypatch.setitem(sys.modules, "pdf2image", fake_pdf2image)
    monkeypatch.setattr(ing, "_ocr_image_to_text", lambda image: "ocr-page-1" if image == "img-1" else "ocr-page-2")

    warnings: list[str] = []
    extracted = ing.extract_text_from_pdf(Path("dummy.pdf"), warnings=warnings)
    assert "ocr-page-1" in extracted
    assert "ocr-page-2" not in extracted
    assert "skip OCR" in extracted
    assert not warnings


def test_extract_text_from_pdf_falls_back_when_rendering_unavailable(monkeypatch) -> None:
    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakePdfReader:
        def __init__(self, _path: str) -> None:
            self.pages = [FakePage("Layer text survives without OCR.")]

    fake_pypdf = types.SimpleNamespace(PdfReader=FakePdfReader)

    def _raise_poppler(_path: str):
        raise RuntimeError("poppler not installed")

    fake_pdf2image = types.SimpleNamespace(convert_from_path=_raise_poppler)
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    monkeypatch.setitem(sys.modules, "pdf2image", fake_pdf2image)

    warnings: list[str] = []
    extracted = ing.extract_text_from_pdf(Path("dummy.pdf"), warnings=warnings)
    assert "Layer text survives without OCR." in extracted
    assert any("PDF OCR rendering unavailable" in warning for warning in warnings)


def test_extract_text_from_pptx_runs_ocr_on_picture_shapes(monkeypatch) -> None:
    class FakePicture:
        def __init__(self) -> None:
            self.image = types.SimpleNamespace(blob=b"binary-image")

    class FakeTextShape:
        text = "Slide title"

    class FakePresentation:
        def __init__(self, _path: str) -> None:
            self.slides = [types.SimpleNamespace(shapes=[FakeTextShape(), FakePicture()])]

    class FakeOpenedImage:
        def __enter__(self):
            return "opened-image"

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeImageModule:
        @staticmethod
        def open(_buffer):
            return FakeOpenedImage()

    class FakeUnidentifiedImageError(Exception):
        pass

    fake_pptx = types.SimpleNamespace(Presentation=FakePresentation)
    fake_picture_mod = types.SimpleNamespace(Picture=FakePicture)
    fake_pptx_shapes = types.ModuleType("pptx.shapes")
    monkeypatch.setitem(sys.modules, "pptx", fake_pptx)
    monkeypatch.setitem(sys.modules, "pptx.shapes", fake_pptx_shapes)
    monkeypatch.setitem(sys.modules, "pptx.shapes.picture", fake_picture_mod)
    monkeypatch.setitem(
        sys.modules,
        "PIL",
        types.SimpleNamespace(Image=FakeImageModule, UnidentifiedImageError=FakeUnidentifiedImageError),
    )
    monkeypatch.setattr(ing, "_ocr_image_to_text", lambda _image: "ocr-from-picture")

    warnings: list[str] = []
    extracted = ing.extract_text_from_pptx(Path("deck.pptx"), warnings=warnings)
    assert "Slide title" in extracted
    assert "ocr-from-picture" in extracted
    assert not warnings


def test_ingest_manifest_records_ocr_failures_without_crashing(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "flowchart.png"
    image_path.write_bytes(b"fake-image-content")

    manifest = InputManifest(
        process_name="Order Intake",
        context_region="ANZ",
        pain_points=["Manual entry"],
        files=[str(image_path)],
    )

    monkeypatch.setattr(ing, "detect_mime_type", lambda _path: "image/png")

    def _fail_extract(_path: Path, _mime: str, warnings: list[str] | None = None) -> str:
        raise RuntimeError("Tesseract executable not found")

    monkeypatch.setattr(ing, "extract_text", _fail_extract)

    result = ingest_manifest(manifest)
    assert result["documents"][0]["error"].startswith("Extraction failed:")
    assert any("Tesseract executable not found" in message for message in result["extraction_errors"])
