"""Convert File engine choice: applicability policy and dialog/source contracts."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.ui.main_frame import MainFrame

_ROOT = Path(__file__).resolve().parents[3]
_FRAME_SOURCE = (_ROOT / "quill" / "ui" / "main_frame.py").read_text(encoding="utf-8")
_DIALOG_SOURCE = (_ROOT / "quill" / "ui" / "convert_file_dialog.py").read_text(encoding="utf-8")


def _request(source: str, token: str) -> SimpleNamespace:
    return SimpleNamespace(source_path=Path(source), output_token=token)


def test_markitdown_applies_to_office_and_pdf_into_markdown() -> None:
    assert MainFrame._markitdown_convert_applies(_request("a.docx", "gfm"))
    assert MainFrame._markitdown_convert_applies(_request("a.pptx", "markdown"))
    assert MainFrame._markitdown_convert_applies(_request("a.xlsx", "commonmark"))
    assert MainFrame._markitdown_convert_applies(_request("a.pdf", "plain"))


def test_markitdown_refused_for_other_routes() -> None:
    # Wrong source: MarkItDown cannot read Markdown or HTML.
    assert not MainFrame._markitdown_convert_applies(_request("a.md", "gfm"))
    assert not MainFrame._markitdown_convert_applies(_request("a.html", "plain"))
    # Wrong output: MarkItDown only produces Markdown/plain text.
    assert not MainFrame._markitdown_convert_applies(_request("a.docx", "docx"))
    assert not MainFrame._markitdown_convert_applies(_request("a.pdf", "epub"))


def test_convert_file_honors_engine_choice() -> None:
    # The handler must consult the request's engine, never silently substitute
    # one the user did not pick, and route MarkItDown conversions to the bridge.
    start = _FRAME_SOURCE.index("def convert_file(")
    body = _FRAME_SOURCE[start : _FRAME_SOURCE.index("\n    def ", start + 1)]
    assert 'getattr(request, "engine", "auto")' in body
    assert "_markitdown_convert_applies(request)" in body
    assert "convert_with_markitdown(request.source_path)" in body
    assert "Convert with Pandoc instead?" in body


def test_dialog_offers_engine_choice_with_descriptions() -> None:
    # The dialog exposes an accessible engine choice whose description text
    # follows the selection, and the request carries the chosen engine token.
    assert "Conversion &engine" in _DIALOG_SOURCE
    assert "_sync_engine_description" in _DIALOG_SOURCE
    assert "engine=self._current_engine()" in _DIALOG_SOURCE
    assert 'engine: str = "auto"' in _DIALOG_SOURCE
