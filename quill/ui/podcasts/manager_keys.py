"""The Podcast Manager's keyboard hooks, in one place.

Extracted from ``manager_dialog.py`` when hold-to-scan arrived and that module
was at its GATE-11 ceiling -- and it belongs here anyway: the dialog's key
handling had become a chain of "does this one want it, then does that one", and
a chain is easier to read whole than spread through a thousand-line window.

**One hook, not several.** Two ``EVT_CHAR_HOOK`` bindings on the same window
means only one of them decides whether the key travels on, and which one wins is
an implementation detail nobody should have to depend on. So there is a single
entry point and an explicit order: hold-to-scan, then the Winamp transport
letters, then anything else passes through untouched.

Plain functions taking the dialog as ``host``, the house pattern for extracted
UI helpers.
"""

from __future__ import annotations

from typing import Any


def on_char_hook(host: Any, event: Any) -> None:
    """Every key press in the Manager, in the order things get to claim it."""
    scan = getattr(host, "_scan_hold", None)
    if scan is not None and scan.handles(
        key_code=event.GetKeyCode(),
        shift=bool(event.ShiftDown()),
        ctrl=bool(event.ControlDown()),
        alt=bool(event.AltDown()),
    ):
        # Every auto-repeat arrives here, which is how the hold is measured;
        # press() is idempotent for exactly that reason.
        scan.press()
        return
    host._on_winamp_char_hook(event)


def on_key_up(host: Any, event: Any) -> None:
    """End a scan the moment the key actually comes up.

    The watchdog timer in ``scan_hold_control`` would end it anyway; this only
    makes the drop back immediate rather than up to the grace window late.
    """
    scan = getattr(host, "_scan_hold", None)
    if scan is not None and scan.is_scanning and event.GetKeyCode() == host._wx.WXK_RIGHT:
        scan.stop()
    event.Skip()
