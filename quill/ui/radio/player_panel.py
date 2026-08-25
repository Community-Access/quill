"""The player: a real window in the standalone apps, a summons everywhere else.

The question this answered first (2026-08-18) was *"should the player be its
own window?"* -- and the first answer was no: a permanent player window costs a
third citizen in the Alt+Tab rotation, so the player became a modal panel
summoned with Go to Player and dismissed with Escape.

That answer was half right, and the wrong half got reported (2026-08-23): *"the
player is not showing... it should come to the front"*. A modal panel cannot be
Ctrl+Tabbed to, cannot sit beside the Browse window while you compare, and
under a screen reader's keyboard hook a ShowModal summoned from an accelerator
can silently fail to appear at all. So in the standalone apps -- wherever a
:class:`~quill.ui.window_menu.WindowManager` exists -- the player is now a
**modeless frame**, a peer of Browse and the managers:

* **Go to Player opens it, and if it is already open, brings it to the
  front.** One key, one place, always.
* It joins the shared &Window menu and the Ctrl+Tab / Ctrl+1..9 rotation like
  every other radio window.
* **Escape (or Close) closes it and returns you to the window you came
  from**, exactly as the other modeless surfaces do.

Embedded QUILL passes no window manager and keeps the modal summons unchanged.

Either shape, every button runs the same dispatcher the keys and the menus run
(:func:`quill.ui.radio.transport_keys.perform`), so this panel cannot drift
from them -- and a verb the thing playing cannot do refuses out loud here
exactly as it does everywhere else.

The buttons are laid out in the order somebody reaches for them, not in the
order the table happens to list them: the transport first, then position, then
speed, then chapters.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio import transport_commands as tc
from quill.ui.dialog_contract import announce_surface_exit, apply_modal_ids, bind_close_button

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
    # The two transport slots. Their labels here are only the *resting* ones:
    # both are re-read from ``transport_commands.primary_face`` /
    # ``pause_face`` on every refresh, which is why the ids look swapped. The
    # first slot is the Play/Stop button, so it is listed under STOP (the verb
    # it spends most of its life offering); the second is Pause/Resume, which
    # is PLAY_PAUSE in both of its states. See TRANSPORT_SLOTS below.
    (tc.STOP, "&Play"),
    (tc.PLAY_PAUSE, "Pau&se"),
    (tc.SKIP_BACK, "Skip &Back"),
    (tc.SKIP_FORWARD, "Skip &Forward"),
    (tc.ANNOUNCE_POSITION, "Where Am &I?"),
    (tc.PREVIOUS_CHAPTER, "Pre&vious Chapter"),
    (tc.NEXT_CHAPTER, "&Next Chapter"),
    (tc.CHAPTER_LIST, "&Chapters..."),
    (tc.SPEED_DOWN, "Slo&wer"),
    (tc.SPEED_UP, "Fas&ter"),
    (tc.SPEED_RESET, "Norma&l Speed"),
    # Skip Silence sits with the speed buttons because that is what it is for:
    # getting through the same hour faster (11.7). K, because S is Stop, F is
    # Skip Forward and every letter of "silence" that reads well was taken.
    (tc.SKIP_SILENCE, "S&kip Silence"),
    (tc.VOLUME_DOWN, "Volume &Down"),
    (tc.VOLUME_UP, "Vol&ume Up"),
    (tc.MUTE, "&Mute/Unmute"),
)

#: Commands that must never become buttons. Named rather than implied, so the
#: test that keeps this panel in step with the table can tell "deliberately
#: absent" from "added to the table and forgotten here".
NOT_BUTTONS: frozenset[str] = frozenset({tc.GO_TO_PLAYER, tc.COMMAND_PALETTE})

#: The two buttons whose label, accessible name, enabled state and *verb* are
#: resolved at refresh time rather than read from :data:`BUTTONS`.
#:
#: There used to be a Play/Pause button and a Stop button side by side, and on
#: live radio one of them was always wrong: a live stream cannot be paused, so
#: Play/Pause meant Play/Restart. Now the first button always starts and always
#: ends (Play, then Stop -- Alt+P either way) and the second owns pause, which
#: is the verb only a podcast, a recording or a local file has. On a live
#: station the second is present and dimmed and says why, rather than
#: disappearing: this grid is navigated by Tab, and a control that comes and
#: goes moves every control after it.
TRANSPORT_SLOTS: frozenset[str] = frozenset({tc.STOP, tc.PLAY_PAUSE})

#: What each transport slot is *for*, spoken by F1 and by the help text. Two
#: sentences rather than one because the pair is easy to confuse until somebody
#: has been told the difference: one ends playback, the other holds your place.
_TRANSPORT_HELP: dict[str, str] = {
    tc.STOP: (
        "Starts what is selected, and stops whatever is playing. The label says "
        "which: Play when nothing is on, Stop when something is."
    ),
    tc.PLAY_PAUSE: (
        "Holds a podcast, recording or local file where it is and picks it up "
        "there. Live radio cannot be paused -- it is going out now -- so this is "
        "dimmed on a station, and Stop is what ends one."
    ),
}


#: The modal panel currently on screen, if any.
#:
#: The transport keyboard is installed on this panel too, so a key does not stop
#: working merely because you are standing in the player -- which is the whole
#: claim :mod:`quill.ui.radio.transport_keys` makes, and the panel was the one
#: window where it was not true. That makes Go to Player pressable *from inside
#: the player*, and a second modal stacked over the first is a trap: closing one
#: leaves you in the other, having pressed nothing to get there.
_OPEN: PlayerPanel | None = None

#: The modeless player window currently open, if any. One per process, which is
#: one per app: the standalone apps each run in their own process, and embedded
#: QUILL (no WindowManager) never takes this path.
_OPEN_WINDOW: PlayerPanel | None = None


def _window_alive(panel: PlayerPanel | None) -> bool:
    """True when *panel*'s frame still exists (wx dead-object safe)."""
    if panel is None:
        return False
    try:
        return bool(panel.window)  # a destroyed wx window is falsy
    except Exception:  # noqa: BLE001 - a half-torn-down window counts as gone
        return False


def embed(host: Any, page: Any) -> Any:
    """Build the player *into* the main window's page (main_view).

    Not registered as ``_OPEN`` or ``_OPEN_WINDOW``: those track the player
    *window*, and this is not one. Go to Player while the player is the main
    view focuses it rather than summoning a second copy -- the check lives in
    the app's opener, which is the one place that knows what the main window is
    currently showing.
    """
    panel = PlayerPanel(None, host, windows=getattr(host, "_windows", None), embed_in=page)
    panel.show()
    return panel


def summon(host: Any, parent: Any = None) -> None:
    """Open the player over *parent* -- or raise the open player window.

    With a :class:`~quill.ui.window_menu.WindowManager` on *host* (the
    standalone apps), the player is a modeless frame: already open means come
    to the front, not a second copy. Without one (embedded QUILL), the player
    stays the modal panel that gives focus back when it closes.
    """
    import wx

    global _OPEN, _OPEN_WINDOW
    windows = getattr(host, "_windows", None)
    if windows is not None:
        if _window_alive(_OPEN_WINDOW):
            windows.activate(windows.key_for(_OPEN_WINDOW.window))
            return
        panel = PlayerPanel(None, host, windows=windows)
        _OPEN_WINDOW = panel
        panel.show()
        return
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


def refresh_open(host: Any = None) -> None:
    """Re-read whichever player is on screen, if any.

    The modeless window has no modal loop keeping it honest: playback can
    change from the main window, the Browse tree, or a media key while it sits
    open, so the app's own status refresh calls this to keep the readout (and
    the favorites label) telling the current truth. Cheap and dead-widget safe;
    a no-op when no player is open.
    """
    for panel in (_OPEN, _OPEN_WINDOW):
        if panel is not None and _window_alive(panel):
            panel._refresh()


class PlayerPanel:
    """The whole player on one small surface -- modal panel or modeless frame."""

    def __init__(
        self,
        parent: Any,
        host: Any,
        *,
        announce: Callable[[str], None] | None = None,
        windows: Any = None,
        embed_in: Any = None,
    ):
        import wx

        self._wx = wx
        self._host = host
        self._announce = announce or getattr(host, "_announce", None) or (lambda _m: None)
        # Modeless (a WindowManager was supplied): a top-level peer frame with
        # no parent, so it never floats glued over the window that opened it
        # and takes its own place in the Ctrl+Tab rotation. Modal: the summons.
        self._windows = windows
        #: Hosted in the main window, not a window at all: see main_view_host.
        self._embedded = embed_in is not None
        self._modeless = windows is not None and not self._embedded
        self._menu_ids: list[object] = []
        if self._embedded:
            self._surface = embed_in
            self._win = self._surface.GetTopLevelParent()
            self._surface.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        elif self._modeless:
            self._win = wx.Frame(None, title="Player", style=wx.DEFAULT_FRAME_STYLE)
            self._surface = wx.Panel(self._win, style=wx.TAB_TRAVERSAL)
            self._build_surface_menu_bar()
            self._win.Bind(wx.EVT_CLOSE, self._on_close)
            self._win.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        else:
            self._win = wx.Dialog(parent, title="Player")
            self._surface = self._win
        self.dialog = self._win  # back-compat alias: this was always .dialog
        root = wx.BoxSizer(wx.VERTICAL)

        # The readout first, and read-only: what is playing, where, how fast.
        # A panel that offers twelve verbs and never says what they act on is a
        # panel somebody has to guess at.
        # Sized in characters, not pixels. A fixed (420, 80) box is 420 pixels
        # at every font size, so the listener who has turned the system font up
        # -- the listener most likely to be reading this box rather than hearing
        # it -- is the one whose text clips.
        char_width, char_height = self._win.GetTextExtent("M")
        self._status = wx.TextCtrl(
            self._surface,
            value=self.status_text(),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            size=(char_width * 46, char_height * 4 + 8),
        )
        self._status.SetName("Now playing")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 10)

        grid = wx.GridSizer(0, 3, 6, 6)
        #: The two slots whose face is state, not text: {command id: button}.
        self._transport_buttons: dict[str, Any] = {}
        for command_id, label in BUTTONS:
            command = tc.command(command_id)
            button = wx.Button(self._surface, label=label)
            if command is not None:
                button.SetName(f"{label.replace('&', '')} ({command.key})")
            if command_id in TRANSPORT_SLOTS:
                self._transport_buttons[command_id] = button
            button.Bind(wx.EVT_BUTTON, lambda _e, cid=command_id: self._run(cid))
            grid.Add(button, 0, wx.EXPAND)
        root.Add(grid, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._refresh_transport_buttons()

        # Saving the station you are listening to belongs here as much as on the
        # Station menu: this panel is "everything about what is playing", and
        # that is the one fact the decision turns on. One handler, two doors --
        # the label flips exactly as the menu item's does.
        self._fav_btn = wx.Button(self._surface, label="Add to &Favorites")
        self._fav_btn.SetHelpText(
            "Saves the station that is playing right now to your favorites -- "
            "or removes it, when it is already there. The label says which."
        )
        self._fav_btn.Bind(wx.EVT_BUTTON, lambda _e: self._toggle_favorite())
        fav_row = wx.BoxSizer(wx.HORIZONTAL)
        fav_row.Add(self._fav_btn, 0)
        root.Add(fav_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._refresh_favorite_button()

        if not self._modeless:
            # Only the modal panel carries a Close button: a real window
            # closes with Alt+F4/Ctrl+F4, Ctrl+W, or Escape. A sizer with a
            # stretch spacer, not wx.ALIGN_RIGHT: the banned-pattern gate
            # rejects that alignment in quill/ui because of how it reports to
            # a screen reader (A11Y-4, the dialog contract).
            close_row = wx.BoxSizer(wx.HORIZONTAL)
            close_btn = wx.Button(self._surface, wx.ID_CANCEL, "Cl&ose")
            close_btn.SetHelpText(
                "Closes the player and puts focus back where you came from. "
                "Playback is not touched."
            )
            # ``modeless`` is spelled out because a frame answers ID_CANCEL
            # with nothing. (Left implicit once, and the required keyword made
            # every summon raise TypeError before the window ever showed --
            # the "player is not showing" report, 2026-08-23.)
            bind_close_button(self._win, close_btn, modeless=False)
            close_row.AddStretchSpacer()
            close_row.Add(close_btn)
            root.Add(close_row, 0, wx.EXPAND | wx.ALL, 10)

        if self._modeless:
            self._surface.SetSizer(root)
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(self._surface, 1, wx.EXPAND)
            self._win.SetSizerAndFit(outer)
        else:
            self._win.SetSizerAndFit(root)
            apply_modal_ids(self._win, cancel_id=wx.ID_CANCEL)

        # The transport keyboard, on the player itself. Without this the panel
        # was the one window in the app where the keys stopped working: a modal
        # dialog has no accelerator table of its own, so Ctrl+P did nothing here
        # while it did something in every window behind it. The keys and the
        # buttons run the same dispatcher and leave the same readout, because
        # ``after`` is the refresh the buttons already use.
        from quill.ui.radio import transport_keys

        transport_keys.install(
            self._win,
            host,
            wx=wx,
            after=self._refresh,
            extra_entries=self._windows.accelerator_entries() if self._modeless else (),
        )

    @property
    def window(self) -> Any:
        """The top-level wx window (frame or dialog) this panel lives on."""
        return self._win

    # -- modeless lifecycle ------------------------------------------------------

    def _build_surface_menu_bar(self) -> None:
        """Menu bar for the modeless frame: &Close + the shared &Window menu,
        so Alt lands on a real menu and Ctrl+Tab / Ctrl+1..9 reach every open
        window from here too."""
        wx = self._wx
        menu_bar = wx.MenuBar()
        player_menu = wx.Menu()
        close_id = wx.NewIdRef()
        player_menu.Append(close_id, "&Close\tCtrl+W")
        self._win.Bind(wx.EVT_MENU, lambda _e: self._win.Close(), id=close_id)
        menu_bar.Append(player_menu, "&Player")
        self._windows.install(self._win, menu_bar)
        self._win.SetMenuBar(menu_bar)
        self._menu_ids.append(close_id)

    def _on_char_hook(self, event: Any) -> None:
        # A frame has no automatic Escape->Cancel; wire it to close, keeping
        # the "visit" contract the modal shape established. Ctrl+F4 closes
        # like any document window (Alt+F4 already works natively).
        if event.GetKeyCode() == self._wx.WXK_ESCAPE or (
            event.GetKeyCode() == self._wx.WXK_F4 and event.ControlDown()
        ):
            self._win.Close()
            return
        event.Skip()

    def _on_close(self, event: Any) -> None:
        global _OPEN_WINDOW
        previous = self._windows.previous_key(self._win)
        self._windows.unregister(self._win)
        if _OPEN_WINDOW is self:
            _OPEN_WINDOW = None
        announce_surface_exit("Player", self._announce)
        event.Skip()
        self._win.Destroy()
        if previous:
            self._windows.activate(previous)

    # -- shared behaviour --------------------------------------------------------

    def _toggle_favorite(self) -> None:
        """Run the host's one favorites handler, then re-read the label."""
        toggle = getattr(self._host, "_on_favorite_toggle", None)
        if callable(toggle):
            toggle()
        self._refresh_favorite_button()

    def _refresh_favorite_button(self) -> None:
        """Say what pressing it would do, and refuse when there is nothing on."""
        button = getattr(self, "_fav_btn", None)
        if button is None:
            return
        station = None
        controller = getattr(self._host, "_radio_controller", None)
        if controller is not None:
            station = getattr(getattr(controller, "state", None), "station", None)
        favorites = getattr(self._host, "_radio_favorites", None)
        saved = bool(station is not None and favorites is not None and favorites.contains(station))
        label = "Remove from &Favorites" if saved else "Add to &Favorites"
        if button.GetLabel() != label:
            button.SetLabel(label)
        button.SetName(
            "Remove the playing station from favorites"
            if saved
            else "Add the playing station to favorites"
        )
        button.Enable(station is not None)

    def status_text(self) -> str:
        """What is playing, where you are in it, and how fast. Never raises.

        The reading itself belongs to :mod:`quill.ui.radio.transport_keys`: this
        panel is summoned from Quill Cast as well as Quill Radio, and only the
        dispatcher knows both players' shapes. Written here first, it knew one --
        so Cast's panel said "Playing." and nothing else.
        """
        from quill.ui.radio import transport_keys

        return transport_keys.describe_now_playing(self._host)

    def _transport_face(self, command_id: str) -> Any:
        """What one of the two transport slots should read and run right now."""
        from quill.ui.radio import transport_face

        primary, pause = transport_face.faces(self._host)
        return primary if command_id == tc.STOP else pause

    def _refresh_transport_buttons(self) -> None:
        """Put the current truth on Play/Stop and Pause/Resume. Never raises.

        The accessible name carries the key as well as the label, because these
        two are the only buttons here whose *verb* changes underneath the
        listener -- the name has to say Stop (Ctrl+.) rather than keep
        advertising Ctrl+P after the label flipped.
        """
        for command_id, button in getattr(self, "_transport_buttons", {}).items():
            try:
                face = self._transport_face(command_id)
                if button.GetLabel() != face.label:
                    button.SetLabel(face.label)
                button.SetName(f"{face.plain} ({face.key})")
                button.Enable(face.enabled)
                button.SetHelpText(
                    _TRANSPORT_HELP[command_id]
                    if face.enabled
                    else f"Not available: {face.reason}."
                )
            except Exception:  # noqa: BLE001 - the window may be closing
                return

    def _refresh(self) -> None:
        """Re-read the status line, and only write it when it actually changed.

        ``SetValue`` moves the insertion point back to the start, so rewriting
        an identical string would disturb somebody who had tabbed into the
        readout to review it. A refused verb changes nothing, and now costs
        nothing.
        """
        # Every transport key runs through here, so the favorites label follows
        # a station change made from the panel as well as one made outside it.
        try:
            self._refresh_favorite_button()
            self._refresh_transport_buttons()
            fresh = self.status_text()
            if fresh != self._status.GetValue():
                self._status.SetValue(fresh)
        except Exception:  # noqa: BLE001 - the window may be closing
            return

    def _run(self, command_id: str) -> None:
        """Run a verb, then re-read the panel so it tells the new truth.

        The two transport slots run the verb their *current face* names, not
        the id they are listed under: the button reading Stop must call stop
        even though :data:`BUTTONS` files it under nothing of the sort.
        """
        from quill.ui.radio import transport_keys

        if command_id in TRANSPORT_SLOTS:
            command_id = self._transport_face(command_id).command_id
        transport_keys.perform(self._host, command_id)
        self._refresh()

    def focus_default_control(self) -> None:
        """Keyboard focus where this surface expects it: the readout."""
        for name in ("_readout", "_status_text", "_surface"):
            control = getattr(self, name, None)
            if control is None:
                continue
            try:
                control.SetFocus()
            except Exception:  # noqa: BLE001 - focus is best-effort
                continue
            return

    def show(self) -> int:
        if self._embedded:
            return 0
        if self._modeless:
            from quill.ui.dialog_contract import show_modeless_surface

            self._windows.register(self._win, "Player")
            show_modeless_surface(self._win, "Player", announce=self._announce)
            return 0
        from quill.ui.dialog_contract import show_modal_dialog

        self._win.CentreOnParent()
        try:
            return int(show_modal_dialog(self._win, "Player", announce=self._announce))
        finally:
            self._win.Destroy()
