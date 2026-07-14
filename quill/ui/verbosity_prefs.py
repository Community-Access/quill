"""Verbosity preferences panel (verbosity §16, §17).

The embeddable top-level panel: a profile picker, the four-channel mix (with the
always-on Visual floor), validation-mode and mastery boxes, buttons that launch
the Preview Lab / History / Safe Mode / Library / Import-Export dialogs, and a
filterable verb table (master/detail) whose "Edit announcement..." opens the
token editor for the selected verb. Initial focus is the filter, where power
users start. Wires to the pure core (`profiles`, `registry`, `channels`); the
sub-dialogs are launched lazily with this panel's top-level window as parent.

This is a ``wx.Panel`` for embedding in the Preferences hub (wired in sub-PR
1.5). It does not override ``AcceptsFocus`` (A11Y-TAB-1).
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.verbosity.channels import VISUAL_ALWAYS_ON_NAME, Channel
from quill.core.verbosity.profiles import BUILTIN_PROFILES, DEFAULT_PROFILE
from quill.core.verbosity.registry import VerbRegistry, default_registry

__all__ = ["VerbosityPrefsPanel"]

_PROFILE_NAMES = ["Beginner", "Normal", "Expert", "Quiet"]
_VALIDATION_MODES = ["On button", "On focus", "Live"]


class VerbosityPrefsPanel(wx.Panel):
    """Embeddable verbosity preferences."""

    def __init__(
        self,
        parent: object,
        *,
        registry: VerbRegistry | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._registry = registry or default_registry()
        self._announce = announce_cb or (lambda _m: None)
        self._verbs = self._registry.all()

        root = wx.BoxSizer(wx.VERTICAL)

        # Profile picker.
        self._profile = wx.RadioBox(
            self, label="&Profile", choices=_PROFILE_NAMES, style=wx.RA_SPECIFY_COLS
        )
        self._profile.SetName("Verbosity profile")
        self._profile.SetSelection(_PROFILE_NAMES.index(DEFAULT_PROFILE.name))
        root.Add(self._profile, 0, wx.EXPAND | wx.ALL, 8)

        # Channel mix. Visual is the always-on floor (checked + disabled).
        channel_box = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Channels")
        self._channels: dict[str, wx.CheckBox] = {}
        for name in ("Speech", "Braille", "Sound", "Visual"):
            cb = wx.CheckBox(channel_box.GetStaticBox(), label=f"&{name}")
            cb.SetValue(True)
            if name == "Visual":
                cb.Disable()
                cb.SetName(VISUAL_ALWAYS_ON_NAME)
            else:
                cb.SetName(f"{name} channel")
            self._channels[name] = cb
            channel_box.Add(cb, 0, wx.ALL, 6)
        root.Add(channel_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        # Validation mode + mastery.
        opts = wx.BoxSizer(wx.HORIZONTAL)
        opts.Add(
            wx.StaticText(self, label="&Validation:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._validation = wx.Choice(self, choices=_VALIDATION_MODES)
        self._validation.SetName("Validation timing")
        self._validation.SetSelection(0)
        opts.Add(self._validation, 0, wx.RIGHT, 16)
        self._mastery = wx.CheckBox(self, label="Suggest &mastery step-downs")
        self._mastery.SetName("Mastery suggestions")
        self._mastery.SetValue(True)
        opts.Add(self._mastery, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(opts, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # Tool buttons.
        tools = wx.BoxSizer(wx.HORIZONTAL)
        self._preview_btn = wx.Button(self, label="Preview &Lab...")
        self._history_btn = wx.Button(self, label="&History...")
        self._library_btn = wx.Button(self, label="&Templates...")
        self._safe_btn = wx.Button(self, label="&Safe Mode...")
        self._io_btn = wx.Button(self, label="Import / E&xport...")
        for b in (
            self._preview_btn,
            self._history_btn,
            self._library_btn,
            self._safe_btn,
            self._io_btn,
        ):
            tools.Add(b, 0, wx.RIGHT, 6)
        root.Add(tools, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # Verb table: filter + master list + detail.
        root.Add(wx.StaticText(self, label="&Find a verb:"), 0, wx.LEFT | wx.TOP, 10)
        self._filter = wx.SearchCtrl(self)
        self._filter.SetName("Filter verbs")
        self._filter.SetHint("Filter by verb name or namespace")
        root.Add(self._filter, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        split = wx.BoxSizer(wx.HORIZONTAL)
        self._verb_list = wx.ListBox(self, style=wx.LB_SINGLE)
        self._verb_list.SetName("Verbs")
        self._verb_list.SetMinSize(wx.Size(220, 180))
        split.Add(self._verb_list, 1, wx.EXPAND | wx.RIGHT, 8)
        self._detail = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self._detail.SetName("Verb details")
        self._detail.SetMinSize(wx.Size(260, 180))
        split.Add(self._detail, 1, wx.EXPAND)
        root.Add(split, 1, wx.EXPAND | wx.ALL, 10)

        edit_row = wx.BoxSizer(wx.HORIZONTAL)
        self._edit_btn = wx.Button(self, label="&Edit announcement...")
        self._order_btn = wx.Button(self, label="Data &order...")
        edit_row.Add(self._edit_btn, 0, wx.RIGHT, 6)
        edit_row.Add(self._order_btn, 0)
        root.Add(edit_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._status = wx.StaticText(self, label="")
        self._status.SetName("Verbosity status")
        root.Add(self._status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.SetSizer(root)

        self._profile.Bind(wx.EVT_RADIOBOX, lambda _e: self._on_profile())
        self._filter.Bind(wx.EVT_TEXT, lambda _e: self._repopulate())
        self._verb_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_verb())
        self._preview_btn.Bind(wx.EVT_BUTTON, lambda _e: self._launch_preview())
        self._history_btn.Bind(wx.EVT_BUTTON, lambda _e: self._launch_history())
        self._library_btn.Bind(wx.EVT_BUTTON, lambda _e: self._launch_library())
        self._safe_btn.Bind(wx.EVT_BUTTON, lambda _e: self._launch_safe_mode())
        self._io_btn.Bind(wx.EVT_BUTTON, lambda _e: self._launch_import_export())
        self._edit_btn.Bind(wx.EVT_BUTTON, lambda _e: self._launch_token_editor())
        self._order_btn.Bind(wx.EVT_BUTTON, lambda _e: self._launch_data_order())

        self._repopulate()
        self._filter.SetFocus()  # power users come here first

    # -- state --------------------------------------------------------------

    @property
    def selected_profile(self):
        return BUILTIN_PROFILES[_PROFILE_NAMES[self._profile.GetSelection()]]

    def channel_mix(self) -> Channel:
        mix = Channel.VISUAL  # always-on floor
        if self._channels["Speech"].GetValue():
            mix |= Channel.SPEECH
        if self._channels["Braille"].GetValue():
            mix |= Channel.BRAILLE
        if self._channels["Sound"].GetValue():
            mix |= Channel.SOUND
        return mix

    def _set_status(self, message: str) -> None:
        self._status.SetLabel(message)
        if message:
            self._announce(message)

    def _on_profile(self) -> None:
        profile = self.selected_profile
        self._set_status(f"Profile {profile.name}. {profile.description}")

    def _filtered_verbs(self):
        needle = self._filter.GetValue().strip().lower()
        if not needle:
            return list(self._verbs)
        return [v for v in self._verbs if needle in v.id.lower() or needle in v.human_name.lower()]

    def _repopulate(self) -> None:
        self._visible = self._filtered_verbs()
        self._verb_list.Clear()
        for verb in self._visible:
            self._verb_list.Append(f"{verb.human_name}  ({verb.id})")
        if self._visible:
            self._verb_list.SetSelection(0)
            self._on_verb()
        else:
            self._detail.SetValue("")

    def _selected_verb(self):
        index = self._verb_list.GetSelection()
        if index < 0 or index >= len(self._visible):
            return None
        return self._visible[index]

    def _on_verb(self) -> None:
        verb = self._selected_verb()
        if verb is None:
            return
        tokens = ", ".join(f"{{{t.name}}}" for t in verb.supported_tokens) or "(none)"
        self._detail.SetValue(
            f"{verb.human_name}\nid: {verb.id}\nfires when: {verb.firing_context}\n"
            f"severity: {verb.severity.value}\ndefault: {verb.default_template}\ntokens: {tokens}"
        )

    def _top_window(self) -> object:
        return self.GetTopLevelParent()

    # -- launchers (lazy imports to keep the panel light) -------------------

    def _launch_preview(self) -> None:
        from quill.core.verbosity.engine import VerbosityEngine
        from quill.ui.verbosity_preview_lab import VerbosityPreviewLabDialog

        engine = VerbosityEngine(self._registry, self.selected_profile)
        VerbosityPreviewLabDialog(self._top_window(), engine, announce_cb=self._announce).show()

    def _launch_history(self) -> None:
        from quill.core.verbosity.history import AnnouncementHistory
        from quill.ui.verbosity_history import VerbosityHistoryDialog

        VerbosityHistoryDialog(
            self._top_window(), AnnouncementHistory(), announce_cb=self._announce
        ).show()

    def _launch_library(self) -> None:
        from quill.ui.verbosity_library import VerbosityLibraryDialog

        VerbosityLibraryDialog(self._top_window(), announce_cb=self._announce).show()

    def _launch_safe_mode(self) -> None:
        from quill.ui.verbosity_safe_mode import VerbositySafeModeDialog

        VerbositySafeModeDialog(self._top_window(), announce_cb=self._announce).show()

    def _launch_import_export(self) -> None:
        from quill.core.verbosity.profiles import CustomProfile
        from quill.ui.verbosity_import_export import VerbosityImportExportDialog

        current = CustomProfile(name=self.selected_profile.name)
        VerbosityImportExportDialog(self._top_window(), current, announce_cb=self._announce).show()

    def _launch_token_editor(self) -> None:
        verb = self._selected_verb()
        if verb is None:
            return
        from quill.ui.verbosity_token_editor import VerbosityTokenEditorDialog

        VerbosityTokenEditorDialog(
            self._top_window(), verb, template=verb.default_template, announce_cb=self._announce
        ).show()

    def _launch_data_order(self) -> None:
        verb = self._selected_verb()
        if verb is None or verb.default_data_order is None:
            self._set_status("This verb has no reorderable fields.")
            return
        from quill.ui.verbosity_data_order import VerbosityDataOrderDialog

        VerbosityDataOrderDialog(
            self._top_window(),
            verb.default_data_order,
            default_fields=verb.default_data_order.fields,
            announce_cb=self._announce,
        ).show()
