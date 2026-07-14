"""Datalab Chandra cloud OCR service (free-first document conversion, Tier 3).

The paid, consent-gated accuracy escalation from the OCR PRD: when the free
local tiers (MarkItDown, on-device Tesseract) cannot rescue a document —
complex tables, forms, handwriting, dense layouts, poor scans — QUILL can send
it to Datalab's Convert API (Chandra OCR) and open the returned Markdown, HTML,
or text. This module is the wx-free client; every caller must obtain explicit,
per-upload user consent first (PRD §15.1) — nothing here is reachable from any
automatic path.

Trust properties:

* **BYOK.** The API key lives in the Windows credential vault
  (``QUILL/services/datalab/api_key``) with a DPAPI-file fallback and the
  ``DATALAB_API_KEY`` environment variable for CI/portable use — never in
  ``settings.json``.
* **HTTPS enforced** with a verified TLS context; non-HTTPS endpoints refused.
* **Safe Mode blocked**, like every network feature.
* **Logging discipline (PRD §15.3):** job state transitions, error categories,
  and page counts may be logged; file contents, OCR output, API keys, and full
  response bodies never are.
* Datalab deletes results from its servers about an hour after processing;
  QUILL polls and retrieves promptly, keeping the result only in the opened
  document.

GATE-9 / network-egress: the only outbound call site is :func:`_request`; it
runs solely inside :func:`convert_with_datalab`, which is invoked only from
the consent-gated UI flow. Injectable ``opener`` keeps tests fully offline.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError

logger = logging.getLogger(__name__)

DATALAB_DEFAULT_ENDPOINT = "https://www.datalab.to"
DATALAB_CREDENTIAL_TARGET = "QUILL/services/datalab/api_key"
DATALAB_KEY_ENV = "DATALAB_API_KEY"

#: Customer-facing links for the Services tab (PRD §8.5). Kept here so the UI
#: and docs share one source of truth.
DATALAB_LINKS: dict[str, str] = {
    "website": "https://www.datalab.to",
    "api_keys": "https://www.datalab.to/app/keys",
    "pricing": "https://www.datalab.to/pricing",
    "privacy": "https://documentation.datalab.to/platform/security",
    "docs": "https://documentation.datalab.to/docs/welcome/api",
    "file_types": "https://documentation.datalab.to/docs/common/supportedfiletypes",
}

VALID_MODES = ("fast", "balanced", "accurate")
VALID_OUTPUTS = ("markdown", "html", "json")

_POLL_INTERVAL_S = 2.0
_POLL_TIMEOUT_S = 600.0
_REQUEST_TIMEOUT_S = 120.0

ProgressFn = Callable[[str], None]
CancelFn = Callable[[], bool]
#: ``opener(request, timeout) -> response`` — injectable for offline tests.
Opener = Callable[[urllib.request.Request, float], Any]


class DatalabError(CodedError):
    """A cloud conversion failed, with a user-ready, secret-free message."""

    code = "QUILL-OCR-DATALAB-FAILED"


class DatalabCancelled(DatalabError):
    """The user cancelled while the job was in flight."""


@dataclass(slots=True)
class DatalabResult:
    """A retrieved conversion: exactly one content field is populated."""

    output_format: str
    content: str
    page_count: int = 0
    request_id: str = ""


# --------------------------------------------------------------------- key


def load_datalab_api_key() -> str:
    """The stored Datalab key: credential vault, DPAPI file, then env var."""
    try:
        from quill.platform.windows.credential_manager import load_generic_credential

        stored = load_generic_credential(DATALAB_CREDENTIAL_TARGET)
        if stored is not None and stored.secret:
            return stored.secret
    except Exception:  # noqa: BLE001 - vault unavailable off-Windows
        pass
    return os.environ.get(DATALAB_KEY_ENV, "").strip()


def save_datalab_api_key(api_key: str) -> bool:
    """Store (or clear, for an empty key) the Datalab key in the vault."""
    secret = api_key.strip()
    try:
        from quill.platform.windows.credential_manager import (
            delete_generic_credential,
            save_generic_credential,
        )

        if not secret:
            delete_generic_credential(DATALAB_CREDENTIAL_TARGET)
            return True
        save_generic_credential(DATALAB_CREDENTIAL_TARGET, secret, user_name="quill")
        return True
    except Exception:  # noqa: BLE001 - vault unavailable off-Windows
        return False


def datalab_configured(settings: object) -> bool:
    """True when the service is enabled AND a key is available."""
    return bool(getattr(settings, "datalab_enabled", False)) and bool(load_datalab_api_key())


# ----------------------------------------------------------------- request


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()


def _default_opener(request: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.urlopen(  # noqa: S310 - HTTPS enforced by callers
        request, timeout=timeout, context=_ssl_context()
    )


def _request(
    url: str,
    *,
    api_key: str,
    data: bytes | None = None,
    content_type: str = "",
    opener: Opener | None = None,
    timeout: float = _REQUEST_TIMEOUT_S,
) -> dict[str, Any]:
    """One authenticated Datalab call; returns the parsed JSON body.

    GATE-9: the module's single outbound call site. HTTPS is enforced, the
    key travels only in the ``X-API-Key`` header, and error bodies are mapped
    to friendly messages without being logged.
    """
    if not url.lower().startswith("https://"):
        raise DatalabError("The Datalab endpoint must use a secure (HTTPS) address.")
    headers = {"X-API-Key": api_key, "User-Agent": "QUILL"}
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=data, headers=headers)
    open_fn = opener or _default_opener
    try:
        with open_fn(request, timeout) as response:
            payload = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        raise DatalabError(_friendly_http_error(error.code)) from None
    except urllib.error.URLError as error:
        raise DatalabError(
            "QUILL cannot reach the Datalab service. Check your internet "
            f"connection and endpoint. ({getattr(error, 'reason', error)})"
        ) from None
    try:
        parsed = json.loads(payload)
    except ValueError:
        raise DatalabError("Datalab returned an unreadable response. Try again.") from None
    if not isinstance(parsed, dict):
        raise DatalabError("Datalab returned an unexpected response shape. Try again.")
    return parsed


def _friendly_http_error(status: int) -> str:
    """PRD §17 error table, mapped from HTTP status."""
    if status in (401, 403):
        return "Datalab rejected the API key. Check or replace the key in OCR Service Settings."
    if status == 402:
        return "The service reported a billing or credit issue. Check your Datalab account."
    if status == 413:
        return "This file is larger than the service limit. Try a smaller file or a page range."
    if status == 429:
        return "The service is busy or your account is rate-limited. Wait a moment and retry."
    if status >= 500:
        return "The Datalab service reported an internal error. Try again shortly."
    return f"The Datalab service returned an unexpected error (HTTP {status})."


def _multipart(path: Path, fields: dict[str, str]) -> tuple[bytes, str]:
    """Encode the file + option fields as multipart/form-data."""
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
            ).encode()
        )
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
    )
    parts.append(path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


# ----------------------------------------------------------------- convert


def convert_with_datalab(
    path: Path,
    *,
    endpoint: str = DATALAB_DEFAULT_ENDPOINT,
    mode: str = "balanced",
    output_format: str = "markdown",
    paginate: bool = True,
    api_key: str | None = None,
    opener: Opener | None = None,
    on_progress: ProgressFn | None = None,
    cancel_requested: CancelFn | None = None,
    poll_interval: float = _POLL_INTERVAL_S,
    poll_timeout: float = _POLL_TIMEOUT_S,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> DatalabResult:
    """Submit ``path`` to Datalab Convert, poll to completion, return content.

    The caller has already obtained per-upload consent (PRD §15.1). Raises
    :class:`DatalabError` with a friendly message on every failure and
    :class:`DatalabCancelled` when the user backs out mid-flight.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise DatalabError("Cloud OCR is disabled in Safe Mode.")
    key = (api_key if api_key is not None else load_datalab_api_key()).strip()
    if not key:
        raise DatalabError(
            "Datalab is not configured. Add an API key in OCR Service Settings first."
        )
    mode = mode if mode in VALID_MODES else "balanced"
    output_format = output_format if output_format in VALID_OUTPUTS else "markdown"
    base = endpoint.strip().rstrip("/") or DATALAB_DEFAULT_ENDPOINT

    if on_progress is not None:
        on_progress("Uploading to Datalab (with your consent)...")
    body, content_type = _multipart(
        path,
        {
            "output_format": output_format,
            "mode": mode,
            "paginate": "true" if paginate else "false",
        },
    )
    submitted = _request(
        f"{base}/api/v1/convert",
        api_key=key,
        data=body,
        content_type=content_type,
        opener=opener,
    )
    request_id = str(submitted.get("request_id", "") or "")
    check_url = str(submitted.get("request_check_url", "") or "")
    if not check_url:
        error_text = str(submitted.get("error", "") or "")
        raise DatalabError(
            "Datalab did not accept the document."
            + (f" ({error_text})" if error_text else " Try again.")
        )
    logger.info("Datalab job submitted request_id=%s pages=?", request_id)

    deadline = clock() + poll_timeout
    while True:
        if cancel_requested is not None and cancel_requested():
            raise DatalabCancelled("Conversion cancelled. No result was imported.")
        if clock() >= deadline:
            raise DatalabError(
                "The service is taking too long. Try again, or use a smaller page range."
            )
        status = _request(check_url, api_key=key, opener=opener)
        state = str(status.get("status", "") or "").lower()
        if state and state not in ("complete", "completed"):
            if on_progress is not None:
                on_progress("Datalab is processing the document...")
            sleep(poll_interval)
            continue
        if status.get("success") is False:
            error_text = str(status.get("error", "") or "")
            raise DatalabError(
                "The service returned an incomplete result. Try accurate mode "
                "or a smaller page range." + (f" ({error_text})" if error_text else "")
            )
        content = str(status.get(output_format, "") or "")
        if not content and output_format == "json":
            raw = status.get("json")
            content = json.dumps(raw, indent=2) if raw is not None else ""
        if not content:
            raise DatalabError(
                "The service returned an empty result. Try accurate mode or check the file."
            )
        page_count = int(status.get("page_count", 0) or 0)
        logger.info(
            "Datalab job complete request_id=%s pages=%s format=%s",
            request_id,
            page_count,
            output_format,
        )
        if on_progress is not None:
            on_progress("Retrieving the converted document...")
        return DatalabResult(
            output_format=output_format,
            content=content,
            page_count=page_count,
            request_id=request_id,
        )


#: Filename fragments that trigger the extra sensitive-document warning
#: before a cloud upload (PRD §15.2).
SENSITIVE_NAME_FRAGMENTS: tuple[str, ...] = (
    "medical",
    "health",
    "patient",
    "tax",
    "ssn",
    "social security",
    "passport",
    "driver",
    "w2",
    "w-2",
    "bank",
    "legal",
    "contract",
    "student",
    "iep",
    "disability",
    "accommodation",
)


def looks_sensitive(path: Path) -> bool:
    """Filename-only heuristic for the extra §15.2 warning (never inspects content)."""
    name = path.name.lower()
    return any(fragment in name for fragment in SENSITIVE_NAME_FRAGMENTS)


__all__ = [
    "DATALAB_CREDENTIAL_TARGET",
    "DATALAB_DEFAULT_ENDPOINT",
    "DATALAB_KEY_ENV",
    "DATALAB_LINKS",
    "SENSITIVE_NAME_FRAGMENTS",
    "VALID_MODES",
    "VALID_OUTPUTS",
    "DatalabCancelled",
    "DatalabError",
    "DatalabResult",
    "convert_with_datalab",
    "datalab_configured",
    "load_datalab_api_key",
    "looks_sensitive",
    "save_datalab_api_key",
]
