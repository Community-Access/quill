"""The single reviewed egress site for WeatherIndex. wx-free, strict-typed."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable

from quill import __version__
from quill.core.error_codes import CodedError

_BASE = "https://api.wxindex.org"
_TIMEOUT_SECONDS = 15.0
_USER_AGENT = f"QUILL-Radio/{__version__} (+https://github.com/Community-Access/quill)"

Fetcher = Callable[[str], str]


class WxIndexError(CodedError):
    """A WeatherIndex request failed, was refused, or returned bad data."""

    code = "QUILL-RADIO-WXINDEX-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    if safe_mode:
        raise WxIndexError(
            "NOAA Weather Radio is disabled in Safe Mode. "
            "Restart QUILL normally to browse or update it."
        )


def _default_fetch(url: str) -> str:
    # NETWORK-EGRESS: reviewed site (see quill/tools/network_egress_audit.py).
    request = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            body: bytes = resp.read()
            return body.decode("utf-8")
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise WxIndexError(f"Could not reach the NOAA Weather Radio directory: {error}") from error


def http_json(path: str, *, fetcher: Fetcher | None = None) -> object:
    fetch = fetcher or _default_fetch
    body = fetch(f"{_BASE}{path}")
    try:
        return json.loads(body) if body else []
    except ValueError as error:
        raise WxIndexError(
            "The NOAA Weather Radio directory returned an unreadable reply."
        ) from error
