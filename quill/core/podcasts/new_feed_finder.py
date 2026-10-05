"""Find This Show's New Feed: where a podcast went when its feed stopped working.

A feed that the host has removed, a domain that has lapsed, an address that now
returns a web page: Cast could say all of that, and then had nothing to offer.
In the 2026-10-04 Downcast import test a search by title found a verified new
feed for 27 of 115 dead feeds -- Living Blindfully among them -- by hand
(check.md bug 8). This is that search, built into Feed Check.

Three steps, and each one is the code Cast already uses for the same job:

1. **Search the directories by the show's title** -- Add Podcast's own
   :func:`directory_search.search` (Apple Podcasts and Podcast Index), so no
   new place is contacted and the request is the same one a listener's own
   search makes. It runs only when somebody presses the button, like that
   search does.
2. **Verify each candidate** by reading its feed with the feed reader -- a
   candidate that does not answer, or answers with no episodes, is not offered.
   Each one that is offered says how many episodes it has and the date of the
   newest, which is what tells a revived show from a dead one with the same
   name.
3. **Replace Feed keeps the show's history.** Only the address changes: every
   episode, what has been played, positions, notes and settings stay. The next
   read of the new address is a starting point, so its back catalogue does not
   arrive as hundreds of "new" episodes, and episodes it shares with the old
   feed by title are not listed twice.

wx-free, strict-typed. Network only through the directory clients and the feed
reader, each an existing reviewed egress site.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from quill.core.podcasts import check_state
from quill.core.podcasts.itunes_search import PodcastSearchResult
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.opml_import import normalize_feed_url
from quill.core.podcasts.subscriptions import PodcastLibrary

__all__ = [
    "MAX_VERIFIED",
    "Candidate",
    "FindResult",
    "find_new_feed",
    "replace_feed",
]

#: How many directory results are read to verify them. Each is one feed
#: fetch, so this bounds the cost of one press; the right show is nearly
#: always among the first few results for its own title.
MAX_VERIFIED = 6


@dataclass(frozen=True, slots=True)
class Candidate:
    """A directory result whose feed answered with episodes."""

    title: str
    feed_url: str
    artist: str = ""
    episodes: int = 0
    newest: datetime | None = None
    #: The directory's title matches the show's own, ignoring case.
    same_title: bool = False
    #: How close the title is: 0 the same, 1 one contains the other (ignoring
    #: case and a leading "The"), 2 neither. Lower sorts first.
    closeness: int = 2

    def describe(self) -> str:
        """One row, said the way somebody would say it."""
        from quill.core.counted import plural

        parts = [self.title]
        if self.artist:
            parts.append(f"by {self.artist}")
        parts.append(plural(self.episodes, "episode"))
        if self.newest is not None:
            parts.append(f"newest {self.newest.strftime('%d %B %Y').lstrip('0')}")
        host = self.feed_url.split("//", 1)[-1].split("/", 1)[0]
        parts.append(f"at {host}")
        return ", ".join(parts)


@dataclass(slots=True)
class FindResult:
    """What one search found, and a sentence that says so."""

    candidates: list[Candidate]
    #: Directory problems ("iTunes did not answer"), already phrased.
    problems: list[str]
    #: Results that were read and did not hold up (no answer, no episodes).
    rejected: int = 0

    def summary(self, title: str) -> str:
        from quill.core.counted import plural

        if self.candidates:
            said = f"Found {plural(len(self.candidates), 'possible new feed')} for {title}."
        else:
            said = f"No working feed for {title} was found in the podcast directories."
        if self.problems:
            said += " " + " ".join(self.problems)
        return said


Searcher = Callable[[str], tuple[list[PodcastSearchResult], list[str]]]
Verifier = Callable[[str], tuple[int, datetime | None]]


def _default_searcher(safe_mode: bool, source: str, key: str, secret: str) -> Searcher:
    def search(query: str) -> tuple[list[PodcastSearchResult], list[str]]:
        from quill.core.podcasts import directory_search

        found = directory_search.search(
            query, source=source, key=key, secret=secret, safe_mode=safe_mode, limit=15
        )
        return found.results, found.problems

    return search


def _default_verifier(safe_mode: bool) -> Verifier:
    def verify(feed_url: str) -> tuple[int, datetime | None]:
        from quill.core.podcasts import feed_reader
        from quill.core.podcasts.row_speech import _parse  # noqa: PLC2701 - one parser

        info = feed_reader.fetch_and_parse_feed(feed_url, safe_mode=safe_mode)
        dates = [moment for moment in (_parse(e.published) for e in info.episodes) if moment]
        return len(info.episodes), (max(dates) if dates else None)

    return verify


def find_new_feed(
    show: PodcastShow,
    *,
    safe_mode: bool = False,
    source: str = "both",
    key: str = "",
    secret: str = "",
    searcher: Searcher | None = None,
    verifier: Verifier | None = None,
) -> FindResult:
    """Search the directories for *show*'s title and verify what comes back.

    Never raises for a network problem: a directory that does not answer is a
    sentence in ``problems``, and a candidate whose feed fails is left out.
    Candidates come back with the show's own title first, then newest first.
    """
    title = (show.title or "").strip()
    if not title:
        return FindResult([], ["This podcast has no title to search for."])
    search = searcher or _default_searcher(safe_mode, source, key, secret)
    verify = verifier or _default_verifier(safe_mode)
    try:
        results, problems = search(title)
    except Exception as error:  # noqa: BLE001 - a failed search is a sentence
        from quill.core.podcasts.feed_problems import plain

        return FindResult([], [f"The podcast directories did not answer. {plain(error)}"])
    current = normalize_feed_url(show.feed_url)
    seen: set[str] = {current}
    candidates: list[Candidate] = []
    rejected = 0
    for result in results:
        key_url = normalize_feed_url(result.feed_url)
        if not result.feed_url or key_url in seen:
            continue
        seen.add(key_url)
        if len(seen) - 1 > MAX_VERIFIED:
            break
        try:
            episodes, newest = verify(result.feed_url)
        except Exception:  # noqa: BLE001 - a candidate that fails is simply not offered
            rejected += 1
            continue
        if episodes <= 0:
            rejected += 1
            continue
        candidates.append(
            Candidate(
                title=result.title,
                feed_url=result.feed_url,
                artist=result.artist,
                episodes=episodes,
                newest=newest,
                same_title=result.title.strip().casefold() == title.casefold(),
                closeness=_closeness(result.title, title),
            )
        )
    # The show's own name first, then a name that contains it ("The Field of
    # Vision" now listed as "Field of Vision"), then the rest; newest first
    # within each. A directory's own order put an unrelated show with a
    # newer episode above the right one in the 2026-10-04 test.
    candidates.sort(
        key=lambda c: (
            c.closeness,
            -(c.newest.timestamp() if c.newest is not None else 0.0),
        )
    )
    return FindResult(candidates, list(problems), rejected)


def _plain_title(text: str) -> str:
    folded = " ".join(text.casefold().split())
    return folded[4:] if folded.startswith("the ") else folded


def _closeness(found: str, wanted: str) -> int:
    a, b = _plain_title(found), _plain_title(wanted)
    if a == b:
        return 0
    if a and b and (a in b or b in a):
        return 1
    return 2


def replace_feed(library: PodcastLibrary, show: PodcastShow, new_url: str) -> None:
    """Point *show* at *new_url*, keeping everything else it has.

    Episodes, play state, positions, notes and settings are untouched; only the
    address changes. The bookkeeping that described the *old* address -- its
    failure run, its validators, "empty" -- is cleared, and the next read is
    marked as a starting point (:func:`check_state.mark_rebase`), because a new
    host's feed arrives with its own episode ids and must not be announced as a
    flood of new episodes.
    """
    show.feed_url = new_url.strip()
    check_state.mark_rebase(library, show)
