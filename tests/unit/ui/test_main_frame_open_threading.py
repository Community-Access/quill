from __future__ import annotations

from pathlib import Path

from quill.ui.main_frame import MainFrame

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_open_reads_heavy_office_formats_off_the_ui_thread() -> None:
    # PERF-12: large office/PDF reads must run on a worker thread so the UI
    # thread never blocks while parsing them.
    assert "from quill.io.open_read import read_open_document" in SOURCE
    assert "if suffix in _OFFICE_STREAM_SUFFIXES:" in SOURCE
    # The office branch dispatches the read through the background-task helper.
    assert "self._run_background_task(" in SOURCE
    assert (
        "lambda _progress: read_open_document(\n"
        "                    selected_path, suffix, word_mode=word_mode, docx_engine=docx_engine\n"
        "                )"
    ) in SOURCE


def test_open_resolves_word_prompt_before_leaving_the_ui_thread() -> None:
    # The Word open-mode chooser is a wx dialog, so it must be resolved on the
    # UI thread before the worker (which must not touch wx) starts.
    index = SOURCE.index("if suffix in _OFFICE_STREAM_SUFFIXES:")
    branch = SOURCE[index : index + 800]
    assert "self._resolve_word_open_mode(selected_path)" in branch
    assert "_run_background_task" in branch
    # The prompt resolution appears before the worker dispatch.
    assert branch.index("self._resolve_word_open_mode(selected_path)") < branch.index(
        "_run_background_task"
    )


def test_finish_open_document_runs_on_the_ui_thread() -> None:
    assert "def _finish_open_document(" in SOURCE
    assert 'self._epub_book = epub_book if suffix == ".epub" else None' in SOURCE


def test_main_frame_class_is_importable() -> None:
    assert MainFrame is not None


def test_pdf_open_needs_password_detects_encrypted_pdf_only() -> None:
    # #58: the open flow diverts to a password prompt only for a PDF whose read
    # came back tagged engine="encrypted"; any other engine or suffix installs
    # normally.
    frame = MainFrame.__new__(MainFrame)

    class _Doc:
        pass

    doc = _Doc()
    doc.source_metadata = {"source_kind": "pdf", "engine": "encrypted"}
    assert frame._pdf_open_needs_password(doc, ".pdf") is True

    doc.source_metadata = {"source_kind": "pdf", "engine": "pdfplumber"}
    assert frame._pdf_open_needs_password(doc, ".pdf") is False

    # An "encrypted" tag on a non-PDF, or a document with no metadata, never
    # triggers the PDF password prompt.
    doc.source_metadata = {"engine": "encrypted"}
    assert frame._pdf_open_needs_password(doc, ".docx") is False
    doc.source_metadata = None
    assert frame._pdf_open_needs_password(doc, ".pdf") is False


def test_unique_outline_bookmark_name_dedupes_and_collapses_whitespace() -> None:
    frame = MainFrame.__new__(MainFrame)
    used: set[str] = set()
    a = frame._unique_outline_bookmark_name("Chapter 1", used)
    used.add(a)
    b = frame._unique_outline_bookmark_name("Chapter 1", used)
    used.add(b)
    c = frame._unique_outline_bookmark_name("Chapter\n  1", used)  # collapses to "Chapter 1"
    assert a == "Chapter 1"
    assert b == "Chapter 1 (2)"
    assert c == "Chapter 1 (3)"


def test_pdf_outline_import_is_wired_into_open_and_guards_correctly() -> None:
    # The open flow imports a PDF's embedded outline as bookmarks (source-level
    # guards: PDF-only, first-open-only, resolved via page markers).
    assert "self._import_pdf_outline_bookmarks(loaded, suffix)" in SOURCE
    assert 'if suffix != ".pdf":' in SOURCE
    assert 'outline = metadata.get("pdf_outline")' in SOURCE
    # Idempotent: skip when the document already has bookmarks.
    assert 'if getattr(tab, "bookmarks", None):' in SOURCE
    # Page number -> character offset via the shared page-marker helper.
    assert "page_start_for_number(text, int(page))" in SOURCE


def test_encrypted_pdf_open_prompts_and_rereads_with_password() -> None:
    # #58: _finish_open_document diverts an encrypted PDF to the password prompt,
    # and the prompt re-reads the file with the entered password (threaded as
    # pdf_password), looping via encrypted_retry until it opens or is cancelled.
    assert "if self._pdf_open_needs_password(loaded, suffix):" in SOURCE
    assert "self._prompt_and_reopen_encrypted_pdf(" in SOURCE
    assert "read_open_document(selected_path, suffix, pdf_password=password)" in SOURCE
    # A wrong password re-enters the finish path flagged as a retry so the prompt
    # can say "that password did not open ...".
    assert "encrypted_retry=True" in SOURCE
    # The password is collected on the UI thread through the modal-dialog helper.
    assert "wx.PasswordEntryDialog(" in SOURCE
    assert 'self._show_modal_dialog(dialog, "Open Password-Protected PDF")' in SOURCE
