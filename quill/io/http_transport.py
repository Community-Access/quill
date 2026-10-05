"""HTTP/HTTPS transport for the enhanced ``file.open_url`` (issue #155).

The existing :meth:`MainFrame.open_url` decodes the body as raw UTF-8; this
transport is the supporting infrastructure for the new behaviour:

* Stream the response to a local temp file so binary formats (PDF, DOCX,
  images) are no longer corrupted by a forced ``str.decode``.
* Enforce a redirect cap (5) so a malicious server cannot loop the editor
  into a denial-of-service.
* Invoke a progress callback at ~20 Hz for the screen-reader progress
  dialog (handled by the dialog, not by this module).
* Infer a filename from the ``Content-Disposition`` header, then from the
  URL path, then fall back to ``untitled``.
* Ask before downloading (2026-10-04): ``confirm`` is called with the host,
  the file name and the size the server gave, after the headers arrive and
  before a byte of the body is read. ``False`` stops it. The user guide had
  promised this question for a year before the code asked it.
* Stop when asked: ``should_cancel`` is polled between chunks, and a stopped,
  refused or failed download removes its temp file rather than leaving a
  partial copy behind.

The download is then handed to :func:`quill.io.open_read.read_open_document`
which performs the actual format detection (PDF, RTF, DOCX, plain text,
markdown, ...). The "from URL" tab is also tagged so the title bar reads
``"name (from URL)"`` and the save flow is replaced with a "Save Copy to
Local File..." menu (see :mod:`quill.core.feature_command_map`).
"""

from __future__ import annotations

import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from quill.core.net import verified_ssl_context
from quill.io.remote_transport import (
    ProgressCallback,
    RemoteAuthError,
    RemoteNotFoundError,
    RemoteTransportError,
    merge_headers,
)

_MAX_REDIRECTS = 5
_MAX_BYTES = 256 * 1024 * 1024  # 256 MiB cap; matches the S3 transport.

# Conservative defaults: most servers happily serve 8 MiB chunks, and we want
# to keep memory pressure low on the worker thread that hosts the download.
_CHUNK_SIZE = 64 * 1024

#: Every download's temp file starts with this, so a sweep can find the ones a
#: closed tab or a crash left behind (:func:`sweep_stale_downloads`).
TEMP_PREFIX = "quill-url-"

#: ``confirm(host, filename, size)``; ``size`` is ``None`` when the server did
#: not say. Return ``False`` to stop before the body is read.
ConfirmCallback = Callable[[str, str, "int | None"], bool]


class DownloadCancelledError(RemoteTransportError):
    """The person said no to the download, or stopped it part way."""

    code = "QUILL-IO-REMOTE-DOWNLOAD-CANCELLED"


_FILENAME_DISPOSITION = re.compile(
    r"""filename\*?=(?:
        UTF-8''(?P<utf8>[^;]+)
        |
        "(?P<quoted>[^"]+)"
        |
        (?P<bare>[^;]+)
    )""",
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(slots=True)
class HttpDownload:
    """The outcome of a successful :func:`download_url` call."""

    local_path: str
    size: int
    mime_type: str
    filename: str
    elapsed_ms: int
    final_url: str
    headers: dict[str, str]


def download_url(
    url: str,
    *,
    timeout: float = 30.0,
    progress: ProgressCallback | None = None,
    max_bytes: int = _MAX_BYTES,
    confirm: ConfirmCallback | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> HttpDownload:
    """Stream ``url`` to a local temp file and return a :class:`HttpDownload`.

    The caller owns the returned ``local_path`` and removes it with
    :func:`discard_download` once the document is read. The
    :func:`quill.io.open_read.read_open_document` entry point handles the
    format detection on that file. Raises :class:`DownloadCancelledError` when
    ``confirm`` says no or ``should_cancel`` says stop.
    """

    if not url:
        raise RemoteTransportError("URL is empty")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise RemoteTransportError(f"Unsupported URL scheme: {parsed.scheme!r}")
    start = time.monotonic()
    current_url = url
    visited_hosts: set[str] = {parsed.hostname or ""}
    last_headers: dict[str, str] = {}
    request_headers = {"User-Agent": "QUILL/1.0", "Accept": "*/*"}
    for redirect_index in range(_MAX_REDIRECTS + 1):
        request = urllib.request.Request(current_url, headers=request_headers)
        try:
            response = urllib.request.urlopen(
                request,
                timeout=timeout,
                context=verified_ssl_context(),
            )
        except urllib.error.HTTPError as exc:
            status = int(exc.code or 0)
            message = exc.reason or f"HTTP {status}"
            if status in (401, 403):
                raise RemoteAuthError(f"HTTP {status}: {message}") from exc
            if status == 404:
                raise RemoteNotFoundError(f"HTTP 404: {message}") from exc
            raise RemoteTransportError(f"HTTP {status}: {message}") from exc
        except urllib.error.URLError as exc:
            raise RemoteTransportError(f"GET {current_url} failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RemoteTransportError(f"GET {current_url} timed out") from exc
        with response:
            if response.status in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    raise RemoteTransportError("Server returned a redirect with no Location header")
                if redirect_index >= _MAX_REDIRECTS:
                    raise RemoteTransportError(f"Too many redirects (>{_MAX_REDIRECTS})")
                next_url = urllib.parse.urljoin(current_url, location)
                next_parsed = urllib.parse.urlparse(next_url)
                next_host = next_parsed.hostname or ""
                if next_host and next_host not in visited_hosts:
                    visited_hosts.add(next_host)
                current_url = next_url
                continue
            last_headers = merge_headers(response.headers.items())
            mime_type = last_headers.get("Content-Type", "") or ""
            filename = _infer_filename(current_url, last_headers)
            total_header = last_headers.get("Content-Length")
            try:
                total = int(total_header) if total_header else None
            except ValueError:
                total = None
            if total is not None and total > max_bytes:
                raise RemoteTransportError(
                    f"Remote file is {total} bytes; QUILL refuses downloads larger than {max_bytes}"
                )
            if confirm is not None:
                host = urllib.parse.urlparse(current_url).hostname or ""
                if not confirm(host, filename, total):
                    raise DownloadCancelledError("Download declined")
            local_path = _alloc_temp_path(filename)
            try:
                with open(local_path, "wb") as dest:
                    written = _stream_to_file(
                        response,
                        dest,
                        total=total,
                        progress=progress,
                        max_bytes=max_bytes,
                        should_cancel=should_cancel,
                    )
            except BaseException:
                discard_download(local_path)
                raise
            return HttpDownload(
                local_path=local_path,
                size=written,
                mime_type=mime_type,
                filename=filename,
                elapsed_ms=int((time.monotonic() - start) * 1000),
                final_url=current_url,
                headers=last_headers,
            )
    raise RemoteTransportError(f"Too many redirects (>{_MAX_REDIRECTS})")


def _stream_to_file(
    response: IO[bytes],
    dest: IO[bytes],
    *,
    total: int | None,
    progress: ProgressCallback | None,
    max_bytes: int,
    should_cancel: Callable[[], bool] | None = None,
) -> int:
    """Drain ``response`` into ``dest`` with progress + a hard byte cap."""

    written = 0
    while True:
        if should_cancel is not None and should_cancel():
            raise DownloadCancelledError("Download cancelled")
        try:
            chunk = response.read(_CHUNK_SIZE)
        except (OSError, TimeoutError) as exc:
            raise RemoteTransportError(f"Download interrupted: {exc}") from exc
        if not chunk:
            break
        written += len(chunk)
        if written > max_bytes:
            raise RemoteTransportError(f"Remote file exceeds {max_bytes} bytes; download aborted")
        dest.write(chunk)
        if progress is not None:
            progress(written, total)
    return written


def _infer_filename(url: str, headers: dict[str, str]) -> str:
    """Best-effort filename for the title bar and the temp file path."""

    disposition = headers.get("Content-Disposition", "")
    if disposition:
        match = _FILENAME_DISPOSITION.search(disposition)
        if match is not None:
            raw = match.group("utf8") or match.group("quoted") or match.group("bare")
            if raw:
                try:
                    from urllib.parse import unquote

                    return _safe_filename(unquote(raw.strip().strip('"')))
                except ValueError:
                    pass
    parsed = urllib.parse.urlparse(url)
    tail = parsed.path.rsplit("/", 1)[-1] if parsed.path else ""
    if tail:
        return _safe_filename(urllib.parse.unquote(tail))
    return "untitled"


def _safe_filename(name: str) -> str:
    cleaned = "".join(character for character in name if character not in '<>:"/\\|?*\0')
    cleaned = cleaned.strip().rstrip(".") or "untitled"
    return cleaned[:120]


def _alloc_temp_path(filename: str) -> str:
    base = _safe_filename(filename)
    suffix = os.path.splitext(base)[1] or ""
    fd, path = tempfile.mkstemp(prefix=TEMP_PREFIX, suffix=suffix)
    os.close(fd)
    return path


def discard_download(local_path: str | Path) -> None:
    """Remove a download's temp file; quietly, because it is only tidying.

    Refuses anything that is not one of ours -- a name that does not start
    with :data:`TEMP_PREFIX` -- so a wrong path can never delete a document.
    """
    path = Path(local_path)
    if not path.name.startswith(TEMP_PREFIX):
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def sweep_stale_downloads(
    *, directory: str | Path | None = None, older_than_seconds: float = 24 * 3600
) -> int:
    """Remove download temp files older than a day; returns how many went.

    The tab that owned one removes it when it closes; this catches the ones a
    crash or an exit with tabs still open left behind. Run at the start of the
    next Open from URL, so nothing runs for somebody who never uses it.
    """
    folder = Path(directory) if directory is not None else Path(tempfile.gettempdir())
    cutoff = time.time() - older_than_seconds
    removed = 0
    try:
        candidates = list(folder.glob(f"{TEMP_PREFIX}*"))
    except OSError:
        return 0
    for candidate in candidates:
        try:
            if candidate.is_file() and candidate.stat().st_mtime < cutoff:
                candidate.unlink()
                removed += 1
        except OSError:
            continue
    return removed
