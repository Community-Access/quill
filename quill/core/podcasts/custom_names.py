"""Names a listener gives podcasts and episodes, kept through every refresh (ear.md R8).

A rename used to overwrite the feed's title: a podcast's could never be put
back, and an episode's was undone by the next refresh. Now the feed's own name
is kept in ``feed_title`` beside the listener's, the refresh updates only that,
and renaming to nothing (or to the feed's own name) puts the feed's name back.
wx-free, strict-typed.
"""

from __future__ import annotations

from typing import Any

__all__ = ["rename"]


def rename(item: Any, typed: str) -> str:
    """Apply *typed* as *item*'s name; return what to say ("" = no change)."""
    name = (typed or "").strip()
    feed = str(getattr(item, "feed_title", "") or "") or str(item.title)
    if not name or name == feed:
        if not getattr(item, "feed_title", ""):
            return ""
        item.title = feed
        item.feed_title = ""
        return f"Back to the feed's own name, {feed}."
    if name == item.title:
        return ""
    if not item.feed_title:
        item.feed_title = item.title
    item.title = name
    return f"Renamed to {name}. The feed's own name, {feed}, is kept; a refresh will not undo this."
