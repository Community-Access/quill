"""Rewind and Forward by tap count: the timer, and what is said when it fires.

The tiers and the hold-versus-tap rule are pure logic in
:mod:`quill.core.radio.tiered_seek`. This module owns the two things that
cannot be pure: the short wait that lets a burst of presses settle, and the
one announcement afterwards.

**The announcement is where you landed, never how far you moved** --
"2 minutes 10 seconds of 18 minutes", or "3 minutes behind live". The
listener knows how many times they pressed; what they cannot know without
being told is the position, which no screen reader says on its own (GATE-13).

**Refusals are immediate.** Nothing playing, or a live stream on an engine with
no buffer, is said at the first press rather than after the wait: a key that
answers half a second late reads as a key that did nothing.

The same keys as before (Ctrl+Shift+Left and Right); a single tap now moves 12
seconds rather than 30, and a second or third tap goes further.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from quill.core.radio.tiered_seek import SETTLE_SECONDS, SeekBurst

#: ``apply(host, signed_seconds)``: what a settled burst does.
Apply = Callable[[Any, int], None]


def _burst(host: Any) -> SeekBurst:
    burst = getattr(host, "_tiered_seek_burst", None)
    if not isinstance(burst, SeekBurst):
        burst = SeekBurst()
        host._tiered_seek_burst = burst
    return burst


def _stop_timer(host: Any) -> None:
    timer = getattr(host, "_tiered_seek_timer", None)
    host._tiered_seek_timer = None
    stop = getattr(timer, "Stop", None)
    if callable(stop):
        try:
            stop()
        except Exception:  # noqa: BLE001 - a dead timer is already stopped
            pass


def _start_timer(host: Any) -> None:
    """Wait for the burst to settle, then :func:`settle`.

    A host may supply ``tiered_seek_scheduler(delay_ms, callback)`` (tests do,
    to control time). Without a running wx app there is nothing to wait with,
    so the burst settles at once -- one press, one tap's distance.
    """
    _stop_timer(host)
    delay_ms = int(SETTLE_SECONDS * 1000)
    scheduler = getattr(host, "tiered_seek_scheduler", None)
    if callable(scheduler):
        host._tiered_seek_timer = scheduler(delay_ms, lambda: settle(host))
        return
    try:
        import wx

        if wx.GetApp() is None:
            raise RuntimeError("no wx app to time the burst with")
        host._tiered_seek_timer = wx.CallLater(delay_ms, settle, host)
    except Exception:  # noqa: BLE001 - no timer means no wait, never no seek
        settle(host)


def press(host: Any, direction: int, apply: Apply, *, now: float | None = None) -> None:
    """Count one press of Rewind (``-1``) or Forward (``+1``).

    A press in the other direction first settles the burst in progress, so
    Rewind-Rewind-Forward is a minute back and then 12 seconds forward, not a
    muddle of the two.
    """
    burst = _burst(host)
    wanted = 1 if direction > 0 else -1
    if burst.active and burst.direction != wanted:
        settle(host)
    burst.press(wanted, time.monotonic() if now is None else now)
    host._tiered_seek_apply = apply
    _start_timer(host)


def settle(host: Any) -> None:
    """End the burst now: one seek, sized for the final count."""
    _stop_timer(host)
    amount = _burst(host).take()
    apply = getattr(host, "_tiered_seek_apply", None)
    if amount and callable(apply):
        apply(host, amount)


# -- the main window: a timeline when there is one, the live buffer otherwise --


def press_main(host: Any, direction: int) -> None:
    """The main window's Rewind / Forward (``radio.rewind`` / ``radio.forward``)."""
    controller = host._radio_controller
    if not controller.is_seekable():
        if getattr(getattr(controller, "state", None), "station", None) is None:
            host._announce("Nothing is playing.")
            return
        probe = getattr(controller, "behind_live_seconds", None)
        if callable(probe) and probe() is None:
            host._announce(host._radio_dvr_unavailable_message())
            return
    press(host, direction, apply_main)


def apply_main(host: Any, seconds: int) -> None:
    """Move a settled burst along the timeline, or within the live buffer."""
    controller = host._radio_controller
    if controller.is_seekable():
        apply_timeline(host, seconds)
        return
    if seconds < 0:
        behind = controller.rewind(-seconds)
    else:
        behind = controller.forward(seconds)
    if behind is None:
        host._announce(host._radio_dvr_unavailable_message())
        return
    host._announce(host._radio_behind_live_phrase(behind))


def apply_timeline(host: Any, seconds: int) -> None:
    """Move a settled burst along a recording's timeline and say where it is."""
    from quill.ui.radio import bounded_playback_ui

    controller = bounded_playback_ui._controller(host)
    if controller is None or not controller.is_seekable():
        host._announce(bounded_playback_ui.LIVE_REFUSAL)
        return
    controller.skip_by(seconds * 1000)
    host._announce(bounded_playback_ui.describe_position(controller))
