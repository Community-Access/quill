"""Rendering the options a source declares, and remembering the answer.

Extracted from :mod:`quill.ui.radio.browse_tree_menu` under GATE-11 (extract,
never rebaseline) as it landed: the menu module was already at its cap, and
this is a self-contained job with one entry point.

The controls are the platform's own -- ``wx.SingleChoiceDialog`` for a choice,
a masked ``wx.TextEntryDialog`` for a secret -- for the reason every prompt in
this tree uses them: they are the dialogs every screen reader already reads
correctly, and they add no surface to the inventory. What is asked, in what
order, and what the answers mean is declared in
:mod:`quill.core.radio.source_options`; a source that wants a setting writes a
tuple there and gets all of this for nothing.
"""

from __future__ import annotations

from typing import Any


def show(dialog: Any, kind: str) -> None:
    """Ask, for each option this source declares, and remember the answer.

    Rendered from the declaration, so a source that wants a setting writes a
    tuple in ``source_options`` and gets this for nothing. The controls are the
    platform's own -- ``wx.SingleChoiceDialog`` for a choice, a masked
    ``wx.TextEntryDialog`` for a secret -- for the reason every prompt in this
    tree uses them: they are the dialogs every screen reader already reads
    correctly, and they add no surface to the inventory.
    """
    from quill.core.radio import source_options

    declared = source_options.options_for(kind)
    if not declared:
        dialog._announce("This source has no options.")
        return
    history = _history(dialog)
    stored = dict(getattr(history, "source_options", {}) or {}) if history is not None else {}
    wx = dialog._wx
    changed = False
    for option in declared:
        current = source_options.value(stored, option.key)
        if getattr(option, "kind", "") == "choice":
            labels = [said for said, _stored in option.choices]
            values = [held for _said, held in option.choices]
            box = wx.SingleChoiceDialog(  # dialog_button_contract: exempt
                getattr(dialog, "_win", None), option.note or option.label, option.label, labels
            )
            if current in values:
                box.SetSelection(values.index(current))
            try:
                if box.ShowModal() != wx.ID_OK:
                    continue
                stored = source_options.with_value(stored, option.key, values[box.GetSelection()])
            finally:
                box.Destroy()
        else:
            box = wx.TextEntryDialog(  # dialog_button_contract: exempt
                getattr(dialog, "_win", None),
                option.note or option.label,
                option.label,
                style=wx.OK | wx.CANCEL | wx.TE_PASSWORD,
            )
            try:
                if box.ShowModal() != wx.ID_OK:
                    continue
                stored = source_options.with_value(stored, option.key, box.GetValue().strip())
            finally:
                box.Destroy()
        changed = True
        dialog._announce(source_options.describe(option.key, stored))
    if not changed:
        return
    source_options.set_current(stored)
    if history is not None:
        history.source_options = dict(stored)
        save = getattr(_host(dialog), "_save_radio_history", None)
        if callable(save):
            try:
                save()
            except Exception:  # noqa: BLE001 - a failed save must not lose the choice
                pass
    # The rows this source produces are built from the option, so the branch it
    # is on is now out of date -- reload it rather than leaving a list that
    # disagrees with the setting that was just changed.
    from quill.ui.radio import browse_refresh

    browse_refresh.reload_source_branch(dialog, kind)


def _host(dialog: Any) -> Any:
    return getattr(dialog, "_download_host", None) or dialog


def _history(dialog: Any) -> Any:
    return getattr(_host(dialog), "_radio_history", None)
