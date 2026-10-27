"""Native, keyboard-operable capture setup and evidence review."""

from __future__ import annotations

import wx
from wx.lib.scrolledpanel import ScrolledPanel

from quill.core.studio_capture import REGION_PRESETS, CaptureTarget, guided_region, validate_region
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.studio_capture_options import CaptureOptionsMixin

# a11y: needs manual verification — screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


class CaptureSetupDialog(CaptureOptionsMixin, wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        folder: str,
        targets: list[CaptureTarget],
        announce=lambda _text: None,
        choose_control=None,
    ) -> None:
        super().__init__(
            parent, title="Capture screen", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.targets = targets
        self._announce = announce
        self.choose_control = choose_control
        self.content = ScrolledPanel(self)
        panel = self.content
        outer = wx.BoxSizer(wx.VERTICAL)
        hint = wx.StaticText(
            panel,
            label=(
                "Start with a named window: Studio chooses its size for you.\n"
                "A display captures one screen; full desktop includes every screen.\n"
                "Guided region offers whole, top, bottom, left, right or middle portions.\n"
                "For the active-window option, switch windows during the delay.\n"
                "Close sensitive windows before capture.\n"
                "AI sharing requires Ask AI approval or previously enabled automatic AI."
            ),
        )
        outer.Add(hint, 0, wx.ALL, 10)
        outer.Add(wx.StaticText(panel, label="&Target"), 0, wx.LEFT, 10)
        self.target = wx.Choice(panel, choices=[target.friendly_label for target in targets])
        self.target.SetSelection(0)
        set_accessible_name(self.target, "Target")
        self.target.SetHelpText(
            "A named window needs no size settings. Guided region uses familiar "
            "portions of a named window or display. Full desktop includes all screens."
        )
        outer.Add(self.target, 0, wx.EXPAND | wx.ALL, 10)
        refresh = wx.Button(panel, label="&Refresh windows and displays")
        refresh.Bind(wx.EVT_BUTTON, self._refresh_targets)
        refresh.SetHelpText(
            "Refresh windows and displays. A missing target stays selected and "
            "unavailable until you deliberately choose another target."
        )
        outer.Add(refresh, 0, wx.LEFT | wx.RIGHT, 10)
        self.all_windows = wx.CheckBox(panel, label="Show &all windows (advanced)")
        set_accessible_name(self.all_windows, "Show all windows")
        self.all_windows.SetHelpText(
            "Include every visible window, including tool and helper windows. "
            "Leave unchecked for a shorter list of top-level task windows (recommended)."
        )
        self.all_windows.Bind(wx.EVT_CHECKBOX, self._refresh_targets)
        outer.Add(self.all_windows, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.properties = wx.Button(panel, label="Window &properties...")
        self.properties.SetHelpText(
            "Show advanced details about the selected named window, such as its process, "
            "bounds, and internal identifiers."
        )
        self.properties.Bind(wx.EVT_BUTTON, self._show_window_properties)
        outer.Add(self.properties, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.controls_button = wx.Button(panel, label="Choose a specific window &element...")
        self.controls_button.SetHelpText(
            "Choose a named window in Target first, then find a real accessible "
            "part by its name or role, such as a button or document. No sizes are needed."
        )
        self.controls_button.Bind(wx.EVT_BUTTON, self._choose_control)
        outer.Add(self.controls_button, 0, wx.ALL, 10)
        self.region_panel = wx.Panel(panel)
        region_layout = wx.BoxSizer(wx.VERTICAL)
        region_layout.Add(wx.StaticText(self.region_panel, label="Region so&urce"), 0, wx.TOP, 8)
        self.region_sources = []
        self.region_source = wx.Choice(self.region_panel)
        set_accessible_name(self.region_source, "Region source")
        self.region_source.SetHelpText(
            "Choose the window or display that contains what you want to show. "
            "The program calculates its position and size; no pixels are needed."
        )
        region_layout.Add(self.region_source, 0, wx.EXPAND | wx.BOTTOM, 8)
        region_layout.Add(wx.StaticText(self.region_panel, label="Capture &portion"), 0)
        self.portion = wx.Choice(self.region_panel, choices=list(REGION_PRESETS))
        self.portion.SetSelection(0)
        set_accessible_name(self.portion, "Capture portion")
        self.portion.SetHelpText(
            "Whole source is recommended to keep context. Half and middle portions "
            "can cut off text or controls. Review the result before sharing."
        )
        region_layout.Add(self.portion, 0, wx.EXPAND | wx.BOTTOM, 8)
        self.advanced = wx.CheckBox(self.region_panel, label="Enter e&xact coordinates (advanced)")
        self.advanced.SetHelpText(
            "Optional physical-pixel coordinates. Leave unchecked for guided portions. "
            "Numbers describe screen dots, not text size or accessibility quality."
        )
        region_layout.Add(self.advanced, 0, wx.BOTTOM, 8)
        self.numeric_panel = wx.Panel(self.region_panel)
        group = wx.StaticBoxSizer(wx.VERTICAL, self.numeric_panel, label="Advanced physical pixels")
        grid = wx.FlexGridSizer(cols=4, hgap=10, vgap=6)
        self.coordinates = []
        desktop = next(target for target in targets if target.kind == "desktop")
        left, top, right, bottom = desktop.bounds
        values = (left, top, max(1, right - left), max(1, bottom - top))
        for label, value in zip(("&Left", "T&op", "&Width", "&Height"), values, strict=True):
            grid.Add(wx.StaticText(self.numeric_panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            field = wx.SpinCtrl(
                self.numeric_panel,
                min=-100000 if len(self.coordinates) < 2 else 1,
                max=100000,
                initial=value,
            )
            set_accessible_name(field, label.replace("&", "") + " in physical pixels")
            self.coordinates.append(field)
            field.SetHelpText(
                "Rectangle coordinates use physical desktop pixels. Negative left "
                "and top values are allowed for displays left of or above the primary display."
            )
            grid.Add(field, 0, wx.EXPAND)
            field.Bind(wx.EVT_SPINCTRL, self._update_guidance)
            field.Bind(wx.EVT_TEXT, self._update_guidance)
        group.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        self.numeric_panel.SetSizer(group)
        region_layout.Add(self.numeric_panel, 0, wx.EXPAND)
        self.region_panel.SetSizer(region_layout)
        outer.Add(self.region_panel, 0, wx.EXPAND | wx.ALL, 10)
        outer.Add(wx.StaticText(panel, label="Capture plan and &guidance"), 0, wx.LEFT, 10)
        self.guidance = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 100))
        set_accessible_name(self.guidance, "Capture plan and guidance")
        self.guidance.SetHelpText(
            "Review what will be included, what may be cut off, and what to check next. "
            "Geometry checks cannot prove that the screenshot shows the intended content."
        )
        outer.Add(self.guidance, 0, wx.EXPAND | wx.ALL, 10)
        self._refresh_region_sources()
        self.region_source.Bind(wx.EVT_CHOICE, self._update_guidance)
        self.portion.Bind(wx.EVT_CHOICE, self._update_guidance)
        self.advanced.Bind(wx.EVT_CHECKBOX, self._update_guidance)
        self.target.Bind(wx.EVT_CHOICE, self._update_region)
        self._update_region()
        outer.Add(wx.StaticText(panel, label="&Delay in seconds (2 to 60)"), 0, wx.LEFT, 10)
        self.delay = wx.SpinCtrl(panel, min=2, max=60, initial=5)
        set_accessible_name(self.delay, "Delay in seconds (2 to 60)")
        self.delay.SetHelpText(
            "Wait this many seconds before capture. For active-window capture, "
            "switch to the intended window during the delay."
        )
        outer.Add(self.delay, 0, wx.EXPAND | wx.ALL, 10)
        outer.Add(wx.StaticText(panel, label="Save &folder"), 0, wx.LEFT, 10)
        self.folder = wx.TextCtrl(panel, value=folder)
        set_accessible_name(self.folder, "Save folder")
        self.folder.SetHelpText(
            "An absolute folder for PNG screenshots and their verification reports. "
            "The folder is created if needed; existing images are not overwritten."
        )
        outer.Add(self.folder, 0, wx.EXPAND | wx.ALL, 10)
        self._build_capture_options(panel, outer)
        panel.SetSizer(outer)
        panel.SetupScrolling(scroll_x=False)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(panel, 1, wx.EXPAND)
        layout.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="&Start capture",
            cancel_id=wx.ID_CANCEL,
        )
        self.SetSizer(layout)
        available = wx.GetClientDisplayRect()
        self.SetSize((min(800, available.width), min(780, available.height)))
        self.target.SetFocus()

    def _update_region(self, _event=None):
        is_region = self.targets[self.target.GetSelection()].kind == "region"
        self.region_panel.Show(is_region)
        self._sync_window_actions()
        self._update_guidance(_event)

    def _sync_window_actions(self):
        target = self.targets[self.target.GetSelection()]
        self.properties.Enable(target.kind == "window")
        self.controls_button.Enable(target.kind == "window")

    def _show_window_properties(self, _event):
        target = self.targets[self.target.GetSelection()]
        if target.kind != "window":
            self._announce("Select a named window in Target first.")
            self.target.SetFocus()
            return
        details = _window_details_text(target)
        _copy_to_clipboard(details)
        message = (
            "Window properties copied to the clipboard.\n\n"
            + details
            + "\n\nThis information is optional. It can help when reporting a capture issue."
        )
        dialog = wx.MessageDialog(
            self,
            message=message,
            caption="Window properties",
            style=wx.OK | wx.ICON_INFORMATION,
        )
        self.ShowModal(dialog)

    def _choose_control(self, event):
        target = self.targets[self.target.GetSelection()]
        if target.kind != "window" or self.choose_control is None:
            self._announce("Select a named window first to choose one of its accessible controls.")
            self.target.SetFocus()
            return
        selected = self.choose_control(target)
        if selected is not None:
            self.targets.append(selected)
            self.target.Append(selected.friendly_label)
            self.target.SetSelection(len(self.targets) - 1)
            self._update_region()
            self._announce("Control selected. Keep its window still; review after capture.")

    def _refresh_region_sources(self):
        previous = (
            self.region_sources[self.region_source.GetSelection()]
            if self.region_sources and self.region_source.GetSelection() >= 0
            else None
        )
        self.region_sources = [t for t in self.targets if t.kind in {"window", "display"}]
        if not self.region_sources:
            self.region_sources = [t for t in self.targets if t.kind == "desktop"]
        index = 0
        if previous is not None:
            index = next(
                (
                    i
                    for i, t in enumerate(self.region_sources)
                    if (t.kind, t.window_handle, t.process_id, t.device)
                    == (previous.kind, previous.window_handle, previous.process_id, previous.device)
                ),
                -1,
            )
            if index < 0:
                from dataclasses import replace

                self.region_sources.append(
                    replace(previous, label="Unavailable source: " + previous.label)
                )
                index = len(self.region_sources) - 1
        self.region_source.SetItems([t.friendly_label for t in self.region_sources])
        self.region_source.SetSelection(index)

    def _update_guidance(self, _event=None):
        if not hasattr(self, "guidance"):
            return
        is_region = self.targets[self.target.GetSelection()].kind == "region"
        advanced = is_region and self.advanced.GetValue()
        if advanced and _event is not None and _event.GetEventObject() is self.advanced:
            source = self.region_sources[self.region_source.GetSelection()]
            region = guided_region(source, self.portion.GetSelection(), "")
            left, top, right, bottom = region.bounds
            for field, value in zip(
                self.coordinates, (left, top, right - left, bottom - top), strict=True
            ):
                field.SetValue(value)
        self.numeric_panel.Show(advanced)
        self.region_source.Enable(not advanced)
        self.portion.Enable(not advanced)
        try:
            target = self.selected_target()
            if target.kind == "region":
                message = f"Guided region: {target.friendly_label}. "
                if advanced:
                    message += "The numbers fit within the desktop. Content may still be clipped. "
                elif self.portion.GetSelection() != 0:
                    message += (
                        "This excludes part of the source and may cut off words or controls. "
                    )
                message += (
                    "This screen area may include overlapping windows and notifications. "
                    "Keep the source still during the delay. For a whole window, choose its named "
                    "target instead. After capture, read local OCR or ask AI about framing. "
                    "Neither geometry nor AI guarantees the intended content is complete."
                )
            elif target.kind == "window":
                message = (
                    f"Capture whole window: {target.friendly_label}. "
                    "No size settings needed. Restore a minimized window first. "
                    "Review local OCR and framing after capture; protected content may be blank."
                )
            else:
                message = (
                    f"Capture {target.friendly_label}. No size settings needed. "
                    "Desktop and display capture can include unrelated windows and notifications. "
                    "For one application, choose its named window. "
                    "To pick a specific window element, choose a named window target first."
                )
        except ValueError as error:
            message = (
                f"Cannot capture this region: {error} Choose Whole source or correct the values."
            )
        self.guidance.ChangeValue(message)
        self.content.Layout()
        self.content.FitInside()

    def _refresh_targets(self, _event):
        from quill.platform.windows.studio_capture import list_capture_targets

        previous = self.targets[self.target.GetSelection()]
        try:
            updated = list_capture_targets(include_all_windows=self.all_windows.GetValue())
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
        self.target.SetItems([target.friendly_label for target in updated])
        self.target.SetSelection(index)
        self._refresh_region_sources()
        self._update_region()
        self._announce(f"{len(updated)} capture targets available.")

    def selected_target(self) -> CaptureTarget:
        from dataclasses import replace

        target = self.targets[self.target.GetSelection()]
        if target.kind == "region":
            if not self.advanced.GetValue():
                source = self.region_sources[self.region_source.GetSelection()]
                target = guided_region(source, self.portion.GetSelection(), target.device)
                bounds = target.bounds
            else:
                left, top, width, height = (field.GetValue() for field in self.coordinates)
                bounds = (left, top, left + width, top + height)
                target = replace(
                    target,
                    bounds=bounds,
                    label=f"Advanced rectangle: left {left}, top {top}, {width} by {height} pixels",
                )
            desktop = next(t for t in self.targets if t.kind == "desktop")
            validate_region(bounds, desktop.bounds)
        return target

    def focus_invalid_input(self):
        try:
            self.selected_target()
        except ValueError:
            field = self.coordinates[0] if self.advanced.GetValue() else self.region_source
            field.SetFocus()
            return
        self.folder.SetFocus()


def _window_details_text(target: CaptureTarget) -> str:
    title = target.label
    if title.lower().startswith("window:"):
        title = title.split(":", 1)[1].strip()
    left, top, right, bottom = target.bounds
    width = right - left
    height = bottom - top
    handle_hex = hex(target.window_handle) if target.window_handle else "0x0"
    class_name = ""
    process_name = target.application or ""
    executable = ""
    try:
        import win32gui
    except Exception:
        win32gui = None
    if win32gui is not None and target.window_handle:
        try:
            live_title = win32gui.GetWindowText(target.window_handle).strip()
            if live_title:
                title = live_title
        except Exception:
            pass
        try:
            class_name = win32gui.GetClassName(target.window_handle)
        except Exception:
            class_name = ""
    try:
        import psutil
    except Exception:
        psutil = None
    if psutil is not None and target.process_id:
        try:
            process = psutil.Process(target.process_id)
            process_name = process_name or process.name()
            executable = process.exe() or ""
        except Exception:
            pass
    lines = [
        f"Title: {title}",
        f"Application: {process_name or 'Unknown'}",
        f"Process ID: {target.process_id or 'Unknown'}",
        f"Window handle: {target.window_handle} ({handle_hex})",
        f"Class name: {class_name or 'Unknown'}",
        f"Bounds: left {left}, top {top}, width {width}, height {height}",
    ]
    if executable:
        lines.append(f"Executable: {executable}")
    return "\n".join(lines)


def _copy_to_clipboard(text: str) -> None:
    if not text:
        return
    data = wx.TextDataObject(text)
    if wx.TheClipboard.Open():
        try:
            wx.TheClipboard.SetData(data)
        finally:
            wx.TheClipboard.Close()
