"""Real HTTPS form poster for the OAuth device-login flow (AI-19, PRD remaining
work #1).

:mod:`quill.core.ai.device_login` is a complete, poster-free state machine: it
takes an injected ``Poster`` for every network exchange so the engine itself adds
no egress site. This module supplies the one real poster — a TLS-verified
``urlopen`` that POSTs ``application/x-www-form-urlencoded`` and parses the JSON
reply — kept separate so the GATE-9 egress inventory stays explicit (this call
site is registered in :mod:`quill.tools.network_egress_audit`).

Device-flow nuance: providers signal *progress* with an HTTP error status and a
JSON error body (e.g. GitHub returns ``400`` with ``{"error":"authorization_pending"}``
while the user is still authorizing). So the poster reads and parses the body on
both success and ``HTTPError``, returning the parsed object either way; the
device-login state machine classifies the ``error`` field. Genuine transport
failures (DNS, TLS, timeout) raise, which the caller turns into a clean message.

The network ``opener`` is injectable (default: real ``urlopen``), so the
encoding/parse behaviour is unit-tested without any live endpoint.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request

from quill.core.net import verified_ssl_context

__all__ = ["post_form", "Opener"]

# An opener performs one prepared request and returns (status, body_bytes).
Opener = Callable[[Request], "tuple[int, bytes]"]

_TIMEOUT_S = 30.0


def _real_opener(request: Request) -> tuple[int, bytes]:
    from urllib.request import urlopen  # noqa: PLC0415 - localized egress site

    context = verified_ssl_context() if request.full_url.lower().startswith("https") else None
    try:
        with urlopen(request, timeout=_TIMEOUT_S, context=context) as response:
            return int(response.status or 200), response.read()
    except HTTPError as error:
        # OAuth signals device-flow progress (e.g. authorization_pending) via an
        # HTTP error status with a JSON body; read it so the caller can classify.
        return int(error.code), error.read()


def post_form(url: str, fields: dict[str, str], *, opener: Opener | None = None) -> dict[str, Any]:
    """POST ``fields`` as a urlencoded form and return the parsed JSON object.

    Matches the :data:`quill.core.ai.device_login.Poster` signature (callable with
    two positional args), so it can be handed straight to ``request_device_code`` /
    ``run_device_login``. ``opener`` is injectable for tests.

    Raises:
        urllib.error.URLError / OSError: only for genuine transport failures.
    """
    body = urlencode(fields).encode("utf-8")
    request = Request(  # noqa: S310 - https enforced by callers; TLS-verified opener
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "Quill",
        },
    )
    run = opener or _real_opener
    _status, raw = run(request)
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # A non-JSON body (some providers urlencode the reply) is parsed leniently
        # so a token or error field is still recoverable.
        from urllib.parse import parse_qs

        return {key: values[0] for key, values in parse_qs(text).items()}
    return parsed if isinstance(parsed, dict) else {}
