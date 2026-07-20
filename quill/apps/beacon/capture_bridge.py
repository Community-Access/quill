"""Local HTTP capture bridge for browser extensions (PRD 46, Phase 4).

Browser extensions (Chrome/Edge/Firefox) capture pages, selections, links,
headings, media time points, and all-tab dumps, then POST them to this
localhost HTTP endpoint. The bridge writes a :class:`Beacon` into the store
and fires an optional ``on_capture`` callback so the live UI can refresh.

Security model (PRD 46.4):
- Listens on 127.0.0.1 only (never 0.0.0.0).
- Requires a shared bearer token in the ``X-QuillBeacon-Token`` header; the
  token is generated on first run and stored in the data dir. The user copies
  it into the extension options (or it is auto-paired by reading the file).
- Single Origin: the bridge rejects requests whose Origin header is not an
  allowed ``moz-extension://`` / ``chrome-extension://`` scheme, in addition
  to the token check.
- No external network egress; the bridge only accepts inbound captures.

The handler is stdlib-only (``http.server``) so it has no extra dependencies
and runs in the same process as the desktop app.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from quill.apps.beacon import capture, routing

DEFAULT_PORT = 8752
TOKEN_FILE = "bridge_token.txt"
ALLOWED_ORIGIN_SCHEMES = ("moz-extension://", "chrome-extension://")


class CaptureBridge:
    """Owns the HTTP server thread, the store handle, and the shared token."""

    def __init__(
        self,
        db_path,
        *,
        data_dir: str,
        port: int = DEFAULT_PORT,
        on_capture=None,
        token: str | None = None,
    ) -> None:
        # The bridge serves HTTP from worker threads, so it owns a separate
        # SQLite connection (check_same_thread=False) to the same WAL file the
        # desktop app uses. WAL lets the app's connection read committed
        # captures immediately.
        from quill.apps.beacon import db as _db
        from quill.apps.beacon import publish as _publish

        self.store = _db.BeaconStore(db_path, check_same_thread=False)
        self.db_path = str(db_path)
        self.data_dir = data_dir
        self.port = port
        self.on_capture = on_capture
        self.token = token or self._load_or_create_token()
        self.publisher = _publish.PublishManager(self.store, data_dir)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # -- token ----------------------------------------------------------------

    def _token_path(self) -> str:
        return os.path.join(self.data_dir, TOKEN_FILE)

    def _load_or_create_token(self) -> str:
        path = self._token_path()
        try:
            with open(path, encoding="utf-8") as fh:
                tok = fh.read().strip()
                if tok:
                    return tok
        except FileNotFoundError:
            pass
        tok = secrets.token_urlsafe(24)
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(tok)
            # Restrict to the current user where the platform supports it.
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        except OSError:
            pass
        return tok

    # -- lifecycle ------------------------------------------------------------

    def start(self) -> int:
        """Start the bridge on 127.0.0.1. Returns the bound port."""
        if self._server is not None:
            return self.port
        handler = _make_handler(self)
        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="QuillBeaconBridge", daemon=True
        )
        self._thread.start()
        return self.port

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        try:
            self.store.close()
        except Exception:
            pass

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    # -- capture write ---------------------------------------------------------

    def handle_capture(self, payload: dict) -> dict:
        """Validate ``payload`` and write a Beacon. Returns a JSON-able reply."""
        url = (payload.get("url") or "").strip()
        if not url:
            return {"ok": False, "error": "missing url"}
        title = payload.get("title") or ""
        note = payload.get("note") or ""
        selection = payload.get("selection") or ""
        tags = list(payload.get("tags") or [])
        collection = payload.get("collection") or ""
        source = payload.get("source") or "extension"
        type_hint = payload.get("type_hint") or ""
        media_start_ms = int(payload.get("media_start_ms") or 0)

        if selection and not note:
            note = selection
        if selection:
            tags = tags + ["selection"]

        beacon, res = capture.capture(
            url,
            title=title,
            note=note,
            tags=tags,
            capture_source=source,
            media_start_ms=media_start_ms,
        )
        if type_hint:
            res.type = type_hint
        if collection:
            beacon.collections = [collection]
        else:
            routing.route(beacon, res, routing.load_rules(self.data_dir))
        self.store.put_beacon(beacon, resource=res)
        if self.on_capture is not None:
            try:
                self.on_capture(beacon)
            except Exception:
                pass
        return {"ok": True, "beacon_id": beacon.beacon_id}

    def handle_batch(self, payload: dict) -> dict:
        """Capture all-tabs batch. Returns per-item results."""
        items = payload.get("tabs") or []
        results = []
        for item in items:
            results.append(self.handle_capture({**item, "source": "extension-batch"}))
        return {"ok": True, "count": len(results), "results": results}


def _make_handler(bridge: CaptureBridge):
    class _Handler(BaseHTTPRequestHandler):
        # Quiet logging.
        def log_message(self, fmt, *args):  # noqa: D401
            pass

        # -- auth -----------------------------------------------------------
        def _check_origin(self) -> bool:
            origin = self.headers.get("Origin") or ""
            if not origin:
                # Non-browser tools (curl) from localhost are allowed with token.
                return True
            return origin.startswith(ALLOWED_ORIGIN_SCHEMES)

        def _check_token(self) -> bool:
            tok = self.headers.get("X-QuillBeacon-Token") or ""
            return bool(tok) and secrets.compare_digest(tok, bridge.token)

        def _authorized(self) -> bool:
            return self._check_origin() and self._check_token()

        def _send(self, code: int, obj: dict) -> None:
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            # Permissive CORS for extension origins.
            origin = self.headers.get("Origin") or ""
            if origin.startswith(ALLOWED_ORIGIN_SCHEMES):
                self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, code: int, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            origin = self.headers.get("Origin") or ""
            if origin.startswith(ALLOWED_ORIGIN_SCHEMES):
                self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return {}

        # -- routes ---------------------------------------------------------
        def do_OPTIONS(self) -> None:
            self.send_response(204)
            origin = self.headers.get("Origin") or ""
            if origin.startswith(ALLOWED_ORIGIN_SCHEMES):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header(
                    "Access-Control-Allow-Headers", "Content-Type, X-QuillBeacon-Token"
                )
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                self._send(200, {"ok": True, "version": "1", "service": "QuillBeacon"})
                return
            # Published read-only views: public (no token header), gated by the
            # publish token in the URL path. Mirrors /health's public pattern.
            if path == "/published" or path == "/published/":
                self._serve_published_index()
                return
            if path.startswith("/published/"):
                self._serve_published_page(path)
                return
            if path == "/collections" and self._authorized():
                names = [c.name for c in bridge.store.list_collections()]
                self._send(200, {"ok": True, "collections": names})
                return
            if path == "/token" and self._authorized():
                self._send(200, {"ok": True, "token": bridge.token})
                return
            self._send(404, {"ok": False, "error": "not found"})

        def _serve_published_index(self) -> None:
            idx = os.path.join(bridge.data_dir, "published", "index.html")
            try:
                with open(idx, "rb") as fh:
                    self._send_html(200, fh.read())
            except FileNotFoundError:
                self._send_html(
                    200,
                    b"<!DOCTYPE html><html lang='en'><body>"
                    b"<p>No published collections.</p></body></html>",
                )
            except OSError:
                self._send(404, {"ok": False, "error": "not found"})

        def _serve_published_page(self, path: str) -> None:
            # /published/<token>/ -> look up the page by token.
            rest = path[len("/published/") :]
            token = rest.strip("/").split("/", 1)[0]
            found = bridge.publisher.get_by_token(token) if token else None
            if not found:
                self._send(404, {"ok": False, "error": "not found"})
                return
            try:
                with open(found["html_path"], "rb") as fh:
                    self._send_html(200, fh.read())
            except OSError:
                self._send(404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:
            if not self._authorized():
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            path = urlparse(self.path).path
            payload = self._read_json()
            if path == "/capture":
                self._send(200, bridge.handle_capture(payload))
                return
            if path == "/capture-batch":
                self._send(200, bridge.handle_batch(payload))
                return
            self._send(404, {"ok": False, "error": "not found"})

    return _Handler


def find_bridge_port(data_dir: str) -> int | None:
    """Return the port of a running bridge, if recorded in the data dir.

    The desktop app writes ``bridge_port.txt`` on start so extensions can
    discover it. Returns None if no bridge is recorded.
    """
    path = os.path.join(data_dir, "bridge_port.txt")
    try:
        with open(path, encoding="utf-8") as fh:
            return int(fh.read().strip())
    except (FileNotFoundError, ValueError):
        return None
