"""FUX-14 in Quill Beacon's player: chapter keys that exist, and a forward
button that goes the distance it names (2026-11-23).

The player's docstring and the chapter list's accessible name promised "N
next, P previous", and nothing was bound. The keys are Quill Radio's chapter
keys, Ctrl+Shift+Period and Ctrl+Shift+Comma, so type-ahead in the list keeps
its letters.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.apps.beacon.player import PlayerFrame, chapter_key_direction, chapter_step_target


def test_next_goes_to_the_following_chapter_and_stops_at_the_last() -> None:
    starts = [0, 60_000, 120_000]
    assert chapter_step_target(starts, 1_000, 1) == 1
    assert chapter_step_target(starts, 130_000, 1) is None


def test_previous_restarts_the_chapter_unless_just_inside_it() -> None:
    starts = [0, 60_000, 120_000]
    assert chapter_step_target(starts, 90_000, -1) == 1  # well inside: restart
    assert chapter_step_target(starts, 61_000, -1) == 0  # just inside: the one before
    assert chapter_step_target(starts, 1_000, -1) is None  # the first: said, not replayed
    assert chapter_step_target(starts, 30_000, -1) == 0  # well into chapter 1: restart


def test_the_chapter_keys_are_ctrl_shift_period_and_comma() -> None:
    assert chapter_key_direction(ord("."), ctrl=True, shift=True, alt=False) == 1
    assert chapter_key_direction(ord(">"), ctrl=True, shift=True, alt=False) == 1
    assert chapter_key_direction(ord(","), ctrl=True, shift=True, alt=False) == -1
    assert chapter_key_direction(ord("N"), ctrl=False, shift=False, alt=False) == 0
    assert chapter_key_direction(ord("."), ctrl=True, shift=False, alt=False) == 0
    assert chapter_key_direction(ord("."), ctrl=True, shift=True, alt=True) == 0


class _Engine:
    def __init__(self, position: int) -> None:
        self.position = position
        self.seeks: list[int] = []

    def position_ms(self) -> int:
        return self.position

    def seek(self, ms: int) -> None:
        self.seeks.append(ms)
        self.position = ms

    def length_ms(self) -> int:
        return 600_000


class _List:
    def __init__(self, focused: bool = False) -> None:
        self.selection = -1
        self.focused = focused

    def SetSelection(self, index: int) -> None:  # noqa: N802 - wx's name
        self.selection = index

    def GetSelection(self) -> int:  # noqa: N802 - wx's name
        return self.selection

    def HasFocus(self) -> bool:  # noqa: N802 - wx's name
        return self.focused


def _player(position: int, *, focused: bool = False) -> SimpleNamespace:
    said: list[str] = []
    return SimpleNamespace(
        engine=_Engine(position),
        chapters=[
            SimpleNamespace(start_ms=0, title="Welcome"),
            SimpleNamespace(start_ms=60_000, title="The news"),
        ],
        chapter_list=_List(focused),
        announcer=SimpleNamespace(say=lambda text, *_a: said.append(text)),
        said=said,
        _skip_ms=15_000,
        _forward_ms=30_000,
    )


def test_a_chapter_move_seeks_selects_and_says_its_place_once() -> None:
    player = _player(1_000)
    PlayerFrame._step_chapter(player, 1)
    assert player.engine.seeks == [60_000]
    assert player.chapter_list.selection == 1
    assert player.said == ["The news, chapter 2 of 2."]
    PlayerFrame._step_chapter(player, 1)
    assert player.said[-1] == "This is the last chapter."


def test_in_the_focused_list_the_reader_says_the_row() -> None:
    player = _player(1_000, focused=True)
    PlayerFrame._step_chapter(player, 1)
    assert player.chapter_list.selection == 1
    assert player.said == []


def test_a_restart_in_the_focused_list_is_still_said() -> None:
    """The row does not change on a restart, so the reader says nothing."""
    player = _player(90_000, focused=True)
    player.chapter_list.selection = 1
    PlayerFrame._step_chapter(player, -1)
    assert player.engine.seeks == [60_000]
    assert player.said == ["The news, chapter 2 of 2."]


def test_the_30_seconds_button_skips_30_seconds() -> None:
    player = _player(100_000)
    player._seek_delta = lambda delta: PlayerFrame._seek_delta(player, delta)
    PlayerFrame._on_fwd(player)
    assert player.engine.seeks == [130_000]
