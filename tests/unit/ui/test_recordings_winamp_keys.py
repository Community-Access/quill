"""The Winamp keys as the Recordings player actually dispatches them (#1344).

Driven directly against a fake controller and list, the way the sibling volume
test does -- no live wx.App. What matters here is that every key does the thing
the map says *and announces it*: a transport key a blind listener cannot hear
the result of is not a working transport key.
"""

from __future__ import annotations

import types

from quill.core.radio.recordings_index import STATUS_RECORDED, STATUS_SCHEDULED, RecordingEntry
from quill.ui.radio.recordings_manager_dialog import RecordingsManagerDialog

_WXK_UP = 315
_WXK_DOWN = 317
_WXK_LEFT = 314
_WXK_RIGHT = 316


class _State:
    def __init__(self, state: object) -> None:
        self.state = state
        self.station = None
        self.volume_percent = 50
        self.muted = False


class _Controller:
    def __init__(self, state: object) -> None:
        self.state = _State(state)
        self.calls: list[tuple] = []
        self.seekable = True
        self.position = 65_000
        self.duration = 300_000

    def toggle_play_pause(self) -> None:
        self.calls.append(("toggle",))

    def stop(self) -> None:
        self.calls.append(("stop",))

    def play_station(self, station: object) -> None:
        self.calls.append(("play", getattr(station, "name", "")))

    def is_seekable(self) -> bool:
        return self.seekable

    def skip_by(self, ms: int) -> bool:
        self.calls.append(("skip", ms))
        self.position += ms
        return True

    def seek_to(self, ms: int) -> bool:
        self.calls.append(("seek", ms))
        self.position = ms
        return True

    def position_ms(self) -> int:
        return self.position

    def duration_ms(self) -> int:
        return self.duration


class _List:
    def __init__(self, selected: int) -> None:
        self.selected = selected
        self.focused = selected

    def GetFirstSelected(self) -> int:  # noqa: N802 - wx shape
        return self.selected

    def Select(self, row: int) -> None:  # noqa: N802 - wx shape
        self.selected = row

    def Focus(self, row: int) -> None:  # noqa: N802 - wx shape
        self.focused = row

    def EnsureVisible(self, row: int) -> None:  # noqa: N802 - wx shape
        pass


class _KeyEvent:
    def __init__(self, code: int, *, ctrl: bool = False, shift: bool = False) -> None:
        self._code = code
        self._ctrl = ctrl
        self._shift = shift
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802 - wx shape
        return self._code

    def ControlDown(self) -> bool:  # noqa: N802 - wx shape
        return self._ctrl

    def ShiftDown(self) -> bool:  # noqa: N802 - wx shape
        return self._shift

    def AltDown(self) -> bool:  # noqa: N802 - wx shape
        return False

    def Skip(self) -> None:  # noqa: N802 - wx shape
        self.skipped = True


def _entry(name: str, status: str = STATUS_RECORDED) -> RecordingEntry:
    return RecordingEntry(
        id=name,
        name=name,
        status=status,
        path=None if status == STATUS_SCHEDULED else __import__("pathlib").Path(f"C:/rec/{name}"),
        detail="",
    )


class _PlayerState:
    """Stand-in for RadioPlayerState members, compared by identity."""


def _dialog(
    *, playing: bool = True, entries: list[RecordingEntry] | None = None, selected: int = 0
) -> tuple[RecordingsManagerDialog, _Controller, list[str]]:
    from quill.ui.radio.playback_state import RadioPlayerState

    dialog = RecordingsManagerDialog.__new__(RecordingsManagerDialog)
    controller = _Controller(RadioPlayerState.PLAYING if playing else RadioPlayerState.STOPPED)
    announced: list[str] = []
    dialog._wx = types.SimpleNamespace(
        WXK_UP=_WXK_UP, WXK_DOWN=_WXK_DOWN, WXK_LEFT=_WXK_LEFT, WXK_RIGHT=_WXK_RIGHT
    )
    dialog._controller = controller
    dialog._announce = announced.append
    dialog._history = types.SimpleNamespace(winamp_playback_keys=True)
    dialog._entries = entries if entries is not None else [_entry("one"), _entry("two")]
    dialog._list = _List(selected)
    dialog._speak_remaining = False
    dialog._on_selection_changed = lambda: None  # type: ignore[method-assign]
    return dialog, controller, announced


def test_c_pauses_and_says_so() -> None:
    dialog, controller, announced = _dialog(playing=True)
    dialog._on_char_hook(_KeyEvent(ord("C")))
    assert controller.calls == [("toggle",)]
    assert announced == ["Paused."]


def test_c_on_nothing_playing_says_nothing_is_playing() -> None:
    dialog, controller, announced = _dialog(playing=False)
    dialog._on_char_hook(_KeyEvent(ord("C")))
    assert controller.calls == []
    assert announced == ["Nothing is playing."]


def test_v_stops() -> None:
    dialog, controller, announced = _dialog()
    dialog._on_char_hook(_KeyEvent(ord("V")))
    assert controller.calls == [("stop",)]
    assert announced == ["Stopped"]


def test_shift_v_stops_too_rather_than_faking_a_fade() -> None:
    dialog, controller, announced = _dialog()
    dialog._on_char_hook(_KeyEvent(ord("V"), shift=True))
    assert controller.calls == [("stop",)]
    assert announced == ["Stopped"]


def test_b_plays_the_next_finished_recording() -> None:
    dialog, controller, announced = _dialog(selected=0)
    dialog._on_char_hook(_KeyEvent(ord("B")))
    assert controller.calls == [("play", "two")]
    assert dialog._list.selected == 1
    assert announced == ["Playing recording two."]


def test_z_at_the_top_says_so_instead_of_wrapping_silently() -> None:
    dialog, controller, announced = _dialog(selected=0)
    dialog._on_char_hook(_KeyEvent(ord("Z")))
    assert controller.calls == []
    assert announced == ["This is the first recording."]


def test_next_skips_rows_that_cannot_be_played() -> None:
    entries = [_entry("one"), _entry("later", STATUS_SCHEDULED), _entry("three")]
    dialog, controller, _ = _dialog(entries=entries, selected=0)
    dialog._on_char_hook(_KeyEvent(ord("B")))
    assert controller.calls == [("play", "three")]


def test_arrows_seek_by_five_and_thirty_seconds() -> None:
    dialog, controller, announced = _dialog()
    dialog._on_char_hook(_KeyEvent(_WXK_RIGHT))
    dialog._on_char_hook(_KeyEvent(_WXK_LEFT))
    dialog._on_char_hook(_KeyEvent(_WXK_RIGHT, shift=True))
    dialog._on_char_hook(_KeyEvent(_WXK_LEFT, shift=True))
    assert controller.calls == [
        ("skip", 5_000),
        ("skip", -5_000),
        ("skip", 30_000),
        ("skip", -30_000),
    ]
    assert len(announced) == 4


def test_seeking_a_live_stream_says_why_it_cannot() -> None:
    dialog, controller, announced = _dialog()
    controller.seekable = False
    dialog._on_char_hook(_KeyEvent(_WXK_RIGHT))
    assert controller.calls == []
    assert announced == ["There is nothing to seek through right now."]


def test_t_toggles_elapsed_and_remaining() -> None:
    dialog, _controller, announced = _dialog()
    dialog._on_char_hook(_KeyEvent(ord("T")))
    assert announced == ["3 minutes 55 seconds remaining"]
    dialog._on_char_hook(_KeyEvent(ord("T")))
    assert announced[-1] == "1 minute 5 seconds elapsed"


def test_ctrl_t_is_left_alone_for_whats_playing() -> None:
    dialog, controller, announced = _dialog()
    event = _KeyEvent(ord("T"), ctrl=True)
    dialog._on_char_hook(event)
    assert event.skipped is True
    assert controller.calls == []
    assert announced == []


def test_letters_pass_through_when_the_preference_is_off() -> None:
    dialog, controller, _ = _dialog()
    dialog._history = types.SimpleNamespace(winamp_playback_keys=False)
    event = _KeyEvent(ord("V"))
    dialog._on_char_hook(event)
    assert event.skipped is True
    assert controller.calls == []


def test_volume_still_works_with_the_preference_off() -> None:
    """Ctrl+arrow predates #1344 and can never collide with typing."""
    dialog, controller, announced = _dialog()
    dialog._history = types.SimpleNamespace(winamp_playback_keys=False)
    dialog._adjust_volume = lambda *, up: announced.append(f"volume {up}")  # type: ignore[method-assign]
    event = _KeyEvent(_WXK_UP, ctrl=True)
    dialog._on_char_hook(event)
    assert event.skipped is False
    assert announced == ["volume True"]
