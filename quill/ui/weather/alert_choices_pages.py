"""The pages of the Alert Choices window: the controls only, no decisions.

Split from ``alert_choices_dialog`` (GATE-11). ``AlertChoicesPages`` is a mixin; the
dialog class supplies the handlers these controls call (``_add_category``,
``_toggle_place`` and so on) and the state they read.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.weather import alert_rules as ar
from quill.ui.dialog_contract import set_accessible_name
from quill.ui.dpi import dip_size

_AND_ABOVE = (
    ("Choose a shortcut...", None),
    ("Extreme only", ("Extreme",)),
    ("Severe and above", ("Extreme", "Severe")),
    ("Moderate and above", ("Extreme", "Severe", "Moderate")),
    ("Every severity", ar.SEVERITIES),
)
_PRESET_ORDER = ("everything", "essentials", "safety", "custom")
_SAMPLES = (
    ("Tornado Warning", "Extreme"),
    ("Severe Thunderstorm Warning", "Severe"),
    ("Flash Flood Watch", "Severe"),
    ("Winter Weather Advisory", "Moderate"),
    ("Heat Advisory", "Moderate"),
    ("Wind Advisory", "Minor"),
    ("Special Weather Statement", "Minor"),
)
_SAME = "Same as everywhere"


class AlertChoicesPages:
    _wx: Any
    dialog: Any
    _book: Any
    _test_alert: Callable[[], None] | None

    # -- building ----------------------------------------------------------------

    def _button(self, parent: Any, label: str, help_text: str, handler: Callable[[], None]) -> Any:
        btn = self._wx.Button(parent, label=label)
        btn.SetHelpText(help_text)
        btn.Bind(self._wx.EVT_BUTTON, lambda _e: handler())
        return btn

    def _place_control(self, parent: Any, sizer: Any, label: str, control: Any, name: str) -> None:
        """Add a labelled control; the caller has already set its help text inline."""
        wx = self._wx
        sizer.Add(wx.StaticText(parent, label=label), 0, wx.LEFT | wx.TOP, 6)
        set_accessible_name(control, name)
        sizer.Add(control, 0, wx.EXPAND | wx.ALL, 6)

    def _build_which(self) -> Any:
        wx = self._wx
        page = wx.ScrolledWindow(self._book)
        page.SetScrollRate(0, 12)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._preset = wx.Choice(page, choices=[ar.PRESET_LABELS[p] for p in _PRESET_ORDER])
        self._preset.SetHelpText(
            "Everything tells you about every alert. Essentials is tornado, severe "
            "thunderstorm and flash flood warnings, and anything Extreme. Safety is all "
            "warnings and the Extreme or Severe watches. Custom lets you choose below."
        )
        self._place_control(
            page,
            sizer,
            "&Which alerts do you want to hear about?",
            self._preset,
            "Which alerts to be told about",
        )
        self._preset_help = wx.StaticText(page, label="")
        sizer.Add(self._preset_help, 0, wx.LEFT | wx.RIGHT, 12)
        self._extreme = wx.CheckBox(page, label="Always tell me about &Extreme alerts")
        set_accessible_name(self._extreme, "Always tell me about Extreme alerts")
        self._extreme.SetHelpText(
            "On by default. An Extreme alert is told to you whatever else you choose here. "
            "Turning it off lets your other choices hide Extreme alerts too."
        )
        sizer.Add(self._extreme, 0, wx.ALL, 8)

        self._custom_box = wx.StaticBoxSizer(wx.VERTICAL, page, "Custom choices")
        inner = self._custom_box.GetStaticBox()
        self._cat_list = wx.ListBox(inner, size=dip_size(inner, 260, 90))
        self._cat_list.SetHelpText(
            "The categories you will be told about. Use the chooser below to add one and "
            "Remove to take the selected one out. Empty means every type."
        )
        self._place_control(
            inner,
            self._custom_box,
            "Alert &types you want, by category:",
            self._cat_list,
            "Chosen alert categories",
        )
        cat_row = wx.BoxSizer(wx.HORIZONTAL)
        self._cat_add = wx.Choice(inner, choices=list(ar.CATEGORIES))
        set_accessible_name(self._cat_add, "Category to add")
        self._cat_add.SetHelpText("Pick a category, then press Add category.")
        cat_row.Add(self._cat_add, 1, wx.RIGHT, 6)
        cat_row.Add(
            self._button(inner, "Add &category", "Add the chosen category.", self._add_category),
            0,
            wx.RIGHT,
            6,
        )
        cat_row.Add(
            self._button(
                inner, "&Remove category", "Remove the selected category.", self._remove_category
            )
        )
        self._custom_box.Add(cat_row, 0, wx.EXPAND | wx.ALL, 6)

        pick_row = wx.BoxSizer(wx.HORIZONTAL)
        self._evt_cat = wx.Choice(inner, choices=list(ar.CATEGORIES))
        set_accessible_name(self._evt_cat, "Category of the specific alert type")
        self._evt_cat.SetHelpText("Choose a category to list its alert types.")
        self._evt_cat.Bind(wx.EVT_CHOICE, lambda _e: self._fill_events())
        self._evt = wx.Choice(inner)
        set_accessible_name(self._evt, "Specific alert type")
        self._evt.SetHelpText(
            "Pick one alert type, then choose whether to always include or skip it."
        )
        pick_row.Add(self._evt_cat, 1, wx.RIGHT, 6)
        pick_row.Add(self._evt, 1)
        self._custom_box.Add(
            wx.StaticText(inner, label="Specific alert types:"), 0, wx.LEFT | wx.TOP, 6
        )
        self._custom_box.Add(pick_row, 0, wx.EXPAND | wx.ALL, 6)
        btns = wx.BoxSizer(wx.HORIZONTAL)
        btns.Add(
            self._button(
                inner,
                "&Include this type",
                "Tell me about this type even when its category is not chosen.",
                self._include_event,
            ),
            0,
            wx.RIGHT,
            6,
        )
        btns.Add(
            self._button(
                inner,
                "&Skip this type",
                "Never tell me about this type, even when its category is chosen.",
                self._skip_event,
            )
        )
        self._custom_box.Add(btns, 0, wx.ALL, 6)
        self._inc_list = wx.ListBox(inner, size=dip_size(inner, 260, 60))
        self._inc_list.SetHelpText("Alert types you asked to always hear about.")
        self._place_control(
            inner,
            self._custom_box,
            "Types always included:",
            self._inc_list,
            "Specific alert types always included",
        )
        self._skip_list = wx.ListBox(inner, size=dip_size(inner, 260, 60))
        self._skip_list.SetHelpText("Alert types you asked never to hear about.")
        self._place_control(
            inner,
            self._custom_box,
            "Types skipped:",
            self._skip_list,
            "Specific alert types skipped",
        )
        rm = wx.BoxSizer(wx.HORIZONTAL)
        rm.Add(
            self._button(
                inner,
                "Remove from inc&luded",
                "Remove the selected included type.",
                lambda: self._drop(self._inc_list),
            ),
            0,
            wx.RIGHT,
            6,
        )
        rm.Add(
            self._button(
                inner,
                "Remove from s&kipped",
                "Remove the selected skipped type.",
                lambda: self._drop(self._skip_list),
            )
        )
        self._custom_box.Add(rm, 0, wx.ALL, 6)

        self._kind_boxes: dict[str, Any] = {}
        kinds = wx.StaticBoxSizer(wx.HORIZONTAL, inner, "Kinds")
        for kind in ar.KINDS:
            box = wx.CheckBox(kinds.GetStaticBox(), label=ar.KIND_LABELS[kind])
            set_accessible_name(box, f"Include {ar.KIND_LABELS[kind].lower()}")
            box.SetHelpText(f"Tell me about {ar.KIND_LABELS[kind].lower()}.")
            kinds.Add(box, 0, wx.ALL, 6)
            self._kind_boxes[kind] = box
        self._custom_box.Add(kinds, 0, wx.EXPAND | wx.ALL, 6)
        self._sev_boxes: dict[str, Any] = {}
        sevs = wx.StaticBoxSizer(wx.HORIZONTAL, inner, "Severity")
        for sev in ar.SEVERITIES:
            box = wx.CheckBox(sevs.GetStaticBox(), label=sev)
            set_accessible_name(box, f"Include {sev} severity")
            box.SetHelpText(f"Tell me about alerts the National Weather Service rates {sev}.")
            sevs.Add(box, 0, wx.ALL, 6)
            self._sev_boxes[sev] = box
        self._shortcut = wx.Choice(sevs.GetStaticBox(), choices=[label for label, _v in _AND_ABOVE])
        set_accessible_name(self._shortcut, "This severity and above")
        self._shortcut.SetHelpText(
            "A shortcut that selects this severity and every more serious one."
        )
        self._shortcut.Bind(wx.EVT_CHOICE, lambda _e: self._apply_shortcut())
        sevs.Add(self._shortcut, 0, wx.ALL, 6)
        self._custom_box.Add(sevs, 0, wx.EXPAND | wx.ALL, 6)
        sizer.Add(self._custom_box, 0, wx.EXPAND | wx.ALL, 6)
        page.SetSizer(sizer)
        self._preset.Bind(wx.EVT_CHOICE, lambda _e: self._sync_preset())
        self._extreme.Bind(wx.EVT_CHECKBOX, lambda _e: self._confirm_extreme())
        return page

    def _build_how(self) -> Any:
        wx = self._wx
        page = wx.Panel(self._book)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._delivery = wx.Choice(page, choices=[ar.DELIVERY_LABELS[d] for d in ar.Delivery])
        self._delivery.SetHelpText(
            "As before interrupts for urgent alerts and speaks the rest. Alerts you did not "
            "choose are never lost: they stay in the alert list and in Alert Feed Status."
        )
        self._place_control(
            page,
            sizer,
            "&How should an alert you chose be delivered?",
            self._delivery,
            "How chosen alerts are delivered",
        )
        sizer.Add(
            wx.StaticText(page, label="Alert sound for each severity:"), 0, wx.LEFT | wx.TOP, 8
        )
        self._sound_labels: dict[str, Any] = {}
        for sev in ar.SEVERITIES:
            row = wx.BoxSizer(wx.HORIZONTAL)
            row.Add(
                wx.StaticText(page, label=f"{sev}:", size=dip_size(page, 80, -1)),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
                8,
            )
            field = wx.TextCtrl(page, style=wx.TE_READONLY, size=dip_size(page, 260, -1))
            set_accessible_name(field, f"Sound for {sev} alerts")
            field.SetHelpText(
                "The sound file for this severity. The standard alert sound when empty."
            )
            self._sound_labels[sev] = field
            row.Add(field, 1, wx.RIGHT, 6)
            row.Add(
                self._button(
                    page,
                    f"Choose {sev} sound...",
                    f"Choose a .wav file for {sev} alerts.",
                    lambda s=sev: self._choose_sound(s),
                ),
                0,
                wx.RIGHT,
                6,
            )
            row.Add(
                self._button(
                    page,
                    f"Standard {sev}",
                    f"Use the standard alert sound for {sev} alerts.",
                    lambda s=sev: self._reset_sound(s),
                )
            )
            sizer.Add(row, 0, wx.EXPAND | wx.TOP, 6)
        page.SetSizer(sizer)
        return page

    def _build_quiet(self) -> Any:
        wx = self._wx
        page = wx.Panel(self._book)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._quiet_on = wx.CheckBox(page, label="Use &quiet hours")
        set_accessible_name(self._quiet_on, "Use quiet hours")
        self._quiet_on.SetHelpText(
            "During quiet hours Weather Guardian does not speak or sound alerts below Extreme. "
            "They stay in the alert list."
        )
        sizer.Add(self._quiet_on, 0, wx.ALL, 8)
        self._quiet_start = wx.TextCtrl(page)
        self._quiet_start.SetHelpText("When quiet hours begin, as hours and minutes.")
        self._place_control(
            page,
            sizer,
            "&Start (24-hour, like 22:00):",
            self._quiet_start,
            "Quiet hours start time",
        )
        self._quiet_end = wx.TextCtrl(page)
        self._quiet_end.SetHelpText("When quiet hours end, as hours and minutes.")
        self._place_control(
            page, sizer, "&End (24-hour, like 07:00):", self._quiet_end, "Quiet hours end time"
        )
        self._quiet_extreme = wx.CheckBox(
            page, label="Let &Extreme alerts break through quiet hours"
        )
        set_accessible_name(self._quiet_extreme, "Let Extreme alerts break through quiet hours")
        self._quiet_extreme.SetHelpText(
            "On by default. Turned off, nothing at all is spoken during quiet hours, Extreme "
            "tornado warnings included."
        )
        self._quiet_extreme.Bind(wx.EVT_CHECKBOX, lambda _e: self._confirm_breakthrough())
        sizer.Add(self._quiet_extreme, 0, wx.ALL, 8)
        page.SetSizer(sizer)
        return page

    def _build_preview(self) -> Any:
        wx = self._wx
        box = wx.StaticBoxSizer(wx.VERTICAL, self.dialog, "Preview")
        inner = box.GetStaticBox()
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._sample = wx.Choice(inner, choices=[f"{e} ({s})" for e, s in _SAMPLES])
        set_accessible_name(self._sample, "Sample alert to preview")
        self._sample.SetHelpText("A sample alert. Preview says what your choices would do with it.")
        self._sample.SetSelection(0)
        row.Add(self._sample, 1, wx.RIGHT, 6)
        row.Add(
            self._button(
                inner,
                "&Preview",
                "Say in one sentence what would happen to the sample alert.",
                self._preview,
            ),
            0,
            wx.RIGHT,
            6,
        )
        if self._test_alert is not None:
            row.Add(
                self._button(
                    inner,
                    "&Test Alert",
                    "Play the whole alert experience, marked as a test.",
                    self._test_alert,
                )
            )
        box.Add(row, 0, wx.EXPAND | wx.ALL, 6)
        self._preview_text = wx.TextCtrl(
            inner, style=wx.TE_MULTILINE | wx.TE_READONLY, size=dip_size(inner, -1, 48)
        )
        set_accessible_name(self._preview_text, "What would happen to the sample alert")
        self._preview_text.SetHelpText("The result of Preview, in one sentence.")
        box.Add(self._preview_text, 0, wx.EXPAND | wx.ALL, 6)
        return box
