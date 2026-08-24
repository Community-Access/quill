"""Switching audio renditions goes through the ordinary play path.

Reported 2026-08-23: "the audio described track doesn't play when I switch to
it", with a status line reading ``enhanced.mp3`` -- the Sound Enhancements
relay, still pointed at the rendition the listener had just switched *away*
from. Loading the new rendition straight into the engine was the short route,
and it skipped everything the play path does: the relay is built per URL, the
volume and speed the station is due are re-applied there, and so are the one
cross-engine rescue and the spoken error a failed load owes.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.audio_tracks import AudioTrack
from quill.ui.radio import track_selection
from quill.ui.radio.playback_state import RadioPlayerState


class _Station:
    display_name = "A Lecture"
    stream_url = "https://www.youtube.com/watch?v=UusppshIAio"


class _State:
    def __init__(self) -> None:
        self.station = _Station()
        self.state = RadioPlayerState.PLAYING
        self.message = ""


class _Controller:
    """The controller's documented playback surface, and nothing else."""

    def __init__(self, *, fails: bool = False, seekable: bool = True) -> None:
        self._state = _State()
        self._playback_url_override = ""
        self._selected_audio_track: Any = None
        self._pending_resume_ms = 0
        self._shape_declared = 0
        self._fails = fails
        self._seekable = seekable
        self.resolved_plays: list[str] = []

    # what play_audio_track is allowed to touch
    def position_ms(self) -> int:
        return 90_000

    def is_seekable(self) -> bool:
        return self._seekable

    def _play_resolved_station(self, station: Any) -> None:
        # Faithful to the real one in the two ways that matter here.
        self._selected_audio_track = None
        self.resolved_plays.append(self._playback_url_override)
        if self._fails:
            self._state.state = RadioPlayerState.ERROR
            return
        self._state.state = RadioPlayerState.CONNECTING

    def _declare_source_shape(self) -> None:
        self._shape_declared += 1


DESCRIBED = AudioTrack(
    track_id="251-1",
    language="en",
    label="English (described)",
    stream_url="https://media.test/described.webm",
)


def test_switching_replays_through_the_controller_not_the_engine() -> None:
    controller = _Controller()

    assert track_selection.play_audio_track(controller, DESCRIBED) is True

    # The play path ran, and it ran with the new rendition's URL -- which is
    # what rebuilds the Sound Enhancements relay around the right stream.
    assert controller.resolved_plays == ["https://media.test/described.webm"]
    assert controller._playback_url_override == "https://media.test/described.webm"


def test_the_chosen_track_survives_the_reload() -> None:
    """``_play_resolved_station`` clears it by design; the choice is recorded after."""
    controller = _Controller()

    track_selection.play_audio_track(controller, DESCRIBED)

    assert controller._selected_audio_track is DESCRIBED


def test_your_place_is_kept_across_the_switch() -> None:
    controller = _Controller()

    track_selection.play_audio_track(controller, DESCRIBED)

    assert controller._pending_resume_ms == 90_000


def test_a_live_stream_has_no_place_to_keep() -> None:
    controller = _Controller(seekable=False)

    track_selection.play_audio_track(controller, DESCRIBED)

    assert controller._pending_resume_ms == 0


def test_a_failed_switch_leaves_the_old_rendition_the_true_answer() -> None:
    controller = _Controller(fails=True)
    controller._playback_url_override = "https://media.test/original.webm"
    original = AudioTrack(track_id="251-0", language="en", label="English")
    controller._selected_audio_track = original

    assert track_selection.play_audio_track(controller, DESCRIBED) is False

    # Otherwise the next reconnect is handed a URL that did not load, and the
    # picker claims a track nobody is hearing.
    assert controller._playback_url_override == "https://media.test/original.webm"
    assert controller._selected_audio_track is original


def test_a_track_with_no_address_is_not_a_switch() -> None:
    controller = _Controller()
    assert track_selection.play_audio_track(controller, AudioTrack(track_id="x")) is False
    assert controller.resolved_plays == []
