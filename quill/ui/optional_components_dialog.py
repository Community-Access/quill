"""Download Optional Components dialog (Help menu).

A single, accessible touch point that lists every optional, downloadable component
(offline speech engine, neural/classic voices, the audio-export helper, and
non-English spell-check dictionaries) with what is **Installed** versus **Available
to download**, so a user never has to hunt through scattered menus to find or fetch
them (footprint plan §10.2.5).

The status model is the wx-free :func:`quill.core.optional_components.gather_optional_components`.
Each component's actual download keeps its own tested, progress-reporting flow; to
avoid stacking modal dialogs, this picker simply *returns the chosen component id*
and the caller (MainFrame) runs that component's installer after the picker closes.
"""

from __future__ import annotations

from typing import Any

from quill.core.optional_components import OptionalComponent


def show_optional_components_picker(
    wx: Any,
    parent: Any,
    components: list[OptionalComponent],
    show_modal_dialog: Any,
) -> str:
    """Show the picker; return the chosen component id to download, or "".

    Returns the ``component_id`` the user activated (Download / Enter / double
    click) for a not-yet-installed component, or an empty string if they closed
    the dialog or chose an already-installed row.
    """
    dialog = wx.Dialog(
        parent,
        title="Download Optional Components",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    dialog.SetSize((720, 520))
    sizer = wx.BoxSizer(wx.VERTICAL)

    intro = wx.StaticText(
        dialog,
        label=(
            "Optional components QUILL can download on demand. Everything here is "
            "optional; the base app works without them. Choose a component and select "
            "Download to fetch it (checksum-verified, with its own progress)."
        ),
        name="optional_components_intro",
    )
    sizer.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

    listing = wx.ListCtrl(
        dialog,
        style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES,
        name="optional_components_list",
    )
    listing.AppendColumn("Component", width=300)
    listing.AppendColumn("Status", width=170)
    listing.AppendColumn("Size", width=90)
    listing.AppendColumn("Category", width=140)
    for i, comp in enumerate(components):
        listing.InsertItem(i, comp.name)
        listing.SetItem(i, 1, comp.status_label)
        listing.SetItem(i, 2, comp.size_hint or "—")
        listing.SetItem(i, 3, comp.category)
    if components:
        listing.Select(0)
        listing.Focus(0)
    sizer.Add(listing, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

    detail = wx.StaticText(dialog, label="", name="optional_components_detail")
    sizer.Add(detail, 0, wx.EXPAND | wx.ALL, 10)

    chosen = {"id": ""}

    def _selected() -> OptionalComponent | None:
        idx = listing.GetFirstSelected()
        return components[idx] if 0 <= idx < len(components) else None

    def _update_detail() -> None:
        comp = _selected()
        if comp is None:
            detail.SetLabel("")
            return
        bits = [comp.description]
        if comp.note:
            bits.append(comp.note)
        bits.append("Already installed." if comp.installed else "Not installed yet.")
        detail.SetLabel(" ".join(bits))

    def _activate(_evt: Any = None) -> None:
        comp = _selected()
        if comp is None:
            return
        if comp.installed:
            detail.SetLabel(f"{comp.name} is already installed.")
            return
        chosen["id"] = comp.component_id
        dialog.EndModal(wx.ID_OK)

    listing.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: _update_detail())
    listing.Bind(wx.EVT_LIST_ITEM_ACTIVATED, _activate)
    _update_detail()

    btns = wx.BoxSizer(wx.HORIZONTAL)
    # The affirmative button carries wx.ID_OK so Enter works for keyboard/blind
    # users (dialog button-contract). Its bound handler decides whether to close
    # (download a not-yet-installed component) or stay (already installed); it does
    # not call event.Skip(), so the default auto-close never fires unexpectedly.
    download_btn = wx.Button(
        dialog, wx.ID_OK, label="&Download", name="optional_components_download"
    )
    close_btn = wx.Button(dialog, wx.ID_CANCEL, label="&Close")
    close_btn.SetDefault()
    download_btn.Bind(wx.EVT_BUTTON, _activate)
    btns.AddStretchSpacer()
    btns.Add(download_btn, 0, wx.RIGHT, 8)
    btns.Add(close_btn, 0)
    sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 10)

    dialog.SetSizer(sizer)
    from quill.ui.dialog_contract import apply_modal_ids

    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    wx.CallAfter(listing.SetFocus)
    try:
        show_modal_dialog(dialog, "Download Optional Components")
    finally:
        dialog.Destroy()
    return chosen["id"]
