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


def handle_episode_key(dialog: Any, event: Any) -> None:
    """Ctrl+1..Ctrl+9 and Enter, over this episode's Quick Actions.

    A dimmed action answers with *which state* dimmed it (11.2) rather than
    the old "that Quick Action is not available", which is a dead end you
    cannot see around -- and Ctrl+3 on a dimmed row used to say nothing at
    all until the caller added a sentence of its own.
    """
    from quill.ui.podcasts.manager_menus import direct_key_action

    wx = dialog._wx
    code = event.GetKeyCode()
    if event.ControlDown() and not event.ShiftDown() and not event.AltDown():
        if ord("1") <= code <= ord("9"):
            actions = dialog._resolved_episode_actions()
            resolved = direct_key_action(actions, code - ord("0"))
            if resolved is None:
                dialog._announce("There is no Quick Action on that number.")
            elif resolved.enabled:
                resolved.run()
            else:
                dialog._announce(resolved.unavailable_sentence())
            return
    if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
        actions = dialog._resolved_episode_actions()
        if actions:
            if actions[0].enabled:
                actions[0].run()
            else:
                dialog._announce(actions[0].unavailable_sentence())
            return
    event.Skip()
