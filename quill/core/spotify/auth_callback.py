"""One-shot loopback receiver for Spotify's OAuth redirect.

PKCE's redirect lands in the user's browser at ``http://127.0.0.1`` rather than
a public URL, so QUILL runs a tiny local HTTP server -- in the same spirit as
the ``127.0.0.1`` audio relay in :mod:`quill.core.audio_enhance` -- to catch the
single ``GET /callback`` Spotify sends and read the authorization ``code`` out
of its query string.

Two details make this correct:

* **Bind before the browser opens.** The socket is bound in :meth:`__init__`,
  so by the time the caller launches the browser the port is already held and
  Spotify's redirect can never race an unbound port. Passing ``port=0`` binds an
  ephemeral port (used by the tests); :attr:`port` reports what was actually
  bound.
* **Validate ``state``.** The value Spotify echoes back must equal the one from
  :func:`quill.core.spotify.auth.build_authorization`; a mismatch is rejected
  rather than trusted, defeating a cross-site redirect.

The server handles exactly one request and then stops. :meth:`wait` blocks (with
a bounded timeout) for that request and returns the code, or raises
:class:`SpotifyCallbackError`. No outbound network egress: this only *receives*
a connection from the local browser.

wx-free, strict-typed.
"""

from __future__ import annotations

import http.server
import queue
import time
import urllib.parse
from collections.abc import Callable

from quill.core.error_codes import CodedError

#: How long :meth:`CallbackServer.wait` blocks for the redirect before giving
#: up -- long enough for the user to sign in and approve in their browser.
CALLBACK_TIMEOUT_SECONDS = 600.0

#: The plain-text page the browser shows after a successful redirect.
_SUCCESS_BODY = "QUILL is connected to Spotify. You can close this tab and return to QUILL."


class SpotifyCallbackError(CodedError):
    """The loopback redirect never arrived, or arrived malformed/mismatched."""

    code = "QUILL-SPOTIFY-CALLBACK-FAILED"


class CallbackServer:
    """Receives one OAuth redirect on ``127.0.0.1`` and yields its code.

    Bind on construction, launch the browser, then call :meth:`wait`::

        server = CallbackServer(request.state)
        webbrowser.open(request.url)          # port is already bound
        code = server.wait()                  # blocks for the redirect
    """

    def __init__(
        self,
        expected_state: str,
        *,
        host: str = "127.0.0.1",
        port: int = 43217,
        path: str = "/callback",
    ) -> None:
        self._expected_state = expected_state
        self._path = path
        #: Delivers ``(code, error_message)`` from the handler thread to
        #: :meth:`wait`; a non-empty error message means the redirect was bad.
        self._result: queue.Queue[tuple[str, str]] = queue.Queue(maxsize=1)
        self._server = http.server.HTTPServer((host, port), self._build_handler())

    @property
    def port(self) -> int:
        """The port actually bound (resolves an ephemeral ``port=0``)."""
        return int(self._server.server_address[1])

    def wait(
        self,
        timeout: float = CALLBACK_TIMEOUT_SECONDS,
        *,
        on_ready: Callable[[], None] | None = None,
    ) -> str:
        """Block until the redirect arrives; return its authorization code.

        ``on_ready`` (if given) fires once the server is about to start serving
        -- the caller's cue to open the browser. Raises
        :class:`SpotifyCallbackError` on a bad redirect or on timeout.
        """
        try:
            if on_ready is not None:
                on_ready()
            deadline = time.monotonic() + timeout
            while self._result.empty():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._server.timeout = remaining
                self._server.handle_request()
        finally:
            self.close()
        try:
            code, error = self._result.get_nowait()
        except queue.Empty:
            raise SpotifyCallbackError(
                "Timed out waiting for the Spotify sign-in to complete."
            ) from None
        if error:
            raise SpotifyCallbackError(error)
        return code

    def close(self) -> None:
        """Release the bound socket (idempotent)."""
        try:
            self._server.server_close()
        except OSError:
            pass

    def _build_handler(self) -> type[http.server.BaseHTTPRequestHandler]:
        owner = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path != owner._path:
                    self.send_error(404)
                    return
                params = urllib.parse.parse_qs(parsed.query)
                state = params.get("state", [""])[0]
                code = params.get("code", [""])[0]
                error = params.get("error", [""])[0]
                if state != owner._expected_state:
                    owner._deliver("", "The Spotify sign-in response could not be verified.")
                    self._reply(400, "Sign-in verification failed. Please try again in QUILL.")
                    return
                if error:
                    owner._deliver("", f"Spotify sign-in was refused: {error}.")
                elif not code:
                    owner._deliver("", "Spotify did not return an authorization code.")
                    self._reply(400, "Sign-in did not complete. Please try again in QUILL.")
                    return
                else:
                    owner._deliver(code, "")
                self._reply(200, _SUCCESS_BODY)

            def _reply(self, status: int, message: str) -> None:
                body = message.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                return  # keep the loopback server silent

        return _Handler

    def _deliver(self, code: str, error: str) -> None:
        """Record the (first) result; later duplicate requests are ignored."""
        try:
            self._result.put_nowait((code, error))
        except queue.Full:
            pass


__all__ = [
    "CALLBACK_TIMEOUT_SECONDS",
    "CallbackServer",
    "SpotifyCallbackError",
]
