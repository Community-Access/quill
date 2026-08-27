"""No control label may steal a letter its window's menu bar owns.

The report that named the whole class (2026-08-27): *"alt+s ends up taking me
to the treeview and not the station item on the menu bar."* On Windows a
control-label mnemonic outranks a menu-bar mnemonic, so the browse tree's
label ``"&Stations ..."`` silently disarmed the &Station menu in the very
window it had just been added to -- and every peer window had its own version
of the same theft (Recordings' list label ate its own &Recordings menu).

The rule, and its limit: it applies only to **windows that carry a menu bar**.
In an ordinary modal dialog a control mnemonic is the correct, standard
pattern -- there is no menu to fight -- which is why this test names its
surfaces explicitly instead of sweeping every dialog and drowning in correct
behaviour.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3] / "quill"

#: The letters of the radio app's main menu bar. Embedded main-window views
#: (Browse, Find Stations, ...) live under it, so their labels must avoid
#: these too.
MAIN_BAR = set("SEVPADRCQHWN")

#: Surface file -> the Alt letters its own window's bar(s) claim. Peer bars are
#: the surface's own menu + &Station + &Window; embeddable surfaces add the
#: main bar's letters.
SURFACE_BARS: dict[str, set[str]] = {
    "quill/ui/radio/browse_tree_dialog.py": {"B", "S", "W"} | MAIN_BAR,
    "quill/ui/radio/station_browser_dialog.py": {"S", "W"} | MAIN_BAR,
    "quill/ui/radio/recordings_manager_dialog.py": {"R", "S", "W"} | MAIN_BAR,
    "quill/ui/radio/schedule_recording_dialog.py": {"S", "W"},
    "quill/ui/radio/song_history_dialog.py": {"S", "W"},
    "quill/ui/radio/download_queue_dialog.py": {"D", "S", "W"},
    "quill/ui/radio/favorites_manager_dialog.py": {"F", "S", "W"} | MAIN_BAR,
    "quill/ui/radio/player_panel.py": {"P", "S", "W"} | MAIN_BAR,
    "quill/ui/radio/now_playing_dialog.py": {"V", "S", "W"},
}

_LABEL_RX = re.compile(r'label="([^"]*&[A-Za-z][^"]*)"')


def _mnemonic(label: str) -> str:
    index = label.find("&")
    while label[index : index + 2] == "&&":
        index = label.find("&", index + 2)
    if index == -1 or index + 1 >= len(label):
        return ""
    return label[index + 1].upper()


@pytest.mark.parametrize("surface", sorted(SURFACE_BARS))
def test_no_label_shadows_a_menu(surface: str) -> None:
    bar = SURFACE_BARS[surface]
    text = (_ROOT.parent / surface).read_text(encoding="utf-8", errors="replace")
    stolen = []
    for match in _LABEL_RX.finditer(text):
        label = match.group(1)
        letter = _mnemonic(label)
        if letter and letter in bar:
            line = text[: match.start()].count("\n") + 1
            stolen.append(f"line {line}: {label!r} steals Alt+{letter}")
    assert not stolen, f"{surface}: control labels stealing menu letters:\n  " + "\n  ".join(stolen)


def test_the_reported_case_is_fixed() -> None:
    """Alt+S in Browse Stations opens the Station menu; Alt+T jumps to the tree."""
    text = (_ROOT / "ui/radio/browse_tree_dialog.py").read_text(encoding="utf-8")
    assert 'label="S&tations (expand a source to browse it):"' in text
    assert '"&Stations' not in text
