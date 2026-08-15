"""A small on-disk cache for directory listings that change slowly.

Browsing a directory is not searching it. A search is a fresh question every
time; a *browse level* -- the Xiph genre index, an Apple genre tree, a country
list -- is the same answer for hours or days, and refetching it on every open
costs a listener seconds of silence for nothing.

This is the fourth tier the radio stack was missing. The three-tier resolver in
:mod:`quill.core.radio.wxindex` and :mod:`quill.core.radio.reading_services`
(fresh cache -> live refresh -> stale cache -> bundled snapshot) already exists
twice, written out longhand both times; this is that shape as one reusable
function, minus the bundled tier, which is per-source.

Design notes that matter:

* **A stale answer beats no answer.** When the live fetch fails, a cache entry
  past its age is returned rather than an empty list -- with its age available
  so the caller can say so out loud rather than passing it off as current.
* **Failure is never fatal.** An unwritable cache directory, a corrupt file, a
  half-written entry: every one of them degrades to "no cache", never to an
  exception reaching the browse tree.
* **Incomplete entries are marked.** A caller that deliberately read a prefix of
  a huge index (see ``xiph.fetch_genres``) can cache it, but must not have it
  handed back to a caller that asked for the whole thing.

wx-free, strict-typed, no wx and no network of its own.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_LOG = logging.getLogger(__name__)

_CACHE_DIRNAME = "radio-directory-cache"

#: Default freshness window. A browse level is not a search result: a day-old
#: genre list is fine, and Refresh is always one keystroke away on every node.
DEFAULT_MAX_AGE_SECONDS = 24 * 3600


@dataclass(frozen=True, slots=True)
class CacheEntry:
    """A cached payload and what is known about it."""

    payload: Any
    fetched_at: float
    complete: bool = True

    def age_seconds(self, *, now: float | None = None) -> float:
        return max(0.0, (time.time() if now is None else now) - self.fetched_at)

    def is_fresh(self, max_age_seconds: float, *, now: float | None = None) -> bool:
        return self.age_seconds(now=now) < max_age_seconds


def _cache_dir() -> Path:
    return app_data_dir() / _CACHE_DIRNAME


def _safe_name(key: str) -> str:
    """A filesystem-safe file name for *key* (pure, stable across sessions).

    Hashed rather than sanitised so a key containing a slash, a colon or a
    non-ASCII genre name cannot escape the cache directory or collide after
    character stripping.
    """
    import hashlib

    return f"{hashlib.sha256(key.encode('utf-8')).hexdigest()[:32]}.json"


def load(key: str) -> CacheEntry | None:
    """The cache entry for *key*, or ``None`` if absent or unreadable."""
    try:
        raw = read_json(_cache_dir() / _safe_name(key), None)
    except OSError:
        return None
    if not isinstance(raw, dict) or "payload" not in raw:
        return None
    fetched_at = raw.get("fetched_at")
    if not isinstance(fetched_at, int | float):
        return None
    return CacheEntry(
        payload=raw["payload"],
        fetched_at=float(fetched_at),
        complete=bool(raw.get("complete", True)),
    )


def save(key: str, payload: Any, *, complete: bool = True) -> None:
    """Persist *payload* under *key*. Best effort: a full disk or a read-only
    profile must never break the browse that just succeeded."""
    try:
        directory = _cache_dir()
        directory.mkdir(parents=True, exist_ok=True)
        write_json_atomic(
            directory / _safe_name(key),
            {"key": key, "payload": payload, "fetched_at": time.time(), "complete": complete},
        )
    except (OSError, TypeError, ValueError) as error:  # pragma: no cover - environmental
        _LOG.debug("directory cache write failed for %s: %s", key, error)


def forget(key: str) -> None:
    """Drop *key* from the cache -- what Refresh on a browse node calls."""
    try:
        (_cache_dir() / _safe_name(key)).unlink(missing_ok=True)
    except OSError:  # pragma: no cover - environmental
        return


def clear() -> None:
    """Drop every cached listing (diagnostics, and a settings-level reset)."""
    try:
        for path in _cache_dir().glob("*.json"):
            path.unlink(missing_ok=True)
    except OSError:  # pragma: no cover - environmental
        return


def resolve(
    key: str,
    fetch: Callable[[], Any],
    *,
    max_age_seconds: float = DEFAULT_MAX_AGE_SECONDS,
    refresh: bool = False,
    require_complete: bool = False,
    complete: bool | Callable[[], bool] = True,
    empty: Any = None,
) -> tuple[Any, float | None]:
    """Fresh cache -> live fetch -> stale cache, in that order.

    Returns ``(payload, cache_age_seconds)``. The age is ``None`` when the
    payload came from a live fetch and a float when it came from the cache, so
    a caller can say "as of yesterday" instead of implying it is current.

    The payload is deliberately untyped. A cache entry has been through JSON, so
    a generic parameter would be promising a round trip the format cannot make
    -- a tuple comes back a list, a dataclass comes back a dict. Callers coerce
    on the way out (see ``apple_podcasts._genres_from_json``), which is honest
    about where the boundary is.

    *refresh* skips the fresh-cache tier (Refresh on a node). *require_complete*
    rejects a cache entry that was stored as a deliberate prefix. A live fetch
    that raises or returns nothing falls through to a stale entry; if there is
    no entry either, *empty* is returned -- never an exception, because a browse
    tree branch that throws takes the window with it.

    *complete* may be a callable, and usually must be: whether a fetch returned
    the whole listing is generally only known *after* it runs, and passing the
    flag by value binds it a moment too early -- which is exactly how a prefix
    of the Xiph genre index first got cached as if it were the whole directory.
    """
    entry = None if refresh else load(key)
    if entry is not None and (entry.complete or not require_complete):
        if entry.is_fresh(max_age_seconds):
            return entry.payload, entry.age_seconds()
    try:
        payload = fetch()
    except Exception as error:  # noqa: BLE001 - every source has its own error type
        _LOG.debug("directory refresh failed for %s: %s", key, error)
        payload = None  # type: ignore[assignment]
    if payload:
        is_complete = complete() if callable(complete) else complete
        save(key, payload, complete=is_complete)
        return payload, None
    stale = entry if entry is not None else load(key)
    if stale is not None and (stale.complete or not require_complete):
        return stale.payload, stale.age_seconds()
    return (empty if empty is not None else payload), None  # type: ignore[return-value]


def spoken_age(age_seconds: float | None) -> str:
    """How old a cached listing is, in words, or ``""`` when it is live (pure).

    Words rather than a timestamp, matching ``spoken_duration`` in
    ``bounded_playback_ui.py``: a listener hearing "2026-08-12 19:04" has to do
    arithmetic, and a listener hearing "from yesterday" does not.
    """
    if age_seconds is None:
        return ""
    if age_seconds < 90:
        return "just now"
    minutes = age_seconds / 60
    if minutes < 60:
        return f"{int(minutes)} minutes ago"
    hours = minutes / 60
    if hours < 24:
        count = int(hours)
        return "an hour ago" if count == 1 else f"{count} hours ago"
    days = int(hours / 24)
    return "yesterday" if days == 1 else f"{days} days ago"
