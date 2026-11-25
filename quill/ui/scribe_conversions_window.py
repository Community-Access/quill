"""Conversions on This Computer: the family queue, in a modeless window (PRD 7.4, 12).

Each app shows its own instance, read from the shared queue file (refreshed
on the runner's events and every two seconds, for jobs another app runs).
Several files chosen together run one after another on their own (the
exception Pneuma approved on 2026-11-21), so there is no Send Next File.

* A report-view ``wx.ListCtrl`` (File, Formats, Stage), one row per job. A
  row's text changes only when its stage changes; rows update in place and
  are never rebuilt, sorted or scrolled, so focus stays where the person left
  it (FUX-06). Percent, estimated time and the full latest message are in the
  Details field below, which is not rewritten while it has focus.
* Enter opens the result, Delete removes the row, the Applications key or
  Shift+F10 opens every job command; the same commands are buttons.
* The modeless-window contract: a title, Escape closes it and returns focus
  to where it was opened from, F1 answers, and an update never steals focus.

Stage changes are spoken by the controller, once, through the announcement
service -- also when the changed job is the focused row, because an in-place
``SetItem`` is not re-read by NVDA, JAWS or Narrator (accessibility review,
2026-11-20).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import wx

from quill.core.scribe import queue as q
from quill.core.scribe.model import formats_phrase
from quill.core.scribe.sentences import time_left_words
from quill.ui.dialog_contract import bind_close_button, show_modeless_surface

TITLE = "Conversions on This Computer"
EMPTY = "No Scribe for Documents conversions."

#: (label, method, needs a job) -- buttons and the context menu, one table.
COMMANDS: tuple[tuple[str, str], ...] = (
    ("&Open Result", "open_result"),
    # PRD 8.1.7: what can be done next with what was made, chosen by the person.
    ("Nex&t Steps...", "next_steps"),
    ("Open &Folder", "open_folder"),
    ("Ca&ncel Waiting", "cancel_waiting"),
    ("&Retry", "retry"),
    ("&Buy Pages", "buy_pages"),
    ("Enter &Password...", "enter_password"),
    ("Sign &In...", "sign_in"),
    ("Ask for &Human Review...", "ask_review"),
    ("&Copy Details", "copy_details"),
    ("Remo&ve from List", "remove"),
)


def job_details(job: q.Job, now: float | None = None) -> str:
    """The Details field: everything about a job, re-readable. A job Scribe
    asked to slow down shows, silently, how long until it tries again."""
    lines = [f"{job.display_name}: {job.state_words}."]
    if job.state == q.BUSY and job.not_before > (time.time() if now is None else now):
        # A clock time stays true while the field is being read (it is not rewritten then).
        at = time.strftime("%H:%M:%S", time.localtime(job.not_before))
        lines.append(f"Trying again at {at}.")
    if job.formats:
        lines.append(f"Formats: {formats_phrase(job.formats)}.")
    percent = int(round(job.progress * 100))
    if job.state not in q.FINISHED or percent:
        lines.append(f"Progress: {percent} percent.")
    if job.state == q.CONVERTING and job.eta_seconds:
        lines.append(time_left_words(job.eta_seconds).capitalize() + ".")
    if job.message:
        lines.append(f"Latest: {job.message}")
    if job.outputs:
        lines.append("Made: " + "; ".join(str(p) for p in job.outputs.values()))
    if job.folder:
        lines.append(f"Folder: {job.folder}")
    if job.error_code:
        lines.append(f"Code: {job.error_code}")
    return "\n".join(lines)


class ScribeConversionsWindow(wx.Frame):
    #: Stage feedback, when chosen, plays while this window is in front
    #: (quill.core.scribe.feedback.SCRIBE_WINDOW_ATTR).
    is_scribe_window = True

    def __init__(self, parent: Any, controller: Any) -> None:
        super().__init__(parent, title=TITLE, style=wx.DEFAULT_FRAME_STYLE)
        self.SetName("scribe_conversions_window")  # F1 finds its topic by this name (topics.json)
        self._controller = controller
        self._opener: Any = None
        self._ids: list[str] = []
        self._stages: dict[str, str] = {}

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(panel, label="Conv&ersions:"), 0, wx.LEFT | wx.TOP, 6)
        self.list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.InsertColumn(0, "File", width=self.FromDIP(220))
        self.list.InsertColumn(1, "Formats", width=self.FromDIP(200))
        self.list.InsertColumn(2, "Stage", width=self.FromDIP(220))
        self.list.SetHelpText(
            "Every Scribe for Documents job on this computer, from every QUILL app. Enter opens "
            "the result, Delete removes the row, the Applications key lists every command."
        )
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 6)
        self.empty_label = wx.StaticText(panel, label="Status:")
        sizer.Add(self.empty_label, 0, wx.LEFT, 6)
        self.empty = wx.TextCtrl(panel, style=wx.TE_READONLY, value=EMPTY)
        self.empty.SetHelpText("Nothing is waiting or finished. Convert a file to see it here.")
        sizer.Add(self.empty, 0, wx.EXPAND | wx.ALL, 6)
        sizer.Add(wx.StaticText(panel, label="&Details:"), 0, wx.LEFT, 6)
        self.details = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.details.SetMinSize(self.FromDIP(wx.Size(-1, 110)))
        self.details.SetHelpText(
            "The chosen job's progress, estimated time, Scribe's latest message and any error."
        )
        sizer.Add(self.details, 0, wx.EXPAND | wx.ALL, 6)

        grid = wx.WrapSizer(wx.HORIZONTAL)
        self.buttons: dict[str, Any] = {}
        for label, method in COMMANDS:
            button = wx.Button(panel, label=label)
            button.SetHelpText(_COMMAND_HELP[method])
            button.Bind(wx.EVT_BUTTON, lambda _e, m=method: self.run(m))
            grid.Add(button, 0, wx.ALL, 4)
            self.buttons[method] = button
        close = wx.Button(panel, wx.ID_CLOSE, label="Close")
        close.SetHelpText("Closes Conversions on This Computer. Jobs carry on.")
        grid.Add(close, 0, wx.ALL, 4)
        sizer.Add(grid, 0, wx.EXPAND)
        panel.SetSizer(sizer)
        self.SetSize(self.FromDIP(wx.Size(720, 520)))

        bind_close_button(self, close, modeless=True)
        self.list.Bind(wx.EVT_LIST_ITEM_FOCUSED, lambda _e: self._show_details())
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self.run("open_result"))
        self.list.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self.list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.list.Hide()  # shown by refresh() once there is a row
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda _e: self.refresh(), self._timer)
        self.refresh()

    # ------------------------------------------------------------- showing

    def show_from(self, opener: Any) -> None:
        """Show (or raise) the window, remembering where to return focus."""
        self._opener = opener
        if self.IsShown():
            self.Raise()
            (self.list if self._ids else self.empty).SetFocus()
            return
        self._timer.Start(2000)
        show_modeless_surface(self, TITLE, focus=True)
        target = self.list if self._ids else self.empty
        if self._ids and self.list.GetFocusedItem() < 0:
            self.list.Focus(0)
            self.list.Select(0)
        target.SetFocus()

    def _on_char_hook(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
            return
        event.Skip()

    def _on_close(self, event: wx.CloseEvent) -> None:
        self._timer.Stop()
        opener = self._opener
        self._controller.window_closed()
        self.Destroy()
        try:
            if opener is not None and opener:
                opener.SetFocus()
        except RuntimeError:
            pass
        event.Skip(False)

    # ------------------------------------------------------------- updates

    def refresh(self, _job_id: str = "") -> None:
        """Bring the rows up to date in place; never move focus."""
        try:
            jobs = self._controller.queue.jobs()
        except (OSError, TimeoutError):
            return
        by_id = {job.id: job for job in jobs}
        # rows that went away (removed in another app)
        focused_row = self.list.GetFocusedItem()
        for index in range(len(self._ids) - 1, -1, -1):
            if self._ids[index] not in by_id:
                self.list.DeleteItem(index)
                if index == focused_row and self.list.GetItemCount():
                    keep = min(index, self.list.GetItemCount() - 1)
                    self.list.Focus(keep)
                    self.list.Select(keep)
                self._stages.pop(self._ids[index], None)
                del self._ids[index]
        for job in jobs:
            words = job.state_words
            if job.state == q.CONVERTING and job.stage:
                from quill.core.scribe.model import format_label, stage_words

                stage = stage_words(job.stage)
                stage = stage[:1].upper() + stage[1:]  # not capitalize(): it lowers "Scribe's"
                words = f"{stage}: {format_label(job.format)}"
            if job.id not in self._ids:
                row = self.list.InsertItem(self.list.GetItemCount(), job.display_name)
                self.list.SetItem(row, 1, formats_phrase(job.formats))
                self.list.SetItem(row, 2, words)
                self._ids.append(job.id)
                self._stages[job.id] = words
            elif self._stages.get(job.id) != words:
                self.list.SetItem(self._ids.index(job.id), 2, words)
                self._stages[job.id] = words
        has_rows = bool(self._ids)
        if self.empty.IsShown() == has_rows:
            focused = wx.Window.FindFocus()
            if has_rows and focused is self.empty:
                self.list.Focus(0)
                self.list.Select(0)
                self.list.SetFocus()
            elif not has_rows and focused is self.list:
                self.empty.SetFocus()
            self.empty.Show(not has_rows)
            self.empty_label.Show(not has_rows)
            self.list.Show(has_rows)
            self.Layout()
        self._show_details()

    def selected_job(self) -> q.Job | None:
        index = self.list.GetFocusedItem()
        if index < 0 or index >= len(self._ids):
            return None
        try:
            return self._controller.queue.get(self._ids[index])
        except (OSError, TimeoutError):
            return None

    def _show_details(self) -> None:
        if wx.Window.FindFocus() is self.details:
            return  # never rewrite what is being read
        job = self.selected_job()
        text = job_details(job) if job is not None else ""
        if self.details.GetValue() != text:
            self.details.SetValue(text)
            self.details.SetInsertionPoint(0)
        self._enable_buttons(job)

    def _enable_buttons(self, job: q.Job | None) -> None:
        state = job.state if job is not None else ""
        rules = {
            "open_result": bool(job and job.outputs),
            "next_steps": bool(job and job.outputs),
            "open_folder": bool(job and job.folder),
            "cancel_waiting": state in q.ACTIVE or state in q.NEEDS_PERSON,
            "retry": state in (q.FAILED, q.STOPPED, q.NEEDS_SIGNIN, q.GONE),
            "buy_pages": True,
            "enter_password": state == q.NEEDS_PASSWORD,
            "sign_in": state == q.NEEDS_SIGNIN,
            "ask_review": bool(job and job.document_id),
            "copy_details": job is not None,
            "remove": job is not None,
        }
        for method, button in self.buttons.items():
            # Enabled buttons only would hide commands from Tab; they stay
            # enabled and say why when they cannot act (review 2026-11-20).
            button.Enable(True)
            button._quill_can_act = rules.get(method, False)

    # ------------------------------------------------------------ commands

    def _on_list_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.run("remove")
            return
        event.Skip()

    def _on_context_menu(self, _event: Any) -> None:
        menu = wx.Menu()
        for label, method in COMMANDS:
            item = menu.Append(wx.ID_ANY, label)
            self.Bind(wx.EVT_MENU, lambda _e, m=method: self.run(m), item)
        self.PopupMenu(menu)
        menu.Destroy()

    def run(self, method: str) -> None:
        controller = self._controller
        job = self.selected_job()
        if method == "sign_in":
            if controller.sign_in() and job is not None:
                controller.retry(job.id)
        elif job is None:
            controller.host.scribe_announce("Choose a conversion first.")
            return
        elif not getattr(self.buttons[method], "_quill_can_act", True):
            controller.host.scribe_announce(_CANNOT[method].format(name=job.display_name))
            return
        elif method == "open_result":
            controller.open_job_result(job)
        elif method == "next_steps":
            # After any menu that chose it has closed, so the popups never nest.
            wx.CallAfter(self._next_steps, job)
            return
        elif method == "open_folder":
            _open_folder(Path(job.folder))
        elif method == "cancel_waiting":
            controller.cancel_waiting(job.id)
        elif method == "retry":
            controller.retry(job.id)
        elif method == "buy_pages":
            controller.buy_pages(job.purchase_url)
        elif method == "enter_password":
            controller.enter_password(job.id)
        elif method == "ask_review":
            controller.ask_for_review(job.document_id, job.display_name)
        elif method == "copy_details":
            if wx.TheClipboard.Open():
                try:
                    wx.TheClipboard.SetData(wx.TextDataObject(job_details(job)))
                finally:
                    wx.TheClipboard.Close()
                controller.host.scribe_announce("Details copied.")
        elif method == "remove":
            self._remove(job)
        self.refresh()

    def _next_steps(self, job: q.Job) -> None:
        """A menu of what this app can do with the finished outputs (8.1.7), at
        the Next Steps button. One code path for the button and the context menu,
        never a submenu that could be empty (review 2026-11-21)."""
        steps = self._controller.next_steps(job)
        if not steps:
            self._controller.host.scribe_announce(f"{job.display_name} has nothing made yet.")
            return
        button = self.buttons["next_steps"]
        menu = wx.Menu()
        for label, action in steps:
            item = menu.Append(wx.ID_ANY, label)
            menu.Bind(wx.EVT_MENU, lambda _e, a=action: a(), item)
        button.PopupMenu(menu, wx.Point(0, button.GetSize().height))
        menu.Destroy()

    def _remove(self, job: q.Job) -> None:
        index = self._ids.index(job.id) if job.id in self._ids else -1
        self._controller.remove(job.id)
        if index >= 0:
            self.list.DeleteItem(index)
            del self._ids[index]
            self._stages.pop(job.id, None)
            if self._ids:
                target = min(index, len(self._ids) - 1)
                self.list.Focus(target)
                self.list.Select(target)
        self._controller.host.scribe_announce(f"{job.display_name} removed from the list.")


def _open_folder(folder: Path) -> None:
    if folder.is_dir() and hasattr(os, "startfile"):
        os.startfile(str(folder))  # noqa: S606 - the person's own download folder


_COMMAND_HELP = {
    "open_result": (
        "Opens the finished file where it is used: QUILL, Media Player or the braille view."
    ),
    "next_steps": (
        "Lists what this app can do next with what was made, such as reading it aloud "
        "or sending it to the Media Player. Nothing runs until you choose."
    ),
    "open_folder": "Opens the folder the results were saved in.",
    "cancel_waiting": "Stops QUILL waiting. Scribe still finishes it and may use pages.",
    "retry": "Tries the job again, without uploading again when Scribe already has it.",
    "buy_pages": "Opens Scribe's purchase page in your browser. QUILL never takes payment.",
    "enter_password": "Asks for the password of a file that needs one.",
    "sign_in": "Signs in to Scribe for Documents again, then carries on.",
    "ask_review": "Sends the document for human review, Scribe's paid remediation, with a comment.",
    "copy_details": "Copies the details, with QUILL's error code, to the clipboard.",
    "remove": "Removes the row from this list. Nothing is deleted from your Scribe account.",
}
_CANNOT = {
    "open_result": "{name} has no result to open yet.",
    "next_steps": "{name} has nothing made yet.",
    "open_folder": "{name} has no folder yet.",
    "cancel_waiting": "QUILL is not waiting for {name}.",
    "retry": "{name} does not need retrying.",
    "buy_pages": "",
    "enter_password": "{name} does not need a password.",
    "ask_review": "{name} is not in your Scribe account yet.",
    "copy_details": "",
    "remove": "",
}


__all__ = ["COMMANDS", "EMPTY", "ScribeConversionsWindow", "job_details"]
