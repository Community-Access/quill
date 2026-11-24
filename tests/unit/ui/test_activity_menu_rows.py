"""Inkwell's kept results are reachable from its Help menu, with F9 and Shift+F9 (FUX-04)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.keymap import DEFAULT_KEYMAP
from quill.ui.activity_menu_rows import append_activity_rows

_ROOT = Path(__file__).resolve().parents[3]


class _Menu:
    def __init__(self) -> None:
        self.rows: list[str] = []

    def Append(self, _item_id: Any, label: str) -> None:  # noqa: N802 - wx's name
        self.rows.append(label)


class _Frame:
    def __init__(self) -> None:
        self.bound: list[Any] = []

    def Bind(self, _event: Any, handler: Any, id: Any = None) -> None:  # noqa: N802, A002
        self.bound.append(handler)


class _Host:
    def __init__(self) -> None:
        self.frame = _Frame()
        self.calls: list[str] = []
        self.kept: tuple[Any, ...] = ()

    def _menu_label(self, title: str, command_id: str) -> str:
        return f"{title}\t{DEFAULT_KEYMAP[command_id]}"

    def _keep_menu_ids(self, *refs: Any) -> None:
        self.kept = refs

    def open_activity(self) -> None:
        self.calls.append("activity")

    def repeat_last_result(self) -> None:
        self.calls.append("repeat")


def test_the_two_rows_show_their_keys_and_run_their_commands() -> None:
    host, menu = _Host(), _Menu()
    append_activity_rows(host, menu)
    assert menu.rows == ["Activit&y...\tShift+F9", "&Repeat Last Result\tF9"]
    for handler in host.frame.bound:
        handler(None)
    assert host.calls == ["activity", "repeat"]
    assert len(host.kept) == 2


def test_inkwell_help_menu_carries_the_rows() -> None:
    source = (_ROOT / "quill" / "apps" / "inkwell.py").read_text(encoding="utf-8")
    assert "append_activity_rows(self, help_menu)" in source
