"""Whether a Workbench list is current, in words (FUX-13).

The Loading cell said "Up to date, 10:42" once a list had loaded, and nothing
changed it when a later Refresh failed: offline, or limited by the service, the
old rows stayed on screen under a cell that still called them up to date. That
is cached data presented as current, the one thing FUX-13 says never to do.

This module words the three answers the GitHub and WordPress Workbenches give,
from the frame's own facts (loading, the time of the last good load, whether the
last load failed, whether rows are still shown). No cache, timer or network
call is added. wx-free so the wording is tested without a window.
"""

from __future__ import annotations


def loading_cell(*, loading: bool, loaded_at: str, failed: bool) -> str:
    """The status bar's Loading cell."""
    if loading:
        return "Loading"
    if failed:
        if loaded_at:
            return f"Not up to date, from {loaded_at}; the refresh failed"
        return "Load failed"
    return f"Up to date, {loaded_at}" if loaded_at else ""


def loading_readout(*, loading: bool, loaded_at: str, failed: bool) -> str:
    """The Say Loading readout: the cell's facts as a sentence."""
    if loading:
        return "Loading"
    if failed:
        if loaded_at:
            return f"Not up to date: the list shown was loaded at {loaded_at}; the refresh failed"
        return "Nothing loaded: the load failed"
    return f"Up to date, loaded at {loaded_at}" if loaded_at else "Nothing loaded"


def failure_sentence(label: str, error: object, *, loaded_at: str, refresh_key: str) -> str:
    """What a failed load says, once: what failed, why, what is shown, what to do.

    *loaded_at* is the time of the rows still shown, or "" when none are.
    """
    reason = " ".join(str(error).split()).rstrip(".") or type(error).__name__
    parts = [f"Could not load {label}: {reason}."]
    if loaded_at:
        parts.append(f"The list shown is from {loaded_at}.")
    parts.append(f"Refresh ({refresh_key}) tries again." if refresh_key else "Refresh tries again.")
    return " ".join(parts)


def local_clock(iso_utc: str) -> str:
    """A stored UTC time ("2026-11-24T17:42:00Z") as this computer's "10:42", or ""."""
    from datetime import datetime

    try:
        moment = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return ""
    if moment.tzinfo is None:
        return ""
    return moment.astimezone().strftime("%H:%M")
