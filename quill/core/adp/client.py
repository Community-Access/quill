"""ADP Assistant HTTP client: POST /api/ask (docs/API.md sections 2-6, 9).

One bearer credential per client app (label ``quill``), stored in the OS
credential vault -- never settings, never source. HTTPS over QUILL's
verified TLS context. Guardrail hits (rate limit, spend cap, missing model
key) arrive as a normal, friendly ``answer`` -- render them as answers, do
not retry; a real HTTP/connection failure raises :class:`AdpError` for the
caller to speak briefly and stop (never a silent hang). Voice deliberately
lives on the device (API.md section 7): this client never touches
``/api/speak`` or ``/api/transcribe``.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from quill.core.adp.models import AskResponse
from quill.core.error_codes import CodedError

#: Where the client key lives in the OS credential vault.
CREDENTIAL_TARGET = "quill.adp.client_key"

DEFAULT_BASE_URL = "https://adp.bitsinfo.org"

#: The brain can run tools for a while; API.md recommends a generous read
#: timeout. Non-streaming ask stays comfortably under this in practice.
_TIMEOUT_SECONDS = 120.0


class AdpError(CodedError):
    """A real transport/HTTP failure talking to the ADP service (guardrail
    responses are NOT errors -- they arrive as normal answers)."""

    code = "QUILL-ADP-REQUEST-FAILED"


def load_client_key() -> str:
    """The ``quill`` client bearer key from the OS vault ("" when unset)."""
    try:
        from quill.platform.windows.credential_manager import load_generic_credential

        stored = load_generic_credential(CREDENTIAL_TARGET)
        return stored.secret if stored is not None else ""
    except Exception:  # noqa: BLE001 - non-Windows / no vault reads as unset
        return ""


def save_client_key(key: str) -> bool:
    try:
        from quill.platform.windows.credential_manager import (
            delete_generic_credential,
            save_generic_credential,
        )

        if not key.strip():
            delete_generic_credential(CREDENTIAL_TARGET)
            return True
        save_generic_credential(CREDENTIAL_TARGET, key.strip(), user_name="quill")
        return True
    except Exception:  # noqa: BLE001
        return False


def ask(
    question: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    history: list[object] | None = None,
    user_name: str = "",
    safe_mode: bool = False,
    timeout: float = _TIMEOUT_SECONDS,
) -> AskResponse:
    """One non-streaming turn. ``history`` is the previous response's opaque
    ``history`` list (or None for a fresh conversation)."""
    if safe_mode:
        raise AdpError("The ADP Assistant is disabled in Safe Mode.")
    url = base_url.rstrip("/") + "/api/ask"
    if not url.startswith("https://"):
        raise AdpError("The ADP server address must use https.")
    payload: dict[str, object] = {"question": question.strip()}
    if history:
        payload["history"] = history
    if user_name.strip():
        payload["user_name"] = user_name.strip()
    headers = {
        "Content-Type": "application/json",
        "X-ADP-Client": "quill",
    }
    key = load_client_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(  # noqa: S310 - https enforced above
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    from quill.core.net import verified_ssl_context

    try:
        with urllib.request.urlopen(  # noqa: S310 - https + verified context
            request, timeout=timeout, context=verified_ssl_context()
        ) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise AdpError(
                "The ADP service rejected this app's access key. "
                "Check the client key in ADP Settings."
            ) from error
        raise AdpError(f"The ADP service returned an error ({error.code}).") from error
    except (urllib.error.URLError, OSError, TimeoutError) as error:
        raise AdpError(f"Could not reach the ADP service: {error}") from error
    try:
        data = json.loads(raw.decode("utf-8"))
    except ValueError as error:
        raise AdpError("The ADP service returned an unreadable response.") from error
    return AskResponse.from_dict(data)
