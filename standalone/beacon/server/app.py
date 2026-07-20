"""QuillSync hosted server -- HTTP layer (PRD 45.5, 45.9).

A runnable reference server on stdlib ``http.server``. The production target
is FastAPI + PostgreSQL + S3 + Redis (PRD 45.5); this reference proves the
contract locally and is wire-compatible with the QuillSync client
(``quill_beacon.sync``) for the folder-transport shape.

Endpoints:
  POST /auth/request  {"email": "..."} -> {"ok": true}
  GET  /auth/verify?token=...&device=... -> {"device_id", "device_token"}
  POST /sync/push   Bearer <device_token> {"commits":[...], "objects":{hash:b64}}
  POST /sync/pull   Bearer <device_token> {"have":[...]} -> {"commits":[...], "objects":{...}}
  GET  /sync/hints  Bearer <device_token> -> {"new": N}

Auth is client-based (PRD 45.9): the magic link uses a custom URL scheme
(``quillsync://verify``) so it opens the companion app, not a web page. The
server has no web UI; ``/auth/verify`` returns JSON for the client to consume.

Run: ``python -m server`` (defaults to 127.0.0.1:8751).
"""

from __future__ import annotations

import base64
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from server.mailer import LoggingMailer, Mailer
from server.store import ServerStore

# Custom-scheme verify base: the email link opens the companion app, not a
# browser. The companion app calls /auth/verify over HTTP to exchange the token.
VERIFY_BASE = "quillsync://verify"


class SyncServer:
    """Logic layer: ties the store, mailer, and auth together. Testable directly."""

    def __init__(self, store: ServerStore, mailer: Mailer | None = None,
                 *, verify_base: str = VERIFY_BASE) -> None:
        self.store = store
        self.mailer = mailer or LoggingMailer()
        self.verify_base = verify_base

    # -- auth -----------------------------------------------------------------

    def request_magic_link(self, email: str, device_hint: str = "") -> dict:
        raw = self.store.issue_magic_token(email, device_hint=device_hint)
        link = f"{self.verify_base}?token={raw}&device={device_hint or 'web'}"
        self.mailer.send_magic_link(email, link)
        return {"ok": True}

    def verify_magic_link(self, raw_token: str, device_name: str = "device") -> dict | None:
        email = self.store.verify_magic_token(raw_token)
        if not email:
            return None
        # The device token is a fresh random secret; its hash is stored.
        device_token = _new_token()
        reg = self.store.register_device(email, device_name, device_token)
        return {"device_id": reg["device_id"], "device_token": device_token,
                "account": email}

    # -- sync -----------------------------------------------------------------

    def _auth(self, bearer: str | None) -> str | None:
        if not bearer:
            return None
        return self.store.auth_device(bearer.strip())

    def push(self, bearer: str | None, body: dict) -> dict:
        account = self._auth(bearer)
        if not account:
            return {"error": "unauthorized"}
        for blob_hash, b64 in (body.get("objects") or {}).items():
            data = base64.b64decode(b64)
            self.store.put_object(account, blob_hash, data)
        new_commits = 0
        for commit in body.get("commits") or []:
            if not self.store.has_commit(account, commit["commit_id"]):
                self.store.put_commit(account, commit)
                new_commits += 1
        return {"ok": True, "new_commits": new_commits}

    def pull(self, bearer: str | None, body: dict) -> dict:
        account = self._auth(bearer)
        if not account:
            return {"error": "unauthorized"}
        have = set(body.get("have") or [])
        commits = self.store.commits_since(account, have)
        # Gather the objects referenced by the returned commits.
        objects: dict[str, str] = {}
        for c in commits:
            for e in c.get("entries") or []:
                if e.get("tombstone"):
                    continue
                h = e.get("blob_hash")
                if h and h not in objects:
                    data = self.store.get_object(account, h)
                    if data is not None:
                        objects[h] = base64.b64encode(data).decode("ascii")
        return {"commits": commits, "objects": objects}

    def hints(self, bearer: str | None) -> dict:
        account = self._auth(bearer)
        if not account:
            return {"error": "unauthorized"}
        # Opaque hint count: number of commits on the server. The client does
        # not learn object ids or structure from this (PRD 45.5 push hints).
        commits = self.store.commits_since(account, set())
        return {"new": len(commits)}


def _new_token() -> str:
    import os

    return os.urandom(24).hex()


# -- HTTP wiring ---------------------------------------------------------------

def make_handler(server: SyncServer):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # silence default stderr noise
            pass

        def _json(self, code: int, obj: Any) -> None:
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _bearer(self) -> str | None:
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                return auth[len("Bearer "):]
            return None

        def _read(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:  # noqa: N802
            url = urlparse(self.path)
            if url.path == "/auth/verify":
                q = parse_qs(url.query)
                res = server.verify_magic_link(
                    q.get("token", [""])[0], q.get("device", ["device"])[0])
                self._json(200 if res else 401, res or {"error": "invalid or expired token"})
                return
            if url.path == "/sync/hints":
                self._json(200, server.hints(self._bearer()))
                return
            self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            url = urlparse(self.path)
            if url.path == "/auth/request":
                body = self._read()
                if not body.get("email"):
                    self._json(400, {"error": "email required"})
                    return
                self._json(200, server.request_magic_link(body["email"]))
                return
            if url.path == "/sync/push":
                self._json(200, server.push(self._bearer(), self._read()))
                return
            if url.path == "/sync/pull":
                self._json(200, server.pull(self._bearer(), self._read()))
                return
            self._json(404, {"error": "not found"})

    return Handler


def create_server(host: str = "127.0.0.1", port: int = 8751, *,
                  db_path: str = "quillsync_server.db",
                  mailer: Mailer | None = None) -> HTTPServer:
    store = ServerStore(db_path)
    sync_server = SyncServer(store, mailer)
    return HTTPServer((host, port), make_handler(sync_server))


def run(host: str = "127.0.0.1", port: int = 8751) -> int:
    httpd = create_server(host, port)
    print(f"QuillSync reference server on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    return 0