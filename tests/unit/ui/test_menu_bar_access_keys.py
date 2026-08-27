"""Every top-level menu must be openable from the keyboard, and say which key.

Asked for on 2026-08-26: *"all top level menu items on the menu bar need rich
ways to invoke them, like View, Edit, Station, Recording, Help"*. The item-level
rule has been enforced since 3.0 (``test_menu_accelerators``); the **menu
titles** were the one rung of the ladder nobody checked, and they are the rung
you need first -- a menu you cannot open is a menu whose items' keys do not
matter.

Two things are asserted:

* every title appended to a menu bar carries a mnemonic (``&Station``), so
  Alt+letter opens it;
* no two menus on the same bar claim the same letter, because the second one
  silently never opens -- the identical fault the item-level gate exists to
  prevent, one level up.

Source-level rather than runtime, because building every window needs a wx.App
and a display; the literals are what a reviewer reads and what a regression
would change.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3] / "quill"

#: ``menu_bar.Append(menu, "&Station")`` and ``menu_bar.Insert(2, menu, "&View")``.
_APPEND = re.compile(r"\b(?:menu_bar|menubar)\.(?:Append|Insert)\s*\(")


def _menu_bar_titles() -> dict[str, list[tuple[str, int]]]:
    """``{file: [(title, line), ...]}`` for every literal title on a menu bar."""
    found: dict[str, list[tuple[str, int]]] = {}
    for path in _ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if not _APPEND.search(text):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:  # pragma: no cover - the syntax gate catches these
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in ("Append", "Insert"):
                continue
            target = node.func.value
            if not isinstance(target, ast.Name) or target.id not in ("menu_bar", "menubar"):
                continue
            for arg in node.args:
                # The title is the only string literal in the call; a wrapped
                # one (_("&File")) is a Call and is read through it.
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    found.setdefault(str(path.relative_to(_ROOT.parent)), []).append((
                        arg.value,
                        node.lineno,
                    ))
                elif isinstance(arg, ast.Call):
                    for inner in arg.args:
                        if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                            found.setdefault(str(path.relative_to(_ROOT.parent)), []).append((
                                inner.value,
                                node.lineno,
                            ))
    return found


def _mnemonic(title: str) -> str:
    """The Alt letter a title claims, upper-cased, or ``""``."""
    index = title.find("&")
    while index != -1 and title[index : index + 2] == "&&":
        index = title.find("&", index + 2)
    if index == -1 or index + 1 >= len(title):
        return ""
    return title[index + 1].upper()


def test_every_menu_bar_title_carries_an_access_key() -> None:
    missing = [
        f"{path}:{line} {title!r}"
        for path, titles in _menu_bar_titles().items()
        for title, line in titles
        if not _mnemonic(title)
    ]
    assert not missing, "menu-bar titles with no Alt key:\n  " + "\n  ".join(missing)


def test_no_two_menus_on_one_bar_claim_the_same_letter() -> None:
    clashes: list[str] = []
    for path, titles in _menu_bar_titles().items():
        seen: dict[str, str] = {}
        for title, line in titles:
            letter = _mnemonic(title)
            if not letter:
                continue
            if letter in seen and seen[letter] != title:
                clashes.append(f"{path}:{line} Alt+{letter} is both {seen[letter]!r} and {title!r}")
            seen[letter] = title
    assert not clashes, "two menus claiming one key:\n  " + "\n  ".join(clashes)


def test_the_gate_is_actually_looking_at_something() -> None:
    """A scanner that finds nothing passes everything."""
    titles = _menu_bar_titles()
    flat = {title for entries in titles.values() for title, _line in entries}
    assert "&Station" in flat and "&Help" in flat
    assert len(flat) >= 15


def test_the_cheat_sheet_reads_the_letter_from_the_label_not_the_first_letter() -> None:
    """``Vi&deo`` is Alt+D; a sheet that guessed would be confidently wrong."""
    from quill.ui.radio.cheat_sheet_dialog import menu_titles

    class _Bar:
        def __init__(self, labels: list[str]) -> None:
            self._labels = labels

        def GetMenuCount(self) -> int:  # noqa: N802
            return len(self._labels)

        def GetMenuLabel(self, index: int) -> str:  # noqa: N802
            return self._labels[index]

    assert menu_titles(_Bar(["&Station", "Vi&deo", "F&ormat", "Fish && Chips", "None"])) == [
        ("Station", "Alt+S"),
        ("Video", "Alt+D"),
        ("Format", "Alt+O"),
    ]
    assert menu_titles(None) == []


def test_the_menus_are_rows_on_the_sheet() -> None:
    from quill.core.radio.cheat_sheet import build_sheet

    rows = build_sheet([("Station", "Browse Stations...\tCtrl+B")], [("Station", "Alt+S")])
    first = rows[0]
    assert first.group == "Menus"
    assert first.key == "Alt+S"
    assert "Station" in first.action
