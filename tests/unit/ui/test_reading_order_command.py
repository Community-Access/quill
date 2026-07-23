"""Tests for the Improve Reading Order command (PRD §5.6)."""

from __future__ import annotations

from pathlib import Path

from quill.ui.main_frame import MainFrame

SOURCE_DIR = Path(__file__).resolve().parents[3] / "quill" / "ui"
_MAIN = (SOURCE_DIR / "main_frame.py").read_text(encoding="utf-8")
_COMMANDS = (SOURCE_DIR / "main_frame_commands.py").read_text(encoding="utf-8")
_MENU = (SOURCE_DIR / "main_frame_menu.py").read_text(encoding="utf-8")
_BINDINGS = (SOURCE_DIR / "main_frame_menu_bindings.py").read_text(encoding="utf-8")


class _Editor:
    def __init__(self, text: str) -> None:
        self._text = text

    def GetValue(self) -> str:
        return self._text


class _Doc:
    def __init__(self, metadata: dict | None) -> None:
        self.source_metadata = metadata


def _bare_frame(*, text: str, safe_mode: bool = False, metadata: dict | None = None) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame._wx = object()
    frame._safe_mode = safe_mode
    frame.editor = _Editor(text)
    frame.document = _Doc(metadata)

    class _S:
        reading_order_max_pages = 40
        page_estimate_words_per_page = 300

    frame.settings = _S()
    frame._status: list[str] = []
    frame._set_status = frame._status.append  # type: ignore[method-assign]
    return frame


def test_safe_mode_blocks_reading_order() -> None:
    frame = _bare_frame(text="some real text", safe_mode=True)
    frame.open_ai_improve_reading_order()
    assert frame._status and "Safe Mode" in frame._status[-1]


def test_empty_document_is_refused() -> None:
    frame = _bare_frame(text="   \n  ")
    frame.open_ai_improve_reading_order()
    assert frame._status and "Nothing to improve" in frame._status[-1]


def test_page_count_prefers_pdf_metadata() -> None:
    frame = _bare_frame(text="short", metadata={"page_count": 12})
    assert frame._reading_order_page_count("short") == 12


def test_page_count_uses_form_feeds_when_no_metadata() -> None:
    frame = _bare_frame(text="a\fb\fc", metadata=None)
    assert frame._reading_order_page_count("a\fb\fc") == 3


def test_page_count_estimates_from_words_when_unpaginated() -> None:
    frame = _bare_frame(text="", metadata=None)
    words = " ".join(["word"] * 900)  # 900 words / 300 per page = 3 pages
    assert frame._reading_order_page_count(words) == 3


def test_over_page_limit_is_refused_before_any_send() -> None:
    frame = _bare_frame(text="body", metadata={"page_count": 41})
    frame.open_ai_improve_reading_order()
    assert frame._status and "over the 40-page limit" in frame._status[-1]


def test_command_is_registered_menu_wired_and_bound() -> None:
    assert "ReadingOrderMixin," in _MAIN
    assert '"tools.ai_reading_order"' in _COMMANDS
    assert "self.open_ai_improve_reading_order" in _COMMANDS
    assert 'self._menu_label(_("Improve &Reading Order..."), "tools.ai_reading_order")' in _MENU
    assert "self.open_ai_improve_reading_order()" in _BINDINGS


def test_result_opens_as_new_unsaved_document() -> None:
    # The result is opened as a new buffer, never replacing the current document.
    ui_mixin = (SOURCE_DIR / "main_frame_ai_reading_order.py").read_text(encoding="utf-8")
    assert "_power_tools_open_text_in_new_buffer" in ui_mixin
    assert 'transform("reading_order", text)' in ui_mixin
    # Always confirms before sending.
    assert "_confirm_reading_order_send" in ui_mixin
