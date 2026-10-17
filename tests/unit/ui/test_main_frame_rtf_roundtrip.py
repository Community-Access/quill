"""Source-contract test for EDS-21 RTF round-trip wiring in MainFrame.

The live MainFrame is not runtime-instantiated here; the repo validates UI wiring
through source contracts. The save path now delegates format selection to
``quill.io.export.write_document_as``, which routes ``.rtf`` targets through the
RTF io writer while other formats are converted to HTML/plain text or written
verbatim as Markdown. The open dispatch resolves ``.rtf`` via
``read_structured_document`` (which delegates to ``read_rtf_document``).
"""

from __future__ import annotations

from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)
EXPORT_SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "io" / "export.py").read_text(
    encoding="utf-8"
)


def test_imports_rtf_writer() -> None:
    assert "from quill.io.rtf import write_rtf_document" in EXPORT_SOURCE


def test_write_dispatch_routes_rtf() -> None:
    start = EXPORT_SOURCE.index("def write_document_as(")
    body = EXPORT_SOURCE[start:]
    assert "_RTF_SUFFIXES" in body
    assert "write_rtf_document(" in body
    assert "write_text_document(" in body
    assert "self._write_document_to_disk" not in body
    # MainFrame delegates to the wx-free dispatcher.
    assert "write_document_as(" in SOURCE


def test_save_file_uses_dispatch() -> None:
    start = SOURCE.index("def save_file(")
    next_def = SOURCE.index("\n    def ", start + 1)
    body = SOURCE[start:next_def]
    # Save's write step is shared with the clipboard collector's quiet save
    # since 2026-10-15 (main_frame_write_safety._write_named_document), so the
    # two cannot drift; the dispatch is one call further in.
    assert "self._write_named_document()" in body
    safety = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_write_safety.py"
    ).read_text(encoding="utf-8")
    start = safety.index("def _write_named_document(")
    next_def = safety.index("\n    def ", start + 1)
    assert "self._write_document_to_disk(self.document)" in safety[start:next_def]


def test_save_file_as_uses_dispatch() -> None:
    start = SOURCE.index("def save_file_as(")
    next_def = SOURCE.index("\n    def ", start + 1)
    body = SOURCE[start:next_def]
    assert "self._write_document_to_disk(self.document, target)" in body


def test_save_as_wildcard_offers_rtf() -> None:
    start = SOURCE.index("def save_file_as(")
    next_def = SOURCE.index("\n    def ", start + 1)
    body = SOURCE[start:next_def]
    assert "Rich Text Format (*.rtf)|*.rtf" in body
