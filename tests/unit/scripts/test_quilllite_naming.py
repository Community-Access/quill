"""QuillLite is one mixed-case word, everywhere a screen reader will read it.

The name is spoken far more often than it is seen: the Start Menu folder, the
shortcut in it, the desktop icon, the "Launch QuillLite" tick box at the end of
setup, the entry in Add/Remove Programs, the Open With list, and the window
title. Spelled `QuillLite` a reader speaks it as a name. Spelled `Quill Lite` it
becomes two words; spelled `QUILLLITE` it is read letter by letter; spelled
`Quill-Lite` the hyphen is read out as punctuation.

Nothing else enforces this. The installers take the name from one `#define`, the
launcher from one table row and the window title from one constant -- three
places that can drift apart silently, in a string no test ever looked at,
because every one of them still *builds*.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALLERS = (
    REPO_ROOT / "standalone" / "quilllite" / "installer" / "quilllite.iss",
    REPO_ROOT / "standalone" / "quilllite" / "installer" / "quilllite-lite.iss",
)
NAME = "QuillLite"

#: Spellings that are wrong wherever they appear in QuillLite's own packaging.
#: Matched case-sensitively for the first two (a lowercase "quilllite" is a
#: legitimate folder/identifier key) and word-boundaried so a longer word cannot
#: trip them.
WRONG = ("Quill Lite", "QUILL Lite", "Quill-Lite", "QUILLLITE")


def _iss_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="strict")


@pytest.mark.parametrize("installer", INSTALLERS, ids=lambda p: p.name)
def test_the_installer_defines_the_name_in_mixed_case(installer: Path) -> None:
    match = re.search(r'^#define AppName "([^"]+)"', _iss_text(installer), re.M)
    assert match is not None, f"{installer.name} defines no AppName"
    assert match.group(1) == NAME


@pytest.mark.parametrize("installer", INSTALLERS, ids=lambda p: p.name)
def test_the_start_menu_folder_is_named_from_that_define(installer: Path) -> None:
    """Explicit, not left to Inno's default: the folder is read aloud every time
    the user goes looking for the app."""
    text = _iss_text(installer)
    assert re.search(r"^DefaultGroupName=\{#AppName\}", text, re.M), (
        f"{installer.name} does not set DefaultGroupName={{#AppName}}"
    )


def _icons_section(path: Path) -> list[str]:
    """The ``[Icons]`` lines -- the shortcuts, and nothing else. ``Name:`` also
    starts a language, a setup type, a component and a task, none of which is a
    shortcut."""
    rows: list[str] = []
    inside = False
    for line in _iss_text(path).splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            inside = stripped.lower() == "[icons]"
            continue
        if inside and stripped and not stripped.startswith(";"):
            rows.append(stripped)
    return rows


@pytest.mark.parametrize("installer", INSTALLERS, ids=lambda p: p.name)
def test_every_shortcut_takes_its_name_from_the_define(installer: Path) -> None:
    """A literal in an [Icons] Name: is how the spelling drifts -- one shortcut
    gets renamed and the rest keep the old spelling."""
    rows = _icons_section(installer)
    assert rows, f"{installer.name} has no [Icons] section"
    offenders = [
        row
        for row in rows
        # The docs shortcut is named for the document, and the uninstaller
        # shortcut still carries {#AppName} in its own label.
        if "{#AppName}" not in row.split(";", 1)[0] and "userguide" not in row.lower()
    ]
    assert not offenders, f"{installer.name} names a shortcut literally:\n" + "\n".join(offenders)


@pytest.mark.parametrize("installer", INSTALLERS, ids=lambda p: p.name)
def test_no_misspelling_anywhere_in_the_installer(installer: Path) -> None:
    """Comments are exempt: nobody hears a comment. Everything else is read."""
    spoken = "\n".join(
        line for line in _iss_text(installer).splitlines() if not line.strip().startswith(";")
    )
    found = [bad for bad in WRONG if bad in spoken]
    assert not found, f"{installer.name} contains {found}; the name is one word, {NAME}"


def test_the_launcher_is_built_under_the_same_name() -> None:
    """The exe basename and its VERSIONINFO description both come from this row;
    the description is what Windows reads in a UAC prompt and Task Manager."""
    from scripts.build_native_launcher import PRODUCTS

    product = PRODUCTS["quilllite"]
    assert product.name == NAME
    assert product.display == NAME


def test_the_window_title_agrees_with_the_installer() -> None:
    """The one constant the app itself speaks from."""
    from quill.core.lite import APP_NAME

    assert APP_NAME == NAME
