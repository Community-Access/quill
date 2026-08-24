"""Recent Problems: the window over :mod:`quill.core.problem_log`.

Announcements are transient by design, which is right until the one you
needed went past while you were in another window. This window is where a
failure that was spoken once still lives: what failed, why, when, and -- when
an app knows how -- a Retry that tries it again (list.md 11.5).

Shared by Quill Radio and QUILL Cast, in the house ListBox pattern: one whole
spoken sentence per row, read-only rows, a Close button bound through the
dialog contract, and every button saying what it does.

**Retry is by kind, not by closure.** Each app registers one handler per kind
it understands (:func:`register_retry`), so a row survives a restart and
still knows how to try again -- a stored callback could not. A row whose kind
nothing claims simply has no Retry, and the button says so rather than
pretending.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core import problem_log
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

TITLE = "Recent Problems"

#: kind -> handler(problem) -> spoken outcome. Registered by each app for the
#: kinds it can actually retry; an unclaimed kind has no Retry.
_RETRY_HANDLERS: dict[str, Callable[[problem_log.Problem], str]] = {}


def register_retry(kind: str, handler: Callable[[problem_log.Problem], str]) -> None:
    """Teach this app how to retry problems of *kind*.

    The handler is given the whole problem (its ``target`` is the handle) and
    returns what to say. Registering twice replaces, so an app that rebuilds
    its frame does not stack handlers.
    """
    _RETRY_HANDLERS[kind] = handler


def clear_retries() -> None:
    """Forget every registered handler (tests, and app shutdown)."""
    _RETRY_HANDLERS.clear()


def can_retry(problem: problem_log.Problem | None) -> bool:
    return problem is not None and problem.kind in _RETRY_HANDLERS


def retry(problem: problem_log.Problem) -> str:
    """Run the registered handler; what to say either way."""
    handler = _RETRY_HANDLERS.get(problem.kind)
    if handler is None:
        return f"Nothing here can retry a {problem.kind} problem."
    try:
        return handler(problem) or f"Retrying {problem.subject or 'it'}."
    except Exception as error:  # noqa: BLE001 - a retry that fails must say so
        return f"Could not retry {problem.subject or 'it'}: {error}."


def show_recent_problems(host: Any) -> None:
    """Open the Recent Problems window. Modal, house pattern."""
    import wx

    from quill.core.paths import app_data_dir

    data_dir = app_data_dir()
    problems = problem_log.load_problems(data_dir)

    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize(wx.Size(760, 460))
    root = wx.BoxSizer(wx.VERTICAL)

    summary_label = wx.StaticText(dialog, label=problem_log.summary(problems))
    root.Add(summary_label, 0, wx.ALL, 8)
    root.Add(wx.StaticText(dialog, label="&What has failed recently:"), 0, wx.LEFT | wx.RIGHT, 8)
    listbox = wx.ListBox(dialog, choices=[p.row_label() for p in problems], style=wx.LB_SINGLE)
    listbox.SetName(
        "Everything that failed recently, newest first: what it was, why it "
        "failed, and when. Nothing here is sent anywhere."
    )
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)

    row_sizer = wx.BoxSizer(wx.HORIZONTAL)
    retry_btn = wx.Button(dialog, label="&Retry")
    retry_btn.SetHelpText(
        "Tries the highlighted row again -- re-reads the feed, re-queues the "
        "download, reconnects the stream. Available only for rows this app "
        "knows how to retry."
    )
    copy_btn = wx.Button(dialog, label="&Copy All")
    copy_btn.SetHelpText(
        "Copies the whole list as text, for a bug report. It contains addresses "
        "and error messages, never passwords."
    )
    clear_btn = wx.Button(dialog, label="C&lear List")
    clear_btn.SetHelpText(
        "Empties the list. It does not fix anything and does not stop the "
        "problems being recorded again next time they happen."
    )
    close_btn = wx.Button(dialog, wx.ID_CLOSE, label="Cl&ose")
    close_btn.SetHelpText("Closes Recent Problems. The list is kept.")
    for button in (retry_btn, copy_btn, clear_btn, close_btn):
        row_sizer.Add(button, 0, wx.RIGHT, 6)
    root.Add(row_sizer, 0, wx.ALL, 8)
    apply_modal_ids(dialog, affirmative_id=close_btn.GetId(), escape_id=close_btn.GetId())
    dialog.SetSizer(root)

    live: list[problem_log.Problem] = list(problems)

    def _selected() -> problem_log.Problem | None:
        index = listbox.GetSelection()
        if index == wx.NOT_FOUND or index >= len(live):
            return None
        return live[index]

    def _refresh(*, announce: bool = False) -> None:
        live[:] = problem_log.load_problems(data_dir)
        listbox.Set([p.row_label() for p in live])
        summary_label.SetLabel(problem_log.summary(live))
        if live:
            listbox.SetSelection(0)
        _sync_retry()
        if announce:
            host._announce(problem_log.summary(live))

    def _sync_retry() -> None:
        current = _selected()
        retry_btn.Enable(can_retry(current))
        if current is not None and not can_retry(current):
            # 11.2 applies here too: a dimmed verb says which state dimmed it.
            retry_btn.SetHelpText(f"This app cannot retry a {current.kind} problem from here.")

    def _on_retry(_event: Any) -> None:
        current = _selected()
        if current is None:
            host._announce("No row is selected.")
            return
        if not can_retry(current):
            host._announce(f"Retry: this app cannot retry a {current.kind} problem from here.")
            return
        host._announce(retry(current))

    def _on_copy(_event: Any) -> None:
        text = problem_log.report_text(live)
        copier = getattr(host, "_copy_text", None)
        if callable(copier):
            copier(text)
        else:  # pragma: no cover - every app on the shell has _copy_text
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Close()
        host._announce(f"Copied {len(live)} problem row(s).")

    def _on_clear(_event: Any) -> None:
        removed = problem_log.clear_problems(data_dir)
        _refresh()
        host._announce(f"Cleared {removed} problem row(s).")

    retry_btn.Bind(wx.EVT_BUTTON, _on_retry)
    copy_btn.Bind(wx.EVT_BUTTON, _on_copy)
    clear_btn.Bind(wx.EVT_BUTTON, _on_clear)
    clear_btn.Enable(bool(problems))
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
    listbox.Bind(wx.EVT_LISTBOX, lambda _e: _sync_retry())
    apply_listbox_activation(listbox, _on_retry)
    if problems:
        listbox.SetSelection(0)
    _sync_retry()
    wx.CallAfter(listbox.SetFocus)
    try:
        host._show_modal_dialog(dialog, TITLE)
    finally:
        dialog.Destroy()


class RecentProblemsMixin:
    """The frame's side: one command, and the retry handlers it can offer."""

    def _register_recent_problems_command(self) -> None:
        commands: Any = self.commands  # type: ignore[attr-defined]
        commands.try_register(
            "app.recent_problems",
            "Recent Problems...",
            self.open_recent_problems,
            feature_id="core.app",
        )

    def open_recent_problems(self) -> None:
        show_recent_problems(self)
