"""One running language server, spoken to over its standard input and output.

:class:`LspClient` starts an allowlisted server (:mod:`quill.core.lsp.servers`)
through :func:`quill.stability.safe_subprocess.spawn_subprocess_safely`, does
the ``initialize`` handshake, keeps each open document's text in step with
full-text ``didOpen`` / ``didChange``, and answers the few requests a server
makes of its client. Requests block the calling thread for at most their
timeout, so callers run them on the task manager, never on the UI thread.

Two daemon threads per server: one reads standard output and settles pending
requests; one drains standard error so a chatty server cannot block on a full
pipe. Diagnostics arrive as notifications and are handed to ``on_diagnostics``
from the reader thread; the caller marshals them to the UI.

No network: every server is started with the settings in its spec, which turn
off what would reach out.
"""

from __future__ import annotations

import itertools
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.lsp.protocol import FrameError, FrameReader, encode_message, uri_for_path
from quill.core.lsp.servers import ResolvedServer, language_servers_dir

__all__ = ["DiagnosticsCallback", "LspClient", "LspError"]

logger = logging.getLogger(__name__)

#: ``on_diagnostics(uri, diagnostics)``, called on the reader thread.
DiagnosticsCallback = Callable[[str, list[dict[str, Any]]], None]

#: How long ``initialize`` may take: Pyright reads typeshed on its first start.
INITIALIZE_TIMEOUT = 30.0


class LspError(CodedError):
    """A language server failed to start, answered with an error, or timed out."""

    code = "QUILL-CORE-LSP-REQUEST"


class _Pending:
    __slots__ = ("done", "error", "result")

    def __init__(self) -> None:
        self.done = threading.Event()
        self.result: Any = None
        self.error: dict[str, Any] | None = None


class LspClient:
    """A started server, its open documents, and its pending requests."""

    def __init__(
        self,
        server: ResolvedServer,
        root: Path,
        *,
        on_diagnostics: DiagnosticsCallback | None = None,
        spawn: Callable[..., Any] | None = None,
    ) -> None:
        self.server = server
        self.root = root
        self._on_diagnostics = on_diagnostics
        self._spawn = spawn
        self._process: Any = None
        self._ids = itertools.count(1)
        self._pending: dict[int, _Pending] = {}
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._versions: dict[str, int] = {}
        self._texts: dict[str, str] = {}
        self.capabilities: dict[str, Any] = {}
        self.alive = False

    # -- life ----------------------------------------------------------------- #

    def start(self) -> None:
        """Start the server and complete the handshake; raises :class:`LspError`."""
        spawn = self._spawn
        if spawn is None:
            from quill.stability.safe_subprocess import spawn_subprocess_safely

            spawn = spawn_subprocess_safely
        try:
            self._process = spawn(list(self.server.argv), cwd=str(self.root))
        except (OSError, ValueError) as error:
            raise LspError(f"{self.server.spec.name} did not start: {error}") from error
        self.alive = True
        threading.Thread(
            target=self._read_loop, name=f"lsp-{self.server.spec.name}", daemon=True
        ).start()
        threading.Thread(
            target=self._drain_stderr, name=f"lsp-err-{self.server.spec.name}", daemon=True
        ).start()
        result = self.request("initialize", self._initialize_params(), timeout=INITIALIZE_TIMEOUT)
        self.capabilities = dict((result or {}).get("capabilities") or {})
        self.notify("initialized", {})
        settings = self.server.spec.settings
        if settings:
            self.notify("workspace/didChangeConfiguration", {"settings": settings})

    def stop(self) -> None:
        """Ask the server to shut down, then make sure it has."""
        if not self.alive:
            return
        try:
            self.request("shutdown", None, timeout=3.0)
            self.notify("exit", None)
        except LspError:
            pass
        self.alive = False
        process = self._process
        if process is None:
            return
        try:
            process.wait(timeout=3.0)
        except Exception:  # noqa: BLE001 - it is going either way
            try:
                process.kill()
            except Exception:  # noqa: BLE001
                pass

    def _initialize_params(self) -> dict[str, Any]:
        options = _absolute_tsserver(dict(self.server.spec.init_options))
        return {
            "processId": None,
            "clientInfo": {"name": "QUILL", "version": "1.0"},
            "rootUri": uri_for_path(self.root),
            "workspaceFolders": [{"uri": uri_for_path(self.root), "name": self.root.name}],
            "initializationOptions": options,
            "capabilities": {
                "workspace": {"configuration": True, "workspaceFolders": True},
                "textDocument": {
                    "synchronization": {"didSave": True, "dynamicRegistration": False},
                    "completion": {
                        "completionItem": {
                            "snippetSupport": False,
                            "documentationFormat": ["plaintext", "markdown"],
                            "labelDetailsSupport": True,
                        },
                        "contextSupport": True,
                    },
                    "hover": {"contentFormat": ["plaintext", "markdown"]},
                    "signatureHelp": {
                        "signatureInformation": {
                            "documentationFormat": ["plaintext", "markdown"],
                            "parameterInformation": {"labelOffsetSupport": True},
                            "activeParameterSupport": True,
                        }
                    },
                    "publishDiagnostics": {"relatedInformation": False},
                    "diagnostic": {"dynamicRegistration": False},
                    "codeAction": {
                        "codeActionLiteralSupport": {
                            "codeActionKind": {"valueSet": ["quickfix", "refactor", "source"]}
                        },
                        "isPreferredSupport": True,
                    },
                },
            },
        }

    # -- documents ------------------------------------------------------------ #

    def sync(self, path: Path, language_id: str, text: str) -> str:
        """Open *path* in the server, or send its new text; returns its URI."""
        uri = uri_for_path(path)
        if uri not in self._versions:
            self._versions[uri] = 1
            self._texts[uri] = text
            self.notify(
                "textDocument/didOpen",
                {
                    "textDocument": {
                        "uri": uri,
                        "languageId": language_id,
                        "version": 1,
                        "text": text,
                    }
                },
            )
            return uri
        if self._texts.get(uri) != text:
            self._versions[uri] += 1
            self._texts[uri] = text
            self.notify(
                "textDocument/didChange",
                {
                    "textDocument": {"uri": uri, "version": self._versions[uri]},
                    "contentChanges": [{"text": text}],
                },
            )
        return uri

    def close(self, path: Path) -> None:
        uri = uri_for_path(path)
        if self._versions.pop(uri, None) is not None:
            self._texts.pop(uri, None)
            self.notify("textDocument/didClose", {"textDocument": {"uri": uri}})

    @property
    def open_documents(self) -> int:
        return len(self._versions)

    # -- the wire ------------------------------------------------------------- #

    def request(self, method: str, params: Any, *, timeout: float = 5.0) -> Any:
        """Send a request and wait for its answer; raises :class:`LspError`."""
        if not self.alive:
            raise LspError(f"{self.server.spec.name} is not running")
        request_id = next(self._ids)
        pending = _Pending()
        with self._lock:
            self._pending[request_id] = pending
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        if not pending.done.wait(timeout):
            with self._lock:
                self._pending.pop(request_id, None)
            self.notify("$/cancelRequest", {"id": request_id})
            raise LspError(f"{self.server.spec.name} took longer than {timeout:g} s for {method}")
        if pending.error is not None:
            raise LspError(f"{self.server.spec.name}: {pending.error.get('message', 'error')}")
        return pending.result

    def notify(self, method: str, params: Any) -> None:
        if self.alive:
            self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _send(self, message: dict[str, Any]) -> None:
        data = encode_message(message)
        with self._write_lock:
            try:
                self._process.stdin.write(data)
                self._process.stdin.flush()
            except (OSError, ValueError, AttributeError) as error:
                self.alive = False
                raise LspError(f"{self.server.spec.name} stopped listening: {error}") from error

    def _read_loop(self) -> None:
        reader = FrameReader()
        stream = self._process.stdout
        while True:
            try:
                chunk = stream.read(65536)
            except (OSError, ValueError):
                chunk = b""
            if not chunk:
                break
            try:
                messages = reader.feed(chunk)
            except FrameError:
                logger.exception("%s sent a bad frame", self.server.spec.name)
                break
            for message in messages:
                self._dispatch(message)
        self.alive = False
        with self._lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for item in pending:
            item.error = {"message": "the server stopped"}
            item.done.set()

    def _drain_stderr(self) -> None:
        stream = getattr(self._process, "stderr", None)
        if stream is None:
            return
        try:
            while stream.read(4096):
                pass
        except (OSError, ValueError):
            pass

    def _dispatch(self, message: dict[str, Any]) -> None:
        if "id" in message and "method" not in message:
            with self._lock:
                pending = self._pending.pop(message["id"], None)
            if pending is not None:
                pending.result = message.get("result")
                pending.error = message.get("error")
                pending.done.set()
            return
        method = message.get("method", "")
        if "id" in message:
            self._answer(message["id"], method, message.get("params"))
            return
        if method == "textDocument/publishDiagnostics" and self._on_diagnostics is not None:
            params = message.get("params") or {}
            try:
                self._on_diagnostics(
                    str(params.get("uri", "")), list(params.get("diagnostics") or [])
                )
            except Exception:  # noqa: BLE001 - a callback bug must not stop the reader
                logger.exception("diagnostics callback failed")

    def _answer(self, request_id: Any, method: str, params: Any) -> None:
        """The server's own requests: configuration, and the ones we just accept."""
        result: Any = None
        if method == "workspace/configuration":
            items = (params or {}).get("items") or []
            result = [_section(self.server.spec.settings, item.get("section")) for item in items]
        elif method == "workspace/workspaceFolders":
            result = [{"uri": uri_for_path(self.root), "name": self.root.name}]
        try:
            self._send({"jsonrpc": "2.0", "id": request_id, "result": result})
        except LspError:
            pass


def _section(settings: dict[str, Any], section: str | None) -> Any:
    if not section:
        return settings
    value: Any = settings
    for part in section.split("."):
        if not isinstance(value, dict) or part not in value:
            if section == "formattingOptions":
                return {"tabSize": 4, "insertSpaces": True}
            return None
        value = value[part]
    return value


def _absolute_tsserver(options: dict[str, Any]) -> dict[str, Any]:
    """Point typescript-language-server at the bundled TypeScript by absolute path."""
    tsserver = options.get("tsserver")
    if isinstance(tsserver, dict) and "path" in tsserver:
        folder = language_servers_dir()
        if folder is not None:
            options["tsserver"] = {**tsserver, "path": str(folder / tsserver["path"])}
        else:
            options["tsserver"] = {k: v for k, v in tsserver.items() if k != "path"}
    return options
