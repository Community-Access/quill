"""FUX-07 in Quill Inkwell: text is typed only into the place it was meant for.

Quick Insert and an expansion with fields both open a window of Inkwell's own
between choosing the text and typing it. The place is captured before that
window opens and checked again just before typing; the tests fake the place
changing in between (another field, another program, the program restarted)
and assert that nothing is typed, the text is kept, and Insert or Copy is
offered -- with every platform call faked, so nothing is typed for real.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from quill.core.expansion.matcher import GlobalMatch
from quill.core.external_text import TargetSnapshot, TargetState, TextCapability
from quill.platform.windows.text_injector import InjectionResult
from quill.platform.windows.text_runtime import InkwellTextRuntime
from quill.ui.held_text_dialog import COPY, INSERT
from quill.ui.inkwell_destination import InkwellDestinationMixin
from quill.ui.inkwell_expansion import InkwellExpansionMixin

_PRIVATE = "Dear Sam, my account number is 1234"


def _field(**changes: Any) -> TargetSnapshot:
    base = TargetSnapshot(
        target_id="windows:11:22:hwnd:101",
        window_handle=11,
        process_id=22,
        control_id="hwnd:101",
        state=TargetState.SUPPORTED,
        privilege_match=True,
        capabilities=frozenset({TextCapability.INSERT_TEXT}),
    )
    return replace(base, **changes)


_START = _field()
_OTHER_FIELD = _field(target_id="windows:11:22:hwnd:202", control_id="hwnd:202")
_OTHER_PROGRAM = _field(target_id="windows:44:55:hwnd:303", window_handle=44, process_id=55)
_RESTARTED = _field(target_id="windows:11:23:hwnd:101", process_id=23)


class _Host(InkwellExpansionMixin, InkwellDestinationMixin):
    """Inkwell's frame, reduced to what the two mixins reach for."""

    def __init__(self, place: TargetSnapshot | None) -> None:
        self.place = place
        self.typed: list[str] = []
        self.erased: list[int] = []
        self.said: list[str] = []
        self.offers: list[Any] = []
        self.answers: list[str | None] = []
        self.clipboard: list[str] = []
        self.brought_back: list[int] = []
        self.expanded: list[str] = []
        self._hook = None
        self.frame = None

    # the platform, faked
    def _destination_now(self) -> Any:
        return self.place

    def _text_runtime(self) -> Any:
        def probe() -> TargetSnapshot:
            if self.place is None:
                raise OSError("nothing readable")
            return self.place

        return InkwellTextRuntime(
            target_probe=probe,
            send_text=lambda text: self.typed.append(text) or InjectionResult(1, 1),
            send_backspaces=lambda count: self.erased.append(count) or InjectionResult(1, 1),
            move_caret=lambda _steps: InjectionResult(1, 1),
        )

    def _bring_back(self, window: int) -> None:
        self.brought_back.append(window)

    def _after_focus_settles(self, action: Any) -> None:
        action()

    def _ask_held(self, offer: Any) -> str | None:
        self.offers.append(offer)
        return self.answers.pop(0) if self.answers else None

    def _injection_mode_now(self) -> str:
        return "keys"

    # the shell, faked
    def _announce(self, message: str, *, force: bool = False, sound: str = "") -> None:
        self.said.append(message)

    def _copy_to_clipboard(self, text: str) -> bool:
        self.clipboard.append(text)
        return True

    def _after_expansion(self, match: GlobalMatch) -> None:
        self.expanded.append(match.text)


def _held(host: _Host) -> Any:
    from quill.core.expansion.destination import HeldText

    return HeldText(_PRIVATE, _START)


@pytest.mark.parametrize("moved_to", [_OTHER_FIELD, _OTHER_PROGRAM, _RESTARTED, None])
def test_nothing_is_typed_when_the_place_changed(moved_to: TargetSnapshot | None) -> None:
    host = _Host(moved_to)

    host._insert_held(_held(host))

    assert host.typed == []
    assert host.erased == []
    assert len(host.offers) == 1
    assert host.offers[0].can_insert
    assert _PRIVATE not in host.offers[0].sentence  # never read aloud unasked
    assert host.said == []  # the window's own sentence is the only one (GATE-13)


def test_the_text_is_typed_when_the_place_is_the_same() -> None:
    host = _Host(_START)

    host._insert_held(_held(host))

    assert host.typed == [_PRIVATE]
    assert host.offers == []
    assert host.brought_back == [11]


def test_copy_keeps_the_text_on_the_clipboard() -> None:
    host = _Host(_OTHER_FIELD)
    host.answers = [COPY]

    host._insert_held(_held(host))

    assert host.typed == []
    assert host.clipboard == [_PRIVATE]
    assert host.said == ["Copied the text to the clipboard."]
    assert host.brought_back == [11, 11]  # back where you were, ready to paste


def test_the_copy_is_kept_for_f9_and_activity() -> None:
    from quill.core import activity

    activity.LOG.clear()
    host = _Host(_OTHER_FIELD)
    host.answers = [COPY]

    host._insert_held(_held(host))

    latest = activity.LOG.recent()[0]
    assert (latest.action, latest.summary) == ("Insert Text", "Copied the text to the clipboard.")
    assert _PRIVATE not in latest.summary  # the words themselves are never kept
    activity.LOG.clear()


def test_insert_goes_back_to_the_same_place_and_types_only_there() -> None:
    host = _Host(_OTHER_PROGRAM)

    def back_again(window: int) -> None:
        host.brought_back.append(window)
        if len(host.brought_back) == 2:  # Insert, from the offer
            host.place = _START

    host._bring_back = back_again  # type: ignore[method-assign]
    host.answers = [INSERT]

    host._insert_held(_held(host))

    assert host.brought_back == [11, 11]
    assert host.typed == [_PRIVATE]


def test_a_password_field_offers_copy_only() -> None:
    host = _Host(replace(_START, state=TargetState.PROTECTED, protected=True))

    host._insert_held(_held(host))

    assert host.typed == []
    assert not host.offers[0].can_insert


def test_quick_insert_from_inkwell_itself_copies_and_says_so() -> None:
    from quill.core.expansion.destination import HeldText

    host = _Host(_START)

    host._insert_held(HeldText(_PRIVATE, None))

    assert host.typed == []
    assert host.clipboard == [_PRIVATE]
    assert host.said == ["Nothing to insert into; copied to the clipboard instead."]


# -- an expansion with fields ------------------------------------------------ #


def _fields_match() -> GlobalMatch:
    return GlobalMatch(
        abbreviation=None,
        text="Hello ${name}",
        backspace_count=3,
        cursor_offset=0,
        has_cursor=False,
        trailing_space=False,
        trigger_char=" ",
        template="Hello ${form:name}",
        target_window=11,
    )


def _fill(monkeypatch: pytest.MonkeyPatch, host: _Host, after_dialog: Any) -> None:
    """The fill-in form returns a value, and the focus is wherever *after_dialog* says."""
    import quill.ui.fill_in_dialog as fill_in

    def prompt(*_args: Any, **_kwargs: Any) -> str:
        host.place = after_dialog
        return "Hello Sam"

    monkeypatch.setattr(fill_in, "prompt_for_fields", prompt)


def test_fields_type_into_the_field_the_abbreviation_was_typed_in(
    monkeypatch: pytest.MonkeyPatch, wx_call_after: Any
) -> None:
    wx_call_after()
    host = _Host(_START)
    _fill(monkeypatch, host, _START)

    host._expand_with_fields(_fields_match())

    assert host.erased == [3]
    assert host.typed == ["Hello Sam "]
    assert host.expanded == ["Hello Sam"]


def test_fields_are_kept_when_the_focus_came_back_somewhere_else(
    monkeypatch: pytest.MonkeyPatch, wx_call_after: Any
) -> None:
    wx_call_after()
    host = _Host(_START)
    _fill(monkeypatch, host, _OTHER_FIELD)
    host.answers = [COPY]

    host._expand_with_fields(_fields_match())

    assert host.erased == []  # the abbreviation in the other field is untouched
    assert host.typed == []
    assert host.clipboard == ["Hello Sam"]
    assert host.expanded == []


def test_fields_do_not_open_when_the_focus_already_moved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _Host(_OTHER_PROGRAM)
    _fill(monkeypatch, host, _OTHER_PROGRAM)

    host._expand_with_fields(_fields_match())

    assert host.typed == [] and host.erased == []
    assert host.said == ["Not expanded, because the focus is not where you started."]


# -- the global undo --------------------------------------------------------- #


def test_undo_types_nothing_into_another_window(wx_call_after: Any) -> None:
    from quill.core.expansion.undo import UndoPlan

    wx_call_after()
    host = _Host(_OTHER_PROGRAM)
    plan = UndoPlan(text="addr", backspaces=12, window_handle=11)

    host._on_global_undo(plan)

    assert host.typed == [] and host.erased == []
    assert host.said == ["Not undone, because the focus has moved to another window."]


def test_undo_puts_the_abbreviation_back_in_its_own_window(wx_call_after: Any) -> None:
    from quill.core.expansion.undo import UndoPlan

    wx_call_after()
    host = _Host(_START)

    host._on_global_undo(UndoPlan(text="addr", backspaces=12, window_handle=11))

    assert host.erased == [11]
    assert host.typed == ["addr"]
    assert host.said == ["Undone. addr is back."]


# -- a plain expansion ------------------------------------------------------- #


def _plain_match(window: int) -> GlobalMatch:
    return GlobalMatch(
        abbreviation=None,
        text="by the way",
        backspace_count=3,
        cursor_offset=0,
        has_cursor=False,
        trailing_space=False,
        trigger_char=" ",
        target_window=window,
    )


def test_a_plain_expansion_lands_in_the_window_it_was_typed_in(wx_call_after: Any) -> None:
    """Every match carries its window: until 2026-11-23 the field did not
    exist and every system-wide expansion failed in the worker."""
    wx_call_after()
    host = _Host(_START)

    host._inject(_plain_match(11))

    assert host.erased == [3]
    assert host.typed == ["by the way "]


def test_a_plain_expansion_types_nothing_into_another_window(wx_call_after: Any) -> None:
    wx_call_after()
    host = _Host(_OTHER_PROGRAM)

    host._inject(_plain_match(11))

    assert host.typed == [] and host.erased == []
    assert host.said == ["Not expanded, because the focus is not where you started."]


def test_fields_do_not_open_when_windows_cannot_name_the_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _Host(None)
    _fill(monkeypatch, host, None)

    host._expand_with_fields(_fields_match())

    assert host.typed == [] and host.erased == []
    assert host.said == ["Not expanded, because Windows cannot say where the focus is."]
