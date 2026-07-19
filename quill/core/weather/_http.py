"""Shared HTTPS-GET helper for the Weather providers -- one reviewed egress
chokepoint (see ``quill/tools/network_egress_audit.py``). HTTPS-only, verified
TLS, identifying User-Agent (NWS requires one), bounded timeout. wx-free.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

from quill import __version__

#: NWS asks every client to identify itself; a contact URL is the documented
#: convention. Reused for Zippopotam too (harmless, and honest).
USER_AGENT = f"QUILLWeather/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 15.0


def http_json(url: str, *, accept: str = "application/json") -> Any:
    """One HTTPS GET, decoded as JSON. Raises ``OSError``-family errors on
    failure and ``ValueError`` on malformed JSON -- callers wrap these in their
    own :class:`CodedError`. Refuses non-HTTPS URLs outright."""
    if not url.startswith("https://"):
        raise ValueError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
        payload = resp.read().decode("utf-8", errors="replace")
    return json.loads(payload)


#: The exception classes http_json can raise, for callers' ``except`` clauses.
HTTP_ERRORS = (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError, ValueError)
