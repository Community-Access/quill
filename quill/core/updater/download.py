"""Downloading an update: resumable, checked against the signed list (plan 6.4).

* Bytes go to ``<name>.partial`` first. If the app closes half-way, the next
  attempt asks the server for the rest (an HTTP ``Range`` request) instead of
  starting again -- a 200 MB installer on a slow line should not have to be
  fetched from the top three times. Beside it, ``<name>.partial.sha256`` names
  the file those bytes belong to: every build of one version ships under the
  same file name (docs/release/RELEASE.md, "Build numbers"), and half of build
  1 must never be finished with the second half of build 2.
* When the last byte is in, the size and the SHA-256 **from the signed feed**
  are checked before the file gets its real name. A mismatch deletes the file
  and raises; an installer that will run elevated is never kept on trust.
* Before starting, free space is compared with two and a half times the size
  (the download, unpacking it, and the copy being replaced) and a plain
  sentence says so when there is not enough.

The metered-connection, quiet-hours and recording rules for *automatic*
downloads live in :mod:`quill.core.updater.background`; a download somebody
asked for always goes ahead.

wx-free and strict-typed. Every network and disk touch can be passed in.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from quill.core.error_codes import CodedError

__all__ = [
    "SPACE_FACTOR",
    "DownloadVerifyError",
    "NotEnoughSpaceError",
    "download_verified",
    "space_needed",
]

#: Download, unpack, and the copy it replaces.
SPACE_FACTOR = 2.5
_CHUNK = 64 * 1024


class DownloadVerifyError(CodedError):
    """The downloaded file did not match the signed list; it was deleted."""

    code = "QUILL-UPDATE-DOWNLOAD-MISMATCH"


class NotEnoughSpaceError(CodedError):
    """Not enough free disk space to download and install the update."""

    code = "QUILL-UPDATE-DOWNLOAD-NO-SPACE"


class _Response(Protocol):
    status: int

    def read(self, size: int = -1) -> bytes: ...

    def close(self) -> None: ...


#: ``open_range(url, start)`` returns a response whose ``status`` is 206 when
#: it honoured the range and 200 when it is sending the whole file again.
RangeOpener = Callable[[str, int], _Response]


def space_needed(size: int) -> int:
    return int(size * SPACE_FACTOR)


def _megabytes(count: int) -> str:
    return f"{max(1, round(count / (1024 * 1024)))} MB"


def _default_opener(url: str, start: int) -> _Response:
    from urllib.request import Request, urlopen

    from quill.core.updates import _ssl_context, _validate_remote_url

    _validate_remote_url(url)
    headers = {"User-Agent": "QuillVille-Updater/2"}
    if start > 0:
        headers["Range"] = f"bytes={start}-"
    response = urlopen(Request(url, headers=headers), timeout=60, context=_ssl_context())
    return response  # type: ignore[no-any-return]


def _hash_file(path: Path) -> hashlib._Hash:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(block)
    return digest


def download_verified(
    url: str,
    dest: Path,
    *,
    sha256: str,
    size: int,
    open_range: RangeOpener | None = None,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    free_space: Callable[[Path], int] | None = None,
) -> Path:
    """Fetch *url* to *dest*, resuming a ``.partial``, and verify it. Returns *dest*.

    Raises :class:`NotEnoughSpaceError`, :class:`DownloadVerifyError`, or
    ``OSError`` for a network failure (the ``.partial`` is kept for next time).
    """
    expected = sha256.strip().lower()
    if not expected:
        raise DownloadVerifyError("there is no checksum to check this download against")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size == size:
        if hmac.compare_digest(_hash_file(dest).hexdigest(), expected):
            return dest
        dest.unlink(missing_ok=True)
    partial = dest.with_name(dest.name + ".partial")
    claim = dest.with_name(dest.name + ".partial.sha256")
    try:
        claimed = claim.read_text(encoding="ascii").strip().lower()
    except (OSError, UnicodeDecodeError):
        claimed = ""
    if claimed and claimed != expected:  # another build's bytes under this name
        partial.unlink(missing_ok=True)
    have = partial.stat().st_size if partial.is_file() else 0
    if size and have > size:
        partial.unlink(missing_ok=True)
        have = 0
    space = (free_space or (lambda p: shutil.disk_usage(p).free))(dest.parent)
    if size and space < space_needed(size) - have:
        raise NotEnoughSpaceError(
            f"There isn't enough free space to download this update. It needs about "
            f"{_megabytes(space_needed(size))}, and there is {_megabytes(space)} free."
        )
    claim.write_text(expected, encoding="ascii")
    response = (open_range or _default_opener)(url, have)
    try:
        if have and getattr(response, "status", 200) != 206:
            have = 0  # the server ignored the range: start again
        mode = "ab" if have else "wb"
        done = have
        with partial.open(mode) as handle:
            if progress is not None:
                progress(done, size)
            while True:
                if cancelled is not None and cancelled():
                    raise OSError("the download was cancelled")
                chunk = response.read(_CHUNK)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if progress is not None:
                    progress(done, size)
    finally:
        response.close()
    actual_size = partial.stat().st_size
    actual = _hash_file(partial).hexdigest()
    if (size and actual_size != size) or not hmac.compare_digest(actual, expected):
        partial.unlink(missing_ok=True)
        claim.unlink(missing_ok=True)
        raise DownloadVerifyError(
            "The downloaded update did not match the signed list of versions, so it was "
            "deleted. Nothing was installed. Try again later."
        )
    os.replace(partial, dest)
    claim.unlink(missing_ok=True)
    return dest
