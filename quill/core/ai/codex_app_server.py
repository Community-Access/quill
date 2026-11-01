"""The Codex app-server child process and its JSON-RPC client (codex.md 2, 5.2).

One app's agent task on its ChatGPT plan runs as a child process: the bundled
``codex-app-server.exe`` (:mod:`quill.core.ai.codex_binary`). This module
starts it, speaks its protocol and stops it. It never decides anything about
tools or approvals -- :mod:`quill.core.ai.harness.codex` does that.

What the pinned binary (rust-v0.166.0) says, read from its own ``--help`` and
its embedded protocol names (the standalone exe has no
``generate-json-schema`` subcommand, so there is no generated schema):

- **Launch.** The standalone exe takes no ``app-server`` subcommand (codex.md
  2.1 describes the multi-tool ``codex`` exe): it is
  ``codex-app-server.exe --listen stdio:// -c key=value ...``.
- **Wire.** Newline-delimited JSON-RPC with the ``"jsonrpc"`` field omitted:
  requests ``{id, method, params}``, answers ``{id, result | error}``,
  notifications ``{method, params}``. The server also sends requests:
  ``item/tool/call``, the approvals, ``item/tool/requestUserInput``,
  ``mcpServer/elicitation/request``, ``account/chatgptAuthTokens/refresh``.
- **Handshake.** ``initialize {clientInfo {name, title, version},
  capabilities {experimentalApi}}`` then the ``initialized`` notification.

Rules this module keeps (codex.md 2.1, 2.3, 2.4, 5.2, 5.4, 8, G4):

- The binary comes only from :func:`find_codex_app_server` and must match the
  build pin before **every** launch, or :class:`CodexBinaryError`.
- Safe Mode refuses to start (:class:`CodexSafeModeError`).
- The plan token goes only into the child's ``ACCESS_TOKEN``; the child gets a
  minimal environment, never this process's. The token is also remembered by
  :func:`quill.stability.redaction.remember_secret`, so no log line carries it.
- ``CODEX_HOME`` is this app's own per-task folder; the working directory is
  the empty ``work`` folder beside it.
- :meth:`CodexAppServer.close` closes stdin, then kills the child; it is gone
  within :data:`CLOSE_SECONDS`.

wx-free, strict-typed.
"""

from __future__ import annotations

import itertools
import json
import logging
import os
import subprocess
import sys
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import IO, Any

from quill import __version__
from quill.core.ai.agent_workdir import AgentFolders
from quill.core.ai.codex_binary import codex_app_server_matches_pin, find_codex_app_server
from quill.core.error_codes import CodedError
from quill.stability.redaction import (
    redact_known_secrets,
    redact_source_tokens,
    remember_secret,
)
from quill.stability.safe_mode import should_enable_safe_mode
from quill.stability.safe_subprocess import spawn_subprocess_safely

__all__ = [
    "CodexError",
    "CodexBinaryError",
    "CodexSafeModeError",
    "CodexProtocolError",
    "CodexRpcError",
    "CodexRpc",
    "CodexAppServer",
    "PROVIDER_ID",
    "TOKEN_ENV",
    "DISABLED_FEATURES",
    "STOP_SECONDS",
    "CLOSE_SECONDS",
    "launch_overrides",
    "thread_config",
    "command_line",
    "child_env",
]

_log = logging.getLogger(__name__)

#: Stop must end the turn within this long (G4).
STOP_SECONDS = 1.0
#: Closing must have the child gone within this long (G4).
CLOSE_SECONDS = 2.0

#: The model provider QUILL defines for the plan (codex.md 2.1).
PROVIDER_ID = "openai_chatgpt_plan"
#: The child's environment variable that carries the plan token (2.3).
TOKEN_ENV = "ACCESS_TOKEN"
_API_BASE = "https://api.openai.com/v1"

#: Codex's own tools and services, every one off (2.4, G3). Names are the
#: feature keys embedded in the pinned binary; the first seven are 2.4's list.
DISABLED_FEATURES: tuple[str, ...] = (
    "shell_tool",
    "unified_exec",
    "apps",
    "plugins",
    "image_generation",
    "hooks",
    "view_image",
    "plugin_hooks",
    "apply_patch_freeform",
    "js_repl",
    "browser_use",
    "computer_use",
    "in_app_browser",
    "multi_agent",
    "multi_agent_v2",
    "web_search_request",
    "web_search_cached",
    "standalone_web_search",
    "search_tool",
    "tool_search",
    "request_permissions_tool",
    "enable_mcp_apps",
    "memories",
    "sleep_tool",
    "goals",
)

#: Environment variables the child may inherit (case-insensitive on Windows).
#: Everything else -- every API key, GitHub token and QUILL setting -- stays out.
_CHILD_ENV_KEEP = frozenset({
    "SYSTEMROOT",
    "WINDIR",
    "SYSTEMDRIVE",
    "TEMP",
    "TMP",
    "PATH",
    "PATHEXT",
    "PROGRAMDATA",
    "LOCALAPPDATA",
    "APPDATA",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
    "OS",
    "LANG",
    "TZ",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "NO_PROXY",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
})


class CodexError(CodedError):
    """The Codex engine could not do what was asked."""

    code = "QUILL-AI-CODEX-FAILED"


class CodexBinaryError(CodexError):
    """The bundled app-server is missing, or is not the one this build pinned."""

    code = "QUILL-AI-CODEX-BINARY-UNVERIFIED"


class CodexSafeModeError(CodexError):
    """Safe Mode is on: no agent engine starts (G4)."""

    code = "QUILL-AI-CODEX-SAFE-MODE"


class CodexProtocolError(CodexError):
    """The child closed, timed out, or sent something that is not the protocol."""

    code = "QUILL-AI-CODEX-PROTOCOL"


class CodexRpcError(CodexError):
    """The app-server answered a request with a JSON-RPC error."""

    code = "QUILL-AI-CODEX-RPC"

    def __init__(self, message: str, *, rpc_code: int = -32603, data: Any = None) -> None:
        super().__init__(message)
        self.rpc_code = rpc_code
        self.data = data


def launch_overrides() -> list[str]:
    """The ``-c key=value`` overrides, values in TOML (codex.md 2.1, 2.4)."""
    provider = f"model_providers.{PROVIDER_ID}"
    overrides = [
        f'model_provider="{PROVIDER_ID}"',
        f'{provider}.name="ChatGPT plan"',
        f'{provider}.base_url="{_API_BASE}"',
        f'{provider}.env_key="{TOKEN_ENV}"',
        f'{provider}.wire_api="responses"',
        f"{provider}.requires_openai_auth=false",
        f"{provider}.supports_websockets=false",
        f"{provider}.supports_standalone_web_search=false",
        'web_search="disabled"',
        'shell_environment_policy.inherit="none"',
        "analytics.enabled=false",
        "features.skip_host_skill_discovery=true",
    ]
    overrides.extend(f"features.{name}=false" for name in DISABLED_FEATURES)
    return overrides


def thread_config() -> dict[str, Any]:
    """The same switches as ``thread/start``'s ``config`` map (belt and braces)."""
    config: dict[str, Any] = {f"features.{name}": False for name in DISABLED_FEATURES}
    config["web_search"] = "disabled"
    return config


def command_line(binary: Path) -> list[str]:
    """The child's argv: stdio transport plus every override."""
    argv = [str(binary), "--listen", "stdio://"]
    for override in launch_overrides():
        argv.extend(["-c", override])
    return argv


def child_env(token: str, home: Path, *, base: dict[str, str] | None = None) -> dict[str, str]:
    """The child's whole environment: a short allowlist, ``CODEX_HOME``, the token."""
    source = dict(os.environ) if base is None else base
    env = {key: value for key, value in source.items() if key.upper() in _CHILD_ENV_KEEP}
    env["CODEX_HOME"] = str(home)
    env[TOKEN_ENV] = token
    return env


NotificationHandler = Callable[[str, dict[str, Any]], None]
#: Answers a server request; raise :class:`CodexRpcError` to answer with an error.
RequestHandler = Callable[[str, dict[str, Any]], dict[str, Any]]


class CodexRpc:
    """Line-delimited JSON-RPC over a pair of byte streams.

    Notifications are delivered in order on the reader thread. Each server
    request runs on its own thread, so a tool call waiting on an approval
    never stops the reader -- and so Stop can still be heard.
    """

    def __init__(
        self,
        reader: IO[bytes],
        writer: IO[bytes],
        *,
        on_notification: NotificationHandler,
        on_request: RequestHandler,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._on_notification = on_notification
        self._on_request = on_request
        self._ids = itertools.count(1)
        self._pending: dict[int, Future[Any]] = {}
        self._pending_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._closed = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._read_loop, name="codex-rpc", daemon=True)
        self._thread.start()

    def request(self, method: str, params: dict[str, Any] | None, *, timeout: float) -> Any:
        """Send a request and wait for its answer's ``result``."""
        request_id = next(self._ids)
        future: Future[Any] = Future()
        with self._pending_lock:
            if self._closed.is_set():
                raise CodexProtocolError("The Codex engine has closed.")
            self._pending[request_id] = future
        message: dict[str, Any] = {"id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        try:
            self._send(message)
            return future.result(timeout=timeout)
        except FutureTimeout as exc:
            raise CodexProtocolError(f"The Codex engine did not answer {method}.") from exc
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"method": method}
        if params is not None:
            message["params"] = params
        self._send(message)

    def _send(self, message: dict[str, Any]) -> None:
        line = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        with self._write_lock:
            try:
                self._writer.write(line)
                self._writer.flush()
            except (OSError, ValueError) as exc:
                raise CodexProtocolError("The Codex engine is not listening.") from exc

    def _read_loop(self) -> None:
        try:
            for raw in iter(self._reader.readline, b""):
                try:
                    message = json.loads(raw)
                except ValueError:
                    _log.debug("Codex sent a line that is not JSON; ignored.")
                    continue
                if isinstance(message, dict):
                    self._dispatch(message)
        except (OSError, ValueError):
            pass
        finally:
            self._finish()

    def _finish(self) -> None:
        with self._pending_lock:
            self._closed.set()
            pending = list(self._pending.values())
            self._pending.clear()
        for future in pending:
            if not future.done():
                future.set_exception(CodexProtocolError("The Codex engine closed."))

    def _dispatch(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        params = message.get("params")
        params = params if isinstance(params, dict) else {}
        if isinstance(method, str) and "id" in message:
            threading.Thread(
                target=self._serve,
                args=(message["id"], method, params),
                name="codex-server-request",
                daemon=True,
            ).start()
        elif isinstance(method, str):
            try:
                self._on_notification(method, params)
            except Exception:  # noqa: BLE001 - one bad handler must not stop the reader
                _log.exception("Codex notification handler failed for %s", method)
        elif "id" in message:
            self._resolve(message)

    def _resolve(self, message: dict[str, Any]) -> None:
        with self._pending_lock:
            future = self._pending.get(message["id"]) if isinstance(message["id"], int) else None
        if future is None or future.done():
            return
        error = message.get("error")
        if isinstance(error, dict):
            future.set_exception(
                CodexRpcError(
                    str(error.get("message") or "The Codex engine refused the request."),
                    rpc_code=int(error.get("code", -32603) or -32603),
                    data=error.get("data"),
                )
            )
        else:
            future.set_result(message.get("result"))

    def _serve(self, request_id: Any, method: str, params: dict[str, Any]) -> None:
        reply: dict[str, Any] = {"id": request_id}
        try:
            reply["result"] = self._on_request(method, params)
        except CodexRpcError as exc:
            reply["error"] = {"code": exc.rpc_code, "message": exc.args[0] if exc.args else ""}
        except Exception:  # noqa: BLE001 - a handler failure is an error answer, not a hang
            _log.exception("Codex server request handler failed for %s", method)
            reply["error"] = {"code": -32603, "message": "QUILL could not answer this request."}
        try:
            self._send(reply)
        except CodexProtocolError:
            pass


Spawn = Callable[..., "subprocess.Popen[bytes]"]


class CodexAppServer:
    """One running app-server child for one app's task. See the module doc."""

    def __init__(
        self,
        *,
        agent_name: str,
        folders: AgentFolders,
        token: str,
        on_notification: NotificationHandler,
        on_request: RequestHandler,
        binary_resolver: Callable[[], Path | None] = find_codex_app_server,
        pin_check: Callable[[Path], bool] = codex_app_server_matches_pin,
        spawn: Spawn = spawn_subprocess_safely,
        argv: Sequence[str] = (),
        request_timeout: float = 30.0,
    ) -> None:
        self.agent_name = agent_name
        self._folders = folders
        self._token = token
        self._on_notification = on_notification
        self._on_request = on_request
        self._resolve_binary = binary_resolver
        self._pin_check = pin_check
        self._spawn = spawn
        self._argv = list(argv) or list(sys.argv)
        self._timeout = request_timeout
        self._proc: subprocess.Popen[bytes] | None = None
        self._rpc: CodexRpc | None = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def process(self) -> subprocess.Popen[bytes] | None:
        return self._proc

    def start(self) -> dict[str, Any]:
        """Verify, launch and initialize. Returns the ``initialize`` result."""
        if should_enable_safe_mode(self._argv, os.environ):
            raise CodexSafeModeError("Safe Mode is on, so AI agents are off.")
        if not self._token:
            raise CodexError("This app is not signed in with ChatGPT.")
        binary = self._resolve_binary()
        if binary is None:
            raise CodexBinaryError("This build does not include the Codex engine.")
        if not self._pin_check(binary):
            raise CodexBinaryError(
                "The Codex engine on this computer is not the one this release "
                "shipped, so QUILL will not start it."
            )
        remember_secret(self._token)
        self._folders.work.mkdir(parents=True, exist_ok=True)
        self._folders.home.mkdir(parents=True, exist_ok=True)
        proc = self._spawn(
            command_line(binary),
            cwd=str(self._folders.work),
            env=child_env(self._token, self._folders.home),
        )
        self._proc = proc
        if proc.stdout is None or proc.stdin is None:
            self.close()
            raise CodexProtocolError("The Codex engine started without its pipes.")
        if proc.stderr is not None:
            threading.Thread(
                target=_drain_stderr, args=(proc.stderr,), name="codex-stderr", daemon=True
            ).start()
        self._rpc = CodexRpc(
            proc.stdout,
            proc.stdin,
            on_notification=self._on_notification,
            on_request=self._on_request,
        )
        self._rpc.start()
        try:
            result = self.request(
                "initialize",
                {
                    "clientInfo": {
                        "name": self.agent_name,
                        "title": self.agent_name,
                        "version": __version__,
                    },
                    "capabilities": {"experimentalApi": True},
                },
            )
            self._rpc.notify("initialized")
        except CodexError:
            self.close()
            raise
        return result if isinstance(result, dict) else {}

    def request(self, method: str, params: dict[str, Any] | None, *, timeout: float = 0) -> Any:
        if self._rpc is None:
            raise CodexProtocolError("The Codex engine is not running.")
        return self._rpc.request(method, params, timeout=timeout or self._timeout)

    def thread_start(self, params: dict[str, Any]) -> str:
        return _thread_id(self.request("thread/start", params))

    def thread_resume(self, thread_id: str, params: dict[str, Any] | None = None) -> str:
        body = dict(params or {})
        body["threadId"] = thread_id
        return _thread_id(self.request("thread/resume", body)) or thread_id

    def turn_start(self, thread_id: str, text: str) -> str:
        result = self.request(
            "turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": text}]}
        )
        turn = result.get("turn") if isinstance(result, dict) else None
        return str(turn.get("id", "")) if isinstance(turn, dict) else ""

    def turn_interrupt(self, thread_id: str, turn_id: str, *, timeout: float = 0.5) -> bool:
        """Ask the turn to end; True when the server acknowledged in time."""
        try:
            self.request(
                "turn/interrupt", {"threadId": thread_id, "turnId": turn_id}, timeout=timeout
            )
            return True
        except CodexError:
            return False

    def read_rate_limits(self, *, timeout: float = 5.0) -> dict[str, Any] | None:
        """``account/rateLimits/read``; None when the plan provider reports nothing."""
        try:
            result = self.request("account/rateLimits/read", None, timeout=timeout)
        except CodexError:
            return None
        return result if isinstance(result, dict) else None

    def close(self, timeout: float = CLOSE_SECONDS) -> None:
        """End the child: stdin closed first, killed if it lingers (G4)."""
        proc, self._proc = self._proc, None
        self._rpc = None
        if proc is None:
            return
        try:
            if proc.stdin is not None:
                proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=timeout / 4)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=timeout / 2)
            except subprocess.TimeoutExpired:
                _log.warning("The Codex engine did not exit after being killed.")
        for stream in (proc.stdout, proc.stderr):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass


def _thread_id(result: Any) -> str:
    thread = result.get("thread") if isinstance(result, dict) else None
    return str(thread.get("id", "")) if isinstance(thread, dict) else ""


def _drain_stderr(stream: IO[bytes]) -> None:
    """Keep the child's stderr from filling its pipe; log it redacted, briefly."""
    lines = 0
    try:
        for raw in iter(stream.readline, b""):
            lines += 1
            if lines <= 200:
                text = raw.decode("utf-8", errors="replace").rstrip()
                _log.debug("codex: %s", redact_source_tokens(redact_known_secrets(text))[:500])
    except (OSError, ValueError):
        pass
