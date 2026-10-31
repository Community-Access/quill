"""Native keyboard control picker over the shared read-only UIA bridge."""

from __future__ import annotations

import wx

from quill.stability.task_manager import UiLifetimeToken
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.dpi import dip_size


class ScreenshotControlDialog(wx.Dialog):
    def __init__(self, host, source):
        super().__init__(
            host.frame,
            title="Choose screenshot control",
            size=dip_size(host.frame, 750, 560),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.host, self.source = host, source
        self.controls, self.visible = [], []
        self.lifetime = UiLifetimeToken()
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(
            wx.StaticText(
                self,
                label="Choose a real control by name and role. Password and "
                "offscreen controls are excluded. A screen-area capture may include "
                "overlaps; review OCR and the image before sharing.",
            ),
            0,
            wx.ALL,
            8,
        )
        layout.Add(wx.StaticText(self, label="&Find by name or role"), 0, wx.LEFT, 8)
        self.search = wx.TextCtrl(self)
        set_accessible_name(self.search, "Find by name or role")
        self.search.SetHelpText(
            "Filter the selected application's real UIA controls. No AI is used."
        )
        self.search.Bind(wx.EVT_TEXT, self._filter)
        layout.Add(self.search, 0, wx.EXPAND | wx.ALL, 8)
        layout.Add(wx.StaticText(self, label="&Controls"), 0, wx.LEFT, 8)
        self.items = wx.ListBox(self)
        set_accessible_name(self.items, "Controls")
        self.items.SetHelpText(
            "Arrow through controls. Enter selects a capture target; it does not "
            "press or invoke the application's control."
        )
        layout.Add(self.items, 1, wx.EXPAND | wx.ALL, 8)
        self.status = wx.StaticText(self, label="Reading controls in the background...")
        layout.Add(self.status, 0, wx.ALL, 8)
        layout.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(
            self, affirmative_id=wx.ID_OK, affirmative_label="&Use control", cancel_id=wx.ID_CANCEL
        )
        self.Bind(wx.EVT_BUTTON, self._accept, id=wx.ID_OK)
        self.SetSizer(layout)
        self.search.SetFocus()

        def work(*, cancellation_token, **kwargs):
            from quill.platform.windows.screenshot_uia import controls_for_window

            return controls_for_window(source, cancellation_token)

        def ready(task, controls):
            self.controls = controls
            self._filter()

        def failed(task, error):
            self._say(f"Could not read controls: {error}")

        self.task = host._task_manager.submit(
            "Read screenshot controls",
            work,
            on_success=ready,
            on_failure=failed,
            ui_lifetime=self.lifetime,
        )
        # a11y: needs manual verification — real AT focus, scaling and provider errors.

    def _say(self, message):
        self.status.SetLabel(message)
        self.host._announce(message)

    def _filter(self, event=None):
        # Filtering is user-initiated; preserve identity where it remains visible.
        selected = self.items.GetSelection()
        previous = self.visible[selected].runtime_id if selected >= 0 else None
        query = self.search.GetValue().casefold().split()
        self.visible = [
            item for item in self.controls if all(word in item.label.casefold() for word in query)
        ]
        self.items.SetItems([item.label for item in self.visible])
        if self.visible:
            index = next(
                (i for i, item in enumerate(self.visible) if item.runtime_id == previous), 0
            )
            self.items.SetSelection(index)
        self._say(f"{len(self.visible)} controls. Select a control, then Use control.")

    def _accept(self, event):
        if self.items.GetSelection() < 0:
            self._say("Select a control first, or change the search.")
            self.items.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def selected_target(self):
        return self.visible[self.items.GetSelection()].target(self.source)

    def stop(self):
        self.lifetime.invalidate()
        self.task.cancellation_token.cancel()
