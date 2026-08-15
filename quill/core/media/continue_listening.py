"""Everything you started and did not finish, in one list.

QUILL remembers your place in four different things and never showed you the
four together: a podcast episode's ``position_ms``, a LibriVox chapter or an
Internet Archive recording in Quill Radio's own resume store, and a local file
in the media position store. Each one works. None of them could answer the
question people actually have, which is *"what was I in the middle of?"*

So: one list, newest first, **with the provider named on every row.** The naming
is not decoration -- "The Moonstone, chapter 4" means something quite different
depending on whether pressing Enter starts a podcast, a stream, or a file, and a
list that hides which is a list you have to try things in to understand.

Three decisions:

* **Each source is asked separately and may fail alone.** A podcast library that
  will not load must not cost you the LibriVox chapter you were halfway through.
  Every gatherer is wrapped, and a source that raises contributes nothing.
* **Only things that can actually be resumed.** Radio's store keys on a
  normalised stream identity that deliberately cannot be turned back into an
  address, so entries saved before it also kept the URL are skipped rather than
  offered and then failing. An offer that cannot be honoured is worse than an
  absence.
* **Newest first, and that is the only order.** Not "most nearly finished", not
  grouped by provider: the question is *what was I doing*, and the answer to
  that is chronological.

wx-free, strict-typed. Nothing here reads a file it was not handed a store for.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

#: How each provider is named on a row. Full words: this is spoken.
PROVIDER_LABELS: dict[str, str] = {
    "podcast": "podcast",
    "radio": "recording",
    "file": "file on this computer",
}

#: A position under this is the beginning, and offering to go back to it is a
#: row somebody has to skip past for no gain. Matches both stores' own floors.
MIN_RESUME_MS = 30_000

#: Past this fraction it is finished in every way that matters, and a
#: "continue" row for the closing credits is noise.
FINISHED_FRACTION = 0.98


@dataclass(frozen=True, slots=True)
class Unfinished:
    """One thing you were in the middle of, and how to get back to it."""

    title: str
    provider: str  # one of PROVIDER_LABELS
    position_ms: int
    duration_ms: int = 0
    #: Sort key: seconds since the epoch. Every store records *when* in its own
    #: way, so they are normalised here rather than at three call sites.
    saved_at: float = 0.0
    #: What the caller needs to resume it, in that provider's own terms:
    #: ``(show_id, episode_guid)`` for a podcast, a URL for a recording, a path
    #: for a file. Opaque here on purpose -- this module plays nothing.
    key: Any = None
    #: Where it came from, said in one phrase: "The Rest Is History".
    source_label: str = ""

    @property
    def fraction(self) -> float:
        return (self.position_ms / self.duration_ms) if self.duration_ms > 0 else 0.0

    @property
    def is_finished(self) -> bool:
        return self.duration_ms > 0 and self.fraction >= FINISHED_FRACTION

    def row_label(self) -> str:
        """The whole row as one sentence, provider named.

        Position in words, never a timecode: "12:08" spoken aloud is an
        ambiguous pair of numbers, which is why nothing in QUILL says one.
        """
        parts = [self.title or "Untitled"]
        if self.source_label and self.source_label != self.title:
            parts.append(self.source_label)
        parts.append(PROVIDER_LABELS.get(self.provider, self.provider))
        parts.append(f"{spoken_position(self.position_ms)} in")
        if self.duration_ms > 0:
            parts.append(f"{round(self.fraction * 100)}% through")
        return ", ".join(parts)


def spoken_position(position_ms: int) -> str:
    """A position as words. Shared shape with the other spoken helpers."""
    seconds = max(0, position_ms // 1000)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour{'' if hours == 1 else 's'}")
    if minutes:
        parts.append(f"{minutes} minute{'' if minutes == 1 else 's'}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'' if seconds == 1 else 's'}")
    return " ".join(parts)


def _epoch(value: str) -> float:
    """An ISO timestamp as seconds since the epoch, or 0.0 when unreadable."""
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except (TypeError, ValueError):
        return 0.0


def from_podcast_library(library: Any) -> list[Unfinished]:
    """Episodes with a saved position that are not marked played."""
    rows: list[Unfinished] = []
    for show in getattr(library, "shows", []) or []:
        for episode in getattr(show, "episodes", []) or []:
            position = int(getattr(episode, "position_ms", 0) or 0)
            if position < MIN_RESUME_MS or getattr(episode, "played", False):
                continue
            duration = int(getattr(episode, "duration_seconds", 0) or 0) * 1000
            rows.append(
                Unfinished(
                    title=str(getattr(episode, "title", "")),
                    provider="podcast",
                    position_ms=position,
                    duration_ms=duration,
                    # Episodes carry a published date, not a "when you listened"
                    # stamp, so the feed's date is the honest sort key here.
                    saved_at=_epoch(getattr(episode, "published", "")),
                    key=(getattr(show, "id", ""), getattr(episode, "guid", "")),
                    source_label=str(getattr(show, "title", "")),
                )
            )
    return rows


def from_resume_store(store: Any) -> list[Unfinished]:
    """Streamed recordings Quill Radio remembers a place in."""
    rows: list[Unfinished] = []
    for point in store.unfinished():
        rows.append(
            Unfinished(
                title=str(getattr(point, "label", "")) or "A recording",
                provider="radio",
                position_ms=int(getattr(point, "position_ms", 0)),
                duration_ms=int(getattr(point, "duration_ms", 0)),
                saved_at=float(getattr(point, "saved_at", 0.0)),
                key=str(getattr(point, "url", "")),
            )
        )
    return rows


def from_position_store(store: Any, data_dir: Any) -> list[Unfinished]:
    """Local files with a saved place -- books and recordings on this machine.

    The position store keys on the file's *contents*, so it deliberately holds
    no path; the local-only sidecar (``core/media/local_paths``) says where each
    one was last seen. A file whose hint has gone stale is **skipped**, not
    listed: the position is still perfectly good and will be found again next
    time the file is played, but offering a row that cannot open is worse than a
    shorter list.
    """
    from quill.core.media import local_paths
    from quill.core.media.positions import ListeningPosition

    rows: list[Unfinished] = []
    for entity_id in store.entity_ids():
        record = store.get_record(entity_id)
        position = ListeningPosition.from_dict(record) if record else None
        if position is None or position.position_ms < MIN_RESUME_MS:
            continue
        path = local_paths.path_for(data_dir, entity_id)
        if path is None:
            continue
        rows.append(
            Unfinished(
                title=position.label or path.name,
                provider="file",
                position_ms=position.position_ms,
                duration_ms=position.duration_ms,
                saved_at=_epoch(position.updated_at),
                key=str(path),
                source_label=path.parent.name,
            )
        )
    return rows


def gather(sources: list[Callable[[], list[Unfinished]]], *, limit: int = 50) -> list[Unfinished]:
    """Every source, merged, newest first, finished things dropped.

    A source that raises contributes nothing and costs the others nothing: a
    podcast library that will not load must not take the LibriVox chapter with
    it.
    """
    rows: list[Unfinished] = []
    for source in sources:
        try:
            rows.extend(source() or [])
        except Exception:  # noqa: BLE001 - one bad source is not a failed list
            continue
    rows = [row for row in rows if row.position_ms >= MIN_RESUME_MS and not row.is_finished]
    rows.sort(key=lambda row: row.saved_at, reverse=True)
    return rows[: max(1, limit)] if limit else rows


def summarise(rows: list[Unfinished]) -> str:
    """One sentence: how many, and across what.

    Counts the providers rather than only the rows, because the whole point of
    the list is that it spans them -- "6 things, across podcasts and recordings"
    says something a bare 6 does not.
    """
    if not rows:
        return "Nothing unfinished. Everything you started, you finished."
    kinds = list(dict.fromkeys(row.provider for row in rows))
    named = ", ".join(PROVIDER_LABELS.get(kind, kind) + "s" for kind in kinds)
    count = len(rows)
    return f"{count} thing{'' if count == 1 else 's'} you did not finish, across {named}."
