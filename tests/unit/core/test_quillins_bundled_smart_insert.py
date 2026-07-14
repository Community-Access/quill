"""Unit tests for the bundled Smart Insert Quillin's argument-aware handlers.

Covers the =rand(paragraphs, lines) and =todo(count) handlers honoring the
arguments parsed from a smart trigger, and falling back to defaults when no
arguments are supplied. No wx and no subprocess.
"""

from __future__ import annotations

import importlib.util
from typing import Any

from quill.core.quillins.loader import bundled_extensions_root

_DIR = bundled_extensions_root() / "smart-insert"


def _load_extension() -> Any:
    spec = importlib.util.spec_from_file_location("smart_insert_ext", _DIR / "extension.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeApi:
    def __init__(self, settings: dict[str, object] | None = None) -> None:
        self._settings = settings or {}
        self.inserted: list[str] = []
        self.announced: list[str] = []

    def get_setting(self, key: str) -> object:
        return self._settings.get(key)

    def insert_text(self, text: str) -> None:
        self.inserted.append(text)

    def announce(self, message: str) -> None:
        self.announced.append(message)

    def show_choices(self, title: str, items: list[str]) -> str:
        return items[0]


class TestInsertRand:
    def test_honors_paragraph_and_line_args(self) -> None:
        ext = _load_extension()
        api = _FakeApi()
        ext.insert_rand(api, {"trigger": "rand", "args": ["4", "2"]})
        text = api.inserted[0]
        # 4 paragraphs separated by blank lines, 2 lines each.
        assert text.count("Paragraph 4, line 2") == 1
        assert "Paragraph 5" not in text
        assert text.count("\n\n") == 3  # 4 paragraphs -> 3 blank-line separators

    def test_defaults_when_no_args(self) -> None:
        ext = _load_extension()
        api = _FakeApi()
        ext.insert_rand(api, {"trigger": "rand", "args": []})
        text = api.inserted[0]
        assert "Paragraph 3, line 3" in text
        assert "Paragraph 4" not in text

    def test_defaults_when_no_event(self) -> None:
        ext = _load_extension()
        api = _FakeApi()
        ext.insert_rand(api)
        assert "Paragraph 3, line 3" in api.inserted[0]

    def test_non_numeric_args_fall_back_to_defaults(self) -> None:
        ext = _load_extension()
        api = _FakeApi()
        ext.insert_rand(api, {"args": ["abc", ""]})
        assert "Paragraph 3, line 3" in api.inserted[0]


class TestInsertTodo:
    def test_honors_count_arg(self) -> None:
        ext = _load_extension()
        api = _FakeApi()
        ext.insert_todo(api, {"trigger": "todo", "args": ["7"]})
        assert api.inserted[0].count("- [ ]") == 7

    def test_defaults_to_setting_when_no_args(self) -> None:
        ext = _load_extension()
        api = _FakeApi({"default_todo_count": 4})
        ext.insert_todo(api, {"args": []})
        assert api.inserted[0].count("- [ ]") == 4
