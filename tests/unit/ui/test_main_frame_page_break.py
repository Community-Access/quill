"""QUILL's Ctrl+Enter: a page break in Word, RTF, Markdown and braille.

``FormatCodesMixin.insert_page_break`` decides by the kind of document, and on a
link in a text document it still follows the link -- Ctrl+Enter was Follow
Link's key until 2026-11-03. Driven on a stub host, because the routing is the
thing under test; the rich surface's own insert is probed against a real
control in ``scripts`` and tested end to end through RTF and Word in
``tests/unit/io/test_docx_page_breaks.py``.
"""

from __future__ import annotations

from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.tagging import PAGE_BREAK_MARKER
from quill.ui.main_frame_format_codes import FormatCodesMixin


class _Editor:
    def __init__(self, text: str = "", caret: int = 0) -> None:
        self.text = text
        self.caret = caret

    def GetValue(self) -> str:
        return self.text

    def GetInsertionPoint(self) -> int:
        return self.caret

    def GetSelection(self) -> tuple[int, int]:
        return self.caret, self.caret

    def Replace(self, start: int, end: int, text: str) -> None:
        self.text = self.text[:start] + text + self.text[end:]

    def SetInsertionPoint(self, at: int) -> None:
        self.caret = at

    def SetFocus(self) -> None:
        pass


class _Rich:
    def __init__(self) -> None:
        self.breaks = 0

    def insert_page_break(self) -> None:
        self.breaks += 1


class _Host(FormatCodesMixin):
    def __init__(
        self,
        *,
        mode: str = "markup",
        surface: str | None = None,
        text: str = "",
        caret: int = 0,
        brf: bool = False,
    ) -> None:
        self.editor = _Editor(text, caret)
        self.rich = _Rich()
        self.mode = mode
        self.surface = surface
        self.brf = brf
        self.statuses: list[str] = []
        self.followed = 0
        self.braille_breaks = 0
        self.dirty = 0

    def _feature_enabled(self, _feature: str) -> bool:
        return True

    def _current_editor_mode(self) -> str:
        return self.mode

    def _active_richedit(self) -> _Rich:
        return self.rich

    def _mark_rich_formatting_dirty(self) -> None:
        self.dirty += 1

    def _active_markup_surface(self) -> str | None:
        return self.surface

    def _active_brf_resolver(self) -> object | None:
        return object() if self.brf else None

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)

    def follow_link(self) -> None:
        self.followed += 1

    def insert_braille_page_break(self) -> None:
        self.braille_breaks += 1


def test_ctrl_enter_is_insert_page_break_and_follow_link_gave_it_up() -> None:
    assert DEFAULT_KEYMAP["format.insert_page_break"] == "Ctrl+Enter"
    assert DEFAULT_KEYMAP["edit.follow_link"] == ""


def test_a_word_or_rtf_document_gets_a_real_page_break() -> None:
    host = _Host(mode="rich", text="see https://example.com", caret=8)
    host.insert_page_break()
    assert host.rich.breaks == 1
    assert host.dirty == 1
    assert host.followed == 0  # in Word, Ctrl+Enter always breaks the page
    assert host.statuses == ["Page break inserted"]


def test_on_a_link_in_a_text_document_it_still_follows_the_link() -> None:
    host = _Host(surface="markdown", text="[home](https://example.com)", caret=3)
    host.insert_page_break()
    assert host.followed == 1
    assert PAGE_BREAK_MARKER not in host.editor.text


def test_markdown_gets_the_page_break_line() -> None:
    host = _Host(surface="markdown", text="one", caret=3)
    host.insert_page_break()
    assert PAGE_BREAK_MARKER in host.editor.text


def test_braille_gets_a_braille_page() -> None:
    host = _Host(brf=True, text="abc", caret=1)
    host.insert_page_break()
    assert host.braille_breaks == 1


def test_plain_text_says_why() -> None:
    host = _Host(text="plain words", caret=2)
    host.insert_page_break()
    assert host.statuses == ["A page break needs a Word, Rich Text, Markdown or braille document"]
