"""Beacon's Revalidate Health command.

Split out of :mod:`quill.apps.beacon.app` under GATE-11 (extract, never
rebaseline) when App Sounds joined Beacon's Tools menu on 2026-10-14.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.dialog_contract import show_message_box


def revalidate_health(frame: Any) -> None:
    """On-demand link-health revalidation (PRD 13.4, 17.4).

    Local files are checked against the filesystem; web links are checked
    over the network only if the requests library is installed, and only
    after the user confirms. Fail-safe: a missing library or a failed check
    never corrupts the library.
    """
    from quill.apps.beacon import health

    will_network = health._has_requests() if hasattr(health, "_has_requests") else True
    confirm = show_message_box(
        "Re-check link health now?\n\n"
        + (
            "Web links will be checked over the network. "
            if will_network
            else "Web links will be skipped (requests not installed); "
            "only local files will be checked. "
        )
        + "Broken links are marked so you can review or repair them.",
        "Revalidate Health",
        style=wx.ICON_QUESTION | wx.YES_NO,
    )
    if confirm != wx.YES:
        return
    fetcher = None
    if will_network:
        try:
            fetcher = health.default_fetcher
        except Exception:
            fetcher = None
    summary = health.revalidate(frame.store, fetcher=fetcher)
    frame._refresh_results()
    frame.announcer.say(
        f"Checked {summary['checked']}, "
        f"{summary['available']} available, {summary['broken']} broken, "
        f"{summary['skipped']} skipped"
    )
    show_message_box(
        f"Checked: {summary['checked']}\n"
        f"Available: {summary['available']}\n"
        f"Broken: {summary['broken']}\n"
        f"Skipped (no network check): {summary['skipped']}",
        "Revalidate Health",
        wx.OK,
    )
