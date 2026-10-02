"""Simple and Advanced menus, and the two ways this feature could have lied.

The interesting tests here are not "does the mode hide the row". They are the two
ways a mode switch goes wrong:

* **A declared row nothing consults** -- ``ADVANCED_ROWS`` listing a key the menu
  bar never asks about. The switch would announce a change and change nothing.
* **A new row that vanishes for most people** -- somebody adds a menu item, never
  reads this module, and it silently does not exist in the default mode.

Both are checked against the real menu source, not against a fixture, because a
fixture would agree with whatever it was generated from.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts import menu_mode

MENU_SOURCE = Path("quill/apps/podcasts_menu.py")
VIEW_SOURCE = Path("quill/apps/podcasts_view_menu.py")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# -- the mode itself ---------------------------------------------------------- #


def test_simple_is_the_default_and_hides_the_advanced_rows() -> None:
    for row in ("backup", "restore", "import_opml", "delete_all_data"):
        assert not menu_mode.shows(menu_mode.SIMPLE, row)
        assert menu_mode.shows(menu_mode.ADVANCED, row)


def test_an_unknown_row_is_shown_rather_than_hidden() -> None:
    """The deliberate direction. A menu row added by somebody who never read
    menu_mode.py appears for everybody, rather than silently not existing in the
    default mode -- which is the failure nobody would file a bug about."""
    assert menu_mode.shows(menu_mode.SIMPLE, "a_row_nobody_has_written_yet")


def test_a_junk_stored_mode_reads_as_simple() -> None:
    """The fallback is the answer that cannot surprise anybody: a hand-edited file
    reading as Advanced would hand somebody seventeen extra rows unasked."""
    for junk in ("banana", "", None, 7, "ADVANCED "):
        assert menu_mode.normalize_mode(junk) in (menu_mode.SIMPLE, menu_mode.ADVANCED)
    assert menu_mode.normalize_mode("banana") == menu_mode.SIMPLE
    assert menu_mode.normalize_mode("Advanced") == menu_mode.ADVANCED


def test_every_advanced_row_carries_its_reason() -> None:
    """The comment on each key is the review: a row added here has to justify
    itself, and one removed has to say why it became everyday."""
    for row, reason in menu_mode.ADVANCED_ROWS.items():
        assert reason.strip(), row
        assert reason.strip().endswith("."), row


# -- the two ways it could lie ------------------------------------------------ #


def test_every_declared_advanced_row_is_actually_gated_in_the_menu_bar() -> None:
    """A declared row nothing consults is the worst of the three possible states:
    a switch that announces a change and changes nothing."""
    source = _source(MENU_SOURCE)
    ungated = [row for row in menu_mode.ADVANCED_ROWS if f'"{row}"' not in source]
    assert not ungated, (
        f"declared advanced but never gated in the menu bar: {ungated}. Either gate "
        "the row with self._advanced_row(...) or drop it from ADVANCED_ROWS."
    )


def test_the_gating_helper_goes_through_the_one_mode_reader() -> None:
    """Two readers of the mode is two answers about which rows exist."""
    view = _source(VIEW_SOURCE)
    assert "def _advanced_row(" in view
    assert "self._cast_shows_row(row)" in view


def test_the_switch_itself_is_never_one_of_the_hidden_rows() -> None:
    """The one row a mode must never hide is the row that changes the mode."""
    for row in ("advanced_features", "view_menu", "customize_features"):
        assert menu_mode.shows(menu_mode.SIMPLE, row)


def test_the_keyboard_editors_are_everyday_rows() -> None:
    """Every key is the listener's (qc.md section 8). A keyboard user who cannot
    find where keys are changed has been told the keyboard is not theirs, and
    Radio and QUILL Lite keep both editors in plain sight."""
    for row in ("keymap_editor", "global_hotkeys"):
        assert row not in menu_mode.ADVANCED_ROWS
        assert menu_mode.shows(menu_mode.SIMPLE, row)
    source = _source(MENU_SOURCE)
    assert "&Keyboard Shortcuts...\\tCtrl+Alt+Shift+W" in source
    assert "&Global Hotkeys...\\tCtrl+Alt+Shift+H" in source
    assert '_advanced_row(\n            help_menu, "keymap_editor"' not in source


# -- what it says ------------------------------------------------------------- #


def test_switching_on_names_the_count_and_the_way_back() -> None:
    """ "Advanced features on" alone does not tell a listener whether anything
    happened, and the way back should be in the sentence that got them here."""
    said = menu_mode.switch_announcement(menu_mode.ADVANCED)
    assert str(len(menu_mode.ADVANCED_ROWS)) in said
    assert "View menu" in said


def test_switching_off_says_the_features_are_still_reachable() -> None:
    """The promise that makes hiding safe rather than merely tidy."""
    said = menu_mode.switch_announcement(menu_mode.SIMPLE)
    assert "Command Palette" in said
    assert "View menu" in said


def test_the_label_says_which_mode_is_in_force() -> None:
    assert menu_mode.mode_label(menu_mode.SIMPLE) == "Simple"
    assert menu_mode.mode_label(menu_mode.ADVANCED) == "Advanced"
