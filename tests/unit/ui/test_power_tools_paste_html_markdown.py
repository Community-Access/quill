"""Behavior tests for EDS paste-HTML-as-Markdown (QUILL key, then M)."""

from __future__ import annotations

from quill.ui.main_frame_power_tools import PowerToolsActionsMixin


class _Harness(PowerToolsActionsMixin):
    """Minimal stand-in exercising the clipboard-to-insert path."""

    def __init__(self, *, html: str = "", plain: str = "", read_only: bool = False) -> None:
        self._html = html
        self._plain = plain
        self._read_only = read_only
        self.inserted: str | None = None
        self.status: str | None = None

    def _power_tools_clipboard_html(self) -> str:  # type: ignore[override]
        return self._html

    def _power_tools_clipboard_text(self) -> str:  # type: ignore[override]
        return self._plain

    def _document_is_read_only(self) -> bool:  # type: ignore[override]
        return self._read_only

    def _power_tools_insert_at_cursor(self, snippet: str, status: str) -> None:  # type: ignore[override]
        if self._read_only:
            self.status = "Document is read-only"
            return
        self.inserted = snippet
        self.status = status

    def _set_status(self, message: str) -> None:  # type: ignore[override]
        self.status = message


def test_paste_html_inserts_markdown() -> None:
    harness = _Harness(html="<h1>Title</h1><p>Body</p>")
    harness.paste_html_as_markdown()
    assert harness.inserted is not None
    assert "# Title" in harness.inserted
    assert harness.status == "Pasted HTML as Markdown"


def test_paste_falls_back_to_plain_text_as_html() -> None:
    harness = _Harness(html="", plain="<p>From <strong>plain</strong></p>")
    harness.paste_html_as_markdown()
    assert harness.inserted is not None
    assert "**plain**" in harness.inserted


def test_paste_empty_clipboard_reports_status() -> None:
    harness = _Harness(html="", plain="")
    harness.paste_html_as_markdown()
    assert harness.inserted is None
    assert harness.status == "Clipboard is empty"


def test_paste_respects_read_only_guard() -> None:
    harness = _Harness(html="<p>Body</p>", read_only=True)
    harness.paste_html_as_markdown()
    assert harness.inserted is None
    assert harness.status == "Document is read-only"


def test_paste_non_html_text_with_no_markup_still_inserts() -> None:
    harness = _Harness(html="", plain="just words")
    harness.paste_html_as_markdown()
    assert harness.inserted is not None
    assert "just words" in harness.inserted


def test_paste_markdown_inserts_html_fragment() -> None:
    harness = _Harness(plain="# Title\n\nBody with **bold**.")
    harness.paste_markdown_as_html()
    assert harness.inserted is not None
    assert "<h1" in harness.inserted and "Title" in harness.inserted
    assert "<strong>bold</strong>" in harness.inserted
    assert "<html" not in harness.inserted, "must be a body fragment, not a page"
    assert harness.status == "Pasted Markdown as HTML"


def test_paste_markdown_empty_clipboard_reports_status() -> None:
    harness = _Harness(plain="")
    harness.paste_markdown_as_html()
    assert harness.inserted is None
    assert harness.status == "Clipboard is empty"


def test_paste_markdown_respects_read_only_guard() -> None:
    harness = _Harness(plain="# Title", read_only=True)
    harness.paste_markdown_as_html()
    assert harness.inserted is None
    assert harness.status == "Document is read-only"
