"""Alert Choices: which places Weather Guardian watches, which alerts it tells you
about, and how it tells you.

Keyboard first, and no checkboxes inside list controls: lists here are plain
list boxes with an add-from-a-chooser button and a Remove button, so a screen
reader reads each row as ordinary text. Every control has an accessible name and
authored help. The decisions themselves live in ``quill.core.weather.alert_rules``;
this window only edits an ``AlertChoices`` and a place on/off list, and the Preview
asks the same ``decide`` the live watch uses.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from quill.core.weather import alert_rules as ar
from quill.core.weather import alert_rules_store as store
from quill.core.weather import alert_rules_text as text
from quill.core.weather import monitor, place_watch
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    set_accessible_name,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size
from quill.ui.weather.alert_choices_pages import (
    _AND_ABOVE,
    _PRESET_ORDER,
    _SAMPLES,
    AlertChoicesPages,
)
from quill.ui.weather.alert_choices_places import AlertChoicesPlaces


class AlertChoicesDialog(AlertChoicesPages, AlertChoicesPlaces):
    def __init__(
        self,
        parent: object,
        *,
        data_dir: Path,
        places: list[tuple[str, str]],
        announce_cb: Callable[[str], None] | None = None,
        test_alert_cb: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._data_dir = data_dir
        self._places = places  # (id, label), in saved order
        self._announce = announce_cb or (lambda _m: None)
        self._test_alert = test_alert_cb
        self._saved = False
        self._choices = copy.deepcopy(store.load_choices(data_dir))
        self._config = monitor.load_config(data_dir)
        self._muted = set(self._config.muted_ids)
        self._watches = place_watch.load_watches(data_dir)
        self._sound_paths = dict(self._choices.sounds)
        self._place_rules = dict(self._choices.places)

        self.dialog = wx.Dialog(
            parent, title="Alert Choices", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        self._book = wx.Notebook(self.dialog)
        set_accessible_name(self._book, "Alert choices sections")
        self._book.AddPage(self._build_which(), "Which alerts")
        self._book.AddPage(self._build_places(), "Places")
        self._book.AddPage(self._build_how(), "How you are told")
        self._book.AddPage(self._build_quiet(), "Quiet hours")
        root.Add(self._book, 1, wx.EXPAND | wx.ALL, 8)
        root.Add(self._build_preview(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        ok = wx.Button(self.dialog, wx.ID_OK, "&Save")
        ok.SetHelpText("Save these choices and close. A sentence then says what you chose.")
        row.Add(ok, 0, wx.RIGHT, 6)
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close without changing anything. Escape does the same.")
        row.Add(cancel)
        root.Add(row, 0, wx.EXPAND | wx.ALL, 12)
        self.dialog.SetSizer(root)
        root.SetMinSize(dip_size(self.dialog, 640, 520))
        root.Fit(self.dialog)
        ok.Bind(wx.EVT_BUTTON, lambda _e: self._save())
        bind_close_button(self.dialog, cancel, modeless=False)
        self._load_into_controls()

    # -- state <-> controls ----------------------------------------------------------

    def _load_into_controls(self) -> None:
        c = self._choices
        sel = c.general.selection
        self._preset.SetSelection(_PRESET_ORDER.index(sel.preset))
        self._extreme.SetValue(c.extreme_always)
        clause = sel.custom
        self._cat_list.Set(list(clause.categories))
        self._inc_list.Set(list(clause.events))
        self._skip_list.Set(list(clause.skip_events))
        for kind, box in self._kind_boxes.items():
            box.SetValue(not clause.kinds or kind in clause.kinds)
        for sev, box in self._sev_boxes.items():
            box.SetValue(not clause.severities or sev in clause.severities)
        self._delivery.SetSelection(list(ar.Delivery).index(c.general.delivery))
        for sev, field in self._sound_labels.items():
            field.SetValue(self._sound_paths.get(sev, "") or "Standard alert sound")
        self._quiet_on.SetValue(c.quiet.enabled)
        self._quiet_start.SetValue(c.quiet.start)
        self._quiet_end.SetValue(c.quiet.end)
        self._quiet_extreme.SetValue(c.quiet.extreme_breaks_through)
        self._evt_cat.SetSelection(0)
        self._fill_events()
        self._fill_places()
        self._sync_preset()

    def _sync_preset(self) -> None:
        preset = _PRESET_ORDER[self._preset.GetSelection()]
        self._preset_help.SetLabel(ar.PRESET_HELP[preset])
        for child in self._custom_box.GetStaticBox().GetChildren():
            child.Enable(preset == "custom")

    def _fill_events(self) -> None:
        events = ar.EVENTS_BY_CATEGORY[ar.CATEGORIES[max(0, self._evt_cat.GetSelection())]]
        self._evt.Set(list(events))
        self._evt.SetSelection(0)

    def _add_category(self) -> None:
        name = self._cat_add.GetStringSelection()
        if name and name not in self._cat_list.GetStrings():
            self._cat_list.Append(name)
            self._announce(f"{name} added.")

    def _remove_category(self) -> None:
        self._drop(self._cat_list)

    def _drop(self, box: Any) -> None:
        i = box.GetSelection()
        if i != self._wx.NOT_FOUND:
            name = box.GetString(i)
            box.Delete(i)
            self._announce(f"{name} removed.")

    def _include_event(self) -> None:
        name = self._evt.GetStringSelection()
        if name and name not in self._inc_list.GetStrings():
            self._inc_list.Append(name)
            self._announce(f"{name} will always be included.")

    def _skip_event(self) -> None:
        name = self._evt.GetStringSelection()
        if name and name not in self._skip_list.GetStrings():
            self._skip_list.Append(name)
            self._announce(f"{name} will be skipped.")

    def _apply_shortcut(self) -> None:
        picked = _AND_ABOVE[self._shortcut.GetSelection()][1]
        if picked is None:
            return
        for sev, box in self._sev_boxes.items():
            box.SetValue(sev in picked)
        self._announce("Severities set.")

    def _ask(self, message: str, title: str) -> bool:
        wx = self._wx
        dlg = wx.MessageDialog(
            self.dialog, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )
        try:
            return bool(show_modal_dialog(dlg, title) == wx.ID_YES)
        finally:
            dlg.Destroy()

    def _confirm_extreme(self) -> None:
        if self._extreme.GetValue():
            return
        if not self._ask(
            "If you turn this off, your other choices can hide Extreme alerts too, such as a "
            "tornado warning rated Extreme, and you will not be told about them. They still "
            "appear in the alert list. Turn it off?",
            "Stop always telling you about Extreme alerts?",
        ):
            self._extreme.SetValue(True)

    def _confirm_breakthrough(self) -> None:
        if self._quiet_extreme.GetValue():
            return
        if not self._ask(
            "If you turn this off, nothing is spoken or sounded during quiet hours, not even "
            "an Extreme alert such as a tornado warning. Turn it off?",
            "Silence Extreme alerts during quiet hours?",
        ):
            self._quiet_extreme.SetValue(True)

    # -- sounds ----------------------------------------------------------------------

    def _choose_sound(self, severity: str) -> None:
        wx = self._wx
        dlg = wx.FileDialog(
            self.dialog,
            f"Choose a sound for {severity} alerts",
            wildcard="Sound files (*.wav)|*.wav|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self._sound_paths[severity] = dlg.GetPath()
                self._sound_labels[severity].SetValue(dlg.GetPath())
                self._announce(f"{severity} sound chosen.")
        finally:
            dlg.Destroy()

    def _reset_sound(self, severity: str) -> None:
        self._sound_paths.pop(severity, None)
        self._sound_labels[severity].SetValue("Standard alert sound")
        self._announce(f"Using the standard sound for {severity} alerts.")

    # -- collecting / preview / save ------------------------------------------------------

    def _collect_general(self) -> ar.RuleSet:
        preset = _PRESET_ORDER[self._preset.GetSelection()]
        kinds = [k for k, b in self._kind_boxes.items() if b.GetValue()]
        sevs = [s for s, b in self._sev_boxes.items() if b.GetValue()]
        clause = ar.Clause(
            categories=list(self._cat_list.GetStrings()),
            events=list(self._inc_list.GetStrings()),
            skip_events=list(self._skip_list.GetStrings()),
            kinds=[] if len(kinds) in (0, len(ar.KINDS)) else kinds,
            severities=[] if len(sevs) in (0, len(ar.SEVERITIES)) else sevs,
        )
        delivery = list(ar.Delivery)[self._delivery.GetSelection()]
        return ar.RuleSet(ar.Selection(preset, clause), delivery)

    def collect(self) -> ar.AlertChoices:
        start, end = self._quiet_start.GetValue().strip(), self._quiet_end.GetValue().strip()
        return ar.AlertChoices(
            general=self._collect_general(),
            places=dict(self._place_rules),
            quiet=ar.QuietHours(
                enabled=self._quiet_on.GetValue(),
                start=start if ar.valid_clock(start) else self._choices.quiet.start,
                end=end if ar.valid_clock(end) else self._choices.quiet.end,
                extreme_breaks_through=self._quiet_extreme.GetValue(),
            ),
            extreme_always=self._extreme.GetValue(),
            sounds={s: p for s, p in self._sound_paths.items() if p},
        )

    def _preview(self) -> None:
        event, severity = _SAMPLES[max(0, self._sample.GetSelection())]
        sample = text.sample_alert(event, severity)
        pid, label = self._selected_place_or_first()
        decision = ar.decide(sample, pid, self.collect(), datetime.now().time())
        sentence = text.describe_decision(decision, label)
        self._preview_text.SetValue(sentence)
        self._announce(sentence)

    def _selected_place_or_first(self) -> tuple[str, str]:
        pid = self._selected_place()
        for known, label in self._places:
            if known == pid:
                return known, label
        return self._places[0] if self._places else ("", "")

    def _save(self) -> None:
        wx = self._wx
        for field, name in ((self._quiet_start, "start"), (self._quiet_end, "end")):
            if not ar.valid_clock(field.GetValue().strip()):
                self._announce(
                    f"The quiet hours {name} time must be hours and minutes, like 22:00."
                )
                field.SetFocus()
                return
        choices = self.collect()
        self._config.muted_ids = [pid for pid, _label in self._places if pid in self._muted]
        try:
            store.save_choices(self._data_dir, choices)
            place_watch.save_watches(self._data_dir, self._watches)
            current = monitor.load_config(self._data_dir)
            current.muted_ids = self._config.muted_ids
            monitor.save_config(self._data_dir, current)
        except OSError:
            self._announce(
                "Alert choices were not saved: the data folder could not be written. "
                "Your choices are still in this window."
            )
            return
        self._saved = True
        places = place_watch.summary_sentence(self._places, self._muted, self._watches, self._now())
        self._announce(text.describe_choices(choices, places))
        if self.dialog.IsModal():
            self.dialog.EndModal(wx.ID_OK)

    def show(self) -> bool:
        """Modal; True when saved."""
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Save",
            cancel_id=self._wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        try:
            show_modal_dialog(self.dialog, "Alert Choices", announce=self._announce)
        finally:
            self.dialog.Destroy()
        return self._saved
