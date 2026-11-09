"""The running language servers: started on first use, stopped when unused.

One :class:`LanguageServerPool` per process. A server starts the first time
something asks it about a file it serves (Ctrl+., Check This File, parameter
hints), never at launch, so it costs nothing until then. It stops when the
last document of its language closes, and every server stops at exit.

Every method that talks to a server blocks for at most a few seconds and is
meant for a background task; nothing here may run on the UI thread.
"""

from __future__ import annotations

import atexit
import logging
import threading
import time
from pathlib import Path
from typing import Any

from quill.core.lsp.client import LspClient, LspError
from quill.core.lsp.convert import (
    QuickFix,
    ServerCompletion,
    completion_names,
    lsp_position,
    problems_from_diagnostics,
    quick_fixes,
    signature_sentence,
)
from quill.core.lsp.protocol import uri_for_path
from quill.core.lsp.servers import (
    ServerSpec,
    language_id_for,
    resolve_server,
    server_for_path,
)
from quill.core.problems.model import Problem

__all__ = ["LanguageServerPool", "shared_pool"]

logger = logging.getLogger(__name__)

#: How long a check waits for a server's diagnostics after sending the text.
DIAGNOSTICS_WAIT = 3.0
#: How long a server may sit unused before it is stopped (it restarts on demand).
IDLE_STOP = 15 * 60.0
#: After a server fails to start, how long before it is tried again.
RETRY_AFTER = 300.0


class LanguageServerPool:
    """Clients by (server, project root), and the diagnostics they publish."""

    def __init__(self, *, spawn: Any = None) -> None:
        self._spawn = spawn
        self._clients: dict[tuple[str, Path], LspClient] = {}
        self._failed: dict[tuple[str, Path], float] = {}
        self._diagnostics: dict[str, list[dict[str, Any]]] = {}
        self._arrived: dict[str, threading.Event] = {}
        self._used: dict[tuple[str, Path], float] = {}
        self._lock = threading.Lock()

    def _stop_idle(self) -> None:
        """Stop any server nobody has asked anything for :data:`IDLE_STOP` seconds."""
        now = time.monotonic()
        with self._lock:
            idle = [
                (key, client)
                for key, client in self._clients.items()
                if now - self._used.get(key, now) > IDLE_STOP
            ]
            for key, _client in idle:
                self._clients.pop(key, None)
        for _key, client in idle:
            client.stop()

    # -- which server ----------------------------------------------------------- #

    @staticmethod
    def spec_for(path: Path | None) -> ServerSpec | None:
        return server_for_path(path)

    def available(self, path: Path | None) -> bool:
        """True when a server for *path* is present here (bundled or installed)."""
        spec = server_for_path(path)
        return spec is not None and resolve_server(spec) is not None

    def client_for(self, path: Path, root: Path) -> LspClient | None:
        """The running client for *path*, started now if need be; None if absent."""
        spec = server_for_path(path)
        if spec is None:
            return None
        key = (spec.name, root)
        self._stop_idle()
        with self._lock:
            self._used[key] = time.monotonic()
            client = self._clients.get(key)
            if client is not None and client.alive:
                return client
            failed = self._failed.get(key)
            if failed is not None and time.monotonic() - failed < RETRY_AFTER:
                return None
        resolved = resolve_server(spec)
        if resolved is None:
            return None
        client = LspClient(resolved, root, on_diagnostics=self._store, spawn=self._spawn)
        try:
            client.start()
        except LspError:
            logger.exception("%s did not start", spec.name)
            client.stop()
            with self._lock:
                self._failed[key] = time.monotonic()
            return None
        with self._lock:
            self._clients[key] = client
        return client

    def _store(self, uri: str, diagnostics: list[dict[str, Any]]) -> None:
        with self._lock:
            self._diagnostics[uri] = diagnostics
            event = self._arrived.setdefault(uri, threading.Event())
        event.set()

    # -- what the editors ask ----------------------------------------------------- #

    def complete(
        self, path: Path, root: Path, text: str, offset: int, fragment: str, *, limit: int = 8
    ) -> list[ServerCompletion]:
        client = self.client_for(path, root)
        language = language_id_for(path)
        if client is None or language is None:
            return []
        uri = client.sync(path, language, text)
        try:
            result = client.request(
                "textDocument/completion",
                {"textDocument": {"uri": uri}, "position": lsp_position(text, offset)},
                timeout=3.0,
            )
        except LspError:
            return []
        return completion_names(result, fragment, limit=limit)

    def signature(self, path: Path, root: Path, text: str, offset: int) -> str:
        client = self.client_for(path, root)
        language = language_id_for(path)
        if client is None or language is None:
            return ""
        uri = client.sync(path, language, text)
        try:
            result = client.request(
                "textDocument/signatureHelp",
                {"textDocument": {"uri": uri}, "position": lsp_position(text, offset)},
                timeout=3.0,
            )
        except LspError:
            return ""
        return signature_sentence(result)

    def problems(self, path: Path, root: Path, text: str) -> list[Problem] | None:
        """The server's problems for *text*, or None when no server answered.

        Diagnostics are pushed, not asked for, so this sends the text and waits
        up to :data:`DIAGNOSTICS_WAIT` for the server to publish them.
        """
        client = self.client_for(path, root)
        language = language_id_for(path)
        if client is None or language is None:
            return None
        uri = uri_for_path(path)
        with self._lock:
            event = self._arrived.setdefault(uri, threading.Event())
            event.clear()
        client.sync(path, language, text)
        if client.capabilities.get("diagnosticProvider"):
            # LSP 3.17 pull diagnostics (the VS Code Markdown server): ask.
            try:
                report = client.request(
                    "textDocument/diagnostic", {"textDocument": {"uri": uri}}, timeout=5.0
                )
            except LspError:
                report = None
            if isinstance(report, dict) and report.get("kind") == "full":
                self._store(uri, list(report.get("items") or []))
        if not event.wait(DIAGNOSTICS_WAIT):
            with self._lock:
                stored = self._diagnostics.get(uri)
            if stored is None:
                return None
        with self._lock:
            diagnostics = list(self._diagnostics.get(uri, []))
        return problems_from_diagnostics(diagnostics, source=client.server.spec.name)

    def fixes(self, path: Path, root: Path, text: str, problem: Problem) -> list[QuickFix]:
        """Quick Fix: the server's code actions for *problem* that edit only this file."""
        client = self.client_for(path, root)
        language = language_id_for(path)
        if client is None or language is None:
            return []
        uri = client.sync(path, language, text)
        with self._lock:
            diagnostics = [
                item
                for item in self._diagnostics.get(uri, [])
                if int(((item.get("range") or {}).get("start") or {}).get("line", -1)) + 1
                == problem.line
            ]
        start = {"line": problem.line - 1, "character": max(0, problem.column - 1)}
        try:
            actions = client.request(
                "textDocument/codeAction",
                {
                    "textDocument": {"uri": uri},
                    "range": {"start": start, "end": start},
                    "context": {"diagnostics": diagnostics, "only": ["quickfix"]},
                },
                timeout=5.0,
            )
        except LspError:
            return []
        return quick_fixes(actions, uri, text)

    # -- ending --------------------------------------------------------------------- #

    def close(self, path: Path) -> None:
        """A document closed: tell its server, and stop the server if it was the last."""
        spec = server_for_path(path)
        if spec is None:
            return
        with self._lock:
            matching = [
                (key, client) for key, client in self._clients.items() if key[0] == spec.name
            ]
        for key, client in matching:
            client.close(path)
            if client.open_documents == 0:
                client.stop()
                with self._lock:
                    self._clients.pop(key, None)

    def shutdown(self) -> None:
        with self._lock:
            clients = list(self._clients.values())
            self._clients.clear()
        for client in clients:
            client.stop()

    def running(self) -> list[str]:
        with self._lock:
            return sorted({key[0] for key, client in self._clients.items() if client.alive})


_POOL: LanguageServerPool | None = None
_POOL_LOCK = threading.Lock()


def shared_pool() -> LanguageServerPool:
    """The process's one pool, made on first use; every server stops at exit."""
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            _POOL = LanguageServerPool()
            atexit.register(_POOL.shutdown)
        return _POOL
