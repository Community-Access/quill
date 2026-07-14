"""Context-first 'What can I do here?' menu action (the Concierge).

Surfaces :func:`quill.core.ai.concierge.suggest` at the top of the AI menu: it
reads the live file type, selection, outline, and AI state and offers an ordered,
keyboard-reachable list of the most useful actions for *where the user is*, then
runs the chosen one through the command registry. Built as its own module (not in
the size-budgeted menu / main_frame modules) so neither has to grow, mirroring the
Action Ring / Run Agent helpers in :mod:`quill.ui.agent_editor_host`.
"""

from __future__ import annotations

from typing import Any

from quill.ui.agent_editor_host import _catalog_agents, _cursor_line_col


def _file_type_for(controller: Any) -> str:
    """Best-effort file extension for the open document (lowercased, no dot)."""
    try:
        path = getattr(getattr(controller, "document", None), "path", None)
        if path is not None and "." in str(path):
            return str(path).rsplit(".", 1)[-1].lower()
    except Exception:  # noqa: BLE001 - file type is best-effort context
        return ""
    return ""


def _concierge_context(controller: Any) -> Any:
    """Build the lightweight ConciergeContext from live editor signals."""
    from quill.core.ai.concierge import ConciergeContext
    from quill.core.ai.model_manager import load_ai_enabled

    try:
        has_selection = bool(str(controller.editor.GetStringSelection()))
    except Exception:  # noqa: BLE001 - selection is best-effort context
        has_selection = False
    try:
        headings = len(controller._outline_entries())
    except Exception:  # noqa: BLE001 - outline is best-effort context
        headings = 0
    line, col = _cursor_line_col(getattr(controller, "editor", None))
    return ConciergeContext(
        file_type=_file_type_for(controller),
        has_selection=has_selection,
        outline_headings=headings,
        ai_enabled=load_ai_enabled(),
        cursor_line=line,
        cursor_column=col,
    )


def open_concierge(controller: Any) -> None:
    """Show the context-aware "What can I do here?" action list (the Concierge).

    Suggestions come from :func:`concierge.suggest` over the live context and are
    presented as a native single-choice list; the chosen entry runs its command
    through the registry. Unknown targets are refused with a status message rather
    than raising.
    """
    from quill.core.ai.concierge import suggest

    wx = controller._wx
    suggestions = suggest(_concierge_context(controller), _catalog_agents())
    if not suggestions:
        controller._set_status("No AI suggestions for the current context.")
        return
    labels = [f"{s.label} — {s.reason}" if s.reason else s.label for s in suggestions]
    dlg = wx.SingleChoiceDialog(controller.frame, "What can I do here?", "AI Suggestions", labels)
    try:
        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(dlg)
    except Exception:  # noqa: BLE001 - hardening is best-effort on a native dialog
        pass
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return
        target = suggestions[dlg.GetSelection()].target
    finally:
        dlg.Destroy()
    if controller.commands.get(target) is None:
        controller._set_status("That action is not available right now.")
        return
    controller.commands.run(target)


def append_concierge_action(controller: Any, ai_menu: Any) -> None:
    """Append the context-first 'What can I do here?' item and bind it directly."""
    from quill.core.i18n import _

    wx = controller._wx
    item_id = wx.NewIdRef()
    ai_menu.Append(item_id, _("What can I do &here?..."))
    controller.frame.Bind(wx.EVT_MENU, lambda _e: open_concierge(controller), id=item_id)
