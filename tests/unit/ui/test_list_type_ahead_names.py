"""Typing a full name in a list, spaces and all (2026-10-16, Jeff's item 45).

Every list that opens its row on Enter also opened it on **Space**
(``apply_listbox_activation``). Typing "Meeting notes" to reach that snippet
moved to "Meeting agenda" on the M and then *opened it* on the space. Now the
space belongs to the name while one is being typed; Space on its own, Enter
and Escape keep their meanings.

The list here is a fake that records what the glue does, and the key events
are fakes too: nothing is sent to a real window (brief rule 10b).
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.type_ahead import TypeAheadBuffer
from quill.ui import dialog_contract

NAMES = ["Meeting agenda", "Meeting notes", "Meeting notes for Tuesday", "Notes", "Reply"]


class _FakeList:
    def __init__(self, names: list[str], selection: int = 0) -> None:
        self.names = names
        self.selection = selection
        self.handlers: dict[Any, Any] = {}
        self.processed: list[int] = []

    def Bind(self, event: Any, handler: Any) -> None:  # noqa: N802 - wx's name
        self.handlers[event] = handler

    def GetSelection(self) -> int:  # noqa: N802
        return self.selection

    def SetSelection(self, index: int) -> None:  # noqa: N802
        self.selection = index

    def GetStrings(self) -> list[str]:  # noqa: N802
        return list(self.names)

    def GetId(self) -> int:  # noqa: N802
        return 101

    def GetEventHandler(self) -> Any:  # noqa: N802
        outer = self

        class _Handler:
            def ProcessEvent(self, event: Any) -> bool:  # noqa: N802
                outer.processed.append(event.GetInt())
                return True

        return _Handler()


class _Key:
    def __init__(self, char: str = "", code: int | None = None) -> None:
        self._char = char
        self._code = code if code is not None else (ord(char) if char else 0)
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802
        return self._code

    def GetUnicodeKey(self) -> int:  # noqa: N802
        return ord(self._char) if self._char else wx.WXK_NONE

    def ControlDown(self) -> bool:  # noqa: N802
        return False

    def AltDown(self) -> bool:  # noqa: N802
        return False

    def Skip(self) -> None:  # noqa: N802
        self.skipped = True


class _FakeCommandEvent:
    """Stands in for wx.CommandEvent, which will not carry a non-wx object."""

    def __init__(self, _kind: Any, _id: int) -> None:
        self._int = -1

    def SetEventObject(self, _obj: Any) -> None:  # noqa: N802
        pass

    def SetInt(self, value: int) -> None:  # noqa: N802
        self._int = value

    def GetInt(self) -> int:  # noqa: N802
        return self._int


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    now = [100.0]
    monkeypatch.setattr("time.monotonic", lambda: now[0])
    monkeypatch.setattr(wx, "CommandEvent", _FakeCommandEvent)
    return now


def _type(fake: _FakeList, text: str, clock: list[float]) -> list[str]:
    """Press each character the way wx delivers it: key down, then char."""
    opened: list[str] = []
    for char in text:
        code = wx.WXK_SPACE if char == " " else ord(char.upper())
        down = _Key(char, code)
        fake.handlers[wx.EVT_KEY_DOWN](down)
        if down.skipped:
            fake.handlers[wx.EVT_CHAR](_Key(char))
        clock[0] += 0.15
    return opened


def _wire(fake: _FakeList) -> list[int]:
    opened: list[int] = []
    dialog_contract.apply_listbox_activation(fake, lambda _e: opened.append(fake.selection))
    return opened


def test_a_name_with_a_space_reaches_its_row_without_opening_one(clock: list[float]) -> None:
    fake = _FakeList(NAMES, selection=-1)
    opened = _wire(fake)
    _type(fake, "meeting notes", clock)
    assert opened == [], "the space was part of the name, not an activation"
    assert fake.names[fake.selection] == "Meeting notes"
    # A details pane hears about the move the way it hears an arrow key.
    assert fake.processed and fake.processed[-1] == 1


def test_the_longer_name_does_not_hop_between_similar_rows(clock: list[float]) -> None:
    fake = _FakeList(NAMES, selection=-1)
    _wire(fake)
    seen: list[int] = []
    for end in range(1, len("meeting notes f") + 1):
        _type(fake, "meeting notes f"[end - 1], clock)
        seen.append(fake.selection)
    assert fake.names[fake.selection] == "Meeting notes for Tuesday"
    # Once on "Meeting notes", it stays there until the name says otherwise.
    assert seen[8:13] == [1, 1, 1, 1, 1]


def test_space_after_a_pause_still_opens_the_row(clock: list[float]) -> None:
    fake = _FakeList(NAMES, selection=-1)
    opened = _wire(fake)
    _type(fake, "rep", clock)
    clock[0] += 2.0  # a pause ends the name
    _type(fake, " ", clock)
    assert opened == [4]


def test_enter_always_opens_and_ends_the_name(clock: list[float]) -> None:
    fake = _FakeList(NAMES, selection=-1)
    opened = _wire(fake)
    _type(fake, "meeting", clock)
    fake.handlers[wx.EVT_KEY_DOWN](_Key(code=wx.WXK_RETURN))
    assert opened == [0]
    # The next key starts a new name rather than extending the old one.
    _type(fake, "n", clock)
    assert fake.names[fake.selection] == "Notes"


def test_escape_is_left_to_the_dialog(clock: list[float]) -> None:
    fake = _FakeList(NAMES, selection=0)
    opened = _wire(fake)
    escape = _Key(code=wx.WXK_ESCAPE)
    fake.handlers[wx.EVT_KEY_DOWN](escape)
    assert escape.skipped and opened == []


def test_no_match_is_said(clock: list[float], monkeypatch: pytest.MonkeyPatch) -> None:
    said: list[str] = []
    monkeypatch.setattr("quill.platform.sr_announce.announce", said.append)
    fake = _FakeList(NAMES, selection=0)
    _wire(fake)
    _type(fake, "z", clock)
    assert said == ["No match for z"]
    assert fake.selection == 0


def test_the_buffer_knows_when_a_name_is_being_typed() -> None:
    buffer = TypeAheadBuffer(open_suppression=0.0)
    assert not buffer.typing(10.0)
    buffer.press("m", NAMES, -1, now=10.0)
    assert buffer.typing(10.5)
    assert not buffer.typing(12.0)
    buffer.press("e", NAMES, 0, now=10.5)
    buffer.reset()
    assert not buffer.typing(10.6)
