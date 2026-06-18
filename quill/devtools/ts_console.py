"""Python-side TypeScript console bridge.

Manages a long-lived Node.js subprocess (the worker) and provides a
synchronous ``execute(source)`` call from the UI thread's perspective.
The worker speaks the JSON-RPC protocol defined in ``ts_worker_protocol``.

Threading model:
- A dedicated reader thread drains Node stdout continuously.
- ``execute()`` runs on the UI thread: it sends a request and blocks on a
  threading.Event until the worker finishes or times out.
- ``wx.CallAfter`` is used by the *caller* (DevToolsMixin) for UI updates;
  nothing in this module touches wx directly.
"""

from __future__ import annotations

import os
import queue
import shutil
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.script_results import ScriptError, ScriptResult, ScriptSuccess
from quill.devtools.ts_worker_protocol import ExecuteMsg, ReturnMsg, parse_node_message

if TYPE_CHECKING:
    from quill.core.scripting import ConsoleHost

_DEFAULT_TIMEOUT = 30.0  # seconds
_WORKER_JS = Path(__file__).resolve().parents[2] / "tools" / "ts_worker" / "worker.js"


class TypeScriptConsoleError(RuntimeError):
    pass


class TypeScriptConsole:
    """Manages the Node worker subprocess and executes TypeScript code."""

    def __init__(
        self,
        host: ConsoleHost,
        timeout: float = _DEFAULT_TIMEOUT,
        ui_call: Callable[[Callable[[], Any]], Any] | None = None,
    ) -> None:
        self._host = host
        self._timeout = timeout
        self._ui_call = ui_call
        self._proc: subprocess.Popen[str] | None = None
        self._reader: threading.Thread | None = None
        # per-request: req_id -> (event, result_holder)
        self._pending: dict[str, tuple[threading.Event, list[ScriptResult]]] = {}
        self._pending_lock = threading.Lock()
        # (req_id, stream, text)
        self._output_queue: queue.Queue[tuple[str, str, str]] = queue.Queue()
        self._ready = threading.Event()
        self._stopped = False

    # ------------------------------------------------------------------
    # Lifecycle

    def start(self) -> None:
        """Launch the Node worker; raises TypeScriptConsoleError on failure."""
        if self._proc and self._proc.poll() is None:
            return  # already running
        node = shutil.which("node") or shutil.which("node.exe")
        if not node:
            raise TypeScriptConsoleError(
                "Node.js not found on PATH. Install Node.js to use the TypeScript console."
            )
        if not _WORKER_JS.exists():
            raise TypeScriptConsoleError(
                f"TypeScript worker not found: {_WORKER_JS}\n"
                "The QUILL installation may be incomplete."
            )
        self._stopped = False
        self._ready.clear()
        extra: dict = {}
        if os.name == "nt":
            extra["creationflags"] = subprocess.CREATE_NO_WINDOW
        self._proc = subprocess.Popen(
            [node, str(_WORKER_JS)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            **extra,
        )
        self._reader = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader.start()
        if not self._ready.wait(timeout=10.0):
            self.stop()
            raise TypeScriptConsoleError("TypeScript worker failed to start within 10 seconds.")

    def stop(self) -> None:
        """Terminate the Node worker."""
        self._stopped = True
        self._ready.clear()
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None
        with self._pending_lock:
            for evt, holder in self._pending.values():
                holder.append(ScriptError(message="TypeScript worker stopped."))
                evt.set()
            self._pending.clear()

    def restart(self) -> None:
        self.stop()
        time.sleep(0.3)
        self.start()

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # ------------------------------------------------------------------
    # Execution

    def execute(self, source: str) -> ScriptResult:
        """Execute *source* as TypeScript; blocks until done or timeout."""
        if not self.is_running():
            try:
                self.start()
            except TypeScriptConsoleError as exc:
                return ScriptError(message=str(exc))

        req_id = uuid.uuid4().hex
        event = threading.Event()
        holder: list[ScriptResult] = []
        with self._pending_lock:
            self._pending[req_id] = (event, holder)

        msg = ExecuteMsg(req_id=req_id, source=source)
        try:
            assert self._proc and self._proc.stdin
            self._proc.stdin.write(msg.to_json() + "\n")
            self._proc.stdin.flush()
        except OSError as exc:
            with self._pending_lock:
                self._pending.pop(req_id, None)
            return ScriptError(message=f"Failed to send to TypeScript worker: {exc}")

        if not event.wait(timeout=self._timeout):
            with self._pending_lock:
                self._pending.pop(req_id, None)
            return ScriptError(
                message=f"TypeScript execution timed out after {self._timeout:.0f} seconds.",
                suggestion="Use Restart TypeScript Worker to reset the worker.",
            )

        with self._pending_lock:
            self._pending.pop(req_id, None)
        return holder[0] if holder else ScriptError(message="No result received.")

    # ------------------------------------------------------------------
    # Background reader

    def _reader_loop(self) -> None:
        assert self._proc and self._proc.stdout
        for raw_line in self._proc.stdout:
            line = raw_line.rstrip("\n")
            if not line:
                continue
            try:
                msg = parse_node_message(line)
            except ValueError:
                continue
            self._dispatch(msg)
        if not self._stopped:
            with self._pending_lock:
                for evt, holder in self._pending.values():
                    holder.append(ScriptError(message="TypeScript worker exited unexpectedly."))
                    evt.set()
                self._pending.clear()

    def _dispatch(self, msg: dict[str, Any]) -> None:
        kind = msg.get("type")
        req_id = str(msg.get("id", ""))

        if kind == "ready":
            self._ready.set()
            return

        if kind == "output":
            stream = str(msg.get("stream", "log"))
            text = str(msg.get("text", ""))
            self._output_queue.put((req_id, stream, text))
            return

        if kind == "invoke":
            call_id = str(msg.get("call", ""))
            method = str(msg.get("method", ""))
            args = msg.get("args", [])
            if self._ui_call is not None:
                result = self._ui_call(lambda: self._handle_invoke(method, args))
            else:
                result = self._handle_invoke(method, args)
            ret_msg: ReturnMsg
            if isinstance(result, ScriptError):
                ret_msg = ReturnMsg(req_id=req_id, call_id=call_id, error=result.message)
            else:
                ret_msg = ReturnMsg(req_id=req_id, call_id=call_id, value=result)
            try:
                assert self._proc and self._proc.stdin
                self._proc.stdin.write(ret_msg.to_json() + "\n")
                self._proc.stdin.flush()
            except OSError:
                pass
            return

        if kind in ("done", "error"):
            with self._pending_lock:
                entry = self._pending.get(req_id)
            if entry is None:
                return
            evt, holder = entry
            if kind == "done":
                val = msg.get("value")
                output = str(msg.get("output", ""))
                holder.append(ScriptSuccess(value=val, output=output))
            else:
                stack = str(msg.get("stack", ""))
                pre_output = str(msg.get("output", ""))
                detail = (pre_output + "\n" + stack).lstrip("\n") if pre_output else stack
                holder.append(
                    ScriptError(message=str(msg.get("message", "Unknown error")), detail=detail)
                )
            evt.set()

    def _handle_invoke(self, method: str, args: list[Any]) -> Any:
        """Execute a host call requested by the worker; runs on the reader thread."""
        try:
            if method == "insertText":
                self._host.console_replace_selection(str(args[0]) if args else "")
                return None
            if method == "replaceSelection":
                self._host.console_replace_selection(str(args[0]) if args else "")
                return None
            if method == "selectedText":
                return self._host.console_get_selected_text()
            if method == "documentText":
                return self._host.console_get_editor_text()
            if method == "setDocumentText":
                self._host.console_set_editor_text(str(args[0]) if args else "")
                return None
            if method == "gotoLine":
                self._host.console_goto_line(int(args[0]) if args else 1)
                return None
            if method == "gotoOffset":
                self._host.console_goto_offset(int(args[0]) if args else 0)
                return None
            if method == "runCommand":
                cmd = str(args[0]) if args else ""
                self._host.console_run_command(cmd)
                return None
            if method == "commandExists":
                return self._host.console_command_exists(str(args[0]) if args else "")
            if method == "announce":
                self._host.console_announce(str(args[0]) if args else "")
                return None
            if method == "activeDocument":
                name = self._host.console_get_document_name()
                stats = self._host.console_document_stats()
                return {"name": name, "lineCount": stats.get("lines", 0)}
            if method == "documentStats":
                s = self._host.console_document_stats()
                return {
                    "words": s.get("words", 0),
                    "lines": s.get("lines", 0),
                    "chars": s.get("chars", 0),
                }
            if method == "lastAnnouncement":
                anns = self._host.console_get_last_announcements()
                return anns[-1] if anns else ""
            return ScriptError(message=f"Unknown method: {method!r}")
        except Exception as exc:
            return ScriptError(message=str(exc))
