"""SSRF guards for user-supplied outbound URLs in Quill Beacon.

Beacon fetches feed / chapter URLs that come straight from user input or an
imported OPML file. Without a guard, a URL like ``http://169.254.169.254/…``
(cloud metadata) or ``http://127.0.0.1:…/`` would be fetched against the
local network. :func:`validate_public_url` enforces an http(s) scheme and
refuses hosts that resolve to a private, loopback, link-local, or otherwise
non-public address. :func:`read_capped` bounds the response body so a tiny
request cannot stream gigabytes into memory.

wx-free and unit-testable. Note: the address check happens before the fetch,
so a redirect to an internal host (or DNS rebinding) is a residual not fully
covered here; call sites disable or re-validate redirects where it matters.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse
from typing import Any

_ALLOWED_SCHEMES = frozenset({"http", "https"})

#: Cap on a fetched body (feeds/chapters are small; 25 MiB is generous).
MAX_RESPONSE_BYTES = 25 * 1024 * 1024


class UnsafeUrlError(ValueError):
    """Raised when a user-supplied URL targets a disallowed scheme or host."""


def _address_is_public(raw_ip: str) -> bool:
    try:
        ip = ipaddress.ip_address(raw_ip)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_public_url(url: str) -> str:
    """Return *url* unchanged if it is a public http(s) target, else raise.

    Raises :class:`UnsafeUrlError` for a non-http(s) scheme, a missing host,
    a host that will not resolve, or any resolved address that is private /
    loopback / link-local / reserved (blocking cloud-metadata and intranet
    SSRF targets).
    """
    parts = urllib.parse.urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"Only http/https URLs are allowed, not {scheme or 'empty'!r}.")
    host = parts.hostname
    if not host:
        raise UnsafeUrlError("URL has no host.")
    port = parts.port or (443 if scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Could not resolve host {host!r}.") from exc
    for info in infos:
        raw_ip = info[4][0]
        if not _address_is_public(raw_ip):
            raise UnsafeUrlError(
                f"Refusing to fetch a non-public address ({raw_ip}) for host {host!r}."
            )
    return url


def read_capped(resp: Any, *, limit: int = MAX_RESPONSE_BYTES) -> bytes:
    """Read a ``requests`` response body, aborting past *limit* bytes."""
    chunks: list[bytes] = []
    total = 0
    for chunk in resp.iter_content(chunk_size=65536):
        if not chunk:
            continue
        total += len(chunk)
        if total > limit:
            raise UnsafeUrlError(f"Response exceeded the {limit}-byte cap.")
        chunks.append(chunk)
    return b"".join(chunks)
