"""A small, accessible view of the current "What's Playing" text (#1134).

Shows the now-playing title/artist in a read-only, selectable field a screen
reader can review character by character, with a Copy button -- so a listener
can note the exact spelling of a song or artist, or paste it into a lyrics or
store search. The live What's Playing announcement (which just speaks) is
unchanged; this is an on-demand, reviewable companion.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids


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
    ) -> None:
        import wx

        self._wx = wx
        self._transport_host = transport_host
        self._text = text
        self._show_modal = show_modal_dialog
        self._copy = copy_to_clipboard
        self._announce = announce
        self._title = title

        self.dialog = wx.Dialog(
            parent,
            title=self._title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(480, 240))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        # Read-only but selectable: a screen reader can arrow through it
        # character by character, and the user can select-and-copy from it.
        self._field = wx.TextCtrl(
            self.dialog,
            value=self._text,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self._field.SetName("Now playing")
        root.Add(self._field, 1, wx.EXPAND | wx.ALL, 8)

        char_label = wx.StaticText(self.dialog, label=f"{len(self._text):,} characters")
        root.Add(char_label, 0, wx.LEFT | wx.BOTTOM, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._copy_btn = wx.Button(self.dialog, label="&Copy")
        close_btn = wx.Button(self.dialog, wx.ID_CLOSE, label="C&lose")
        apply_modal_ids(
            self.dialog,
            affirmative_id=close_btn.GetId(),
            escape_id=close_btn.GetId(),
        )
        # The transport keyboard, when the surface that opened this one knows
        # about the player. It was installed in the browse tree and nowhere
        # else, so every other Radio dialog was a window where the keys that
        # work everywhere stopped working.
        if self._transport_host is not None:
            from quill.ui.radio import transport_keys

            transport_keys.install(self.dialog, self._transport_host, wx=wx)

        self._copy_btn.Enable(bool(self._text))
        for b in (self._copy_btn, close_btn):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        root.Add(btn_row, 0, wx.ALL, 8)

        self.dialog.SetSizer(root)
        self._copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        wx.CallAfter(self._field.SetFocus)

    def _on_copy(self, _event: object) -> None:
        if self._copy(self._text) and self._announce:
            self._announce("Copied.")

    def show(self) -> int:
        result = self._show_modal(self.dialog, self._title)
        self.dialog.Destroy()
        return result
