"""Accessible control navigation for the family's existing settings dialogs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import wx


@dataclass(frozen=True)
class SettingTarget:
    label: str
    description: str
    control: Any


def find_settings(targets: list[SettingTarget], query: str) -> list[SettingTarget]:
    words = query.casefold().split()
    if not words:
        return []
    return [
        target
        for target in targets
        if all(word in f"{target.label} {target.description}".casefold() for word in words)
    ]


def _targets(parent: Any, prefix: str = "") -> list[SettingTarget]:
    targets = []
    label = ""
    editable = (
        wx.TextCtrl,
        wx.Choice,
        wx.ComboBox,
        wx.CheckBox,
        wx.RadioBox,
        wx.SpinCtrl,
        wx.SpinCtrlDouble,
        wx.Slider,
        wx.Button,
    )
    generic_names = {"text", "choice", "comboBox", "check", "button", "spinCtrl", "slider"}
    for control in parent.GetChildren():
        if isinstance(control, wx.StaticText):
            label = control.GetLabel().replace("&", "").strip().rstrip(":")
            continue
        if isinstance(control, editable):
            if control.GetId() in {wx.ID_OK, wx.ID_CANCEL, wx.ID_APPLY, wx.ID_CLOSE}:
                continue
            name = control.GetName()
            own_label = control.GetLabel() if isinstance(control, (wx.Button, wx.CheckBox)) else ""
            title = own_label or label or (name if name not in generic_names else "")
            title = title.replace("&", "").strip()
            if title:
                targets.append(
                    SettingTarget(
                        f"{prefix}{title}", f"{name} {control.GetHelpText()} {label}", control
                    )
                )
            label = ""
            continue
        if isinstance(control, wx.BookCtrlBase):
            for index in range(control.GetPageCount()):
                targets.extend(_targets(control.GetPage(index), f"{control.GetPageText(index)}: "))
        else:
            targets.extend(_targets(control, prefix))
    return targets


class PreferencesSearch:
    """Find a setting and focus it without changing values or accepting edits."""

    def __init__(self, dialog: Any, announce: Callable[[str], None] | None = None) -> None:
        from quill.ui.app_context_help import ensure_help_provider

        ensure_help_provider()
        self.dialog = dialog
        self.announce = announce or (lambda _message: None)
        self.targets = _targets(dialog)
        self.matches: list[SettingTarget] = []
        self.timer: Any = None
        self.closed = False
        self.panel = wx.Panel(dialog)
        layout = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self.panel, label="Find a setting:")
        layout.Add(label, 0, wx.BOTTOM, 4)
        self.search = wx.TextCtrl(self.panel)
        self.search.SetName("Find a setting")
        self.search.SetHelpText(
            "Find settings by label or help text. Control F returns here. "
            "Down moves to matches; Enter focuses a selected setting without changing it. "
            "Escape clears a search before closing the dialog."
        )
        layout.Add(self.search, 0, wx.EXPAND)
        results_label = wx.StaticText(self.panel, label="Matching settings:")
        layout.Add(results_label, 0, wx.TOP, 4)
        self.results = wx.ListBox(self.panel, size=(-1, 90))
        self.results.SetName("Matching settings")
        self.results.SetHelpText(
            "Settings matching the search. Arrow through results and press Enter "
            "to focus the setting. Disabled settings cannot be changed."
        )
        layout.Add(self.results, 0, wx.EXPAND | wx.TOP, 4)
        self.status = wx.StaticText(self.panel, label="")
        layout.Add(self.status, 0, wx.TOP, 4)
        self.panel.SetSizer(layout)
        self.results.Hide()
        self.status.Hide()
        original = dialog.GetSizer()
        dialog.SetSizer(None, deleteOld=False)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(self.panel, 0, wx.EXPAND | wx.ALL, 8)
        outer.Add(original, 1, wx.EXPAND)
        dialog.SetSizer(outer)
        self.panel.MoveBeforeInTabOrder(dialog.GetChildren()[0])
        self.search.Bind(wx.EVT_TEXT, self._on_search)
        self.results.Bind(wx.EVT_LISTBOX_DCLICK, self._on_choose)
        dialog.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        outer.Fit(dialog)
        self.search.SetFocus()

    def _on_search(self, _event: Any) -> None:
        if self.closed:
            return
        self.matches = find_settings(self.targets, self.search.GetValue())
        active = bool(self.search.GetValue().strip())
        self.results.Set([
            target.label + (" (disabled)" if not target.control.IsEnabled() else "")
            for target in self.matches
        ])
        if self.matches:
            self.results.SetSelection(0)
        self.results.Show(active)
        self.status.Show(active)
        self.status.SetLabel(f"{len(self.matches)} matching settings" if active else "")
        self.dialog.Layout()
        if self.timer is not None:
            self.timer.Stop()
        self.timer = wx.CallLater(250, self._report_count) if active else None

    def _report_count(self) -> None:
        if not self.closed:
            self.announce(f"{len(self.matches)} matching settings")

    def _on_choose(self, _event: Any) -> None:
        index = self.results.GetSelection()
        if not 0 <= index < len(self.matches):
            return
        target = self.matches[index]
        if not target.control.IsEnabled():
            self.announce("This setting is disabled")
            return
        child = target.control
        while child is not self.dialog:
            parent = child.GetParent()
            if parent is None:
                return
            if isinstance(parent, wx.BookCtrlBase):
                for page in range(parent.GetPageCount()):
                    if parent.GetPage(page) is child:
                        parent.SetSelection(page)
                        break
            panels = getattr(parent, "_panels", {})
            for name, panel in panels.items():
                if panel is child and hasattr(parent, "sections"):
                    parent.sections.SetStringSelection(name)
                    parent._on_section(None)
                    break
            child = parent
        self.dialog.Layout()
        target.control.SetFocus()
        parent = target.control.GetParent()
        while parent is not None and parent is not self.dialog:
            if isinstance(parent, wx.ScrolledWindow):
                parent.ScrollChildIntoView(target.control)
                break
            parent = parent.GetParent()

    def _on_key(self, event: Any) -> None:
        key = event.GetKeyCode()
        if event.ControlDown() and key in (ord("F"), ord("f")):
            self.search.SetFocus()
            self.search.SelectAll()
            return
        focused = wx.Window.FindFocus()
        if focused in (self.search, self.results):
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                self._on_choose(None)
                return
            if key == wx.WXK_ESCAPE and self.search.GetValue():
                self.search.SetValue("")
                self.search.SetFocus()
                return
            if key == wx.WXK_DOWN and focused is self.search and self.matches:
                self.results.SetFocus()
                return
        event.Skip()

    def close(self) -> None:
        self.closed = True
        if self.timer is not None:
            self.timer.Stop()


def install_preferences_context_help(dialog: Any) -> None:
    """Onboard apps whose local dialogs bypass the shared show contracts."""
    from quill.ui.app_context_help import install

    install(dialog)
    install_preferences_search(dialog)


def install_preferences_search(
    dialog: Any, *, announce: Callable[[str], None] | None = None
) -> PreferencesSearch | None:
    title_getter = getattr(dialog, "GetTitle", None)
    title = title_getter().casefold() if callable(title_getter) else ""
    if not ("preferences" in title or title.endswith("settings")):
        return None
    if not isinstance(dialog, (wx.Dialog, wx.Frame)) or dialog.GetSizer() is None:
        return None
    existing = getattr(dialog, "_quill_preferences_search", None)
    if existing is not None:
        existing.closed = False
        return existing
    search = PreferencesSearch(dialog, announce)
    dialog._quill_preferences_search = search

    def on_destroy(event: Any) -> None:
        if event.GetEventObject() is dialog:
            search.close()
        event.Skip()

    dialog.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)
    return search
