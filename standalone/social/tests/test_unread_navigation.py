"""Next and Previous Unread in the post list (FUX-14, 2026-11-23).

Unread was spoken on every row and counted on every folder, and the only way to
the next unread post was to arrow past everything already read.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("wx")

from quill_social.keymap import DEFAULT_BINDINGS, Keymap  # noqa: E402
from quill_social.ui.app import SocialFrame  # noqa: E402


class _List:
    def __init__(self, selected: int) -> None:
        self.selected = {selected} if selected >= 0 else set()
        self.focused_row = selected
        self.has_focus = False

    def GetFirstSelected(self) -> int:  # noqa: N802 - wx's name
        return min(self.selected) if self.selected else -1

    def Select(self, index: int, on: bool = True) -> None:  # noqa: N802 - wx's name
        (self.selected.add if on else self.selected.discard)(index)

    def Focus(self, index: int) -> None:  # noqa: N802 - wx's name
        self.focused_row = index

    def EnsureVisible(self, _index: int) -> None:  # noqa: N802 - wx's name
        pass

    def SetFocus(self) -> None:  # noqa: N802 - wx's name
        self.has_focus = True


def _frame(reads: list[bool], selected: int) -> SimpleNamespace:
    said: list[str] = []
    return SimpleNamespace(
        _items=[SimpleNamespace(read=r) for r in reads],
        list=_List(selected),
        announcer=SimpleNamespace(say=lambda text, *_a, **_k: said.append(text)),
        said=said,
    )


def test_next_unread_skips_what_was_read_and_lets_the_reader_say_the_row() -> None:
    frame = _frame([False, True, True, False, False], selected=0)
    SocialFrame._move_unread(frame, 1)
    assert frame.list.selected == {3}
    assert frame.list.focused_row == 3
    assert frame.list.has_focus
    assert frame.said == []


def test_previous_unread_and_both_ends() -> None:
    frame = _frame([False, True, False, True], selected=3)
    SocialFrame._move_unread(frame, -1)
    assert frame.list.selected == {2}
    SocialFrame._move_unread(frame, -1)
    SocialFrame._move_unread(frame, -1)
    assert frame.said == ["No unread before this one."]
    assert frame.list.selected == {0}
    SocialFrame._move_unread(frame, 1)
    SocialFrame._move_unread(frame, 1)
    assert frame.said[-1] == "No more unread."


def test_an_empty_view_says_so() -> None:
    frame = _frame([], selected=-1)
    SocialFrame._move_unread(frame, 1)
    assert frame.said == ["Nothing here."]


def test_the_keys_are_alt_period_and_alt_comma() -> None:
    assert DEFAULT_BINDINGS["next_unread"] == "Alt+."
    assert DEFAULT_BINDINGS["previous_unread"] == "Alt+,"
    assert Keymap().command_for("Alt+.") == "next_unread"
