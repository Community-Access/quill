"""Choose which directories Find Stations searches.

A reorderable/checkable list control is the obvious shape and the wrong one:
checkbox state inside a wx list is announced inconsistently across NVDA, JAWS
and Narrator, so a listener cannot reliably tell on from off -- which is the
only thing this dialog exists to convey. The house pattern is used instead: a
plain ``wx.ListBox`` whose every row *says* its own state, and a button that
flips the focused row.

So a row reads "On. YouTube. Videos, added as stations you can play and
record." State first, because that is the thing being scanned for; the
explanation last, because it is read once and then known.

Turning a source off means it is never contacted -- the search does not fetch
its results and discard them -- so this is a speed and a privacy control as
much as a tidiness one, and the dialog says so.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio import search_sources
from quill.ui.dialog_contract import apply_modal_ids

TITLE = "Search Sources"


def describe_source(source: search_sources.SearchSource, *, enabled: bool) -> str:
    """One row: its state, its name, and what it is.

    State leads because it is what the listener is arrowing the list to check.
    """
    state = "On" if enabled else "Off"
    return f"{state}. {source.label}. {source.description}"


class SearchSourcesDialog:
    """Switch individual search sources on and off."""

    def __init__(
        self,
        parent: object,
        *,
        enabled: object,
        show_modal_dialog: Callable,
        announce: Callable[[str], None],
        on_changed: Callable[[tuple[str, ...]], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._enabled = set(search_sources.normalize(enabled))
        self._announce = announce
        self._on_changed = on_changed
        self._show_modal = show_modal_dialog

        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(wx.Size(620, 440))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        panel = self.dialog
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(
                panel,
                label=(
                    "Choose where Find Stations looks. A source that is off is never "
                    "contacted, so searching is faster and quieter."
                ),
            ),
            0,
            wx.ALL,
            8,
        )

        root.Add(wx.StaticText(panel, label="&Sources:"), 0, wx.LEFT, 8)
        self._list = wx.ListBox(panel, choices=self._labels(), style=wx.LB_SINGLE)
        self._list.SetName("Search sources")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._summary = wx.StaticText(panel, label=self._summary_text())
        root.Add(self._summary, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self._toggle_btn = wx.Button(panel, label="&Turn On or Off")
        self._toggle_btn.SetHelpText(
            "Flips the highlighted directory. Off means Find Stations never "
            "asks it -- fewer sources answer faster."
        )
        all_btn = wx.Button(panel, label="Turn On &All")
        all_btn.SetHelpText("Turns every directory on, the widest possible search.")
        reset_btn = wx.Button(panel, label="&Reset to Default")
        reset_btn.SetHelpText("Returns the search sources to what a fresh install asks.")
        close_btn = wx.Button(panel, wx.ID_CLOSE, label="C&lose")
        close_btn.SetHelpText("Closes this window; your source choices are already saved.")
        for button in (self._toggle_btn, all_btn, reset_btn, close_btn):
            row.Add(button, 0, wx.RIGHT, 6)
        root.Add(row, 0, wx.ALL, 8)

        apply_modal_ids(self.dialog, affirmative_id=close_btn.GetId(), escape_id=close_btn.GetId())
        self.dialog.SetSizer(root)

        self._toggle_btn.Bind(wx.EVT_BUTTON, lambda _e: self._toggle())
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._toggle())
        all_btn.Bind(wx.EVT_BUTTON, lambda _e: self._set_all(search_sources.SOURCE_IDS))
        reset_btn.Bind(wx.EVT_BUTTON, lambda _e: self._set_all(search_sources.DEFAULT_ENABLED))
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))

        if search_sources.SEARCH_SOURCES:
            self._list.SetSelection(0)
        wx.CallAfter(self._list.SetFocus)

    def _labels(self) -> list[str]:
        return [
            describe_source(s, enabled=s.id in self._enabled) for s in search_sources.SEARCH_SOURCES
        ]

    def _summary_text(self) -> str:
        return search_sources.describe_selection(tuple(self._enabled))

    def selection(self) -> tuple[str, ...]:
        """The chosen sources, in registry order."""
        return search_sources.normalize(tuple(self._enabled))

    def _refresh(self, *, keep: int) -> None:
        self._list.Set(self._labels())
        if 0 <= keep < self._list.GetCount():
            self._list.SetSelection(keep)
        self._summary.SetLabel(self._summary_text())
        if self._on_changed is not None:
            self._on_changed(self.selection())

    def _toggle(self) -> None:
        index = self._list.GetSelection()
        if not 0 <= index < len(search_sources.SEARCH_SOURCES):
            return
        source = search_sources.SEARCH_SOURCES[index]
        if source.id in self._enabled:
            self._enabled.discard(source.id)
        else:
            self._enabled.add(source.id)
        self._refresh(keep=index)
        # Say the outcome, not just "toggled": the row label changed underneath
        # the listener, and a reader may not re-read it on its own.
        state = "on" if source.id in self._enabled else "off"
        self._announce(f"{source.label} {state}.")

    def _set_all(self, ids: tuple[str, ...]) -> None:
        self._enabled = set(ids)
        self._refresh(keep=self._list.GetSelection())
        self._announce(self._summary_text())

    def show(self) -> tuple[str, ...]:
        try:
            self._show_modal(self.dialog, TITLE)
        finally:
            self.dialog.Destroy()
        return self.selection()
