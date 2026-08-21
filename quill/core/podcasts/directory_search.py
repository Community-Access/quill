"""One search, whichever directories the listener chose.

Add Podcast used to have one directory and therefore no decision to make. With
two, something has to hold the question "which of these do I ask, and what do I
say when one of them fails" -- and that something must not be the dialog, or the
answer differs the next time somebody adds a search surface.

**A directory that fails does not fail the search.** Asking both and getting one
answer is a result, not an error: the listener wanted podcasts, and they have
some. What the other one said is carried alongside as a sentence, so the status
line can be honest -- "12 results from iTunes. Podcast Index did not answer." --
rather than either hiding the failure or throwing away the results.

**Credentials are the caller's business.** This module is handed a key and a
secret, or empty strings; it never reads the credential store, so it stays pure
enough to test without one.

wx-free, strict-typed. Every request goes through the two directory clients and
their own reviewed egress sites.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.podcasts.itunes_search import PodcastSearchResult

__all__ = ["SOURCE_LABELS", "SOURCES", "DirectorySearch", "search"]

#: The three answers to "which directory". ``itunes`` needs nothing;
#: ``podcast_index`` needs a key; ``both`` asks whichever can answer.
SOURCES: tuple[str, ...] = ("itunes", "podcast_index", "both")

SOURCE_LABELS: tuple[tuple[str, str], ...] = (
    ("itunes", "iTunes (no key needed)"),
    ("podcast_index", "Podcast Index (needs a key)"),
    ("both", "Both directories"),
)


@dataclass(slots=True)
class DirectorySearch:
    """What the search found, and what it could not."""

    results: list[PodcastSearchResult] = field(default_factory=list)
    #: One sentence per directory that could not answer, already phrased.
    problems: list[str] = field(default_factory=list)
    #: How many came from each, before de-duplication -- for the status line.
    counts: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        """The status line: what was found, from where, and what went wrong.

        Names the directories when there is more than one, because "12
        results" from an unknown source is the sentence that makes somebody
        wonder whether the other one was even asked.
        """
        total = len(self.results)
        if not total and self.problems:
            return " ".join(self.problems)
        if not total:
            return "No podcasts matched that."
        parts = [
            f"{count} from {label}"
            for label, count in (
                ("iTunes", self.counts.get("itunes", 0)),
                ("Podcast Index", self.counts.get("podcast_index", 0)),
            )
            if count
        ]
        said = f"{total} result{'' if total == 1 else 's'}"
        if len(parts) > 1:
            said += f": {', '.join(parts)}"
        said += "."
        if self.problems:
            said += " " + " ".join(self.problems)
        return said


def search(
    query: str,
    *,
    source: str = "itunes",
    key: str = "",
    secret: str = "",
    safe_mode: bool = False,
    limit: int = 25,
) -> DirectorySearch:
    """Ask the chosen directories and merge what comes back. Never raises.

    An unknown *source* reads as iTunes, for the same reason an unknown effort
    reads as Thorough: a settings file with a typo in it should behave like one
    with nothing in it.
    """
    from quill.core.podcasts import itunes_search, podcast_index

    wanted = source if source in SOURCES else "itunes"
    found = DirectorySearch()

    if wanted in ("itunes", "both"):
        try:
            rows = itunes_search.search_podcasts(query, limit=limit, safe_mode=safe_mode)
            found.results.extend(rows)
            found.counts["itunes"] = len(rows)
        except Exception as error:  # noqa: BLE001 - one directory failing is not the search failing
            found.problems.append(f"iTunes did not answer: {error}")

    if wanted in ("podcast_index", "both"):
        try:
            rows = podcast_index.search_podcasts(
                query, key=key, secret=secret, limit=limit, safe_mode=safe_mode
            )
            found.counts["podcast_index"] = len(rows)
            found.results = podcast_index.merge_results(found.results, rows)
        except Exception as error:  # noqa: BLE001
            found.problems.append(f"Podcast Index did not answer: {error}")

    return found
