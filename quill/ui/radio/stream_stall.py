"""A stream that ran out of audio: the state, the sentence, and the way back.

The fourth of the "what happens to a stream" modules, beside
:mod:`quill.ui.radio.live_reconnect`, :mod:`quill.ui.radio.resume_playback` and
:mod:`quill.ui.radio.engine_selection` -- plain functions taking the controller
as ``host``, so all four read alike and none of them is a second class hiding
inside ``player_controller``.

**What it fixes.** ``MpvRadioEngine`` used to call the host's announcer
directly when mpv reported ``paused-for-cache``. The words "Buffering..."
arrived and the playback state stayed PLAYING, so every surface that renders
the state -- the focusable status bar's Now Playing cell, the tray tooltip, the
mini-player -- went on claiming playback through dead air. The engine now
reports both edges of a stall and they arrive here, where a stall becomes a
state as well as a sentence.

**What it deliberately does not do.** It does not touch the once-per-run earcon
latch. That lives in the host (``_radio_announce_buffering``), where ten
rebuffers make one sound and ten sentences, and second-guessing it from here
would give a flaky stream its earcon back.

wx-free.
"""

from __future__ import annotations

from typing import Any


def handle(host: Any, active: bool) -> None:
    """Turn the engine's stall report into a playback state on *host*.

    Entering a stall announces; leaving one does not. A stream that stalls ten
    times is genuinely playing ten times, and cueing each recovery would
    reintroduce exactly the ten-earcons-in-a-row problem ``_set_state``'s
    transition check exists to stop -- which is what ``cue=False`` is for.
    """
    from quill.ui.radio.playback_state import RUNNING_STATES, RadioPlayerState

    if host._state.state not in RUNNING_STATES:
        # A report that lands after a stop, an error, a reconnect or a switch to
        # another station describes a stream nobody is listening to.
        return
    if active:
        host._set_state(RadioPlayerState.BUFFERING)
        if host._on_buffering is not None:
            host._on_buffering()
        return
    host._set_state(RadioPlayerState.PLAYING, cue=False)
