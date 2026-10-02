"""Closing Quill Player keeps the listening place and stops its clocks (qc.md F-12).

The Player saved its resume position on a fifteen-second timer and had no close
handler at all, so closing the window could lose up to fifteen seconds of a
listener's place -- and left two ``wx.Timer`` objects running, owned by a frame
that was gone. The timer-ownership gate (``tests/unit/ui/test_timer_ownership.py``)
found it. Kept out of ``player.py``, which is at its GATE-11 budget.
"""

from __future__ import annotations

from typing import Any

__all__ = ["on_player_close"]


def on_player_close(app: Any, event: Any) -> None:
    """Save the position, stop the clocks, and let the window close."""
    try:
        app._save_resume()
    except Exception:  # noqa: BLE001 - closing must never be blocked by a save
        pass
    for name in ("_resume_timer", "_sleep_timer", "_status_timer", "_listen_timer"):
        timer = getattr(app, name, None)
        if timer is None:
            continue
        try:
            timer.Stop()
        except Exception:  # noqa: BLE001 - a timer already gone is already stopped
            pass
    event.Skip()
