"""Why? for the things the GitHub Workbench does on its own (GitHub PRD D13, GH-R-108).

A result that follows a key press explains itself with Shift+F9. Some things
happen with no key at all: a Watch finds something on its round, GitHub puts
a notification in the inbox, a filter quietly covers only the rows already
loaded. Each of those gets a Why?, in a paragraph that says what happened,
what decided it, and what the person can change. Shift+F1 lists it first.

No ``wx``; strict-typed.
"""

from __future__ import annotations

from quill.core.github.watches import Watch, freshness

__all__ = ["why_filter", "why_notification", "why_watch"]

_LOOKS_FOR = {
    "run": "a workflow run finishing",
    "release": "a new release",
    "review": "a new review",
    "comment": "a new comment",
}


def why_watch(watch: Watch, minutes: int, now: float | None = None) -> str:
    """Why a watch said what it said, or why it has said nothing."""
    looks = _LOOKS_FOR.get(watch.kind, "something new")
    rule = f"This watch, {watch.describe()}, looks for {looks}."
    if watch.paused:
        return (
            f"{rule} It is paused, so it is not checked until you resume it. "
            "Pause or Resume Watch starts it again."
        )
    when = (
        f"It is checked every {minutes} minutes while this window is open, and was "
        f"{freshness(watch.last_checked, now)}."
    )
    if not watch.primed:
        found = "Its first check only learns what is there already, so it says nothing yet."
    elif watch.last_result:
        found = (
            f"It last spoke because its check found something it had not seen before: "
            f"{watch.last_result}"
        )
    else:
        found = "Nothing new has turned up since it started, so it has said nothing."
    return (
        f"{rule} {when} {found} It never marks a notification read. "
        "Edit Watch changes what it looks at."
    ).replace("..", ".")


def why_notification(detail: str, repository: str) -> str:
    """Why a notification is in the inbox, from its row's own "Why you got it" line."""
    reason = ""
    for line in detail.splitlines():
        if line.startswith("Why you got it:"):
            reason = line.removeprefix("Why you got it:").strip()
    if not reason:
        reason = "no reason given"
    where = f" on {repository}" if repository else ""
    return (
        f"GitHub sent you this because of this reason: {reason}. GitHub decides that from "
        f"how you watch{where} and what you take part in, not QUILL. Unsubscribe from "
        "Thread stops this one; the Watch level on the repository's sheet changes the rest."
    )


def why_filter(words: str, *, remote: bool, loaded: int, complete: bool) -> str:
    """Why a filter covers what it covers: all of GitHub, or only the rows loaded."""
    if not words:
        return ""
    if remote:
        return (
            f"Your filter, {words}, is sent to GitHub as a search, so it covers everything "
            "GitHub holds for this place, not only the rows loaded."
        )
    if complete:
        scope = f"All {loaded} rows are loaded, so nothing is missed."
    else:
        scope = (
            f"Only {loaded} rows are loaded, so a match among the rest is not found. "
            "Load More, Alt+PageDown, reads the next page."
        )
    return (
        f"Your filter, {words}, is applied here, to the rows already loaded, because "
        f"GitHub's list for this place has no search of its own. {scope}"
    )
