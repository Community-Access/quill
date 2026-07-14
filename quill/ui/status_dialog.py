"""Native Help > Application Status dialog.

Uses wx.Notebook + wx.ListCtrl per section so screen readers get column
navigation (Left/Right arrows) instead of Browse-mode HTML table traversal.
The dialog is non-modal: it stays open while the user works, and the caller
refreshes it by calling :meth:`HelpStatusDialog.refresh`.
"""

from __future__ import annotations

from typing import Any

from quill.ui.dialog_contract import apply_modal_ids, focus_primary_control


class HelpStatusDialog:
    """Non-modal Application Status dialog backed by native wx controls."""

    def __init__(self, parent: Any, wx: Any, initial_data: dict) -> None:
        self._wx = wx

        self.dialog = wx.Dialog(
            parent,
            title="Application Status",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((820, 620))
        sizer = wx.BoxSizer(wx.VERTICAL)
        nb = wx.Notebook(self.dialog)
        nb.SetName("System status sections")

        # -- Status tab (Overview / Whisperer / Speech key-value rows) --
        status_panel = wx.Panel(nb)
        sp_sizer = wx.BoxSizer(wx.VERTICAL)
        self._status_list = wx.ListCtrl(
            status_panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VRULES,
        )
        self._status_list.SetName("Status overview")
        self._status_list.AppendColumn("Section", width=130)
        self._status_list.AppendColumn("Setting", width=220)
        self._status_list.AppendColumn("Value", width=380)
        sp_sizer.Add(self._status_list, 1, wx.EXPAND | wx.ALL, 6)
        status_panel.SetSizer(sp_sizer)
        nb.AddPage(status_panel, "Status")

        # -- Tasks & Downloads tab --
        tasks_panel = wx.Panel(nb)
        tp_sizer = wx.BoxSizer(wx.VERTICAL)
        self._tasks_list = wx.ListCtrl(
            tasks_panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VRULES,
        )
        self._tasks_list.SetName("Tasks and downloads")
        self._tasks_list.AppendColumn("Task / Model", width=220)
        self._tasks_list.AppendColumn("Status", width=90)
        self._tasks_list.AppendColumn("Progress", width=90)
        self._tasks_list.AppendColumn("Started", width=160)
        self._tasks_list.AppendColumn("Finished", width=160)
        tp_sizer.Add(self._tasks_list, 1, wx.EXPAND | wx.ALL, 6)
        tasks_panel.SetSizer(tp_sizer)
        nb.AddPage(tasks_panel, "Tasks & Downloads")

        # -- Features tab --
        features_panel = wx.Panel(nb)
        fp_sizer = wx.BoxSizer(wx.VERTICAL)
        self._features_list = wx.ListCtrl(
            features_panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VRULES,
        )
        self._features_list.SetName("Features")
        self._features_list.AppendColumn("Feature ID", width=230)
        self._features_list.AppendColumn("Name", width=210)
        self._features_list.AppendColumn("Category", width=130)
        self._features_list.AppendColumn("Status", width=80)
        fp_sizer.Add(self._features_list, 1, wx.EXPAND | wx.ALL, 6)
        features_panel.SetSizer(fp_sizer)
        nb.AddPage(features_panel, "Features")

        # -- Actions tab --
        actions_panel = wx.Panel(nb)
        ap_sizer = wx.BoxSizer(wx.VERTICAL)
        self._actions_ctrl = wx.TextCtrl(
            actions_panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        )
        self._actions_ctrl.SetName("Recent actions")
        ap_sizer.Add(self._actions_ctrl, 1, wx.EXPAND | wx.ALL, 6)
        actions_panel.SetSizer(ap_sizer)
        nb.AddPage(actions_panel, "Actions")

        sizer.Add(nb, 1, wx.EXPAND | wx.ALL, 8)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        refresh_btn = wx.Button(self.dialog, label="Refresh")
        refresh_btn.SetName("Refresh")
        close_btn = wx.Button(self.dialog, wx.ID_CLOSE, label="Close")
        close_btn.SetDefault()
        refresh_btn.Bind(wx.EVT_BUTTON, lambda _e: self._request_refresh())
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.Hide())
        btn_sizer.Add(refresh_btn, 0, wx.RIGHT, 8)
        btn_sizer.Add(close_btn, 0)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(sizer)
        self.dialog.Bind(wx.EVT_CLOSE, lambda _e: self.dialog.Hide())
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)

        self._refresh_callback: Any = None
        self.refresh(initial_data)

    def set_refresh_callback(self, callback: Any) -> None:
        self._refresh_callback = callback

    def _request_refresh(self) -> None:
        if callable(self._refresh_callback):
            self._refresh_callback()

    def refresh(self, data: dict) -> None:
        """Repopulate all list controls with updated data."""
        self._status_list.DeleteAllItems()
        # Blank the Section cell when it repeats the row above. Otherwise a
        # screen reader re-reads the section name ("Overview", "Overview"...) on
        # every Down-arrow within a section, drowning out the actual setting.
        last_section = None
        for section, setting, value in data.get("status_rows", []):
            idx = self._status_list.GetItemCount()
            self._status_list.InsertItem(idx, "" if section == last_section else section)
            self._status_list.SetItem(idx, 1, setting)
            self._status_list.SetItem(idx, 2, str(value))
            last_section = section

        self._tasks_list.DeleteAllItems()
        for task, status, progress, started, finished in data.get("task_rows", []):
            idx = self._tasks_list.GetItemCount()
            self._tasks_list.InsertItem(idx, task)
            self._tasks_list.SetItem(idx, 1, status)
            self._tasks_list.SetItem(idx, 2, str(progress))
            self._tasks_list.SetItem(idx, 3, started)
            self._tasks_list.SetItem(idx, 4, finished)

        self._features_list.DeleteAllItems()
        for fid, name, cat, state in data.get("feature_rows", []):
            idx = self._features_list.GetItemCount()
            self._features_list.InsertItem(idx, fid)
            self._features_list.SetItem(idx, 1, name)
            self._features_list.SetItem(idx, 2, cat)
            self._features_list.SetItem(idx, 3, state)

        actions = "\n".join(f"- {a}" for a in data.get("actions", []))
        self._actions_ctrl.ChangeValue(actions)

    def show(self) -> None:
        if not self.dialog.IsShown():
            self.dialog.Show()
        self.dialog.Raise()
        # Land on the first control of the visible tab, not the notebook tab
        # strip (a bare dialog.SetFocus() forwards to the notebook). This is a
        # non-modal window shown via Show(), so it routes focus itself.
        focus_primary_control(self.dialog)

    def is_alive(self) -> bool:
        try:
            return bool(self.dialog) and not self.dialog.IsBeingDeleted()
        except Exception:  # noqa: BLE001
            return False

    def close(self) -> None:
        try:
            self.dialog.Destroy()
        except Exception:  # noqa: BLE001
            pass
