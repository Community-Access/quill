"""Whether a play is reported to RadioBrowser's community count, and the doing of it.

Extracted from ``main_frame_radio`` (GATE-11) when the preference landed, and
the better home regardless: deciding whether to make a network request about
something the listener just played is domain logic with a consent question in
it, not a detail of the window that happens to own the player. Wx-free, so the
decision is testable without a frame.

The report itself is RadioBrowser's community click count -- the signal that
directory ranks stations by. Giving it is the default, because a directory
every listener takes from and nobody gives back to decays into a list of dead
streams. Not giving it is one checkbox, because it is still a request naming a
station, and "on unless you say otherwise" is only honest if saying otherwise
is possible.
"""

from __future__ import annotations

from typing import Protocol


class _SharePreference(Protocol):
    """The one field this module reads off the radio history/preferences."""

    share_play_counts: bool


def should_report_play(history: _SharePreference | None) -> bool:
    """True when the listener has not opted out of the community play count.

    Missing state answers *yes*, matching the stored default: an upgrade from a
    build that predates the preference must not read a silent absence as a
    refusal, and a caller that has no preferences object at all is not evidence
    of one either.
    """
    if history is None:
        return True
    return bool(getattr(history, "share_play_counts", True))


def report_play(
    station_uuid: str,
    *,
    history: _SharePreference | None,
    safe_mode: bool = False,
) -> None:
    """Report *station_uuid* as played, if the listener shares play counts.

    Best-effort and silent either way: a missed vote is never worth a message,
    let alone interrupting playback. ``register_click`` itself ignores an id
    that did not come from RadioBrowser, so a station from another directory
    reaches the network from here no matter what this preference says.
    """
    if not should_report_play(history):
        return
    from quill.core.radio import radio_browser

    try:
        radio_browser.register_click(station_uuid, safe_mode=safe_mode)
    except Exception:  # noqa: BLE001 - a missed click-vote must never surface
        return
