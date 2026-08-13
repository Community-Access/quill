"""The Media Player adopts the shared Winamp map (x.md item 13).

Quill Radio's recordings list was first, QUILL Cast second, and this was the
last holdout -- which mattered, because an audiobook player with a track list
is the surface a Winamp user is most likely to reach for.

The point of these tests is that there is still only **one** map: the same
letters resolve to the same actions here as everywhere else, and this surface
adds no bindings of its own. A second implementation is exactly what the
shared ``winamp_keys`` module exists to prevent.

The mixin is driven against a stub host rather than a real frame -- what is
under test is the dispatch and the wording, not wx.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.ui.media.winamp_mixin import MediaWinampKeysMixin
from quill.ui.radio import winamp_keys as wk


class _Player:
    def __init__(self, *, media: bool = True, playing: bool = False, length: int = 600_000) -> None:
        self._media = media
        self._playing = playing
        self._length = length
        self.position = 100_000
        self._volume = 50
        self.stopped = False
        self.chapter_steps: list[int] = []

    def has_media(self) -> bool:
        return self._media

    def is_playing(self) -> bool:
        return self._playing

    def play(self) -> None:
        self._playing = True

    def toggle(self) -> None:
        self._playing = not self._playing

    def stop(self) -> None:
        self._playing = False
        self.stopped = True

    def playhead_ms(self) -> int:
        return self.position

    def length_ms(self) -> int:
        return self._length

    def seek_to(self, ms: int) -> None:
        self.position = ms

    def volume(self) -> int:
        return self._volume

    def set_volume(self, percent: int) -> int:
        self._volume = max(0, min(100, percent))
        return self._volume

    def next_chapter(self) -> None:
        self.chapter_steps.append(1)

    def previous_chapter(self) -> None:
        self.chapter_steps.append(-1)


class _Host(MediaWinampKeysMixin):
    def __init__(self, player: _Player, *, playlist: list[tuple[str, Any]] | None = None) -> None:
        self._player = player
        self._playlist = playlist if playlist is not None else []
        self._playlist_index = -1
        self._chapters: list[object] = []
        self.announced: list[str] = []
        self.played: list[tuple[Any, str]] = []
        self.opened = 0
        self.go_to_position_calls = 0

    def _announce(self, text: str) -> None:
        self.announced.append(text)

    def _play_payload(self, payload: Any, title: str, *, autoplay: bool) -> None:
        self.played.append((payload, title))

    def _on_open_file(self, _event: Any) -> None:
        self.opened += 1

    def _on_go_to_position(self, _event: Any) -> None:
        self.go_to_position_calls += 1

    def _winamp_focus_is_text_entry(self) -> bool:
        return False


def _tracks(count: int = 3) -> list[tuple[str, Any]]:
    return [(f"Chapter {n + 1}", ("load", f"file{n + 1}.mp3")) for n in range(count)]


# -- one shared map ----------------------------------------------------------


def test_the_letters_resolve_through_the_shared_map_not_a_local_one() -> None:
    """If this surface had its own table, these would be free to drift."""
    assert wk.resolve_winamp_action("X") == wk.ACTION_PLAY
    assert wk.resolve_winamp_action("C") == wk.ACTION_PAUSE
    assert wk.resolve_winamp_action("V") == wk.ACTION_STOP
    assert wk.resolve_winamp_action("B") == wk.ACTION_NEXT
    assert wk.resolve_winamp_action("Z") == wk.ACTION_PREVIOUS


def test_every_mapped_action_has_a_handler_here() -> None:
    """The gap this catches: the shared map gains an action and one surface
    silently ignores it."""
    host = _Host(_Player())
    for action in set(wk.ACTION_LABELS):
        if action in (wk.ACTION_VOLUME_UP, wk.ACTION_VOLUME_DOWN):
            continue  # handled before dispatch, with the Ctrl+arrow branch
        host._run_winamp_action(action)  # must not raise


# -- transport ---------------------------------------------------------------


def test_x_plays_and_says_so() -> None:
    host = _Host(_Player(playing=False))
    host._run_winamp_action(wk.ACTION_PLAY)
    assert host._player.is_playing() is True
    assert host.announced == ["Playing"]


def test_x_on_something_already_playing_says_so_rather_than_restarting() -> None:
    host = _Host(_Player(playing=True))
    host._run_winamp_action(wk.ACTION_PLAY)
    assert host.announced == ["Already playing"]


def test_x_with_nothing_open_points_at_what_to_do() -> None:
    host = _Host(_Player(media=False))
    host._run_winamp_action(wk.ACTION_PLAY)
    assert "Open a file" in host.announced[0]


def test_c_pauses_and_unpauses_saying_which() -> None:
    host = _Host(_Player(playing=True))
    host._run_winamp_action(wk.ACTION_PAUSE)
    assert host.announced == ["Paused"]
    host._run_winamp_action(wk.ACTION_PAUSE)
    assert host.announced == ["Paused", "Playing"]


def test_shift_v_stops_cleanly_rather_than_pretending_to_fade() -> None:
    """This engine has no fade, and a control that claims one it does not have
    is worse than one that says what it did."""
    host = _Host(_Player(playing=True))
    host._run_winamp_action(wk.ACTION_STOP_FADE)
    assert host._player.stopped is True
    assert host.announced == ["Stopped"]


def test_l_opens_a_file() -> None:
    host = _Host(_Player())
    host._run_winamp_action(wk.ACTION_OPEN)
    assert host.opened == 1


# -- stepping ----------------------------------------------------------------


def test_b_and_z_step_through_the_track_list() -> None:
    host = _Host(_Player(), playlist=_tracks())
    host._playlist_index = 0

    host._run_winamp_action(wk.ACTION_NEXT)
    assert host._playlist_index == 1
    assert host.played[-1][1] == "Chapter 2"

    host._run_winamp_action(wk.ACTION_PREVIOUS)
    assert host._playlist_index == 0
    assert host.played[-1][1] == "Chapter 1"


def test_stepping_past_either_end_says_so_and_stays_put() -> None:
    host = _Host(_Player(), playlist=_tracks())
    host._playlist_index = 2
    host._run_winamp_action(wk.ACTION_NEXT)
    assert host._playlist_index == 2
    assert "last track" in host.announced[-1]

    host._playlist_index = 0
    host._run_winamp_action(wk.ACTION_PREVIOUS)
    assert host._playlist_index == 0
    assert "first track" in host.announced[-1]


def test_a_single_file_book_steps_by_chapter_instead() -> None:
    """One file with chapter marks has no track list; stepping by chapter is
    the same intent against the other shape."""
    host = _Host(_Player(), playlist=[])
    host._chapters = [object(), object()]

    host._run_winamp_action(wk.ACTION_NEXT)
    host._run_winamp_action(wk.ACTION_PREVIOUS)

    assert host._player.chapter_steps == [1, -1]


def test_nothing_to_step_through_says_so() -> None:
    host = _Host(_Player(), playlist=[])
    host._run_winamp_action(wk.ACTION_NEXT)
    assert "nothing to step through" in host.announced[-1]


# -- seeking -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("action", "delta"),
    [
        (wk.ACTION_FORWARD_5, 5_000),
        (wk.ACTION_BACK_5, -5_000),
        (wk.ACTION_FORWARD_30, 30_000),
        (wk.ACTION_BACK_30, -30_000),
    ],
)
def test_the_arrows_seek_by_the_same_steps_as_every_other_surface(action: str, delta: int) -> None:
    host = _Host(_Player())
    start = host._player.position
    host._run_winamp_action(action)
    assert host._player.position == start + delta


def test_seeking_is_clamped_to_the_timeline() -> None:
    host = _Host(_Player(length=20_000))
    host._player.position = 5_000
    host._run_winamp_action(wk.ACTION_BACK_30)
    assert host._player.position == 0

    host._player.position = 15_000
    host._run_winamp_action(wk.ACTION_FORWARD_30)
    assert host._player.position == 20_000


# -- position readout --------------------------------------------------------


def test_t_flips_elapsed_and_remaining() -> None:
    host = _Host(_Player(length=600_000))
    host._player.position = 100_000

    host._run_winamp_action(wk.ACTION_TOGGLE_TIME)
    assert "remaining" in host.announced[-1]

    host._run_winamp_action(wk.ACTION_TOGGLE_TIME)
    assert "remaining" not in host.announced[-1]
    assert " of " in host.announced[-1]


def test_the_position_is_spoken_as_words_never_as_a_clock() -> None:
    """ "1:40" read aloud is a time of day; "1 minute 40 seconds" is a
    duration. Same rule as the chapter list and Cast."""
    host = _Host(_Player(length=600_000))
    host._player.position = 100_000

    text = host._winamp_position_text()

    assert "minute" in text and "second" in text
    assert ":" not in text


def test_ctrl_j_opens_the_existing_accessible_go_to_position_dialog() -> None:
    """Not a second, lesser prompt: the Media Player already had one built to
    the desktop accessibility checklist, on Ctrl+G."""
    host = _Host(_Player())
    host._run_winamp_action(wk.ACTION_JUMP_TO_TIME)
    assert host.go_to_position_calls == 1


# -- volume ------------------------------------------------------------------


def test_ctrl_arrows_change_volume_and_say_the_level() -> None:
    host = _Host(_Player())
    host._winamp_volume(up=True)
    assert host._player.volume() == 55
    assert host.announced[-1] == "Volume 55"

    host._winamp_volume(up=False)
    assert host._player.volume() == 50
