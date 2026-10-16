"""A compact Auphonic post-production client (upload, poll, fetch results).

Auphonic (auphonic.com) is an audio post-production service podcasters and
audiobook narrators use for leveling, noise reduction, and encoding. QUILL's
client covers the practical loop through Auphonic's "simple API": list the
account's presets, upload a finished master and start a production, poll until
it is done, and download the results.

Privacy/consent: everything requires the user's own API token (stored in the
Windows Credential Manager under :data:`CREDENTIAL_TARGET`, never in settings)
and runs only from the explicit publish dialog, which names the service and is
absent in Safe Mode. All calls funnel through the two reviewed egress sites
below (HTTPS-only, verified TLS, bounded timeouts) — see
``quill/tools/network_egress_audit.py``. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context

API_BASE = "https://auphonic.com/api"
#: Windows Credential Manager target for the user's Auphonic API token.
CREDENTIAL_TARGET = "quill:publish:auphonic"
_TIMEOUT_SECONDS = 60.0
#: Production statuses that mean "finished" (3 = Done per Auphonic's API docs).
DONE_STATUS = 3
ERROR_STATUS = 2


class AuphonicError(CodedError):
    """An Auphonic call failed; the message is speakable."""

    code = "QUILL-PUBLISH-AUPHONIC-FAILED"


class AuphonicCancelled(AuphonicError):
    """The user cancelled mid-transfer; nothing more was sent or fetched."""


#: How much body is handed to the socket per read when streaming an upload.
_UPLOAD_BLOCK = 64 * 1024
#: How much response body is read per chunk when streaming a download.
_DOWNLOAD_BLOCK = 64 * 1024


class _ProgressReader:
    """File-like upload body: reports progress, honors cancel, never loads it all.

    ``urllib`` hands file-like ``data`` to ``http.client``, which streams it
    with repeated ``read()`` calls — so every block is a chance to report
    bytes sent and to abort. The body is a sequence of parts, each either
    bytes or an open binary file, read in turn: an hour of WAV goes up a block
    at a time instead of being held in memory twice (2026-10-15). The caller
    sets Content-Length from :attr:`total`.
    """

    def __init__(
        self,
        parts: bytes | list[bytes | BinaryIO],
        on_bytes: Callable[[int, int], None] | None,
        is_cancelled: Callable[[], bool] | None,
        *,
        total: int | None = None,
    ) -> None:
        self._parts: list[bytes | BinaryIO] = [parts] if isinstance(parts, bytes) else parts
        self.total = (
            total if total is not None else sum(len(p) for p in self._parts if isinstance(p, bytes))
        )
        self._index = 0
        self._offset = 0
        self._sent = 0
        self._on_bytes = on_bytes
        self._is_cancelled = is_cancelled

    def read(self, size: int = -1) -> bytes:
        if self._is_cancelled is not None and self._is_cancelled():
            raise AuphonicCancelled("Cancelled — the Auphonic upload was stopped.")
        if size is None or size < 0:
            size = max(self.total - self._sent, 0)
        out = bytearray()
        while len(out) < size and self._index < len(self._parts):
            part = self._parts[self._index]
            want = size - len(out)
            if isinstance(part, bytes):
                chunk = part[self._offset : self._offset + want]
                self._offset += len(chunk)
                exhausted = self._offset >= len(part)
            else:
                chunk = part.read(want)
                exhausted = not chunk
            out.extend(chunk)
            if exhausted:
                self._index += 1
                self._offset = 0
        self._sent += len(out)
        if out and self._on_bytes is not None:
            self._on_bytes(self._sent, self.total)
        return bytes(out)


@dataclass(slots=True)
class Preset:
    """One saved Auphonic preset."""

    uuid: str
    name: str


@dataclass(slots=True)
class AccountInfo:
    """The account behind the token: who, and how many credits remain."""

    username: str
    credits: float


@dataclass(slots=True)
class ProductionStatus:
    """A production's progress snapshot."""

    uuid: str
    status: int
    status_string: str
    output_files: list[dict[str, object]] = field(default_factory=list)

    @property
    def done(self) -> bool:
        return self.status == DONE_STATUS

    @property
    def failed(self) -> bool:
        return self.status == ERROR_STATUS


def _request(
    url: str,
    token: str,
    *,
    data: bytes | _ProgressReader | None = None,
    content_type: str = "",
    on_bytes: Callable[[int, int], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    sink: BinaryIO | None = None,
) -> bytes:
    """One authenticated HTTPS exchange — the reviewed JSON egress site.

    ``on_bytes(done, total)`` reports upload progress when *data* is given and
    download progress otherwise; ``is_cancelled`` aborts between blocks with
    :class:`AuphonicCancelled`. With *sink*, a download is written to it block
    by block and ``b""`` is returned, so a large file is never held in memory.
    """
    if not url.startswith("https://"):
        raise AuphonicError("Refusing a non-HTTPS Auphonic request.")
    headers = {"User-Agent": http_client.user_agent(), "Authorization": f"Bearer {token}"}
    if content_type:
        headers["Content-Type"] = content_type
    body: bytes | _ProgressReader | None = data
    if isinstance(data, _ProgressReader):
        headers["Content-Length"] = str(data.total)
    elif data is not None and (on_bytes is not None or is_cancelled is not None):
        # Streamed upload: http.client reads the file-like body in blocks, so
        # progress and cancel get a look-in on every block. Content-Length is
        # required when the body has no len().
        headers["Content-Length"] = str(len(data))
        body = _ProgressReader(data, on_bytes, is_cancelled)
    request = urllib.request.Request(url, data=body, headers=headers)
    context = verified_ssl_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            if data is None and (
                sink is not None or on_bytes is not None or is_cancelled is not None
            ):
                total = int(resp.headers.get("Content-Length") or 0)
                received = bytearray()
                count = 0
                while True:
                    if is_cancelled is not None and is_cancelled():
                        raise AuphonicCancelled("Cancelled — the Auphonic download was stopped.")
                    chunk = resp.read(_DOWNLOAD_BLOCK)
                    if not chunk:
                        break
                    count += len(chunk)
                    if sink is not None:
                        sink.write(chunk)
                    else:
                        received.extend(chunk)
                    if on_bytes is not None:
                        on_bytes(count, total)
                return bytes(received)
            return bytes(resp.read())
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            body = json.loads(error.read().decode("utf-8"))
            detail = str(body.get("error_message", "")) if isinstance(body, dict) else ""
        except Exception:  # noqa: BLE001
            pass
        raise AuphonicError(detail or f"Auphonic said {error.code}: {error.reason}") from error
    except (urllib.error.URLError, TimeoutError, ssl.SSLError) as error:
        raise AuphonicError(f"Could not reach Auphonic: {error}") from error


def _json(
    url: str,
    token: str,
    *,
    data: bytes | _ProgressReader | None = None,
    content_type: str = "",
    on_bytes: Callable[[int, int], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> dict[str, object]:
    payload = _request(
        url,
        token,
        data=data,
        content_type=content_type,
        on_bytes=on_bytes,
        is_cancelled=is_cancelled,
    )
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except ValueError as error:
        raise AuphonicError("Auphonic returned an unexpected response.") from error
    return parsed if isinstance(parsed, dict) else {}


def list_presets(token: str) -> list[Preset]:
    """The account's saved presets (name + uuid)."""
    data = _json(f"{API_BASE}/presets.json", token)
    presets: list[Preset] = []
    entries = data.get("data")
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, dict) and entry.get("uuid"):
            presets.append(Preset(uuid=str(entry["uuid"]), name=str(entry.get("preset_name", ""))))
    return presets


def account_info(token: str) -> AccountInfo:
    """The account's username and remaining credits (shown before submitting)."""
    data = _json(f"{API_BASE}/user.json", token)
    user = data.get("data")
    if not isinstance(user, dict):
        raise AuphonicError("Auphonic returned an unexpected response.")
    try:
        credits = float(user.get("credits", 0.0) or 0.0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        credits = 0.0
    return AccountInfo(username=str(user.get("username", "")), credits=credits)


def _multipart(fields: dict[str, str], file_field: str, path: Path) -> tuple[bytes, str]:
    """Encode *fields* + one file as multipart/form-data (pure; unit-tested)."""
    boundary = f"----quill-{uuid.uuid4().hex}"
    lines: list[bytes] = []
    for key, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        lines.append(f"{value}\r\n".encode())
    lines.append(f"--{boundary}\r\n".encode())
    lines.append(
        f'Content-Disposition: form-data; name="{file_field}"; '
        f'filename="{path.name}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n".encode()
    )
    lines.append(path.read_bytes())
    lines.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(lines), f"multipart/form-data; boundary={boundary}"


def _multipart_parts(
    fields: dict[str, str], file_field: str, path: Path, handle: BinaryIO
) -> tuple[list[bytes | BinaryIO], int, str]:
    """The same multipart body as :func:`_multipart`, as parts to stream.

    Returns ``(parts, total_length, content_type)``; the file is read from
    *handle* as it is sent, and its size comes from the file system.
    """
    boundary = f"----quill-{uuid.uuid4().hex}"
    head: list[bytes] = []
    for key, value in fields.items():
        head.append(f"--{boundary}\r\n".encode())
        head.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        head.append(f"{value}\r\n".encode())
    head.append(f"--{boundary}\r\n".encode())
    head.append(
        f'Content-Disposition: form-data; name="{file_field}"; '
        f'filename="{path.name}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n".encode()
    )
    opening = b"".join(head)
    closing = f"\r\n--{boundary}--\r\n".encode()
    total = len(opening) + path.stat().st_size + len(closing)
    return [opening, handle, closing], total, f"multipart/form-data; boundary={boundary}"


def start_production(
    token: str,
    path: Path,
    *,
    title: str = "",
    preset_uuid: str = "",
    on_progress: Callable[[str], None] | None = None,
    on_bytes: Callable[[int, int], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> str:
    """Upload *path* and start a production via the simple API; returns its uuid.

    ``on_bytes(sent, total)`` reports upload bytes; ``is_cancelled`` aborts the
    upload between blocks with :class:`AuphonicCancelled`.
    """
    fields: dict[str, str] = {"action": "start", "title": title or path.stem}
    if preset_uuid:
        fields["preset"] = preset_uuid
    if on_progress is not None:
        on_progress(f"Uploading {path.name} to Auphonic...")
    with path.open("rb") as handle:
        parts, total, content_type = _multipart_parts(fields, "input_file", path, handle)
        data = _json(
            f"{API_BASE}/simple/productions.json",
            token,
            data=_ProgressReader(parts, on_bytes, is_cancelled, total=total),
            content_type=content_type,
        )
    production = data.get("data")
    if not isinstance(production, dict) or not production.get("uuid"):
        raise AuphonicError("Auphonic did not accept the upload.")
    return str(production["uuid"])


def production_status(token: str, production_uuid: str) -> ProductionStatus:
    """The current status of a production."""
    data = _json(f"{API_BASE}/production/{production_uuid}.json", token)
    production = data.get("data")
    if not isinstance(production, dict):
        raise AuphonicError("Auphonic returned an unexpected response.")
    outputs = production.get("output_files")
    return ProductionStatus(
        uuid=production_uuid,
        status=int(production.get("status", -1) or -1),
        status_string=str(production.get("status_string", "")),
        output_files=[o for o in outputs if isinstance(o, dict)]
        if isinstance(outputs, list)
        else [],
    )


def download_results(
    token: str,
    status: ProductionStatus,
    out_dir: Path,
    *,
    on_progress: Callable[[str], None] | None = None,
    on_bytes: Callable[[str, int, int], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> list[Path]:
    """Download a finished production's output files into *out_dir*.

    ``on_bytes(filename, done, total)`` reports download bytes per file;
    ``is_cancelled`` aborts between blocks with :class:`AuphonicCancelled`.

    Each file streams to ``<name>.part`` and only then takes its name, and a
    name already in the folder is never overwritten: the new file becomes
    "name (2).ext" (2026-10-15). A cancelled or failed download leaves no
    partial file. The server's name is used only as a bare file name, so it
    cannot place a file outside *out_dir*.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for output in status.output_files:
        url = str(output.get("download_url", ""))
        filename = _safe_name(str(output.get("filename", "")) or url.rsplit("/", 1)[-1])
        if not url or not filename:
            continue
        if on_progress is not None:
            on_progress(f"Downloading {filename}...")
        per_file = (
            None
            if on_bytes is None
            else (lambda done, total, _name=filename: on_bytes(_name, done, total))
        )
        target = _unused_path(out_dir / filename)
        partial = target.with_name(target.name + ".part")
        try:
            with partial.open("wb") as sink:
                _request(url, token, on_bytes=per_file, is_cancelled=is_cancelled, sink=sink)
            final = _unused_path(target)  # again: another file may have arrived
            os.replace(partial, final)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        written.append(final)
    return written


def _safe_name(name: str) -> str:
    """The last part of *name* only: never a path the server chose."""
    return PurePosixPath(name.replace("\\", "/")).name.strip().lstrip(".")


def _unused_path(path: Path) -> Path:
    """*path*, or "name (2).ext", "name (3).ext"... when it already exists."""
    if not path.exists():
        return path
    for number in range(2, 10_000):
        candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise AuphonicError(f"Too many files called {path.name} in {path.parent}.")
