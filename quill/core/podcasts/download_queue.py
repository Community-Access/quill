"""The podcast episode download queue: its own thread, resumable transfers,
and two independent pause controls (podcasts.md §4).

Runs on a dedicated background worker thread rather than the shared
``QuillTaskManager`` pool, so a backlog of podcast downloads never competes
with or slows down other QUILL background work (AI calls, transcription,
etc.) for a pool slot.

Two genuinely independent pause controls, not one setting wearing two hats:

- :meth:`PodcastDownloadQueue.pause_all` / :meth:`resume_all` stop the worker
  from *starting* new transfers; anything already mid-transfer keeps running
  to completion.
- :meth:`PodcastDownloadQueue.pause_item` / :meth:`resume_item` halt one
  specific transfer immediately, wherever it is (queued-but-not-started, or
  actively downloading) -- resuming continues from the partial bytes already
  on disk via an HTTP ``Range`` request when the server supports it, falling
  back to a clean restart when it doesn't.

wx-free, strict-typed. All callbacks fire on the worker thread; callers that
touch wx must marshal back to the UI thread themselves (e.g. via
``wx.CallAfter``), the same contract QUILL's other background workers use.
"""

from __future__ import annotations

import logging
import ssl
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from quill import __version__
from quill.core.error_codes import CodedError

_log = logging.getLogger(__name__)

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 20.0
_CHUNK_BYTES = 65536
_MAX_CONCURRENT = 3

DownloadStatus = Literal["queued", "downloading", "paused", "completed", "failed", "cancelled"]


class DownloadError(CodedError):
    """A podcast episode download failed outright (not paused/cancelled)."""

    code = "QUILL-PODCASTS-DOWNLOAD-FAILED"


@dataclass(slots=True)
class DownloadItem:
    """One queued/in-flight/finished episode download."""

    item_id: str
    show_id: str
    episode_guid: str
    url: str
    destination: Path
    status: DownloadStatus = "queued"
    bytes_downloaded: int = 0
    total_bytes: int = 0
    error_message: str = ""
    _pause_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)


def _fetch_chunked(
    url: str,
    destination: Path,
    *,
    pause_event: threading.Event,
    cancel_event: threading.Event,
    on_progress: Callable[[int, int], None],
) -> DownloadStatus:
    """One resumable HTTPS download -- the reviewed egress site.

    Reads in bounded chunks so pause/cancel take effect within one chunk,
    not only between whole-file attempts.
    """
    if not url.startswith("https://"):
        raise DownloadError("Only https:// episode links can be downloaded.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    resume_from = destination.stat().st_size if destination.exists() else 0
    headers = {"User-Agent": _USER_AGENT}
    if resume_from:
        headers["Range"] = f"bytes={resume_from}-"
    request = urllib.request.Request(url, headers=headers)
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            resumed = resume_from and getattr(resp, "status", 200) == 206
            written = resume_from if resumed else 0
            content_length = resp.headers.get("Content-Length")
            total = (written + int(content_length)) if content_length else 0
            mode = "ab" if resumed else "wb"
            with open(destination, mode) as handle:
                while True:
                    if cancel_event.is_set():
                        return "cancelled"
                    if pause_event.is_set():
                        return "paused"
                    chunk = resp.read(_CHUNK_BYTES)
                    if not chunk:
                        break
                    handle.write(chunk)
                    written += len(chunk)
                    on_progress(written, total)
        return "completed"
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise DownloadError(f"Could not download that episode: {error}") from error


class PodcastDownloadQueue:
    """Owns the one background download worker for the whole app."""

    def __init__(
        self,
        *,
        max_concurrent: int = _MAX_CONCURRENT,
        on_status_changed: Callable[[DownloadItem], None] | None = None,
        on_completed: Callable[[DownloadItem], None] | None = None,
    ) -> None:
        self._max_concurrent = max(1, max_concurrent)
        self._on_status_changed = on_status_changed or (lambda _item: None)
        self._on_completed = on_completed or (lambda _item: None)
        self._items: dict[str, DownloadItem] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()
        self._all_paused = False
        self._wake = threading.Event()
        self._active_count = 0
        self._shutdown = False
        self._worker = threading.Thread(
            target=self._run, name="quill-podcast-downloads", daemon=True
        )
        self._worker.start()

    # -- public API -----------------------------------------------------

    def enqueue(
        self, item_id: str, *, show_id: str, episode_guid: str, url: str, destination: Path
    ) -> DownloadItem:
        item = DownloadItem(
            item_id=item_id,
            show_id=show_id,
            episode_guid=episode_guid,
            url=url,
            destination=destination,
        )
        with self._lock:
            self._items[item_id] = item
            self._order.append(item_id)
        self._wake.set()
        self._on_status_changed(item)
        return item

    def pause_all(self) -> None:
        """Stop starting new transfers; anything already mid-transfer keeps
        running to completion (podcasts.md §4, control 1)."""
        with self._lock:
            self._all_paused = True

    def resume_all(self) -> None:
        with self._lock:
            self._all_paused = False
        self._wake.set()

    @property
    def all_paused(self) -> bool:
        with self._lock:
            return self._all_paused

    def pause_item(self, item_id: str) -> bool:
        """Halt this one transfer immediately, wherever it is
        (podcasts.md §4, control 2)."""
        with self._lock:
            item = self._items.get(item_id)
            if item is None or item.status in ("completed", "cancelled"):
                return False
            item._pause_event.set()
            if item.status == "queued":
                item.status = "paused"
        self._on_status_changed(item)
        return True

    def resume_item(self, item_id: str) -> bool:
        with self._lock:
            item = self._items.get(item_id)
            if item is None or item.status not in ("paused",):
                return False
            item._pause_event.clear()
            item.status = "queued"
        self._on_status_changed(item)
        self._wake.set()
        return True

    def cancel_item(self, item_id: str) -> bool:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return False
            item._cancel_event.set()
            if item.status in ("queued", "paused"):
                item.status = "cancelled"
        self._on_status_changed(item)
        return True

    def get(self, item_id: str) -> DownloadItem | None:
        with self._lock:
            return self._items.get(item_id)

    def active_count(self) -> int:
        """How many items are currently downloading (for a status summary)."""
        with self._lock:
            return sum(1 for item in self._items.values() if item.status == "downloading")

    def shutdown(self) -> None:
        self._shutdown = True
        self._wake.set()

    # -- worker -----------------------------------------------------------

    def _next_startable(self) -> DownloadItem | None:
        with self._lock:
            if self._all_paused or self._active_count >= self._max_concurrent:
                return None
            for item_id in self._order:
                item = self._items[item_id]
                if item.status == "queued":
                    item.status = "downloading"
                    self._active_count += 1
                    return item
            return None

    def _run(self) -> None:
        while not self._shutdown:
            item = self._next_startable()
            if item is None:
                self._wake.wait(timeout=1.0)
                self._wake.clear()
                continue
            self._on_status_changed(item)
            threading.Thread(
                target=self._run_one,
                args=(item,),
                daemon=True,
                name=f"quill-podcast-dl-{item.item_id}",
            ).start()

    def _run_one(self, item: DownloadItem) -> None:
        def progress(written: int, total: int) -> None:
            item.bytes_downloaded = written
            item.total_bytes = total
            self._on_status_changed(item)

        try:
            result = _fetch_chunked(
                item.url,
                item.destination,
                pause_event=item._pause_event,
                cancel_event=item._cancel_event,
                on_progress=progress,
            )
        except DownloadError as error:
            result = "failed"
            item.error_message = str(error)
            _log.warning("Podcast download failed for %s: %s", item.item_id, error)
        item.status = result
        with self._lock:
            self._active_count = max(0, self._active_count - 1)
        self._on_status_changed(item)
        if result == "completed":
            self._on_completed(item)
        self._wake.set()
