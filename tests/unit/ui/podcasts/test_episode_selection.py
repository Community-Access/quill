"""Select All and Invert Selection on the episode list (earshot.md E5)."""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.podcasts import episode_selection
from quill.ui.podcasts.episode_selection import invert_selection, select_all, selection_key


class _List:
    def __init__(self, count: int, selected: set[int] | None = None) -> None:
        self.count = count
        self.selected = set(selected or ())

    def GetItemCount(self) -> int:  # noqa: N802 - wx's name
        return self.count

    def Select(self, index: int, on: bool = True) -> None:  # noqa: N802
        (self.selected.add if on else self.selected.discard)(index)

    def GetFirstSelected(self) -> int:  # noqa: N802
        return min(self.selected) if self.selected else -1

    def GetNextSelected(self, index: int) -> int:  # noqa: N802
        later = sorted(i for i in self.selected if i > index)
        return later[0] if later else -1


class _Host:
    def __init__(self, episodes: _List) -> None:
        self._episodes = episodes
        self.said: list[str] = []

    def _announce(self, text: str) -> None:
        self.said.append(text)


class _Key:
    def __init__(self, code: int, *, ctrl: bool = True, shift: bool = False) -> None:
        self.code, self.ctrl, self.shift = code, ctrl, shift

    def GetKeyCode(self) -> int:  # noqa: N802
        return self.code

    def ControlDown(self) -> bool:  # noqa: N802
        return self.ctrl

    def ShiftDown(self) -> bool:  # noqa: N802
        return self.shift

    def AltDown(self) -> bool:  # noqa: N802
        return False


def test_select_all_selects_every_row_and_says_how_many() -> None:
    host = _Host(_List(412, {3}))
    select_all(host)
    assert host._episodes.selected == set(range(412))
    assert host.said == ["All 412 episodes selected."]


def test_invert_selects_the_exceptions() -> None:
    host = _Host(_List(5, {0, 1, 2}))
    invert_selection(host)
    assert host._episodes.selected == {3, 4}
    assert host.said == ["2 of 5 episodes selected."]


def test_an_empty_list_says_so() -> None:
    host = _Host(_List(0))
    select_all(host)
    assert host.said == ["There are no episodes here to select."]


def test_the_keys_only_belong_to_the_focused_list(monkeypatch: Any) -> None:
    host = _Host(_List(3))
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: host._episodes))
    assert selection_key(host, _Key(ord("A"))) is True
    assert host._episodes.selected == {0, 1, 2}
    assert selection_key(host, _Key(ord("I"), shift=True)) is True
    assert host._episodes.selected == set()
    assert selection_key(host, _Key(ord("A"), ctrl=False)) is False
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: object()))  # the search box
    assert selection_key(host, _Key(ord("A"))) is False


def test_the_module_names_its_two_commands() -> None:
    assert set(episode_selection.__all__) == {"invert_selection", "select_all", "selection_key"}
