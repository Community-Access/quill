"""Download Optional Components dialog (Help menu).

A single, accessible hub that lists every optional, downloadable component with
what is **Installed** versus **Available to download**, a rich description of the
focused component, and — for installed ones — **Test** (prove it works) and
**Remove** (delete QUILL's downloaded copy). Download keeps each component's
tested, progress-reporting flow: the dialog returns the chosen id and the caller
(MainFrame) runs that installer, so there are no stacked download modals. Remove
and Test happen in place and the dialog stays open, refreshing the row.

The status model and all logic are wx-free
(:mod:`quill.core.optional_components`); this module is layout + event routing.
Actions on the focused component are delegated to a small *controller* the caller
supplies (see :class:`ComponentsController`).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, Protocol

from quill.core.optional_components import OptionalComponent, describe_component, manage_target
from quill.ui.dialog_contract import apply_modal_ids, show_message_box


class ComponentsController(Protocol):
    """The host (MainFrame) actions the dialog delegates to for the focused row."""

    def components(self) -> list[OptionalComponent]:
        """The current component list (re-read after an install/remove)."""

    def removable(self, component_id: str) -> bool:
        """True when Remove can delete a QUILL-downloaded copy of this component."""

    def remove(self, component_id: str) -> bool:
        """Remove the component (delete files, reset dependent state). True on success."""

    def test(
        self, component_id: str, *, on_state_change: Callable[[str], None] | None = None
    ) -> None:
        """Prove the component works (play a voice sample / self-test); announces.

        ``on_state_change``, when the component is a voice, reports
        "generating"/"playing"/"idle" so the caller can toggle a Stop button.
        Ignored for non-voice components (engine/tool self-tests run to
        completion quickly and only announce their result)."""

    def stop_test(self, component_id: str) -> None:
        """Cancel an in-progress voice preview started via test()."""

    def is_previewable(self, component_id: str) -> bool:
        """True when test() reports state changes (a voice component)."""

    def manage(self, component_id: str) -> None:
        """Open the component's own management dialog (models / voices)."""


def show_optional_components_picker(
    wx: Any,
    parent: Any,
    show_modal_dialog: Any,
    controller: ComponentsController,
    *,
    preselect: str = "",
) -> str:
    """Show the hub; return a component id to **download**, or "".

    Download closes the dialog and returns the id (the caller runs the installer).
    Remove and Test act in place and keep the dialog open. ``preselect`` focuses
    that row on open (used by the routed prompts / #874 failure points).
    """
    dialog = wx.Dialog(
        parent,
        title="Download Optional Components",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    dialog.SetSize((760, 560))
    sizer = wx.BoxSizer(wx.VERTICAL)

    intro = wx.StaticText(
        dialog,
        label=(
            "Optional components QUILL can download on demand. Everything here is "
            "optional; the base app works without them. Choose one and select Download "
            "to fetch it (checksum-verified, with its own progress). For an installed "
            "component, Test proves it works and Remove deletes QUILL's copy."
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
    listing.AppendColumn("Status", width=150)
    listing.AppendColumn("Size", width=90)
    listing.AppendColumn("Category", width=150)
    sizer.Add(listing, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

    # Rich, read-only, multiline description of the focused component.
    detail = wx.TextCtrl(
        dialog,
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NO_VSCROLL,
        size=(-1, 110),
        name="optional_components_detail",
    )
    sizer.Add(detail, 0, wx.EXPAND | wx.ALL, 10)

    chosen = {"id": ""}
    testing = {"active": False}
    rows: list[OptionalComponent] = []

    def _selected() -> OptionalComponent | None:
        idx = listing.GetFirstSelected()
        return rows[idx] if 0 <= idx < len(rows) else None

    def _populate(comps: list[OptionalComponent], select_id: str = "") -> None:
        """Fill the list from a worker-gathered component list (UI thread)."""
        try:
            rows.clear()
            rows.extend(comps)
            listing.DeleteAllItems()
            for i, comp in enumerate(rows):
                listing.InsertItem(i, comp.name)
                listing.SetItem(i, 1, comp.status_label)
                listing.SetItem(i, 2, comp.size_hint or "—")
                listing.SetItem(i, 3, comp.category)
            target = 0
            if select_id:
                target = next((i for i, c in enumerate(rows) if c.component_id == select_id), 0)
            if rows:
                listing.Select(target)
                listing.Focus(target)
            _sync_controls()
        except RuntimeError:
            # The dialog was closed before the load finished; nothing to fill.
            return

    def _load_async(select_id: str = "") -> None:
        """Gather the component list off the UI thread and then populate.

        The detectors run tool version probes (pandoc/ffmpeg/node) and filesystem
        scans, which stall the dialog if done on open; doing them on a worker lets
        the window appear immediately with a brief "Loading…" state."""
        detail.SetValue("Loading components…")
        for btn in (download_btn, test_btn, remove_btn):
            btn.Enable(False)

        def _work() -> None:
            try:
                comps = controller.components()
            except Exception:  # noqa: BLE001 - never let the worker crash the app
                comps = []
            wx.CallAfter(_populate, comps, select_id)

        threading.Thread(target=_work, daemon=True).start()

    def _sync_controls() -> None:
        comp = _selected()
        if comp is None:
            detail.SetValue("")
            for btn in (download_btn, test_btn, manage_btn, remove_btn):
                btn.Enable(False)
            return
        detail.SetValue(describe_component(comp))
        # Download/Test key off effective_ready, not installed: most components
        # agree, but the Dictation row is "installed" as soon as its engine
        # binary exists even with no model downloaded yet -- Download must stay
        # offered (it resumes the guided picker at the model step) and Test must
        # stay off until the row is truly usable. Manage/Remove still key off
        # installed so Manage Speech Models is reachable in that partial state.
        ready = comp.effective_ready
        download_btn.Enable(not ready)
        download_btn.SetLabel("Installed" if ready else "&Download")
        test_btn.Enable(ready or testing["active"])
        if not testing["active"]:
            test_btn.SetLabel("&Test")
        remove_btn.Enable(comp.installed and controller.removable(comp.component_id))
        # Manage routes to the component's own models/voices dialog when relevant.
        target = manage_target(comp.component_id)
        manage_btn.SetLabel(
            "&Manage models…"
            if target == "models"
            else ("&Manage voices…" if target == "voices" else "&Manage…")
        )
        manage_btn.Enable(comp.installed and target is not None)

    def _on_download(_evt: Any = None) -> None:
        comp = _selected()
        if comp is None or comp.effective_ready:
            return
        chosen["id"] = comp.component_id
        dialog.EndModal(wx.ID_OK)

    def _on_state_change(state: str) -> None:
        testing["active"] = state in ("generating", "playing")
        test_btn.SetLabel("&Stop" if testing["active"] else "&Test")

    def _on_test(_evt: Any = None) -> None:
        comp = _selected()
        if comp is None:
            return
        if testing["active"]:
            controller.stop_test(comp.component_id)
            _on_state_change("idle")
            return
        if not comp.effective_ready:
            return
        if controller.is_previewable(comp.component_id):
            controller.test(comp.component_id, on_state_change=_on_state_change)
        else:
            controller.test(comp.component_id)  # announces its own result

    def _on_remove(_evt: Any = None) -> None:
        comp = _selected()
        if comp is None or not comp.installed:
            return
        if (
            show_message_box(
                f"Remove {comp.name}? This deletes QUILL's downloaded copy and turns "
                "its features back off. You can download it again any time.",
                "Remove Component",
                wx.ICON_QUESTION | wx.YES_NO,
                dialog,
            )
            != wx.YES
        ):
            return
        controller.remove(comp.component_id)  # announces its own result
        _load_async(select_id=comp.component_id)
        listing.SetFocus()

    def _on_manage(_evt: Any = None) -> None:
        comp = _selected()
        if comp is None or not comp.installed or manage_target(comp.component_id) is None:
            return
        controller.manage(comp.component_id)  # opens the models/voices dialog

    listing.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: _sync_controls())
    listing.Bind(wx.EVT_LIST_ITEM_ACTIVATED, _on_download)

    btns = wx.BoxSizer(wx.HORIZONTAL)
    # Download carries wx.ID_OK so Enter downloads the focused row for keyboard
    # users (dialog button-contract). Test/Remove are plain buttons that act in
    # place. Close carries wx.ID_CANCEL (Escape).
    download_btn = wx.Button(
        dialog, wx.ID_OK, label="&Download", name="optional_components_download"
    )
    test_btn = wx.Button(dialog, label="&Test", name="optional_components_test")
    manage_btn = wx.Button(dialog, label="&Manage…", name="optional_components_manage")
    remove_btn = wx.Button(dialog, label="&Remove", name="optional_components_remove")
    close_btn = wx.Button(dialog, wx.ID_CANCEL, label="&Close")
    close_btn.SetDefault()
    download_btn.Bind(wx.EVT_BUTTON, _on_download)
    test_btn.Bind(wx.EVT_BUTTON, _on_test)
    manage_btn.Bind(wx.EVT_BUTTON, _on_manage)
    remove_btn.Bind(wx.EVT_BUTTON, _on_remove)
    btns.AddStretchSpacer()
    for btn in (download_btn, test_btn, manage_btn, remove_btn, close_btn):
        btns.Add(btn, 0, wx.RIGHT, 8)
    sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 10)

    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    _load_async(select_id=preselect)
    wx.CallAfter(listing.SetFocus)
    try:
        show_modal_dialog(dialog, "Download Optional Components")
    finally:
        dialog.Destroy()
    return chosen["id"]
