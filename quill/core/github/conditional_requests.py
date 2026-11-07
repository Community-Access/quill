"""Conditional GitHub reads: send the last ETag, and treat a 304 as "nothing changed".

GitHub answers ``If-None-Match`` with 304 Not Modified when a resource is the
same as last time, and a 304 does not count against the rate limit. So the
workbench keeps the last ETag and body for each read it repeats (Explore's
Pages view, Insights, caches, secrets, the community profile) and a refresh
that changed nothing says so instead of re-announcing the same list.

The cache is per account (the key is a hash of the token, never the token),
bounded to :data:`MAX_ENTRIES` reads of at most :data:`MAX_BODY_CHARS` each,
and written with :func:`~quill.core.storage.write_json_atomic`. Losing it costs
one full read, so it is a regenerable ``cache`` in the persistence audit.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from quill.core.github.navigation_state import account_key_for_token
from quill.core.github.rate_limits import RateLimitTracker
from quill.core.github.rest_transport import RestResponse, request_json
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_FILENAME = "github_etag_cache.json"
_VERSION = 1
MAX_ENTRIES = 64
MAX_BODY_CHARS = 262_144
_MAX_ACCOUNTS = 8


@dataclass(slots=True)
class _Entry:
    etag: str
    data: Any
    stored_at: float


@dataclass(frozen=True, slots=True)
class ConditionalResult:
    """A read's body, and whether it differs from the last one QUILL saw."""

    data: Any
    changed: bool
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)


class EtagCache:
    """The last ETag and body per request key, for one account."""

    def __init__(self, path: Path | None, account_key: str) -> None:
        self._path = path
        self._account_key = account_key
        self._lock = threading.Lock()
        self._entries: dict[str, _Entry] = {}
        self._others: dict[str, Any] = {}

    @classmethod
    def load(cls, token: str | None, *, path: Path | None = None) -> EtagCache:
        target = path if path is not None else app_data_dir() / _FILENAME
        cache = cls(target, account_key_for_token(token))
        raw = read_json(target, default={})
        accounts = raw.get("accounts") if isinstance(raw, dict) else None
        if isinstance(accounts, dict):
            cache._others = {k: v for k, v in accounts.items() if k != cache._account_key}
            mine = accounts.get(cache._account_key)
            if isinstance(mine, dict):
                for key, value in mine.items():
                    if (
                        isinstance(key, str)
                        and isinstance(value, dict)
                        and isinstance(value.get("etag"), str)
                    ):
                        stored = value.get("at")
                        cache._entries[key] = _Entry(
                            value["etag"],
                            value.get("data"),
                            float(stored) if isinstance(stored, (int, float)) else 0.0,
                        )
        return cache

    def get(self, key: str) -> tuple[str, Any] | None:
        with self._lock:
            entry = self._entries.get(key)
            return (entry.etag, entry.data) if entry is not None else None

    def put(self, key: str, etag: str, data: Any) -> bool:
        """Keep *data* under *key*; False (and nothing kept) when it is too large."""
        if not etag:
            return False
        try:
            size = len(json.dumps(data))
        except (TypeError, ValueError):
            return False
        if size > MAX_BODY_CHARS:
            with self._lock:
                self._entries.pop(key, None)
            return False
        with self._lock:
            self._entries[key] = _Entry(etag, data, time.time())
            if len(self._entries) > MAX_ENTRIES:
                oldest = sorted(self._entries.items(), key=lambda item: item[1].stored_at)
                for stale, _entry in oldest[: len(self._entries) - MAX_ENTRIES]:
                    del self._entries[stale]
        self.save()
        return True

    def forget(self, key: str) -> None:
        with self._lock:
            removed = self._entries.pop(key, None)
        if removed is not None:
            self.save()

    def save(self) -> bool:
        if self._path is None:
            return True
        with self._lock:
            mine = {
                key: {"etag": entry.etag, "data": entry.data, "at": entry.stored_at}
                for key, entry in self._entries.items()
            }
            others = dict(list(self._others.items())[-(_MAX_ACCOUNTS - 1) :])
        try:
            write_json_atomic(
                self._path, {"version": _VERSION, "accounts": {**others, self._account_key: mine}}
            )
        except OSError:
            return False
        return True


_CACHES: dict[str, EtagCache] = {}
_CACHES_LOCK = threading.Lock()


def cache_for(token: str | None) -> EtagCache:
    """This process's cache for the account behind *token*, loaded once."""
    key = account_key_for_token(token)
    with _CACHES_LOCK:
        cache = _CACHES.get(key)
        if cache is None:
            cache = EtagCache.load(token)
            _CACHES[key] = cache
        return cache


def reset_caches() -> None:
    """Forget the loaded caches (the files stay); the next read loads again."""
    with _CACHES_LOCK:
        _CACHES.clear()


def request_key(path: str, query: dict[str, str] | None = None) -> str:
    return path + (f"?{urlencode(sorted(query.items()))}" if query else "")


def conditional_get(
    token: str | None,
    path: str,
    *,
    query: dict[str, str] | None = None,
    cache: EtagCache | None = None,
    extra_headers: dict[str, str] | None = None,
    opener: Any = None,
    tracker: RateLimitTracker | None = None,
) -> ConditionalResult:
    """GET *path* with the last ETag; a 304 hands back the stored body, unchanged."""
    store = cache if cache is not None else cache_for(token)
    key = request_key(path, query)
    previous = store.get(key)
    headers = dict(extra_headers or {})
    if previous is not None:
        headers["If-None-Match"] = previous[0]
    response: RestResponse = request_json(
        token, "GET", path, query=query, extra_headers=headers, opener=opener, tracker=tracker
    )
    if response.status == 304:
        if previous is not None:
            return ConditionalResult(previous[1], False, 304, response.headers)
        # A 304 with nothing stored cannot be shown; ask again without a validator.
        response = request_json(
            token,
            "GET",
            path,
            query=query,
            extra_headers=dict(extra_headers or {}),
            opener=opener,
            tracker=tracker,
        )
    etag = response.header("ETag")
    changed = previous is None or previous[1] != response.data
    if etag:
        store.put(key, etag, response.data)
    return ConditionalResult(response.data, changed, response.status, response.headers)


__all__ = [
    "MAX_BODY_CHARS",
    "MAX_ENTRIES",
    "ConditionalResult",
    "EtagCache",
    "cache_for",
    "conditional_get",
    "request_key",
    "reset_caches",
]
