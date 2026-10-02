"""Every link in what you are reading, as a list you can act on.

Show notes and transcripts are full of addresses -- the paper being discussed,
the sponsor, the guest's site -- and in a read-only text box the only way to
follow one was to read it out character by character and retype it into a
browser. That is the least accessible possible way to follow a link, and it is
what QUILL was offering (reported 2026-08-18).

So: one list, and the verbs on it. Deliberately shared -- the transcript reader,
the show-notes viewer and the Notes reader (qc.md 5c) all have the same problem,
and a second, subtly different list of links is exactly the drift the shared cue
parser and the shared transcript window exist to prevent.

**Grown for the Notes reader (qc.md 5c, 2026-10-02).** Jeff: "a show links button
should also be visible so that you can get a list of links to arrow through with
titles and you can copy to the clipboard, view in browser or close." So:

* **Each row reads title, then where it goes** -- "Support the show on Patreon,
  patreon.com/thedaily" -- so the title is what you arrow through and the address
  is there at the end of the row when you want it. The same address twice is one
  row (:func:`quill.core.text_links._dedupe`, first title wins).
* **Four buttons and the same four on the row's context menu**: Open in Browser
  (Enter on a row), Copy Address, Copy All Addresses, and -- one row deeper, on the
  context menu only -- Copy Title and Address.
* **Close (Escape) goes back to the link you were on**: :attr:`chosen` is the row
  that was selected when the window closed, so the reader behind it can put the
  caret there.

**A ``wx.ListBox``, not a grid.** Each row is one thing with one address; arrow
keys, first-letter navigation and the screen reader's own list reporting ("3 of
17") all come free and behave the way they behave everywhere else.

**Opening leaves the app.** It goes to the system browser, exactly as
``core/browser_reader.py`` prefers -- QUILL has no accessible embedded web view
and will not pretend otherwise.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from quill.core.text_links import Link, describe
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button


class LinkListDialog:
    """A list of links, with Open, Copy, Copy All and a context menu."""

    def __init__(
        self,
        parent: object,
        *,
        links: Sequence[Link],
        title: str = "Links",
        announce_cb: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[object, str], int] | None = None,
        select_url: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self._links = list(links)
        self._announce = announce_cb or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog
        #: The link selected when the window closed -- where Close goes back to.
        self.chosen: Link | None = None

        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((640, 400))
        root = wx.BoxSizer(wx.VERTICAL)

        heading = describe(self._links)
        root.Add(wx.StaticText(self.dialog, label=f"&Links -- {heading}"), 0, wx.LEFT | wx.TOP, 10)

        self._list = wx.ListBox(self.dialog, choices=[link.row for link in self._links])
        self._list.SetName("Links. Enter opens one in your browser")
        self._list.SetHelpText(
            "Every link, in the order it appears, each read as its title and then "
            "where it goes. Enter opens the selected link in your browser; the "
            "Applications key also offers Copy Title and Address."
        )
        if self._links:
            self._list.SetSelection(self._index_of(select_url))
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._open_btn = wx.Button(self.dialog, label="&Open in Browser")
        self._open_btn.SetHelpText("Opens the selected link in your web browser.")
        self._copy_btn = wx.Button(self.dialog, label="&Copy Address")
        self._copy_btn.SetHelpText("Puts the selected link's address on the clipboard.")
        self._copy_both_btn = wx.Button(self.dialog, label="Copy &Title and Address")
        self._copy_both_btn.SetHelpText(
            "Puts the selected link's title and address on the clipboard."
        )
        self._copy_all_btn = wx.Button(self.dialog, label="Copy &All Addresses")
        self._copy_all_btn.SetHelpText(
            "Puts every address on the clipboard, one per line, for pasting into a note."
        )
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetHelpText("Closes the list and returns you to the link you were on.")
        # modeless=False: this is a modal dialog. The keyword is required, and
        # without it the window raised TypeError before it ever appeared -- every
        # Links... button in Show Notes and the transcript reader did nothing
        # (found 2026-10-02 building the Notes reader).
        bind_close_button(self.dialog, close_btn, modeless=False)
        for button in (
            self._open_btn,
            self._copy_btn,
            self._copy_both_btn,
            self._copy_all_btn,
        ):
            button.Enable(bool(self._links))
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, cancel_id=wx.ID_CANCEL)

        self._list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self.open_selected())
        self._list.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._list.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self.show_context_menu())
        self._open_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_selected())
        self._copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self.copy_selected())
        self._copy_both_btn.Bind(wx.EVT_BUTTON, lambda _e: self.copy_title_and_address())
        self._copy_all_btn.Bind(wx.EVT_BUTTON, lambda _e: self.copy_all())

    def _index_of(self, url: str) -> int:
        wanted = (url or "").rstrip("/").lower()
        for index, link in enumerate(self._links):
            if wanted and link.url.rstrip("/").lower() == wanted:
                return index
        return 0

    def show(self) -> int:
        self.dialog.CentreOnParent()
        self._list.SetFocus()
        title = self.dialog.GetTitle()
        try:
            if self._show_modal_dialog is not None:
                return int(self._show_modal_dialog(self.dialog, title))
            return int(self.dialog.ShowModal())  # dialog_button_contract: exempt
        finally:
            self.chosen = self.selected()
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

    #: The context menu's rows: ``(label, method)``. The four the buttons have,
    #: with Copy Title and Address one row deeper than the button row goes. No
    #: access keys: a popup inherits the window's, and duplicates are worse than
    #: none (GATE-14).
    MENU_ROWS: tuple[tuple[str, str], ...] = (
        ("Open in Browser", "open_selected"),
        ("Copy Address", "copy_selected"),
        ("Copy Title and Address", "copy_title_and_address"),
        ("Copy All Addresses", "copy_all"),
    )

    def show_context_menu(self) -> None:
        """The row's verbs, from the Applications key, Shift+F10 or a right-click."""
        wx = self._wx
        if not self._links:
            return
        menu = wx.Menu()
        for label, method in self.MENU_ROWS:
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            menu.Bind(wx.EVT_MENU, lambda _e, m=method: getattr(self, m)(), id=item_id)
        try:
            self._list.PopupMenu(menu)
        finally:
            menu.Destroy()

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
        self._announce("Opened in your browser.")
        return True

    def copy_selected(self) -> str:
        """Put the highlighted address on the clipboard."""
        link = self.selected()
        if link is None:
            self._announce("Choose a link first.")
            return ""
        return self._to_clipboard(link.url, f"Copied {link.url}.")

    def copy_selected_with_title(self) -> str:
        """Compatibility name for the title-and-address copy action."""
        return self.copy_title_and_address()

    def copy_title_and_address(self) -> str:
        """The title, then the address on the next line -- for a message."""
        link = self.selected()
        if link is None:
            self._announce("Choose a link first.")
            return ""
        title = " ".join(link.text.split())
        text = f"{title}\n{link.url}" if title and title != link.url else link.url
        return self._to_clipboard(text, "Copied the title and address.")

    def copy_all(self) -> str:
        """Every address, one per line -- for pasting into notes."""
        if not self._links:
            return ""
        text = "\n".join(link.url for link in self._links)
        count = len(self._links)
        return self._to_clipboard(text, f"Copied {count} address{'' if count == 1 else 'es'}.")

    def _to_clipboard(self, text: str, spoken: str) -> str:
        wx = self._wx
        try:
            if not wx.TheClipboard.Open():
                self._announce("That could not be copied.")
                return ""
            try:
                if not wx.TheClipboard.SetData(wx.TextDataObject(text)):
                    self._announce("That could not be copied.")
                    return ""
            finally:
                wx.TheClipboard.Close()
        except Exception:  # noqa: BLE001 - a clipboard is never worth an exception
            self._announce("That could not be copied.")
            return ""
        self._announce(spoken)
        return text
