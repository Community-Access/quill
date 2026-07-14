"""Tests for the bundled word-count-node Quillin.

Validates the manifest, and stresses the JavaScript handler directly using
the node_quillin_runner with an injected runner so no real Node.js process
is needed for the unit tests.

An integration marker test at the bottom optionally spawns real Node.js if
it is on PATH, so CI can verify the actual JS behaviour.
"""

from __future__ import annotations

import json
import shutil

import pytest

from quill.core.quillins.model import RUNTIME_NODE
from quill.core.quillins.validation import parse_manifest
from quill.plugins.node_quillin_runner import run_node_command
from quill.tools import quillin_lint as ql

_BUNDLED = ql._REPO_ROOT / "quill" / "quillins_bundled" / "word-count-node"


# ---------------------------------------------------------------------------
# Manifest correctness
# ---------------------------------------------------------------------------


def test_manifest_is_present() -> None:
    assert (_BUNDLED / "manifest.json").is_file()


def test_manifest_passes_strict_lint() -> None:
    report = ql.lint_quillin(_BUNDLED)
    assert report.ok(strict=True), report.render(strict=True)


def test_manifest_runtime_is_node() -> None:
    raw = json.loads((_BUNDLED / "manifest.json").read_text(encoding="utf-8"))
    assert raw.get("runtime") == "node"


def test_manifest_main_is_js() -> None:
    raw = json.loads((_BUNDLED / "manifest.json").read_text(encoding="utf-8"))
    assert raw.get("main", "").endswith(".js")


def test_manifest_has_word_count_command() -> None:
    raw = json.loads((_BUNDLED / "manifest.json").read_text(encoding="utf-8"))
    commands = raw.get("contributes", {}).get("commands", [])
    assert any(cmd.get("run", {}).get("handler") == "wordCount" for cmd in commands)


def test_manifest_parses_to_node_extension_manifest() -> None:
    raw = json.loads((_BUNDLED / "manifest.json").read_text(encoding="utf-8"))
    manifest = parse_manifest(raw)
    assert manifest.runtime == RUNTIME_NODE
    assert manifest.is_node_runtime
    assert manifest.main is not None and manifest.main.endswith(".js")


# ---------------------------------------------------------------------------
# Protocol simulation via injected runner
# ---------------------------------------------------------------------------


class _FakeServices:
    def __init__(self) -> None:
        self.announced: list[str] = []
        self.replaced: list[str] = []
        self.statuses: list[str] = []
        self.inserted: list[str] = []
        self.set_texts: list[str] = []
        self.buffers: list[tuple[str, str]] = []

    def get_text(self) -> str:
        return ""

    def get_selection(self) -> str:
        return ""

    def get_cursor(self) -> dict:
        return {}

    def get_cursor_offset(self) -> int:
        return 0

    def get_selection_range(self) -> dict:
        return {}

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

    def prompt(self, *a) -> None:
        return None

    def show_choices(self, *a) -> None:
        return None

    def read_file(self, p: str) -> str:
        return ""

    def write_file(self, p: str, t: str) -> None:
        pass

    def fetch(self, *a) -> dict:
        return {}

    def get_clipboard(self) -> str:
        return ""

    def set_clipboard(self, t: str) -> None:
        pass


def _fake_which(exe: str) -> str:
    """Stub that makes every executable appear to be on PATH."""
    return exe


def _simulated_runner():
    """
    Simulate what the real extension.js does: count words in selection or text,
    return an announce action.
    """

    def runner(command: list[str], stdin_text: str, timeout: float) -> tuple[int, str, str]:
        request = json.loads(stdin_text.strip())
        ctx_data = request.get("params", {}).get("context", {})
        content = ctx_data.get("selection") or ctx_data.get("text", "")
        trimmed = content.strip()
        words = 0 if not trimmed else len(trimmed.split())
        label = "1 word" if words == 1 else f"{words} words"
        response = {"result": None, "actions": [{"type": "announce", "args": [label]}]}
        return (0, json.dumps(response) + "\n", "")

    return runner


def _load_manifest() -> object:
    return json.loads((_BUNDLED / "manifest.json").read_text(encoding="utf-8"))


def test_word_count_announces_selection_words() -> None:
    raw = _load_manifest()
    manifest = parse_manifest(raw)
    services = _FakeServices()
    command_id = manifest.contributes.commands[0].id

    run_node_command(
        manifest,
        _BUNDLED,
        command_id,
        {"selection": "hello world foo", "text": "full doc text"},
        services,
        master_enabled=True,
        runner=_simulated_runner(),
        which=_fake_which,
    )

    assert services.announced == ["3 words"]


def test_word_count_uses_document_text_when_no_selection() -> None:
    raw = _load_manifest()
    manifest = parse_manifest(raw)
    services = _FakeServices()
    command_id = manifest.contributes.commands[0].id

    run_node_command(
        manifest,
        _BUNDLED,
        command_id,
        {"selection": "", "text": "one two three four"},
        services,
        master_enabled=True,
        runner=_simulated_runner(),
        which=_fake_which,
    )

    assert services.announced == ["4 words"]


def test_word_count_handles_empty_document() -> None:
    raw = _load_manifest()
    manifest = parse_manifest(raw)
    services = _FakeServices()
    command_id = manifest.contributes.commands[0].id

    run_node_command(
        manifest,
        _BUNDLED,
        command_id,
        {"selection": "", "text": ""},
        services,
        master_enabled=True,
        runner=_simulated_runner(),
        which=_fake_which,
    )

    assert services.announced == ["0 words"]


def test_word_count_singular_for_one_word() -> None:
    raw = _load_manifest()
    manifest = parse_manifest(raw)
    services = _FakeServices()
    command_id = manifest.contributes.commands[0].id

    run_node_command(
        manifest,
        _BUNDLED,
        command_id,
        {"selection": "word"},
        services,
        master_enabled=True,
        runner=_simulated_runner(),
        which=_fake_which,
    )

    assert services.announced == ["1 word"]


def test_word_count_handles_whitespace_only_text() -> None:
    raw = _load_manifest()
    manifest = parse_manifest(raw)
    services = _FakeServices()
    command_id = manifest.contributes.commands[0].id

    run_node_command(
        manifest,
        _BUNDLED,
        command_id,
        {"selection": "   \n\t  "},
        services,
        master_enabled=True,
        runner=_simulated_runner(),
        which=_fake_which,
    )

    assert services.announced == ["0 words"]


# ---------------------------------------------------------------------------
# Real Node.js integration (skipped if node not on PATH)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_real_node_word_count_two_words() -> None:
    """Spawn the actual extension.js and verify the protocol round-trip."""
    raw = _load_manifest()
    manifest = parse_manifest(raw)
    services = _FakeServices()
    command_id = manifest.contributes.commands[0].id

    result = run_node_command(
        manifest,
        _BUNDLED,
        command_id,
        {"selection": "hello world", "text": ""},
        services,
        master_enabled=True,
    )

    # If Node.js is available the result must be ok and announce fired.
    assert result.ok, f"node runner failed: {result.error}"
    assert services.announced == ["2 words"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_real_node_word_count_empty_is_zero() -> None:
    raw = _load_manifest()
    manifest = parse_manifest(raw)
    services = _FakeServices()
    command_id = manifest.contributes.commands[0].id

    result = run_node_command(
        manifest,
        _BUNDLED,
        command_id,
        {"selection": "", "text": ""},
        services,
        master_enabled=True,
    )

    assert result.ok, f"node runner failed: {result.error}"
    assert services.announced == ["0 words"]
