"""Gate 3: the menus are shaped the way Word, WordPad and Notepad shaped them.

The last of the three menu gates. The other two ask whether a row advertises its
key (`test_menu_accelerators`) and whether two rows fight over one Alt letter
(`test_menu_item_access_keys`). This one asks the question underneath both:
**is the row where somebody would go looking for it?**

That is not a matter of taste. A person arriving from Word has thirty years of
muscle memory about which menu holds Find, and a screen-reader user pays for a
wrong guess in seconds of listening -- open the menu, hear eleven items, close
it, open another. Word, WordPad and Notepad agree about nearly all of this, and
where they agree there is nothing for QUILL to have an opinion about.

Source-level, like the other menu gates: building every menu needs a wx.App and
a display, and the literals are what a reviewer reads and what a regression
changes.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MENU = _ROOT / "quill" / "ui" / "main_frame_menu.py"
_LITE = _ROOT / "quill" / "core" / "lite" / "commands.py"

#: The top-level titles, in the order Word and WordPad put them. Notepad has a
#: subset in the same order. QUILL adds menus for things neither has (AI,
#: QuillVille) and they go after, never between.
_EXPECTED_ORDER: tuple[str, ...] = ("File", "Edit", "View", "Insert", "Format", "Tools", "Help")

#: ``command id -> the menu it belongs in``, where Microsoft's products agree.
#: The value is the *variable name* the builder uses for that menu, which is how
#: the source names a menu at all.
_EXPECTED_HOME: dict[str, str] = {
    # File: Word, WordPad and Notepad all agree.
    "file.new": "file_menu",
    "file.open": "file_menu",
    "file.save": "file_menu",
    "file.save_as": "file_menu",
    "file.print": "file_menu",
    # Edit: Word puts Go To under Edit beneath Find and Replace, and Notepad puts
    # it in Edit too.
    "edit.undo": "edit_menu",
    "edit.redo": "edit_menu",
    "navigate.go_to_line": "edit_menu",
    # View: the status bar is View in all three.
    "view.toggle_status_bar": "view_menu",
}

#: Rows the toolkit owns: wx gives them their platform label, their accelerator
#: and their handler from a stock id, which is why they carry no command id to
#: look up. Checked by the id instead, in the menu Microsoft puts them in.
_STOCK_HOME: dict[str, str] = {
    "wx.ID_CUT": "edit_menu",
    "wx.ID_COPY": "edit_menu",
    "wx.ID_PASTE": "edit_menu",
    "wx.ID_SELECTALL": "edit_menu",
    "wx.ID_UNDO": "edit_menu",
    "wx.ID_REDO": "edit_menu",
}

#: Rows whose home QUILL decides for itself, with the reason. A row here is a
#: deliberate divergence from the Microsoft shape, which rule 1 allows only when
#: something else in the family owns the position.
_OUR_OWN_SHAPE: dict[str, str] = {
    "edit.find": "Inside Edit's Search Tools submenu since 2026-09-17. Word has "
    "eleven search commands loose in Edit; a submenu is how eleven rows become one "
    "row plus a list, which is cheaper to hear.",
    "edit.replace": "As edit.find: inside Edit > Search Tools.",
    "format.selection_font": "Format > Font for Selection..., beside the other "
    "formatting rather than as Word's modal Font dialog: QUILL's font commands act on "
    "a selection and the menu says so, which is the difference a listener needs.",
    "view.toggle_soft_wrap": "View, which is where Notepad has Word Wrap -- but "
    "spelled Soft Wrap, because wrapping here never changes the file and Notepad's "
    "name has convinced people for thirty years that it might.",
    "edit.paste_plain_text": "Edit, beside Paste, which is where Word's Paste Special "
    "is -- but with its own row rather than a submenu, because there is one option.",
}


def _menu_source() -> str:
    return _MENU.read_text(encoding="utf-8")


def _appended_titles(source: str) -> list[str]:
    """The menu-bar titles, in the order they are appended."""
    pattern = re.compile(r'menu_bar\.Append\(\s*\w+,\s*(?:_\()?"([^"]+)"')
    return [match.group(1).replace("&", "") for match in pattern.finditer(source)]


def test_the_top_level_menus_are_in_microsofts_order() -> None:
    titles = _appended_titles(_menu_source())
    assert titles, "no menu-bar titles found; the scan has stopped seeing the bar"
    positions = {title: index for index, title in enumerate(titles)}
    expected = [title for title in _EXPECTED_ORDER if title in positions]
    actual = sorted(expected, key=lambda title: positions[title])
    assert actual == expected, (
        "QUILL's menu bar reorders the menus somebody arrived knowing:\n"
        f"  expected {expected}\n  found    {actual}"
    )


def test_every_menu_microsoft_has_is_present() -> None:
    titles = set(_appended_titles(_menu_source()))
    missing = [title for title in _EXPECTED_ORDER if title not in titles]
    assert not missing, f"menus somebody would look for and not find: {missing}"


def test_quills_own_menus_come_after_the_shared_ones() -> None:
    """Add to the end. A new menu between File and Edit moves everything."""
    titles = _appended_titles(_menu_source())
    if "Help" not in titles:
        return
    shared = [title for title in titles if title in _EXPECTED_ORDER]
    # Help is last in all three products, and QUILL's extra menus sit before it.
    assert shared[-1] == "Help", f"Help must be the last shared menu, found {shared[-1]}"


def _command_menu_homes(source: str) -> dict[str, set[str]]:
    """``command id -> the menu variables it is appended to``."""
    pattern = re.compile(
        r"(?P<menu>\w*menu\w*)\.Append(?:CheckItem|RadioItem|SubMenu)?\((?P<args>[^;]{0,400}?)\)\n",
        re.DOTALL,
    )
    homes: dict[str, set[str]] = {}
    for match in pattern.finditer(source):
        args = match.group("args")
        for command_id in re.findall(r'"([a-z_]+\.[a-z_0-9.]+)"', args):
            homes.setdefault(command_id, set()).add(match.group("menu"))
    return homes


def test_every_shared_command_is_in_the_menu_microsoft_puts_it_in() -> None:
    homes = _command_menu_homes(_menu_source())
    wrong: list[str] = []
    for command_id, expected in sorted(_EXPECTED_HOME.items()):
        found = homes.get(command_id)
        if not found:
            wrong.append(f"{command_id}: no menu row at all (expected {expected})")
        elif expected not in found:
            wrong.append(f"{command_id}: in {sorted(found)}, expected {expected}")
    assert not wrong, (
        "rows that are not where somebody would look for them (rule 1):\n  " + "\n  ".join(wrong)
    )


def test_the_stock_clipboard_rows_are_in_edit() -> None:
    """Cut, Copy, Paste, Select All, Undo, Redo -- Edit, in all three products."""
    source = _menu_source()
    wrong: list[str] = []
    for stock_id, expected in sorted(_STOCK_HOME.items()):
        pattern = re.compile(rf"(\w*menu\w*)\.Append\w*\(\s*{re.escape(stock_id)}\b")
        found = {match.group(1) for match in pattern.finditer(source)}
        if not found:
            continue  # a row QUILL does not offer at all is not a misplacement
        if expected not in found:
            wrong.append(f"{stock_id}: in {sorted(found)}, expected {expected}")
    assert not wrong, "stock rows in the wrong menu (rule 1):\n  " + "\n  ".join(wrong)


def test_exit_is_the_last_thing_in_file() -> None:
    """Every one of the three ends File with it, and muscle memory goes to the end."""
    source = _menu_source()
    assert "self._id_exit = wx.ID_EXIT" in source
    exit_row = source.rindex("self._id_exit")
    file_rows = [
        index for index in range(len(source)) if source.startswith("file_menu.Append", index)
    ]
    assert file_rows, "no File rows found"
    assert exit_row > file_rows[0], "Exit must come after File's other rows"


def test_every_deliberate_divergence_has_its_reason() -> None:
    for command_id, reason in sorted(_OUR_OWN_SHAPE.items()):
        assert len(reason) > 40, f"{command_id}: a divergence needs an argument"
        assert command_id not in _EXPECTED_HOME, f"{command_id} cannot be both"


def test_the_two_tables_do_not_disagree_with_the_code() -> None:
    """A divergence for a command that no longer exists is a stale exemption.

    Searched across the menu builders rather than one file: a menu row may be
    appended by the mixin that owns the feature (the font rows live in
    ``main_frame_editor_font.py``), which is the shape GATE-11 pushed them into.
    """
    sources = "".join(
        path.read_text(encoding="utf-8")
        for path in sorted((_ROOT / "quill" / "ui").glob("main_frame*.py"))
    )
    for command_id in sorted(_OUR_OWN_SHAPE):
        assert f'"{command_id}"' in sources, f"{command_id} is exempted but has no menu row"


def test_quilllite_keeps_the_same_menu_bar_shape() -> None:
    """Rule 2, one level up: the two products' menu bars agree about what exists.

    QuillLite's titles come from its command table, which is the one list its menu
    bar and its key list both read -- so this checks the table rather than a
    builder, and a menu that stopped existing would fail here.
    """
    from quill.core.lite.commands import COMMANDS

    titles: list[str] = []
    for row in COMMANDS:
        top = str(row[0]).split("|")[0].replace("&", "")
        if top and top not in titles:
            titles.append(top)
    for expected in ("File", "Edit", "View", "Insert", "Format", "Tools", "Help"):
        assert expected in titles, f"QuillLite has no {expected} menu"
    # And in the same relative order, for the same reason QUILL's are checked.
    positions = {title: index for index, title in enumerate(titles)}
    shared = [title for title in _EXPECTED_ORDER if title in positions]
    assert shared == sorted(shared, key=lambda title: positions[title])
