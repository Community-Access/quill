"""Cast's library search index: one box, the whole library, bounded work (F-09).

Find in library (qc.md 4.2, P10) searches podcasts, episode titles, your own
notes, show notes and downloaded transcripts from one box. Done the obvious
way -- walk every show and fold every title on every pause in typing -- that is
a full-library scan per keystroke, on the thread the screen reader is waiting
on, and it grows with the library. QC2 6.3 names the cure: *search must be an
index, not a scan disguised as a feature.* This module is the index.

How it stays bounded:

* **Per show, not per library.** Each podcast keeps one record: its folded
  title, and its episode titles (and show notes) folded once and joined into a
  single string with an offset table. A query is one ``str.find`` per show --
  C speed -- and a bisect to turn a position back into an episode, so the cost
  of a search is the number of shows plus the number of *matches*, never a
  Python loop over every episode.
* **Incremental.** :meth:`LibrarySearchIndex.sync` compares a cheap per-show
  fingerprint (title, episode count, first and last episode) and rebuilds only
  the shows that changed; :meth:`~LibrarySearchIndex.invalidate` marks one show
  stale when the caller knows better (a feed refresh rewrote its episodes'
  text). The second search after a refresh of one podcast rebuilds one record.
* **Capped.** At most ``cap`` hits are kept (newest first within each kind,
  through a bounded heap), while ``total`` still counts every match, so the
  sentence says "1,204 matches" and the tree shows 200. Show notes are folded
  up to :data:`NOTES_CHARS_PER_EPISODE` each and :data:`NOTES_TOTAL_CHARS` in
  all; what the cap turned away is counted in :meth:`stats`.
* **Cancellable and immutable.** Every loop checks a cancel test, and the
  answer is a frozen :class:`SearchOutcome` of :class:`SearchHit` values -- ids
  and strings, never live model objects -- so the UI can drop a stale one.

Ranked as the plan ranks them: podcasts, then episode titles, then your notes,
then show notes, then transcript text; an episode is listed once, at its best
rank. Episode Filters given the "search" scope still hide what they hide.

wx-free and strict-typed; the UI half is ``quill/ui/podcasts/library_find.py``.
"""

from __future__ import annotations

import heapq
import html
import re
import threading
from array import array
from bisect import bisect_right
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any

from quill.stability.task_manager import CancelledError

__all__ = [
    "KIND_EPISODE",
    "KIND_NOTE",
    "KIND_SHOW",
    "KIND_SHOW_NOTES",
    "KIND_TRANSCRIPT",
    "NOTES_CHARS_PER_EPISODE",
    "NOTES_TOTAL_CHARS",
    "RESULT_CAP",
    "LibrarySearchIndex",
    "SearchHit",
    "SearchOutcome",
    "find_everything",
    "fold_query",
]

KIND_SHOW = "show"
KIND_EPISODE = "episode"
KIND_NOTE = "note"
KIND_SHOW_NOTES = "show_notes"
KIND_TRANSCRIPT = "transcript"

#: Hits kept per search. The tree's own cap for an opened view.
RESULT_CAP = 200

#: Show-notes characters folded per episode: the summary paragraph, which is
#: where a guest's name or a topic is, without the sponsor reads and link lists.
NOTES_CHARS_PER_EPISODE = 1_000

#: Show-notes characters folded in all, across the whole library.
NOTES_TOTAL_CHARS = 24_000_000

_TAG_RE = re.compile(r"<[^>]*>")

#: How many shows or notes between two looks at the cancel test.
_CANCEL_STRIDE = 64


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One match, as values: what it is, where it lives, why it matched."""

    kind: str
    show_id: str
    show_title: str
    episode_guid: str = ""
    episode_title: str = ""
    published: str = ""
    #: The note's first line, or a window of transcript around the hit.
    snippet: str = ""


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    """One finished search: the capped hits and the uncapped count."""

    query: str
    hits: tuple[SearchHit, ...]
    total: int
    generation: int = 0


def fold_query(query: str) -> str:
    """The query as the index compares it: trimmed, case-folded, one line."""
    return query.strip().replace("\n", " ").casefold()


def _fold_title(title: str) -> str:
    return (title or "").replace("\n", " ").casefold()


def _notes_text(description: str, cap: int) -> str:
    """Show notes as folded plain text, cut at *cap* characters.

    A regex rather than the HTML parser ``show_notes`` uses for reading: this
    runs once per episode across a whole library, and the index needs words,
    not paragraphs or link addresses.
    """
    if not description or cap <= 0:
        return ""
    text = description[: cap * 4]
    if "<" in text:
        text = _TAG_RE.sub(" ", text)
    if "&" in text:
        text = html.unescape(text)
    return " ".join(text.split())[:cap].replace("\n", " ").casefold()


def _joined(parts: Sequence[str]) -> tuple[str, array[int]]:
    starts: array[int] = array("q")
    position = 0
    for part in parts:
        starts.append(position)
        position += len(part) + 1
    return "\n".join(parts), starts


def _matching_positions(hay: str, starts: array[int], needle: str) -> Iterator[int]:
    """Indices of the parts of *hay* containing *needle*, each once, in order."""
    if not hay:
        return
    find = hay.find
    count = len(starts)
    position = find(needle)
    while position >= 0:
        index = bisect_right(starts, position) - 1
        yield index
        if index + 1 >= count:
            return
        position = find(needle, starts[index + 1])


def _part(hay: str, starts: array[int], index: int) -> str:
    end = starts[index + 1] - 1 if index + 1 < len(starts) else len(hay)
    return hay[starts[index] : end]


class _ShowRecord:
    """One podcast, folded. Holds references to the model, never copies of it."""

    __slots__ = (
        "episodes",
        "fingerprint",
        "notes_chars",
        "notes_hay",
        "notes_starts",
        "positions",
        "show",
        "title_folded",
        "title_hay",
        "title_starts",
    )

    def __init__(self, show: Any, episodes: tuple[Any, ...], fingerprint: tuple[Any, ...]) -> None:
        self.show = show
        self.episodes = episodes
        self.fingerprint = fingerprint
        self.title_folded = _fold_title(str(show.title or ""))
        self.title_hay, self.title_starts = _joined([_fold_title(e.title) for e in episodes])
        self.notes_hay = ""
        self.notes_starts: array[int] = array("q")
        self.notes_chars = 0
        self.positions: dict[str, int] | None = None

    def position_of(self, guid: str) -> int:
        """The episode's index in this record, or -1; built only when asked."""
        if self.positions is None:
            self.positions = {episode.guid: index for index, episode in enumerate(self.episodes)}
        return self.positions.get(guid, -1)

    def title_matches(self, index: int, needle: str) -> bool:
        return needle in _part(self.title_hay, self.title_starts, index)

    def notes_match(self, index: int, needle: str) -> bool:
        if not self.notes_hay:
            return False
        return needle in _part(self.notes_hay, self.notes_starts, index)


def _fingerprint(show: Any, episodes: tuple[Any, ...]) -> tuple[Any, ...]:
    """Cheap and O(1): what a change to a show almost always changes.

    A feed refresh that rewrites an existing episode's title in place keeps the
    count and the ends the same, which is why the refresh also calls
    :meth:`LibrarySearchIndex.invalidate` for the show it merged.
    """
    if not episodes:
        return (show.title, 0)
    first, last = episodes[0], episodes[-1]
    return (show.title, len(episodes), first.guid, first.title, last.guid, last.title)


class LibrarySearchIndex:
    """Every podcast's searchable text, folded once and kept current per show."""

    def __init__(
        self,
        *,
        notes_chars_per_episode: int = NOTES_CHARS_PER_EPISODE,
        notes_total_chars: int = NOTES_TOTAL_CHARS,
    ) -> None:
        self._notes_per_episode = max(0, notes_chars_per_episode)
        self._notes_total = max(0, notes_total_chars)
        self._records: dict[str, _ShowRecord] = {}
        self._order: list[str] = []
        self._dirty: set[str] = set()
        self._all_dirty = False
        self._notes_chars = 0
        self._notes_skipped = 0
        self._lock = threading.RLock()
        #: Bumped whenever a sync changed what a search could find.
        self.generation = 0
        #: Records rebuilt by the most recent sync -- one after one refresh.
        self.last_rebuilt = 0

    # -- keeping it current ------------------------------------------------ #

    def invalidate(self, show_id: str | None = None) -> None:
        """Mark one show (or, with ``None``, every show) for a rebuild at the next sync."""
        with self._lock:
            if show_id is None:
                self._all_dirty = True
            else:
                self._dirty.add(str(show_id))

    def sync(self, shows: Iterable[Any], *, cancel: Callable[[], bool] | None = None) -> int:
        """Bring the index in line with *shows* (library order). Returns records rebuilt.

        Raises :class:`~quill.stability.task_manager.CancelledError` when *cancel*
        answers yes; what was rebuilt before that stays rebuilt.
        """
        with self._lock:
            order: list[str] = []
            rebuilt = 0
            for count, show in enumerate(shows):
                if cancel is not None and count % _CANCEL_STRIDE == 0 and cancel():
                    raise CancelledError("search superseded")
                show_id = str(show.id)
                order.append(show_id)
                episodes = tuple(show.episodes)
                fingerprint = _fingerprint(show, episodes)
                known = self._records.get(show_id)
                if (
                    known is not None
                    and not self._all_dirty
                    and known.show is show
                    and known.fingerprint == fingerprint
                    and show_id not in self._dirty
                ):
                    continue
                if known is not None:
                    self._notes_chars -= known.notes_chars
                self._records[show_id] = self._build(show, episodes, fingerprint)
                self._dirty.discard(show_id)
                rebuilt += 1
            live = set(order)
            removed = [show_id for show_id in self._records if show_id not in live]
            for show_id in removed:
                self._notes_chars -= self._records.pop(show_id).notes_chars
            self._order = order
            self._dirty.clear()
            self._all_dirty = False
            if rebuilt or removed:
                self.generation += 1
            self.last_rebuilt = rebuilt
            return rebuilt

    def _build(self, show: Any, episodes: tuple[Any, ...], fingerprint: tuple[Any, ...]) -> Any:
        record = _ShowRecord(show, episodes, fingerprint)
        if self._notes_per_episode:
            room = self._notes_total - self._notes_chars
            parts: list[str] = []
            used = 0
            for episode in episodes:
                text = _notes_text(
                    str(getattr(episode, "description", "") or ""), self._notes_per_episode
                )
                if text and used + len(text) > room:
                    self._notes_skipped += 1
                    text = ""
                used += len(text)
                parts.append(text)
            if used:
                record.notes_hay, record.notes_starts = _joined(parts)
                record.notes_chars = used
                self._notes_chars += used
        return record

    def stats(self) -> dict[str, int]:
        """Sizes and what the memory caps turned away (diagnostics; no user text)."""
        with self._lock:
            return {
                "shows": len(self._records),
                "episodes": sum(len(r.episodes) for r in self._records.values()),
                "notes_characters": self._notes_chars,
                "notes_skipped_for_memory": self._notes_skipped,
                "generation": self.generation,
            }

    # -- asking it ----------------------------------------------------------- #

    def search(
        self,
        query: str,
        *,
        notes: Iterable[Any] = (),
        transcripts: Iterable[Any] = (),
        hidden: Callable[[Any], Callable[[Any], bool] | None] | None = None,
        cap: int = RESULT_CAP,
        cancel: Callable[[], bool] | None = None,
    ) -> tuple[list[SearchHit], int]:
        """``(hits, total)``: at most *cap* ranked hits, and how many matched.

        *notes* are your episode notes (``show_id``, ``episode_guid``, ``text``);
        *transcripts* are :class:`~quill.core.podcasts.transcript_index.TranscriptMatch`
        values; *hidden* answers, per show, the Episode Filter's "hide from
        search" test (``None`` for a show with no such rule).
        """
        needle = fold_query(query)
        if not needle:
            return [], 0
        with self._lock:
            records = [self._records[s] for s in self._order if s in self._records]
            by_id = dict(self._records)
        stop = _Stopper(cancel)
        predicates: dict[str, Callable[[Any], bool] | None] = {}

        def is_hidden(record: _ShowRecord, episode: Any) -> bool:
            if hidden is None:
                return False
            show_id = str(record.show.id)
            if show_id not in predicates:
                predicates[show_id] = hidden(record.show)
            predicate = predicates[show_id]
            return predicate is not None and bool(predicate(episode))

        hits: list[SearchHit] = []
        total = 0
        for record in records:
            stop.tick()
            if needle in record.title_folded:
                total += 1
                if len(hits) < cap:
                    hits.append(SearchHit(KIND_SHOW, str(record.show.id), str(record.show.title)))

        # Episode titles, newest first across the library, through a bounded heap.
        counter = [0]

        def titled() -> Iterator[tuple[str, str, int, _ShowRecord, int]]:
            for sequence, record in enumerate(records):
                stop.tick()
                for index in _matching_positions(record.title_hay, record.title_starts, needle):
                    episode = record.episodes[index]
                    if is_hidden(record, episode):
                        continue
                    counter[0] += 1
                    yield (episode.published or "", episode.title or "", -sequence, record, index)

        hits.extend(self._newest(titled(), cap - len(hits), KIND_EPISODE))
        total += counter[0]

        # Your notes, in the order they were written.
        for count, note in enumerate(notes):
            if count % _CANCEL_STRIDE == 0:
                stop.tick()
            text = str(getattr(note, "text", "") or "")
            if needle not in text.casefold():
                continue
            noted_in = by_id.get(str(getattr(note, "show_id", "")))
            if noted_in is None:
                continue
            index = noted_in.position_of(str(getattr(note, "episode_guid", "")))
            if index < 0 or is_hidden(noted_in, noted_in.episodes[index]):
                continue
            total += 1
            if len(hits) < cap:
                lines = text.splitlines()
                hits.append(self._hit(KIND_NOTE, noted_in, index, lines[0] if lines else ""))

        # Show notes, for episodes their title did not already find.
        counter[0] = 0

        def noted() -> Iterator[tuple[str, str, int, _ShowRecord, int]]:
            for sequence, record in enumerate(records):
                stop.tick()
                for index in _matching_positions(record.notes_hay, record.notes_starts, needle):
                    if record.title_matches(index, needle):
                        continue
                    episode = record.episodes[index]
                    if is_hidden(record, episode):
                        continue
                    counter[0] += 1
                    yield (episode.published or "", episode.title or "", -sequence, record, index)

        hits.extend(self._newest(noted(), cap - len(hits), KIND_SHOW_NOTES))
        total += counter[0]

        # Transcript text, for episodes nothing above already found.
        spoken: list[tuple[str, str, int, _ShowRecord, int, str]] = []
        for count, match in enumerate(transcripts):
            if count % _CANCEL_STRIDE == 0:
                stop.tick()
            heard_in = by_id.get(str(match.show_id))
            if heard_in is None:
                continue
            index = heard_in.position_of(str(match.episode_guid))
            if (
                index < 0
                or heard_in.title_matches(index, needle)
                or heard_in.notes_match(index, needle)
            ):
                continue
            episode = heard_in.episodes[index]
            if is_hidden(heard_in, episode):
                continue
            total += 1
            spoken.append((
                episode.published or "",
                episode.title or "",
                0,
                heard_in,
                index,
                match.snippet,
            ))
        spoken.sort(key=lambda row: (row[0], row[1]), reverse=True)
        for _published, _title, _seq, record, index, snippet in spoken[: max(0, cap - len(hits))]:
            hits.append(self._hit(KIND_TRANSCRIPT, record, index, snippet))
        return hits, total

    @staticmethod
    def _hit(kind: str, record: _ShowRecord, index: int, snippet: str = "") -> SearchHit:
        episode = record.episodes[index]
        return SearchHit(
            kind,
            str(record.show.id),
            str(record.show.title),
            str(episode.guid),
            str(episode.title or ""),
            str(episode.published or ""),
            snippet,
        )

    def _newest(
        self, rows: Iterator[tuple[str, str, int, _ShowRecord, int]], room: int, kind: str
    ) -> list[SearchHit]:
        """The *room* newest of *rows*, consuming all of them (so they are counted)."""
        if room <= 0:
            for _row in rows:
                pass
            return []
        best = heapq.nlargest(room, rows, key=lambda row: (row[0], row[1], row[2]))
        return [self._hit(kind, record, index) for _p, _t, _s, record, index in best]


class _Stopper:
    """The cancel test, asked at a stride so asking costs nothing measurable."""

    __slots__ = ("_cancel", "_count")

    def __init__(self, cancel: Callable[[], bool] | None) -> None:
        self._cancel = cancel
        self._count = 0

    def tick(self) -> None:
        if self._cancel is None:
            return
        self._count += 1
        if self._count % _CANCEL_STRIDE == 0 and self._cancel():
            raise CancelledError("search superseded")


def find_everything(
    index: LibrarySearchIndex,
    shows: Sequence[Any],
    query: str,
    *,
    library: Any = None,
    notes: Iterable[Any] = (),
    transcripts: Any = None,
    cap: int = RESULT_CAP,
    cancel: Callable[[], bool] | None = None,
) -> SearchOutcome:
    """One whole Find, for a worker thread: sync, index transcripts, search.

    *shows* is a list the caller copied on the UI thread (the model's own list
    is the UI thread's to change); *transcripts* is a
    :class:`~quill.core.podcasts.transcript_index.TranscriptSearchIndex` or
    ``None``. Raises ``CancelledError`` if *cancel* answers yes on the way.
    """
    index.sync(shows, cancel=cancel)
    matches: Iterable[Any] = ()
    needle = fold_query(query)
    if transcripts is not None and needle:
        if not transcripts.refresh(cancel=cancel):
            raise CancelledError("search superseded")
        matches = list(transcripts.search(needle, cancel=cancel))
    hidden = None
    if library is not None:
        from quill.core.podcasts.episode_filter_maintenance import hide_predicate
        from quill.core.podcasts.models_filters import SCOPE_SEARCH

        def hidden(show: Any) -> Callable[[Any], bool] | None:
            return hide_predicate(library, show, SCOPE_SEARCH)

    hits, total = index.search(
        query, notes=notes, transcripts=matches, hidden=hidden, cap=cap, cancel=cancel
    )
    if cancel is not None and cancel():
        raise CancelledError("search superseded")
    return SearchOutcome(query.strip(), tuple(hits), total, index.generation)
