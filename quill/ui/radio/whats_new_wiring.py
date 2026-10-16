"""What's New, wired: one key that says what changed since you last looked.

Todo P3 "Radio extras" 8. The words and the sorting are wx-free in
:mod:`quill.core.radio.whats_new`; this is the command, its menu row and the
moment the summary is said. Alt+Shift+N (N for New), beside What Is On Now
(Ctrl+Alt+H): one asks what is broadcast, the other what arrived while you
were away.

Saying the summary marks those notices read in the notification centre, so a
second press says "Nothing new" instead of the same news; the entries stay in
the centre (Help > Notifications) for anybody who wants the detail.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

COMMAND = "radio.whats_new"


def register(app: Any) -> None:
    app.commands.try_register(
        COMMAND, "What's New", lambda: announce_whats_new(app), feature_id="core.radio"
    )


def append_menu_item(host: Any, menu: Any, wx: Any) -> Any:
    """Append the row, bound to *host*; the id is pinned here."""
    item_id = wx.NewIdRef()
    item = menu.Append(item_id, host._menu_label("What's Ne&w", COMMAND))
    item.SetHelp("Says what arrived since you last looked: new episodes, videos and reminders.")
    host.frame.Bind(wx.EVT_MENU, lambda _e: announce_whats_new(host), id=item_id)
    host._keep_menu_ids(item_id)
    return item_id


def announce_whats_new(host: Any, *, path: Any = None) -> str:
    """Say the summary, then mark what it covered as read. Returns what was said."""
    from quill.core.notifications import load_notifications, mark_read
    from quill.core.radio.whats_new import gather, summary

    try:
        news = gather(load_notifications(path=path))
    except Exception:  # noqa: BLE001 - an unreadable centre is a sentence, not a crash
        logger.debug("What's New could not read the notification centre", exc_info=True)
        said = "The notification list could not be read."
        host._announce(said)
        return said
    said = summary(news)
    host._announce(said)
    for notice_id in news.ids:
        try:
            mark_read(notice_id, path=path)
        except Exception:  # noqa: BLE001 - it was said; the mark is best-effort
            logger.debug("Could not mark a notice read", exc_info=True)
            break
    return said


__all__ = ["COMMAND", "announce_whats_new", "append_menu_item", "register"]
