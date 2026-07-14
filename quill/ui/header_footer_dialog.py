"""Header/Footer Builder dialog (#892): named presets over a small, fixed
token set -- left/center/right zones for header and footer, an optional
different first page, and a page-numbering style.

Modeled on the other small builder dialogs this session (Insert Image,
Print Studio): a preset picker fills in sensible defaults, editable fields
let you adjust from there, and the whole thing is keyboard-first rather
than a blank canvas.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import wx

from quill.core.header_footer import PRESETS, HeaderFooterSpec, PageNumberStyle
from quill.ui.dialog_contract import set_accessible_name


class HeaderFooterDialog:
    """Choose a preset, then adjust its header/footer zones and options."""

    def __init__(
        self,
        parent: object,
        spec: HeaderFooterSpec | None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._announce = announce_cb or (lambda _msg: None)
        self._result: HeaderFooterSpec | None = None
        self._preset_names = list(PRESETS.keys())

        self.dialog = wx.Dialog(
            parent, title="Header and Footer", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(560, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="&Preset:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._preset_choice = wx.Choice(self.dialog, choices=self._preset_names)
        self._preset_choice.SetName("Header and footer preset")
        root.Add(self._preset_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(self._zone_group("Header", "header"), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        root.Add(
            self._zone_group("Footer", "footer"), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8
        )

        self._first_page_check = wx.CheckBox(self.dialog, label="&Different first page")
        self._first_page_check.SetName("Different first page")
        root.Add(self._first_page_check, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        root.Add(
            self._zone_group("First page header", "first_page_header"),
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        root.Add(
            self._zone_group("First page footer", "first_page_footer"),
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )

        options_row = wx.BoxSizer(wx.HORIZONTAL)
        options_row.Add(
            wx.StaticText(self.dialog, label="Page &number style:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._page_style_choice = wx.Choice(
            self.dialog, choices=["Numeric (1, 2, 3)", "Roman (I, II, III)"]
        )
        self._page_style_choice.SetName("Page number style")
        self._page_style_choice.SetSelection(0)
        options_row.Add(self._page_style_choice, 0, wx.LEFT, 4)
        options_row.Add(
            wx.StaticText(self.dialog, label="&Start numbering at:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
            12,
        )
        self._start_page_ctrl = wx.SpinCtrl(self.dialog, min=1, max=9999, initial=1)
        set_accessible_name(self._start_page_ctrl, "Start page number")
        options_row.Add(self._start_page_ctrl, 0, wx.LEFT, 4)
        root.Add(options_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_save = wx.Button(self.dialog, wx.ID_OK, label="&Save")
        btn_cancel = wx.Button(self.dialog, wx.ID_CANCEL, label="C&ancel")
        btn_row.AddStretchSpacer(1)
        btn_row.Add(self._btn_save, 0, wx.RIGHT, 4)
        btn_row.Add(btn_cancel, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Save",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )

        self._preset_choice.Bind(wx.EVT_CHOICE, self._on_preset_selected)
        self._first_page_check.Bind(wx.EVT_CHECKBOX, self._on_first_page_toggle)
        self._btn_save.Bind(wx.EVT_BUTTON, self._on_save)

        self._load_from_spec(spec or HeaderFooterSpec())
        self._on_first_page_toggle(None)
        self._preset_choice.SetFocus()

    def _zone_group(self, label: str, prefix: str) -> object:
        box = wx.StaticBoxSizer(wx.HORIZONTAL, self.dialog, label)
        for zone, mnemonic in (("left", "&Left"), ("center", "&Center"), ("right", "&Right")):
            column = wx.BoxSizer(wx.VERTICAL)
            column.Add(wx.StaticText(self.dialog, label=f"{mnemonic}:"), 0)
            ctrl = wx.TextCtrl(self.dialog)
            ctrl.SetName(f"{label} {zone}")
            setattr(self, f"_{prefix}_{zone}", ctrl)
            column.Add(ctrl, 0, wx.EXPAND)
            box.Add(column, 1, wx.EXPAND | wx.RIGHT, 6)
        return box

    # -- public API --

    def show(self) -> HeaderFooterSpec | None:
        """Show the dialog modally; return the saved spec, or None if canceled."""
        from quill.ui.dialog_contract import show_modal_dialog

        show_modal_dialog(self.dialog, "Header and Footer")
        return self._result

    def close(self) -> None:
        self.dialog.Destroy()

    # -- internal helpers --

    def _load_from_spec(self, spec: HeaderFooterSpec) -> None:
        self._header_left.SetValue(spec.header_left)
        self._header_center.SetValue(spec.header_center)
        self._header_right.SetValue(spec.header_right)
        self._footer_left.SetValue(spec.footer_left)
        self._footer_center.SetValue(spec.footer_center)
        self._footer_right.SetValue(spec.footer_right)
        self._first_page_check.SetValue(spec.first_page_different)
        self._first_page_header_left.SetValue(spec.first_page_header_left)
        self._first_page_header_center.SetValue(spec.first_page_header_center)
        self._first_page_header_right.SetValue(spec.first_page_header_right)
        self._first_page_footer_left.SetValue(spec.first_page_footer_left)
        self._first_page_footer_center.SetValue(spec.first_page_footer_center)
        self._first_page_footer_right.SetValue(spec.first_page_footer_right)
        self._page_style_choice.SetSelection(
            1 if spec.page_number_style == PageNumberStyle.ROMAN else 0
        )
        self._start_page_ctrl.SetValue(spec.start_page_number)

    def _form_to_spec(self) -> HeaderFooterSpec:
        return HeaderFooterSpec(
            header_left=self._header_left.GetValue(),
            header_center=self._header_center.GetValue(),
            header_right=self._header_right.GetValue(),
            footer_left=self._footer_left.GetValue(),
            footer_center=self._footer_center.GetValue(),
            footer_right=self._footer_right.GetValue(),
            first_page_different=self._first_page_check.GetValue(),
            first_page_header_left=self._first_page_header_left.GetValue(),
            first_page_header_center=self._first_page_header_center.GetValue(),
            first_page_header_right=self._first_page_header_right.GetValue(),
            first_page_footer_left=self._first_page_footer_left.GetValue(),
            first_page_footer_center=self._first_page_footer_center.GetValue(),
            first_page_footer_right=self._first_page_footer_right.GetValue(),
            page_number_style=(
                PageNumberStyle.ROMAN
                if self._page_style_choice.GetSelection() == 1
                else PageNumberStyle.ARABIC
            ),
            start_page_number=self._start_page_ctrl.GetValue(),
        )

    # -- event handlers --

    def _on_preset_selected(self, _event: object) -> None:
        index = self._preset_choice.GetSelection()
        if index == wx.NOT_FOUND:
            return
        preset = PRESETS[self._preset_names[index]]
        first_page_different = self._first_page_check.GetValue()
        self._load_from_spec(replace(preset, first_page_different=first_page_different))
        self._on_first_page_toggle(None)
        self._announce(f"Preset applied: {self._preset_names[index]}")

    def _on_first_page_toggle(self, _event: object) -> None:
        enabled = self._first_page_check.GetValue()
        for ctrl in (
            self._first_page_header_left,
            self._first_page_header_center,
            self._first_page_header_right,
            self._first_page_footer_left,
            self._first_page_footer_center,
            self._first_page_footer_right,
        ):
            ctrl.Enable(enabled)

    def _on_save(self, _event: object) -> None:
        self._result = self._form_to_spec()
        if self.dialog.IsModal():
            self.dialog.EndModal(wx.ID_OK)
