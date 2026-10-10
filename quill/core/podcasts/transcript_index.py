"""Downloaded transcripts, indexed once and searched without reading the disk (F-09).

Find in library searches the transcripts already on this machine -- fetched from
a feed's ``podcast:transcript`` tag or transcribed here -- and **never** fetches
one. Until this index existed the only transcript search was Search Everywhere,
which read every cached file from disk on every search: fine for a handful,
and the scan qc.md's F-09 exists to replace once a listener has hundreds.

Three properties, each with a test in ``test_cast_search_index.py``:

* **Incremental.** A refresh lists the cache folder (one ``scandir``, which on
  Windows carries each file's size and time for free) and reads only the files
  that are new or changed since the last refresh; a file that has gone is
  dropped. The second search reads nothing it has already read.
* **Cancellable.** The refresh runs on the task manager, never the UI thread,
  and checks its cancel test between files, so a query superseded by more
  typing stops reading at the next file rather than finishing a stale job.
* **Bounded.** Each transcript is indexed up to :data:`PER_TRANSCRIPT_CHARS`,
  and the whole index up to :data:`TOTAL_CHARS`; a transcript that would pass
  the total is skipped and *counted* (``stats()``), so the cap is observable in
  diagnostics rather than a silent miss. Text only -- no user data is logged.

wx-free. The folder is the transcript cache ``transcripts.py`` writes.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "PER_TRANSCRIPT_CHARS",
    "TOTAL_CHARS",
    "TranscriptMatch",
    "TranscriptSearchIndex",
]

#: The longest single transcript indexed, in characters. A three-hour interview
#: is about 180,000; this is twice that, so only a pathological file is cut.
PER_TRANSCRIPT_CHARS = 400_000

#: The whole index's ceiling, in characters of searchable text. Each indexed
#: transcript is held twice (as written, for the snippet, and folded, for the
#: search), so this is roughly 2 x this many characters of memory at most.
TOTAL_CHARS = 32_000_000

#: Characters either side of a hit in a snippet.
_SNIPPET_BEFORE = 30
_SNIPPET_AFTER = 50


@dataclass(frozen=True, slots=True)
class TranscriptMatch:
    """One transcript that contains the query, with a window around the first hit."""

    show_id: str
    episode_guid: str
    snippet: str


@dataclass(slots=True)
class _Entry:
    stamp: tuple[int, int]  # (mtime_ns, size)
    show_id: str
    episode_guid: str
    text: str
    folded: str


def _default_directory() -> Path:
    from quill.core.podcasts.transcripts import _cache_dir

    return _cache_dir()


class TranscriptSearchIndex:
    """The cached transcripts, folded once, searched in memory."""

    def __init__(
        self,
        directory: Callable[[], Path] | None = None,
        *,
        per_transcript_chars: int = PER_TRANSCRIPT_CHARS,
        total_chars: int = TOTAL_CHARS,
    ) -> None:
        self._directory = directory or _default_directory
        self._per_transcript = max(1, per_transcript_chars)
        self._total_limit = max(1, total_chars)
        self._entries: dict[str, _Entry] = {}
        self._chars = 0
        #: Files the total cap turned away, by the stamp they had then; a
        #: changed file is tried again.
        self._skipped: dict[str, tuple[int, int]] = {}
        self._lock = threading.RLock()
        #: Bumped whenever what a search could find changes.
        self.generation = 0
        #: Files read by the most recent refresh -- zero on a warm second search.
        self.last_reads = 0

    # -- keeping it current ------------------------------------------------ #

    def refresh(self, *, cancel: Callable[[], bool] | None = None) -> bool:
        """Bring the index up to date with the folder. Returns whether it finished.

        ``False`` only when *cancel* answered yes part-way; what was read before
        that stays read, so the next refresh carries on rather than starting over.
        """
        with self._lock:
            self.last_reads = 0
            try:
                folder = self._directory()
                listing = list(os.scandir(folder)) if folder.is_dir() else []
            except OSError:
                listing = []
            seen: set[str] = set()
            for entry in listing:
                if cancel is not None and cancel():
                    return False
                name = entry.name
                if not name.endswith(".txt"):
                    continue
                seen.add(name)
                try:
                    info = entry.stat()
                except OSError:
                    continue
                stamp = (int(info.st_mtime_ns), int(info.st_size))
                known = self._entries.get(name)
                if known is not None and known.stamp == stamp:
                    continue
                if known is None and self._skipped.get(name) == stamp:
                    continue
                self._read(name, Path(entry.path), stamp)
            for gone in [name for name in self._entries if name not in seen]:
                self._drop(gone)
            self._skipped = {k: v for k, v in self._skipped.items() if k in seen}
            return True

    def _read(self, name: str, path: Path, stamp: tuple[int, int]) -> None:
        self.last_reads += 1
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return
        parts = raw.split("\n", 2)
        if len(parts) != 3 or not parts[0] or not parts[1]:
            return
        text = parts[2][: self._per_transcript]
        if name in self._entries:
            self._drop(name)
        folded = text.casefold()
        accounted_chars = len(folded)
        if self._chars + accounted_chars > self._total_limit:
            self._skipped[name] = stamp
            return
        # A casefold that changes the length (German sharp s, a few ligatures)
        # would misplace the snippet window; search the folded text and show it.
        shown = text if len(folded) == len(text) else folded
        self._entries[name] = _Entry(stamp, parts[0], parts[1], shown, folded)
        self._chars += accounted_chars
        self.generation += 1

    def _drop(self, name: str) -> None:
        entry = self._entries.pop(name, None)
        if entry is not None:
            self._chars -= len(entry.folded)
            self.generation += 1

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._skipped.clear()
            self._chars = 0
            self.generation += 1

    # -- asking it ----------------------------------------------------------- #

    def search(
        self, needle: str, *, cancel: Callable[[], bool] | None = None
    ) -> Iterator[TranscriptMatch]:
        """Every indexed transcript containing *needle* (already casefolded)."""
        if not needle:
            return
        with self._lock:
            entries = list(self._entries.values())
        for count, entry in enumerate(entries):
            if cancel is not None and count % 64 == 0 and cancel():
                return
            position = entry.folded.find(needle)
            if position < 0:
                continue
            start = max(0, position - _SNIPPET_BEFORE)
            window = entry.text[start : position + len(needle) + _SNIPPET_AFTER]
            yield TranscriptMatch(entry.show_id, entry.episode_guid, " ".join(window.split()))

    def stats(self) -> dict[str, int]:
        """What is indexed and what the memory cap turned away (diagnostics)."""
        with self._lock:
            return {
                "transcripts": len(self._entries),
                "characters": self._chars,
                "skipped_for_memory": len(self._skipped),
            }
