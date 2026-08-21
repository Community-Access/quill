"""The searches you have already run, so running one again is not retyping it.

WHY THIS EXISTS
---------------
Find Stations remembered *which sources* it searched and *which Source facet*
you filtered by, on the stated principle that "a preference you have to re-set
on every search is not really a preference". It remembered nothing about the
searches themselves. So the listener who checks the same four stations every
morning -- or who is working through a genre one country at a time -- retyped
the query every time, and a typo meant starting again.

WHAT A "SEARCH" IS HERE
-----------------------
Not a string. Find Stations has three fields (name, tag/genre, country), and
they compose: *jazz* in *France* is a different search from *jazz* in *Brazil*,
and remembering only the word "jazz" would hand back the wrong one. So an entry
is the whole triple, and revisiting one restores all three fields together.

TWO RULES THAT KEEP THE LIST WORTH OPENING
------------------------------------------
* **Repeating a search moves it up rather than adding a second copy.** A list
  whose top five rows are the same query five times has spent its whole length
  on one search. De-duplication is case- and space-insensitive because "Jazz "
  and "jazz" are the same intention typed twice, and a listener arrowing a list
  cannot see the difference between rows that differ only in whitespace.
* **An empty search is never remembered.** Clearing the fields is how you start
  over, not something to come back to.

PRIVACY
-------
This is a list of what somebody has been searching for, kept on their own
machine in their own data folder alongside the stations they played. It is
never sent anywhere -- there is no network call in this module and nothing
reads it but the dialog -- and ``Clear Recent Searches`` empties it outright.
It rides ``radio_history.json``, which is the file that already holds the
recently-played list, so a listener clearing that file clears this too rather
than discovering a second history they did not know about.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

#: How many searches to keep. Long enough to cover "what was I looking at
#: yesterday", short enough that the whole list can be arrowed through without
#: it becoming its own navigation problem.
MAX_RECENT_SEARCHES = 15


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """One search as the listener actually expressed it: up to three fields."""

    name: str = ""
    tag: str = ""
    country: str = ""

    @property
    def is_empty(self) -> bool:
        """True when there is nothing here to search for, or to remember."""
        return not (self.name.strip() or self.tag.strip() or self.country.strip())

    def key(self) -> tuple[str, str, str]:
        """What makes two entries "the same search" for de-duplication.

        Case- and space-insensitive: somebody who typed ``Jazz`` yesterday and
        ``jazz `` today ran one search twice, and two rows that a screen reader
        reads identically are worse than useless -- they are indistinguishable.
        """
        return (
            self.name.strip().casefold(),
            self.tag.strip().casefold(),
            self.country.strip().casefold(),
        )

    def label(self) -> str:
        """The row as it should be *heard*: "jazz, tagged blues, in France".

        Every part names itself, because a bare list of values ("jazz, blues,
        France") leaves the listener to work out which field each one came
        from -- and "blues" is a plausible station name as well as a plausible
        tag. A search with no name leads with the field it does have rather
        than an empty gap.
        """
        parts: list[str] = []
        name = self.name.strip()
        tag = self.tag.strip()
        country = self.country.strip()
        if name:
            parts.append(name)
        if tag:
            parts.append(f"tagged {tag}" if name else f"Tagged {tag}")
        if country:
            parts.append(f"in {country}")
        return ", ".join(parts) if parts else "Empty search"


def remember(
    entries: Iterable[SearchQuery],
    query: SearchQuery,
    *,
    limit: int = MAX_RECENT_SEARCHES,
) -> tuple[SearchQuery, ...]:
    """*entries* with *query* at the front, de-duplicated and capped.

    Returns a new tuple rather than mutating, so the caller decides when the
    history is actually written -- a search that fails to reach the network is
    still a search the listener ran and typed, and is worth keeping.
    """
    if query.is_empty:
        return tuple(entries)[:limit]
    key = query.key()
    kept = [entry for entry in entries if entry.key() != key]
    return tuple([query, *kept])[: max(0, limit)]


def to_json(entries: Iterable[SearchQuery]) -> list[dict[str, str]]:
    """The stored form: a list of plain objects, one per search."""
    return [
        {"name": entry.name, "tag": entry.tag, "country": entry.country}
        for entry in entries
        if not entry.is_empty
    ]


def from_json(raw: object, *, limit: int = MAX_RECENT_SEARCHES) -> tuple[SearchQuery, ...]:
    """Read the stored form back, ignoring anything malformed.

    Deliberately forgiving in one direction only: a row that is not an object,
    or whose fields are not strings, is dropped rather than raising. A history
    file damaged by a half-finished write must cost the listener their search
    history at worst, never their ability to open Find Stations.
    """
    if not isinstance(raw, list):
        return ()
    out: list[SearchQuery] = []
    seen: set[tuple[str, str, str]] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        tag = item.get("tag")
        country = item.get("country")
        query = SearchQuery(
            name=name if isinstance(name, str) else "",
            tag=tag if isinstance(tag, str) else "",
            country=country if isinstance(country, str) else "",
        )
        if query.is_empty or query.key() in seen:
            continue
        seen.add(query.key())
        out.append(query)
        if len(out) >= limit:
            break
    return tuple(out)
