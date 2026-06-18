"""Unit tests for the capability- and consent-gated API dispatcher.

These drive :class:`quill.core.quillins.host.ApiDispatcher` directly, without
spawning a worker subprocess, so the security gate is tested in isolation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.quillins import protocol
from quill.core.quillins.host import ApiDispatcher, ExtensionHost
from quill.core.quillins.model import Contributions, ExtensionManifest, QuillinError


class _RecordingServices:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def get_text(self) -> str:
        self.calls.append(("get_text", ()))
        return "document body"

    def get_selection(self) -> str:
        self.calls.append(("get_selection", ()))
        return "sel"

    def get_cursor(self) -> dict[str, int]:
        return {"line": 1, "column": 1, "percent": 0}

    def insert_text(self, text: str) -> None:
        self.calls.append(("insert_text", (text,)))

    def replace_selection(self, text: str) -> None:
        self.calls.append(("replace_selection", (text,)))

    def announce(self, message: str) -> None:
        self.calls.append(("announce", (message,)))

    def read_file(self, path: str) -> str:
        self.calls.append(("read_file", (path,)))
        return "file contents"

    def write_file(self, path: str, text: str) -> None:
        self.calls.append(("write_file", (path, text)))

    def fetch(self, url: str, method: str, body: str | None) -> dict[str, Any]:
        self.calls.append(("fetch", (url, method, body)))
        return {"status": 200}

    def get_clipboard(self) -> str:
        return "clip"

    def set_clipboard(self, text: str) -> None:
        self.calls.append(("set_clipboard", (text,)))


def _manifest(*capabilities: str, net_allowed_hosts: tuple[str, ...] = ()) -> ExtensionManifest:
    return ExtensionManifest(
        id="com.example.t",
        name="T",
        version="1.0.0",
        capabilities=tuple(capabilities),
        main="extension.py",
        contributes=Contributions(),
        net_allowed_hosts=net_allowed_hosts,
    )


def _call(dispatcher: ApiDispatcher, method: str, *args: Any) -> dict[str, Any]:
    return dispatcher.handle({"type": "api_call", "id": 1, "method": method, "args": list(args)})


def test_granted_read_method_succeeds() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest("editor.read"), services)
    result = _call(dispatcher, "get_text")
    assert result["ok"] is True
    assert result["value"] == "document body"


def test_ungranted_capability_is_denied() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest("editor.read"), services)  # no editor.write
    result = _call(dispatcher, "insert_text", "x")
    assert result["ok"] is False
    assert result["error_kind"] == "CapabilityError"
    assert services.calls == []  # service was never reached


def test_unknown_method_is_rejected() -> None:
    dispatcher = ApiDispatcher(_manifest("editor.read"), _RecordingServices())
    result = _call(dispatcher, "launch_missiles")
    assert result["ok"] is False
    assert "unknown method" in result["message"]


def test_consent_gated_capability_requires_consent_grant() -> None:
    services = _RecordingServices()
    seen: list[tuple[str, str]] = []

    def consent(capability: str, detail: str) -> bool:
        seen.append((capability, detail))
        return True

    dispatcher = ApiDispatcher(_manifest("fs.read"), services, consent=consent)
    result = _call(dispatcher, "read_file", "C:/notes.txt")
    assert result["ok"] is True
    assert seen and seen[0][0] == "fs.read"
    assert services.calls == [("read_file", ("C:/notes.txt",))]


def test_consent_denied_blocks_the_call() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest("fs.read"), services, consent=lambda c, d: False)
    result = _call(dispatcher, "read_file", "C:/notes.txt")
    assert result["ok"] is False
    assert result["error_kind"] == "ConsentDeniedError"
    assert services.calls == []


def test_default_consent_is_deny() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest("net"), services)  # no consent callback
    result = _call(dispatcher, "fetch", "https://example.com")
    assert result["ok"] is False
    assert result["error_kind"] == "ConsentDeniedError"


def test_non_consent_capability_does_not_prompt() -> None:
    services = _RecordingServices()
    prompted = False

    def consent(capability: str, detail: str) -> bool:
        nonlocal prompted
        prompted = True
        return True

    dispatcher = ApiDispatcher(_manifest("editor.write"), services, consent=consent)
    result = _call(dispatcher, "insert_text", "hello")
    assert result["ok"] is True
    assert prompted is False  # install-time capability, never per-action prompt


def test_granted_capabilities_override_manifest() -> None:
    services = _RecordingServices()
    # Manifest declares editor.write, but the user only granted editor.read.
    dispatcher = ApiDispatcher(
        _manifest("editor.read", "editor.write"),
        services,
        granted_capabilities=("editor.read",),
    )
    assert _call(dispatcher, "get_text")["ok"] is True
    assert _call(dispatcher, "insert_text", "x")["ok"] is False


def test_args_must_be_a_list() -> None:
    dispatcher = ApiDispatcher(_manifest("editor.read"), _RecordingServices())
    result = dispatcher.handle({"type": "api_call", "id": 1, "method": "get_text", "args": "x"})
    assert result["ok"] is False
    assert "args must be a list" in result["message"]


# -- net_allowed_hosts enforcement -------------------------------------------


def test_fetch_allowed_when_no_allowlist() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest("net"), services, consent=lambda c, d: True)
    result = _call(dispatcher, "fetch", "https://example.com/data")
    assert result["ok"] is True
    assert services.calls[0][0] == "fetch"


def test_fetch_blocked_when_host_not_in_allowlist() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(
        _manifest("net", net_allowed_hosts=("api.example.com",)),
        services,
        consent=lambda c, d: True,
    )
    result = _call(dispatcher, "fetch", "https://evil.com/steal")
    assert result["ok"] is False
    assert "net_allowed_hosts" in result["message"]
    assert services.calls == []


def test_fetch_allowed_when_host_matches_exact() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(
        _manifest("net", net_allowed_hosts=("api.example.com",)),
        services,
        consent=lambda c, d: True,
    )
    result = _call(dispatcher, "fetch", "https://api.example.com/v1/data")
    assert result["ok"] is True


def test_fetch_allowed_when_wildcard_matches_subdomain() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(
        _manifest("net", net_allowed_hosts=("*.example.com",)),
        services,
        consent=lambda c, d: True,
    )
    result = _call(dispatcher, "fetch", "https://sub.example.com/data")
    assert result["ok"] is True


def test_fetch_blocked_when_wildcard_does_not_match_parent() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(
        _manifest("net", net_allowed_hosts=("*.example.com",)),
        services,
        consent=lambda c, d: True,
    )
    # "example.com" itself does not match "*.example.com"
    result = _call(dispatcher, "fetch", "https://example.com/data")
    assert result["ok"] is False


# -- invoke_event (Part 0) ----------------------------------------------------


class _NullServices:
    """Minimal HostServices stand-in; never reached in these transport tests."""

    def __getattr__(self, _name: str) -> Any:  # pragma: no cover - defensive
        def _stub(*_a: Any, **_k: Any) -> Any:
            return None

        return _stub


def _event_host() -> tuple[ExtensionHost, list[dict[str, Any]]]:
    host = ExtensionHost(
        ExtensionManifest(
            id="com.example.e",
            name="E",
            version="1.0.0",
            main="extension.py",
            contributes=Contributions(),
        ),
        Path("."),
        _NullServices(),
    )
    sent: list[dict[str, Any]] = []
    host._send = sent.append  # type: ignore[assignment,method-assign]
    # The worker reports a successful, valueless result for the invoke.
    host._pump_until_result = lambda: protocol.result_ok(host._call_id)  # type: ignore[assignment,method-assign]
    return host, sent


def test_invoke_event_calls_handler_by_name() -> None:
    host, sent = _event_host()
    host.invoke_event("on_after_save", {"file_path": "C:/a.txt"})
    invoke = next(m for m in sent if m.get("type") == protocol.MSG_INVOKE)
    assert invoke["command"] == "on_after_save"
    assert invoke["context"] == {"file_path": "C:/a.txt"}


def test_invoke_event_rejects_empty_handler_name() -> None:
    host, _sent = _event_host()
    with pytest.raises(QuillinError):
        host.invoke_event("", {})
