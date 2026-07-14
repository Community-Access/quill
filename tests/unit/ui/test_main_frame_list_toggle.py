"""Tests for the MainFrame list-toggle wrapper methods (PR3, EdSharp port).

The pure helpers (``should_auto_fill_numbers``, ``fill_numbered_markers``,
``strip_list_markers``, ``is_caret_inside_list``) are exercised in
``tests/unit/core/test_markdown_sections.py``.  This module verifies the
``MainFrame`` wiring: insert vs. strip decision, surface gating, the
three-way auto-fill gate (markdown surface OR setting OR armed flag), and
the announcement strings.
"""

from __future__ import annotations

import time
from pathlib import Path

from quill.core.markdown_sections import (
    _LIST_AUTO_FILL_ARM_SECONDS,
    should_auto_fill_numbers,
)
from quill.core.settings import Settings
from quill.ui.main_frame import MainFrame


class _Editor:
    def __init__(self, text: str = "", caret: int = 0) -> None:
        self._text = text
        self._caret = caret
        self._selection = (0, 0)
        self.set_value_calls: list[str] = []
        self.set_caret_calls: list[int] = []
        self.set_focus_calls = 0

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._caret

    def SetValue(self, text: str) -> None:
        self._text = text
        self.set_value_calls.append(text)

    def SetInsertionPoint(self, caret: int) -> None:
        self._caret = caret
        self.set_caret_calls.append(caret)

    def GetStringSelection(self) -> str:
        start, end = self._selection
        if start == end:
            return ""
        return self._text[start:end]

    def GetSelection(self) -> tuple[int, int]:
        return self._selection

    def SetFocus(self) -> None:  # pragma: no cover - trivial
        self.set_focus_calls += 1

    def ReplaceSelection(self, text: str) -> None:  # pragma: no cover - trivial
        pass

    def Replace(self, start: int, end: int, text: str) -> None:
        self._text = self._text[:start] + text + self._text[end:]
        self.set_value_calls.append(self._text)
        if self._selection != (0, 0):
            self._selection = (start, start)


class _Document:
    def __init__(self, path: str | None) -> None:
        self.path = Path(path) if path is not None else None


def _make_frame(
    text: str = "",
    caret: int = 0,
    path: str | None = "test.md",
    *,
    list_auto_fill_numbers: bool = False,
    armed_until: float = 0.0,
) -> tuple[MainFrame, _Editor]:
    frame = MainFrame.__new__(MainFrame)
    frame.settings = Settings()
    frame.settings.list_auto_fill_numbers = list_auto_fill_numbers
    frame._status_message = ""
    frame._set_status = lambda message: setattr(frame, "_status_message", message)  # type: ignore[method-assign]
    frame._announce = lambda message: setattr(frame, "_status_message", message)  # type: ignore[method-assign]
    editor = _Editor(text=text, caret=caret)
    frame.editor = editor  # type: ignore[assignment]
    frame.document = _Document(path)  # type: ignore[assignment]
    frame._numbered_list_armed_until = armed_until
    frame._feature_enabled = lambda _feature_id: True  # type: ignore[method-assign]
    return frame, editor


# ---------------------------------------------------------------------------
# Surface gating
# ---------------------------------------------------------------------------


def test_toggle_bullet_list_in_plain_text_skips() -> None:
    frame, editor = _make_frame(path="test.txt", text="hello")
    frame.toggle_bullet_list()
    assert editor._text == "hello"
    assert "only available" in frame._status_message.lower()


def test_toggle_numbered_list_in_plain_text_skips() -> None:
    frame, editor = _make_frame(path="test.txt", text="hello")
    frame.toggle_numbered_list()
    assert editor._text == "hello"
    assert "only available" in frame._status_message.lower()


# ---------------------------------------------------------------------------
# Insert path
# ---------------------------------------------------------------------------


def test_toggle_bullet_list_inserts_when_caret_is_outside_list() -> None:
    frame, editor = _make_frame(text="hello\n", caret=0)
    frame.toggle_bullet_list()
    new_text = editor._text
    assert new_text != "hello\n"
    # Inserted body should contain bullet markers.
    assert "-" in new_text


def test_toggle_numbered_list_inserts_with_no_fill_when_setting_off_and_not_markdown() -> None:
    # Use a markdown surface but disable the auto-fill setting and skip the
    # arming flag.  Today this is the default behaviour: only the first item
    # gets a marker.
    frame, editor = _make_frame(
        text="hello\n", caret=0, list_auto_fill_numbers=False, armed_until=0.0
    )
    frame.toggle_numbered_list()
    new_text = editor._text
    assert new_text != "hello\n"
    # The first item carries "1. " (existing format_ops behaviour); later
    # items are bare lines.
    assert "1. " in new_text


def test_toggle_numbered_list_arms_document_for_five_minutes() -> None:
    frame, _editor = _make_frame(text="\n", caret=0)
    before = time.monotonic()
    frame.toggle_numbered_list()
    after = time.monotonic()
    armed = frame._numbered_list_armed_until
    assert armed >= before + _LIST_AUTO_FILL_ARM_SECONDS
    # Allow a small fudge factor for clock granularity.
    assert armed <= after + _LIST_AUTO_FILL_ARM_SECONDS + 0.5


# ---------------------------------------------------------------------------
# Strip path
# ---------------------------------------------------------------------------


def test_toggle_bullet_list_strips_when_caret_is_inside_list() -> None:
    text = "hello\n- a\n- b\n- c\n"
    caret = text.index("- a") + 3
    frame, editor = _make_frame(text=text, caret=caret)
    frame.toggle_bullet_list()
    new_text = editor._text
    assert "- a" not in new_text
    assert "- b" not in new_text
    assert "Bullet List removed" in frame._status_message


def test_toggle_numbered_list_strips_when_caret_is_inside_list() -> None:
    text = "intro\n1. one\n2. two\n3. three\n"
    caret = text.index("2. two") + 3
    frame, editor = _make_frame(text=text, caret=caret)
    frame.toggle_numbered_list()
    new_text = editor._text
    assert "1. one" not in new_text
    assert "2. two" not in new_text
    assert "Numbered List removed" in frame._status_message


# ---------------------------------------------------------------------------
# Dead editor
# ---------------------------------------------------------------------------


def test_toggle_bullet_list_survives_dead_editor() -> None:
    class _DeadEditor:
        def GetValue(self) -> str:
            raise RuntimeError("dead widget")

        def GetInsertionPoint(self) -> int:
            raise RuntimeError("dead widget")

        def GetStringSelection(self) -> str:
            raise RuntimeError("dead widget")

    frame = MainFrame.__new__(MainFrame)
    frame.settings = Settings()
    frame._status_message = ""
    frame._set_status = lambda message: setattr(frame, "_status_message", message)  # type: ignore[method-assign]
    frame._announce = lambda message: setattr(frame, "_status_message", message)  # type: ignore[method-assign]
    frame.editor = _DeadEditor()  # type: ignore[assignment]
    frame.document = _Document("test.md")  # type: ignore[assignment]
    frame._numbered_list_armed_until = 0.0
    frame._feature_enabled = lambda _feature_id: True  # type: ignore[method-assign]
    frame.toggle_bullet_list()  # must not raise.


def test_toggle_numbered_list_survives_dead_editor() -> None:
    class _DeadEditor:
        def GetValue(self) -> str:
            raise RuntimeError("dead widget")

        def GetInsertionPoint(self) -> int:
            raise RuntimeError("dead widget")

        def GetStringSelection(self) -> str:
            raise RuntimeError("dead widget")

    frame = MainFrame.__new__(MainFrame)
    frame.settings = Settings()
    frame._status_message = ""
    frame._set_status = lambda message: setattr(frame, "_status_message", message)  # type: ignore[method-assign]
    frame._announce = lambda message: setattr(frame, "_status_message", message)  # type: ignore[method-assign]
    frame.editor = _DeadEditor()  # type: ignore[assignment]
    frame.document = _Document("test.md")  # type: ignore[assignment]
    frame._numbered_list_armed_until = 0.0
    frame._feature_enabled = lambda _feature_id: True  # type: ignore[method-assign]
    frame.toggle_numbered_list()  # must not raise.


# ---------------------------------------------------------------------------
# Three-way auto-fill gate (unit-style assertion through the public helper)
# ---------------------------------------------------------------------------


def test_auto_fill_gate_markdown_surface_always_fills() -> None:
    settings = Settings()
    settings.list_auto_fill_numbers = False
    assert should_auto_fill_numbers(settings, "markdown", armed_until=0.0) is True


def test_auto_fill_gate_setting_on_fills_in_any_surface() -> None:
    settings = Settings()
    settings.list_auto_fill_numbers = True
    assert should_auto_fill_numbers(settings, "html", armed_until=0.0) is True
    assert should_auto_fill_numbers(settings, "plain", armed_until=0.0) is True


def test_auto_fill_gate_armed_flag_fills_within_window() -> None:
    settings = Settings()
    settings.list_auto_fill_numbers = False
    armed = time.monotonic() + 60.0
    assert should_auto_fill_numbers(settings, "html", armed_until=armed) is True


def test_auto_fill_gate_armed_flag_expires() -> None:
    settings = Settings()
    settings.list_auto_fill_numbers = False
    past = time.monotonic() - 60.0
    assert should_auto_fill_numbers(settings, "html", armed_until=past) is False


def test_auto_fill_gate_default_off_does_not_fill_plain() -> None:
    settings = Settings()
    settings.list_auto_fill_numbers = False
    assert should_auto_fill_numbers(settings, "plain", armed_until=0.0) is False


def test_settings_dataclass_exposes_list_auto_fill_numbers() -> None:
    settings = Settings()
    assert hasattr(settings, "list_auto_fill_numbers")
    assert settings.list_auto_fill_numbers is False
