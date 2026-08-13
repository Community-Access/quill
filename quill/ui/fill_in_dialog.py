"""Ask for an expansion's fill-in fields.

One labelled text box per field, in the order the template asks for them, with
the first one focused. Deliberately a plain vertical form: a screen reader reads
label then value down the dialog, Tab moves between them, and Enter accepts --
nothing to explore, nothing to discover.

Shared by QUILL's editor and Quill Inkwell so a template behaves identically
wherever it is used.

Hardened dialog (A11Y-4): exposes show() and close(); callers never touch the
inner wx.Dialog.
"""

from __future__ import annotations

import wx

from quill.core.expansion.fields import FieldSpec
from quill.ui.dialog_contract import apply_modal_ids

#: Above this many fields the form scrolls rather than growing off-screen.
_SCROLL_AFTER = 6


class FillInDialog:
    """Collects one value per field. :attr:`values` is keyed by ``FieldSpec.key``."""

    def __init__(self, parent: object, specs: list[FieldSpec], *, title: str = "Fill In") -> None:
        self._specs = specs
        self._controls: list[wx.TextCtrl] = []

        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(420, min(140 + 46 * len(specs), 480)))

        root = wx.BoxSizer(wx.VERTICAL)
        host: wx.Window = self.dialog
        if len(specs) > _SCROLL_AFTER:
            panel = wx.ScrolledWindow(self.dialog, style=wx.TAB_TRAVERSAL | wx.VSCROLL)
            panel.SetScrollRate(0, 12)
            panel.SetName("Fields")
            host = panel

        grid = wx.FlexGridSizer(cols=2, hgap=8, vgap=8)
        grid.AddGrowableCol(1)
        for spec in specs:
            label = wx.StaticText(host, label=f"{spec.label}:")
            grid.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
            field = wx.TextCtrl(host, value=spec.default, style=wx.TE_PROCESS_ENTER)
            # The visible label and the accessible name agree, so speech and
            # braille match what is on screen.
            field.SetName(spec.label)
            field.Bind(wx.EVT_TEXT_ENTER, self._on_enter)
            grid.Add(field, 1, wx.EXPAND)
            self._controls.append(field)

        if host is self.dialog:
            root.Add(grid, 1, wx.EXPAND | wx.ALL, 12)
        else:
            host.SetSizer(grid)
            root.Add(host, 1, wx.EXPAND | wx.ALL, 12)

        buttons = self.dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            ok_btn = self.dialog.FindWindowById(wx.ID_OK)
            if ok_btn is not None:
                ok_btn.SetLabel("&Insert")
                ok_btn.SetDefault()
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Insert",
            cancel_id=wx.ID_CANCEL,
        )
        if self._controls:
            self._controls[0].SetFocus()
            self._controls[0].SelectAll()

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()

    @property
    def values(self) -> dict[str, str]:
        return {
            spec.key: control.GetValue()
            for spec, control in zip(self._specs, self._controls, strict=False)
        }

    def _on_enter(self, event: wx.CommandEvent) -> None:
        """Enter accepts the form, except when there is another field to fill.

        On any field but the last, Enter moves on -- which is what someone
        filling a short form expects, and it keeps a one-field template to a
        single keystroke.
        """
        control = event.GetEventObject()
        try:
            index = self._controls.index(control)
        except ValueError:
            index = len(self._controls) - 1
        if index < len(self._controls) - 1:
            self._controls[index + 1].SetFocus()
            self._controls[index + 1].SelectAll()
            return
        self.dialog.EndModal(wx.ID_OK)


def prompt_for_fields(
    parent: object,
    expansion: str,
    show_modal: object,
    *,
    title: str = "Fill In",
) -> str | None:
    """Ask for any fields in *expansion* and return it filled, or None.

    Returns *expansion* unchanged when it has no fields, and None when the user
    cancels -- which must leave whatever they typed exactly as it was, so a
    cancelled form costs nothing.

    ``show_modal`` is the host's own modal runner (``_show_modal_dialog``), so
    QUILL and Quill Inkwell both go through their dialog contract rather than
    calling ShowModal here.
    """
    from quill.core.expansion.fields import fill_fields, parse_fields

    specs = parse_fields(expansion)
    if not specs:
        return expansion
    dialog = FillInDialog(parent, specs, title=title)
    try:
        result = show_modal(dialog.dialog, title)  # type: ignore[operator]
        if result != wx.ID_OK:
            return None
        return fill_fields(expansion, dialog.values)
    finally:
        dialog.close()
