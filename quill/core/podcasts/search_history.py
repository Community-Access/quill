"""The searches QUILL Cast has already run, so running one again is not retyping.

Quill Radio keeps them (:mod:`quill.core.radio.search_history`); Cast started
from nothing every time. The gap matters more here than the feature sounds,
because of *what* a podcast search is: somebody looking for the episode about
the harbour will run that search several times over a week, from a different
place in the library each time, and the query is the part they have to
reconstruct from memory on every attempt.

**One string, not three.** Radio's entry is a triple -- name, tag, country --
because Find Stations has three fields and they compose. Cast's Search
Everywhere has one box, over shows, episodes, notes and transcripts at once.
Modelling it as a triple to share Radio's module would have meant two empty
fields on every row and a label that reads "harbour, tagged , in " to a screen
reader. Same two rules, though, and they are the rules that make the list worth
opening at all:

* **Re-running a search moves it up rather than adding a second copy.** A list
  whose top five rows are the same query five times has spent its whole length
  on one search. De-duplication is case- and space-insensitive, because
  ``Harbour`` and ``harbour `` are one intention typed twice, and two rows that
  a screen reader reads identically are worse than useless.
* **An empty search is never remembered.** Clearing the box is how you start
  over, not somewhere to come back to.

**Privacy.** This is a list of what somebody has been searching for, kept on
their own machine beside the episodes they played. Nothing in this module
touches the network, and it rides ``podcast_history.json`` -- the file that
already holds the recently-played list -- so clearing that file clears this
too, rather than leaving a second history nobody knew about.

wx-free, strict-typed, no I/O.
"""

from __future__ import annotations

from collections.abc import Iterable

__all__ = ["MAX_RECENT_SEARCHES", "normalize", "remember", "from_json", "to_json"]

#: How many to keep. Long enough for "what was I looking for yesterday", short
#: enough that the whole dropdown can be arrowed through without becoming its
#: own navigation problem. The same number Radio keeps.
MAX_RECENT_SEARCHES = 15


def normalize(query: str) -> str:
    """What makes two searches "the same" for de-duplication."""
    return " ".join(str(query or "").split()).casefold()


def remember(
    entries: Iterable[str],
    query: str,
    *,
    limit: int = MAX_RECENT_SEARCHES,
) -> tuple[str, ...]:
    """*entries* with *query* at the front, de-duplicated and capped.

    Returns a new tuple rather than mutating, so the caller decides when the
    history is written. A search that found nothing is still a search somebody
    ran and typed, and is worth keeping -- often the *most* worth keeping,
    since it is the one they will try again with different words.
    """
    kept = [entry for entry in entries if entry.strip()]
    text = str(query or "").strip()
    if not text:
        return tuple(kept)[: max(0, limit)]
    key = normalize(text)
    kept = [entry for entry in kept if normalize(entry) != key]
    return tuple([text, *kept])[: max(0, limit)]


def to_json(entries: Iterable[str]) -> list[str]:
    """The stored form: plain strings, blanks dropped."""
    return [entry.strip() for entry in entries if entry and entry.strip()]


def from_json(raw: object, *, limit: int = MAX_RECENT_SEARCHES) -> tuple[str, ...]:
    """Read the stored form back, ignoring anything malformed.

    Forgiving in one direction only: a row that is not a string, or is blank,
    or repeats one already read, is dropped rather than raising. A history file
    damaged by a half-finished write should cost somebody their search history
    at worst, never their ability to open the app.
    """
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        text = item.strip()
        key = normalize(text)
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return tuple(out)
