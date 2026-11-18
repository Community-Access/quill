"""Resolve the operating system's configured proxy without handling credentials."""

from __future__ import annotations

import logging
import urllib.request
from urllib.parse import urlsplit

__all__ = ["resolve_system_proxy"]

_log = logging.getLogger(__name__)


def resolve_system_proxy(request: object) -> str | None:
    """Return a PAC-style route for a URL, or let the SDK use its own resolver.

    Only proxy endpoints without embedded credentials are returned. This callback
    deliberately does not implement Basic or Negotiate authentication.
    """
    target = urlsplit(str(getattr(request, "url", "") or ""))
    if target.scheme not in {"http", "https", "ws", "wss"} or not target.hostname:
        return None

    try:
        if urllib.request.proxy_bypass(target.hostname):
            return "DIRECT"
        configured = urllib.request.getproxies()
    except (OSError, ValueError):
        _log.warning("Could not read the operating system proxy configuration.")
        return None

    raw_proxy = configured.get(target.scheme) or configured.get("all")
    if not raw_proxy:
        return None

    endpoint = urlsplit(raw_proxy if "://" in raw_proxy else f"http://{raw_proxy}")
    if (
        endpoint.scheme not in {"http", "https"}
        or not endpoint.hostname
        or endpoint.username is not None
        or endpoint.password is not None
        or endpoint.path not in {"", "/"}
        or endpoint.query
        or endpoint.fragment
    ):
        _log.warning("Ignoring an unsupported or credential-bearing system proxy endpoint.")
        return None

    try:
        port = endpoint.port or (443 if endpoint.scheme == "https" else 80)
    except ValueError:
        _log.warning("Ignoring an invalid system proxy port.")
        return None

    hostname = endpoint.hostname
    if any(char.isspace() or char in ";<>/" for char in hostname):
        _log.warning("Ignoring an invalid system proxy host.")
        return None
    authority = f"[{hostname}]" if ":" in hostname else hostname
    directive = "HTTPS" if endpoint.scheme == "https" else "PROXY"
    return f"{directive} {authority}:{port}"
