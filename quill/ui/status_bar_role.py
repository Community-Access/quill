"""Telling Windows that the status bar is a status bar.

Both editors build their bar as a :class:`wx.Panel` holding a row of focusable
buttons, and that is the right shape: a native ``wxStatusBar`` is painted text
with no focus, no keyboard route and nothing for a screen reader to land on,
which is why neither editor uses one. What the panel never did was *say* what it
is. wx installs its own accessible on a panel reporting ``ROLE_SYSTEM_CLIENT``,
so to MSAA and UIA the bar is an anonymous box of buttons.

That is invisible right up until somebody presses the key for it. JAWS's
Insert+Page Down means "read the status bar": it looks for a control with the
status-bar role and, finding none, falls back to screen-scraping the bottom line
of the window -- which is why the readout has been partial and unreliable and
why one user asked "I wonder if we need to remove this description from the
status bar, or how we can make it reliable?" The answer is neither removing
anything nor scraping better: it is answering the question the reader is
actually asking.

Two roles, because a status bar's *cells* are not buttons either. A reader
walking a status bar expects ``ROLE_SYSTEM_STATUSBAR`` holding text, and
announcing "Position, button" on arrival is the kind of small wrongness that
makes somebody stop trusting the row. The buttons stay buttons to the keyboard
-- Enter still acts, the arrows still move -- and read as what they are.
"""

from __future__ import annotations

from typing import Any

__all__ = ["mark_as_status_bar", "mark_as_status_cell"]


def _role_accessible(wx: Any, role: int) -> Any:
    """A ``wx.Accessible`` subclass that reports *role* and defers on the rest."""

    class _Role(wx.Accessible):  # type: ignore[misc]
        def GetRole(self, childId: int) -> tuple[int, int]:  # noqa: N803 - wx API shape
            return (wx.ACC_OK, role)

    return _Role


def mark_as_status_bar(wx: Any, panel: Any) -> bool:
    """Report *panel* to Windows as a status bar. ``True`` when it took.

    Never raises. ``wx.Accessible`` is a Windows-only build option and the
    accessible a panel already carries is wx's own; replacing it is best effort,
    and a bar that keeps the wrong role is exactly as usable by keyboard as it
    was a moment ago.
    """
    return _set_role(wx, panel, getattr(wx, "ROLE_SYSTEM_STATUSBAR", None))


def mark_as_status_cell(wx: Any, button: Any) -> bool:
    """Report *button* as a status-bar cell rather than a button.

    The cell announces its own name and value either way; this is what stops
    the reader adding "button" to every one of them while walking the row.
    """
    return _set_role(wx, button, getattr(wx, "ROLE_SYSTEM_STATICTEXT", None))


def _set_role(wx: Any, window: Any, role: int | None) -> bool:
    if role is None or not hasattr(wx, "Accessible"):
        return False
    try:
        window.SetAccessible(_role_accessible(wx, role)(window))
    except Exception:  # noqa: BLE001 - an accessible role is never worth a crash
        return False
    return True
