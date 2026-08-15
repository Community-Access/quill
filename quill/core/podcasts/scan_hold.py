"""Hold to scan forward, release to drop back.

Skipping forward in fixed jumps answers *"get me past this"*. It does not answer
*"where does this bit end?"* -- for that you need to hear the audio going past,
which is what scanning is, and what a tape deck's fast-forward always did.

The gesture is **press and hold**: while the key is down, playback runs at four
times speed; the moment it comes up, it drops back to exactly the speed it was
at. Both edges are announced, because the one thing that must never happen is
being left at 4x without knowing it -- a player stuck at four times speed with
no announcement is indistinguishable from a broken one.

Why four: fast enough to cover a minute in fifteen seconds, slow enough that
speech is still recognisable as speech. Anything past about six is noise, and
scanning you cannot follow is just seeking with extra steps.

**Release is inferred from the repeat, not from a key-up event.** Holding a key
produces a stream of auto-repeats; when they stop, the key is up. That is
deliberate: a key-up can be missed entirely if focus moves, a dialog opens, or
the window is deactivated mid-hold, and every one of those would leave playback
at 4x forever. A repeat that simply stops arriving cannot fail that way -- the
worst case is ending the scan a fraction of a second late.

wx-free, strict-typed, pure. The clock and the keyboard belong to the caller.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Playback speed while the key is held.
SCAN_RATE = 4.0

#: How long after the last auto-repeat to treat the key as released. Windows'
#: fastest repeat rate is about 30 per second and its slowest about 2; 400 ms
#: comfortably outlasts the slowest setting, so a scan never stutters, and is
#: short enough that the drop back feels immediate.
RELEASE_GRACE_MS = 400

#: What is said as the scan starts. Short on purpose: it is spoken over audio
#: that is already playing, and the listener is holding a key down.
BEGIN_MESSAGE = "Scanning forward, 4 times speed."


@dataclass(slots=True)
class ScanState:
    """Whether a scan is running, and what to go back to when it ends."""

    active: bool = False
    #: The speed in force before the scan. Restored exactly -- somebody who
    #: listens at 1.5 must not be handed back 1.0 for having scanned.
    restore_rate: float = 1.0
    #: When the most recent auto-repeat arrived, in the caller's own clock.
    last_repeat_ms: int = 0


def begin(state: ScanState, *, current_rate: float, now_ms: int) -> bool:
    """Start scanning, if it is not already running. True when this started it.

    Idempotent under auto-repeat, which is the whole point: the second and
    fiftieth repeat of a held key must extend the scan, not restart it and
    certainly not overwrite ``restore_rate`` with 4.0.
    """
    state.last_repeat_ms = now_ms
    if state.active:
        return False
    state.active = True
    state.restore_rate = current_rate if current_rate > 0 else 1.0
    return True


def keep_alive(state: ScanState, *, now_ms: int) -> None:
    """Record another auto-repeat: the key is still down."""
    if state.active:
        state.last_repeat_ms = now_ms


def should_end(state: ScanState, *, now_ms: int) -> bool:
    """Whether the repeats have stopped long enough to call the key released."""
    if not state.active:
        return False
    return (now_ms - state.last_repeat_ms) >= RELEASE_GRACE_MS


def end(state: ScanState) -> float:
    """Stop scanning and return the speed to restore."""
    state.active = False
    return state.restore_rate if state.restore_rate > 0 else 1.0


def end_message(rate: float) -> str:
    """What is said as the scan stops -- always naming the speed returned to.

    Named rather than merely "back to normal" because it is often not normal:
    the listener may have been at 1.5 or 0.8, and confirming the actual number
    is what makes it safe to trust the key.
    """
    if abs(rate - 1.0) < 0.01:
        return "Back to normal speed."
    return f"Back to {rate:g} times speed."
