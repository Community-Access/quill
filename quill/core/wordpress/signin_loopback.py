"""The one-time loopback listener for WordPress sign-in redirects.

Split from :mod:`quill.core.wordpress.signin` (GATE-11) and re-exported
there. It binds ``127.0.0.1`` -- never ``localhost``, which WordPress refuses
and RFC 8252 section 8.3 warns about -- serves exactly one request, and stops.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Literal
from urllib.parse import urlsplit

from quill.core.wordpress.signin_base import (
    LOOPBACK_HOST,
    LOOPBACK_PATH,
    ListenerError,
    Secret,
    query_params,
)

_log = logging.getLogger(__name__)

__all__ = ["ListenerOutcome", "LoopbackListener"]


# --------------------------------------------------------------------------
# Loopback listener
# --------------------------------------------------------------------------

_DONE_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - QUILL</title>
</head>
<body>
<main>
<h1>{heading}</h1>
<p>You can close this tab and go back to QUILL.</p>
</main>
</body>
</html>
"""


def _done_page(query: Mapping[str, str]) -> bytes:
    declined = query.get("success", "").lower() == "false" or "error" in query
    if declined:
        title, heading = "Not connected", "QUILL was not connected"
    else:
        title, heading = "Signed in", "You're signed in"
    return _DONE_PAGE.format(title=title, heading=heading).encode("utf-8")


ListenerOutcome = Literal["pending", "received", "timed_out", "cancelled"]


class LoopbackListener:
    """A one-time HTTP listener on ``127.0.0.1`` for a browser redirect.

    It binds a random free port, serves exactly one request on ``path`` in a
    background thread, answers with a short accessible page, hands the full
    request URL to ``on_request``, and shuts down. Requests for other paths
    (a favicon, say) get a 404 and do not count. It stops by itself after
    ``timeout`` seconds, and :meth:`cancel` stops it at any time.

    The received URL may carry a password, so the server never logs a
    request line and the page is sent with ``Cache-Control: no-store`` and
    ``Referrer-Policy: no-referrer``.
    """

    _POLL_SECONDS = 0.1

    def __init__(
        self,
        path: str = LOOPBACK_PATH,
        *,
        on_request: Callable[[str], None] | None = None,
        timeout: float = 300.0,
    ) -> None:
        if not path.startswith("/"):
            raise ValueError("path must start with '/'")
        self._path = path
        self._on_request = on_request
        self._timeout = timeout
        self._lock = threading.Lock()
        self._finished = threading.Event()
        self._cancelled = threading.Event()
        self._received: Secret | None = None
        self._outcome: ListenerOutcome = "pending"
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __repr__(self) -> str:
        return f"LoopbackListener(path={self._path!r}, outcome={self._outcome!r})"

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> str:
        """Bind and start serving; returns the redirect URI to hand out."""
        if self._server is not None:
            raise ListenerError("This listener has already been started.")
        listener = self

        class _Handler(BaseHTTPRequestHandler):
            server_version = "QUILL"
            sys_version = ""

            def do_GET(self) -> None:  # noqa: N802 - http.server's name
                listener._handle(self)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                # The default writes the request line, password and all, to
                # stderr. Say nothing.
                return

        try:
            server = ThreadingHTTPServer((LOOPBACK_HOST, 0), _Handler)
        except OSError as exc:
            raise ListenerError(
                f"QUILL could not listen on {LOOPBACK_HOST} ({exc.strerror or exc})."
            ) from exc
        server.daemon_threads = True
        server.timeout = self._POLL_SECONDS
        self._server = server
        self._thread = threading.Thread(
            target=self._serve, name="wordpress-signin-loopback", daemon=True
        )
        self._thread.start()
        return self.redirect_uri

    def cancel(self) -> None:
        """Stop listening now. Safe to call more than once, or before start."""
        with self._lock:
            if self._outcome == "pending":
                self._outcome = "cancelled"
        self._cancelled.set()
        if self._server is None:
            self._finished.set()

    def wait(self, timeout: float | None = None) -> str | None:
        """Block until a request arrives, the timeout passes or it is cancelled.

        Returns the received URL, or ``None`` if nothing usable arrived.
        """
        self._finished.wait(timeout)
        if self._thread is not None:
            self._thread.join(timeout)
        received = self._received
        return received.reveal() if received is not None else None

    def __enter__(self) -> LoopbackListener:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.cancel()
        if self._thread is not None:
            self._thread.join(5.0)

    # -- state -------------------------------------------------------------

    @property
    def port(self) -> int:
        if self._server is None:
            raise ListenerError("This listener has not been started.")
        return int(self._server.server_address[1])

    @property
    def redirect_uri(self) -> str:
        return f"http://{LOOPBACK_HOST}:{self.port}{self._path}"

    @property
    def outcome(self) -> ListenerOutcome:
        return self._outcome

    @property
    def done(self) -> bool:
        return self._finished.is_set()

    # -- internals ---------------------------------------------------------

    def _serve(self) -> None:
        server = self._server
        assert server is not None
        deadline = time.monotonic() + self._timeout
        try:
            while not self._cancelled.is_set():
                with self._lock:
                    if self._outcome != "pending":
                        break
                if time.monotonic() >= deadline:
                    with self._lock:
                        if self._outcome == "pending":
                            self._outcome = "timed_out"
                    break
                server.handle_request()
        finally:
            server.server_close()
            self._finished.set()

    def _handle(self, handler: BaseHTTPRequestHandler) -> None:
        parts = urlsplit(handler.path)
        if parts.path != self._path:
            self._respond(handler, 404, b"Not found\n", "text/plain; charset=utf-8")
            return
        with self._lock:
            first = self._outcome == "pending"
            if first:
                url = f"http://{LOOPBACK_HOST}:{self.port}{handler.path}"
                self._received = Secret(url)
                self._outcome = "received"
        if not first:
            self._respond(handler, 410, b"Already used\n", "text/plain; charset=utf-8")
            return
        self._respond(
            handler, 200, _done_page(query_params(handler.path)), "text/html; charset=utf-8"
        )
        callback = self._on_request
        if callback is not None and self._received is not None:
            try:
                callback(self._received.reveal())
            except Exception:  # noqa: BLE001 - a callback bug must not hang sign-in
                _log.exception("WordPress sign-in callback failed")
        self._finished.set()

    @staticmethod
    def _respond(
        handler: BaseHTTPRequestHandler, status: int, body: bytes, content_type: str
    ) -> None:
        try:
            handler.send_response(status)
            handler.send_header("Content-Type", content_type)
            handler.send_header("Content-Length", str(len(body)))
            handler.send_header("Cache-Control", "no-store")
            handler.send_header("Referrer-Policy", "no-referrer")
            handler.send_header("Connection", "close")
            handler.end_headers()
            handler.wfile.write(body)
        except OSError:
            # The browser went away; the URL is what matters, not the page.
            pass
