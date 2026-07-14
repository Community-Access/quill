"""Proof-of-concept test for the bundled sample Quillin.

The ``examples/quillins/markdown-helpers`` directory is the framework's reference
Quillin: a Layer 1 snippet command plus a Layer 2 handler command. This test
proves the sample is a *real*, loadable extension — not just documentation — by
driving it through the same wx-free core the host uses:

* its ``manifest.json`` validates and parses into an :class:`ExtensionManifest`;
* :func:`build_registry` resolves both commands with no conflicts and wires the
  Format menu, context menu, and hotkey contributions;
* the Layer 1 snippet expands its ``${filename}``/``${date}``/``${cursor}`` tokens;
* the Layer 2 ``extension.py`` registers its handler via ``register(api)`` and the
  handler wraps a selection in Markdown bold against a fake host context.

It imports no ``wx`` and spawns no worker, so it runs everywhere the core tests
run while still exercising the end-to-end author-facing contract.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from quill.core.quillins.loader import bundled_extensions_root
from quill.core.quillins.model import ExtensionManifest
from quill.core.quillins.registry import build_registry
from quill.core.quillins.snippets import SnippetContext, expand_snippet
from quill.core.quillins.validation import parse_manifest, validate_manifest

_EXAMPLE_DIR = bundled_extensions_root() / "markdown-helpers"


def _load_manifest() -> ExtensionManifest:
    raw = json.loads((_EXAMPLE_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert validate_manifest(raw) == []
    return parse_manifest(raw)


def test_example_manifest_is_valid_and_parses() -> None:
    manifest = _load_manifest()
    assert manifest.id == "com.quill.bundled.markdown-helpers"
    assert manifest.is_layer_two
    assert manifest.main == "extension.py"
    command_ids = {command.id for command in manifest.contributes.commands}
    assert command_ids == {"ext.mdh.frontmatter", "ext.mdh.bold"}


def test_example_registry_resolves_without_conflicts() -> None:
    manifest = _load_manifest()
    registry = build_registry([manifest])
    assert registry.conflicts == ()
    assert registry.command_title("ext.mdh.bold") == "Wrap Selection in Bold"
    menu_parents = {menu.parent for menu in registry.menus}
    assert menu_parents == {"Format"}
    assert {ctx.command_id for ctx in registry.context_menu} == {"ext.mdh.bold"}
    assert {hotkey.command_id for hotkey in registry.hotkeys} == {"ext.mdh.bold"}


def test_example_snippet_expands_layer_one_placeholders() -> None:
    manifest = _load_manifest()
    snippet = next(
        command.snippet
        for command in manifest.contributes.commands
        if command.id == "ext.mdh.frontmatter"
    )
    assert snippet is not None
    expansion = expand_snippet(snippet, SnippetContext(filename="notes.md", date="2025-01-02"))
    assert "title: notes.md" in expansion.text
    assert "date: 2025-01-02" in expansion.text
    assert "${cursor}" not in expansion.text
    # The caret lands where ${cursor} was, before the trailing newline content.
    assert expansion.cursor == expansion.text.index("\n\n") + 2


class _FakeApi:
    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[Any], None]] = {}

    def register_command(self, name: str, handler: Callable[[Any], None]) -> None:
        self.handlers[name] = handler


class _FakeCtx:
    def __init__(self, selection: str) -> None:
        self._selection = selection
        self.replaced: list[str] = []
        self.announced: list[str] = []

    def get_selection(self) -> str:
        return self._selection

    def replace_selection(self, text: str) -> None:
        self.replaced.append(text)

    def announce(self, message: str) -> None:
        self.announced.append(message)

    def is_verbosity_speech_enabled(self) -> bool:
        return True


def _register_example() -> _FakeApi:
    namespace: dict[str, Any] = {}
    exec(  # noqa: S102 - executing the trusted in-repo sample under test
        (_EXAMPLE_DIR / "extension.py").read_text(encoding="utf-8"),
        namespace,
    )
    api = _FakeApi()
    namespace["register"](api)
    return api


def test_example_handler_wraps_selection_in_bold() -> None:
    manifest = _load_manifest()
    handler_name = next(
        command.handler for command in manifest.contributes.commands if command.id == "ext.mdh.bold"
    )
    assert handler_name == "wrap_bold"

    api = _register_example()
    assert handler_name in api.handlers

    ctx = _FakeCtx(selection="hello")
    api.handlers[handler_name](ctx)
    assert ctx.replaced == ["**hello**"]
    assert ctx.announced == ["Wrapped the selection in Markdown bold."]


def test_example_handler_announces_when_no_selection() -> None:
    api = _register_example()
    ctx = _FakeCtx(selection="")
    api.handlers["wrap_bold"](ctx)
    assert ctx.replaced == []
    assert ctx.announced == ["Select some text first, then run Wrap Selection in Bold."]
