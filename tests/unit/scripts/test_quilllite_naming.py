"""QUILL Lite is spelled one way everywhere a screen reader will read it.

The name is spoken far more often than it is seen: the Start Menu folder, the
shortcut in it, the desktop icon, the "Launch QUILL Lite" tick box at the end of
setup, the entry in Add/Remove Programs, the Open With list, and the window
title. Since 2026-09-25 that name is **QUILL Lite** -- the family name a reader
already knows, then the word that says which one.

The machine identifier did **not** change, and must not: the exe
(``QuillLite.exe``), the install and data folders, the single-instance name, the
release assets and the installer's AppId all keep the one-word ``QuillLite``,
because renaming any of them would strand an existing install. So this gate
checks both halves -- the spoken name is ``QUILL Lite``, and ``QuillLite``
survives only where it is an identifier.

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
#: One installer, since 2026-09-15. The thin "Lite" installer was retired with
#: the Companion zip -- see the note at the top of scripts/build_release.ps1 --
#: so QUILL Lite publishes an installer and a portable zip and nothing else.
INSTALLERS = (REPO_ROOT / "standalone" / "quilllite" / "installer" / "quilllite.iss",)
NAME = "QUILL Lite"
IDENTIFIER = "QuillLite"

#: Spellings that are wrong wherever they are spoken. Word-boundaried, so the
#: lowercase ``quilllite`` folder/identifier key cannot trip them.
WRONG = ("Quill Lite", "Quill-Lite", "QUILLLITE", "Quill lite", "QUILL LITE")

#: ``QuillLite`` as an identifier: the exe, a folder in a path, an asset prefix.
_IDENTIFIER_USE = re.compile(r"(?<=[\\/])QuillLite|QuillLite(?=[\\/\-.])")


def _iss_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="strict")


def _spoken_lines(path: Path) -> list[str]:
    """Everything outside comments: nobody hears a comment."""
    return [line for line in _iss_text(path).splitlines() if not line.strip().startswith(";")]


@pytest.mark.parametrize("installer", INSTALLERS, ids=lambda p: p.name)
def test_the_installer_defines_the_display_name(installer: Path) -> None:
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


@pytest.mark.parametrize("installer", INSTALLERS, ids=lambda p: p.name)
def test_an_upgrade_does_not_leave_the_old_shortcuts_behind(installer: Path) -> None:
    """The group was "QuillLite" until 2026-09-25. Inno reuses the previous
    group unless told not to, and never deletes a shortcut it did not make this
    time -- so without both of these an upgrade reads the product out twice."""
    text = _iss_text(installer)
    assert re.search(r"^UsePreviousGroup=no", text, re.M)
    assert '{autoprograms}\\QuillLite"' in text
    assert '{autodesktop}\\QuillLite.lnk"' in text


@pytest.mark.parametrize("installer", INSTALLERS, ids=lambda p: p.name)
def test_the_install_folder_keeps_the_identifier(installer: Path) -> None:
    """An upgrade must land where the last version is, not beside it."""
    assert re.search(r"^DefaultDirName=\{autopf\}\\QuillLite$", _iss_text(installer), re.M)


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
    spoken = "\n".join(_spoken_lines(installer))
    found = [bad for bad in WRONG if re.search(rf"\b{re.escape(bad)}\b", spoken)]
    assert not found, f"{installer.name} contains {found}; the name is {NAME}"


@pytest.mark.parametrize("installer", INSTALLERS, ids=lambda p: p.name)
def test_the_old_spelling_survives_only_as_an_identifier(installer: Path) -> None:
    """``QuillLite`` in a spoken line has to be a path, an exe or a registry
    key -- never a word somebody hears."""
    loose = []
    for line in _spoken_lines(installer):
        stripped = _IDENTIFIER_USE.sub("", line)
        if IDENTIFIER in stripped:
            loose.append(line.strip())
    assert not loose, f"{installer.name} speaks the old name:\n" + "\n".join(loose)


def test_the_launcher_keeps_its_exe_name_and_speaks_the_display_name() -> None:
    """The exe basename and its VERSIONINFO description both come from this row;
    the description is what Windows reads in a UAC prompt and Task Manager."""
    from scripts.build_native_launcher import PRODUCTS

    product = PRODUCTS["quilllite"]
    assert product.name == IDENTIFIER
    assert product.display == NAME


def test_the_window_title_agrees_with_the_installer() -> None:
    """The one constant the app itself speaks from, and the one it keeps its
    folder and single-instance name under."""
    from quill.core.lite import APP_ID, APP_NAME, RELEASE_ASSET_PREFIX

    assert APP_NAME == NAME
    assert APP_ID == IDENTIFIER
    assert RELEASE_ASSET_PREFIX == IDENTIFIER
