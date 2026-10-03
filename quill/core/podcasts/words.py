"""The words QUILL Cast uses, and the ones it does not (qc.md section 12).

Follow, unfollow, following. Podcast, never show or feed or subscription
(except "OPML subscription list", the format's own name). Episode. Unheard,
never unplayed. Place. Now Playing. Find, never search. Personal Audio. Inbox.
Queue. Downloaded, never cached. Settings for This Podcast; Preferences.

Pure. :func:`offences` is what the gate (``quill/tools/cast_words_audit.py``)
asks of every user-facing string literal in the Cast UI, and what a test can
ask of a sentence. A word is forbidden as a *whole word*, case-insensitive,
and a handful of fixed phrases that carry the format's own name are let
through; everything else the gate finds is either rewritten or classified in
the reviewed allowlist, with the reason beside it.
"""

from __future__ import annotations

import re

__all__ = ["ALLOWED_PHRASES", "FORBIDDEN", "offences", "scrub_allowed"]

#: Forbidden word -> the word to use instead (the message the gate prints).
FORBIDDEN: dict[str, str] = {
    "unsubscribe": "unfollow",
    "unsubscribed": "unfollowed",
    "unsubscribing": "unfollowing",
    "subscribe": "follow",
    "subscribed": "followed",
    "subscribing": "following",
    "subscription": "podcast (or 'the podcasts you follow')",
    "subscriptions": "podcasts (or 'the podcasts you follow')",
    "unplayed": "unheard",
    "cached": "downloaded",
    "search": "find",
    "searches": "finds",
    "searching": "finding",
}

#: Phrases that carry a format's or a product's own name, and are allowed.
ALLOWED_PHRASES: tuple[str, ...] = (
    "OPML subscription list",
    "subscription list",
    "Search Everywhere",
    "Podcast Index",
    "search engine",
    "Spotify",
)

_WORD = re.compile(r"[A-Za-z']+")


def scrub_allowed(text: str) -> str:
    """*text* with every allowed phrase blanked, so its words are not counted."""
    scrubbed = text
    for phrase in ALLOWED_PHRASES:
        scrubbed = re.sub(re.escape(phrase), " ", scrubbed, flags=re.IGNORECASE)
    return scrubbed


def offences(text: str) -> list[str]:
    """Every forbidden word in *text*, as it appears, in order, once each."""
    found: list[str] = []
    seen: set[str] = set()
    for match in _WORD.finditer(scrub_allowed(text)):
        word = match.group(0)
        key = word.lower().strip("'")
        if key in FORBIDDEN and key not in seen:
            seen.add(key)
            found.append(word)
    return found
