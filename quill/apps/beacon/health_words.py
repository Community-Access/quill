"""A bookmark's health and sync state, in words (FUX-13).

Beacon's Health column and the Details field showed the stored code itself:
"availableOffline", "onlineOnly", "temporarilyUnavailable", read letter-run by a
screen reader and meaning nothing to anyone who has not read the PRD. The model
says health is "conveyed as text, never color alone" (PRD 9.2); this is that
text. The column gets a short state; Details gets the state, why where it is
known, and what can be done, by the menu's label and key.

A bookmark edited since the last sync was also never said to be only on this
computer, although the library keeps that fact (``dirty``). Details says so.

The stored codes are unchanged, so the search syntax ``health:broken`` and
every synced library keep working. wx-free so it is tested without a window.
"""

from __future__ import annotations

from quill.apps.beacon import model

#: Revalidate Health's label and key, as the Tools menu shows them.
_RECHECK = "Revalidate Health (Ctrl+Alt+H) checks it again."

#: The Health column: the state, short.
COLUMN: dict[str, str] = {
    model.HEALTH_AVAILABLE: "Available",
    model.HEALTH_OFFLINE: "Available offline",
    model.HEALTH_ONLINE_ONLY: "Online only",
    model.HEALTH_MOVED: "Moved",
    model.HEALTH_CHANGED: "Changed",
    model.HEALTH_PARTIAL: "Partly matched",
    model.HEALTH_AUTH: "Needs sign-in",
    model.HEALTH_UNAVAILABLE: "Unavailable for now",
    model.HEALTH_BROKEN: "Broken link",
    model.HEALTH_UNSUPPORTED: "Not supported",
    model.HEALTH_REMOVED: "Removed by its provider",
    model.HEALTH_ARCHIVED: "Archived",
    model.HEALTH_DELETED: "Deleted",
}

#: Details: what the state means for opening it, and what to do.
_DETAIL: dict[str, str] = {
    model.HEALTH_OFFLINE: "It opens without the internet.",
    model.HEALTH_ONLINE_ONLY: "It needs the internet to open.",
    model.HEALTH_MOVED: "Its address has changed since you saved it.",
    model.HEALTH_CHANGED: "What it points to has changed since you saved it.",
    model.HEALTH_PARTIAL: "Only part of the saved place could be found.",
    model.HEALTH_AUTH: "Sign in to the site, then open it again.",
    model.HEALTH_UNAVAILABLE: f"It could not be reached last time. {_RECHECK}",
    model.HEALTH_BROKEN: f"It could not be found last time. {_RECHECK}",
    model.HEALTH_UNSUPPORTED: "Beacon cannot open this kind of place.",
    model.HEALTH_REMOVED: "Its provider no longer offers it.",
}


def column(code: str) -> str:
    """The Health column's words for *code*; an unknown code is shown as it is."""
    return COLUMN.get(code, code)


def detail(code: str) -> str:
    """The Details line: "Health: Broken link. It could not be found ..."."""
    sentence = _DETAIL.get(code, "")
    return f"Health: {column(code)}." + (f" {sentence}" if sentence else "")


def sync_detail(dirty: bool, sync_configured: bool) -> str:
    """Whether this bookmark's latest change is synced, or "" when sync is off."""
    if not sync_configured:
        return ""
    if dirty:
        return "Sync: changed on this computer, not synced yet."
    return "Sync: synced."


def detail_lines(code: str, dirty: bool, sync_configured: bool) -> list[str]:
    """The Health and optional sync lines for a bookmark's Details field."""
    lines = [detail(code)]
    synced = sync_detail(dirty, sync_configured)
    if synced:
        lines.append(synced)
    return lines
