"""Telling the listener a slow branch is still working, and the Find box's manners.

Two small behaviours that both answer the same question -- *is this thing
stuck, or just slow?* -- extracted from ``browse_tree_dialog`` under GATE-11
(extract, never rebaseline), host-taking functions like ``browse_find`` and
``browse_prefetch``.

**The slow-load notice.** A directory that is merely slow and one that has hung
feel identical until something says otherwise. A branch that takes longer than
:data:`SLOW_LOAD_SECONDS` says so out loud, once; the notice is cancelled the
moment children arrive, so a fast branch never says anything beyond its count.
Directories really do go down -- LibriVox spent 2026-08-16 timing out after
nineteen seconds -- and silence for that long reads as a broken app.

**Find's focus manners.** Tabbing into the Find box selects whatever is there,
so typing replaces the last search and one Backspace clears it, instead of
landing at the end of somebody else's words.

Which is also why the Find row is *one control*. It used to carry a Find
button and a Clear button, two tab stops sitting between the box and the tree
-- on the path a listener walks constantly -- to reach two things the keyboard
already does better: Enter searches, Escape clears the search and returns to
the folder. The row moved above the tree in the same pass, so Shift+Tab from
the stations lands on it and Tab comes straight back (2026-08-16).
"""

from __future__ import annotations

from typing import Any

#: How long a branch may load in silence before it says it is still going.
SLOW_LOAD_SECONDS = 3


def start_slow_load_notice(host: Any, label: str) -> None:
    """Arm the "still loading" notice for the branch named *label*."""
    wx = host._wx
    timer = getattr(host, "_slow_load_timer", None)
    if timer is None:
        timer = host._slow_load_timer = wx.Timer(host._win)
        host._win.Bind(wx.EVT_TIMER, lambda _e: _speak(host), timer)
    host._slow_load_label = label
    timer.StartOnce(SLOW_LOAD_SECONDS * 1000)


def stop_slow_load_notice(host: Any) -> None:
    """Children arrived (or failed): the branch is no longer in suspense."""
    timer = getattr(host, "_slow_load_timer", None)
    if timer is not None:
        timer.Stop()


def _speak(host: Any) -> None:
    label = getattr(host, "_slow_load_label", "")
    host._announce(f"Still loading {label}. This directory is being slow.")


def on_find_focus(host: Any, event: Any) -> None:
    """Tabbing into Find selects what is there.

    Deferred, because on Windows the control sets its own selection *after*
    this event -- doing it inline would be immediately undone.
    """
    event.Skip()
    host._wx.CallAfter(select_find_text, host)


def select_find_text(host: Any) -> None:
    control = getattr(host, "_find_ctrl", None)
    if control is not None and control:
        control.SelectAll()


def empty_row_text(*, unreachable: bool, override: str = "") -> str:
    """What the single row inside an empty folder should say (pure).

    A folder whose fetch returned nothing used to be left with NO children at
    all: the "Loading..." placeholder was deleted and nothing replaced it, so
    wx dropped the expander and the branch could neither be collapsed nor
    reopened -- and said nothing about why it was empty (reported 2026-08-16).
    One row fixes both: it keeps the folder navigable *and* answers the
    question, distinguishing "there is nothing here" from "this could not be
    reached, try again" -- the same distinction the browse contract makes
    everywhere else.

    *override* lets a branch say something better than the generic text;
    Favorites uses it to point at where stations come from.
    """
    if override:
        return override
    return "Could not be reached. Open it again to try." if unreachable else "Nothing in here."
