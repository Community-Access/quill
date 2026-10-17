"""Find a named text by the words in it, in any order.

The snippet picker, the Abbreviations manager and the Copy Tray search each
matched the search box as **one** piece of text: "meeting notes" found a
snippet called "Meeting notes for Tuesday" and missed "Notes from the
meeting", and "reply thanks" found nothing at all although one snippet is
named "Thanks" and replies. The command palette has matched the other way since
it shipped ("add url" finds "URL Add"); this is the same rule, shared, so the
lists that hold somebody's own text answer the way the palette does.

The rule: the whole search, as typed, anywhere in the row -- or else every word
of it somewhere in the row, in any order. Case is ignored. An empty search
matches everything. Callers still rank the exact and starts-with matches first;
this only decides what is *in* the list.
"""

from __future__ import annotations

from collections.abc import Iterable

__all__ = ["SearchTerms", "matches_search"]

_ROW_JOIN = "\n"


class SearchTerms:
    """A search prepared once, for asking of many rows (a keystroke's worth)."""

    __slots__ = ("needle", "words")

    def __init__(self, query: str) -> None:
        self.needle = " ".join(query.casefold().split())
        self.words = tuple(self.needle.split(" ")) if " " in self.needle else ()

    def found_in(self, folded: str) -> bool:
        """*folded* is the row's text, already case-folded."""
        if not self.needle or self.needle in folded:
            return True
        return bool(self.words) and all(word in folded for word in self.words)

    def found_in_fields(self, fields: Iterable[str]) -> bool:
        """The same question over separate fields, folded and joined here."""
        return self.found_in(_ROW_JOIN.join(str(field).casefold() for field in fields))


def matches_search(query: str, fields: Iterable[str]) -> bool:
    """True when *query* (whole, or word by word) is found across *fields*."""
    return SearchTerms(query).found_in_fields(fields)
