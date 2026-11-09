"""The language-server client and pool (quill.core.lsp.client, .pool), driven
against a scripted server that speaks the protocol over in-memory pipes."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest

from quill.core.lsp import pool as pool_module
from quill.core.lsp.client import LspClient, LspError
from quill.core.lsp.pool import LanguageServerPool
from quill.core.lsp.protocol import FrameReader, encode_message
from quill.core.lsp.servers import ResolvedServer, server_for_path


class _Pipe:
    """A blocking byte pipe: write() on one side, read() on the other."""

    def __init__(self) -> None:
        self._data = bytearray()
        self._closed = False
        self._cond = threading.Condition()

    def write(self, data: bytes) -> int:
        with self._cond:
            self._data.extend(data)
            self._cond.notify_all()
        return len(data)

    def flush(self) -> None:
        pass

    def read(self, size: int = -1) -> bytes:
        with self._cond:
            while not self._data and not self._closed:
                self._cond.wait(5)
            chunk = bytes(self._data[:size] if size > 0 else self._data)
            del self._data[: len(chunk)]
            return chunk

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify_all()


class FakeServer:
    """Answers initialize, completion, signatureHelp and codeAction; publishes
    diagnostics on didOpen and didChange."""

    def __init__(self, *, slow: bool = False, pull: bool = False) -> None:
        self.stdin = _Pipe()
        self.stdout = _Pipe()
        self.stderr = _Pipe()
        self.slow = slow
        self.pull = pull
        self.seen: list[str] = []
        self.killed = False
        threading.Thread(target=self._serve, daemon=True).start()

    def _send(self, message: dict[str, Any]) -> None:
        self.stdout.write(encode_message(message))

    def _serve(self) -> None:
        reader = FrameReader()
        while True:
            chunk = self.stdin.read(65536)
            if not chunk:
                return
            for message in reader.feed(chunk):
                self._handle(message)

    def _handle(self, message: dict[str, Any]) -> None:
        method = message.get("method", "")
        self.seen.append(method)
        params = message.get("params") or {}
        if method == "initialize":
            caps: dict[str, Any] = {"completionProvider": {}}
            if self.pull:
                caps["diagnosticProvider"] = {}
            # The server asks its client something before answering.
            self._send({
                "jsonrpc": "2.0",
                "id": 900,
                "method": "workspace/configuration",
                "params": {"items": [{"section": "json"}]},
            })
            self._send({"jsonrpc": "2.0", "id": message["id"], "result": {"capabilities": caps}})
        elif method == "textDocument/completion":
            if self.slow:
                return
            self._send({
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": [{"label": "counter", "kind": 6}, {"label": "count", "kind": 3}],
            })
        elif method == "textDocument/signatureHelp":
            self._send({
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "signatures": [
                        {"label": "f(a, b)", "parameters": [{"label": "a"}, {"label": "b"}]}
                    ],
                    "activeParameter": 1,
                },
            })
        elif method == "textDocument/codeAction":
            uri = params["textDocument"]["uri"]
            edit = {
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 3}},
                "newText": "const",
            }
            self._send({
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": [{"title": "Use const", "edit": {"changes": {uri: [edit]}}}],
            })
        elif method == "textDocument/diagnostic":
            self._send({
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "kind": "full",
                    "items": [
                        {"range": {"start": {"line": 0, "character": 0}}, "message": "pulled"}
                    ],
                },
            })
        elif method in ("textDocument/didOpen", "textDocument/didChange") and not self.pull:
            uri = params["textDocument"]["uri"]
            self._send({
                "jsonrpc": "2.0",
                "method": "textDocument/publishDiagnostics",
                "params": {
                    "uri": uri,
                    "diagnostics": [
                        {
                            "range": {"start": {"line": 0, "character": 4}},
                            "severity": 1,
                            "message": "pushed",
                        }
                    ],
                },
            })
        elif method == "shutdown":
            self._send({"jsonrpc": "2.0", "id": message["id"], "result": None})
        elif method == "exit":
            self.stdout.close()

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def kill(self) -> None:
        self.killed = True
        self.stdout.close()


def _eventually(check: Any, seconds: float = 2.0) -> bool:
    """The fake server reads on its own thread; give it a moment to see a notification."""
    import time

    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.01)
    return bool(check())


def _resolved(name: str = "x.ts") -> ResolvedServer:
    spec = server_for_path(name)
    assert spec is not None
    return ResolvedServer(spec, ("node", "server.js", "--stdio"))


def test_handshake_completion_hint_and_the_servers_own_request(tmp_path: Path) -> None:
    server = FakeServer()
    client = LspClient(_resolved(), tmp_path, spawn=lambda argv, cwd: server)
    client.start()
    assert "completionProvider" in client.capabilities
    uri = client.sync(tmp_path / "a.ts", "typescript", "let cou")
    result = client.request("textDocument/completion", {"textDocument": {"uri": uri}})
    assert [item["label"] for item in result] == ["counter", "count"]
    assert server.seen[:2] == ["initialize", ""], "the client answered workspace/configuration"
    client.stop()
    assert _eventually(lambda: "exit" in server.seen) and "shutdown" in server.seen


def test_a_slow_server_times_out_and_is_told_to_cancel(tmp_path: Path) -> None:
    server = FakeServer(slow=True)
    client = LspClient(_resolved(), tmp_path, spawn=lambda argv, cwd: server)
    client.start()
    with pytest.raises(LspError, match="took longer"):
        client.request("textDocument/completion", {}, timeout=0.2)
    assert _eventually(lambda: "$/cancelRequest" in server.seen)


def test_a_server_that_will_not_start_is_an_lsp_error(tmp_path: Path) -> None:
    def refuse(argv: list[str], cwd: str) -> Any:
        raise OSError("no such file")

    client = LspClient(_resolved(), tmp_path, spawn=refuse)
    with pytest.raises(LspError, match="did not start"):
        client.start()


def test_documents_sync_once_then_only_on_change(tmp_path: Path) -> None:
    server = FakeServer()
    client = LspClient(_resolved(), tmp_path, spawn=lambda argv, cwd: server)
    client.start()
    path = tmp_path / "a.ts"
    client.sync(path, "typescript", "a")
    client.sync(path, "typescript", "a")
    client.sync(path, "typescript", "ab")
    client.request("textDocument/completion", {})
    assert server.seen.count("textDocument/didOpen") == 1
    assert server.seen.count("textDocument/didChange") == 1
    client.close(path)
    assert client.open_documents == 0


@pytest.fixture
def fake_pool(monkeypatch, tmp_path: Path):
    servers_started: list[FakeServer] = []

    def spawn(argv: list[str], cwd: str) -> FakeServer:
        server = FakeServer(pull=getattr(spawn, "pull", False))
        servers_started.append(server)
        return server

    monkeypatch.setattr(pool_module, "resolve_server", lambda spec: _resolved_for(spec))
    pool = LanguageServerPool(spawn=spawn)
    pool.started = servers_started  # type: ignore[attr-defined]
    pool.spawn = spawn  # type: ignore[attr-defined]
    yield pool
    pool.shutdown()


def _resolved_for(spec: Any) -> ResolvedServer:
    return ResolvedServer(spec, ("node", "server.js"))


def test_pool_completes_hints_problems_and_fixes(fake_pool, tmp_path: Path) -> None:
    path = tmp_path / "a.ts"
    names = fake_pool.complete(path, tmp_path, "let cou", 7, "cou")
    assert [(n.label, n.kind) for n in names] == [("count", "function"), ("counter", "variable")]
    assert fake_pool.signature(path, tmp_path, "f(1, ", 5) == "Parameter 2 of 2, b. f(a, b)"
    problems = fake_pool.problems(path, tmp_path, "let x")
    assert [(p.line, p.column, p.message) for p in problems] == [(1, 5, "pushed")]
    fixes = fake_pool.fixes(path, tmp_path, "let x", problems[0])
    assert [f.title for f in fixes] == ["Use const"]
    assert len(fake_pool.started) == 1, "one server per language and project, reused"
    assert fake_pool.running() == ["TypeScript server"]


def test_pull_diagnostics_are_asked_for(fake_pool, tmp_path: Path, monkeypatch) -> None:
    fake_pool.spawn.pull = True
    monkeypatch.setattr(pool_module, "DIAGNOSTICS_WAIT", 0.5)
    problems = fake_pool.problems(tmp_path / "a.ts", tmp_path, "x")
    assert [p.message for p in problems] == ["pulled"]


def test_closing_the_last_document_stops_the_server(fake_pool, tmp_path: Path) -> None:
    path = tmp_path / "a.ts"
    fake_pool.complete(path, tmp_path, "x", 1, "x")
    fake_pool.close(path)
    assert fake_pool.running() == []


def test_an_idle_server_is_stopped_and_restarts_on_demand(
    fake_pool, tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "a.ts"
    fake_pool.complete(path, tmp_path, "x", 1, "x")
    monkeypatch.setattr(pool_module, "IDLE_STOP", -1.0)
    fake_pool.complete(tmp_path / "b.py", tmp_path, "x", 1, "x")
    assert "TypeScript server" not in fake_pool.running()


def test_a_server_that_fails_is_not_retried_at_once(monkeypatch, tmp_path: Path) -> None:
    calls: list[int] = []

    def refuse(argv: list[str], cwd: str) -> Any:
        calls.append(1)
        raise OSError("nope")

    monkeypatch.setattr(pool_module, "resolve_server", _resolved_for)
    pool = LanguageServerPool(spawn=refuse)
    assert pool.complete(tmp_path / "a.ts", tmp_path, "x", 1, "x") == []
    assert pool.complete(tmp_path / "a.ts", tmp_path, "x", 1, "x") == []
    assert calls == [1]
