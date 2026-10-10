"""Bounded, thread-safe, on-disk cache for synthesized TTS sentence audio.

Read Aloud renders speech one sentence at a time to a temporary WAV file
(``ReadAloudController._run_wav_sentences``). When a document repeats a
sentence -- a heading, a refrain, a boilerplate disclaimer, or simply the same
paragraph re-read -- the WAV is byte-for-byte identical for a given engine and
voice configuration. Re-synthesizing it wastes the most expensive part of the
pipeline (PERF-3) and, for long documents, repeatedly hammers the engine
(PERF-10).

This module provides a small disk-backed LRU cache keyed by a stable signature
of the engine configuration plus the exact sentence text. The cache is bounded
by both an entry count and a total byte budget so that long-document playback
cannot let the cache grow without limit. It is UI-framework-agnostic and holds
no audio in memory -- only file paths and sizes -- so memory stays flat.

The public seam used by ``read_aloud`` is :func:`cached_sentence_generator`,
which wraps an engine's ``generate_sentence_wav`` closure so the existing
playback loop needs no changes: on a cache hit the cached WAV is materialized
at the caller's output path instead of being re-rendered.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import threading
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path

#: Default ceilings. A few hundred short sentences of WAV stay well under this.
_DEFAULT_MAX_ENTRIES = 512
_DEFAULT_MAX_BYTES = 256 * 1024 * 1024  # 256 MiB


def signature(*parts: object) -> str:
    """Return a stable hex signature for the given configuration parts.

    The parts identify everything that affects the rendered audio: the engine
    name, voice/model identifiers, rate/speed, and the exact sentence text.
    The same inputs always yield the same key, independent of process or run.
    """

    hasher = hashlib.sha256()
    for part in parts:
        hasher.update(repr(part).encode("utf-8", "surrogatepass"))
        hasher.update(b"\x00")
    return hasher.hexdigest()


class TtsCache:
    """A disk-backed LRU cache of synthesized sentence WAV files."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        max_entries: int = _DEFAULT_MAX_ENTRIES,
        max_bytes: int = _DEFAULT_MAX_BYTES,
    ) -> None:
        self._dir = cache_dir
        self._max_entries = max(1, int(max_entries))
        self._max_bytes = max(1, int(max_bytes))
        self._lock = threading.Lock()
        # key -> stored size in bytes, ordered oldest-first for LRU eviction.
        self._entries: OrderedDict[str, int] = OrderedDict()
        self._total_bytes = 0
        self._load_existing()

    def _path_for(self, key: str) -> Path:
        return self._dir / f"{key}.wav"

    def _load_existing(self) -> None:
        try:
            files = sorted(
                (p for p in self._dir.glob("*.wav") if p.is_file()),
                key=lambda p: p.stat().st_mtime,
            )
        except OSError:
            return
        for path in files:
            try:
                size = path.stat().st_size
            except OSError:
                continue
            self._entries[path.stem] = size
            self._total_bytes += size
        self._evict_locked()

    def _evict_locked(self) -> None:
        while self._entries and (
            len(self._entries) > self._max_entries or self._total_bytes > self._max_bytes
        ):
            key, size = self._entries.popitem(last=False)
            self._total_bytes -= size
            try:
                self._path_for(key).unlink(missing_ok=True)
            except OSError:
                pass

    def get(self, key: str) -> Path | None:
        """Return the cached WAV path for ``key`` or ``None`` on a miss."""

        with self._lock:
            if key not in self._entries:
                return None
            path = self._path_for(key)
            if not path.exists():
                # Evicted underneath us; drop the stale index entry.
                self._total_bytes -= self._entries.pop(key, 0)
                return None
            self._entries.move_to_end(key)
            return path

    def put(self, key: str, source: Path) -> Path:
        """Store ``source`` under ``key`` and return the cached path.

        The source file is copied into the cache directory; the caller's file
        is left untouched. Eviction runs after insertion to honour the bounds.
        """

        dest = self._path_for(key)
        with self._lock:
            try:
                self._dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
                size = dest.stat().st_size
            except OSError:
                return source
            if key in self._entries:
                self._total_bytes -= self._entries.pop(key)
            self._entries[key] = size
            self._total_bytes += size
            self._evict_locked()
        return dest

    def clear(self) -> None:
        """Remove every cached file and reset the index."""

        with self._lock:
            for key in list(self._entries):
                try:
                    self._path_for(key).unlink(missing_ok=True)
                except OSError:
                    pass
            self._entries.clear()
            self._total_bytes = 0


_DEFAULT_CACHE: TtsCache | None = None
_DEFAULT_LOCK = threading.Lock()


def default_cache() -> TtsCache:
    """Return the process-wide cache rooted under the app data directory."""

    global _DEFAULT_CACHE
    with _DEFAULT_LOCK:
        if _DEFAULT_CACHE is None:
            from quill.core.paths import app_data_dir

            _DEFAULT_CACHE = TtsCache(app_data_dir() / "cache" / "tts")
        return _DEFAULT_CACHE


def cached_sentence_generator(
    seed: object,
    generate_sentence_wav: Callable[[str, Path], None],
    *,
    cache: TtsCache | None = None,
) -> Callable[[str, Path], None]:
    """Wrap an engine generator with identical-sentence caching.

    ``seed`` captures the engine configuration (name, voice, rate, model). The
    returned closure has the same ``(sentence, out)`` contract as the original:
    on a cache hit it copies the cached WAV to ``out``; on a miss it renders
    via ``generate_sentence_wav`` and stores the result for next time.
    """

    store = cache if cache is not None else default_cache()

    def materialize(hit: Path, out: Path) -> bool:
        try:
            out.unlink(missing_ok=True)
            os.link(hit, out)
            return True
        except OSError:
            try:
                shutil.copyfile(hit, out)
                return True
            except OSError:
                return False

    def generate(sentence: str, out: Path) -> None:
        key = signature(seed, sentence)
        hit = store.get(key)
        if hit is not None and materialize(hit, out):
            return
        generate_sentence_wav(sentence, out)
        try:
            if out.exists() and out.stat().st_size > 0:
                store.put(key, out)
        except OSError:
            pass

    return generate
