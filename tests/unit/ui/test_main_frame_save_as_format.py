from __future__ import annotations

from pathlib import Path

from quill.ui.main_frame import MainFrame


def _frame() -> MainFrame:
    return MainFrame.__new__(MainFrame)


def test_typed_extension_is_honored_over_filter() -> None:
    frame = _frame()
    # User typed .txt but the HTML filter (index 2) was highlighted: keep .txt.
    assert frame._resolve_save_target(Path("notes.txt"), 2) == Path("notes.txt")


def test_missing_extension_uses_text_filter() -> None:
    frame = _frame()
    assert frame._resolve_save_target(Path("notes"), 0) == Path("notes.txt")


def test_missing_extension_uses_markdown_filter() -> None:
    frame = _frame()
    assert frame._resolve_save_target(Path("notes"), 1) == Path("notes.md")


def test_missing_extension_uses_html_filter() -> None:
    frame = _frame()
    assert frame._resolve_save_target(Path("notes"), 2) == Path("notes.html")


def test_missing_extension_uses_rtf_filter() -> None:
    frame = _frame()
    assert frame._resolve_save_target(Path("notes"), 3) == Path("notes.rtf")


def test_missing_extension_uses_word_filter() -> None:
    frame = _frame()
    assert frame._resolve_save_target(Path("notes"), 4) == Path("notes.docx")


def test_all_files_filter_defaults_to_markdown() -> None:
    frame = _frame()
    # "All files" is now filter index 5 (after Word at 4); unknown indices fall
    # back to Markdown.
    assert frame._resolve_save_target(Path("notes"), 5) == Path("notes.md")
    assert frame._resolve_save_target(Path("notes"), -1) == Path("notes.md")


def test_no_double_extension_created() -> None:
    frame = _frame()
    result = frame._resolve_save_target(Path("report.txt"), 2)
    assert result.suffix == ".txt"
    assert str(result).count(".") == 1


# --------------------------------------------------------------------------- #
# source contract: save wiring
# --------------------------------------------------------------------------- #
_SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_surface_sync_machinery_stays_retired() -> None:
    # The post-Save-As surface reload sync retired with the Rich text lens
    # (One Editor, Every Format): retargeting is now the Document Format
    # switcher's explicit job. Pin the absence so it does not creep back.
    assert "_maybe_reload_surface_after_save_as" not in _SOURCE
    assert "_resolve_surface_sync" not in _SOURCE
    assert "save_as_surface_sync" not in _SOURCE


def test_save_file_redirects_when_format_retargeted() -> None:
    # The Document Format switcher retargets the file type; Save must propose
    # the renamed path through Save As, never silently rewrite in place.
    start = _SOURCE.index("def save_file(")
    body = _SOURCE[start : _SOURCE.index("\n    def ", start + 1)]
    assert "_pending_format_redirect" in body


def test_export_route_for_suffix() -> None:
    # Pandoc-capable targets get routed to File > Export; the rest are refused.
    assert MainFrame._export_route_for_suffix(".pdf") == "pdf"
    assert MainFrame._export_route_for_suffix(".ODT") == "odt"
    assert MainFrame._export_route_for_suffix(".epub") == "epub"
    assert MainFrame._export_route_for_suffix(".xlsx") is None
    assert MainFrame._export_route_for_suffix(".docx") is None


def test_save_file_guards_export_only_originals() -> None:
    # Ctrl-S on an opened PDF/EPUB/spreadsheet must never write text over the
    # binary original; it explains and routes to Save As instead.
    start = _SOURCE.index("def save_file(")
    body = _SOURCE[start : _SOURCE.index("\n    def ", start + 1)]
    assert "EXPORT_ONLY_SUFFIXES" in body
    assert "self.save_file_as()" in body


def test_save_file_as_offers_export_for_export_only_suffixes() -> None:
    start = _SOURCE.index("def save_file_as(")
    body = _SOURCE[start : _SOURCE.index("\n    def ", start + 1)]
    assert "EXPORT_ONLY_SUFFIXES" in body
    assert "_export_route_for_suffix" in body
    assert "self.export_document(" in body


def test_save_file_as_reports_write_failures() -> None:
    # A failed conversion/write must not crash or claim success.
    start = _SOURCE.index("def save_file_as(")
    body = _SOURCE[start : _SOURCE.index("\n    def ", start + 1)]
    assert "except OSError" in body
    assert "Could not save" in body


def test_save_file_as_announces_format_conversion() -> None:
    # After a converting Save As (.docx/.rtf/HTML) the screen reader hears what
    # actually happened: the file is Word/RTF/HTML on disk, but the editor still
    # holds QUILL text and each save re-converts.
    start = _SOURCE.index("def save_file_as(")
    body = _SOURCE[start : _SOURCE.index("\n    def ", start + 1)]
    assert "_announce_save_as_conversion(target)" in body


def test_announce_save_as_conversion_wording() -> None:
    spoken: list[str] = []
    frame = _frame()
    frame._announce = spoken.append  # type: ignore[method-assign]
    frame._announce_save_as_conversion(Path("report.docx"))
    assert spoken == [
        "Saved as report.docx, Word format. You are still editing QUILL text; "
        "each save converts it to Word."
    ]
    spoken.clear()
    # Non-converting formats stay quiet: the status line already covers them.
    frame._announce_save_as_conversion(Path("notes.md"))
    frame._announce_save_as_conversion(Path("notes.txt"))
    assert spoken == []


def test_export_document_preserves_editor_line_breaks() -> None:
    # The editor is line-oriented: one editor line is one paragraph. Bare "gfm"
    # treats a single newline as a soft wrap, which joined all of a user's lines
    # into one long paragraph in every Pandoc export (Caroline's report).
    start = _SOURCE.index("def export_document(")
    body = _SOURCE[start : _SOURCE.index("\n    def ", start + 1)]
    assert 'from_format="gfm+hard_line_breaks"' in body
    assert 'from_format="gfm",' not in body


def test_reload_in_place_reads_before_closing() -> None:
    start = _SOURCE.index("def _reload_in_place(")
    body = _SOURCE[start : _SOURCE.index("\n    def ", start + 1)]
    # The file must be read before the current tab is deleted so a read failure
    # leaves the live document intact.
    read_at = body.index("read_open_document(")
    delete_at = body.index("DeletePage(")
    assert read_at < delete_at
