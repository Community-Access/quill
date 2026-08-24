"""Choose which branches Browse Stations shows.

Quill Radio 3.0 took the browse tree from thirteen branches to twenty-eight.
That is a good problem and it is still a problem: someone who only ever opens
their local NPR affiliate and ACB Media now arrows past Audius, Mixcloud and
Project Gutenberg every time they open the window. For a screen-reader user
that is not clutter, it is distance.

The same house pattern as :mod:`quill.ui.radio.search_sources_dialog`, for the
same reason: checkbox state inside a wx list is announced inconsistently across
NVDA, JAWS and Narrator, so every row *says* its own state instead -- "On.
LibriVox Audiobooks. Public-domain audiobooks, by chapter." -- and one button
flips the focused row. Rows are ordered by their settings group with the group
named on the first row of each, so twenty-eight entries read as six short runs
rather than a wall.

And the same rule search follows: **a branch that is off is not in the tree at
all, and is never contacted.** This is a speed and privacy control as much as a
tidiness one, and the dialog says so.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio import browse_visibility
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

TITLE = "Browse Sources"


def describe_source(
    source: browse_visibility.BrowseSourceInfo, *, enabled: bool, first_in_group: bool
) -> str:
    """One row: its state, its name, what it is -- and its group, when the row
    opens one, so the runs stay legible while arrowing straight through."""
    state = "On" if enabled else "Off"
    group = f" {source.group} -- " if first_in_group else " "
    return f"{state}.{group}{source.label}. {source.description}"


def _rows(enabled: set[str]) -> tuple[list[browse_visibility.BrowseSourceInfo], list[str]]:
    """The sources in group order, and their spoken labels."""
    infos: list[browse_visibility.BrowseSourceInfo] = []
    labels: list[str] = []
    for _group, pairs in browse_visibility.in_groups(browse_visibility.enable_all()):
        for index, (source, _on) in enumerate(pairs):
            infos.append(source)
            labels.append(
                describe_source(source, enabled=source.id in enabled, first_in_group=index == 0)
            )
    return infos, labels


class BrowseSourcesDialog:
    """Switch individual browse branches on and off."""

    def __init__(
        self,
        parent: object,
        *,
        enabled: object,
        show_modal_dialog: Callable,
        announce: Callable[[str], None],
    ) -> None:
        import wx

        self._wx = wx
        #: ``None`` (never set) resolves to the defaults here; what ``show``
        #: returns is always an explicit list, because opening this dialog is
        #: the moment the choice becomes the listener's own.
        self._enabled = set(browse_visibility.normalize(enabled))
        self._announce = announce
        self._show_modal = show_modal_dialog
        self._sources, labels = _rows(self._enabled)

        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(wx.Size(680, 480))
        self._build_ui(labels)

    def _build_ui(self, labels: list[str]) -> None:
        wx = self._wx
        panel = self.dialog
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(
                panel,
                label=(
                    "Choose which branches Browse Stations shows. A branch that is "
                    "off is not in the tree at all and is never contacted."
                ),
            ),
            0,
            wx.ALL,
            8,
        )

        root.Add(wx.StaticText(panel, label="&Branches:"), 0, wx.LEFT, 8)
        self._list = wx.ListBox(panel, choices=labels, style=wx.LB_SINGLE)
        self._list.SetName("Browse branches")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._summary = wx.StaticText(panel, label=self._summary_text())
        root.Add(self._summary, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self._toggle_btn = wx.Button(panel, label="&Turn On or Off")
        self._toggle_btn.SetHelpText(
            "Flips the highlighted source. Off means gone from the Browse "
            "tree entirely -- and never contacted."
        )
        all_btn = wx.Button(panel, label="Turn On &All")
        all_btn.SetHelpText("Turns every source on, restoring the full Browse tree.")
        reset_btn = wx.Button(panel, label="&Reset to Default")
        reset_btn.SetHelpText("Returns the source list to what a fresh install shows.")
        close_btn = wx.Button(panel, wx.ID_CLOSE, label="C&lose")
        close_btn.SetHelpText("Closes this window; your source choices are already saved.")
        for button in (self._toggle_btn, all_btn, reset_btn, close_btn):
            row.Add(button, 0, wx.RIGHT, 6)
        root.Add(row, 0, wx.ALL, 8)

        apply_modal_ids(self.dialog, affirmative_id=close_btn.GetId(), escape_id=close_btn.GetId())
        self.dialog.SetSizer(root)

        self._toggle_btn.Bind(wx.EVT_BUTTON, lambda _e: self._toggle())
        apply_listbox_activation(self._list, lambda _e: self._toggle())
        all_btn.Bind(wx.EVT_BUTTON, lambda _e: self._set_all(browse_visibility.enable_all()))
        reset_btn.Bind(wx.EVT_BUTTON, lambda _e: self._set_all(browse_visibility.default_enabled()))
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))

        if self._sources:
            self._list.SetSelection(0)
        wx.CallAfter(self._list.SetFocus)

    def _summary_text(self) -> str:
        return browse_visibility.describe_selection(tuple(self._enabled))

    def selection(self) -> tuple[str, ...]:
        """The chosen branches, in tree order."""
        return browse_visibility.normalize(tuple(self._enabled))

    def _refresh(self, *, keep: int) -> None:
        _infos, labels = _rows(self._enabled)
        self._list.Set(labels)
        if 0 <= keep < self._list.GetCount():
            self._list.SetSelection(keep)
        self._summary.SetLabel(self._summary_text())

    def _toggle(self) -> None:
        index = self._list.GetSelection()
        if not 0 <= index < len(self._sources):
            return
        source = self._sources[index]
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
