"""Unit tests for the bundled line-tools Quillin.

Covers:
- line_ops.py algorithm: duplicate, delete, move up/down, join paragraph,
  and join-with-next-line — including edge cases (first/last line, single line,
  blank lines, multi-paragraph). All six stay tested here because all six are
  still used: five of them by QUILL's own core commands, which is exactly why
  the Quillin stopped shipping them (bad.md 7.1, P2.5).
- manifest.json: validates, declares correct capabilities, and contributes the
  ONE command the core does not register — join with the next line.
- extension.py: the handler reads text + cursor offset, applies the transform,
  calls set_text only when the document changes, and always calls set_cursor.

No wx is imported and no subprocess is spawned.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from quill.core.quillins.loader import bundled_extensions_root
from quill.core.quillins.registry import build_registry
from quill.core.quillins.validation import parse_manifest, validate_manifest

_DIR = bundled_extensions_root() / "line-tools"


# -- helpers ------------------------------------------------------------------


def _load_manifest():
    raw = json.loads((_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert validate_manifest(raw) == []
    return parse_manifest(raw)


def _load_line_ops():
    spec = importlib.util.spec_from_file_location("line_ops", _DIR / "line_ops.py")
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
    text: str = ""
    cursor: int = 0
    set_text_calls: list[str] = field(default_factory=list)
    set_cursor_calls: list[int] = field(default_factory=list)

    def get_text(self) -> str:
        return self.text

    def get_cursor_offset(self) -> int:
        return self.cursor

    def set_text(self, text: str) -> None:
        self.set_text_calls.append(text)
        self.text = text

    def set_cursor(self, offset: int) -> None:
        self.set_cursor_calls.append(offset)
        self.cursor = offset


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


# -- line_ops.py algorithm ----------------------------------------------------


def test_duplicate_line_inserts_copy_below() -> None:
    ops = _load_line_ops()
    text = "alpha\nbeta\ngamma"
    # cursor on "beta" (line index 1, starts at offset 6)
    new_text, new_cursor = ops.duplicate_line(text, 6)
    assert new_text == "alpha\nbeta\nbeta\ngamma"
    assert new_text[new_cursor:].startswith("beta")


def test_duplicate_line_on_single_line() -> None:
    ops = _load_line_ops()
    new_text, new_cursor = ops.duplicate_line("only", 0)
    assert new_text == "only\nonly"
    assert new_cursor == 5


def test_delete_line_removes_current() -> None:
    ops = _load_line_ops()
    text = "alpha\nbeta\ngamma"
    new_text, _ = ops.delete_line(text, 6)
    assert new_text == "alpha\ngamma"


def test_delete_line_single_line_yields_empty() -> None:
    ops = _load_line_ops()
    new_text, new_cursor = ops.delete_line("only", 0)
    assert new_text == ""
    assert new_cursor == 0


def test_delete_last_line_leaves_cursor_on_previous() -> None:
    ops = _load_line_ops()
    text = "first\nlast"
    new_text, new_cursor = ops.delete_line(text, 6)
    assert new_text == "first"
    assert new_cursor == 0


def test_move_line_up_swaps_with_previous() -> None:
    ops = _load_line_ops()
    text = "alpha\nbeta\ngamma"
    new_text, _ = ops.move_line_up(text, 6)
    assert new_text == "beta\nalpha\ngamma"


def test_move_line_up_from_first_is_noop() -> None:
    ops = _load_line_ops()
    text = "alpha\nbeta"
    new_text, new_cursor = ops.move_line_up(text, 0)
    assert new_text == text
    assert new_cursor == 0


def test_move_line_down_swaps_with_next() -> None:
    ops = _load_line_ops()
    text = "alpha\nbeta\ngamma"
    new_text, _ = ops.move_line_down(text, 0)
    assert new_text == "beta\nalpha\ngamma"


def test_move_line_down_from_last_is_noop() -> None:
    ops = _load_line_ops()
    text = "alpha\nbeta"
    new_text, new_cursor = ops.move_line_down(text, 6)
    assert new_text == text
    assert new_cursor == 6


def test_join_paragraph_collapses_run() -> None:
    ops = _load_line_ops()
    text = "hello\nworld\n\nnext paragraph"
    new_text, _ = ops.join_paragraph(text, 0)
    assert new_text == "hello world\n\nnext paragraph"


def test_join_paragraph_single_line_is_noop() -> None:
    ops = _load_line_ops()
    text = "only\n\nother"
    new_text, new_cursor = ops.join_paragraph(text, 0)
    assert new_text == text


def test_join_paragraph_on_blank_line_is_noop() -> None:
    ops = _load_line_ops()
    text = "alpha\n\nbeta"
    blank_cursor = len("alpha\n")
    new_text, _ = ops.join_paragraph(text, blank_cursor)
    assert new_text == text


def test_join_with_next_line_merges_two_lines() -> None:
    ops = _load_line_ops()
    text = "hello  \n  world"
    new_text, _ = ops.join_with_next_line(text, 0)
    assert new_text == "hello world"


def test_join_with_next_line_on_last_is_noop() -> None:
    ops = _load_line_ops()
    text = "only"
    new_text, new_cursor = ops.join_with_next_line(text, 0)
    assert new_text == text


# -- manifest + registry ------------------------------------------------------


def test_manifest_validates_and_has_correct_id() -> None:
    manifest = _load_manifest()
    assert manifest.id == "com.quill.bundled.line-tools"
    assert manifest.is_layer_two


def test_manifest_capabilities() -> None:
    manifest = _load_manifest()
    assert "editor.read" in manifest.capabilities
    assert "editor.write" in manifest.capabilities


def test_it_ships_only_the_verb_the_core_does_not_have() -> None:
    """A Quillin may *add* a verb and may never re-ship one the core has.

    It shipped six. Five were QUILL core commands with real chords already --
    Ctrl+D, Ctrl+Shift+Delete, Ctrl+Shift+Up/Down, Ctrl+Alt+Shift+J -- so the
    same verb was registered twice, which is two places for the behaviour and
    the wording to drift (bad.md 7.1, P2.5). Join with the next line is the one
    the core does not register, and it is the one that stayed.
    """
    from quill.core.keymap import DEFAULT_KEYMAP

    manifest = _load_manifest()
    command_ids = {c.id for c in manifest.contributes.commands}
    assert command_ids == {"ext.lines.join_next"}
    for core_id in (
        "format.duplicate_line",
        "format.delete_line",
        "format.move_line_up",
        "format.move_line_down",
        "format.join_lines",
    ):
        assert DEFAULT_KEYMAP[core_id], core_id
    registry = build_registry([manifest])
    assert registry.conflicts == ()
    parents = {m.parent for m in registry.menus}
    assert parents == {"Edit"}


# -- extension handler behavior -----------------------------------------------


def test_handler_join_with_next_line_merges() -> None:
    api = _register_extension()
    ctx = _FakeCtx(text="hello\nworld", cursor=0)
    api.handlers["join_with_next_line"](ctx)
    assert ctx.set_text_calls == ["hello world"]


def test_handler_set_cursor_always_called() -> None:
    """Even when the text does not change: the caret still has to be placed."""
    api = _register_extension()
    ctx = _FakeCtx(text="alpha", cursor=0)
    api.handlers["join_with_next_line"](ctx)
    assert ctx.set_text_calls == []
    assert ctx.set_cursor_calls == [0]
