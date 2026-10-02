"""Activity: every result this app produced this session, and what you can do about each.

The window over :mod:`quill.core.activity` (qc.md F-10, 7.2 and 7.5). Recent
Problems keeps *failures* across restarts; Activity keeps *everything* that
happened in this session -- saves, refreshes, imports, things that finished
after you closed the window that started them -- with the next actions each
result offers: Retry, Undo, Open, Open Folder. A result spoken while you were
in another window is not gone; it is here, with its buttons.

Shared by every app (QUILL, QUILL Lite, and every app on the shell). The house
ListBox pattern: one whole sentence per row, a details pane, buttons that say
what they do and are dimmed (with the reason as their help) when the selected
row does not offer them. Focus returns to the same result by identity after
the list changes (:func:`quill.core.activity.restore_index`).

**Next actions are closures, kept for this session only.** A result's Retry is
the code that can try *that* write again, which cannot survive a restart --
that is what Recent Problems' retry-by-kind is for. :func:`report_result`
registers them; an evicted result's closures go with it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core import activity
from quill.core.activity import ActionResult

TITLE = "Activity"

#: (operation id, action id) -> callable returning the sentence to say.
_ACTIONS: dict[tuple[str, str], Callable[[], str | None]] = {}


def register_actions(result: ActionResult, actions: dict[str, Callable[[], str | None]]) -> None:
    """Keep *result*'s next-action callables, by its operation id."""
    for action_id, handler in actions.items():
        _ACTIONS[(result.operation_id, action_id)] = handler
    # Bounded with the log: drop closures whose result has been evicted.
    live = {r.operation_id for r in activity.LOG.recent()}
    for key in [key for key in _ACTIONS if key[0] not in live]:
        del _ACTIONS[key]


def can_run(result: ActionResult | None, action_id: str) -> bool:
    return (
        result is not None
        and result.has(action_id)
        and (result.operation_id, action_id) in _ACTIONS
    )


def run_action(result: ActionResult, action_id: str) -> str:
    """Run one next action; what to say either way. Never raises."""
    handler = _ACTIONS.get((result.operation_id, action_id))
    label = next((a.label for a in result.next_actions if a.id == action_id), action_id)
    if handler is None:
        return f"{label} is not available for this result any more."
    try:
        return handler() or f"{label}: done."
    except Exception as error:  # noqa: BLE001 - an action that fails must say so
        return f"{label} did not work: {error}."


def report_result(
    host: Any,
    result: ActionResult,
    actions: dict[str, Callable[[], str | None]] | None = None,
) -> ActionResult:
    """Record *result*, keep its actions, and say it if it is to be said.

    The one call a feature makes when something finishes. Speech goes through
    the host's own ``_announce`` (so verbosity, braille, earcons and the
    transcript all apply); a ``review`` result is only recorded.
    """
    activity.LOG.record(result)
    if actions:
        register_actions(result, actions)
    if result.importance == activity.SPEAK:
        announce = getattr(host, "_announce", None)
        if callable(announce):
            announce(result.spoken())
    return result


def repeat_last_result(host: Any) -> str:
    """Say the newest important result again, with what can be done about it."""
    latest = activity.LOG.latest_important()
    if latest is None:
        said = "Nothing to repeat yet: no result has been reported in this session."
    else:
        said = latest.spoken()
        offered = [a.label for a in latest.next_actions if can_run(latest, a.id)]
        if offered:
            said += " Activity offers " + ", ".join(offered) + "."
    host._announce(said)
    return said


#: The buttons, in order: (action id, label, help when available).
_BUTTONS = (
    (activity.RETRY.id, "&Retry", "Tries the selected action again, the same way."),
    (activity.UNDO.id, "&Undo", "Undoes the selected action, if it can still be undone."),
    (activity.OPEN.id, "O&pen", "Opens what the selected action made or changed."),
    (
        activity.OPEN_FOLDER.id,
        "Open &Folder",
        "Opens the folder involved -- for a failed save, the folder the file "
        "lives in, so you can see whether the disk is full or the folder is "
        "read only.",
    ),
)


def show_activity(host: Any) -> None:
    """Open the Activity window. Modal, house pattern; changes nothing by itself."""
    import wx

    from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

    results = activity.LOG.recent()
    parent = getattr(host, "frame", None) or getattr(host, "_ai_parent", lambda: None)()
    dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize(wx.Size(760, 520))
    root = wx.BoxSizer(wx.VERTICAL)

    summary_label = wx.StaticText(dialog, label=activity.summary_sentence(results))
    root.Add(summary_label, 0, wx.ALL, 8)
    root.Add(wx.StaticText(dialog, label="&What happened:"), 0, wx.LEFT | wx.RIGHT, 8)
    listbox = wx.ListBox(dialog, choices=[r.row() for r in results], style=wx.LB_SINGLE)
    listbox.SetHelpText(
        "Everything this app reported in this session, newest first: whether it "
        "worked, what it was, and when. Problems stay here after they were "
        "spoken. Nothing here is sent anywhere."
    )
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)

    root.Add(wx.StaticText(dialog, label="&Details:"), 0, wx.LEFT | wx.RIGHT, 8)
    details = wx.TextCtrl(
        dialog, size=(-1, 110), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP
    )
    details.SetHelpText(
        "Everything about the selected result: the full sentence, the reason, "
        "when it happened and what you can do. Read only."
    )
    root.Add(details, 0, wx.EXPAND | wx.ALL, 8)

    row = wx.BoxSizer(wx.HORIZONTAL)
    buttons: dict[str, Any] = {}
    for action_id, label, help_text in _BUTTONS:
        button = wx.Button(dialog, label=label)
        button.SetHelpText(help_text)
        buttons[action_id] = button
        row.Add(button, 0, wx.RIGHT, 6)
    copy_btn = wx.Button(dialog, label="&Copy Details")
    copy_btn.SetHelpText("Copies the selected result's details as text, for a support message.")
    clear_btn = wx.Button(dialog, label="C&lear List")
    clear_btn.SetHelpText(
        "Empties this session's list. Recent Problems keeps its own record of failures."
    )
    close_btn = wx.Button(dialog, wx.ID_CLOSE, label="Close")
    close_btn.SetHelpText("Closes Activity. The list is kept for this session.")
    for button in (copy_btn, clear_btn, close_btn):
        row.Add(button, 0, wx.RIGHT, 6)
    root.Add(row, 0, wx.ALL, 8)
    dialog.SetSizer(root)
    apply_modal_ids(dialog, affirmative_id=close_btn.GetId(), escape_id=close_btn.GetId())

    live: list[ActionResult] = list(results)

    def _selected() -> ActionResult | None:
        index = listbox.GetSelection()
        if index == wx.NOT_FOUND or index >= len(live):
            return None
        return live[index]

    def _sync() -> None:
        current = _selected()
        details.SetValue(current.details_text() if current is not None else "")
        for action_id, button in buttons.items():
            available = can_run(current, action_id)
            button.Enable(available)
        copy_btn.Enable(current is not None)
        clear_btn.Enable(bool(live))

    def _refill(keep: str | None, previous: int) -> None:
        live[:] = activity.LOG.recent()
        listbox.Set([r.row() for r in live])
        summary_label.SetLabel(activity.summary_sentence(live))
        index = activity.restore_index([r.operation_id for r in live], keep, previous)
        if index >= 0:
            listbox.SetSelection(index)
        _sync()

    def _run(action_id: str) -> None:
        current = _selected()
        if current is None:
            host._announce("No result is selected.")
            return
        if not can_run(current, action_id):
            return
        previous = listbox.GetSelection()
        host._announce(run_action(current, action_id))
        _refill(current.operation_id, previous)

    def _default_action(_event: Any) -> None:
        current = _selected()
        if current is None:
            return
        for action_id, _label, _help in _BUTTONS:
            if can_run(current, action_id):
                _run(action_id)
                return
        details.SetFocus()

    def _on_copy(_event: Any) -> None:
        current = _selected()
        if current is None:
            return
        text = current.details_text()
        copier = getattr(host, "_copy_text", None)
        if callable(copier):
            copier(text)
        elif wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        host._announce("Details copied.")

    def _on_clear(_event: Any) -> None:
        removed = activity.LOG.clear()
        _refill(None, -1)
        host._announce(f"Cleared {removed} result(s).")

    for action_id, button in buttons.items():
        button.Bind(wx.EVT_BUTTON, lambda _e, a=action_id: _run(a))
    copy_btn.Bind(wx.EVT_BUTTON, _on_copy)
    clear_btn.Bind(wx.EVT_BUTTON, _on_clear)
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
    listbox.Bind(wx.EVT_LISTBOX, lambda _e: _sync())
    apply_listbox_activation(listbox, _default_action)
    if live:
        listbox.SetSelection(0)
    _sync()
    wx.CallAfter(listbox.SetFocus)
    try:
        shower = getattr(host, "_show_modal_dialog", None)
        if callable(shower):
            shower(dialog, TITLE)
        else:  # pragma: no cover - every host has one
            from quill.ui.dialog_contract import show_modal_dialog

            show_modal_dialog(dialog, TITLE, announce=getattr(host, "_announce", None))
    finally:
        dialog.Destroy()


class ActivityMixin:
    """The frame's side: two commands, and the one call features make."""

    def _register_activity_commands(self) -> None:
        commands: Any = self.commands  # type: ignore[attr-defined]
        binding_for = getattr(self, "_binding_for", None)
        for command_id, label, handler in (
            ("app.activity", "Activity...", self.open_activity),
            ("app.repeat_last_result", "Repeat Last Result", self.repeat_last_result),
        ):
            commands.try_register(
                command_id,
                label,
                handler,
                keybinding=binding_for(command_id) if callable(binding_for) else None,
                feature_id="core.app",
            )

    def open_activity(self) -> None:
        show_activity(self)

    def repeat_last_result(self) -> None:
        repeat_last_result(self)

    def report_result(
        self,
        result: ActionResult,
        actions: dict[str, Callable[[], str | None]] | None = None,
    ) -> ActionResult:
        return report_result(self, result, actions)


__all__ = [
    "TITLE",
    "ActivityMixin",
    "can_run",
    "register_actions",
    "repeat_last_result",
    "report_result",
    "run_action",
    "show_activity",
]
