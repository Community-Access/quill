"""Progressive disclosure for saved setups and bounded repeated/scrolling captures."""

from __future__ import annotations

import wx

from quill.core.screenshot_workspaces import (
    load_workspaces,
    remove_workspace,
    save_workspace,
    workspace_target,
)
from quill.ui.dialog_contract import set_accessible_name

MODES = ("One screenshot", "Several screenshots", "Scrolling page (supported windows)")


class CaptureOptionsMixin:
    def _build_capture_options(self, panel, layout):
        advanced_panel = wx.Panel(panel)
        advanced_layout = wx.BoxSizer(wx.VERTICAL)
        # The label before the control: a screen reader names a control from
        # the static text built just before it (GATE-CTLLABEL).
        advanced_layout.Add(wx.StaticText(advanced_panel, label="Capture mode"), 0, wx.TOP, 8)
        self.mode = wx.Choice(advanced_panel, choices=list(MODES))
        self.mode.SetSelection(0)
        set_accessible_name(self.mode, "Capture mode")
        self.mode.SetHelpText(
            "Several screenshots repeats the chosen target. Scrolling page "
            "moves a supported window through its content and tries to join matching overlaps. "
            "Scrolling may expose hidden content. Partial results are marked."
        )
        advanced_layout.Add(self.mode, 0, wx.EXPAND)
        advanced_layout.Add(
            wx.StaticText(
                advanced_panel,
                label="Scrolling captures content beyond "
                "what is currently visible. Review all results before sharing.",
            ),
            0,
            wx.TOP,
            8,
        )
        self.count = wx.SpinCtrl(advanced_panel, min=1, max=30, initial=1)
        set_accessible_name(self.count, "Number of screenshots or scrolling limit")
        self.count.SetHelpText(
            "From 1 to 30. Scrolling needs at least 2. This bounds storage and memory use."
        )

        def choose_mode(event):
            if self.mode.GetSelection() and self.count.GetValue() == 1:
                self.count.SetValue(3)
            self._announce(
                "Capture mode changed. Review the number of screenshots before starting."
            )

        self.mode.Bind(wx.EVT_CHOICE, choose_mode)
        advanced_layout.Add(
            wx.StaticText(advanced_panel, label="Number of screenshots or scrolling limit"),
            0,
            wx.TOP,
            8,
        )
        advanced_layout.Add(self.count, 0, wx.EXPAND)
        self.interval = wx.SpinCtrl(advanced_panel, min=1, max=60, initial=2)
        set_accessible_name(self.interval, "Seconds between repeated screenshots")
        self.interval.SetHelpText(
            "From 1 to 60 seconds between repeated screenshots. Does not affect scrolling."
        )
        advanced_layout.Add(
            wx.StaticText(advanced_panel, label="Seconds between repeated screenshots"),
            0,
            wx.TOP,
            8,
        )
        advanced_layout.Add(self.interval, 0, wx.EXPAND)
        self.countdown = wx.CheckBox(advanced_panel, label="Speak the countdown before capture")
        self.countdown.SetHelpText(
            "Optional spoken/text countdown during the selected delay. Off by default."
        )
        advanced_layout.Add(self.countdown, 0, wx.TOP, 8)
        self.setup_name = wx.TextCtrl(advanced_panel)
        set_accessible_name(self.setup_name, "Name for this capture setup")
        self.setup_name.SetHelpText(
            "Save a capture setup. AI permission and output destinations are never saved."
        )
        advanced_layout.Add(
            wx.StaticText(advanced_panel, label="Name for this capture setup"), 0, wx.TOP, 8
        )
        advanced_layout.Add(self.setup_name, 0, wx.EXPAND)
        self.setups = wx.Choice(advanced_panel, choices=sorted(load_workspaces()))
        set_accessible_name(self.setups, "Saved capture setups")
        self.setups.SetHelpText(
            "Saved windows are rechecked. Select again if the application closed or restarted."
        )
        if self.setups.GetCount():
            self.setups.SetSelection(0)
        advanced_layout.Add(
            wx.StaticText(advanced_panel, label="Saved capture setups"), 0, wx.TOP, 8
        )
        advanced_layout.Add(self.setups, 0, wx.EXPAND)
        buttons = wx.WrapSizer(wx.HORIZONTAL)
        for label, handler in (
            ("Save this setup", self._save_setup),
            ("Use saved setup", self._load_setup),
            ("Remove saved setup", self._remove_setup),
        ):
            button = wx.Button(advanced_panel, label=label)
            button.SetHelpText(label + ". No screenshot or upload happens when managing a setup.")
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.ALL, 3)
        advanced_layout.Add(buttons, 0, wx.EXPAND)
        advanced_panel.SetSizer(advanced_layout)
        advanced_panel.Hide()
        self.extra_options = wx.CheckBox(panel, label="More capture options (Ad&vanced)")
        self.extra_options.SetHelpText(
            "Optional repeated shots, scrolling and saved setups. One shot is the default."
        )

        def toggle(event):
            advanced_panel.Show(self.extra_options.GetValue())
            panel.Layout()
            panel.FitInside()
            self._announce(
                "More capture options shown."
                if self.extra_options.GetValue()
                else "More capture options hidden."
            )

        self.extra_options.Bind(wx.EVT_CHECKBOX, toggle)
        layout.Add(self.extra_options, 0, wx.ALL, 8)
        layout.Add(advanced_panel, 0, wx.EXPAND | wx.ALL, 8)

    def capture_options(self):
        # Hiding Advanced also makes its modes inactive, without erasing saved values.
        if not self.extra_options.GetValue():
            return "One screenshot", 1, self.interval.GetValue()
        return self.mode.GetStringSelection(), self.count.GetValue(), self.interval.GetValue()

    def _save_setup(self, event):
        try:
            mode, count, interval = self.capture_options()
            save_workspace(
                self.setup_name.GetValue(),
                self.selected_target(),
                self.delay.GetValue(),
                count,
                interval,
                mode=mode,
            )
            self.setups.SetItems(sorted(load_workspaces()))
            self.setups.SetStringSelection(self.setup_name.GetValue().strip())
            self._announce("Capture setup saved. Output folder and AI consent were not saved.")
        except Exception as error:
            self._announce(f"Could not save the setup: {error}")

    def _load_setup(self, event):
        try:
            name = self.setups.GetStringSelection()
            target, delay, count, interval = workspace_target(name)
            self.targets.append(target)
            self.target.Append(target.friendly_label)
            self.target.SetSelection(len(self.targets) - 1)
            if target.kind == "region":
                self.advanced.SetValue(True)
                left, top, right, bottom = target.bounds
                for field, value in zip(
                    self.coordinates, (left, top, right - left, bottom - top), strict=True
                ):
                    field.SetValue(value)
            self.delay.SetValue(max(2, delay))
            self.count.SetValue(count)
            self.interval.SetValue(interval)
            mode = str(load_workspaces()[name].get("mode", MODES[0]))
            self.mode.SetStringSelection(mode if mode in MODES else MODES[0])
            self._update_region()
            self._announce(
                "Setup selected. Review the source before capture; output folder is unchanged."
            )
        except Exception as error:
            self._announce(f"Could not load this setup: {error}. Choose the source again.")

    def _remove_setup(self, event):
        remove_workspace(self.setups.GetStringSelection())
        self.setups.SetItems(sorted(load_workspaces()))
        self._announce("Saved setup removed.")
