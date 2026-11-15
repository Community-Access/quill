"""QUILL Lite's submenus with no letter of their own get a free one (how.md review 14).

Tools > WordPress, Tools > Forms and Edit > WordPress had no access letter in
QUILL Lite: no letter of either name is free in those menus. They take a free
letter in parentheses, as QUILL's menu pass does, and never one a row beside
them holds (GATE-14).
"""

from __future__ import annotations

import collections

import pytest

pytest.importorskip("wx")

from quill.apps.lite_window_menus import submenu_letters  # noqa: E402
from quill.core.lite.keymap import resolved_commands  # noqa: E402
from quill.ui.menu_routes import mnemonic_of  # noqa: E402


def _menus() -> dict[str, list]:
    menus: dict[str, list] = collections.defaultdict(list)
    for row in resolved_commands(lambda _feature: True, {}):
        menus[row[0]].append(row)
    return menus


def test_the_wordpress_and_forms_submenus_have_a_letter_no_sibling_holds() -> None:
    menus = _menus()
    for path, title in (("&Tools", "WordPress"), ("&Tools", "Forms"), ("&Edit", "WordPress")):
        given = submenu_letters(menus[path]).get(title, "")
        letter = mnemonic_of(given)
        assert letter, (path, title)
        others = [mnemonic_of(row[1]) for row in menus[path] if row[1] != title]
        assert letter not in others, (path, title, letter)


def test_no_menu_gains_a_duplicate_letter() -> None:
    for path, rows in _menus().items():
        titles = submenu_letters(rows)
        letters = [mnemonic_of(titles.get(r[1], r[1])) for r in rows if r[4] != "sep"]
        seen = [x for x in letters if x]
        assert len(seen) == len(set(seen)), path


def test_a_submenu_with_its_own_letter_is_left_alone() -> None:
    rows = [("&Format", "Word&Press", "", "", "sub"), ("&Format", "&Bold", "", "", "")]
    assert submenu_letters(rows) == {}  # type: ignore[arg-type]
