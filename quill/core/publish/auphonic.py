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
import ssl
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill import __version__

API_BASE = "https://auphonic.com/api"
#: Windows Credential Manager target for the user's Auphonic API token.
CREDENTIAL_TARGET = "quill:publish:auphonic"
_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 60.0
#: Production statuses that mean "finished" (3 = Done per Auphonic's API docs).
DONE_STATUS = 3
ERROR_STATUS = 2


class AuphonicError(RuntimeError):
    """An Auphonic call failed; the message is speakable."""


class AuphonicCancelled(AuphonicError):
    """The user cancelled mid-transfer; nothing more was sent or fetched."""


#: How much body is handed to the socket per read when streaming an upload.
_UPLOAD_BLOCK = 64 * 1024
#: How much response body is read per chunk when streaming a download.
_DOWNLOAD_BLOCK = 64 * 1024


class _ProgressReader:
    """File-like wrapper over an upload body: reports progress, honors cancel.

    ``urllib`` hands file-like ``data`` to ``http.client``, which streams it
    with repeated ``read()`` calls — so every block is a chance to report
    bytes sent and to abort. Content-Length is set by the caller, keeping the
    request identical on the wire to the plain-bytes form.
    """

    def __init__(
        self,
        body: bytes,
        on_bytes: Callable[[int, int], None] | None,
        is_cancelled: Callable[[], bool] | None,
    ) -> None:
        self._view = memoryview(body)
        self._total = len(body)
        self._sent = 0
        self._on_bytes = on_bytes
        self._is_cancelled = is_cancelled

    def read(self, size: int = -1) -> bytes:
        if self._is_cancelled is not None and self._is_cancelled():
            raise AuphonicCancelled("Cancelled — the Auphonic upload was stopped.")
        if size is None or size < 0:
            size = self._total - self._sent
        chunk = bytes(self._view[self._sent : self._sent + size])
        self._sent += len(chunk)
        if chunk and self._on_bytes is not None:
            self._on_bytes(self._sent, self._total)
        return chunk


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
    data: bytes | None = None,
    content_type: str = "",
    on_bytes: Callable[[int, int], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> bytes:
    """One authenticated HTTPS exchange — the reviewed JSON egress site.

    ``on_bytes(done, total)`` reports upload progress when *data* is given and
    download progress otherwise; ``is_cancelled`` aborts between blocks with
    :class:`AuphonicCancelled`.
    """
    if not url.startswith("https://"):
        raise AuphonicError("Refusing a non-HTTPS Auphonic request.")
    headers = {"User-Agent": _USER_AGENT, "Authorization": f"Bearer {token}"}
    if content_type:
        headers["Content-Type"] = content_type
    body: bytes | _ProgressReader | None = data
    if data is not None and (on_bytes is not None or is_cancelled is not None):
        # Streamed upload: http.client reads the file-like body in blocks, so
        # progress and cancel get a look-in on every block. Content-Length is
        # required when the body has no len().
        headers["Content-Length"] = str(len(data))
        body = _ProgressReader(data, on_bytes, is_cancelled)
    request = urllib.request.Request(url, data=body, headers=headers)
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            if data is None and (on_bytes is not None or is_cancelled is not None):
                total = int(resp.headers.get("Content-Length") or 0)
                received = bytearray()
                while True:
                    if is_cancelled is not None and is_cancelled():
                        raise AuphonicCancelled("Cancelled — the Auphonic download was stopped.")
                    chunk = resp.read(_DOWNLOAD_BLOCK)
                    if not chunk:
                        break
                    received.extend(chunk)
                    if on_bytes is not None:
                        on_bytes(len(received), total)
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
    data: bytes | None = None,
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
    body, content_type = _multipart(fields, "input_file", path)
    data = _json(
        f"{API_BASE}/simple/productions.json",
        token,
        data=body,
        content_type=content_type,
        on_bytes=on_bytes,
        is_cancelled=is_cancelled,
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
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for output in status.output_files:
        url = str(output.get("download_url", ""))
        filename = str(output.get("filename", "")) or url.rsplit("/", 1)[-1]
        if not url or not filename:
            continue
        if on_progress is not None:
            on_progress(f"Downloading {filename}...")
        per_file = (
            None
            if on_bytes is None
            else (lambda done, total, _name=filename: on_bytes(_name, done, total))
        )
        payload = _request(url, token, on_bytes=per_file, is_cancelled=is_cancelled)
        target = out_dir / filename
        target.write_bytes(payload)
        written.append(target)
    return written
