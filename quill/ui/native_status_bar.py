"""The status bar Windows itself knows how to answer for.

Both editors build their visible status bar as a :class:`wx.Panel` of focusable
buttons, and that is the right shape for a keyboard: F6 lands in it, the arrows
walk it, Enter acts, Escape leaves. It is the wrong shape for one specific
question, and it is the question screen-reader users ask of a status bar more
than any other -- JAWS's Insert+Page Down, "read the status bar".

That command does not look for a *role*. It looks for a window of class
``msctls_statusbar32`` and reads its parts. Finding none, it falls back to
scraping the bottom line of the window off the screen model, and what it finds
there is whatever happened to land on the last row of a wrapping button panel.
The report that started this read ``"CRLF (Windows) Modified"`` -- the final two
cells of twelve, because the other ten had wrapped onto rows above. Nothing was
broken; the reader was reading the bottom line correctly and the bottom line was
two cells.

:mod:`quill.ui.status_bar_role` was the first attempt: give the panel
``ROLE_SYSTEM_STATUSBAR`` through :class:`wx.Accessible` and let the reader find
it by role. It did not take, and the evidence was a user hearing "Button" at the
end of a cell that had been marked ``ROLE_SYSTEM_STATICTEXT``. ``wx.Accessible``
feeds MSAA only, and the status-bar command is class-based. The role marking
stays -- it costs nothing and helps readers that do consult it -- but it was
never going to answer this.

So the answer is to have the control the reader is looking for. ``wxStatusBar``
on wxMSW *is* ``msctls_statusbar32`` (``wxUSE_NATIVE_STATUSBAR``), so the frame
gets a real one, carrying the same text the button row shows and carrying it
**unclipped**: the parts are read with ``SB_GETTEXT`` rather than off the
screen, so nothing depends on what fits or on how the row wrapped. It is a
mirror, not a second source of truth -- the cells stay the thing that is
maintained, and this reflects them.

One field, not one per cell. A native bar draws its parts at fixed widths and
ellipsises what does not fit, which would reintroduce the exact failure this
replaces for anyone whose reader takes the drawn text; a single field holds the
whole sentence whatever the window's width.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

__all__ = [
    "SEPARATOR",
    "native_status_text",
    "show_native_status_bar",
    "sync_native_status_bar",
]

#: What goes between two cells' worth of text. A full stop, because it is the
#: one separator every screen reader treats the same way at every punctuation
#: level: a sentence break and a pause, spoken by none of them. A vertical bar
#: is read aloud by some and swallowed by others, and a comma is already inside
#: half the values ("Line 3, column 1 of 20").
SEPARATOR = ". "


def native_status_text(labels: Iterable[str]) -> str:
    """One line of text from the cells' labels, in the order they are shown.

    Empty cells are dropped rather than left as a gap, and a label that already
    ends in its own punctuation does not get a second full stop on top of it.
    """
    parts: list[str] = []
    for label in labels:
        text = str(label or "").strip()
        if not text:
            continue
        parts.append(text.rstrip(".") if text.endswith(".") else text)
    return SEPARATOR.join(parts)


def sync_native_status_bar(frame: Any, text: str) -> Any:
    """Put *text* on *frame*'s native status bar, creating it if need be.

    Returns the bar, or ``None`` when there is nothing to put text on -- a stub
    frame in a test, or a platform whose ``wx`` has no status bar at all. Never
    raises: the visible bar is the button row, and a frame that could not build
    this one is exactly as usable as it was a moment ago.
    """
    if frame is None:
        return None
    try:
        bar = frame.GetStatusBar()
        if bar is None:
            # One field. See the module docstring: per-cell fields would be
            # drawn at fixed widths and ellipsised, which is the failure this
            # control exists to end.
            bar = frame.CreateStatusBar(1)
            if bar is not None:
                bar.SetName("Status bar")
        if bar is None:
            return None
        # Written only when it changed. The native control repaints on every
        # SetStatusText, and this runs on the same coalesced refresh the cells
        # do -- which is every pause in typing and every pause in arrowing.
        if bar.GetStatusText(0) != text:
            bar.SetStatusText(text, 0)
    except Exception:  # noqa: BLE001 - a status bar is never worth a crash
        return None
    return bar


def show_native_status_bar(frame: Any, visible: bool) -> None:
    """Show or hide the native bar with the rest of the status bar.

    Hidden means the frame takes the row back, which is why the size event is
    sent: ``wxFrame`` only stops reserving space for a status bar it is told to
    re-measure. Never raises, for the reason above.
    """
    if frame is None:
        return
    try:
        bar = frame.GetStatusBar()
        if bar is None or bool(bar.IsShown()) == bool(visible):
            return
        bar.Show(bool(visible))
        frame.SendSizeEvent()
    except Exception:  # noqa: BLE001
        return
