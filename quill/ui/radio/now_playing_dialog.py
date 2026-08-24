"""A small, accessible view of the current "What's Playing" text (#1134).

Shows the now-playing title/artist in a read-only, selectable field a screen
reader can review character by character, with a Copy button -- so a listener
can note the exact spelling of a song or artist, or paste it into a lyrics or
store search. The live What's Playing announcement (which just speaks) is
unchanged; this is an on-demand, reviewable companion.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import announce_surface_exit, apply_modal_ids

#: The one open modeless viewer, if any. This window is a snapshot -- of a
#: track, a station's details, or the full now-playing state -- so opening a
#: new one *replaces* the old rather than raising it: raising would present
#: stale text under a fresh gesture, and stacking copies is clutter. One
#: per process, which is one per standalone app.
_OPEN: NowPlayingDialog | None = None


class NowPlayingDialog:
    """Read-only, copyable view of the current now-playing text.

    Parameters
    ----------
    parent:
        wx parent window (the main frame).
    text:
        The clean now-playing text (e.g. "YOUR SONG by Elton John").
    show_modal_dialog:
        MainFrame's ``_show_modal_dialog`` gate (names the modal region and
        manages focus for screen readers).
    copy_to_clipboard:
        MainFrame's ``_copy_to_clipboard`` (returns True on success).
    announce:
        Optional spoken-announcement callback for the Copy result.
    """

    def __init__(
        self,
        parent: object,
        text: str,
        show_modal_dialog: Callable,
        copy_to_clipboard: Callable[[str], bool],
        announce: Callable[[str], None] | None = None,
        *,
        title: str = "Now Playing",
        transport_host: object | None = None,
        windows: object | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._transport_host = transport_host
        self._text = text
        self._show_modal = show_modal_dialog
        self._copy = copy_to_clipboard
        self._announce = announce
        self._title = title
        self._windows = windows
        self._modeless = windows is not None
        self._menu_id_refs: list[object] = []

        # Modeless parentless wx.Frame (a peer window in the taskbar, the
        # &Window menu and Ctrl+Tab) when standalone Radio supplies a
        # WindowManager; an unchanged modal wx.Dialog for embedded QUILL.
        if self._modeless:
            self._win = wx.Frame(None, title=self._title, style=wx.DEFAULT_FRAME_STYLE)
            self._surface = wx.Panel(self._win, style=wx.TAB_TRAVERSAL)
            self._build_surface_menu_bar()
            self._win.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
            self._win.Bind(wx.EVT_CLOSE, self._on_close)
        else:
            self._win = wx.Dialog(
                parent,
                title=self._title,
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._surface = self._win
        self.dialog = self._win  # back-compat alias for callers that reference it
        self._win.SetSize(wx.Size(480, 240))
        self._build_ui()

    def _build_surface_menu_bar(self) -> None:
        """Menu bar for the modeless frame: &Close + the shared &Window menu."""
        wx = self._wx
        menu_bar = wx.MenuBar()
        surface_menu = wx.Menu()
        close_id = wx.NewIdRef()
        surface_menu.Append(close_id, "&Close\tCtrl+W")
        self._win.Bind(wx.EVT_MENU, lambda _e: self._win.Close(), id=close_id)
        menu_bar.Append(surface_menu, "&View")
        self._windows.install(self._win, menu_bar)
        self._win.SetMenuBar(menu_bar)
        self._menu_id_refs.append(close_id)

    def _on_char_hook(self, event: object) -> None:
        # A frame has no automatic Escape->Cancel; wire it (and Ctrl+F4, the
        # document-window close key) to close, like every peer window.
        wx = self._wx
        if event.GetKeyCode() == wx.WXK_ESCAPE or (
            event.GetKeyCode() == wx.WXK_F4 and event.ControlDown()
        ):
            self._win.Close()
            return
        event.Skip()

    def _on_close(self, event: object) -> None:
        global _OPEN
        if _OPEN is self:
            _OPEN = None
        previous = self._windows.previous_key(self._win)
        self._windows.unregister(self._win)
        if self._announce:
            announce_surface_exit(self._title, self._announce)
        event.Skip()
        self._win.Destroy()
        if previous:
            self._windows.activate(previous)

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        # Read-only but selectable: a screen reader can arrow through it
        # character by character, and the user can select-and-copy from it.
        self._field = wx.TextCtrl(
            self._surface,
            value=self._text,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self._field.SetName("Now playing")
        root.Add(self._field, 1, wx.EXPAND | wx.ALL, 8)

        char_label = wx.StaticText(self._surface, label=f"{len(self._text):,} characters")
        root.Add(char_label, 0, wx.LEFT | wx.BOTTOM, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._copy_btn = wx.Button(self._surface, label="&Copy")
        self._copy_btn.SetHelpText(
            "Copies the whole text to the clipboard -- the exact spelling, "
            "ready for a search or a note."
        )
        btn_row.Add(self._copy_btn, 0, wx.RIGHT, 6)
        if not self._modeless:
            # Only the modal dialog carries a Close button: a real window
            # closes with Alt+F4/Ctrl+F4, Ctrl+W, or Escape (2026-08-23).
            close_btn = wx.Button(self._surface, wx.ID_CLOSE, label="C&lose")
            close_btn.SetHelpText("Closes this snapshot; open it again any time for fresh facts.")
            btn_row.Add(close_btn, 0, wx.RIGHT, 6)
            apply_modal_ids(
                self._win,
                affirmative_id=close_btn.GetId(),
                escape_id=close_btn.GetId(),
            )
            close_btn.Bind(wx.EVT_BUTTON, lambda _e: self._win.EndModal(wx.ID_CLOSE))
        # The transport keyboard, when the surface that opened this one knows
        # about the player. It was installed in the browse tree and nowhere
        # else, so every other Radio dialog was a window where the keys that
        # work everywhere stopped working. The WindowManager's Ctrl+Tab /
        # Ctrl+1..9 rows ride in the same table when this is a peer window.
        if self._transport_host is not None:
            from quill.ui.radio import transport_keys

            transport_keys.install(
                self._win,
                self._transport_host,
                wx=wx,
                extra_entries=self._windows.accelerator_entries() if self._modeless else (),
            )

        self._copy_btn.Enable(bool(self._text))
        root.Add(btn_row, 0, wx.ALL, 8)

        self._surface.SetSizer(root)
        if self._modeless:
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(self._surface, 1, wx.EXPAND)
            self._win.SetSizer(outer)
        self._copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        wx.CallAfter(self._field.SetFocus)

    def _on_copy(self, _event: object) -> None:
        if self._copy(self._text) and self._announce:
            self._announce("Copied.")

    def show(self) -> int:
        if self._modeless:
            from quill.ui.dialog_contract import show_modeless_surface

            global _OPEN
            old = _OPEN
            if old is not None and old is not self:
                # A fresh snapshot replaces the stale one -- see _OPEN above.
                # Torn down directly (unregister + Destroy) rather than via
                # Close(): the close handler would announce an exit and raise
                # the previous window mid-way through opening this one.
                try:
                    old._windows.unregister(old._win)
                    old._win.Destroy()
                except Exception:  # noqa: BLE001 - a half-dead window must not block the new one
                    pass
            _OPEN = self
            self._windows.register(self._win, self._title)
            show_modeless_surface(self._win, self._title, announce=self._announce)
            return 0
        result = self._show_modal(self._win, self._title)
        self._win.Destroy()
        return result
