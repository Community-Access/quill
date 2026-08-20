"""Every link in what you are reading, as a list you can act on.

Show notes and transcripts are full of addresses -- the paper being discussed,
the sponsor, the guest's site -- and in a read-only text box the only way to
follow one was to read it out character by character and retype it into a
browser. That is the least accessible possible way to follow a link, and it is
what QUILL was offering (reported 2026-08-18).

So: one list, two verbs. Open it in the real browser, or copy it to the
clipboard. Deliberately small, and deliberately shared -- the transcript reader
and the show-notes viewer both have the same problem, and a second, subtly
different list of links is exactly the drift the shared cue parser and the
shared transcript window exist to prevent.

**A ``wx.ListBox``, not a grid.** Each row is one thing with one address; arrow
keys, first-letter navigation and the screen reader's own list reporting ("3 of
17") all come free and behave the way they behave everywhere else.

**The row says the name and the address.** The name alone hides where a link
goes, which is the one fact somebody deciding whether to open it needs; the
address alone is a string nobody can skim. See
:attr:`quill.core.text_links.Link.label`.

**Opening leaves the app.** It goes to the system browser, exactly as
``core/browser_reader.py`` prefers -- QUILL has no accessible embedded web view
and will not pretend otherwise.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from quill.core.text_links import Link, describe
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button


class LinkListDialog:
    """A list of links, with Open and Copy."""

    def __init__(
        self,
        parent: object,
        *,
        links: Sequence[Link],
        title: str = "Links",
        announce_cb: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[object, str], int] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._links = list(links)
        self._announce = announce_cb or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog

        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((640, 400))
        root = wx.BoxSizer(wx.VERTICAL)

        heading = describe(self._links)
        root.Add(wx.StaticText(self.dialog, label=f"&Links -- {heading}"), 0, wx.LEFT | wx.TOP, 10)

        self._list = wx.ListBox(self.dialog, choices=[link.label for link in self._links])
        self._list.SetName("Links. Enter opens one in your browser")
        if self._links:
            self._list.SetSelection(0)
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._open_btn = wx.Button(self.dialog, label="&Open in Browser")
        self._copy_btn = wx.Button(self.dialog, label="&Copy Address")
        self._copy_all_btn = wx.Button(self.dialog, label="Copy &All")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cl&ose")
        bind_close_button(self.dialog, close_btn)
        for button in (self._open_btn, self._copy_btn, self._copy_all_btn):
            button.Enable(bool(self._links))
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, cancel_id=wx.ID_CANCEL)

        self._list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self.open_selected())
        self._list.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._open_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_selected())
        self._copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self.copy_selected())
        self._copy_all_btn.Bind(wx.EVT_BUTTON, lambda _e: self.copy_all())

    def show(self) -> int:
        self.dialog.CentreOnParent()
        self._list.SetFocus()
        title = self.dialog.GetTitle()
        try:
            if self._show_modal_dialog is not None:
                return int(self._show_modal_dialog(self.dialog, title))
            return int(self.dialog.ShowModal())  # dialog_button_contract: exempt
        finally:
            self.dialog.Destroy()

    def _on_char_hook(self, event: object) -> None:
        wx = self._wx
        key = event.GetKeyCode()  # type: ignore[attr-defined]
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.open_selected()
            return
        if key == ord("C") and event.ControlDown():  # type: ignore[attr-defined]
            self.copy_selected()
            return
        event.Skip()  # type: ignore[attr-defined]

    def selected(self) -> Link | None:
        index = self._list.GetSelection()
        if index < 0 or index >= len(self._links):
            return None
        return self._links[index]

    def open_selected(self) -> bool:
        """Open the highlighted link in the system browser."""
        link = self.selected()
        if link is None:
            self._announce("Choose a link first.")
            return False
        import webbrowser

        try:
            webbrowser.open(link.url)
        except Exception:  # noqa: BLE001 - a browser that will not start is an answer
            self._announce("That link could not be opened.")
            return False
        self._announce(f"Opened {link.url} in your browser.")
        return True

    def copy_selected(self) -> str:
        """Put the highlighted address on the clipboard."""
        link = self.selected()
        if link is None:
            self._announce("Choose a link first.")
            return ""
        return self._to_clipboard(link.url, f"Copied {link.url}.")

    def copy_all(self) -> str:
        """Every address, one per line -- for pasting into notes."""
        if not self._links:
            return ""
        text = "\n".join(link.url for link in self._links)
        return self._to_clipboard(text, f"Copied {len(self._links)} addresses.")

    def _to_clipboard(self, text: str, spoken: str) -> str:
        wx = self._wx
        try:
            if wx.TheClipboard.Open():
                try:
                    wx.TheClipboard.SetData(wx.TextDataObject(text))
                finally:
                    wx.TheClipboard.Close()
        except Exception:  # noqa: BLE001 - a clipboard is never worth an exception
            self._announce("That could not be copied.")
            return ""
        self._announce(spoken)
        return text
