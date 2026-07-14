"""Unit tests for the bundled insert-character Quillin.

Covers:
- codepoints.py algorithm: valid hex, decimal (d prefix), U+ notation, empty
  input, out-of-range, surrogates, and invalid strings.
- manifest.json: validates, resolves to Insert menu, declares correct
  capabilities and a single Layer 2 handler command.
- extension.py: handler inserts the correct character, announces the code point
  name, handles invalid input gracefully, and cancels on prompt dismissal.

No wx is imported and no subprocess is spawned.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest

from quill.core.quillins.loader import bundled_extensions_root
from quill.core.quillins.registry import build_registry
from quill.core.quillins.validation import parse_manifest, validate_manifest

_DIR = bundled_extensions_root() / "insert-character"


# -- helpers ------------------------------------------------------------------


def _load_manifest():
    raw = json.loads((_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert validate_manifest(raw) == []
    return parse_manifest(raw)


def _load_codepoints():
    spec = importlib.util.spec_from_file_location("codepoints", _DIR / "codepoints.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeApi:
    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[Any], None]] = {}

    def register_command(self, name: str, handler: Callable[[Any], None]) -> None:
        self.handlers[name] = handler


@dataclass
class _FakeCtx:
    prompts: list[str | None] = field(default_factory=list)
    inserted: list[str] = field(default_factory=list)
    announced: list[str] = field(default_factory=list)

    def prompt(self, title: str, label: str, default: str = "") -> str | None:
        return self.prompts.pop(0)

    def insert_text(self, text: str) -> None:
        self.inserted.append(text)

    def announce(self, message: str) -> None:
        self.announced.append(message)

    def is_verbosity_speech_enabled(self) -> bool:
        return True


def _register_extension() -> _FakeApi:
    sys.path.insert(0, str(_DIR))
    try:
        ns: dict[str, Any] = {}
        exec((_DIR / "extension.py").read_text(encoding="utf-8"), ns)  # noqa: S102
        api = _FakeApi()
        ns["register"](api)
        return api
    finally:
        sys.path.remove(str(_DIR))


# -- codepoints.py algorithm --------------------------------------------------


def test_hex_input_returns_correct_char() -> None:
    cp = _load_codepoints()
    assert cp.parse_codepoint("41") == "A"
    assert cp.parse_codepoint("1F600") == "\U0001f600"


def test_hex_is_case_insensitive() -> None:
    cp = _load_codepoints()
    assert cp.parse_codepoint("1f600") == cp.parse_codepoint("1F600")


def test_decimal_prefix_d() -> None:
    cp = _load_codepoints()
    assert cp.parse_codepoint("d65") == "A"
    assert cp.parse_codepoint("d128512") == "\U0001f600"


def test_uppercase_D_is_hex_digit_not_prefix() -> None:
    cp = _load_codepoints()
    assert cp.parse_codepoint("D") == "\r"  # 0xD == carriage return


def test_u_plus_notation() -> None:
    cp = _load_codepoints()
    assert cp.parse_codepoint("U+0041") == "A"
    assert cp.parse_codepoint("u+1F600") == "\U0001f600"


def test_whitespace_is_stripped() -> None:
    cp = _load_codepoints()
    assert cp.parse_codepoint("  41  ") == "A"


def test_empty_input_raises() -> None:
    cp = _load_codepoints()
    with pytest.raises(cp.CodepointError, match="Enter a Unicode code point"):
        cp.parse_codepoint("")
    with pytest.raises(cp.CodepointError):
        cp.parse_codepoint("   ")


def test_invalid_hex_raises() -> None:
    cp = _load_codepoints()
    with pytest.raises(cp.CodepointError, match="Invalid code point"):
        cp.parse_codepoint("GGGG")


def test_out_of_range_raises() -> None:
    cp = _load_codepoints()
    with pytest.raises(cp.CodepointError, match="out of range"):
        cp.parse_codepoint("110000")  # one past U+10FFFF


def test_unpaired_surrogate_raises() -> None:
    cp = _load_codepoints()
    with pytest.raises(cp.CodepointError, match="surrogate"):
        cp.parse_codepoint("D800")
    with pytest.raises(cp.CodepointError, match="surrogate"):
        cp.parse_codepoint("DFFF")


def test_boundary_codepoints_are_valid() -> None:
    cp = _load_codepoints()
    assert cp.parse_codepoint("0") == "\x00"
    assert cp.parse_codepoint("10FFFF") == "\U0010ffff"


# -- manifest + registry ------------------------------------------------------


def test_manifest_validates_and_has_correct_id() -> None:
    manifest = _load_manifest()
    assert manifest.id == "com.quill.bundled.insert-character"
    assert manifest.is_layer_two


def test_manifest_has_correct_capabilities() -> None:
    manifest = _load_manifest()
    assert set(manifest.capabilities) >= {"ui.prompt", "ui.announce", "editor.write"}


def test_manifest_single_command_under_insert_menu() -> None:
    manifest = _load_manifest()
    command_ids = {c.id for c in manifest.contributes.commands}
    assert "ext.insert.character" in command_ids
    registry = build_registry([manifest])
    assert registry.conflicts == ()
    parents = {m.parent for m in registry.menus}
    assert "Insert" in parents


# -- extension handler behavior -----------------------------------------------


def test_handler_inserts_ascii_char() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["41"])
    api.handlers["insert_character"](ctx)
    assert ctx.inserted == ["A"]
    assert ctx.announced and "U+0041" in ctx.announced[0]


def test_handler_inserts_emoji() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["1F600"])
    api.handlers["insert_character"](ctx)
    assert ctx.inserted == ["\U0001f600"]


def test_handler_inserts_via_decimal_prefix() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["d65"])
    api.handlers["insert_character"](ctx)
    assert ctx.inserted == ["A"]


def test_handler_inserts_via_u_plus_notation() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["U+0041"])
    api.handlers["insert_character"](ctx)
    assert ctx.inserted == ["A"]


def test_handler_announces_codepoint_and_name() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["41"])
    api.handlers["insert_character"](ctx)
    assert ctx.announced
    assert "U+0041" in ctx.announced[0]
    assert "LATIN" in ctx.announced[0].upper()


def test_handler_cancel_does_nothing() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=[None])
    api.handlers["insert_character"](ctx)
    assert ctx.inserted == []
    assert ctx.announced == []


def test_handler_invalid_input_announces_error_no_insert() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["GGGG"])
    api.handlers["insert_character"](ctx)
    assert ctx.inserted == []
    assert ctx.announced
    assert "Invalid" in ctx.announced[0] or "code point" in ctx.announced[0].lower()


def test_handler_surrogate_announces_error() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["D800"])
    api.handlers["insert_character"](ctx)
    assert ctx.inserted == []
    assert ctx.announced


def test_handler_out_of_range_announces_error() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["110000"])
    api.handlers["insert_character"](ctx)
    assert ctx.inserted == []
    assert ctx.announced
