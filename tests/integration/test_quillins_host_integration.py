"""End-to-end integration tests for the out-of-process Quillin host bridge.

These spawn the real :mod:`quill.core.quillins.host_worker` subprocess and drive
it through :class:`quill.core.quillins.host.ExtensionHost`, exercising the full
Layer 2 round-trip plus the capability and consent security gates and the worker
isolation guarantees (no editor crash, path containment).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.quillins.host import ExtensionHost
from quill.core.quillins.model import (
    Contributions,
    ExtensionCommand,
    ExtensionManifest,
)


class _FakeEditor:
    """A trivial in-test stand-in for the host services protocol."""

    def __init__(self, *, selection: str = "", text: str = "") -> None:
        self._selection = selection
        self._text = text
        self.replaced: list[str] = []
        self.inserted: list[str] = []
        self.announced: list[str] = []
        self.written_files: list[tuple[str, str]] = []
        self.fetched: list[str] = []

    def get_text(self) -> str:
        return self._text

    def get_selection(self) -> str:
        return self._selection

    def get_cursor(self) -> dict[str, int]:
        return {"line": 1, "column": 1, "percent": 0}

    def insert_text(self, text: str) -> None:
        self.inserted.append(text)

    def replace_selection(self, text: str) -> None:
        self.replaced.append(text)

    def announce(self, message: str) -> None:
        self.announced.append(message)

    def is_verbosity_speech_enabled(self) -> bool:
        return True

    def read_file(self, path: str) -> str:
        return "SECRET FILE CONTENTS"

    def write_file(self, path: str, text: str) -> None:
        self.written_files.append((path, text))

    def fetch(self, url: str, method: str, body: str | None) -> dict[str, Any]:
        self.fetched.append(url)
        return {"status": 200, "body": "ok"}

    def get_clipboard(self) -> str:
        return "clip"

    def set_clipboard(self, text: str) -> None:
        pass


def _write_extension(directory: Path, body: str) -> None:
    (directory / "extension.py").write_text(body, encoding="utf-8")


def _manifest(
    *capabilities: str,
    command_id: str = "ext.t.run",
    handler: str = "run",
    main: str | None = "extension.py",
) -> ExtensionManifest:
    return ExtensionManifest(
        id="com.example.t",
        name="T",
        version="1.0.0",
        capabilities=tuple(capabilities),
        main=main,
        contributes=Contributions(
            commands=(ExtensionCommand(id=command_id, title="Run", handler=handler),)
        ),
    )


def test_handler_round_trip_reads_and_writes(tmp_path: Path) -> None:
    _write_extension(
        tmp_path,
        "def register(api):\n"
        "    def run(ctx):\n"
        "        ctx.replace_selection(ctx.get_selection().title())\n"
        "        ctx.announce('done')\n"
        "    api.register_command('run', run)\n",
    )
    editor = _FakeEditor(selection="hello world")
    manifest = _manifest("editor.read", "editor.write", "ui.announce", "ui.command")
    host = ExtensionHost(manifest, tmp_path, editor, consent=lambda c, d: True)
    try:
        host.start()
        assert host.load() == ("run",)
        host.invoke("ext.t.run", {})
    finally:
        host.close()
    assert editor.replaced == ["Hello World"]
    assert editor.announced == ["done"]


def test_undeclared_capability_is_blocked_in_worker(tmp_path: Path) -> None:
    _write_extension(
        tmp_path,
        "def register(api):\n"
        "    def run(ctx):\n"
        "        try:\n"
        "            ctx.read_file('C:/secret.txt')\n"
        "            ctx.announce('LEAKED')\n"
        "        except Exception as exc:\n"
        "            ctx.announce('blocked:' + type(exc).__name__)\n"
        "    api.register_command('run', run)\n",
    )
    editor = _FakeEditor()
    # editor.read but NOT fs.read.
    manifest = _manifest("editor.read", "ui.announce", "ui.command")
    host = ExtensionHost(manifest, tmp_path, editor, consent=lambda c, d: True)
    try:
        host.start()
        host.load()
        host.invoke("ext.t.run", {})
    finally:
        host.close()
    assert editor.announced == ["blocked:CapabilityError"]


def test_consent_denied_blocks_filesystem_read(tmp_path: Path) -> None:
    _write_extension(
        tmp_path,
        "def register(api):\n"
        "    def run(ctx):\n"
        "        try:\n"
        "            ctx.read_file('C:/secret.txt')\n"
        "            ctx.announce('LEAKED')\n"
        "        except Exception as exc:\n"
        "            ctx.announce('denied:' + type(exc).__name__)\n"
        "    api.register_command('run', run)\n",
    )
    editor = _FakeEditor()
    manifest = _manifest("fs.read", "ui.announce", "ui.command")
    host = ExtensionHost(manifest, tmp_path, editor, consent=lambda c, d: False)
    try:
        host.start()
        host.load()
        host.invoke("ext.t.run", {})
    finally:
        host.close()
    assert editor.announced == ["denied:ConsentDeniedError"]


def test_consent_granted_allows_network(tmp_path: Path) -> None:
    _write_extension(
        tmp_path,
        "def register(api):\n"
        "    def run(ctx):\n"
        "        resp = ctx.fetch('https://example.com')\n"
        "        ctx.announce('status:' + str(resp['status']))\n"
        "    api.register_command('run', run)\n",
    )
    editor = _FakeEditor()
    manifest = _manifest("net", "ui.announce", "ui.command")
    host = ExtensionHost(manifest, tmp_path, editor, consent=lambda c, d: True)
    try:
        host.start()
        host.load()
        host.invoke("ext.t.run", {})
    finally:
        host.close()
    assert editor.fetched == ["https://example.com"]
    assert editor.announced == ["status:200"]


def test_handler_exception_is_surfaced_not_fatal(tmp_path: Path) -> None:
    _write_extension(
        tmp_path,
        "def register(api):\n"
        "    def run(ctx):\n"
        "        raise RuntimeError('boom')\n"
        "    api.register_command('run', run)\n",
    )
    editor = _FakeEditor()
    manifest = _manifest("ui.command")
    host = ExtensionHost(manifest, tmp_path, editor, consent=lambda c, d: True)
    try:
        host.start()
        host.load()
        with pytest.raises(Exception) as excinfo:
            host.invoke("ext.t.run", {})
        assert "boom" in str(excinfo.value)
    finally:
        host.close()


def test_log_never_carries_to_announcements(tmp_path: Path) -> None:
    _write_extension(
        tmp_path,
        "def register(api):\n"
        "    def run(ctx):\n"
        "        ctx.log('diagnostic only')\n"
        "        ctx.announce('user message')\n"
        "    api.register_command('run', run)\n",
    )
    editor = _FakeEditor()
    manifest = _manifest("ui.announce", "ui.command")
    host = ExtensionHost(manifest, tmp_path, editor, consent=lambda c, d: True)
    try:
        host.start()
        host.load()
        host.invoke("ext.t.run", {})
    finally:
        host.close()
    assert editor.announced == ["user message"]
    assert "diagnostic only" in host.logs


def test_context_manager_starts_and_closes(tmp_path: Path) -> None:
    _write_extension(
        tmp_path,
        "def register(api):\n"
        "    def run(ctx):\n"
        "        ctx.insert_text('hi')\n"
        "    api.register_command('run', run)\n",
    )
    editor = _FakeEditor()
    manifest = _manifest("editor.write", "ui.command")
    with ExtensionHost(manifest, tmp_path, editor, consent=lambda c, d: True) as host:
        host.load()
        host.invoke("ext.t.run", {})
    assert editor.inserted == ["hi"]


def test_main_module_escaping_directory_is_rejected(tmp_path: Path) -> None:
    _write_extension(tmp_path, "def register(api):\n    pass\n")
    editor = _FakeEditor()
    # main points outside the extension directory via traversal.
    manifest = _manifest("ui.command", main="../evil.py")
    host = ExtensionHost(manifest, tmp_path, editor, consent=lambda c, d: True)
    try:
        host.start()
        with pytest.raises(Exception) as excinfo:
            host.load()
        assert "escapes" in str(excinfo.value) or "import" in str(excinfo.value)
    finally:
        host.close()
