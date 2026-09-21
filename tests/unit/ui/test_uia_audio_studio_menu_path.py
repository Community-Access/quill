"""The UIA suite's Audio Studio menu path must still be the menu's own path.

``tests/uia/test_audio_studio_dialogs.py`` drives the real application by
keystroke, so it carries a literal menu path -- ``%thb`` for Tools > Speech >
Audiobook & Batch Speech. That literal rotted: it used to read ``%tsa`` for a
"Speech > Audio Studio" row that no longer exists, and because the UIA suite
runs nightly, informationally, on a runner nobody watches, the rot showed up
only as seven red tests whose failure (``ElementNotEnabled``) named neither the
menu nor the path. ``%ts`` opens Story Studio, which is modal, which disables
the main window, which is what the exception was actually about.

This gate is the cheap half of that lesson: it recomputes the path from the
menu source every time the fast suite runs, so a renamed label or a moved
mnemonic fails here -- in seconds, with the right sentence -- instead of at
3 a.m. in a workflow whose failures are advisory.

It is source-level for the same reason as the access-key gates beside it:
building the menu needs a ``wx.App`` and a display, and the literals are what
a reviewer reads and what a regression would change.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MENU = _ROOT / "quill" / "ui" / "main_frame_menu.py"
_UIA_TEST = _ROOT / "tests" / "uia" / "test_audio_studio_dialogs.py"


def _mnemonic(label: str) -> str:
    """The Alt letter *label* claims, lower-cased, or ``""``. ``&&`` is literal."""
    index = label.find("&")
    while index != -1 and label[index : index + 2] == "&&":
        index = label.find("&", index + 2)
    if index == -1 or index + 1 >= len(label):
        return ""
    return label[index + 1].lower()


def _labels_appended_to(source: str, variable: str) -> list[str]:
    """Every ampersanded label appended to the menu held in *variable*."""
    tree = ast.parse(source, filename=str(_MENU))
    labels: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in {"Append", "AppendCheckItem", "AppendRadioItem", "AppendSubMenu"}:
            continue
        owner = node.func.value
        if not isinstance(owner, ast.Name) or owner.id != variable:
            continue
        for argument in node.args:
            found = next(
                (
                    child.value
                    for child in ast.walk(argument)
                    if isinstance(child, ast.Constant)
                    and isinstance(child.value, str)
                    and "&" in child.value
                ),
                None,
            )
            if found is not None:
                labels.append(found)
                break
    return labels


def _one_label_containing(labels: list[str], fragment: str, where: str) -> str:
    matches = [label for label in labels if fragment in label]
    assert len(matches) == 1, (
        f"expected exactly one {where} label containing {fragment!r}, found {matches!r}; "
        "the UIA suite's Audio Studio menu path is derived from it"
    )
    return matches[0]


def _uia_menu_path() -> str:
    """``_AUDIO_STUDIO_MENU_PATH`` read out of the UIA test without importing it.

    Importing would pull in ``pywinauto``, which the fast suite does not have
    and should not need to check a string.
    """
    tree = ast.parse(_UIA_TEST.read_text(encoding="utf-8"), filename=str(_UIA_TEST))
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "_AUDIO_STUDIO_MENU_PATH" in targets:
                assert isinstance(node.value.value, str)
                return node.value.value
    raise AssertionError(f"{_UIA_TEST.name} no longer defines _AUDIO_STUDIO_MENU_PATH")


def test_the_uia_audio_studio_path_matches_the_menu() -> None:
    source = _MENU.read_text(encoding="utf-8")

    menu_bar = _labels_appended_to(source, "menu_bar")
    tools_title = _one_label_containing(menu_bar, "Tools", "menu-bar")

    tools_items = _labels_appended_to(source, "tools_menu")
    speech_title = _one_label_containing(tools_items, "Speec", "Tools-menu")

    speech_items = _labels_appended_to(source, "speech_menu")
    studio_title = _one_label_containing(speech_items, "Batch Speech", "Speech-submenu")

    expected = f"%{_mnemonic(tools_title)}{_mnemonic(speech_title)}{_mnemonic(studio_title)}"
    assert _uia_menu_path() == expected, (
        f"the UIA suite types {_uia_menu_path()!r} to open the Audio Studio, but the menu "
        f"now spells that path {expected!r} "
        f"({tools_title!r} > {speech_title!r} > {studio_title!r})"
    )


def test_each_letter_of_the_path_is_unique_in_its_own_menu() -> None:
    """A duplicated mnemonic cycles instead of pressing, so the path would hang.

    Windows does not activate a letter two rows share; it moves the highlight
    and waits for Enter. ``test_menu_item_access_keys.py`` already forbids that
    menu-wide, but the three letters this path depends on are worth naming: if
    one of them ever collides, the UIA suite would open a menu and sit there.
    """
    source = _MENU.read_text(encoding="utf-8")
    for variable, fragment in (
        ("menu_bar", "Tools"),
        ("tools_menu", "Speec"),
        ("speech_menu", "Batch Speech"),
    ):
        labels = _labels_appended_to(source, variable)
        wanted = _mnemonic(_one_label_containing(labels, fragment, variable))
        claimants = [label for label in labels if _mnemonic(label) == wanted]
        assert len(claimants) == 1, (
            f"Alt+{wanted.upper()} is claimed by {len(claimants)} rows of {variable}: "
            f"{claimants!r}; the Audio Studio menu path needs it to press, not cycle"
        )
