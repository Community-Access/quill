"""The player, summoned where you are and gone when you are done.

The question this answers (2026-08-18): *"should the player be its own window?
Can we make that magical some how?"*

A permanent player window buys one obvious place and costs a third citizen in
the Alt+Tab rotation -- which is the thing that was being complained about in
the first place ("when in the browse window the main window showing the player
is in the alt+tab order"). And with the transport keyboard now working in every
window (:mod:`quill.ui.radio.transport_keys`), an always-open player is mostly
furniture.

So the player has no window. It has a **summons**:

* One key (Go to Player) opens this panel *wherever you already are*.
* It holds the whole transport plus a readout of what is playing, where you are
  in it, and how fast -- the facts a menu makes you hunt for.
* **Escape closes it and puts focus back exactly where it was**, to the control
  and the character. It is a visit, not a destination.
* It never joins the Alt+Tab rotation as something to manage: it is modal to
  the window that summoned it, so closing it cannot leave you somewhere else.

Every button runs the same dispatcher the keys and the menus run
(:func:`quill.ui.radio.transport_keys.perform`), so this panel cannot drift from
them -- and a verb the thing playing cannot do refuses out loud here exactly as
it does everywhere else.

The buttons are laid out in the order somebody reaches for them, not in the
order the table happens to list them: the transport first, then position, then
speed, then chapters.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio import transport_commands as tc
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

#: The buttons, in reaching order, as ``(command id, label)``. The labels are
#: this panel's own: the table's are written for a Playback menu, and here they
#: only compete with each other, so they can be short and plain.
#:
#: **Every mnemonic here is unique, including the Close button's O.** A repeated
#: mnemonic in a dialog does not activate anything -- wx cycles focus between
#: the claimants instead -- so a duplicate is a key that quietly stops working.
#: Previous Chapter took V and Volume Down took D for that reason: T and W were
#: already spoken for by Faster and Slower.
#:
#: Two commands are deliberately absent: Go to Player (this *is* the player) and
#: the command palette (a door out of a panel you summoned is noise). Where Am I
#: doubles as the Refresh this panel would otherwise need -- every button re-reads
#: the status line, so the one verb that changes nothing is how you ask again.
BUTTONS: tuple[tuple[str, str], ...] = (
    (tc.PLAY_PAUSE, "&Play/Pause"),
    (tc.STOP, "&Stop"),
    (tc.SKIP_BACK, "Skip &Back"),
    (tc.SKIP_FORWARD, "Skip &Forward"),
    (tc.ANNOUNCE_POSITION, "Where Am &I?"),
    (tc.PREVIOUS_CHAPTER, "Pre&vious Chapter"),
    (tc.NEXT_CHAPTER, "&Next Chapter"),
    (tc.CHAPTER_LIST, "&Chapters..."),
    (tc.SPEED_DOWN, "Slo&wer"),
    (tc.SPEED_UP, "Fas&ter"),
    (tc.SPEED_RESET, "Norma&l Speed"),
    (tc.VOLUME_DOWN, "Volume &Down"),
    (tc.VOLUME_UP, "Vol&ume Up"),
    (tc.MUTE, "&Mute/Unmute"),
)

#: Commands that must never become buttons. Named rather than implied, so the
#: test that keeps this panel in step with the table can tell "deliberately
#: absent" from "added to the table and forgotten here".
NOT_BUTTONS: frozenset[str] = frozenset({tc.GO_TO_PLAYER, tc.COMMAND_PALETTE})


#: The panel currently on screen, if any.
#:
#: The transport keyboard is installed on this panel too, so a key does not stop
#: working merely because you are standing in the player -- which is the whole
#: claim :mod:`quill.ui.radio.transport_keys` makes, and the panel was the one
#: window where it was not true. That makes Go to Player pressable *from inside
#: the player*, and a second modal stacked over the first is a trap: closing one
#: leaves you in the other, having pressed nothing to get there.
_OPEN: PlayerPanel | None = None


def summon(host: Any, parent: Any = None) -> None:
    """Open the panel over *parent*, and give focus back when it closes."""
    import wx

    global _OPEN
    if _OPEN is not None:
        # Pressed from inside the player. Saying so beats both alternatives: a
        # second panel is a trap, and doing nothing is how a key teaches
        # somebody it is broken.
        announce = getattr(host, "_announce", None)
        if callable(announce):
            announce("You are already in the player.")
        return
    window = parent or getattr(host, "frame", None) or getattr(host, "_win", None)
    if window is None:
        return
    # Whatever had focus, to the control -- not the window. Restoring the window
    # would leave somebody at the top of a list they were halfway down.
    previous = wx.Window.FindFocus()
    panel = PlayerPanel(window, host)
    _OPEN = panel
    try:
        panel.show()
    finally:
        _OPEN = None
    if previous is not None:
        try:
            previous.SetFocus()
        except Exception:  # noqa: BLE001 - the control may be gone; the window is not
            pass


class PlayerPanel:
    """A small modal surface holding the whole player."""

    def __init__(self, parent: Any, host: Any, *, announce: Callable[[str], None] | None = None):
        import wx

        self._wx = wx
        self._host = host
        self._announce = announce or getattr(host, "_announce", None) or (lambda _m: None)

        self.dialog = wx.Dialog(parent, title="Player")
        root = wx.BoxSizer(wx.VERTICAL)

        # The readout first, and read-only: what is playing, where, how fast.
        # A panel that offers twelve verbs and never says what they act on is a
        # panel somebody has to guess at.
        # Sized in characters, not pixels. A fixed (420, 80) box is 420 pixels
        # at every font size, so the listener who has turned the system font up
        # -- the listener most likely to be reading this box rather than hearing
        # it -- is the one whose text clips.
        char_width, char_height = self.dialog.GetTextExtent("M")
        self._status = wx.TextCtrl(
            self.dialog,
            value=self.status_text(),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            size=(char_width * 46, char_height * 4 + 8),
        )
        self._status.SetName("Now playing")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 10)

        grid = wx.GridSizer(0, 3, 6, 6)
        for command_id, label in BUTTONS:
            command = tc.command(command_id)
            button = wx.Button(self.dialog, label=label)
            if command is not None:
                button.SetName(f"{label.replace('&', '')} ({command.key})")
            button.Bind(wx.EVT_BUTTON, lambda _e, cid=command_id: self._run(cid))
            grid.Add(button, 0, wx.EXPAND)
        root.Add(grid, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # A sizer with a stretch spacer, not wx.ALIGN_RIGHT: the banned-pattern
        # gate rejects that alignment in quill/ui because of how it reports to
        # a screen reader (A11Y-4, the dialog contract).
        close_row = wx.BoxSizer(wx.HORIZONTAL)
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cl&ose")
        bind_close_button(self.dialog, close_btn)
        close_row.AddStretchSpacer()
        close_row.Add(close_btn)
        root.Add(close_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(self.dialog, cancel_id=wx.ID_CANCEL)

        # The transport keyboard, on the player itself. Without this the panel
        # was the one window in the app where the keys stopped working: a modal
        # dialog has no accelerator table of its own, so Ctrl+P did nothing here
        # while it did something in every window behind it. The keys and the
        # buttons run the same dispatcher and leave the same readout, because
        # ``after`` is the refresh the buttons already use.
        from quill.ui.radio import transport_keys

        transport_keys.install(self.dialog, host, wx=wx, after=self._refresh)

    def status_text(self) -> str:
        """What is playing, where you are in it, and how fast. Never raises.

        The reading itself belongs to :mod:`quill.ui.radio.transport_keys`: this
        panel is summoned from Quill Cast as well as Quill Radio, and only the
        dispatcher knows both players' shapes. Written here first, it knew one --
        so Cast's panel said "Playing." and nothing else.
        """
        from quill.ui.radio import transport_keys

        return transport_keys.describe_now_playing(self._host)

    def _refresh(self) -> None:
        """Re-read the status line, and only write it when it actually changed.

        ``SetValue`` moves the insertion point back to the start, so rewriting
        an identical string would disturb somebody who had tabbed into the
        readout to review it. A refused verb changes nothing, and now costs
        nothing.
        """
        try:
            fresh = self.status_text()
            if fresh != self._status.GetValue():
                self._status.SetValue(fresh)
        except Exception:  # noqa: BLE001 - the dialog may be closing
            return

    def _run(self, command_id: str) -> None:
        """Run a verb, then re-read the panel so it tells the new truth."""
        from quill.ui.radio import transport_keys

        transport_keys.perform(self._host, command_id)
        self._refresh()

    def show(self) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        try:
            return int(show_modal_dialog(self.dialog, "Player", announce=self._announce))
        finally:
            self.dialog.Destroy()
