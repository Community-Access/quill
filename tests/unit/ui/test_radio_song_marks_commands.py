"""The song-mark commands, end to end over a fake controller and a fake mpv.

Each handler on the Playback menu is called here: Previous Song, Next Song,
Which Song Is This, the four saves, and the station's own time-shift length.
What they say is checked as well as what they do, because what is said after
a jump is the whole of the feedback (GATE-13: the title and the distance from
live, nothing the screen reader already knows).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import wx

from quill.core.radio import timeshift
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.history import RadioHistory
from quill.core.radio.models import RadioStation
from quill.core.radio.recording import RecordingSettings
from quill.ui.main_frame_radio import RadioMixin
from quill.ui.radio import engine_selection, song_marks_ui
from quill.ui.radio.mpv_live_extras import LiveExtras

STATION = RadioStation(name="Jazz 24", stream_url="http://example.invalid/jazz")


class _Mpv:
    def __init__(self) -> None:
        self.doubles: dict[str, float | None] = {"time-pos": 150.0, "demuxer-cache-time": 260.0}
        self.strings: dict[str, str | None] = {
            "audio-codec-name": "mp3",
            "demuxer-cache-state": json.dumps({"seekable-ranges": [{"start": 0, "end": 260}]}),
        }
        self.commands: list[tuple[str, ...]] = []

    def get_double(self, name: str) -> float | None:
        return self.doubles.get(name)

    def get_str(self, name: str) -> str | None:
        return self.strings.get(name)

    def set_str(self, _name: str, _value: str) -> int:
        return 0

    def command(self, *args: str) -> None:
        self.commands.append(args)
        if args[0] == "seek":
            self.doubles["time-pos"] = float(args[1])
        if args[0] == "dump-cache":
            Path(args[3]).write_bytes(b"ID3")


class _Engine:
    def __init__(self) -> None:
        self.mpv = _Mpv()
        self.live_extras = LiveExtras(self.mpv, title=lambda: "")
        self._loaded = True
        self.bounded = False
        self.configured: list[int | None] = []

    def is_bounded(self) -> bool:
        return self.bounded

    def jump_to_live(self) -> bool:
        self.mpv.doubles["time-pos"] = 259.0
        return True

    def configure_timeshift(self, minutes: int | None) -> None:
        self.configured.append(minutes)


class _Controller:
    def __init__(self, engine: _Engine | None, *, mpv_active: bool = True) -> None:
        self._mpv_engine = engine
        self._mpv_active = mpv_active
        self._state = type("S", (), {"station": STATION})()

    @property
    def state(self) -> Any:
        return self._state

    def _is_mpv_active(self) -> bool:
        return self._mpv_active

    def jump_to_live(self) -> bool:
        return bool(self._mpv_engine and self._mpv_engine.jump_to_live())


class _Tasks:
    def submit(self, _name: str, func: Any, *, on_success: Any, on_failure: Any) -> None:
        try:
            result = func()
        except Exception as error:  # noqa: BLE001
            on_failure(_name, error)
            return
        on_success(_name, result)


class _Host:
    radio_jump_to_live = RadioMixin.radio_jump_to_live
    _radio_dvr_unavailable_message = RadioMixin._radio_dvr_unavailable_message
    _radio_behind_live_phrase = staticmethod(RadioMixin._radio_behind_live_phrase)

    def __init__(self, controller: _Controller, tmp_path: Path) -> None:
        self._radio_controller = controller
        self.said: list[str] = []
        self._task_manager = _Tasks()
        self._wx = wx
        self._radio_recording_settings = RecordingSettings(destination_root=str(tmp_path))
        self._radio_history = RadioHistory()
        self._radio_favorites = RadioFavoritesStore()
        self.persisted = 0
        self.selected: Any = None

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def _persist_radio_favorites(self) -> None:
        self.persisted += 1

    def _selected_favorite(self) -> Any:
        return self.selected


@pytest.fixture
def host(tmp_path: Path, wx_session_app: Any, wx_call_after: Any) -> _Host:
    wx_call_after()
    engine = _Engine()
    marks = engine.live_extras.marks
    marks.mark("Artist - Alpha", 0.0)
    marks.mark("Artist - Bravo", 100.0)
    marks.mark("Artist - Charlie", 200.0)
    return _Host(_Controller(engine), tmp_path)


def _engine(host: _Host) -> _Engine:
    engine = host._radio_controller._mpv_engine
    assert engine is not None
    return engine


# -- jumping ----------------------------------------------------------------------


def test_previous_song_restarts_the_song_and_says_its_title_and_distance(host: _Host) -> None:
    song_marks_ui.previous_song(host)
    assert _engine(host).mpv.commands[-1] == ("seek", "100.000", "absolute")
    assert host.said == ["Bravo by Artist. 2 minutes 40 seconds behind live."]


def test_previous_song_just_after_a_start_goes_to_the_one_before(host: _Host) -> None:
    _engine(host).mpv.doubles["time-pos"] = 101.0
    song_marks_ui.previous_song(host)
    assert _engine(host).mpv.commands[-1] == ("seek", "0.000", "absolute")
    assert host.said[-1].startswith("Alpha by Artist.")


def test_previous_song_at_the_oldest_start_says_so(host: _Host) -> None:
    _engine(host).mpv.doubles["time-pos"] = 1.0
    song_marks_ui.previous_song(host)
    assert _engine(host).mpv.commands == []
    assert host.said == ["This is the oldest song in the buffer."]


def test_next_song_goes_to_the_next_start(host: _Host) -> None:
    song_marks_ui.next_song(host)
    assert _engine(host).mpv.commands[-1] == ("seek", "200.000", "absolute")
    assert host.said == ["Charlie by Artist. 1 minute behind live."]


def test_next_song_after_the_last_goes_back_to_live(host: _Host) -> None:
    _engine(host).mpv.doubles["time-pos"] = 210.0
    song_marks_ui.next_song(host)
    assert host.said == ["Back to live."]


def test_next_song_while_live_says_there_is_none_yet(host: _Host) -> None:
    _engine(host).mpv.doubles["time-pos"] = 258.0
    song_marks_ui.next_song(host)
    assert host.said == ["You are listening live; there is no next song yet."]


def test_no_marks_is_said_rather_than_silence(host: _Host) -> None:
    _engine(host).live_extras.marks.clear()
    song_marks_ui.next_song(host)
    assert host.said == [song_marks_ui.NO_MARKS]


def test_refusals_without_a_buffer(tmp_path: Path, wx_session_app: Any) -> None:
    nothing = _Host(_Controller(None), tmp_path)
    nothing._radio_controller._state = type("S", (), {"station": None})()
    song_marks_ui.previous_song(nothing)
    assert nothing.said == ["Nothing is playing."]
    classic = _Host(_Controller(_Engine(), mpv_active=False), tmp_path)
    song_marks_ui.which_song(classic)
    assert "mpv playback engine" in classic.said[-1]


def test_a_finished_recording_has_no_song_marks(host: _Host) -> None:
    _engine(host).bounded = True
    song_marks_ui.next_song(host)
    assert host.said == [song_marks_ui.RECORDING_REFUSAL]


# -- where am I -----------------------------------------------------------------------


def test_which_song_says_title_position_and_distance_from_live(host: _Host) -> None:
    song_marks_ui.which_song(host)
    assert host.said == [
        "Bravo by Artist, 50 seconds in, song 2 of 3 in the buffer. "
        "1 minute 50 seconds behind live."
    ]


def test_which_song_before_the_first_mark(host: _Host) -> None:
    marks = _engine(host).live_extras.marks
    marks.clear()
    marks.mark("Artist - Late", 200.0)
    song_marks_ui.which_song(host)
    assert host.said == ["No song is marked here yet. 1 minute 50 seconds behind live."]


# -- saving -----------------------------------------------------------------------------


def test_save_current_song_writes_one_file_named_like_a_recording(
    host: _Host, tmp_path: Path
) -> None:
    song_marks_ui.save_current(host)
    dump = _engine(host).mpv.commands[-1]
    assert dump[:3] == ("dump-cache", "100.000", "200.000")
    written = Path(dump[3])
    assert written.parent == tmp_path
    assert written.name.startswith("Jazz 24 - ")
    assert written.name.endswith(" - Artist - Bravo.mp3")
    assert host.said == [f"Saved Bravo by Artist to {tmp_path.name}."]


def test_save_previous_and_next(host: _Host) -> None:
    song_marks_ui.save_previous(host)
    assert _engine(host).mpv.commands[-1][1:3] == ("0.000", "100.000")
    song_marks_ui.save_next(host)
    # The song still playing is saved as far as it has got: up to the live edge.
    assert _engine(host).mpv.commands[-1][1:3] == ("200.000", "260.000")


def test_save_all_writes_every_buffered_song_to_its_own_file(host: _Host, tmp_path: Path) -> None:
    song_marks_ui.save_all(host)
    dumps = [c for c in _engine(host).mpv.commands if c[0] == "dump-cache"]
    assert len(dumps) == 3
    assert len({d[3] for d in dumps}) == 3
    assert host.said == [f"Saved 3 songs to {tmp_path.name}."]


def test_a_station_change_mid_save_never_saves_from_the_new_buffer(
    host: _Host, tmp_path: Path
) -> None:
    mpv = _engine(host).mpv
    first_dump = mpv.command

    def change_after_first(*args: str) -> None:
        first_dump(*args)
        if args[0] == "dump-cache":
            _engine(host).live_extras.on_load()  # the listener chose another station

    mpv.command = change_after_first  # type: ignore[method-assign]
    song_marks_ui.save_all(host)
    dumps = [c for c in mpv.commands if c[0] == "dump-cache"]
    assert len(dumps) == 1, "the other two positions belong to the old buffer"
    assert host.said == [f"Saved 1 of 3 songs to {tmp_path.name}; the rest failed."]


def test_saving_the_same_song_twice_never_overwrites(host: _Host) -> None:
    song_marks_ui.save_current(host)
    song_marks_ui.save_current(host)
    dumps = [c[3] for c in _engine(host).mpv.commands if c[0] == "dump-cache"]
    assert dumps[0] != dumps[1]


def test_save_previous_at_the_oldest_song_says_so(host: _Host) -> None:
    _engine(host).mpv.doubles["time-pos"] = 50.0
    song_marks_ui.save_previous(host)
    assert host.said == ["There is no earlier song in the buffer."]


def test_a_failed_save_is_said(host: _Host) -> None:
    def refuse(*_args: str) -> None:
        raise OSError("disk full")

    _engine(host).mpv.command = refuse  # type: ignore[method-assign]
    song_marks_ui.save_current(host)
    assert host.said == ["Bravo by Artist could not be saved."]


# -- the station's own time-shift length ----------------------------------------------


def _favorite(host: _Host) -> Any:
    host._radio_favorites.add(STATION)
    return host._radio_favorites.favorites[0]


def test_choosing_a_station_length_saves_it_and_says_when_it_applies(
    host: _Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    favorite = _favorite(host)
    asked: list[tuple[str, list[str], int]] = []

    def answer(_app: Any, _prompt: str, title: str, labels: list[str], index: int) -> int:
        asked.append((title, labels, index))
        return 3  # (-1, 0, 30, 60, ...) -> 60 minutes

    monkeypatch.setattr(song_marks_ui, "_ask_choice", answer)
    song_marks_ui.choose_station_timeshift(host)
    assert asked[0][0] == "Time-Shift Length for Jazz 24"
    assert asked[0][2] == 0  # it followed Preferences until now
    assert favorite.timeshift_minutes == 60
    assert host.persisted == 1
    assert host.said == [
        "Jazz 24: 1 hour, on disk. It takes effect the next time this station starts."
    ]


def test_cancelling_the_choice_changes_nothing(
    host: _Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    favorite = _favorite(host)
    monkeypatch.setattr(song_marks_ui, "_ask_choice", lambda *_a: None)
    song_marks_ui.choose_station_timeshift(host)
    assert favorite.timeshift_minutes == timeshift.FOLLOW_PREFERENCES
    assert host.persisted == 0
    assert host.said == []


def test_a_station_that_is_not_a_favorite_is_told_how(host: _Host) -> None:
    song_marks_ui.choose_station_timeshift(host)
    assert host.said[0].startswith("Add this station to your favorites first")


def test_the_selected_favorite_is_used_when_the_playing_station_is_not_one(
    host: _Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = RadioStation(name="News", stream_url="http://example.invalid/news")
    host._radio_favorites.add(other)
    host.selected = host._radio_favorites.favorites[0]
    monkeypatch.setattr(song_marks_ui, "_ask_choice", lambda *_a: 1)  # memory only
    song_marks_ui.choose_station_timeshift(host)
    assert host.selected.timeshift_minutes == 0


def test_the_engine_gets_the_stations_own_length_before_it_plays(host: _Host) -> None:
    favorite = _favorite(host)
    favorite.timeshift_minutes = 180
    host._radio_history.timeshift_minutes = 30
    controller = host._radio_controller
    controller._resolve_timeshift_minutes = lambda st: song_marks_ui.resolve_timeshift_minutes(
        host, st
    )
    engine = _engine(host)
    engine_selection.prepare_station(controller, engine)
    assert engine.configured == [180]
    assert engine.live_extras.marks.station_name == "Jazz 24"
    favorite.timeshift_minutes = timeshift.FOLLOW_PREFERENCES
    engine_selection.prepare_station(controller, engine)
    assert engine.configured[-1] == 30


# -- the second title source --------------------------------------------------------


def test_a_title_from_the_icy_reader_marks_the_live_edge(host: _Host) -> None:
    song_marks_ui.note_title(host, "Artist - Delta")
    marks = _engine(host).live_extras.marks.marks
    assert (marks[-1].title, marks[-1].position) == ("Artist - Delta", 260.0)


def test_note_title_is_silent_and_safe_without_mpv(tmp_path: Path) -> None:
    quiet = _Host(_Controller(None, mpv_active=False), tmp_path)
    song_marks_ui.note_title(quiet, "Artist - Delta")
    assert quiet.said == []
