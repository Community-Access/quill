"""Reopen the last Find Streams results.

A scan of a big station page can take a minute and finds dozens of streams.
Close the window to listen to one, and the list is gone. So the last results are
kept, with the way they were shown (the filter, the sort order and the row you
were on), and **Reopen Last Results** in Find Streams puts them back.

Rules that keep it trustworthy:

* **Nothing plays and nothing rescans.** Reopening only fills the list. The
  streams are shown as they were checked, and the status says when, so an old
  "live" is never passed off as fresh; Test checks it again by playing it.
* **A New Search clears it.** The next scan that finds anything replaces it, and
  **Clear Recent Searches...** forgets it with the other remembered things.
* **A damaged or missing file is ignored quietly.** Any unreadable, oversized or
  wrongly shaped content gives ``None``: no error, no sentence, no crash.
* **Only public web addresses are kept.** An address that is not http or https
  is dropped, as is one on this computer or the listener's own network
  (:mod:`quill.core.net_public`), and the list is capped at
  :data:`MAX_STREAMS` rows.

It is stored on the listener's own computer, in ``find_streams_last.json``, and
is never sent anywhere. The idea is Andre Louis's, from StreamSift
(https://github.com/OnjLouis/StreamSift, MIT), written in QUILL's own code.

wx-free, network-free, strict-typed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from quill.core import storage
from quill.core.net_public import host_is_refused
from quill.core.radio import find_streams_view as view
from quill.core.radio.page_links import PageStreamCandidate

__all__ = [
    "FILE_NAME",
    "MAX_STREAMS",
    "LastResults",
    "clear",
    "from_json",
    "load",
    "offer_sentence",
    "reopened_sentence",
    "save",
    "to_json",
]

FILE_NAME = "find_streams_last.json"
MAX_STREAMS = 500
_MAX_TEXT = 512
_VERSION = 1


@dataclass(slots=True)
class LastResults:
    """The last scan's rows and how they were shown."""

    page_url: str
    candidates: list[PageStreamCandidate]
    page_title: str = ""
    favicon_url: str = ""
    order: str = view.SCAN
    format: str = ""
    live_only: bool = False
    #: The address of the row that had focus, "" for the first.
    current: str = ""
    saved_at: float = field(default_factory=time.time)

    @property
    def state(self) -> view.ViewState:
        return view.ViewState(self.order, self.format, self.live_only)


_CANDIDATE_FIELDS = {f.name: f.type for f in fields(PageStreamCandidate)}


def _text(value: Any) -> str:
    return value[:_MAX_TEXT] if isinstance(value, str) else ""


def _safe_url(value: Any) -> str:
    from urllib.parse import urlsplit

    text = _text(value).strip()
    parts = urlsplit(text)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        return ""
    return "" if host_is_refused(parts.hostname) else text


def _candidate_to_json(c: PageStreamCandidate) -> dict[str, Any]:
    return {name: getattr(c, name) for name in _CANDIDATE_FIELDS}


def _candidate_from_json(raw: Any) -> PageStreamCandidate | None:
    if not isinstance(raw, dict):
        return None
    url = _safe_url(raw.get("url"))
    if not url:
        return None
    bitrate = raw.get("bitrate_kbps")
    listeners = raw.get("listeners")
    return PageStreamCandidate(
        url=url,
        reason=_text(raw.get("reason")),
        label=_text(raw.get("label")),
        check=_text(raw.get("check")),
        codec=_text(raw.get("codec")),
        bitrate_kbps=bitrate if isinstance(bitrate, int) and 0 <= bitrate < 100000 else 0,
        stream_name=_text(raw.get("stream_name")),
        genre=_text(raw.get("genre")),
        check_note=_text(raw.get("check_note")),
        listeners=listeners if isinstance(listeners, int) and listeners >= 0 else None,
        label_is_name=raw.get("label_is_name") is True,
    )


def to_json(results: LastResults) -> dict[str, Any]:
    return {
        "version": _VERSION,
        "page_url": results.page_url,
        "page_title": results.page_title,
        "favicon_url": results.favicon_url,
        "order": results.order,
        "format": results.format,
        "live_only": results.live_only,
        "current": results.current,
        "saved_at": results.saved_at,
        "candidates": [_candidate_to_json(c) for c in results.candidates[:MAX_STREAMS]],
    }


def from_json(raw: Any) -> LastResults | None:
    """Rebuild saved results, or ``None`` for anything damaged or empty."""
    try:
        if not isinstance(raw, dict) or raw.get("version") != _VERSION:
            return None
        rows = raw.get("candidates")
        if not isinstance(rows, list):
            return None
        candidates = [c for c in map(_candidate_from_json, rows[:MAX_STREAMS]) if c is not None]
        if not candidates:
            return None
        order = raw.get("order")
        fmt = raw.get("format")
        saved = raw.get("saved_at")
        return LastResults(
            page_url=_text(raw.get("page_url")),
            candidates=candidates,
            page_title=_text(raw.get("page_title")),
            favicon_url=_text(raw.get("favicon_url")),
            order=order if order in view.ORDERS else view.SCAN,
            format=fmt if fmt in view.FORMATS else "",
            live_only=raw.get("live_only") is True,
            current=_text(raw.get("current")),
            saved_at=float(saved) if isinstance(saved, (int, float)) else 0.0,
        )
    except (TypeError, ValueError, OverflowError):
        return None


def load(directory: Path) -> LastResults | None:
    """The saved results, or ``None``; never raises."""
    try:
        return from_json(storage.read_json(directory / FILE_NAME, None))
    except Exception:  # noqa: BLE001 - damaged saved results are ignored quietly
        return None


def save(directory: Path, results: LastResults) -> None:
    """Write the results; a failure to write is ignored (they are a convenience)."""
    try:
        storage.write_json_atomic(directory / FILE_NAME, to_json(results))
    except OSError:
        pass


def clear(directory: Path) -> bool:
    """Forget the saved results; True when there was a file to remove."""
    try:
        (directory / FILE_NAME).unlink()
    except OSError:
        return False
    return True


def _site(results: LastResults) -> str:
    from urllib.parse import urlsplit

    return urlsplit(results.page_url).hostname or results.page_title or "the last page"


def _count(results: LastResults) -> str:
    n = len(results.candidates)
    return f"{n:,} {'stream' if n == 1 else 'streams'}"


def offer_sentence(results: LastResults) -> str:
    """Said when Find Streams opens and results are waiting."""
    return (
        f"Your last results are saved: {_count(results)} from {_site(results)}. "
        "Choose Reopen Last Results to see them."
    )


def reopened_sentence(results: LastResults, *, now: float | None = None) -> str:
    """Said after Reopen: what is shown and how old it is, and that nothing ran."""
    age = (now if now is not None else time.time()) - results.saved_at
    if age < 90:
        when = "a moment ago"
    elif age < 3600:
        when = f"{int(age // 60)} minutes ago"
    elif age < 86400:
        hours = int(age // 3600)
        when = f"{hours} {'hour' if hours == 1 else 'hours'} ago"
    else:
        days = int(age // 86400)
        when = f"{days} {'day' if days == 1 else 'days'} ago"
    return (
        f"Reopened {_count(results)} from {_site(results)}, found {when}. "
        "Nothing was scanned or played."
    )
