"""The browser's way back: a one-shot loopback listener for the OAuth redirect.

Split from :mod:`quill.core.ai.chatgpt_account` under GATE-11, and a real seam:
this is the only socket that module ever opens, and the only part of a sign-in
that is not a pure function of its inputs.

Started **before** the browser opens, on port 0, so the redirect URI OpenAI is
told is the one actually listening -- the generic waiter in
:mod:`quill.core.auth.flows` opens its socket after the browser, which is a
race a fast browser can lose. Only :data:`CALLBACK_PATH` is answered; a favicon
request or a stray tab gets a 404 and does not end the wait. Every query
parameter of the redirect is captured, because OpenAI's dynamic registration
returns the issued ``client_id`` beside the code, and the generic waiter keeps
only code, state and error.

wx-free and strict-typed.
"""

from __future__ import annotations

import threading
from urllib.parse import parse_qs, urlparse

__all__ = ["CALLBACK_PATH", "LoopbackListener"]

CALLBACK_PATH = "/auth/callback"


class LoopbackListener:
    """A one-shot listener on 127.0.0.1 for the browser's redirect."""

    def __init__(self, host: str = "127.0.0.1") -> None:
        import http.server

        self._captured: dict[str, str] = {}
        self._done = threading.Event()
        captured = self._captured
        done = self._done

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - http.server API
                parsed = urlparse(self.path)
                if parsed.path != CALLBACK_PATH:
                    self.send_error(404)
                    return
                captured.update({k: v[0] for k, v in parse_qs(parsed.query).items()})
                body = (
                    b"QUILL received the ChatGPT sign-in result. You can close this "
                    b"tab and go back to the app."
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                done.set()

            def log_message(self, *args: object) -> None:  # silence stderr
                pass

        self._server = http.server.ThreadingHTTPServer((host, 0), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def redirect_uri(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host!s}:{port!s}{CALLBACK_PATH}"

    def wait(self, timeout: float) -> dict[str, str]:
        """The redirect's query parameters, or ``{}`` on timeout or cancel."""
        self._done.wait(timeout)
        return dict(self._captured)

    def cancel(self) -> None:
        """End the wait early with nothing captured."""
        self._done.set()

    def close(self) -> None:
        try:
            self._server.shutdown()
            self._server.server_close()
        except OSError:
            pass
