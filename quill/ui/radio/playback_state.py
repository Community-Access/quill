"""Quill Radio's playback state model: the states, the snapshot, and the sets.

Lifted out of ``player_controller.py`` when BUFFERING and RECONNECTING joined
the enum. Three reasons, and the first is the one that matters:

1. **Fifteen private copies of one membership rule.** "Is a stream on the air?"
   was spelled ``state in (PLAYING, CONNECTING)`` in fifteen places -- the
   Stop/Play button label, the favorites context menu, three browse dialogs'
   now-playing badge, the sleep inhibitor, the close guard. Adding two states
   without naming that rule would have left every one of them quietly wrong.
   A state model whose membership rule is copied fifteen times is not a state
   model; it is a convention.
2. **The snapshot travelled further than its owner.** ``RadioPlaybackState``
   is handed to every subscriber, and reading one should not mean importing the
   eleven-hundred-line controller that happens to produce it.
3. **GATE-11.** ``player_controller.py`` sat on its ceiling, and the budget is
   a ratchet that says *extract*, not *rebaseline*.

wx-free: the states are plain data, and the wording lives one module over in
:mod:`quill.ui.radio.playback_status`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from quill.core.radio.models import RadioStation
from quill.ui.radio import playback_status


class RadioPlayerState(Enum):
    STOPPED = auto()
    CONNECTING = auto()
    #: Started, then ran out of audio. mpv pauses itself to refill its cache
    #: (``paused-for-cache``), which used to be announced without ever leaving
    #: PLAYING -- so the status bar and the tray tooltip both said "playing"
    #: through dead air, which is the one thing a listener can already tell is
    #: false. Only the mpv engine can report it; wx.media cannot see a stall.
    BUFFERING = auto()
    PLAYING = auto()
    PAUSED = auto()
    #: A dropped live stream being retried by :mod:`quill.ui.radio.live_reconnect`.
    #: It used to re-enter CONNECTING, which is true in the narrow sense and
    #: wrong in every way that matters: "connecting" is what a station the
    #: listener just chose does, and a listener who did not press anything
    #: deserves to be told that the app is recovering rather than starting.
    RECONNECTING = auto()
    ERROR = auto()


#: "Is a stream on the air, or on its way to it?" -- the question a dozen
#: surfaces ask: the Stop/Play button label, the favorites context menu, the
#: browse dialogs' now-playing badge, the sleep inhibitor, and the close
#: confirmation that must not throw away live audio.
#:
#: It exists because the answer used to be spelled out as
#: ``(PLAYING, CONNECTING)`` in fifteen places. Adding BUFFERING and
#: RECONNECTING to the enum without this would have left every one of them
#: quietly wrong -- Stop turning back into Play mid-stall, the machine allowed
#: to sleep during a reconnect, a favorite losing its "playing" badge every
#: time its stream hiccuped. A state model with fifteen private copies of its
#: own membership rule is not a state model.
ACTIVE_STATES: frozenset[RadioPlayerState] = frozenset({
    RadioPlayerState.CONNECTING,
    RadioPlayerState.BUFFERING,
    RadioPlayerState.PLAYING,
    RadioPlayerState.RECONNECTING,
})

#: The same, plus PAUSED: "is there a station here to load again?" -- what the
#: output-device, Sound Enhancements and engine-preference switches ask before
#: restarting the stream so the new setting takes effect.
RESTARTABLE_STATES: frozenset[RadioPlayerState] = ACTIVE_STATES | {RadioPlayerState.PAUSED}

#: "Is a stream *running*?" -- narrower than ACTIVE_STATES, and the set every
#: site that used to compare against PLAYING alone actually meant. Before
#: BUFFERING existed, a stall stayed PLAYING, so "PLAYING" and "running" were
#: the same word; splitting the two would have silently broken Play/Pause into
#: a restart mid-stall, stopped the track-title poll every time a stream
#: hiccuped, and let a sleep timer that fired during a stall leave the radio on
#: all night. Not the same as ACTIVE_STATES: connecting and reconnecting are on
#: the way to running, not running.
RUNNING_STATES: frozenset[RadioPlayerState] = frozenset({
    RadioPlayerState.PLAYING,
    RadioPlayerState.BUFFERING,
})


@dataclass(slots=True)
class RadioPlaybackState:
    """A snapshot handed to every subscriber on every change."""

    state: RadioPlayerState
    station: RadioStation | None
    muted: bool
    volume_percent: int
    message: str = ""

    @property
    def status_text(self) -> str:
        """One line for the status bar / tray tooltip.

        The wording lives in :mod:`quill.ui.radio.playback_status` so the three
        surfaces that render it -- the status-bar cell, the tray tooltip and the
        mini-player -- read one implementation, and a test of the wording does
        not have to build a controller and therefore a window.
        """
        return playback_status.status_text(
            state=self.state.name,
            station=self.station.name if self.station is not None else "",
            muted=self.muted,
            message=self.message,
        )
