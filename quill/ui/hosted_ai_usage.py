"""AI Usage: one read-only list for every connection (codex.md 10A.11).

Replaces the three usage windows there were -- the free AI's allowance, the own
key's model and bill, and the ChatGPT account window's usage row -- with one,
opened by the same Usage command and keys as before (QUILL Ctrl+Alt+Shift+F2,
QUILL Lite Ctrl+Alt+Shift+F9).

**Everything is text (decision 13).** One row a connection that is set up,
each a sentence saying whose number it is: a service's count is named as the
service's, a count kept on this computer is called a local count, and money is
never worked out from anything. No meter, gauge or progress bar carries a
number here or anywhere else.

**One button.** Manage Usage opens the selected connection's own page. The rows
are :meth:`AiService.usage_rows`; this window composes none of them.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_listbox_activation
from quill.ui.dpi import dip_size
from quill.ui.hosted_ai_dialogs import _PAD, _close_row, focus_on

__all__ = ["TITLE", "UsageFrame"]

TITLE = "AI Usage"


class UsageFrame(wx.Frame):
    """The rows, and Manage Usage."""

    def __init__(
        self,
        parent: Any,
        service: Any,
        announce: Callable[[str], None],
        *,
        fetch_free: bool = False,
    ) -> None:
        super().__init__(parent, title=TITLE)
        self._service = service
        self._announce = announce
        self._rows: list[Any] = []

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)
        label = wx.StaticText(panel, label="&Usage by connection")
        self._list = wx.ListBox(panel, style=wx.LB_SINGLE)
        set_accessible_name(self._list, "Usage by connection")
        self._list.SetHelpText(
            "One sentence for each connection that is set up: how much has been used "
            "and whose count it is. A count kept on this computer is called a local "
            "count; a service's own number is named as the service's."
        )
        apply_listbox_activation(self._list, lambda _e: self.manage())
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, _PAD)

        manage = wx.Button(panel, label="&Manage Usage")
        manage.SetHelpText(
            "Opens the selected connection's own usage or billing page in your web "
            "browser, where its limits and bill are kept."
        )
        manage.Bind(wx.EVT_BUTTON, lambda _e: self.manage())
        _close_row(self, sizer, manage)

        self.SetInitialSize(dip_size(self, 620, 380))
        self.Centre()
        self.show_rows()
        focus_on(self, self._list)
        if fetch_free:
            service.fetch_quota(on_done=self._free_arrived, on_error=lambda _m: None)

    def show_rows(self, free_quota: Any = None) -> None:
        """Fill the list from the service, keeping the selection where it was."""
        index = self._list.GetSelection()
        self._rows = list(self._service.usage_rows(free_quota))
        texts = [f"{row.sentence} {row.detail}".strip() for row in self._rows]
        self._list.Set(texts)
        if not texts:
            return
        if index == wx.NOT_FOUND:
            in_use = getattr(self._service, "connection_in_use", "")
            index = next((i for i, r in enumerate(self._rows) if r.connection == in_use), 0)
        self._list.SetSelection(min(index, len(texts) - 1))

    def _free_arrived(self, quota: Any) -> None:
        if not self:
            return
        self.show_rows(quota)
        # A row changed under focus without a selection change, which the reader
        # does not say: the free AI's sentence is the news.
        free = next((r for r in self._rows if r.connection == "free"), None)
        if free is not None:
            self._announce(free.sentence)

    def manage(self) -> None:
        """Open the selected connection's own page."""
        index = self._list.GetSelection()
        if not 0 <= index < len(self._rows):
            return
        row = self._rows[index]
        if not row.manage_url:
            self._announce("This connection has no usage page. The count here is the whole story.")
            return
        # The browser taking focus is what the reader announces; only failure is ours.
        if not wx.LaunchDefaultBrowser(row.manage_url):
            self._announce(f"Could not open a browser. Go to {row.manage_url}.")
