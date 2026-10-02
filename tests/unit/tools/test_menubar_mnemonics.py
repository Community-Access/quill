"""GATE-15: a panel control may not share an Alt letter with a top-level menu.

The Alt+S bug (2026-09-30): ``&Stop`` on the main panel and ``&Subscriptions`` on
the menu bar. wxMSW gave the ambiguous key to the button, so the one key a listener
uses to reach the first menu pressed Stop instead. GATE-14 could not see it because
it compares controls with controls and menus with menus; this collision is between
the two scopes.

The first test is the one that matters: a gate that has never fired proves nothing,
so the detector is shown a known collision and must find exactly it.
"""

from __future__ import annotations

from pathlib import Path

from quill.tools import check_menubar_mnemonics as gate

_PANEL = """
import wx

def build(panel):
    label = wx.StaticText(panel, label="&Library:")
    play = wx.Button(panel, label="Pla&y")
    stop = wx.Button(panel, label="&Stop")
    fav = wx.Button(panel, label="Add to Fa&vorites")
    fine = wx.Button(panel, label="&Add Podcast...")
"""

_MENUS = """
import wx

def build(self):
    menu_bar = wx.MenuBar()
    subs = wx.Menu()
    subs.Append(wx.NewIdRef(), "&Stop\\tCtrl+.")
    menu_bar.Append(subs, "&Subscriptions")
    menu_bar.Append(wx.Menu(), "&View")
    menu_bar.Append(wx.Menu(), "&Help")
"""


def _run(tmp_path: Path, panel: str, menus: str) -> list[gate.Collision]:
    panel_file = tmp_path / "panel.py"
    menu_file = tmp_path / "menus.py"
    panel_file.write_text(panel, encoding="utf-8")
    menu_file.write_text(menus, encoding="utf-8")
    found = gate._Found()
    gate._scan(menu_file, found, menus=True, controls=False)
    gate._scan(panel_file, found, menus=False, controls=True)
    collisions = []
    for label, file, line in found.controls:
        letter = gate._letter(label)
        if letter and letter in found.menus:
            collisions.append(
                gate.Collision("test", letter, found.menus[letter], label, file, line)
            )
    return collisions


def test_the_detector_finds_the_alt_s_bug_and_the_alt_v_bug(tmp_path: Path) -> None:
    """Exactly the two collisions Jeff hit, and nothing else -- Play, Add and the
    Library label are all on letters the bar does not use."""
    found = _run(tmp_path, _PANEL, _MENUS)
    assert sorted((c.letter, c.control_label) for c in found) == [
        ("S", "&Stop"),
        ("V", "Add to Fa&vorites"),
    ]


def test_a_menu_row_inside_a_menu_is_not_a_top_level_menu(tmp_path: Path) -> None:
    """``subs.Append(id, "&Stop\\tCtrl+.")`` is a row one level down and shares the
    window with nothing on the panel. Only ``menu_bar.Append`` defines the bar."""
    found = _run(tmp_path, 'import wx\ndef b(p):\n    wx.Button(p, label="&Stop")\n', _MENUS)
    # &Stop the row must not have produced a second S entry on top of the menu's.
    assert [c.menu_label for c in found] == ["&Subscriptions"]


def test_a_doubled_ampersand_is_a_literal_and_not_a_mnemonic(tmp_path: Path) -> None:
    """ "Rock && Roll" has no access key; "&&" is how wx spells an ampersand."""
    assert gate._letter("Rock && Roll") is None
    assert gate._letter("&Rock && Roll") == "R"


def test_an_f_string_label_still_yields_its_leading_mnemonic() -> None:
    """The View menu's spine rows build ``f"{label}\\t{accelerator}"``; the gate
    reads the literal head so those rows are not invisible to it."""
    import ast

    node = ast.parse('f"&Inbox\\t{key}"').body[0].value  # type: ignore[attr-defined]
    assert gate._string_of(node) == "&Inbox\t"


def test_every_rostered_app_is_clean_today() -> None:
    """The live check, for the three apps reviewed so far. A new collision in any
    of them fails here with the file and line."""
    for app in gate.APPS:
        assert gate.check_app(app) == [], app


def test_a_label_built_at_run_time_is_checked_like_a_literal(monkeypatch) -> None:
    """The survey of 2026-09-30 found ``&Pause`` reclaiming Alt+P from the
    Podcasts menu the moment anything played: the gate had read only the static
    ``Pla&y``. Every label the transport button can show is now handed to the
    gate by its own module, and a bad one is reported with that module's path."""
    assert gate.check_app("cast") == []
    monkeypatch.setitem(
        gate.DYNAMIC_LABELS,
        "cast",
        (("quill/core/podcasts/transport_intent.py", lambda: ["&Pause The Daily"]),),
    )
    found = gate.check_app("cast")
    assert [(c.letter, c.control_label, c.control_file) for c in found] == [
        ("P", "&Pause The Daily", "quill/core/podcasts/transport_intent.py")
    ]


def test_both_transport_buttons_hand_the_gate_every_label_they_can_show() -> None:
    from quill.core import transport_button as tb
    from quill.core.podcasts import transport_intent

    providers = {rel: fn for rel, fn in gate.DYNAMIC_LABELS["cast"]}
    assert (
        providers["quill/core/podcasts/transport_intent.py"]() == transport_intent.label_samples()
    )
    providers = {rel: fn for rel, fn in gate.DYNAMIC_LABELS["radio"]}
    assert providers["quill/core/transport_button.py"]() == tb.label_samples(
        tb.RADIO_MNEMONICS, active_verb="stop"
    )


def test_the_gate_names_the_letter_the_menu_and_the_control() -> None:
    """A collision report the reader can act on without opening two files."""
    text = str(gate.Collision("cast", "S", "&Subscriptions", "&Stop", "quill/x.py", 7))
    assert "Alt+S" in text
    assert "'&Subscriptions'" in text
    assert "'&Stop'" in text
    assert "quill/x.py:7" in text
