"""The seek keys pick the right kind of seek (x.md item 8).

A live stream and a finished video are not the same thing to move around in,
and Ctrl+Shift+Left/Right used to treat them as one:

* a **live stream** seeks within mpv's cache, and the honest thing to report
  is how far behind the live edge you now are;
* a **finished video** has a real timeline, so the same keystroke should move
  along it and say "3 minutes of 18 minutes".

Sending a video down the DVR path announced a distance behind a live edge that
does not exist -- a fabricated measurement (rule A-10) on the one source where
the honest number was available all along. It also left
``bounded_playback_ui.skip_back`` / ``skip_forward`` with no caller at all:
written for exactly this, and unreachable.
"""

from __future__ import annotations

from typing import Any

from quill.ui.main_frame_radio import RadioMixin


class _Controller:
    def __init__(self, *, seekable: bool, position: int = 100_000) -> None:
        self._seekable = seekable
        self.position = position
        self.duration = 1_120_000
        self.dvr_calls: list[tuple[str, int]] = []
        self.skips: list[int] = []
        self.chapter_index = -1

    # -- the bounded (video) side
    def is_seekable(self) -> bool:
        return self._seekable

    def duration_ms(self) -> int:
        return self.duration if self._seekable else 0

    def position_ms(self) -> int:
        return self.position

    def skip_by(self, ms: int) -> bool:
        self.skips.append(ms)
        self.position = max(0, min(self.duration, self.position + ms))
        return True

    def current_chapter_index(self) -> int:
        return self.chapter_index

    def chapters(self) -> list[object]:
        return []

    # -- the live (DVR) side
    def rewind(self, seconds: int = 30) -> float | None:
        self.dvr_calls.append(("rewind", seconds))
        return 45.0

    def forward(self, seconds: int = 30) -> float | None:
        self.dvr_calls.append(("forward", seconds))
        return 15.0

    @property
    def state(self) -> Any:
        class _S:
            station = object()

        return _S()

    # bounded_playback_ui.describe_position reaches the engine for position
    @property
    def _engine(self) -> Any:
        controller = self

        class _E:
            @staticmethod
            def position_ms() -> int:
                return controller.position

        return _E()


class _Host:
    """The slice of MainFrame the two transport commands actually use."""

    radio_rewind = RadioMixin.radio_rewind
    radio_forward = RadioMixin.radio_forward
    _radio_seek_bounded = RadioMixin._radio_seek_bounded
    # staticmethod on the real mixin; re-wrap so it does not pick up self here.
    _radio_behind_live_phrase = staticmethod(RadioMixin._radio_behind_live_phrase)
    _radio_dvr_unavailable_message = RadioMixin._radio_dvr_unavailable_message

    def __init__(self, controller: _Controller) -> None:
        self._radio_controller = controller
        self.announced: list[str] = []

    def _announce(self, text: str) -> None:
        self.announced.append(text)


# -- a finished video --------------------------------------------------------


def test_a_video_seeks_along_its_own_timeline() -> None:
    host = _Host(_Controller(seekable=True))

    host.radio_forward()

    assert host._radio_controller.skips == [30_000]
    assert host._radio_controller.dvr_calls == [], "the DVR path must not be used"


def test_rewinding_a_video_steps_back_along_the_timeline() -> None:
    host = _Host(_Controller(seekable=True))

    host.radio_rewind()

    assert host._radio_controller.skips == [-30_000]
    assert host._radio_controller.dvr_calls == []


def test_a_video_never_reports_a_distance_behind_a_live_edge() -> None:
    """The fabricated measurement this fixes: a finished video has no live
    edge to be behind."""
    host = _Host(_Controller(seekable=True))

    host.radio_forward()
    host.radio_rewind()

    spoken = " ".join(host.announced).casefold()
    assert "behind live" not in spoken
    assert "live" not in spoken


def test_a_video_says_where_it_landed_in_words() -> None:
    host = _Host(_Controller(seekable=True))

    host.radio_forward()

    said = host.announced[-1]
    assert "minute" in said and " of " in said
    assert ":" not in said, "spoken positions are words, never a clock face"


# -- a live stream -----------------------------------------------------------


def test_a_live_stream_still_uses_the_dvr_buffer() -> None:
    host = _Host(_Controller(seekable=False))

    host.radio_rewind()
    host.radio_forward()

    assert host._radio_controller.dvr_calls == [("rewind", 30), ("forward", 30)]
    assert host._radio_controller.skips == [], "a live stream has no timeline to skip along"


def test_a_live_stream_still_reports_how_far_behind_it_is() -> None:
    host = _Host(_Controller(seekable=False))

    host.radio_rewind()

    assert "behind live" in host.announced[0].casefold()


def test_a_stream_without_dvr_still_explains_itself() -> None:
    class _NoDvr(_Controller):
        def rewind(self, seconds: int = 30) -> float | None:
            return None

    host = _Host(_NoDvr(seekable=False))
    host.radio_rewind()

    assert "mpv" in host.announced[0] or "Nothing is playing" in host.announced[0]
