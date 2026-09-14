"""Arrowing onto a misspelled word says so, and Shift+F10 answers about it.

Both reported on 2026-09-12, and both are the same missing question asked twice.

QuillLite's only spelling check was the as-you-type one, which asks
``misspelling_behind`` -- the word you have just *finished* -- and every key
including an arrow restarted it. So arrowing down onto a line often fired (the
word behind the caret happened to be the misspelled one) and arrowing right into
that same word never did (there is no finished word behind the caret). "Which
word am I standing in" was never asked.

The context menu had the opposite shape of gap: the logic was right and tested,
and the *event* that reaches it was not. A right-click always worked; Shift+F10
on a subclassed native RichEdit is not something wxMSW can be relied on to turn
into a context-menu event. Tests that call the builder directly cannot see that
-- which is the F8 bug's shape exactly, so the key path is driven here.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.apps.lite_window_spelling import DocumentSpellingMixin


class _Control:
    def __init__(self, text: str, cursor: int) -> None:
        self._text = text
        self._cursor = cursor
        self.popped = 0

    def GetValue(self) -> str:  # noqa: N802 - wx API shape
        return self._text

    def GetInsertionPoint(self) -> int:  # noqa: N802 - wx API shape
        return self._cursor

    def SetInsertionPoint(self, position: int) -> None:  # noqa: N802 - wx API shape
        self._cursor = position

    def PopupMenu(self, _menu: Any, _point: Any = None) -> None:  # noqa: N802 - wx API shape
        self.popped += 1


class _Settings:
    spell_check_while_typing = True
    spelling_alert_sound = True
    spelling_alert_speech = False
    spelling_alert_repeat_ms = 750
    share_quill_dictionary = False


class _App:
    def __init__(self) -> None:
        self.settings = _Settings()
        self.data_dir = None

    def feature_enabled(self, _area: str) -> bool:
        return True


class _Window(DocumentSpellingMixin):
    """The spelling mixin over a fake control, with the outputs recorded."""

    def __init__(self, text: str, cursor: int) -> None:
        self.control = _Control(text, cursor)
        self.app = _App()
        self.path = None
        self.announcements: list[str] = []
        self.status: list[str] = []
        self.cues: list[str] = []
        self._live_spelling = True
        self._spell_timer = None
        self._spell_dictionary_cache: set[str] | None = None
        self._last_live_word = None
        self._last_live_alert_at = 0.0

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _set_status_message(self, message: str) -> None:
        self.status.append(message)

    def _spelling_enabled(self) -> bool:
        return True

    def _spell_dictionary(self) -> set[str]:
        return set()

    def _play_spelling_alert(self) -> None:
        self.cues.append("spelling-alert")

    @property
    def spell_ignores(self):  # type: ignore[no-untyped-def]
        from quill.core.spelling.context_menu import IgnoreList

        if getattr(self, "_ignores", None) is None:
            self._ignores = IgnoreList()
        return self._ignores


#: "recieve" is misspelled; the caret positions below are inside it.
TEXT = "I recieve mail"
WORD_START = 2
WORD_MIDDLE = 5


# ---------------------------------------------------------------------------
# Arrowing onto the word


@pytest.mark.parametrize("caret", [WORD_START, WORD_MIDDLE, WORD_START + 6])
def test_landing_anywhere_in_the_word_reports_it(caret: int) -> None:
    """The start, the middle and the last letter are all "this word"."""
    window = _Window(TEXT, caret)
    window.check_spelling_at_caret(wx.WXK_RIGHT)
    assert window.cues == ["spelling-alert"]
    assert window.status and "recieve" in window.status[0]


def test_moving_by_word_reports_it_too() -> None:
    """Ctrl+Right lands on the first character, which used to report the word
    *before* it or nothing at all."""
    window = _Window(TEXT, WORD_START)
    window.check_spelling_at_caret(wx.WXK_RIGHT)
    assert window.cues == ["spelling-alert"]


def test_a_line_move_still_reports() -> None:
    window = _Window(TEXT, WORD_MIDDLE)
    window.check_spelling_at_caret(wx.WXK_DOWN)
    assert window.cues == ["spelling-alert"]


def test_a_click_reports_it(cue_free_key: int = 0) -> None:
    """EVT_LEFT_UP carries no key code, and a click is navigation by any
    reading."""
    window = _Window(TEXT, WORD_MIDDLE)
    window.check_spelling_at_caret(cue_free_key)
    assert window.cues == ["spelling-alert"]


def test_a_correctly_spelled_word_says_nothing() -> None:
    window = _Window("I receive mail", WORD_MIDDLE)
    window.check_spelling_at_caret(wx.WXK_RIGHT)
    assert window.cues == []
    assert window.status == []


def test_typing_is_not_navigation() -> None:
    """A letter key must not reach this path: judging the word under the caret
    while it is still being typed reports every word as wrong on its way to
    being right, which is what the as-you-type check exists to avoid."""
    window = _Window(TEXT, WORD_MIDDLE)
    window.check_spelling_at_caret(ord("a"))
    assert window.cues == []


def test_arrowing_back_and_forth_over_one_word_does_not_drum() -> None:
    """Shared throttle state with the typing path: one word, one alert."""
    window = _Window(TEXT, WORD_MIDDLE)
    window.check_spelling_at_caret(wx.WXK_RIGHT)
    window.check_spelling_at_caret(wx.WXK_LEFT)
    window.check_spelling_at_caret(wx.WXK_RIGHT)
    assert window.cues == ["spelling-alert"]


def test_the_spelling_area_switched_off_says_nothing(monkeypatch) -> None:
    window = _Window(TEXT, WORD_MIDDLE)
    monkeypatch.setattr(window, "_spelling_enabled", lambda: False)
    window.check_spelling_at_caret(wx.WXK_RIGHT)
    assert window.cues == []


def test_live_spelling_switched_off_says_nothing() -> None:
    window = _Window(TEXT, WORD_MIDDLE)
    window._live_spelling = False
    window.check_spelling_at_caret(wx.WXK_RIGHT)
    assert window.cues == []


def test_a_broken_control_never_breaks_the_caret(monkeypatch) -> None:
    """A spell check must never be the reason an arrow key stops working."""

    def _explode() -> str:
        raise RuntimeError("the control went away")

    window = _Window(TEXT, WORD_MIDDLE)
    monkeypatch.setattr(window.control, "GetValue", _explode)
    window.check_spelling_at_caret(wx.WXK_RIGHT)  # must not raise
    assert window.cues == []


def test_speech_is_off_by_default_and_the_status_bar_carries_it() -> None:
    """Speaking over a listener who is moving through their own document is the
    thing the earcon exists to avoid."""
    window = _Window(TEXT, WORD_MIDDLE)
    window.check_spelling_at_caret(wx.WXK_RIGHT)
    assert window.announcements == []
    assert window.status == ['Possible misspelling: "recieve"']


def test_asking_for_speech_gets_speech() -> None:
    window = _Window(TEXT, WORD_MIDDLE)
    window.app.settings.spelling_alert_speech = True
    window.check_spelling_at_caret(wx.WXK_RIGHT)
    assert window.announcements == ['Possible misspelling: "recieve"']


# ---------------------------------------------------------------------------
# Shift+F10 and the Applications key


class _KeyEvent:
    """A wx.KeyEvent's shape, with the modifiers the check actually reads."""

    def __init__(self, code: int, *, shift: bool = False, ctrl: bool = False, alt: bool = False):
        self._code = code
        self._shift = shift
        self._ctrl = ctrl
        self._alt = alt
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802 - wx API shape
        return self._code

    def ShiftDown(self) -> bool:  # noqa: N802 - wx API shape
        return self._shift

    def ControlDown(self) -> bool:  # noqa: N802 - wx API shape
        return self._ctrl

    def AltDown(self) -> bool:  # noqa: N802 - wx API shape
        return self._alt

    def Skip(self) -> None:  # noqa: N802 - wx API shape
        self.skipped = True


def _is_menu_key(event: _KeyEvent) -> bool:
    from quill.apps.lite_window_typing import DocumentTypingMixin

    return DocumentTypingMixin._is_context_menu_key(event)


def test_shift_f10_is_the_context_menu_key() -> None:
    assert _is_menu_key(_KeyEvent(wx.WXK_F10, shift=True))


def test_the_applications_key_is_too() -> None:
    assert _is_menu_key(_KeyEvent(wx.WXK_WINDOWS_MENU))


def test_plain_f10_is_the_menu_bar_and_is_left_alone() -> None:
    """Taking F10 would break the one key that reaches the menu bar."""
    assert not _is_menu_key(_KeyEvent(wx.WXK_F10))


@pytest.mark.parametrize(
    "event",
    [
        _KeyEvent(wx.WXK_F10, shift=True, ctrl=True),
        _KeyEvent(wx.WXK_F10, shift=True, alt=True),
        _KeyEvent(wx.WXK_WINDOWS_MENU, ctrl=True),
    ],
    ids=["ctrl+shift+f10", "alt+shift+f10", "ctrl+apps"],
)
def test_a_chord_with_extra_modifiers_is_something_else(event: _KeyEvent) -> None:
    assert not _is_menu_key(event)


def test_an_ordinary_letter_is_not_the_menu_key() -> None:
    assert not _is_menu_key(_KeyEvent(ord("A")))


def test_the_keyboard_menu_asks_about_the_word_at_the_caret(monkeypatch) -> None:
    """The whole point of the report: the caret is in a misspelled word and the
    menu must be built for *that* word, with no event to hit-test."""
    from quill.apps.lite_window_context_menu import DocumentContextMenuMixin

    seen: dict[str, int] = {}

    class _Win(DocumentContextMenuMixin):
        def __init__(self) -> None:
            self.control = _Control(TEXT, WORD_MIDDLE)

        def _show_context_menu(self, position, event) -> None:  # type: ignore[no-untyped-def]
            seen["position"] = position
            seen["event"] = event

    _Win().open_context_menu_at_caret()
    assert seen["position"] == WORD_MIDDLE
    assert seen["event"] is None
