"""A fake Scribe for Documents for tests: REST plus a scripted Phoenix channel.

Everything is in-process: :meth:`FakeScribe.transport` answers the REST calls
:class:`quill.core.scribe.client.ScribeClient` makes, :meth:`FakeScribe.connector`
hands :class:`quill.core.scribe.channel.DocumentChannel` a scripted socket,
and :meth:`FakeScribe.poster` answers the OAuth form posts. Nothing touches
the network. It replays stages, chunks, errors, drops and ``password_required``
as the real server's client library describes them.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

BASE = "https://scribe.test"
STORAGE = "https://storage.scribe.test"


class FakeResponse:
    def __init__(
        self,
        status: int,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
        drop_after: int | None = None,
    ) -> None:
        self.status = status
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self._body = body
        self._pos = 0
        self._drop_after = drop_after

    def read(self, size: int = -1) -> bytes:
        if self._drop_after is not None and self._pos >= self._drop_after:
            raise ConnectionResetError("dropped")
        end = len(self._body) if size < 0 else self._pos + size
        if self._drop_after is not None:
            end = min(end, self._drop_after)
        chunk = self._body[self._pos : end]
        self._pos += len(chunk)
        return chunk

    def close(self) -> None:
        pass


def _json(status: int, data: Any) -> FakeResponse:
    return FakeResponse(status, json.dumps(data).encode(), {"Content-Type": "application/json"})


def _error(status: int, code: str, message: str, **extra: Any) -> FakeResponse:
    return _json(status, {"error": {"code": code, "message": message, **extra}})


@dataclass
class FakeDocument:
    id: str
    title: str
    password: str = ""
    unlocked: bool = True
    outputs: dict[str, str] = field(default_factory=dict)  # format -> stage
    trashed: bool = False
    settings: dict[str, Any] = field(default_factory=dict)
    preview_running: bool = True
    #: The ``document[settings][field]`` form fields sent with the upload.
    upload_settings: dict[str, str] = field(default_factory=dict)


class FakeSocket:
    def __init__(self, server: FakeScribe, url: str) -> None:
        self.server = server
        self.url = url
        self.inbox: deque[str] = deque()
        self.sent: list[list[Any]] = []
        self.closed = False
        self.topic = ""

    def _push(self, ref: str | None, event: str, payload: Any) -> None:
        self.inbox.append(json.dumps([None, ref, self.topic, event, payload]))

    def send(self, message: str) -> None:
        frame = json.loads(message)
        self.sent.append(frame)
        _join, ref, topic, event, payload = frame
        self.server.on_frame(self, ref, topic, event, payload)

    def recv(self, timeout: float | None = None) -> str:
        if self.server.drop_next_recv:
            self.server.drop_next_recv -= 1
            raise ConnectionResetError("dropped")
        if not self.inbox:
            time.sleep(min(timeout or 0.0, 0.005))
            raise TimeoutError
        return self.inbox.popleft()

    def close(self) -> None:
        self.closed = True


class FakeScribe:
    """State and scripts. Change the public attributes to script a scenario."""

    def __init__(self) -> None:
        self.documents: dict[str, FakeDocument] = {}
        self.requests: list[tuple[str, str, dict[str, str], bytes]] = []
        self.sockets: list[FakeSocket] = []
        self.pages_remaining = 100
        self.suggest_buying_pages = False
        #: ``GET /api/billing``'s ``subscription``: None, or {"store", "renews_at"}.
        self.subscription: dict[str, str] | None = None
        self.access_token = "access-token-1"
        self.refresh_token = "refresh-token-1"
        self.reject_token_once = False
        self.revoked: list[str] = []
        self.token_posts: list[dict[str, str]] = []
        # channel scripts
        self.in_progress_once = False
        self.rate_limited_once = False
        self.needs_purchase = False
        self.error_for_format: dict[str, tuple[str, str]] = {}
        self.stages = ("queue", "start", "convert", "add_image_descriptions", "complete")
        self.chunks: list[str] = []
        #: Chunks carry ``index`` (Scribe since 2026-11-23); False is an older server.
        self.chunk_indexes = True
        #: Preview chunks already streamed, sent first on a join that asks for
        #: ``replay_chunks`` (indexes 0, 1, ...); live :attr:`chunks` follow on.
        self.streamed: list[str] = []
        self.join_payloads: list[Any] = []
        self.drop_next_recv = 0
        self.drop_download_after: int | None = None
        self.fail_connect = 0
        self.file_bytes: dict[str, bytes] = {}
        #: The file name the download's Content-Disposition gives, per format.
        self.disposition_names: dict[str, str] = {}
        self._next_id = 1
        # account
        self.organization_name: str | None = None
        self.account_defaults: dict[str, Any] = {"language": "", "tts_rate": 1.0}
        self.default_patches: list[dict[str, Any]] = []
        self.settings_patches: list[tuple[str, dict[str, Any]]] = []
        self.not_a_document = False
        # Scribe's rate limit: *rate_limit* actions (uploads, start_conversion,
        # password tries) per person in fixed 60-second windows of *clock*.
        self.rate_limit: int | None = None
        self.clock: Any = time.monotonic
        self.actions: list[float] = []
        self.rate_limited_count = 0

    def _over_limit(self) -> bool:
        """Count one action; True when Scribe would answer ``rate_limited``."""
        now = float(self.clock())
        if self.rate_limit is not None:
            window = int(now // 60)
            used = sum(1 for t in self.actions if int(t // 60) == window)
            if used >= self.rate_limit:
                self.rate_limited_count += 1
                return True
        self.actions.append(now)
        return False

    def serve_files(self, files: dict[str, Any], names: dict[str, str] | None = None) -> None:
        """Each format's download returns the bytes of ``files[format]`` (a path:
        the real corpus output), named *names[format]* by the server."""
        for fmt, path in files.items():
            self.file_bytes[fmt] = path.read_bytes()
        self.disposition_names.update(names or {})

    # ----------------------------------------------------------------- REST

    def add_document(self, title: str = "Notes.pdf", **kwargs: Any) -> FakeDocument:
        doc = FakeDocument(id=f"doc{self._next_id}", title=title, **kwargs)
        self._next_id += 1
        self.documents[doc.id] = doc
        return doc

    def transport(self, request: urllib.request.Request, timeout: float) -> FakeResponse:
        url = request.full_url
        headers = {k.lower(): v for k, v in request.header_items()}
        body = request.data or b""
        method = request.get_method()
        self.requests.append((method, url, headers, body))
        if url.startswith(STORAGE):
            return self._storage(url, headers)
        auth = headers.get("authorization", "")
        if auth != f"Bearer {self.access_token}" or self.reject_token_once:
            self.reject_token_once = False
            return _error(401, "unauthenticated", "Please sign in.")
        path = urlsplit(url).path
        return self._route(method, path, body)

    def _route(self, method: str, path: str, body: bytes) -> FakeResponse:
        if path == "/api/documents" and method == "POST":
            if self._over_limit():
                return _error(429, "rate_limited", "Slow down.")
            text = body.decode("utf-8", errors="replace")
            name = re.search(r'filename="([^"]+)"', text)
            password = re.search(r'name="document\[password\]"\r\n\r\n([^\r]*)', text)
            title = name.group(1) if name else "Linked document"
            if self.not_a_document or title.lower().endswith((".html", ".htm")):
                return _error(422, "not_a_document", "That is a web page.")
            doc = self.add_document(title=title)
            doc.upload_settings = dict(
                re.findall(r'name="document\[settings\]\[([a-z_]+)\]"\r\n\r\n([^\r]*)', text)
            )
            if "LOCKED" in text and not password:
                doc.unlocked = False
            return _json(201, {"document_id": doc.id})
        if path == "/api/documents" and method == "GET":
            docs = [self._summary(d) for d in self.documents.values() if not d.trashed]
            return _json(
                200,
                {
                    "documents": docs,
                    "pages_remaining": self.pages_remaining,
                    "suggest_buying_pages": self.suggest_buying_pages,
                },
            )
        if path == "/api/documents/trash":
            docs = [
                {
                    **self._summary(d),
                    "trashed_at": "2026-11-20T10:00:00Z",
                    "permanently_delete_at": "2026-11-27T10:00:00Z",
                }
                for d in self.documents.values()
                if d.trashed
            ]
            return _json(200, {"documents": docs})
        if path == "/api/account_info":
            return _json(
                200,
                {
                    "first_name": "Pat",
                    "last_name": "Reader",
                    "email": "pat@example.com",
                    "organization_name": self.organization_name,
                },
            )
        if path == "/api/billing":
            return _json(
                200,
                {
                    "pages_remaining": self.pages_remaining,
                    "subscription": self.subscription,
                    "app_account_token": "x",
                },
            )
        if path == "/api/settings/languages":
            return _json(200, {"languages": [["English", "en"], ["French", "fr"]]})
        if path == "/api/settings/dialects":
            return _json(200, {"dialects": {"en": [["English (US)", "en-US"]]}})
        if path == "/api/settings/voices":
            return _json(200, {"voices": {"en-US": [["Ava", "en-US-Ava", True]]}})
        if path == "/api/settings/braille_tables":
            return _json(200, {"braille_tables": [["UEB Grade 2", "en-ueb-g2"]]})
        if path == "/api/document_settings":
            if method == "PATCH":
                patch = json.loads(body or b"{}").get("settings", {})
                self.default_patches.append(patch)
                self.account_defaults.update(patch)
            return _json(200, dict(self.account_defaults))
        match = re.match(r"^/api/documents/([^/]+)(/.*)?$", path)
        if not match:
            return _error(404, "not_found", "No such page.")
        doc = self.documents.get(match.group(1))
        rest = match.group(2) or ""
        if doc is None:
            return _error(404, "not_found", "We couldn't find that document.")
        if rest == "/outputs":
            return _json(
                200, {"outputs": self._outputs(doc), "is_password_needed": not doc.unlocked}
            )
        if rest == "/settings":
            if method == "PATCH":
                doc.settings = json.loads(body or b"{}").get("settings", {})
                self.settings_patches.append((doc.id, dict(doc.settings)))
            return _json(200, {"language": "", "tts_rate": 1.0, **doc.settings})
        if rest == "/trash":
            doc.trashed = True
            return _json(200, {})
        if rest == "/recover":
            doc.trashed = False
            return _json(200, {})
        if rest == "/feedback":
            return _json(200, {})
        if rest == "" and method == "DELETE":
            if not doc.trashed:
                return _error(422, "not_trashed", "Move it to the trash first.")
            del self.documents[doc.id]
            return _json(200, {})
        if rest == "" and method == "PATCH":
            doc.title = json.loads(body)["document"]["title"]
            return _json(200, self._summary(doc))
        dl = re.match(r"^/outputs/([a-z_0-9]+)/download$", rest)
        if dl:
            fmt = dl.group(1)
            if doc.outputs.get(fmt) != "complete":
                return _error(409, "conversion_not_complete", "Not finished yet.")
            return FakeResponse(302, b"", {"Location": f"{STORAGE}/{doc.id}/{fmt}"})
        return _error(404, "not_found", "No such page.")

    def _storage(self, url: str, headers: dict[str, str]) -> FakeResponse:
        _doc_id, fmt = urlsplit(url).path.strip("/").split("/")
        data = self.file_bytes.get(fmt, f"{fmt} content ".encode() * 50)
        start = 0
        ranged = headers.get("range", "")
        if ranged.startswith("bytes="):
            start = int(ranged[6:].rstrip("-"))
        part = data[start:]
        out_headers = {
            "Content-Length": str(len(part)),
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(self.disposition_names.get(fmt, f"Notes.{_ext(fmt)}")),
        }
        status = 200
        if start:
            status = 206
            out_headers["Content-Range"] = f"bytes {start}-{len(data) - 1}/{len(data)}"
        drop = self.drop_download_after
        self.drop_download_after = None
        return FakeResponse(status, part, out_headers, drop_after=drop)

    @staticmethod
    def _outputs(doc: FakeDocument) -> list[dict[str, Any]]:
        return [
            {
                "format": fmt,
                "stage": stage,
                "progress": 1.0 if stage == "complete" else 0.5,
                "estimated_time_remaining": 30_000,
                "is_preview": False,
                "downloadable": True,
            }
            for fmt, stage in doc.outputs.items()
        ]

    def _summary(self, doc: FakeDocument) -> dict[str, Any]:
        return {
            "id": doc.id,
            "title": doc.title,
            "page_count": 3,
            "inserted_at": "2026-11-20T09:00:00Z",
            "is_password_needed": not doc.unlocked,
            "outputs": self._outputs(doc),
        }

    # -------------------------------------------------------------- channel

    def connector(self, url: str) -> FakeSocket:
        if self.fail_connect:
            self.fail_connect -= 1
            raise ConnectionRefusedError("down")
        token = parse_qs(urlsplit(url).query).get("token", [""])[0]
        if token != self.access_token:
            raise ConnectionRefusedError("refused")
        sock = FakeSocket(self, url)
        self.sockets.append(sock)
        return sock

    def on_frame(self, sock: FakeSocket, ref: str, topic: str, event: str, payload: Any) -> None:
        if event == "heartbeat":
            return
        sock.topic = topic
        doc = self.documents.get(topic.split(":", 1)[1])
        if event == "phx_join":
            self.join_payloads.append(payload)
            if doc is None:
                sock._push(
                    ref, "phx_reply", {"status": "error", "response": {"reason": "not_found"}}
                )
                return
            sock._push(ref, "phx_reply", {"status": "ok", "response": {}})
            if self.chunk_indexes and isinstance(payload, dict) and payload.get("replay_chunks"):
                for index, chunk in enumerate(self.streamed):
                    sock._push(None, "chunk", {"index": index, "content": chunk})
            if not doc.unlocked:
                sock._push(None, "password_required", {})
            return
        if event != "start_conversion" or doc is None:
            return
        fmt = payload["format"]
        if self._over_limit():
            sock._push(
                ref, "phx_reply", {"status": "error", "response": {"reason": "rate_limited"}}
            )
            return
        if self.in_progress_once:
            self.in_progress_once = False
            sock._push(
                ref,
                "phx_reply",
                {"status": "error", "response": {"reason": "conversion_in_progress"}},
            )
            start = len(self.streamed)
            for index, chunk in enumerate(self.chunks, start):
                frame: dict[str, Any] = {"content": chunk}
                if self.chunk_indexes:
                    frame["index"] = index
                sock._push(None, "chunk", frame)
            sock._push(None, "conversion_complete", {"format": "html_stream", "output_id": "p"})
            return
        if self.rate_limited_once:
            self.rate_limited_once = False
            sock._push(
                ref, "phx_reply", {"status": "error", "response": {"reason": "rate_limited"}}
            )
            return
        if self.needs_purchase:
            sock._push(
                ref,
                "phx_reply",
                {
                    "status": "error",
                    "response": {
                        "reason": "needs_purchase",
                        "message": "You need more pages.",
                        "purchase_url": "https://scribe.test/buy",
                    },
                },
            )
            return
        if not doc.unlocked:
            if payload.get("password") != doc.password:
                sock._push(ref, "phx_reply", {"status": "ok", "response": {"output_id": "o"}})
                sock._push(
                    None,
                    "error",
                    {"reason": "invalid_password", "message": "That password is not right."},
                )
                return
            doc.unlocked = True
        sock._push(ref, "phx_reply", {"status": "ok", "response": {"output_id": f"{fmt}-1"}})
        if fmt in self.error_for_format:
            reason, message = self.error_for_format[fmt]
            sock._push(None, "error", {"reason": reason, "message": message})
            return
        for index, stage in enumerate(self.stages):
            sock._push(
                None,
                "status",
                {"format": fmt, "stage": stage, "progress": (index + 1) / len(self.stages)},
            )
        doc.outputs[fmt] = "complete"
        sock._push(None, "conversion_complete", {"format": fmt, "output_id": f"{fmt}-1"})

    # ---------------------------------------------------------------- OAuth

    def poster(self, url: str, fields: dict[str, str]) -> dict[str, Any]:
        self.token_posts.append(dict(fields))
        path = urlsplit(url).path
        if path == "/oauth/revoke":
            self.revoked.append(fields.get("token", ""))
            return {}
        grant = fields.get("grant_type")
        if grant == "authorization_code" and fields.get("code") == "good-code":
            return {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_in": 3600,
            }
        if grant == "refresh_token" and fields.get("refresh_token") == self.refresh_token:
            self.access_token = self.access_token + "x"
            return {"access_token": self.access_token, "expires_in": 3600}
        return {"error": "invalid_grant", "message": "Your session has expired."}


def _ext(fmt: str) -> str:
    return {"daisy": "zip", "offline_html": "zip"}.get(fmt, fmt)


class MemorySecrets:
    """A SecretsManager backend kept in a dict."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def load(self, cred_name: str) -> str:
        return self.values.get(cred_name, "")

    def save(self, cred_name: str, value: str) -> None:
        self.values[cred_name] = value

    def delete(self, cred_name: str) -> bool:
        return self.values.pop(cred_name, None) is not None


class StaticTokens:
    """A TokenSource that reads the fake's current token and refreshes it."""

    def __init__(self, server: FakeScribe) -> None:
        self.server = server
        self.refreshes = 0

    def access_token(self) -> str:
        return self.server.access_token

    def force_refresh(self) -> str:
        self.refreshes += 1
        return self.server.access_token


class FakeClock:
    """A clock that moves only when slept on, for the runner's waits."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        self.now += 0.001
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(seconds, 0.01)
