"""Abstract base class and shared types for the remote file transports.

Four transport implementations live next to this file:

* :mod:`quill.io.ftp_transport`      — FTP via :mod:`ftplib`.
* :mod:`quill.io.sftp_transport`     — SFTP via :mod:`paramiko`.
* :mod:`quill.io.webdav_transport`   — WebDAV via :mod:`urllib` + :mod:`xml.etree`.
* :mod:`quill.io.s3_transport`       — S3 (object storage) via boto3 with a
                                       manual SigV4 fallback.

The transports all conform to :class:`RemoteTransport`. They are not used for
inline editing (that is File > SSH; see :mod:`quill.core.ssh.client`); they
are a *convenience retrieval path*. The transport is expected to copy bytes
between the remote host and a local :class:`tempfile.NamedTemporaryFile`, and
the higher-level :mod:`quill.io.open_read` pipeline is what understands the
resulting format. That keeps the editor's format-detection logic, the undo
stack, and the recovery layer all on a single code path.

Threading: every transport method is synchronous and meant to be called from
a background thread inside :class:`quill.stability.task_manager.QuillTaskManager`.
Progress callbacks (when supplied) are invoked on the same worker thread;
callers that want to update wx widgets must marshal the result through
``wx.CallAfter``.
"""

from __future__ import annotations

import io
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from quill.core.error_codes import CodedError

ProgressCallback = Callable[[int, int | None], None]
"""``(bytes_so_far, total_bytes_or_none)`` callback.

``total_bytes`` is ``None`` when the transport does not know the size up front
(e.g. an S3 server that returns no ``Content-Length`` on a ranged GET).
"""


class RemoteTransportError(CodedError):
    """Base class for all transport-layer errors (connection, auth, IO).

    The editor's "Open from Remote" path catches this class to surface a
    single screen-reader-friendly message ("Could not connect to ``host``,
    reason: <error>") without leaking stack traces.
    """

    code = "QUILL-IO-REMOTE-TRANSPORT"


class RemoteAuthError(RemoteTransportError):
    """Raised on 401, 403, AUTH failure, or S3 SignatureDoesNotMatch."""


class RemoteNotFoundError(RemoteTransportError):
    """Raised on 404 / ``NoSuchFile`` / ``NoSuchKey``."""


@dataclass(slots=True)
class RemoteEntry:
    """A single directory entry returned by :meth:`RemoteTransport.list_dir`.

    Mirrors :class:`quill.core.ssh.client.RemoteEntry` so the file-tree
    dialog UI does not have to special-case transports; the only difference
    is that the ``size`` field is set when the transport knows it (always for
    S3, sometimes for FTP, never for WebDAV ``PROPFIND`` without a separate
    ``GET``).
    """

    name: str
    is_dir: bool
    size: int = 0
    modified: float = 0.0  # POSIX timestamp; 0 when unknown
    mime_type: str = ""

    def to_display(self) -> str:
        """Return the human-readable string for a listbox row."""

        if self.is_dir:
            return f"[{self.name}]"
        return self.name


@dataclass(slots=True)
class DownloadResult:
    """Outcome of a :meth:`RemoteTransport.download` call.

    ``path`` is the *local* file the transport wrote to. Callers are expected
    to feed it straight into :func:`quill.io.open_read.read_open_document`.
    The transport does not own this file; the caller is responsible for
    unlinking it (or moving it to a managed temp dir).
    """

    path: str
    size: int
    mime_type: str = ""
    elapsed_ms: int = 0
    headers: dict[str, str] = field(default_factory=dict)


class RemoteTransport(ABC):
    """The cross-protocol transport contract.

    Implementations must be safe to construct in the background thread that
    will use them. They do not need to be safe to share across threads.
    """

    @abstractmethod
    def list_dir(self, path: str) -> list[RemoteEntry]:
        """Return the directory entries under ``path`` (empty list on root)."""

    @abstractmethod
    def download(
        self,
        remote_path: str,
        local_path: str,
        *,
        progress: ProgressCallback | None = None,
    ) -> DownloadResult:
        """Copy ``remote_path`` to ``local_path`` and return a :class:`DownloadResult`."""

    @abstractmethod
    def upload(
        self,
        local_path: str,
        remote_path: str,
        *,
        progress: ProgressCallback | None = None,
    ) -> DownloadResult:
        """Copy ``local_path`` to ``remote_path`` and return a :class:`DownloadResult`."""

    @abstractmethod
    def close(self) -> None:
        """Release any held sockets or sessions. Idempotent."""

    # --- context manager glue ------------------------------------------------

    def __enter__(self) -> RemoteTransport:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


# --- shared helpers ---------------------------------------------------------


def chunked_copy(
    source: io.RawIOBase | io.BufferedIOBase,
    dest: io.RawIOBase | io.BufferedIOBase,
    *,
    total: int | None,
    chunk_size: int = 64 * 1024,
    progress: ProgressCallback | None = None,
) -> int:
    """Copy ``source`` to ``dest`` honouring ``progress``.

    Returns the number of bytes copied. The transport progress is updated on
    every chunk; callers should treat the callback as advisory (it runs on a
    background thread, so it must marshal any UI work via ``wx.CallAfter``).
    """

    written = 0
    last_report = 0.0
    while True:
        chunk = source.read(chunk_size)
        if not chunk:
            break
        dest.write(chunk)
        written += len(chunk)
        if progress is not None:
            # Throttle the callback to roughly 20 Hz so we do not flood the
            # event queue on fast networks. The cost of missing an update is
            # purely cosmetic; the byte count is still accurate.
            now = time.monotonic()
            if now - last_report >= 0.05 or (total is not None and written >= total):
                progress(written, total)
                last_report = now
    return written


def merge_headers(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    """Coerce an iterable of ``(name, value)`` pairs into a case-preserved dict."""

    merged: dict[str, str] = {}
    for name, value in headers:
        if not name:
            continue
        merged[str(name)] = str(value)
    return merged
