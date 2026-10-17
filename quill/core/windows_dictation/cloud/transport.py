"""How every cloud speech provider reaches the network, and what its failures say.

Two openers, both certificate-checked through
:func:`quill.core.net.verified_ssl_context`:

* :func:`urlopen` for HTTPS, and
* :func:`create_connection` for a WebSocket (``websockets``' synchronous
  client, which the shared runtime already carries for OpenAI's live
  dictation).

Each provider module calls one of these at its **own** call site, so the
network egress audit (GATE-9) has one reviewed entry per provider call site,
naming the provider's fixed host. No provider takes a host the person typed,
except where a provider's own address *is* the person's resource, and then the
host must match the provider's domain (:func:`require_host`).

:func:`failure` turns any HTTP or socket failure into one plain sentence that
names the field to check -- never the key, never the response body.

Tests replace :func:`urlopen` and :func:`create_connection` on this module with
recorded fakes; nothing in the test suite touches the real network.

wx-free.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

from quill.core.windows_dictation.cloud.errors import (
    CloudAuthError,
    CloudFieldError,
    CloudNetworkError,
    CloudQuotaError,
    CloudSpeechError,
    CloudUnsupportedError,
)

__all__ = [
    "create_connection",
    "failure",
    "failing_as",
    "read_json",
    "require_host",
    "urlopen",
]


def urlopen(request: Any, *, timeout: float = 30.0) -> Any:
    """Open *request* over verified TLS. The one HTTPS opener for speech providers."""
    from urllib.request import urlopen as _open

    from quill.core.net import verified_ssl_context

    return _open(request, timeout=timeout, context=verified_ssl_context())


def create_connection(url: str, headers: Mapping[str, str] | None = None) -> Any:
    """A WebSocket to *url*, certificate-checked; secrets only in *headers* or
    where the provider's protocol puts them. Raises
    :class:`CloudUnsupportedError` when this copy has no WebSocket client."""
    from quill.core.net import verified_ssl_context

    try:
        from websockets.sync.client import (  # type: ignore[import-not-found,unused-ignore]
            connect,
        )
    except ImportError as error:
        raise CloudUnsupportedError(
            "Live dictation with this provider needs a part that is missing from "
            "this copy of QUILL."
        ) from error
    return connect(
        url,
        additional_headers=dict(headers or {}),
        ssl=verified_ssl_context(),
        open_timeout=15,
        max_size=None,
    )


def read_json(response: Any) -> Any:
    """The JSON body of *response*, or ``{}`` when there is none."""
    raw = response.read()
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except ValueError:
        raise CloudSpeechError("The provider's answer could not be read.") from None


def _status_of(error: BaseException) -> int:
    if isinstance(error, HTTPError):
        return int(error.code or 0)
    response = getattr(error, "response", None)  # websockets' InvalidStatus
    return int(getattr(response, "status_code", 0) or getattr(error, "status_code", 0) or 0)


def failure(
    name: str,
    error: BaseException,
    *,
    auth_field: str = "Key",
    place_field: str = "",
) -> CloudSpeechError:
    """One sentence for a failed call to provider *name*.

    *auth_field* is the field a refused credential points at; *place_field*
    the one a "not found" points at (a region, project or address).
    """
    if isinstance(error, CloudSpeechError):
        return error
    status = _status_of(error)
    noun = auth_field.lower()
    if status in (401, 403):
        return CloudAuthError(f"The {noun} was refused. Check {auth_field}.", field=auth_field)
    if status == 404:
        if place_field:
            return CloudFieldError(
                f"{name} found nothing at that address. Check {place_field}.", field=place_field
            )
        return CloudSpeechError(f"{name} found nothing at that address (error 404).")
    if status in (402, 429):
        return CloudQuotaError(
            f"{name} says the account is out of credit or sending too fast. "
            f"Check your {name} account."
        )
    if status >= 500:
        return CloudNetworkError(
            f"{name} had a problem of its own (error {status}). Try again shortly."
        )
    if status:
        return CloudSpeechError(f"{name} did not accept the request (error {status}).")
    if isinstance(error, (URLError, OSError, TimeoutError)):
        return CloudNetworkError(f"{name} could not be reached. Check the internet connection.")
    return CloudNetworkError(f"The connection to {name} was lost.")


@contextmanager
def failing_as(name: str, *, auth_field: str = "Key", place_field: str = "") -> Iterator[None]:
    """Run a network call; any failure leaves as :func:`failure`'s sentence."""
    try:
        yield
    except CloudSpeechError:
        raise
    except Exception as error:  # noqa: BLE001 - one sentence, never the key
        raise failure(name, error, auth_field=auth_field, place_field=place_field) from None


def require_host(url: str, suffixes: tuple[str, ...], *, field: str) -> str:
    """*url*, when it is HTTPS on one of the provider's own domains; else a
    :class:`CloudFieldError` naming *field*. Used where the address is the
    person's own resource (an Azure endpoint, an IBM service URL)."""
    text = url.strip().rstrip("/")
    parts = urlsplit(text)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host or not any(host.endswith(s) for s in suffixes):
        domains = " or ".join(suffixes)
        raise CloudFieldError(
            f"{field} must be an https address ending in {domains}. Check {field}.", field=field
        )
    return text
