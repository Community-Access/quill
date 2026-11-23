"""Find Streams reads only the public internet (quill.core.net_public).

A local HTTP server stands in for "a public site": the lookup is faked to
answer a public address, and the pinned connection is redirected to the local
server, so the whole chain -- check, pin, redirects, chunked read, deadline --
runs for real without leaving this computer.
"""

from __future__ import annotations

import http.server
import socket
import threading
import time
import urllib.error
from collections.abc import Iterator
from typing import Any

import pytest

from quill.core import net_public
from quill.core.net_public import NotPublicAddress, RefusedAddress

_PUBLIC = "93.184.216.34"


@pytest.mark.parametrize(
    ("address", "public"),
    [
        (_PUBLIC, True),
        ("1.1.1.1", True),
        ("2606:4700:4700::1111", True),
        ("10.0.0.1", False),
        ("172.16.5.4", False),
        ("192.168.1.1", False),
        ("127.0.0.1", False),
        ("0.0.0.0", False),
        ("169.254.169.254", False),  # cloud metadata
        ("100.64.0.1", False),  # carrier-grade NAT
        ("192.0.2.10", False),  # documentation
        ("198.18.0.1", False),  # benchmarking
        ("224.0.0.1", False),  # multicast
        ("240.0.0.1", False),  # reserved
        ("255.255.255.255", False),
        ("::1", False),
        ("::", False),
        ("fc00::1", False),  # unique-local
        ("fd12:3456::1", False),
        ("fe80::1", False),  # link-local
        ("ff02::1", False),  # multicast
        ("2001:db8::1", False),  # documentation
        ("::ffff:192.168.1.1", False),  # IPv4-mapped
        ("::ffff:93.184.216.34", True),
        ("::192.168.1.1", False),  # IPv4-compatible
        ("64:ff9b::a00:1", False),  # NAT64 of 10.0.0.1
        ("64:ff9b::5db8:d822", True),  # NAT64 of 93.184.216.34
        ("2002:c0a8:101::1", False),  # 6to4 of 192.168.1.1
        ("2002:5db8:d822::1", True),  # 6to4 of 93.184.216.34
        ("not an address", False),
    ],
)
def test_the_address_table(address: str, public: bool) -> None:
    assert net_public.address_is_public(address) is public


@pytest.mark.parametrize(
    ("host", "refused"),
    [
        ("", True),
        ("router", True),  # a single label
        ("localhost", True),
        ("LOCALHOST.", True),
        ("printer.localhost", True),
        ("nas.local", True),
        ("db.internal", True),
        ("box.home.arpa", True),
        ("127.1", True),  # resolvers read it as 127.0.0.1
        ("0x7f.0.0.1", True),
        ("2130706433", True),
        ("[::1]", True),
        ("192.168.1.1", True),
        ("radio.example.org", False),
        (_PUBLIC, False),
        ("[2606:4700:4700::1111]", False),
    ],
)
def test_hosts_refused_before_any_lookup(host: str, refused: bool) -> None:
    assert net_public.host_is_refused(host) is refused


@pytest.mark.parametrize(
    "url",
    [
        "ftp://radio.example.org/live",
        "file:///C:/Windows/win.ini",
        "data:text/plain,hi",
        "https://user:secret@radio.example.org/",
        "https://radio.example.org/a\\b",
        "https://radio.example.org/\x00",
        "https://radio.example.org:port/",
        "https://radio.example.org/" + "a" * net_public.MAX_URL_CHARS,
    ],
)
def test_addresses_that_are_never_read(url: str) -> None:
    with pytest.raises(RefusedAddress):
        net_public.check_url(url)


def test_a_private_address_is_its_own_refusal() -> None:
    with pytest.raises(NotPublicAddress):
        net_public.check_url("http://192.168.1.1/")
    assert issubclass(NotPublicAddress, OSError)
    assert NotPublicAddress.code != RefusedAddress.code


def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the network was used")

    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(net_public, "_proxy_for", lambda *_a: "")


def test_a_literal_private_address_makes_no_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_network(monkeypatch)
    for url in ("http://192.168.1.1/", "http://169.254.169.254/latest/", "http://localhost:8000/"):
        with pytest.raises(NotPublicAddress):
            net_public.fetch(url, max_bytes=100, timeout=1)


def _answers(*addresses: str) -> Any:
    """A stand-in for net_public's lookup (socket.getaddrinfo itself is left
    alone: the local server's own connections use it)."""

    def lookup(_host: str, _port: int) -> list[str]:
        return list(addresses)

    return lookup


def test_a_mixed_public_and_private_answer_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(net_public, "_proxy_for", lambda *_a: "")
    monkeypatch.setattr(net_public, "_lookup", _answers(_PUBLIC, "10.0.0.7"))
    monkeypatch.setattr(net_public, "_connect_pinned", lambda *_a: pytest.fail("connected anyway"))
    with pytest.raises(NotPublicAddress):
        net_public.fetch("http://radio.example.org/", max_bytes=100, timeout=1)


# -- a real server on this computer, standing in for a public one ---------------


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args: Any) -> None:
        pass

    def _redirect(self, where: str) -> None:
        self.send_response(302)
        self.send_header("Location", where)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - the http.server name
        path = self.path
        if path.startswith("http://"):  # asked as a proxy
            body = b"via the proxy " + path.encode()
        elif path == "/page":
            body = b"<html>" + self.headers.get("Host", "").encode() + b"</html>"
        elif path == "/to-private":
            return self._redirect("http://192.168.1.1/admin")
        elif path == "/to-ftp":
            return self._redirect("ftp://radio.example.org/")
        elif path == "/to-page":
            return self._redirect("/page")
        elif path.startswith("/hop/"):
            return self._redirect(f"/hop/{int(path.rsplit('/', 1)[1]) + 1}")
        elif path == "/drip":
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.end_headers()
            try:
                for _ in range(100):
                    self.wfile.write(b"x")
                    self.wfile.flush()
                    time.sleep(0.05)
            except OSError:
                pass
            return
        else:
            body = b"missing"
            self.send_response(404)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def server() -> Iterator[int]:
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield int(httpd.server_address[1])
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture
def pinned(monkeypatch: pytest.MonkeyPatch, server: int) -> list[str]:
    """The lookup answers a public address; the pinned connection records the
    address it was given and reaches the local server instead."""
    connected: list[str] = []
    real = socket.create_connection
    monkeypatch.setattr(net_public, "_proxy_for", lambda *_a: "")
    monkeypatch.setattr(net_public, "_lookup", _answers(_PUBLIC))

    def connect(address: str, port: int, timeout: Any, source: Any = None) -> socket.socket:
        connected.append(address)
        return real(("127.0.0.1", server), timeout)

    monkeypatch.setattr(net_public, "_connect_pinned", connect)
    return connected


def test_the_connection_goes_to_the_checked_address(
    monkeypatch: pytest.MonkeyPatch, pinned: list[str], server: int
) -> None:
    answers = iter([[_PUBLIC], ["10.0.0.9"], ["10.0.0.9"]])

    def rebinding(host: str, port: int) -> list[str]:
        return list(_answers(*next(answers))(host, port))

    monkeypatch.setattr(net_public, "_lookup", rebinding)
    reply = net_public.fetch(f"http://radio.example.org:{server}/page", max_bytes=1000, timeout=5)
    assert reply.status == 200
    # One lookup, and the connection used its answer -- not a second lookup,
    # which a rebinding name would now answer with a private address.
    assert pinned == [_PUBLIC]
    assert f"radio.example.org:{server}".encode() in reply.body  # the Host header kept the name


def test_a_redirect_to_a_private_address_is_refused(pinned: list[str], server: int) -> None:
    with pytest.raises(NotPublicAddress):
        net_public.fetch(f"http://radio.example.org:{server}/to-private", max_bytes=100, timeout=5)
    assert pinned == [_PUBLIC]  # the private hop was never connected


def test_a_redirect_to_ftp_is_refused(pinned: list[str], server: int) -> None:
    with pytest.raises(RefusedAddress):
        net_public.fetch(f"http://radio.example.org:{server}/to-ftp", max_bytes=100, timeout=5)


def test_a_redirect_is_followed_and_rechecked(pinned: list[str], server: int) -> None:
    reply = net_public.fetch(f"http://radio.example.org:{server}/to-page", max_bytes=100, timeout=5)
    assert reply.status == 200
    assert reply.final_url == f"http://radio.example.org:{server}/page"
    assert pinned == [_PUBLIC, _PUBLIC]


def test_a_sixth_redirect_is_refused(pinned: list[str], server: int) -> None:
    with pytest.raises(RefusedAddress, match="redirected too many times"):
        net_public.fetch(f"http://radio.example.org:{server}/hop/0", max_bytes=100, timeout=5)
    assert len(pinned) == net_public.MAX_REDIRECTS + 1


def test_an_error_answer_is_raised_for_the_caller_to_read(pinned: list[str], server: int) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        net_public.fetch(f"http://radio.example.org:{server}/gone", max_bytes=100, timeout=5)
    assert caught.value.code == 404


def test_a_slow_drip_stops_at_the_deadline(pinned: list[str], server: int) -> None:
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        net_public.fetch(
            f"http://radio.example.org:{server}/drip",
            max_bytes=1_000_000,
            timeout=5,
            deadline_seconds=0.6,
        )
    assert time.monotonic() - started < 3


def test_a_proxy_is_honoured(monkeypatch: pytest.MonkeyPatch, server: int) -> None:
    def unresolvable(*_a: Any) -> Any:
        raise urllib.error.URLError(socket.gaierror("only the proxy knows this name"))

    monkeypatch.setattr(net_public, "_lookup", unresolvable)
    monkeypatch.setattr(net_public, "_proxy_for", lambda *_a: f"http://127.0.0.1:{server}")
    monkeypatch.setattr(net_public, "_connect_pinned", lambda *_a: pytest.fail("pinned"))
    reply = net_public.fetch("http://radio.example.org/live", max_bytes=1000, timeout=5)
    assert reply.body == b"via the proxy http://radio.example.org/live"


def test_behind_a_proxy_the_address_is_still_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(net_public, "_proxy_for", lambda *_a: "http://proxy.example.org:3128")
    monkeypatch.setattr(net_public, "_lookup", _answers("10.1.2.3"))
    with pytest.raises(NotPublicAddress):
        net_public.fetch("http://intranet.example.org/", max_bytes=100, timeout=1)
    with pytest.raises(NotPublicAddress):
        net_public.fetch("http://192.168.0.10/", max_bytes=100, timeout=1)


def test_https_connects_to_the_checked_address_and_verifies_the_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connected: list[tuple[str, int]] = []
    wrapped: list[str] = []

    class _Context:
        def wrap_socket(self, sock: Any, server_hostname: str = "") -> Any:
            wrapped.append(server_hostname)
            return sock

    class _Socket:
        def setsockopt(self, *_a: Any) -> None:
            pass

    def connect(address: str, port: int, *_a: Any) -> Any:
        connected.append((address, port))
        return _Socket()

    monkeypatch.setattr(net_public, "_connect_pinned", connect)
    connection = net_public._PinnedHTTPSConnection(
        "radio.example.org", pinned=_PUBLIC, context=_Context()
    )
    connection.connect()
    assert connected == [(_PUBLIC, 443)]
    assert wrapped == ["radio.example.org"]  # the certificate is checked against the name
