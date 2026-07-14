"""Characterization tests for the bundled ``text-tools`` and ``insert-tools`` Quillins.

These two Quillins were converted out of QUILL's core/UI Python (the power-tools
mixin and ``quill/ui/features/line_transforms.py``) into real, sandboxed Quillins
(``docs/quillins.md`` Wave 1). This module pins the conversion:

* the vendored ``algorithms.py`` reproduces, byte for byte, the output the deleted
  ``quill.core.{regex_ops,set_ops,wrap_ops}`` modules and ``line_ops.number_lines``
  produced (the assertions are lifted from their original unit tests);
* each manifest validates and resolves into the Format/Insert/Search menus;
* the Layer 2 ``extension.py`` registers its six handlers and they drive a fake
  capability host context to the same outcomes the core handlers produced;
* the Layer 1 ``insert-tools`` snippets expand the date/time placeholders.

It imports no ``wx`` and spawns no worker, so it runs wherever the core tests run
while still exercising the end-to-end author-facing contract.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from quill.core.quillins.loader import bundled_extensions_root
from quill.core.quillins.model import ExtensionManifest
from quill.core.quillins.registry import build_registry
from quill.core.quillins.snippets import SnippetContext, expand_snippet
from quill.core.quillins.validation import parse_manifest, validate_manifest

_TEXT_DIR = bundled_extensions_root() / "text-tools"
_INSERT_DIR = bundled_extensions_root() / "insert-tools"


def _load_manifest(directory: Path) -> ExtensionManifest:
    raw = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert validate_manifest(raw) == []
    return parse_manifest(raw)


def _load_algorithms() -> Any:
    spec = importlib.util.spec_from_file_location(
        "text_tools_algorithms", _TEXT_DIR / "algorithms.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# Vendored-algorithm characterization (the old core unit tests, re-pinned).
# --------------------------------------------------------------------------- #
def test_vendored_number_lines_matches_core() -> None:
    algorithms = _load_algorithms()
    assert algorithms.number_lines("a\nb\nc", start=5) == "5. a\n6. b\n7. c"
    assert algorithms.number_lines("a\n\nb", start=1) == "1. a\n\n2. b"


def test_vendored_wrap_matches_core() -> None:
    algorithms = _load_algorithms()
    assert algorithms.widest_line_width("ab\nabcd\nabc") == 4
    assert algorithms.widest_line_width("") == 0
    text = "the quick brown fox jumps over the lazy dog"
    wrapped = algorithms.hard_wrap(text, 15)
    assert all(len(line) <= 15 for line in wrapped.split("\n"))
    assert wrapped.replace("\n", " ") == text
    paragraphs = algorithms.hard_wrap("alpha beta gamma\n\ndelta epsilon zeta", 10)
    assert "" in paragraphs.split("\n")
    assert paragraphs.count("\n\n") == 1
    assert algorithms.hard_wrap("anything here", 0) == "anything here"


def test_vendored_regex_matches_core() -> None:
    algorithms = _load_algorithms()
    assert algorithms.count_matches("a1 b2 c3", r"\d") == 3
    assert algorithms.count_matches("no digits", r"\d") == 0
    text = "name: Ada\nname: Alan"
    assert algorithms.extract_matches(text, r"name: (\w+)") == "name: Ada\nname: Alan"
    with pytest.raises(algorithms.RegexError):
        algorithms.count_matches("text", r"(")


def test_vendored_set_ops_match_core() -> None:
    algorithms = _load_algorithms()
    text = "apple\nbanana\ncherry\nbanana\ndate\napple"
    cursor = len("apple\nbanana\ncherry\n")
    assert algorithms.lines_in_first_not_second(text, cursor) == ["cherry"]
    assert algorithms.lines_common_to_both(text, cursor) == ["apple", "banana"]
    assert algorithms.format_lines(["a", "b"]) == "a\nb"


def test_vendored_cursor_offset_is_line_start() -> None:
    algorithms = _load_algorithms()
    text = "apple\nbanana\ncherry\nbanana"
    # Line 4 begins after "apple\nbanana\ncherry\n".
    assert algorithms.cursor_offset_for_line(text, 4) == len("apple\nbanana\ncherry\n")
    assert algorithms.cursor_offset_for_line(text, 1) == 0


# --------------------------------------------------------------------------- #
# Manifest + registry contract.
# --------------------------------------------------------------------------- #
def test_text_tools_manifest_and_menus() -> None:
    manifest = _load_manifest(_TEXT_DIR)
    assert manifest.id == "com.quill.bundled.text-tools"
    assert manifest.is_layer_two
    command_ids = {command.id for command in manifest.contributes.commands}
    assert command_ids == {
        "ext.text.number_lines",
        "ext.text.hard_wrap",
        "ext.text.count_regex",
        "ext.text.extract_regex",
        "ext.text.lines_first_only",
        "ext.text.lines_common",
        "ext.text.html_to_markdown",
    }
    registry = build_registry([manifest])
    assert registry.conflicts == ()
    parents = {menu.parent for menu in registry.menus}
    assert parents == {"Format", "Search", "Edit"}


def test_insert_tools_manifest_is_capability_free_layer_one() -> None:
    manifest = _load_manifest(_INSERT_DIR)
    assert manifest.id == "com.quill.bundled.insert-tools"
    assert manifest.capabilities == ()
    assert not manifest.is_layer_two
    registry = build_registry([manifest])
    assert registry.conflicts == ()
    assert {menu.parent for menu in registry.menus} == {"Date and Time"}


def test_insert_tools_snippets_expand() -> None:
    manifest = _load_manifest(_INSERT_DIR)
    snippets = {command.id: command.snippet for command in manifest.contributes.commands}
    date = expand_snippet(snippets["ext.insert.date"], SnippetContext(date="2025-01-02"))
    assert date.text == "2025-01-02"
    both = expand_snippet(
        snippets["ext.insert.datetime"], SnippetContext(date="2025-01-02", time="09:30")
    )
    assert both.text == "2025-01-02 09:30"


# --------------------------------------------------------------------------- #
# Layer 2 handler behavior against a fake capability host.
# --------------------------------------------------------------------------- #
class _FakeApi:
    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[Any], None]] = {}

    def register_command(self, name: str, handler: Callable[[Any], None]) -> None:
        self.handlers[name] = handler


@dataclass
class _Cursor:
    line: int
    column: int = 0


@dataclass
class _FakeCtx:
    text: str = ""
    selection: str = ""
    cursor_line: int = 1
    prompts: list[str | None] = field(default_factory=list)
    set_text_calls: list[str] = field(default_factory=list)
    replaced: list[str] = field(default_factory=list)
    buffers: list[tuple[str, str]] = field(default_factory=list)
    announced: list[str] = field(default_factory=list)

    def get_text(self) -> str:
        return self.text

    def get_selection(self) -> str:
        return self.selection

    def get_cursor(self) -> _Cursor:
        return _Cursor(line=self.cursor_line)

    def prompt(self, title: str, label: str, default: str = "") -> str | None:
        return self.prompts.pop(0)

    def set_text(self, text: str) -> None:
        self.set_text_calls.append(text)
        self.text = text

    def replace_selection(self, text: str) -> None:
        self.replaced.append(text)

    def open_buffer(self, text: str, title: str = "") -> None:
        self.buffers.append((text, title))

    def announce(self, message: str) -> None:
        self.announced.append(message)

    def is_verbosity_speech_enabled(self) -> bool:
        return True


def _register_text_tools() -> _FakeApi:
    directory = _TEXT_DIR
    sys.path.insert(0, str(directory))
    try:
        namespace: dict[str, Any] = {}
        exec(  # noqa: S102 - executing the trusted in-repo Quillin under test
            (directory / "extension.py").read_text(encoding="utf-8"),
            namespace,
        )
        api = _FakeApi()
        namespace["register"](api)
        return api
    finally:
        sys.path.remove(str(directory))


def test_handler_number_lines_uses_prompt_and_set_text() -> None:
    api = _register_text_tools()
    ctx = _FakeCtx(text="a\nb\nc", prompts=["5"])
    api.handlers["number_lines"](ctx)
    assert ctx.set_text_calls == ["5. a\n6. b\n7. c"]
    assert ctx.announced == ["Numbered lines"]


def test_handler_number_lines_cancel_does_nothing() -> None:
    api = _register_text_tools()
    ctx = _FakeCtx(text="a", prompts=[None])
    api.handlers["number_lines"](ctx)
    assert ctx.set_text_calls == []
    assert ctx.announced == []


def test_handler_hard_wrap_on_selection() -> None:
    api = _register_text_tools()
    ctx = _FakeCtx(selection="the quick brown fox", prompts=["10"])
    api.handlers["hard_wrap"](ctx)
    assert ctx.replaced
    assert all(len(line) <= 10 for line in ctx.replaced[0].split("\n"))
    assert ctx.announced == ["Hard-wrapped at 10 characters"]


def test_handler_count_regex_announces_total() -> None:
    api = _register_text_tools()
    ctx = _FakeCtx(text="a1 b2 c3", prompts=[r"\d"])
    api.handlers["count_regex"](ctx)
    assert ctx.announced == ["3 match(es)"]


def test_handler_extract_regex_opens_buffer() -> None:
    api = _register_text_tools()
    ctx = _FakeCtx(text="name: Ada\nname: Alan", prompts=[r"name: \w+"])
    api.handlers["extract_regex"](ctx)
    assert ctx.buffers == [("name: Ada\nname: Alan", "Extracted matches")]


def test_handler_lines_first_only_splits_on_cursor_line() -> None:
    api = _register_text_tools()
    ctx = _FakeCtx(text="apple\nbanana\ncherry\nbanana\ndate\napple", cursor_line=4)
    api.handlers["lines_first_only"](ctx)
    assert ctx.buffers == [("cherry", "1 line(s) in first block only")]


def test_handler_lines_common_splits_on_cursor_line() -> None:
    api = _register_text_tools()
    ctx = _FakeCtx(text="apple\nbanana\ncherry\nbanana\ndate\napple", cursor_line=4)
    api.handlers["lines_common"](ctx)
    assert ctx.buffers == [("apple\nbanana", "2 line(s) common to both blocks")]
