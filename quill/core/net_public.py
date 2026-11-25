"""Read a web address only when it is on the public internet.

Some of QUILL's requests go to addresses nobody typed: Find Streams opens the
stream links a page names, and stream recovery fetches a broken favourite's
homepage, which comes from a directory anyone can edit. Without a guard, any
public page could make the listener's PC send requests into their own network
-- the router, a NAS, a printer, a service on this computer -- and a listener
who cannot see the address hears only "Found 2 live streams."

:func:`fetch` is the one reviewed egress site for those requests
(``quill/tools/network_egress_entries_radio_finding.py``). It refuses, before
anything is sent:

* anything but ``http`` and ``https``; an address with a user name or password;
  control characters or a backslash; more than :data:`MAX_URL_CHARS` characters
  (:func:`check_url`);
* a host that names this computer or a home network without a lookup: empty, a
  single label, ``localhost`` and ``*.localhost``, ``*.local``, ``*.internal``,
  ``*.home.arpa``, an all-number name, or a literal address that is not public
  (:func:`host_is_refused`);
* a name whose lookup returns **any** address that is not public, so a
  round-robin answer cannot hide one private address among public ones
  (:func:`address_is_public`, which unwraps IPv4-mapped, IPv4-compatible,
  NAT64 and 6to4 addresses first).

The connection is then **pinned** to the address that was checked, so a name
cannot be switched to a private address between the check and the connect. A
secure connection still verifies the certificate against the host name, through
the one shared check in :mod:`quill.core.net`. Redirects are followed by hand,
at most :data:`MAX_REDIRECTS`, each one checked again; there is no FTP, file or
data handler at all. The body is read in 64 KB chunks under an overall
deadline, so a server trickling bytes cannot hold a worker for minutes.

**Proxies are honoured.** Behind a configured proxy, the proxy does its own
lookup and connects for QUILL, so pinning is not possible there; the address is
still checked first, and a name that resolves here to a private address is
still refused.

The public-only rule, the pinning and the re-checked redirects are ideas from
Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift), written here
in QUILL's own code. StreamSift turns proxies off; QUILL keeps them, so people
behind a corporate proxy still get results.

wx-free, strict-typed. Family infrastructure: Beacon can move onto it later.
"""

from __future__ import annotations

import functools
import http.client
import ipaddress
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.error_codes import CodedError

__all__ = [
    "MAX_REDIRECTS",
    "MAX_URL_CHARS",
    "NOT_PUBLIC_SENTENCE",
    "HttpReply",
    "NotPublicAddress",
    "RefusedAddress",
    "address_is_public",
    "check_url",
    "fetch",
    "host_is_refused",
]

MAX_REDIRECTS = 5
MAX_URL_CHARS = 4096
CHUNK_BYTES = 65536

NOT_PUBLIC_SENTENCE = (
    "That address is on this computer or your own network, which QUILL does not scan."
)

_SCHEMES = frozenset({"http", "https"})
_DEFAULT_PORTS = {"http": 80, "https": 443}
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
_LOCAL_NAMES = frozenset({"localhost", "local", "internal", "home.arpa"})
_LOCAL_SUFFIXES = (".localhost", ".local", ".internal", ".home.arpa")
_UNSAFE_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f\\]")
_HEX_LABEL = re.compile(r"0x[0-9a-f]*")
_NAT64 = ipaddress.IPv6Network("64:ff9b::/96")


class RefusedAddress(CodedError, OSError):
    """An address :func:`fetch` will not read: wrong kind, or unsafe in shape."""

    code = "QUILL-NET-PUBLIC-ADDRESS"


class NotPublicAddress(RefusedAddress):
    """The address is on this computer or the listener's own network."""

    code = "QUILL-NET-PUBLIC-REFUSED"


@dataclass(frozen=True, slots=True)
class HttpReply:
    """What :func:`fetch` hands back: status, headers, the first bytes."""

    status: int
    headers: Mapping[str, str]
    body: bytes
    final_url: str = ""


IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


def _embedded_ipv4(address: ipaddress.IPv6Address) -> ipaddress.IPv4Address | None:
    """The IPv4 address an IPv6 one carries, when it carries one."""
    if address.ipv4_mapped is not None:
        return address.ipv4_mapped
    if address.sixtofour is not None:
        return address.sixtofour
    if address in _NAT64 or int(address) >> 32 == 0:
        # NAT64's well-known prefix, and the old IPv4-compatible form (::a.b.c.d),
        # which also covers :: and ::1.
        return ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
    return None


def address_is_public(address: str | IPAddress) -> bool:
    """True only for a globally reachable unicast address.

    Private ranges, loopback, link-local (and so cloud metadata,
    169.254.169.254), carrier-grade NAT, test and documentation ranges,
    reserved and multicast addresses, and IPv6 unique-local and link-local
    addresses are all refused, as is anything that does not parse.
    """
    try:
        parsed = ipaddress.ip_address(address) if isinstance(address, str) else address
    except ValueError:
        return False
    if isinstance(parsed, ipaddress.IPv6Address):
        parsed = _embedded_ipv4(parsed) or parsed
    return bool(parsed.is_global and not parsed.is_multicast and not parsed.is_reserved)


def _literal(host: str) -> IPAddress | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _numeric_label(label: str) -> bool:
    return label.isdigit() or bool(_HEX_LABEL.fullmatch(label))


def host_is_refused(host: str) -> bool:
    """True for a host that is plainly not on the public internet (no lookup)."""
    name = host.strip().lower().rstrip(".")
    if name.startswith("[") and name.endswith("]"):
        name = name[1:-1]
    if not name:
        return True
    literal = _literal(name)
    if literal is not None:
        return not address_is_public(literal)
    if "." not in name or name in _LOCAL_NAMES or name.endswith(_LOCAL_SUFFIXES):
        return True
    # 127.1 and 0x7f.0.0.1 are not names: resolvers read them as addresses.
    return all(_numeric_label(label) for label in name.split("."))


def check_url(url: str) -> urllib.parse.SplitResult:
    """*url*, split, when it may be read at all; raises :class:`RefusedAddress`."""
    if len(url) > MAX_URL_CHARS:
        raise RefusedAddress("That address is too long to read.")
    if _UNSAFE_CHARS.search(url):
        raise RefusedAddress("That address has characters a web address cannot have.")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme.lower() not in _SCHEMES:
        raise RefusedAddress("Only addresses that start with http:// or https:// can be read.")
    if "@" in parts.netloc:
        raise RefusedAddress(
            "That address carries a user name or password, which QUILL never sends."
        )
    try:
        _port = parts.port
    except ValueError as error:
        raise RefusedAddress("That address has a port that is not a number.") from error
    if host_is_refused(parts.hostname or ""):
        raise NotPublicAddress(NOT_PUBLIC_SENTENCE)
    return parts


def _lookup(host: str, port: int) -> list[str]:
    try:
        answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as error:
        raise urllib.error.URLError(error) from error
    return list(dict.fromkeys(str(answer[4][0]) for answer in answers))


def _public_address(host: str, port: int) -> str:
    """The address to connect to: *host* itself, or its first looked-up address
    when every address the lookup returned is public."""
    literal = _literal(host)
    if literal is not None:
        return str(literal)
    addresses = _lookup(host, port)
    if not addresses:
        raise urllib.error.URLError(f"No address was found for {host}.")
    if not all(address_is_public(address) for address in addresses):
        raise NotPublicAddress(NOT_PUBLIC_SENTENCE)
    return addresses[0]


def _refuse_private_answer(host: str, port: int) -> None:
    """Behind a proxy: refuse a name that resolves here to a private address.
    A name this computer cannot resolve is left to the proxy."""
    try:
        addresses = _lookup(host, port)
    except urllib.error.URLError:
        return
    if not all(address_is_public(address) for address in addresses):
        raise NotPublicAddress(NOT_PUBLIC_SENTENCE)


def _connect_pinned(
    address: str, port: int, timeout: Any, source_address: Any = None
) -> socket.socket:
    """Open the connection to the address that was checked, never a new lookup."""
    return socket.create_connection((address, port), timeout, source_address)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, *, pinned: str, **kwargs: Any) -> None:
        super().__init__(host, **kwargs)
        self._pinned = pinned
        self._create_connection = self._open_pinned  # type: ignore[assignment]

    def _open_pinned(
        self, address: tuple[str, int], timeout: Any = None, source_address: Any = None
    ) -> socket.socket:
        return _connect_pinned(self._pinned, address[1], timeout, source_address)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connects to the checked address; the certificate is still verified
    against the host name, which is what ``server_hostname`` carries."""

    def __init__(self, host: str, *, pinned: str, **kwargs: Any) -> None:
        super().__init__(host, **kwargs)
        self._pinned = pinned
        self._create_connection = self._open_pinned  # type: ignore[assignment]

    def _open_pinned(
        self, address: tuple[str, int], timeout: Any = None, source_address: Any = None
    ) -> socket.socket:
        return _connect_pinned(self._pinned, address[1], timeout, source_address)


class _PinnedHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, pinned: str) -> None:
        super().__init__()
        self._pinned = pinned

    def http_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        factory = functools.partial(_PinnedHTTPConnection, pinned=self._pinned)
        return self.do_open(factory, req)  # type: ignore[arg-type]


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, pinned: str) -> None:
        from quill.core.net import verified_ssl_context

        super().__init__(context=verified_ssl_context())
        self._pinned = pinned

    def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        factory = functools.partial(_PinnedHTTPSConnection, pinned=self._pinned)
        return self.do_open(factory, req, context=self._context)  # type: ignore[arg-type,attr-defined]


def _opener(*handlers: urllib.request.BaseHandler) -> urllib.request.OpenerDirector:
    """An opener with only the handlers given, plus error handling: no redirect
    handler (redirects are checked by hand), no FTP, file or data handler."""
    opener = urllib.request.OpenerDirector()
    for handler in (
        *handlers,
        urllib.request.HTTPDefaultErrorHandler(),
        urllib.request.HTTPErrorProcessor(),
    ):
        opener.add_handler(handler)
    return opener


def _proxy_for(scheme: str, host: str) -> str:
    """The proxy configured for *scheme*, or "" when none applies to *host*."""
    proxy = urllib.request.getproxies().get(scheme, "")
    if not proxy or urllib.request.proxy_bypass(host):
        return ""
    return proxy


def _read(response: http.client.HTTPResponse, max_bytes: int, deadline: float) -> bytes:
    """At most *max_bytes* of the body, in chunks, before *deadline*."""
    chunks: list[bytes] = []
    total = 0
    while total < max_bytes:
        if time.monotonic() > deadline:
            raise TimeoutError("The answer took too long to arrive.")
        chunk = response.read1(min(CHUNK_BYTES, max_bytes - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


def _fetch_once(
    url: str, max_bytes: int, timeout: float, deadline: float, headers: Mapping[str, str]
) -> HttpReply:
    parts = check_url(url)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("The answer took too long to arrive.")
    scheme = parts.scheme.lower()
    host = parts.hostname or ""
    port = parts.port or _DEFAULT_PORTS[scheme]
    proxy = _proxy_for(scheme, host)
    if proxy:
        _refuse_private_answer(host, port)
        from quill.core.net import verified_ssl_context

        opener = _opener(
            urllib.request.ProxyHandler({scheme: proxy}),
            urllib.request.HTTPHandler(),
            urllib.request.HTTPSHandler(context=verified_ssl_context()),
        )
    else:
        pinned = _public_address(host, port)
        opener = _opener(_PinnedHTTPHandler(pinned), _PinnedHTTPSHandler(pinned))
    request = urllib.request.Request(url, headers=dict(headers))
    with opener.open(request, timeout=min(timeout, remaining)) as response:
        body = _read(response, max_bytes, deadline)
        return HttpReply(int(response.status), dict(response.headers.items()), body, url)


def fetch(
    url: str,
    *,
    max_bytes: int,
    timeout: float,
    deadline_seconds: float | None = None,
    headers: Mapping[str, str] | None = None,
) -> HttpReply:
    """One GET of a public address -- the reviewed egress site.

    Reads at most *max_bytes*; each network wait is bounded by *timeout*, and
    the whole request, redirects included, by *deadline_seconds* (twice
    *timeout* when not given). Raises :class:`NotPublicAddress` for an address
    on this computer or a home network, :class:`RefusedAddress` for one that
    may not be read at all or a redirect past :data:`MAX_REDIRECTS`, and
    ``urllib.error.HTTPError`` for a 4xx or 5xx answer, which callers read.
    """
    deadline = time.monotonic() + (timeout * 2 if deadline_seconds is None else deadline_seconds)
    current = url
    for hop in range(MAX_REDIRECTS + 1):
        try:
            return _fetch_once(current, max_bytes, timeout, deadline, headers or {})
        except urllib.error.HTTPError as error:
            location = error.headers.get("Location", "") if error.headers else ""
            if error.code not in _REDIRECT_CODES or not location:
                raise
            error.close()
            if hop == MAX_REDIRECTS:
                raise RefusedAddress("That address redirected too many times.") from error
            current = urllib.parse.urljoin(current, location.strip())
    raise RefusedAddress("That address redirected too many times.")  # pragma: no cover
