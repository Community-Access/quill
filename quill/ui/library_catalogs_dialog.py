"""**Catalogs...** -- adding a library QUILL has never heard of.

The payoff for building the ebook half on OPDS rather than on one adapter per
provider: a catalogue is a name and a URL, so a personal Calibre library, a
school's repository or a nonprofit accessible-book collection becomes searchable
without waiting for a QUILL release.

Two things this window is careful about:

* **It says when a catalogue is not encrypted.** A library on a home network is
  usually plain HTTP, and refusing those would rule out the case this feature
  mostly exists for -- so they are allowed, and the row says so out loud rather
  than letting somebody assume otherwise.
* **Removing a built-in switches it off instead**, and says that is what it did.
  Deleting it would only bring it back on the next launch, because the built-ins
  are code rather than data, and a control whose effect silently reverts is
  worse than one that explains itself.

A plain single-select ``wx.ListBox`` with explicit buttons -- the same shape as
the Library window it is opened from.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.library import catalogs as catalogs_module
from quill.ui.dialog_contract import apply_modal_ids

TITLE = "Book Catalogs"


class LibraryCatalogsDialog:
    """Add, switch off, or remove an OPDS catalogue."""

    def __init__(
        self,
        parent: Any,
        *,
        data_dir: Path | str,
        announce: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
        ask: Callable[[str, str], str] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._data_dir = Path(data_dir)
        self._announce = announce or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog
        self._ask = ask
        self._catalogs = catalogs_module.load(self._data_dir)

        self._dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self._dialog,
                label=(
                    "Catalogs QUILL searches for ebooks. Any library that publishes "
                    "an OPDS feed can be added, including one on your own computer."
                ),
            ),
            0,
            wx.ALL,
            10,
        )
        root.Add(wx.StaticText(self._dialog, label="&Catalogs:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._list = wx.ListBox(self._dialog, style=wx.LB_SINGLE)
        self._list.SetName("Book catalogs QUILL searches")
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._add_btn = wx.Button(self._dialog, label="&Add Catalog...")
        self._toggle_btn = wx.Button(self._dialog, label="&Switch Off")
        self._remove_btn = wx.Button(self._dialog, label="&Remove")
        buttons.Add(self._add_btn, 0, wx.RIGHT, 6)
        buttons.Add(self._toggle_btn, 0, wx.RIGHT, 6)
        buttons.Add(self._remove_btn, 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(self._dialog, wx.ID_CANCEL, "Cl&ose"), 0)
        root.Add(buttons, 0, wx.ALL, 10)

        self._dialog.SetSizer(root)
        self._dialog.SetMinSize((560, 380))
        self._dialog.Fit()
        apply_modal_ids(self._dialog, cancel_id=wx.ID_CANCEL, cancel_label="Close")

        self._add_btn.Bind(wx.EVT_BUTTON, lambda _e: self.add_catalog())
        self._toggle_btn.Bind(wx.EVT_BUTTON, lambda _e: self.toggle_selected())
        self._remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self.remove_selected())
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._sync_buttons())
        self._refresh()
        self._list.SetFocus()

    @property
    def dialog(self) -> Any:
        return self._dialog

    @property
    def catalogs(self) -> list[catalogs_module.Catalog]:
        return self._catalogs

    def _refresh(self) -> None:
        selection = max(0, self._list.GetSelection())
        self._list.Set([catalog.display for catalog in self._catalogs])
        if self._catalogs:
            self._list.SetSelection(min(selection, len(self._catalogs) - 1))
        self._sync_buttons()

    def _selected(self) -> catalogs_module.Catalog | None:
        index = self._list.GetSelection()
        if index < 0 or index >= len(self._catalogs):
            return None
        return self._catalogs[index]

    def _sync_buttons(self) -> None:
        """Name the toggle after what it will do to *this* catalogue."""
        catalog = self._selected()
        self._toggle_btn.Enable(catalog is not None)
        self._remove_btn.Enable(catalog is not None)
        if catalog is not None:
            self._toggle_btn.SetLabel("&Switch On" if not catalog.enabled else "&Switch Off")

    def add_catalog(self) -> bool:
        """Ask for a name and an address, and add it."""
        wx = self._wx
        ask = self._ask or self._prompt
        name = ask("What is this catalog called?", "Add Catalog")
        if not name:
            return False
        url = ask("Address of the OPDS catalog (starts with https:// or http://):", "Add Catalog")
        if not url:
            return False
        if not catalogs_module.is_supported_url(url):
            self._announce(
                "That is not an address QUILL can use. An OPDS catalog address "
                "starts with https:// or http://."
            )
            return False
        added = catalogs_module.add(self._catalogs, name=name, url=url)
        if added is None:
            self._announce("That catalog is already in the list.")
            return False
        catalogs_module.save(self._data_dir, self._catalogs)
        self._refresh()
        if not added.is_encrypted:
            self._announce(
                f"Added {added.name}. This one is not an encrypted connection, "
                "so treat what you read from it the way you would any plain web page."
            )
        else:
            self._announce(f"Added {added.name}.")
        _ = wx
        return True

    def _prompt(self, message: str, title: str) -> str:
        wx = self._wx
        with wx.TextEntryDialog(  # dialog_button_contract: exempt
            self._dialog, message, title
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return ""
            return str(dialog.GetValue()).strip()

    def toggle_selected(self) -> bool:
        catalog = self._selected()
        if catalog is None:
            return False
        catalog.enabled = not catalog.enabled
        catalogs_module.save(self._data_dir, self._catalogs)
        self._refresh()
        self._announce(
            f"{catalog.name} will be searched."
            if catalog.enabled
            else f"{catalog.name} will not be searched."
        )
        return True

    def remove_selected(self) -> bool:
        """Remove one that was added; switch off a built-in, and say so."""
        catalog = self._selected()
        if catalog is None:
            return False
        removed = catalogs_module.remove(self._catalogs, catalog.id)
        catalogs_module.save(self._data_dir, self._catalogs)
        self._refresh()
        if removed:
            self._announce(f"Removed {catalog.name}.")
        else:
            self._announce(
                f"{catalog.name} comes with QUILL, so it was switched off rather "
                "than removed. It can be switched back on here at any time."
            )
        return True

    def show(self) -> int:
        """Show the window, and always destroy it afterwards (A11Y-4)."""
        try:
            if self._show_modal_dialog is not None:
                return int(self._show_modal_dialog(self._dialog, TITLE))
            return int(self._dialog.ShowModal())  # dialog_button_contract: exempt
        finally:
            self._dialog.Destroy()
