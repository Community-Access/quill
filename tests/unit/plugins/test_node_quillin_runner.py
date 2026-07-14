"""Tests for the Node.js Quillin runner (quill.plugins.node_quillin_runner).

All tests use an injected runner and a fake ``which`` so no Node.js process is
spawned and no PATH check fires.  The runner callable follows the same signature
used by external_engine._default_runner:
(command, stdin_text, timeout) -> (returncode, stdout, stderr).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from quill.core.ai.external_engine import EngineResult
from quill.core.quillins.model import (
    RUNTIME_NODE,
    Contributions,
    ExtensionCommand,
    ExtensionManifest,
)
from quill.plugins.node_quillin_runner import (
    _dispatch_action,
    _handler_for,
    run_node_command,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _FakeServices:
    """Minimal HostServices stub that records all calls."""

    def __init__(self, *, selection: str = "", text: str = "") -> None:
        self._selection = selection
        self._text = text
        self.replaced: list[str] = []
        self.inserted: list[str] = []
        self.set_texts: list[str] = []
        self.announced: list[str] = []
        self.statuses: list[str] = []
        self.buffers: list[tuple[str, str]] = []

    def get_text(self) -> str:
        return self._text

    def get_selection(self) -> str:
        return self._selection

    def get_cursor(self) -> dict[str, int]:
        return {"line": 1, "column": 1, "percent": 0}

    def get_cursor_offset(self) -> int:
        return 0

    def get_selection_range(self) -> dict[str, int]:
        return {"start": 0, "end": len(self._selection)}

    def insert_text(self, t: str) -> None:
        self.inserted.append(t)

    def replace_selection(self, t: str) -> None:
        self.replaced.append(t)

    def set_text(self, t: str) -> None:
        self.set_texts.append(t)

    def open_buffer(self, t: str, title: str) -> None:
        self.buffers.append((t, title))

    def announce(self, m: str) -> None:
        self.announced.append(m)

    def is_verbosity_speech_enabled(self) -> bool:
        return True

    def set_status(self, m: str) -> None:
        self.statuses.append(m)

    def prompt(self, *a: Any) -> None:
        return None

    def show_choices(self, *a: Any) -> None:
        return None

    def read_file(self, p: str) -> str:
        return ""

    def write_file(self, p: str, t: str) -> None:
        pass

    def fetch(self, *a: Any) -> dict[str, Any]:
        return {}

    def get_clipboard(self) -> str:
        return ""

    def set_clipboard(self, t: str) -> None:
        pass


def _make_manifest(
    *,
    handler_name: str = "myHandler",
    command_id: str = "ext.test.cmd",
    capabilities: list[str] | None = None,
) -> ExtensionManifest:
    if capabilities is None:
        capabilities = ["editor.read", "ui.announce", "ui.command"]
    return ExtensionManifest(
        id="com.example.test",
        name="Test",
        version="1.0.0",
        runtime=RUNTIME_NODE,
        capabilities=tuple(capabilities),
        main="extension.js",
        contributes=Contributions(
            commands=(ExtensionCommand(id=command_id, title="Cmd", handler=handler_name),),
        ),
    )


def _ok_runner(response_dict: dict[str, Any]):
    """Return a runner that always replies with response_dict."""

    def runner(command: list[str], stdin_text: str, timeout: float) -> tuple[int, str, str]:
        return (0, json.dumps(response_dict) + "\n", "")

    return runner


def _error_runner(error_msg: str):
    def runner(command: list[str], stdin_text: str, timeout: float) -> tuple[int, str, str]:
        return (1, "", error_msg)

    return runner


def _fake_which(exe: str) -> str:
    """Stub: pretend every executable resolves to itself so PATH checks pass."""
    return exe


def _run(
    manifest: ExtensionManifest,
    directory: Path,
    command_id: str,
    context: dict[str, Any],
    services: _FakeServices,
    runner,
    *,
    master_enabled: bool = True,
) -> EngineResult:
    """Helper that calls run_node_command with test-friendly defaults."""
    return run_node_command(
        manifest,
        directory,
        command_id,
        context,
        services,
        master_enabled=master_enabled,
        runner=runner,
        which=_fake_which,
    )


# ---------------------------------------------------------------------------
# _handler_for
# ---------------------------------------------------------------------------


def test_handler_for_finds_correct_handler() -> None:
    manifest = _make_manifest(handler_name="doThing", command_id="ext.t.go")
    assert _handler_for(manifest, "ext.t.go") == "doThing"


def test_handler_for_raises_for_unknown_command() -> None:
    manifest = _make_manifest()
    with pytest.raises(Exception, match="unknown command"):
        _handler_for(manifest, "ext.nope.nope")


def test_handler_for_raises_for_snippet_command() -> None:
    manifest = ExtensionManifest(
        id="com.example.snip",
        name="Snip",
        version="1.0.0",
        runtime=RUNTIME_NODE,
        capabilities=(),
        contributes=Contributions(
            commands=(ExtensionCommand(id="ext.s.snip", title="S", snippet="hello"),),
        ),
    )
    with pytest.raises(Exception, match="snippet"):
        _handler_for(manifest, "ext.s.snip")


# ---------------------------------------------------------------------------
# _dispatch_action
# ---------------------------------------------------------------------------


def test_dispatch_replace_selection() -> None:
    services = _FakeServices()
    _dispatch_action({"type": "replace_selection", "args": ["**bold**"]}, services)
    assert services.replaced == ["**bold**"]


def test_dispatch_insert_text() -> None:
    services = _FakeServices()
    _dispatch_action({"type": "insert_text", "args": ["inserted"]}, services)
    assert services.inserted == ["inserted"]


def test_dispatch_set_text() -> None:
    services = _FakeServices()
    _dispatch_action({"type": "set_text", "args": ["new doc"]}, services)
    assert services.set_texts == ["new doc"]


def test_dispatch_announce() -> None:
    services = _FakeServices()
    _dispatch_action({"type": "announce", "args": ["5 words"]}, services)
    assert services.announced == ["5 words"]


def test_dispatch_set_status() -> None:
    services = _FakeServices()
    _dispatch_action({"type": "set_status", "args": ["Done"]}, services)
    assert services.statuses == ["Done"]


def test_dispatch_open_buffer() -> None:
    services = _FakeServices()
    _dispatch_action({"type": "open_buffer", "args": ["content", "My Title"]}, services)
    assert services.buffers == [("content", "My Title")]


def test_dispatch_open_buffer_missing_title_defaults_empty() -> None:
    services = _FakeServices()
    _dispatch_action({"type": "open_buffer", "args": ["content"]}, services)
    assert services.buffers == [("content", "")]


def test_dispatch_unknown_type_is_silently_ignored() -> None:
    services = _FakeServices()
    _dispatch_action({"type": "future_action", "args": ["x"]}, services)
    assert not services.announced
    assert not services.replaced


def test_dispatch_missing_args_defaults_to_empty() -> None:
    services = _FakeServices()
    _dispatch_action({"type": "announce"}, services)
    assert services.announced == [""]


def test_dispatch_non_list_args_defaults_to_empty() -> None:
    services = _FakeServices()
    _dispatch_action({"type": "announce", "args": "oops"}, services)
    assert services.announced == [""]


# ---------------------------------------------------------------------------
# run_node_command — action dispatching
# ---------------------------------------------------------------------------


def test_run_dispatches_announce_action(tmp_path: Path) -> None:
    (tmp_path / "extension.js").write_text("", encoding="utf-8")
    manifest = _make_manifest()
    services = _FakeServices()
    response = {"result": None, "actions": [{"type": "announce", "args": ["2 words"]}]}

    result = _run(
        manifest,
        tmp_path,
        "ext.test.cmd",
        {"selection": "hello world"},
        services,
        _ok_runner(response),
    )

    assert result.ok
    assert services.announced == ["2 words"]


def test_run_dispatches_replace_selection_action(tmp_path: Path) -> None:
    (tmp_path / "extension.js").write_text("", encoding="utf-8")
    manifest = _make_manifest()
    services = _FakeServices()
    response = {"result": None, "actions": [{"type": "replace_selection", "args": ["**hello**"]}]}

    result = _run(
        manifest, tmp_path, "ext.test.cmd", {"selection": "hello"}, services, _ok_runner(response)
    )

    assert result.ok
    assert services.replaced == ["**hello**"]


def test_run_dispatches_multiple_actions_in_order(tmp_path: Path) -> None:
    (tmp_path / "extension.js").write_text("", encoding="utf-8")
    manifest = _make_manifest()
    services = _FakeServices()
    response = {
        "result": None,
        "actions": [
            {"type": "set_status", "args": ["Working..."]},
            {"type": "announce", "args": ["Done"]},
        ],
    }

    _run(manifest, tmp_path, "ext.test.cmd", {}, services, _ok_runner(response))

    assert services.statuses == ["Working..."]
    assert services.announced == ["Done"]


# ---------------------------------------------------------------------------
# run_node_command — request content
# ---------------------------------------------------------------------------


def test_run_sends_handler_name_as_method(tmp_path: Path) -> None:
    (tmp_path / "extension.js").write_text("", encoding="utf-8")
    manifest = _make_manifest(handler_name="processText", command_id="ext.test.cmd")
    services = _FakeServices()
    received_stdin: list[str] = []

    def capturing_runner(
        command: list[str], stdin_text: str, timeout: float
    ) -> tuple[int, str, str]:
        received_stdin.append(stdin_text)
        return (0, json.dumps({"result": None, "actions": []}) + "\n", "")

    _run(manifest, tmp_path, "ext.test.cmd", {"selection": "text"}, services, capturing_runner)

    assert received_stdin
    parsed = json.loads(received_stdin[0].strip())
    assert parsed["method"] == "processText"
    assert parsed["params"]["context"]["selection"] == "text"


def test_run_includes_capabilities_in_params(tmp_path: Path) -> None:
    (tmp_path / "extension.js").write_text("", encoding="utf-8")
    manifest = _make_manifest(capabilities=["editor.read", "ui.announce", "ui.command"])
    services = _FakeServices()
    received_stdin: list[str] = []

    def capturing_runner(
        command: list[str], stdin_text: str, timeout: float
    ) -> tuple[int, str, str]:
        received_stdin.append(stdin_text)
        return (0, json.dumps({"result": None, "actions": []}) + "\n", "")

    _run(manifest, tmp_path, "ext.test.cmd", {}, services, capturing_runner)

    parsed = json.loads(received_stdin[0].strip())
    assert set(parsed["params"]["capabilities"]) == {"editor.read", "ui.announce", "ui.command"}


def test_run_uses_node_executable_in_command(tmp_path: Path) -> None:
    (tmp_path / "extension.js").write_text("", encoding="utf-8")
    manifest = _make_manifest()
    services = _FakeServices()
    captured_commands: list[list[str]] = []

    def capturing_runner(
        command: list[str], stdin_text: str, timeout: float
    ) -> tuple[int, str, str]:
        captured_commands.append(command)
        return (0, json.dumps({"result": None, "actions": []}) + "\n", "")

    run_node_command(
        manifest,
        tmp_path,
        "ext.test.cmd",
        {},
        services,
        master_enabled=True,
        node_executable="node",
        runner=capturing_runner,
        which=_fake_which,
    )

    assert captured_commands
    assert captured_commands[0][0] == "node"
    assert captured_commands[0][1] == str(tmp_path / "extension.js")


# ---------------------------------------------------------------------------
# run_node_command — failure modes
# ---------------------------------------------------------------------------


def test_run_error_result_not_dispatched(tmp_path: Path) -> None:
    (tmp_path / "extension.js").write_text("", encoding="utf-8")
    manifest = _make_manifest()
    services = _FakeServices()

    result = _run(manifest, tmp_path, "ext.test.cmd", {}, services, _error_runner("boom"))

    assert not result.ok
    assert not services.announced
    assert not services.replaced


def test_run_master_disabled_returns_unavailable(tmp_path: Path) -> None:
    (tmp_path / "extension.js").write_text("", encoding="utf-8")
    manifest = _make_manifest()
    services = _FakeServices()

    result = run_node_command(
        manifest,
        tmp_path,
        "ext.test.cmd",
        {},
        services,
        master_enabled=False,
        runner=_ok_runner({"result": None, "actions": []}),
        which=_fake_which,
    )

    assert not result.ok
    assert result.unavailable


def test_run_raises_for_missing_main(tmp_path: Path) -> None:
    from quill.core.quillins.model import QuillinError

    manifest = ExtensionManifest(
        id="com.example.nomain",
        name="No Main",
        version="1.0.0",
        runtime=RUNTIME_NODE,
    )
    services = _FakeServices()

    with pytest.raises(QuillinError, match="no 'main' module"):
        run_node_command(
            manifest,
            tmp_path,
            "ext.test.cmd",
            {},
            services,
            master_enabled=True,
            which=_fake_which,
        )


def test_run_raises_for_unknown_command(tmp_path: Path) -> None:
    from quill.core.quillins.model import QuillinError

    (tmp_path / "extension.js").write_text("", encoding="utf-8")
    manifest = _make_manifest()
    services = _FakeServices()

    with pytest.raises(QuillinError, match="unknown command"):
        run_node_command(
            manifest,
            tmp_path,
            "ext.test.NOPE",
            {},
            services,
            master_enabled=True,
            which=_fake_which,
        )


def test_run_no_actions_key_handled_gracefully(tmp_path: Path) -> None:
    (tmp_path / "extension.js").write_text("", encoding="utf-8")
    manifest = _make_manifest()
    services = _FakeServices()

    result = _run(manifest, tmp_path, "ext.test.cmd", {}, services, _ok_runner({"result": None}))

    assert result.ok
    assert not services.announced


def test_run_actions_with_non_dict_items_skipped(tmp_path: Path) -> None:
    (tmp_path / "extension.js").write_text("", encoding="utf-8")
    manifest = _make_manifest()
    services = _FakeServices()
    response = {"result": None, "actions": ["not a dict", {"type": "announce", "args": ["ok"]}]}

    result = _run(manifest, tmp_path, "ext.test.cmd", {}, services, _ok_runner(response))

    assert result.ok
    assert services.announced == ["ok"]
