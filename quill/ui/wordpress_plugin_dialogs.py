"""Plugin Fields: the fields a site's plugins add to a page or post (wordpress.md 9.15).

One plain form: an event's start, end and venue, a product's prices and
stock, and an SEO title and description. A field with a length search
engines care about has a line under it that keeps its count, and QUILL says
once when the text goes over that length and once when it comes back under,
because a count changing on a line the person is not on is exactly what a
screen reader does not say (GATE-13 allows it; the count itself is never
announced keystroke by keystroke).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import wx

from quill.core.wordpress.block_catalog import Field
from quill.core.wordpress.plugin_shop_seo import length_note
from quill.ui import wordpress_dialogs as dlg
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.wordpress_dialogs import labelled_row

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


class PluginFieldsDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        purpose: str,
        fields: Sequence[Field],
        limits: Mapping[str, int],
        announce: Callable[[str], None],
        ok_label: str,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(purpose)
        self.fields = list(fields)
        self.controls: list[wx.Window] = []
        self._announce = announce
        self._over: dict[str, bool] = {}
        #: field key -> its read-only length line.
        self.counts: dict[str, wx.TextCtrl] = {}
        sizer = wx.BoxSizer(wx.VERTICAL)
        for f in self.fields:
            if f.kind == "choice":
                combo = wx.Choice(self, choices=list(f.choices))
                combo.SetHelpText(f.help)
                if f.choices:
                    combo.SetSelection(f.values.index(f.value) if f.value in f.values else 0)
                labelled_row(sizer, self, f.label, combo)
                self.controls.append(combo)
                continue
            multiline = f.kind == "multiline"
            edit = wx.TextCtrl(
                self, value=str(f.value or ""), style=wx.TE_MULTILINE if multiline else 0
            )
            edit.SetHelpText(f.help)
            if multiline:
                edit.SetMinSize(dip_size(self, 420, 80))
            labelled_row(sizer, self, f.label, edit)
            self.controls.append(edit)
            limit = limits.get(f.key)
            if limit:
                spoken = f.label.replace("&", "").rstrip(":")
                count = wx.TextCtrl(
                    self,
                    value=length_note(spoken, edit.GetValue(), limit),
                    style=wx.TE_READONLY,
                )
                count.SetHelpText(
                    f"How long the {spoken.lower()} is, against the about {limit} characters "
                    "search engines show. Read only."
                )
                count.SetName(f"{spoken} length")
                self.counts[f.key] = count
                sizer.Add(count, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
                self._over[f.key] = len(edit.GetValue()) > limit
                edit.Bind(
                    wx.EVT_TEXT,
                    lambda _e, k=f.key, e=edit, c=count, n=spoken, m=limit: self._count(
                        k, e, c, n, m
                    ),
                )
        sizer.Add(dlg._buttons(self, ok_label), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)

    def _count(
        self, key: str, edit: wx.TextCtrl, count: wx.TextCtrl, name: str, limit: int
    ) -> None:
        text = edit.GetValue()
        count.SetValue(length_note(name, text, limit))
        over = len(text) > limit
        if over != self._over.get(key, False):
            self._over[key] = over
            self._announce(
                f"{name} is now over {limit} characters."
                if over
                else f"{name} is back within {limit} characters."
            )

    def answers(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for f, control in zip(self.fields, self.controls, strict=True):
            if isinstance(control, wx.Choice):
                index = control.GetSelection()
                out[f.key] = f.values[index] if 0 <= index < len(f.values) else f.value
            elif isinstance(control, wx.TextCtrl):
                out[f.key] = control.GetValue()
        return out


def ask_plugin_fields(
    parent: wx.Window,
    show_modal: dlg.ShowModal,
    *,
    title: str,
    purpose: str,
    fields: Sequence[Field],
    limits: Mapping[str, int],
    announce: Callable[[str], None],
    ok_label: str = "Save to Site",
) -> dict[str, Any] | None:
    """The answers by field key, or None when cancelled."""
    dialog = PluginFieldsDialog(
        parent,
        title=title,
        purpose=purpose,
        fields=fields,
        limits=limits,
        announce=announce,
        ok_label=ok_label,
    )
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        return dialog.answers()
    finally:
        dialog.Destroy()
