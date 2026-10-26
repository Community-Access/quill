"""Native, keyboard-operable capture setup and evidence review."""

from __future__ import annotations

import wx

from quill.core.studio_capture import CaptureTarget, validate_region
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

# a11y: needs manual verification — screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


class CaptureSetupDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        folder: str,
        targets: list[CaptureTarget],
        announce=lambda _text: None,
    ) -> None:
        super().__init__(
            parent, title="Capture screen", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.targets = targets
        self._announce = announce
        outer = wx.BoxSizer(wx.VERTICAL)
        hint = wx.StaticText(
            self,
            label=(
                "Select a named window, display, full desktop, or numeric rectangle.\n"
                "For the active-window option, switch windows during the delay.\n"
                "Close sensitive windows before capture.\n"
                "AI sharing requires Ask AI approval or previously enabled automatic AI."
            ),
        )
        outer.Add(hint, 0, wx.ALL, 10)
        outer.Add(wx.StaticText(self, label="&Target"), 0, wx.LEFT, 10)
        self.target = wx.Choice(self, choices=[target.label for target in targets])
        self.target.SetSelection(0)
        set_accessible_name(self.target, "Target")
        self.target.SetHelpText(
            "Select a named window, display, desktop, active window or rectangle. "
            "A selected window is captured directly, without capturing other displays."
        )
        outer.Add(self.target, 0, wx.EXPAND | wx.ALL, 10)
        refresh = wx.Button(self, label="&Refresh windows and displays")
        refresh.Bind(wx.EVT_BUTTON, self._refresh_targets)
        refresh.SetHelpText(
            "Refresh windows and displays. A missing target stays selected and "
            "unavailable until you deliberately choose another target."
        )
        outer.Add(refresh, 0, wx.LEFT | wx.RIGHT, 10)
        group = wx.StaticBoxSizer(wx.VERTICAL, self, label="Numeric rectangle in physical pixels")
        grid = wx.FlexGridSizer(cols=4, hgap=10, vgap=6)
        self.coordinates = []
        desktop = next(target for target in targets if target.kind == "desktop")
        left, top, right, bottom = desktop.bounds
        values = (left, top, max(1, right - left), max(1, bottom - top))
        for label, value in zip(("&Left", "T&op", "&Width", "&Height"), values, strict=True):
            grid.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            field = wx.SpinCtrl(
                self, min=-100000 if len(self.coordinates) < 2 else 1, max=100000, initial=value
            )
            set_accessible_name(field, label.replace("&", "") + " in physical pixels")
            self.coordinates.append(field)
            field.SetHelpText(
                "Rectangle coordinates use physical desktop pixels. Negative left "
                "and top values are allowed for displays left of or above the primary display."
            )
            grid.Add(field, 0, wx.EXPAND)
        group.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        outer.Add(group, 0, wx.EXPAND | wx.ALL, 10)
        self.target.Bind(wx.EVT_CHOICE, self._update_region)
        self._update_region()
        outer.Add(wx.StaticText(self, label="&Delay in seconds (2 to 60)"), 0, wx.LEFT, 10)
        self.delay = wx.SpinCtrl(self, min=2, max=60, initial=5)
        set_accessible_name(self.delay, "Delay in seconds (2 to 60)")
        self.delay.SetHelpText(
            "Wait this many seconds before capture. For active-window capture, "
            "switch to the intended window during the delay."
        )
        outer.Add(self.delay, 0, wx.EXPAND | wx.ALL, 10)
        outer.Add(wx.StaticText(self, label="Save &folder"), 0, wx.LEFT, 10)
        self.folder = wx.TextCtrl(self, value=folder)
        set_accessible_name(self.folder, "Save folder")
        self.folder.SetHelpText(
            "An absolute folder for PNG screenshots and their verification reports. "
            "The folder is created if needed; existing images are not overwritten."
        )
        outer.Add(self.folder, 0, wx.EXPAND | wx.ALL, 10)
        outer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="&Start capture",
            cancel_id=wx.ID_CANCEL,
        )
        self.SetSizerAndFit(outer)
        self.target.SetFocus()

    def _update_region(self, _event=None):
        is_region = self.targets[self.target.GetSelection()].kind == "region"
        for field in self.coordinates:
            field.Enable(is_region)

    def _refresh_targets(self, _event):
        from quill.platform.windows.studio_capture import list_capture_targets

        previous = self.targets[self.target.GetSelection()]
        try:
            updated = list_capture_targets()
        except Exception as error:
            self._announce(f"Could not refresh targets: {error}")
            return

        def same_identity(target):
            return (
                target.kind == previous.kind
                and target.window_handle == previous.window_handle
                and target.process_id == previous.process_id
                and (target.kind != "display" or target.device == previous.device)
            )

        index = next((i for i, target in enumerate(updated) if same_identity(target)), -1)
        if index < 0:
            from dataclasses import replace

            updated.append(replace(previous, label="Unavailable target: " + previous.label))
            index = len(updated) - 1
        self.targets = updated
        self.target.SetItems([target.label for target in updated])
        self.target.SetSelection(index)
        self._update_region()
        self._announce(f"{len(updated)} capture targets available.")

    def selected_target(self) -> CaptureTarget:
        from dataclasses import replace

        target = self.targets[self.target.GetSelection()]
        if target.kind == "region":
            left, top, width, height = (field.GetValue() for field in self.coordinates)
            bounds = (left, top, left + width, top + height)
            desktop = next(t for t in self.targets if t.kind == "desktop")
            validate_region(bounds, desktop.bounds)
            target = replace(
                target,
                bounds=bounds,
                label=f"Rectangle: left {left}, top {top}, {width} by {height} pixels",
            )
        return target
