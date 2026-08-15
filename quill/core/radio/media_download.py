"""Saving a recording to a file -- one chapter, or a whole book.

:mod:`quill.core.radio.downloadable` decides *whether* something may be saved.
This does the saving, and it is written around the case that actually matters:
**a book is not one file.** A LibriVox novel is forty chapters, each its own
address, and "download this book" means forty transfers that must survive a
dropped connection, be stoppable halfway, and report progress in a way somebody
listening can follow.

The design, in four decisions:

* **One chapter at a time, in order.** Not four at once. A parallel fetch is
  faster on a good connection and is a worse citizen on somebody else's free
  library -- and these are all free libraries, run on donations. Order also means
  a part-finished book is the *first* N chapters, which is a book you can start
  listening to, rather than a scattering you cannot.
* **Resumable, because a long book will be interrupted.** A partial file is kept
  and the next attempt asks for the rest with a Range header. A forty-chapter
  book over a domestic connection is a real risk of losing an hour's transfer to
  one blip.
* **Cancel is checked inside the read loop**, not between files, so stopping a
  book stops within a chunk rather than at the end of a 90 MB chapter.
* **Progress is counted in chapters, not bytes.** "Chapter 12 of 40" is something
  a person can hold; "43.7 megabytes" is not, and a percentage of an unknown
  total is a number the code does not actually have.

Nothing here decides rights, and nothing here touches wx. The single HTTPS
egress site is :func:`_fetch_to_file`, reviewed in the network egress audit.

wx-free, strict-typed.
"""

from __future__ import annotations

import ssl
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError

_USER_AGENT = "Quill Radio"
_TIMEOUT_SECONDS = 30.0
_CHUNK_BYTES = 256 * 1024

#: A cap on one file, so a mislabelled address cannot fill somebody's disk.
#: Generous: an unabridged audiobook chapter is routinely 80-100 MB.
MAX_FILE_BYTES = 2_000_000_000


class DownloadError(CodedError):
    """A download could not be completed."""

    code = "QUILL-RADIO-DOWNLOAD-FAILED"


@dataclass(slots=True)
class BookProgress:
    """How far through a multi-part download we are, in speakable terms."""

    done: int = 0
    total: int = 0
    current: str = ""
    #: Files that failed, by name, so the summary can be honest rather than
    #: reporting a success that skipped four chapters.
    failed: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return self.total > 0 and self.done >= self.total

    def spoken(self) -> str:
        """ "Chapter 12 of 40." -- what a listener actually wants to hear."""
        if not self.total:
            return "Nothing to download."
        if self.is_complete and not self.failed:
            return f"Downloaded all {self.total}."
        return f"{self.done} of {self.total}."


def _fetch_to_file(
    url: str,
    destination: Path,
    *,
    cancel: threading.Event | None = None,
    on_bytes: Callable[[int], None] | None = None,
) -> Path:
    """One resumable HTTPS GET into *destination* -- the reviewed egress site.

    Reads in bounded chunks so a cancel takes effect inside a file rather than
    only between files.
    """
    if not url.lower().startswith(("https://", "http://")):
        raise DownloadError("Only web addresses can be downloaded.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # A destination that already exists is complete: files only ever arrive via
    # ``partial.replace``, so there is no half-written state to distrust. This
    # is what makes re-queueing a stopped book *resume* -- the saved chapters
    # answer instantly instead of transferring again, which the queue's closing
    # message promises out loud.
    try:
        if destination.is_file() and destination.stat().st_size > 0:
            return destination
    except OSError:
        pass
    partial = destination.with_suffix(destination.suffix + ".part")
    resume_from = partial.stat().st_size if partial.exists() else 0

    headers = {"User-Agent": _USER_AGENT}
    if resume_from:
        headers["Range"] = f"bytes={resume_from}-"
    request = urllib.request.Request(url, headers=headers)
    context = ssl.create_default_context()

    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            # 206 means the server honoured the Range; 200 means it ignored it
            # and is sending the whole file, so the partial must be discarded
            # rather than appended to -- which would corrupt it silently.
            resumed = bool(resume_from) and int(getattr(resp, "status", 200)) == 206
            mode = "ab" if resumed else "wb"
            written = resume_from if resumed else 0
            with partial.open(mode) as handle:
                while True:
                    if cancel is not None and cancel.is_set():
                        raise DownloadError("Download stopped.")
                    chunk = resp.read(_CHUNK_BYTES)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_FILE_BYTES:
                        raise DownloadError("That file is larger than Quill Radio will download.")
                    handle.write(chunk)
                    if on_bytes is not None:
                        on_bytes(written)
    except DownloadError:
        raise
    except urllib.error.HTTPError as error:
        # 416: the Range asked for bytes past the end, meaning the partial
        # already holds the whole file -- a transfer that finished writing and
        # was interrupted before the rename. Without this, every retry asks the
        # same impossible Range and the file is stuck failing forever.
        if error.code == 416 and resume_from:
            partial.replace(destination)
            return destination
        raise DownloadError(f"Could not download that file: {error}") from error
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        # The partial is deliberately left in place: the next attempt resumes
        # from it, which is the whole point of writing to one.
        raise DownloadError(f"Could not download that file: {error}") from error

    partial.replace(destination)
    return destination


def download_one(
    station: Any,
    folder: Path | str,
    *,
    cancel: threading.Event | None = None,
) -> Path:
    """Save one recording. Raises :class:`DownloadError` with a spoken reason.

    The rights check happens here as well as in the menu, because a menu item is
    a convenience and this is the boundary: nothing reaches the network until
    :mod:`downloadable` has said yes.
    """
    from quill.core.radio import downloadable

    decision = downloadable.can_download(station)
    if not decision.allowed:
        raise DownloadError(decision.reason)
    url = str(getattr(station, "stream_url", ""))
    target = Path(folder) / downloadable.suggested_filename(station, url=url)
    written = _fetch_to_file(url, target, cancel=cancel)
    _write_licence(station, written)
    return written


def _write_licence(station: Any, audio: Path) -> None:
    """Drop the licence beside the file, where the row carries one.

    Saving Creative Commons audio and discarding its terms strips exactly the
    information the licence exists to travel with. A plain text file beside the
    audio is the least it can do and needs nothing to read it.
    """
    from quill.core.radio import downloadable

    licence = downloadable.licence_note(station)
    if not licence:
        return
    try:
        audio.with_suffix(audio.suffix + ".licence.txt").write_text(
            f"{getattr(station, 'name', '')}\n{licence}\n{getattr(station, 'homepage', '')}\n",
            encoding="utf-8",
        )
    except OSError:
        # A licence note that cannot be written must never cost somebody the
        # audio they already downloaded.
        return


def download_book(
    chapters: Sequence[Any],
    folder: Path | str,
    *,
    cancel: threading.Event | None = None,
    on_progress: Callable[[BookProgress], None] | None = None,
) -> BookProgress:
    """Save a whole book, chapter by chapter, in order. Never raises.

    One chapter failing does not stop the rest -- forty chapters and one bad
    address should leave you thirty-nine chapters and an honest count, not an
    error and nothing. The failures are named in the result so the summary can
    say which.
    """
    progress = BookProgress(total=len(chapters))
    destination = Path(folder)
    for chapter in chapters:
        if cancel is not None and cancel.is_set():
            break
        progress.current = str(getattr(chapter, "name", "") or "")
        if on_progress is not None:
            on_progress(progress)
        try:
            download_one(chapter, destination, cancel=cancel)
            progress.done += 1
        except DownloadError:
            if cancel is not None and cancel.is_set():
                break
            progress.failed.append(progress.current or "one chapter")
        if on_progress is not None:
            on_progress(progress)
    progress.current = ""
    return progress


def summarise(progress: BookProgress, *, stopped: bool = False) -> str:
    """What to say when a book download ends, however it ended."""
    if not progress.total:
        return "There was nothing to download."
    if stopped:
        return f"Download stopped. {progress.done} of {progress.total} saved."
    if progress.failed:
        count = len(progress.failed)
        return (
            f"Downloaded {progress.done} of {progress.total}. "
            f"{count} could not be downloaded: {', '.join(progress.failed[:3])}."
        )
    return f"Downloaded all {progress.total}."
