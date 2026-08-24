"""The three chapter buttons on the player, present only when there are chapters.

Asked for directly (2026-08-18): *"the player should also have buttons to move
to the next and previous chapter and a button to list chapters as well so one
can jump quickly to a specific chapter."*

Chapters were reachable already -- the Playback menu has had them, and now the
whole transport keyboard carries them into every window
(:mod:`quill.core.radio.transport_commands`) -- but a menu is a place you go to
*look* for something and a button is a thing you meet. For an episode with
chapters, moving between them is the main way you navigate it, and that belongs
in the Tab order beside Play.

**They appear only when the thing playing actually has chapters**, and vanish
again when it does not. That is the opposite of this codebase's usual
"absent, not greyed" rule for menus, and deliberately so: a menu item that
comes and goes is confusing because you went looking for it, while three
permanently dead buttons in the Tab order are three keystrokes every listener
pays on every visit to a live station that will never have a chapter in it.

Split out of ``quill/apps/radio.py`` under GATE-11: that module is at its
budget, and "what the chapter buttons are" is a whole concern rather than a
line of wiring.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import transport_commands
from quill.ui.dialog_contract import set_accessible_name

#: Which verb each button runs, in the order they sit in the row, and the label
#: it wears **here**.
#:
#: The label is not the transport table's: that one is written for a Playback
#: menu, and this row answers to a different crowd. On a button, Alt+letter is
#: resolved by the menu bar first (#1208), and Quill Radio's menu bar owns S, V,
#: P, R, U, Q, H and W -- so the table's "P&revious Chapter" would open the
#: Record menu and the button would never fire. The gate in
#: tests/unit/ui/test_button_mnemonics.py is what caught exactly that.
_BUTTONS: tuple[tuple[str, str, str], ...] = (
    ("_prev_chapter_btn", transport_commands.PREVIOUS_CHAPTER, "Previous Chap&ter"),
    ("_next_chapter_btn", transport_commands.NEXT_CHAPTER, "&Next Chapter"),
    ("_chapters_btn", transport_commands.CHAPTER_LIST, "&Chapters..."),
)


def build(app: Any, panel: Any, buttons: Any, wx: Any) -> None:
    """Create the three buttons, hidden, and add them to *buttons*.

    The *key* in each accessible name comes from the shared transport table, so
    a button announces the same keystroke the menu advertises and a rebinding
    cannot leave the two disagreeing. The label does not -- see :data:`_BUTTONS`.
    """
    from quill.ui.radio import transport_keys

    for attribute, command_id, label in _BUTTONS:
        command = transport_commands.command(command_id)
        if command is None:  # pragma: no cover - the table is a constant
            continue
        button = wx.Button(panel, label=label)
        set_accessible_name(button, f"{label.replace('&', '')} ({command.key})")
        button.SetHelpText(
            "A chapter control; it appears only while what is playing has "
            "chapters, and runs the same command as its key."
        )
        button.Bind(
            wx.EVT_BUTTON,
            lambda _event, cid=command_id: _act(app, cid),
        )
        button.Hide()
        buttons.Add(button, 0, wx.RIGHT, 6)
        setattr(app, attribute, button)
    app._chapter_buttons_shown = False
    # Bound here rather than imported at use: the dispatcher is what makes the
    # button and the key do the same thing by construction.
    app._transport_keys = transport_keys


def _act(app: Any, command_id: str) -> None:
    from quill.ui.radio import transport_keys

    transport_keys.perform(app, command_id)
    refresh(app)


def has_chapters(app: Any) -> bool:
    """Whether the thing playing published chapters. Never raises.

    Read from the controller, which reads them from the source -- a video's own
    markers or an episode's Podcasting 2.0 chapters, never guessed.
    """
    controller = getattr(app, "_radio_controller", None)
    if controller is None:
        return False
    try:
        return bool(controller.chapters())
    except Exception:  # noqa: BLE001 - a button probe must never crash the panel
        return False


def refresh(app: Any) -> None:
    """Show or hide the three buttons to match what is playing.

    Re-laid out only when the answer *changes*, so this can be called from the
    status refresh (which fires on every playback event) without shuffling the
    Tab order under somebody's fingers.
    """
    wanted = has_chapters(app)
    if bool(getattr(app, "_chapter_buttons_shown", False)) == wanted:
        return
    app._chapter_buttons_shown = wanted
    shown = False
    for attribute, _command_id, _label in _BUTTONS:
        button = getattr(app, attribute, None)
        if button is None:
            continue
        button.Show(wanted)
        shown = True
    if not shown:
        return
    panel = getattr(app, "frame", None)
    if panel is not None:
        panel.Layout()
    announce = getattr(app, "_announce", None)
    if callable(announce) and wanted:
        # Said once, when they arrive: three new buttons appearing silently in
        # the Tab order is a change somebody discovers by tabbing into it.
        announce("This has chapters. Previous Chapter, Next Chapter and Chapters are on the panel.")
