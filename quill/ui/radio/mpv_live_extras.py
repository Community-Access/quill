"""What the mpv radio engine adds to the live buffer: song marks and the cushion.

Two ideas from BlindRadio by serrebidev (MIT), applied to mpv:

* **Song marks** (:mod:`quill.core.radio.song_marks`). mpv's ICY and HLS
  metadata are *timed*: the demuxer files each title change at the timestamp
  it arrived with and hands it over when playback reaches it
  (``demux/demux.c``, ``add_timed_metadata``). So when mpv's title changes,
  ``time-pos`` is where that song starts in the buffer, and the engine marks
  it there. The out-of-band title reader can also report a title; that one
  describes the live edge, so it is marked at ``demuxer-cache-time``, and the
  marks keep whichever sighting is earlier.
* **The adaptive cushion** (:mod:`quill.core.radio.cushion`). The engine's
  poll already watches ``paused-for-cache``; each stall is handed to the
  policy, and when the policy changes its mind ``cache-pause-wait`` is
  written, which mpv honours on the next stall without a reload.

Kept out of ``mpv_radio_engine.py`` so that module stays under its size
ceiling, and wx-free so it can be driven by a fake mpv client in tests. It
needs only ``get_str``, ``get_double``, ``set_str`` and ``command``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from quill.core.radio import cushion
from quill.core.radio.song_marks import SongMarks

_log = logging.getLogger(__name__)

#: Poll ticks between title checks. The engine polls every 200 ms; reading
#: three title properties five times a second buys nothing over once a second.
TITLE_EVERY_TICKS = 5


def seekable_start(raw: str | None, playhead: float | None) -> float | None:
    """The oldest buffered position, from ``demuxer-cache-state`` JSON (pure).

    The range holding the playhead when there is one (the buffer you are in),
    else the first range. ``None`` when mpv reports none or the text is not
    the shape mpv writes.
    """
    try:
        state = json.loads(raw or "")
    except ValueError:
        return None
    ranges = state.get("seekable-ranges") if isinstance(state, dict) else None
    if not isinstance(ranges, list):
        return None
    starts: list[tuple[float, float]] = []
    for entry in ranges:
        if not isinstance(entry, dict):
            continue
        try:
            starts.append((float(entry["start"]), float(entry["end"])))
        except (KeyError, TypeError, ValueError):
            continue
    if not starts:
        return None
    if playhead is not None:
        for start, end in starts:
            if start <= playhead <= end:
                return start
    return starts[0][0]


class LiveExtras:
    """Song marks and the cushion for one mpv engine."""

    def __init__(
        self,
        client: Any,
        *,
        title: Callable[[], str],
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._mpv = client
        self._title = title
        self.marks = SongMarks()
        self.cushion = cushion.CushionPolicy() if clock is None else cushion.CushionPolicy(clock)
        self._ticks = 0
        self._last_title = ""

    # -- positions on the stream timeline -------------------------------------

    def playhead(self) -> float | None:
        return self._mpv.get_double("time-pos")

    def live_edge(self) -> float | None:
        return self._mpv.get_double("demuxer-cache-time")

    def buffer_start(self) -> float | None:
        return seekable_start(self._mpv.get_str("demuxer-cache-state"), self.playhead())

    def codec(self) -> str:
        return str(self._mpv.get_str("audio-codec-name") or "")

    # -- life cycle -------------------------------------------------------------

    def on_load(self) -> None:
        """A new stream: no marks yet, and the normal cushion.

        Written unconditionally: an option set at runtime survives a load, so
        the last station's deep cushion would otherwise carry over.
        """
        self.marks.clear()
        self._last_title = ""
        self._ticks = 0
        self.cushion.reset()
        self._set_cushion(cushion.NORMAL_SECONDS)

    def on_poll(self, *, stalled: bool, was_stalled: bool) -> None:
        """One engine poll tick while a stream is loaded."""
        if stalled and not was_stalled:
            self._set_cushion(self.cushion.stall_started())
        elif was_stalled and not stalled:
            self.cushion.stall_ended()
        elif not stalled:
            self._set_cushion(self.cushion.tick())
        self._ticks += 1
        if self._ticks % TITLE_EVERY_TICKS == 0:
            self._check_title()

    def _set_cushion(self, seconds: float | None) -> None:
        if seconds is None:
            return
        status = self._mpv.set_str("cache-pause-wait", cushion.mpv_value(seconds))
        if isinstance(status, int) and status < 0:
            _log.warning("mpv refused cache-pause-wait=%s (status %s)", seconds, status)

    def _check_title(self) -> None:
        title = self._title()
        if not title or title == self._last_title:
            return
        self._last_title = title
        position = self.playhead()
        if position is None:
            return
        start = self.buffer_start()
        self.marks.mark(title, position, buffer_start=start)
        if start is not None:
            self.marks.forget_before(start)

    def mark_live_edge(self, title: str) -> bool:
        """A title read from outside mpv: it describes the live edge."""
        edge = self.live_edge()
        if edge is None:
            return False
        return self.marks.mark(title, edge, buffer_start=self.buffer_start())

    # -- moving and saving ---------------------------------------------------------

    def seek_to(self, position: float) -> bool:
        try:
            self._mpv.command("seek", f"{max(0.0, position):.3f}", "absolute")
        except Exception:  # noqa: BLE001 - a failed seek must not crash playback
            _log.exception("mpv song seek failed")
            return False
        return True

    def dump(self, start: float, end: float, target: str) -> bool:
        """Write the buffer from *start* to *end* to *target*, as the station sent it.

        mpv's ``dump-cache`` copies the packets without decoding them, into a
        container chosen from the file's extension. Safe from a worker thread:
        the libmpv client API is thread-safe, and the only reason to keep it
        off the UI thread is that a long dump takes a while.
        """
        try:
            self._mpv.command("dump-cache", f"{start:.3f}", f"{end:.3f}", target)
        except Exception:  # noqa: BLE001 - a failed dump is a failed save, never a crash
            _log.exception("mpv dump-cache failed")
            return False
        return True


__all__ = ["TITLE_EVERY_TICKS", "LiveExtras", "seekable_start"]
