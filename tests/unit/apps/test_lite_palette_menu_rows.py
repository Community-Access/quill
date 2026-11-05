"""QUILL Lite's palette finds what its command table cannot hold.

The table is the menus' source, so every fixed command is already a row. The
open windows and the recent files are built into the menu at run time and were
invisible to the palette; they are added from the window's own menu bar.
"""

from __future__ import annotations

from quill.apps.lite_services import LiteServicesMixin
from quill.core.lite import keymap as keymap_mod
from quill.ui.palette_menu_reach import MENU_COMMAND_PREFIX
from tests.unit.ui.test_palette_menu_reach import _Bar, _Item, _Menu


class _Services(LiteServicesMixin):
    def __init__(self) -> None:
        self.keymap = keymap_mod.default_keymap()

    def feature_enabled(self, area_id: str) -> bool:  # noqa: ARG002
        return True


class _Frame:
    def __init__(self, bar) -> None:
        self._bar = bar

    def GetMenuBar(self):  # noqa: N802 - wx API shape
        return self._bar


def test_recent_files_and_windows_are_rows_and_table_commands_are_not_doubled() -> None:
    bar = _Bar(
        (
            "&File",
            _Menu(
                _Item(1, "&New\tCtrl+N"),
                _Item(2, "Open &Recent", submenu=_Menu(_Item(21, "&1 notes.txt\tAlt+Shift+1"))),
            ),
        ),
        ("&Window", _Menu(_Item(31, "&1 notes.txt\tAlt+1"))),
    )
    registry = _Services().command_registry(_Frame(bar))
    titles = {c.title for c in registry.list() if c.id.startswith(MENU_COMMAND_PREFIX)}
    assert "File > Open Recent > 1 notes.txt" in titles
    assert "Window > 1 notes.txt" in titles
    # File > New is a table command, so it is listed once, as lite.cmd_new.
    assert "File > New" not in titles
    assert any(c.id.startswith("lite.") for c in registry.list())
