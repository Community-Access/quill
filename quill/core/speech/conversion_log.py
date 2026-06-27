"""A small, wx-free diagnostic log for the batch document-to-speech run.

The batch export writes a human-readable log into the output folder (where the
audio lands) so a long, unattended conversion leaves a trail: what was found,
each document's progress and chapter count, timings, skips, errors, and the final
summary. The folder is ensured and the file is opened **before** conversion starts
(see :func:`open_conversion_log`), so the log exists even if the first step fails.

Strict-typed and dependency-free: it is opened on the UI thread and written from
the background task thread (a single writer), each line flushed so a crash still
leaves the progress on disk.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from types import TracebackType


def default_log_path(folder: Path, *, now: datetime | None = None) -> Path:
    """Return a timestamped log path inside *folder* (not yet created)."""
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return folder / f"quill-batch-speech-{stamp}.log"


class ConversionLog:
    """A timestamped, line-buffered text log opened before a conversion run.

    Use :func:`open_conversion_log` to create one. Every :meth:`log` line is
    prefixed with the seconds elapsed since the log opened and flushed to disk.
    Safe to use as a context manager; :meth:`close` is idempotent.
    """

    def __init__(self, path: Path, handle: object) -> None:
        self.path = path
        self._handle = handle
        self._start = time.monotonic()
        self._closed = False

    def log(self, message: str) -> None:
        """Append one timestamped line; never raises (logging must not break a run)."""
        if self._closed or self._handle is None:
            return
        elapsed = time.monotonic() - self._start
        line = f"[{elapsed:8.1f}s] {message}\n"
        try:
            self._handle.write(line)  # type: ignore[attr-defined]
            self._handle.flush()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - a failed log write must not abort the run
            pass

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._handle.close()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self) -> ConversionLog:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


def open_conversion_log(
    folder: Path, *, title: str = "Batch export to speech", now: datetime | None = None
) -> ConversionLog:
    """Create *folder* if needed, open a fresh log inside it, and write a header.

    Raises ``OSError`` if the folder cannot be created or the file cannot be
    opened, so the caller can fall back to a no-op log rather than crashing.
    """
    folder.mkdir(parents=True, exist_ok=True)
    path = default_log_path(folder, now=now)
    handle = path.open("w", encoding="utf-8")
    log = ConversionLog(path, handle)
    log.log(f"{title} — log opened {datetime.now().isoformat(timespec='seconds')}")
    log.log(f"Output folder: {folder}")
    return log


class NullConversionLog(ConversionLog):
    """A log that discards everything — used when the real log cannot be opened."""

    def __init__(self) -> None:
        super().__init__(Path(), None)

    def log(self, message: str) -> None:  # noqa: D401 - no-op
        return
