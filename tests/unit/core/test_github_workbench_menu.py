"""The GitHub Workbench Mode table (quill/core/github/workbench_menu.py).

One table for both editors: its shape, QUILL Lite's subset, the letters, the keys,
and how QUILL Lite's bar is arranged for each mode.
"""

from __future__ import annotations

import collections

from quill.core.github import workbench_menu as table
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.lite.commands import COMMANDS
from quill.core.lite.parity import COMMAND_EQUIVALENTS


def _letter(label: str) -> str:
    index = label.find("&")
    return label[index + 1].lower() if 0 <= index < len(label) - 1 else ""


def _menus(entries, title="&GitHub"):
    """Each (sub)menu's labels, by title."""
    found: dict[str, list[str]] = {title: []}
    for entry in entries:
        if isinstance(entry, table.Row):
            found[title].append(entry.label)
        elif isinstance(entry, table.Submenu):
            found[title].append(entry.title)
            found.update(_menus(entry.entries, entry.title))
    return found


def _no_bad_separators(entries) -> None:
    assert entries and entries[0] is not None and entries[-1] is not None
    for before, after in zip(entries, entries[1:], strict=False):
        assert not (before is None and after is None)
    for entry in entries:
        if isinstance(entry, table.Submenu):
            _no_bad_separators(entry.entries)


def test_no_separator_first_last_or_twice_in_any_menu() -> None:
    for entries in (
        table.WORKBENCH_ROWS,
        table.LITE_GITHUB_MENU,
        table.NORMAL_REMOTE_ROWS,
        table.REPOSITORY_ROWS,
        table.LOCAL_GIT_ROWS,
    ):
        _no_bad_separators(entries)


def test_no_access_letter_twice_in_any_one_menu() -> None:
    for entries in (table.WORKBENCH_ROWS, table.REPOSITORY_ROWS, table.LOCAL_GIT_ROWS):
        for title, labels in _menus(entries).items():
            letters = [_letter(label) for label in labels if _letter(label)]
            twice = [k for k, n in collections.Counter(letters).items() if n > 1]
            assert twice == [], (title, twice)


def test_the_first_row_is_the_way_out() -> None:
    first = table.WORKBENCH_ROWS[0]
    assert isinstance(first, table.Row)
    assert first.command_id == table.TOGGLE_COMMAND_ID
    assert first.lite_handler == table.TOGGLE_LITE_HANDLER


def test_quill_lite_is_a_subset_of_quill_and_never_ahead() -> None:
    quill_ids = set(table.command_ids())
    for row in table._walk(table.LITE_GITHUB_MENU):
        assert row.command_id in quill_ids
        # The parity table says the same thing the table does.
        assert COMMAND_EQUIVALENTS[row.lite_handler] == row.command_id, row


def test_every_command_id_is_in_quills_keymap_and_has_no_chord() -> None:
    for command_id in (
        *table.command_ids(),
        *table.command_ids(table.NORMAL_REMOTE_ROWS),
        *table.command_ids(table.REPOSITORY_ROWS),
    ):
        # Some older GitHub and Local Git ids predate the keymap entry
        # convention; keyless either way. The ids this program added must be there.
        if command_id in table.NEW_COMMAND_IDS:
            assert command_id in DEFAULT_KEYMAP, command_id
        assert DEFAULT_KEYMAP.get(command_id, "") == "", command_id


def test_every_quill_lite_handler_is_a_row_in_its_table_with_no_key() -> None:
    handlers = {row[3]: row for row in COMMANDS}
    for handler in table.lite_handlers():
        assert handler in handlers, handler
        assert handlers[handler][2] == "", handler


def test_every_moved_row_has_a_normal_home_and_every_new_one_is_listed() -> None:
    normal = {
        *table.command_ids(table.NORMAL_REMOTE_ROWS),
        *table.command_ids(table.REPOSITORY_ROWS),
        *table.command_ids(table.LOCAL_GIT_ROWS),
    }
    homeless = [
        cid
        for cid in table.command_ids()
        if cid not in normal and cid not in table.NEW_COMMAND_IDS and cid != "help.github_guide"
    ]
    assert homeless == []
    # Everything the normal homes hold goes into the GitHub menu: nothing is left behind.
    assert normal <= set(table.command_ids())


def test_readout_is_omitted_when_there_is_no_repository() -> None:
    assert table.readout_label("") == ""
    assert table.readout_label(" octo/cat ") == "Repository: octo/cat"


class _Menu:
    def __init__(self) -> None:
        self.items: list[object] = []

    def AppendSeparator(self) -> None:  # noqa: N802 - wx's spelling
        self.items.append("---")

    def AppendSubMenu(self, sub: _Menu, title: str) -> None:  # noqa: N802
        self.items.append((title, sub.items))

    def GetMenuItemCount(self) -> int:  # noqa: N802
        return len(self.items)


def test_fill_leaves_out_rows_and_empty_submenus_without_dangling_separators() -> None:
    menu = _Menu()
    count = table.fill(
        menu,
        table.WORKBENCH_ROWS,
        lambda m, row: m.items.append(row.label),
        _Menu,
        keep=lambda row: not row.command_id.startswith(("localgit.", "github.list", "github.c")),
    )
    assert count == len(menu.items) - menu.items.count("---")
    assert "&Local Git" not in [i[0] for i in menu.items if isinstance(i, tuple)]
    assert "Code&spaces" not in [i[0] for i in menu.items if isinstance(i, tuple)]
    assert menu.items[0] != "---" and menu.items[-1] != "---"
    assert all(
        not (a == "---" and b == "---") for a, b in zip(menu.items, menu.items[1:], strict=False)
    )


def _resolved() -> list[tuple[str, str, str, str, str]]:
    from quill.core.lite.keymap import resolved_commands

    return list(resolved_commands(lambda _area: True, {}))


def test_lite_normal_mode_has_no_github_menu_and_keeps_file_rows() -> None:
    rows = table.lite_arrange(_resolved(), workbench=False)
    assert all(row[0] != table.GITHUB_MENU_TITLE for row in rows)
    file_handlers = {row[3] for row in rows if row[0] == "&File"}
    assert set(table.LITE_NORMAL_HANDLERS) <= file_handlers


def test_lite_workbench_mode_moves_rows_after_tools_and_keeps_every_key() -> None:
    before = _resolved()
    rows = table.lite_arrange(before, workbench=True, repository="octo/cat")
    tops: list[str] = []
    for row in rows:
        top = row[0].split("|", 1)[0]
        if top not in tops:
            tops.append(top)
    assert tops.index("&GitHub") == tops.index("&Tools") + 1
    github = [row for row in rows if row[0] == "&GitHub"]
    assert github[0] == ("&GitHub", "Repository: octo/cat", "", "", "readout")
    assert github[1][3] == table.TOGGLE_LITE_HANDLER
    # Moved, never duplicated: a moved row is in GitHub and nowhere else.
    for handler in table.LITE_NORMAL_HANDLERS:
        assert [row[0] for row in rows if row[3] == handler] == ["&GitHub"]
    # One chord, one command, in both modes.
    keys_before = {row[3]: row[2] for row in before if row[2]}
    keys_after = {row[3]: row[2] for row in rows if row[2]}
    assert keys_before == keys_after
    labels = [row[1] for row in github if row[4] == ""]
    letters = [_letter(label) for label in labels]
    assert len(letters) == len(set(letters)), labels


def test_lite_workbench_mode_with_github_switched_off_is_normal_mode() -> None:
    rows = [row for row in _resolved() if row[3] != table.TOGGLE_LITE_HANDLER]
    assert table.lite_arrange(rows, workbench=True) == table.lite_arrange(rows, workbench=False)
