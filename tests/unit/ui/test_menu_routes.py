"""The route pass itself: the seating rules, the fallbacks, and idempotence.

``test_quill_menu_accelerators.py`` asserts the *outcome* on the real menu bar --
every enabled item advertises a route, no popup claims a letter twice. This file
asserts the *rules*, on small menus built here, because the outcome test can only
say that something is wrong and not which rule broke.

The five that would each be a silent regression:

* **Accelerator beats submenu beats menu order.** This is what makes the pass
  safe to run unattended: Save keeps S from Snapshots because Save has Ctrl+S.
* **Maximum matching, not first-fit.** Greedy stranded nine File-menu items,
  including the whole Open from Remote subtree, because it took a letter that
  was some later item's only one.
* **A letter the title does not contain is appended**, in the Windows/CJK
  convention -- ``Print Studio... (&Z)`` -- rather than the item going without.
* **An appended letter folds into the path** rather than standing beside it:
  ``Print Studio... (Alt+F, &Z)``, one parenthetical and not two.
* **Idempotence.** A menu rebuilt in place is passed again, so a second run has
  to change nothing at all.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.ui.menu_routes import (  # noqa: E402
    apply_menu_routes,
    mnemonic_of,
    reapply_menu_routes,
    split_label,
    strip_mnemonic,
    with_mnemonic,
)

_TAB = chr(9)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _bar(menus: dict[str, list[tuple[str, str]]]):
    """A menu bar from ``{"&File": [("&Save", "Ctrl+S"), ("&New", "")]}``."""
    bar = wx.MenuBar()
    for title, rows in menus.items():
        menu = wx.Menu()
        for label, accel in rows:
            menu.Append(wx.ID_ANY, f"{label}{_TAB}{accel}" if accel else label)
        bar.Append(menu, title)
    return bar


def _labels(bar, index: int = 0) -> list[str]:
    return [item.GetItemLabel() for item in bar.GetMenu(index).GetMenuItems()]


def _mnemonics(bar, index: int = 0) -> list[str]:
    return [mnemonic_of(split_label(label)[0]) for label in _labels(bar, index)]


# ---------------------------------------------------------------------------
# label helpers, which need no menu at all


def test_a_label_splits_into_title_and_accelerator() -> None:
    assert split_label("Save &As...\tCtrl+Shift+S") == ("Save &As...", "Ctrl+Shift+S")
    assert split_label("&Bold") == ("&Bold", "")


def test_a_mnemonic_is_read_case_folded() -> None:
    assert mnemonic_of("Indentin&g") == "G"


def test_a_doubled_ampersand_is_a_literal_not_a_mnemonic() -> None:
    """A field called "R&&D" is called "R&D", and has no mnemonic."""
    assert mnemonic_of("R&&D") == ""
    assert strip_mnemonic("R&&D") == "R&&D"


def test_a_doubled_ampersand_survives_being_given_a_mnemonic() -> None:
    assert with_mnemonic("R&&D Notes", "N") == "R&&D &Notes"


def test_a_letter_the_title_has_is_marked_in_place() -> None:
    assert with_mnemonic("Print Studio...", "S") == "Print &Studio..."


def test_a_letter_the_title_lacks_is_appended() -> None:
    """The Windows/CJK convention, and better than no seat at all."""
    assert with_mnemonic("Print Studio...", "Z") == "Print Studio... (&Z)"


# ---------------------------------------------------------------------------
# the seating rules


def test_an_item_with_an_accelerator_keeps_its_letter(wx_app) -> None:
    """A command worth a global chord is worth its mnemonic."""
    bar = _bar({"&File": [("&Snapshots", ""), ("&Save", "Ctrl+S")]})
    apply_menu_routes(bar)
    assert _mnemonics(bar) == ["N", "S"] or _mnemonics(bar)[1] == "S"
    assert mnemonic_of(split_label(_labels(bar)[1])[0]) == "S"


def test_a_submenu_keeps_its_letter_over_a_plain_sibling(wx_app) -> None:
    """A parent's letter is the first step of the path for its whole subtree."""
    bar = wx.MenuBar()
    menu = wx.Menu()
    menu.Append(wx.ID_ANY, "&Import Notes")
    child = wx.Menu()
    child.Append(wx.ID_ANY, "&Word Document...")
    menu.AppendSubMenu(child, "&Import")
    bar.Append(menu, "&File")
    apply_menu_routes(bar)
    titles = [split_label(label)[0] for label in _labels(bar)]
    assert mnemonic_of(titles[1]) == "I", titles


def test_the_earlier_item_keeps_a_contested_letter(wx_app) -> None:
    bar = _bar({"&File": [("&New", ""), ("&Notes", "")]})
    apply_menu_routes(bar)
    assert mnemonic_of(split_label(_labels(bar)[0])[0]) == "N"


def test_no_two_items_in_one_popup_end_up_on_one_letter(wx_app) -> None:
    bar = _bar({"&File": [("&New", ""), ("&Notes", ""), ("&Nothing", "")]})
    apply_menu_routes(bar)
    letters = _mnemonics(bar)
    assert len(set(letters)) == len(letters), letters


def test_maximum_matching_seats_an_item_first_fit_would_strand(wx_app) -> None:
    """Greedy takes B for "Bat", stranding "Bee" whose only letters are B and E.

    A maximum matching moves the earlier item to its second choice instead,
    which is the whole reason the pass does not use first-fit: greedy stranded
    nine File-menu items, the Open from Remote subtree among them.
    """
    bar = _bar({"&File": [("Be", ""), ("Bee", ""), ("Ebb", "")]})
    apply_menu_routes(bar)
    letters = [letter for letter in _mnemonics(bar) if letter]
    assert len(letters) == 3, _labels(bar)
    assert len(set(letters)) == 3, _labels(bar)


def test_a_full_popup_leaves_an_item_with_no_letter_rather_than_a_duplicate(wx_app) -> None:
    """GATE-14's rule: a duplicate advertises a key that may not work.

    Thirty-seven items whose titles offer one letter between them: thirty-six
    can be seated (the alphabet plus the digits) and the last cannot.
    """
    bar = _bar({"&File": [(f"A{index}", "") for index in range(40)]})
    apply_menu_routes(bar)
    letters = [letter for letter in _mnemonics(bar) if letter]
    assert len(set(letters)) == len(letters)
    assert len(letters) <= 36


# ---------------------------------------------------------------------------
# the paths


def test_a_keyless_item_gains_its_alt_path(wx_app) -> None:
    bar = _bar({"&File": [("&New", "")]})
    apply_menu_routes(bar)
    assert _labels(bar)[0] == "&New (Alt+F, N)"


def test_a_nested_item_names_every_step(wx_app) -> None:
    bar = wx.MenuBar()
    menu = wx.Menu()
    child = wx.Menu()
    child.Append(wx.ID_ANY, "&Word Document...")
    menu.AppendSubMenu(child, "&Import")
    bar.Append(menu, "&File")
    apply_menu_routes(bar)
    nested = bar.GetMenu(0).GetMenuItems()[0].GetSubMenu().GetMenuItems()[0]
    assert nested.GetItemLabel() == "&Word Document... (Alt+F, I, W)"


def test_an_item_with_a_real_accelerator_is_left_alone(wx_app) -> None:
    """It already says how to reach it; a second route would be noise."""
    bar = _bar({"&File": [("&Save", "Ctrl+S")]})
    apply_menu_routes(bar)
    assert _labels(bar)[0] == f"&Save{_TAB}Ctrl+S"


def test_a_disabled_item_is_left_alone(wx_app) -> None:
    """There is nothing to reach, so a route would promise something false."""
    bar = _bar({"&File": [("&New", "")]})
    bar.GetMenu(0).GetMenuItems()[0].Enable(False)
    apply_menu_routes(bar)
    assert _labels(bar)[0] == "&New"


def test_an_appended_letter_folds_into_the_path(wx_app) -> None:
    """One parenthetical, not two: the letter says what it is for.

    Three items whose titles offer two letters between them, so one of them has
    no seat in its own name and gets a letter appended. The appended letter must
    end up marked *inside* the Alt path, not sitting in a bracket beside it.
    """
    bar = _bar({"&File": [("Aa", ""), ("Ab", ""), ("Ba", "")]})
    apply_menu_routes(bar)
    labels = _labels(bar)
    appended = [label for label in labels if "(Alt+F, &" in label]
    assert len(appended) == 1, labels
    assert appended[0].count("(") == 1, appended[0]
    assert " (&" not in appended[0], appended[0]


def test_the_menu_bar_itself_gets_distinct_letters(wx_app) -> None:
    bar = _bar({"&File": [("&New", "")], "&Format": [("&Bold", "")]})
    apply_menu_routes(bar)
    letters = [mnemonic_of(bar.GetMenuLabel(i)) for i in range(bar.GetMenuCount())]
    assert len(set(letters)) == 2, letters


def test_a_top_level_menu_with_no_letter_is_given_one(wx_app) -> None:
    bar = _bar({"Tools": [("&New", "")]})
    apply_menu_routes(bar)
    assert mnemonic_of(bar.GetMenuLabel(0)) == "T"


# ---------------------------------------------------------------------------
# running it again


def test_a_second_pass_changes_nothing(wx_app) -> None:
    """A menu rebuilt in place is passed again; the pass has to be a no-op then."""
    bar = _bar({
        "&File": [("&New", ""), ("&Notes", ""), ("&Save", "Ctrl+S")],
        "&Format": [("&Bold", "Ctrl+B"), ("Bullets", "")],
    })
    apply_menu_routes(bar)
    before = [_labels(bar, 0), _labels(bar, 1)]
    report = apply_menu_routes(bar)
    assert [_labels(bar, 0), _labels(bar, 1)] == before
    assert (report.routed, report.mnemonics_assigned, report.mnemonics_moved) == (0, 0, 0)


def test_the_report_counts_what_it_did(wx_app) -> None:
    bar = _bar({"&File": [("&New", ""), ("Notes", "")]})
    report = apply_menu_routes(bar)
    assert report.routed == 2
    assert report.mnemonics_assigned == 1  # "Notes" had none
    assert report.unroutable == ()


# ---------------------------------------------------------------------------
# the frame-level entry point


def test_reapply_returns_none_for_a_frame_with_no_menu_bar(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        assert reapply_menu_routes(frame) is None
    finally:
        frame.Destroy()


def test_reapply_returns_none_for_something_that_is_not_a_frame() -> None:
    assert reapply_menu_routes(object()) is None


def test_reapply_routes_a_frames_bar(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        frame.SetMenuBar(_bar({"&File": [("&New", "")]}))
        report = reapply_menu_routes(frame)
        assert report is not None and report.routed == 1
        assert frame.GetMenuBar().GetMenu(0).GetMenuItems()[0].GetItemLabel() == "&New (Alt+F, N)"
    finally:
        frame.Destroy()
