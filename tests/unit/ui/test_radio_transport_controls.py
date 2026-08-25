"""The transport pair, and the menus that stopped saying it three times.

Two reports, one afternoon (2026-08-25):

* *"can we get the play button to convert to a stop button instead of two
  buttons across the UI where these buttons appear"*
* *"we need a way to handle stop in the cases of podcasts along with play and
  pause/stop... as well as local or offline content, not just podcasts"*

So: one control that starts and ends, one that pauses -- and the pause one
dimmed, not missing, on a live station. These cover the player side of that
(the wording rules are pinned in ``test_transport_face.py``), plus the tray
menu, which had grown *three* transport rows for one player.
"""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path

import pytest

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"
_MAIN_FRAME_RADIO = (_UI / "main_frame_radio.py").read_text(encoding="utf-8")
_PLAYER_PANEL = (_UI / "radio" / "player_panel.py").read_text(encoding="utf-8")


class _CastPhase(Enum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()


class _CastState:
    """Quill Cast's shape: an episode, no station field at all."""

    def __init__(self, phase: _CastPhase, title: str = "Episode 12") -> None:
        self.state = phase
        self.title = title
        self.episode_guid = "guid"
        self.show_id = "show"


class _CastHost:
    def __init__(self, state: _CastState) -> None:
        self._podcast_controller = type("C", (), {"state": state})()


def _radio_host(phase: object, *, is_recording: bool = False, station: bool = True):
    """Radio's shape: a ``RadioPlayerState`` and a station that may be a file."""
    stationish = type("S", (), {"name": "ACB Mainstream", "is_recording": is_recording})()
    state = type("St", (), {"state": phase, "station": stationish if station else None})()
    return type("H", (), {"_radio_controller": type("C", (), {"state": state})()})()


def test_a_live_station_is_playing_and_not_bounded() -> None:
    from quill.ui.radio import transport_face
    from quill.ui.radio.playback_state import RadioPlayerState

    assert transport_face.state(_radio_host(RadioPlayerState.PLAYING)) == (True, False, False)


def test_a_stalled_live_station_is_still_playing() -> None:
    """BUFFERING must not flip Stop back to Play mid-stall.

    That is the exact bug ``ACTIVE_STATES`` was extracted to prevent, and a
    label is one more place it could have come back.
    """
    from quill.ui.radio import transport_face
    from quill.ui.radio.playback_state import RadioPlayerState

    playing, _bounded, paused = transport_face.state(_radio_host(RadioPlayerState.BUFFERING))
    assert playing and not paused


def test_a_recording_is_bounded_so_pause_is_offered() -> None:
    from quill.ui.radio import transport_face
    from quill.ui.radio.playback_state import RadioPlayerState

    host = _radio_host(RadioPlayerState.PLAYING, is_recording=True)
    _primary, pause = transport_face.faces(host)

    assert transport_face.state(host)[1] is True
    assert pause.plain == "Pause"
    assert pause.enabled


def test_a_stopped_player_reads_play_even_with_a_station_still_loaded() -> None:
    """The label probe is narrower than the "may this verb run" probe.

    ``_state`` keeps a loaded station counting as playing so Stop is not
    refused; a *label* that did the same would say Stop with nothing on.
    """
    from quill.ui.radio import transport_face
    from quill.ui.radio.playback_state import RadioPlayerState

    primary, pause = transport_face.faces(_radio_host(RadioPlayerState.STOPPED))

    assert primary.plain == "Play"
    assert not pause.enabled


def test_a_paused_podcast_reads_stop_and_resume() -> None:
    from quill.ui.radio import transport_face

    primary, pause = transport_face.faces(_CastHost(_CastState(_CastPhase.PAUSED)))

    assert (primary.plain, pause.plain) == ("Stop", "Resume")
    assert pause.enabled


def test_a_playing_podcast_reads_stop_and_pause() -> None:
    from quill.ui.radio import transport_face

    primary, pause = transport_face.faces(_CastHost(_CastState(_CastPhase.PLAYING)))

    assert (primary.plain, pause.plain) == ("Stop", "Pause")
    assert pause.enabled


def test_a_host_with_no_player_at_all_dims_rather_than_raising() -> None:
    from quill.ui.radio import transport_face

    primary, pause = transport_face.faces(object())

    assert primary.plain == "Play"
    assert not pause.enabled


def test_the_tray_menu_no_longer_carries_its_own_transport_rows() -> None:
    """It had Play/Pause, Stop, and then the status bar's Play-or-Stop.

    Three rows, one player, two of them saying the same thing -- in the menu
    most often reached with the screen reader's own cursor.
    """
    tray = _MAIN_FRAME_RADIO[_MAIN_FRAME_RADIO.index("def _build_radio_tray_menu") :]
    tray = tray[: tray.index("def ", 10)]

    assert 'menu.Append(play_id, "Play / Pause")' not in tray
    assert 'menu.Append(stop_id, "Stop")' not in tray
    assert "self._build_radio_status_bar_menu(menu)" in tray


def test_the_status_bar_menu_renders_the_shared_pair() -> None:
    assert "transport_face.append_menu_rows(self, menu, wx)" in _MAIN_FRAME_RADIO


def test_the_player_panel_resolves_its_two_transport_slots_at_refresh_time() -> None:
    """Not from the static table: a button reading Stop must call stop."""
    assert "TRANSPORT_SLOTS" in _PLAYER_PANEL
    assert "self._transport_face(command_id).command_id" in _PLAYER_PANEL


def test_the_player_panel_still_offers_both_transport_verbs() -> None:
    pytest.importorskip("wx")
    from quill.core.radio import transport_commands as tc
    from quill.ui.radio import player_panel

    on_panel = {command_id for command_id, _label in player_panel.BUTTONS}

    assert tc.STOP in on_panel
    assert tc.PLAY_PAUSE in on_panel
    assert player_panel.TRANSPORT_SLOTS == {tc.STOP, tc.PLAY_PAUSE}
