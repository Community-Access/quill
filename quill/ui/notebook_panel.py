"""Docked Notebook Entries panel for MainFrame (§10.4 Milestone 2)."""

from __future__ import annotations


class NotebookEntriesPanel:
    """Docked panel showing entries for the active notebook.

    Housed in ``_main_splitter`` as the left pane. Always constructed but only
    visible when ``_main_splitter`` is split.  ``wx`` is passed in (not imported
    at module level) to match the lazy-import pattern used elsewhere in the UI
    layer.
    """

    def __init__(self, parent: object, wx: object) -> None:
        self._wx = wx
        self.panel = wx.Panel(parent)
        self.panel.SetName("Notebook entries")
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._name_label = wx.StaticText(self.panel, label="No notebook open")
        self._name_label.SetName("Notebook name")
        self._goal_label = wx.StaticText(self.panel, label="")
        self._goal_label.SetName("Notebook goal")
        self._filter = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        self._filter.SetName("Filter notebook entries")
        self._filter.SetHint("Filter entries...")
        self._listbox = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self._listbox.SetName("Notebook entries list")

        sizer.Add(self._name_label, 0, wx.EXPAND | wx.ALL, 4)
        sizer.Add(self._goal_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        sizer.Add(self._filter, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        sizer.Add(self._listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        self.panel.SetSizer(sizer)

        self._entries: list[object] = []
        self._filter.Bind(wx.EVT_TEXT, self._on_filter_change)

    def load(self, notebook: object) -> None:
        """Populate the panel from a Notebook instance."""
        name = getattr(notebook, "name", "Untitled Notebook")
        self._name_label.SetLabel(name)
        goal = getattr(notebook, "goal", None)
        if goal is not None and getattr(goal, "enabled", False):
            count = getattr(goal, "today_count", 0)
            target = getattr(goal, "daily_target", 500)
            unit = getattr(goal, "unit", "words")
            self._goal_label.SetLabel(f"Goal: {count:,} / {target:,} {unit} today")
        else:
            self._goal_label.SetLabel("")
        self._entries = list(getattr(notebook, "entries", []))
        self._refresh_listbox(self._filter.GetValue())

    def clear(self) -> None:
        """Remove all entries from the panel."""
        self._name_label.SetLabel("No notebook open")
        self._goal_label.SetLabel("")
        self._entries = []
        self._listbox.Clear()

    def selected_entry(self) -> object | None:
        """Return the currently selected NotebookEntry, or None."""
        wx = self._wx
        idx = self._listbox.GetSelection()
        if idx == wx.NOT_FOUND:
            return None
        return self._listbox.GetClientData(idx)

    def _refresh_listbox(self, query: str) -> None:
        query = query.strip().lower()
        self._listbox.Clear()
        for entry in self._entries:
            title = getattr(entry, "title", None) or getattr(entry, "path", "")
            if query and query not in title.lower():
                continue
            idx = self._listbox.Append(title)
            self._listbox.SetClientData(idx, entry)

    def _on_filter_change(self, event: object) -> None:
        self._refresh_listbox(self._filter.GetValue())
        event.Skip()
