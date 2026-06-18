"""Parent-process host controller for Layer 2 Quillins.

This is the trusted side of the out-of-process bridge. It spawns the sandboxed
worker (:mod:`quill.core.quillins.host_worker`), runs the extension's
``register``/handlers by message, and — crucially — **enforces capabilities and
consent** on every request the worker makes back into the editor, filesystem, or
network. The worker can ask; only the host can act.

The controller is wx-free. The concrete editor/ui operations are supplied by the
UI layer through the :class:`HostServices` protocol, so all ``wx`` effects are
marshalled onto the UI thread by the caller, never here.

SEC-8: a host is only ever constructed for an explicitly enabled Quillin, which
the loader refuses to surface unless ``core.third_party_plugins`` is on (locked
off for 1.0).
"""

from __future__ import annotations

import subprocess
import sys
import urllib.parse
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from quill.core.quillins import protocol
from quill.core.quillins.model import (
    API_VERSION,
    CAP_CLIPBOARD_READ,
    CAP_CLIPBOARD_WRITE,
    CAP_EDITOR_READ,
    CAP_EDITOR_WRITE,
    CAP_FS_READ,
    CAP_FS_WRITE,
    CAP_NET,
    CAP_SETTINGS_OWN_READ,
    CAP_SETTINGS_OWN_WRITE,
    CAP_STORAGE,
    CAP_UI_ANNOUNCE,
    CAP_UI_CHOICES,
    CAP_UI_PROMPT,
    CAP_UI_STATUS,
    CONSENT_GATED_CAPABILITIES,
    ApiVersionError,
    CapabilityError,
    ConsentDeniedError,
    ExtensionManifest,
    QuillinError,
)

# Maps each worker-callable API method to the capability it requires.
_METHOD_CAPABILITY: dict[str, str] = {
    "get_text": CAP_EDITOR_READ,
    "get_selection": CAP_EDITOR_READ,
    "get_cursor": CAP_EDITOR_READ,
    "get_cursor_offset": CAP_EDITOR_READ,
    "get_selection_range": CAP_EDITOR_READ,
    "insert_text": CAP_EDITOR_WRITE,
    "replace_selection": CAP_EDITOR_WRITE,
    "set_text": CAP_EDITOR_WRITE,
    "open_buffer": CAP_EDITOR_WRITE,
    "set_cursor": CAP_EDITOR_WRITE,
    "replace_range": CAP_EDITOR_WRITE,
    "announce": CAP_UI_ANNOUNCE,
    "prompt": CAP_UI_PROMPT,
    "set_status": CAP_UI_STATUS,
    "show_choices": CAP_UI_CHOICES,
    "read_file": CAP_FS_READ,
    "write_file": CAP_FS_WRITE,
    "fetch": CAP_NET,
    "get_clipboard": CAP_CLIPBOARD_READ,
    "set_clipboard": CAP_CLIPBOARD_WRITE,
    "get_storage": CAP_STORAGE,
    "set_storage": CAP_STORAGE,
    "delete_storage": CAP_STORAGE,
    "get_setting": CAP_SETTINGS_OWN_READ,
    "set_setting": CAP_SETTINGS_OWN_WRITE,
}


class HostServices(Protocol):
    """The editor/ui/fs/net operations a Quillin may drive through the host.

    The UI layer supplies a concrete implementation that routes editor writes
    through core commands + undo history and marshals ``wx`` work onto the UI
    thread. Every method must return JSON-serialisable values.
    """

    def get_text(self) -> str: ...
    def get_selection(self) -> str: ...
    def get_cursor(self) -> dict[str, int]: ...
    def get_cursor_offset(self) -> int: ...
    def get_selection_range(self) -> dict[str, int]: ...
    def insert_text(self, text: str) -> None: ...
    def replace_selection(self, text: str) -> None: ...
    def set_text(self, text: str) -> None: ...
    def open_buffer(self, text: str, title: str) -> None: ...
    def set_cursor(self, offset: int) -> None: ...
    def replace_range(self, start: int, end: int, text: str) -> None: ...
    def announce(self, message: str) -> None: ...
    def prompt(self, title: str, label: str, default: str) -> str | None: ...
    def set_status(self, message: str) -> None: ...
    def show_choices(self, title: str, items: list[str]) -> str | None: ...
    def read_file(self, path: str) -> str: ...
    def write_file(self, path: str, text: str) -> None: ...
    def fetch(self, url: str, method: str, body: str | None) -> dict[str, Any]: ...
    def get_clipboard(self) -> str: ...
    def set_clipboard(self, text: str) -> None: ...


ConsentCallback = Callable[[str, str], bool]


def _always_deny(capability: str, detail: str) -> bool:
    return False


class ApiDispatcher:
    """Capability- and consent-gated dispatch of worker API calls.

    Separated from the transport so it can be unit-tested without spawning a
    subprocess: feed it an ``api_call`` message and inspect the ``api_result``.
    """

    def __init__(
        self,
        manifest: ExtensionManifest,
        services: HostServices,
        *,
        consent: ConsentCallback = _always_deny,
        granted_capabilities: tuple[str, ...] | None = None,
        storage: dict[str, str] | None = None,
    ) -> None:
        self._services = services
        self._consent = consent
        granted = granted_capabilities
        if granted is None:
            granted = manifest.capabilities
        self._granted: frozenset[str] = frozenset(granted)
        self._storage: dict[str, str] = storage if storage is not None else {}
        self._net_allowed_hosts: tuple[str, ...] = manifest.net_allowed_hosts

    def handle(self, message: dict[str, Any]) -> dict[str, Any]:
        call_id = int(message.get("id", 0))
        method = str(message.get("method", ""))
        args = message.get("args", [])
        if not isinstance(args, list):
            return protocol.api_error(call_id, "QuillinError", "args must be a list")

        capability = _METHOD_CAPABILITY.get(method)
        if capability is None:
            return protocol.api_error(call_id, "QuillinError", f"unknown method: {method}")
        if capability not in self._granted:
            return protocol.api_error(
                call_id, "CapabilityError", f"capability not granted: {capability}"
            )
        if capability in CONSENT_GATED_CAPABILITIES:
            detail = f"{method}({', '.join(str(arg) for arg in args[:1])})"
            if not self._consent(capability, detail):
                return protocol.api_error(
                    call_id, "ConsentDeniedError", f"consent denied for {capability}"
                )

        try:
            value = self._invoke_service(method, args)
        except QuillinError as error:
            return protocol.api_error(call_id, type(error).__name__, str(error))
        except Exception as error:  # never let a service fault crash the host loop
            return protocol.api_error(call_id, "QuillinError", str(error))
        return protocol.api_ok(call_id, value)

    def _is_host_allowed(self, url: str) -> bool:
        """Return True if ``url``'s hostname matches ``net_allowed_hosts``.

        An empty allowlist means all hosts are permitted (backwards-compatible
        default). Wildcard patterns ``*.example.com`` match any subdomain.
        """

        if not self._net_allowed_hosts:
            return True
        try:
            host = urllib.parse.urlparse(url).hostname or ""
        except Exception:
            return False
        for pattern in self._net_allowed_hosts:
            if pattern.startswith("*."):
                # "*.example.com" matches "sub.example.com" but NOT "example.com"
                suffix = "." + pattern[2:]
                if host.endswith(suffix):
                    return True
            elif pattern == host:
                return True
        return False

    def _invoke_service(self, method: str, args: list[Any]) -> Any:
        services = self._services
        if method == "get_text":
            return services.get_text()
        if method == "get_selection":
            return services.get_selection()
        if method == "get_cursor":
            return services.get_cursor()
        if method == "insert_text":
            services.insert_text(str(args[0]))
            return None
        if method == "replace_selection":
            services.replace_selection(str(args[0]))
            return None
        if method == "set_text":
            services.set_text(str(args[0]))
            return None
        if method == "open_buffer":
            title = str(args[1]) if len(args) > 1 else ""
            services.open_buffer(str(args[0]), title)
            return None
        if method == "announce":
            services.announce(str(args[0]))
            return None
        if method == "prompt":
            label = str(args[1]) if len(args) > 1 else ""
            default = str(args[2]) if len(args) > 2 else ""
            return services.prompt(str(args[0]), label, default)
        if method == "read_file":
            return services.read_file(str(args[0]))
        if method == "write_file":
            services.write_file(str(args[0]), str(args[1]))
            return None
        if method == "fetch":
            url = str(args[0])
            if not self._is_host_allowed(url):
                raise QuillinError(f"fetch blocked: host not in net_allowed_hosts ({url!r})")
            http_method = str(args[1]) if len(args) > 1 else "GET"
            body = args[2] if len(args) > 2 else None
            return services.fetch(url, http_method, None if body is None else str(body))
        if method == "get_clipboard":
            return services.get_clipboard()
        if method == "set_clipboard":
            services.set_clipboard(str(args[0]))
            return None
        if method == "get_cursor_offset":
            return services.get_cursor_offset()
        if method == "get_selection_range":
            return services.get_selection_range()
        if method == "set_cursor":
            services.set_cursor(int(args[0]))
            return None
        if method == "replace_range":
            services.replace_range(int(args[0]), int(args[1]), str(args[2]))
            return None
        if method == "set_status":
            services.set_status(str(args[0]))
            return None
        if method == "show_choices":
            title = str(args[0]) if args else ""
            items = [str(i) for i in args[1]] if len(args) > 1 and isinstance(args[1], list) else []
            return services.show_choices(title, items)
        if method == "get_storage":
            return self._storage.get(str(args[0]))
        if method == "set_storage":
            self._storage[str(args[0])] = str(args[1])
            return None
        if method == "delete_storage":
            self._storage.pop(str(args[0]), None)
            return None
        if method == "get_setting":
            return self._storage.get(str(args[0]))
        if method == "set_setting":
            self._storage[str(args[0])] = str(args[1])
            return None
        raise QuillinError(f"unhandled method: {method}")


def _raise_for_error(error_kind: str, message: str) -> None:
    if error_kind == "CapabilityError":
        raise CapabilityError(message)
    if error_kind == "ConsentDeniedError":
        raise ConsentDeniedError(message)
    if error_kind == "ApiVersionError":
        raise ApiVersionError(message)
    raise QuillinError(message)


class ExtensionHost:
    """Drive a single Quillin's out-of-process worker.

    Lifecycle: :meth:`start` spawns the worker and verifies the API version,
    :meth:`load` runs ``register(api)`` and returns the registered command ids,
    :meth:`invoke` runs a handler, and :meth:`close` shuts the worker down. The
    message loop is synchronous and deterministic: an ``invoke`` pumps the
    worker's API calls through the gated :class:`ApiDispatcher` until a result.
    """

    def __init__(
        self,
        manifest: ExtensionManifest,
        directory: Path,
        services: HostServices,
        *,
        consent: ConsentCallback = _always_deny,
        granted_capabilities: tuple[str, ...] | None = None,
        python_executable: str | None = None,
        storage: dict[str, str] | None = None,
    ) -> None:
        self._manifest = manifest
        self._directory = directory
        self._dispatcher = ApiDispatcher(
            manifest,
            services,
            consent=consent,
            granted_capabilities=granted_capabilities,
            storage=storage,
        )
        self._python = python_executable or sys.executable
        self._process: subprocess.Popen[str] | None = None
        self._call_id = 0
        self._logs: list[str] = []

    @property
    def logs(self) -> list[str]:
        return list(self._logs)

    def start(self) -> None:
        if self._manifest.main is None:
            raise QuillinError("manifest has no 'main' module; not a Layer 2 extension")
        self._process = subprocess.Popen(
            [self._python, "-m", "quill.core.quillins.host_worker", str(self._directory)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        hello = self._read_message()
        if hello.get("type") != protocol.MSG_HELLO:
            raise QuillinError("worker did not greet with a hello message")
        worker_version = int(hello.get("api_version", 0))
        if worker_version != API_VERSION:
            raise ApiVersionError(
                f"worker targets API v{worker_version}, host speaks v{API_VERSION}"
            )

    def load(self) -> tuple[str, ...]:
        assert self._manifest.main is not None
        self._send(protocol.load(self._manifest.main, list(self._manifest.capabilities)))
        message = self._pump_until_result()
        commands = message.get("commands", [])
        if isinstance(commands, list):
            return tuple(str(item) for item in commands)
        return ()

    def invoke(self, command_id: str, context: dict[str, Any]) -> Any:
        handler = self._handler_for(command_id)
        self._call_id += 1
        self._send(protocol.invoke(self._call_id, handler, context))
        message = self._pump_until_result()
        return message.get("value")

    def invoke_event(self, handler_name: str, context: dict[str, Any]) -> Any:
        """Invoke a registered handler by name (event/timer dispatch).

        Works like :meth:`invoke` but takes the handler function name directly
        rather than resolving it from a command id, because document-event and
        timer handlers are not registered as commands.
        """

        if not isinstance(handler_name, str) or not handler_name:
            raise QuillinError("invoke_event requires a non-empty handler name")
        self._call_id += 1
        self._send(protocol.invoke(self._call_id, handler_name, context))
        message = self._pump_until_result()
        return message.get("value")

    def _handler_for(self, command_id: str) -> str:
        for command in self._manifest.contributes.commands:
            if command.id == command_id:
                if command.handler is None:
                    raise QuillinError(f"command '{command_id}' is a snippet, not a handler")
                return command.handler
        raise QuillinError(f"unknown command: {command_id}")

    def close(self) -> None:
        process = self._process
        if process is None:
            return
        try:
            if process.poll() is None:
                self._send(protocol.shutdown())
                process.wait(timeout=5)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        finally:
            if process.poll() is None:
                process.kill()
            self._process = None

    def __enter__(self) -> ExtensionHost:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _pump_until_result(self) -> dict[str, Any]:
        """Service the worker's API calls until it reports a terminal result."""

        while True:
            message = self._read_message()
            kind = message.get("type")
            if kind == protocol.MSG_API_CALL:
                self._send(self._dispatcher.handle(message))
                continue
            if kind == protocol.MSG_LOG:
                self._logs.append(str(message.get("message", "")))
                continue
            if kind in (protocol.MSG_RESULT, protocol.MSG_REGISTERED):
                if kind == protocol.MSG_RESULT and not message.get("ok", True):
                    _raise_for_error(
                        str(message.get("error_kind", "QuillinError")),
                        str(message.get("message", "extension error")),
                    )
                return message
            raise QuillinError(f"unexpected message from worker: {kind!r}")

    def _send(self, message: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None:
            raise QuillinError("worker process is not running")
        process.stdin.write(protocol.encode_message(message))
        process.stdin.flush()

    def _read_message(self) -> dict[str, Any]:
        process = self._process
        if process is None or process.stdout is None:
            raise QuillinError("worker process is not running")
        line = process.stdout.readline()
        if not line:
            raise QuillinError("worker process closed the connection")
        return protocol.decode_message(line)
