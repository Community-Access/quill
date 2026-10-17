"""GATE-15, at run time: no control in an app's main window shares an Alt letter
with a menu on that window's menu bar.

On wxMSW an Alt+letter that both a top-level menu and a control in the same
frame claim goes to the *control*, so the menu stops opening from that letter
and nothing says so (Jeff in Quill Cast, 2026-09-30: "alt+s doesn't invoke the
station menu either, it invokes stop"). ``quill/tools/check_menubar_mnemonics.py``
reads that from source, which cannot see a label handed to a helper
(``PlayerPanel._button``), read from a tuple table (Studio's three journey
buttons), or a menu appended by a helper (the shared **Window** menu). The
2026-10-17 pass (todo 49) found exactly those: the Media Player's Play,
Previous chapter, Rewind, Forward and Normalize loudness took Alt+P, V, W, F
and N from Playback, View, Window, File and Navigation; Studio's Build From
Recordings took Alt+B from Book Tools; QUILL Transcribe's Discard Held Words
took Alt+W from Window.

So this gate builds each app's **real** main window in memory (no input is
sent and nothing is shown; ``tests/unit/docs/_app_menu_bar.py`` closes every
door to the machine) and walks every control under the frame, notebook pages
included, against the menu titles the frame really has. Labels a control
shows only in another state (Pause, Unmute) are listed per app and checked
the same way. The rule is GATE-15's: **the menu bar wins**, and the control
moves to a free letter, or loses its mnemonic when none is free (GATE-14).
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.unit.docs._app_menu_bar import real_app_shell
from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")


@pytest.fixture
def wx_app():
    yield wx.App.Get() or shared_wx_app()


_CONTROLS = ("Button", "ToggleButton", "CheckBox", "RadioButton", "StaticText")


def _letter(label: str) -> str:
    index = label.find("&")
    while index != -1 and label[index : index + 2] == "&&":
        index = label.find("&", index + 2)
    if index == -1 or index + 1 >= len(label) or not label[index + 1].isalnum():
        return ""
    return label[index + 1].upper()


def _menu_letters(frame: Any) -> dict[str, str]:
    bar = frame.GetMenuBar()
    letters: dict[str, str] = {}
    for index in range(bar.GetMenuCount()):
        title = bar.GetMenuLabel(index)
        if _letter(title):
            letters.setdefault(_letter(title), title)
    return letters


def _control_labels(window: Any) -> list[str]:
    found: list[str] = []
    for child in window.GetChildren():
        if type(child).__name__ in _CONTROLS:
            found.append(child.GetLabel())
        found.extend(_control_labels(child))
    return found


def collisions(frame: Any, other_states: tuple[str, ...] = ()) -> list[str]:
    """``"'Re&wind' takes Alt+W from '&Window'"`` for every clash in *frame*."""
    menus = _menu_letters(frame)
    clashes = []
    for label in [*_control_labels(frame), *other_states]:
        letter = _letter(label)
        if letter and letter in menus:
            clashes.append(f"{label!r} takes Alt+{letter} from {menus[letter]!r}")
    return clashes


def duplicates(frame: Any, other_states: tuple[str, ...] = ()) -> list[str]:
    """GATE-14 across the whole frame: two different controls on one letter.

    Each entry of *other_states* is a second label of a control already in the
    frame (Pause for Play), so it is checked against the menus above but not
    counted again here.
    """
    seen: dict[str, str] = {}
    clashes = []
    for label in _control_labels(frame):
        letter = _letter(label)
        if not letter:
            continue
        if letter in seen and seen[letter] != label:
            clashes.append(f"{label!r} and {seen[letter]!r} both claim Alt+{letter}")
        seen.setdefault(letter, label)
    return clashes


#: (module, frame class, labels a control shows in another state).
APPS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "player": (
        "quill.apps.player",
        "QuillMediaPlayerFrame",
        ("P&ause", "&Unmute"),  # PlayerPanel's other states, as the player names them
    ),
    "studio": ("quill.apps.studio", "StudioAppFrame", ()),
    "transcribe": ("quill.apps.transcribe", "QuillTranscribeFrame", ()),
    "inkwell": ("quill.apps.inkwell", "QuillInkwellFrame", ()),
    "converter": ("quill.apps.converter", "QuillConverterFrame", ()),
    "weather": ("quill.apps.weather", "WeatherAppFrame", ()),
}


@pytest.mark.parametrize("app", sorted(APPS))
def test_no_control_takes_a_menu_letter(app: str, quill_data_dir, monkeypatch, request) -> None:  # type: ignore[no-untyped-def]
    module, cls, other_states = APPS[app]
    with real_app_shell(monkeypatch, request, module, cls) as shell:
        assert len(_menu_letters(shell.frame)) >= 5  # a gate that sees no menus passes all
        assert len(_control_labels(shell.frame)) >= 3
        found = collisions(shell.frame, other_states)
        dupes = duplicates(shell.frame, other_states)
    assert found == [], "controls that take a menu's Alt letter:\n  " + "\n  ".join(found)
    assert dupes == [], "controls sharing an Alt letter:\n  " + "\n  ".join(dupes)


def test_the_player_states_are_the_ones_the_panel_shows(wx_app) -> None:
    """The extra labels above are the player's real Pause and Unmute, not a guess."""
    from quill.ui.media.player_access_keys import PLAYER_PANEL_LABELS

    _module, _cls, other_states = APPS["player"]
    assert PLAYER_PANEL_LABELS["player.pause"] in other_states
    assert PLAYER_PANEL_LABELS["player.unmute"] in other_states


def test_the_walk_reaches_a_helper_built_button(wx_app) -> None:
    """A gate that cannot see the Window menu or a looped label passes everything."""
    frame = wx.Frame(None)
    try:
        bar = wx.MenuBar()
        bar.Append(wx.Menu(), "&File")
        bar.Append(wx.Menu(), "&Window")
        frame.SetMenuBar(bar)
        panel = wx.Panel(frame)
        for label in ("&Open", "Re&wind"):
            wx.Button(panel, label=label)
        assert collisions(frame) == ["'Re&wind' takes Alt+W from '&Window'"]
        assert collisions(frame, ("&Forward",)) == [
            "'Re&wind' takes Alt+W from '&Window'",
            "'&Forward' takes Alt+F from '&File'",
        ]
    finally:
        frame.Destroy()
