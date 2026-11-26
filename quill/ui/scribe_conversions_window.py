"""Conversions on This Computer: the family queue, in a modeless window (PRD 7.4, 12).

Each app shows its own instance, read from the shared queue file (refreshed
on the runner's events and every two seconds, for jobs another app runs).
Several files chosen together run one after another on their own (the
exception Pneuma approved on 2026-11-21), so there is no Send Next File.

* A native tree (``wx.TreeCtrl``, 2026-11-24). A job is a row, "Notes.pdf,
  Word: Converting: Word", and a **named set** (:mod:`quill.core.scribe.sets`)
  is one row, "Board packet: 12 of 34 done, 35 percent", with its documents
  under it: Right arrow opens it, Left closes it. Rows update in place and
  are never rebuilt, sorted or scrolled, so focus, the reader and what is
  open stay where the person left them (FUX-06). The row the person is on
  is not rewritten while the tree has focus -- a screen reader would read
  the new text out -- and catches up when they move; Details is current.
* Enter on a document opens the result; Enter on a set opens Set Details
  (:mod:`quill.ui.scribe_set_details`) with the conversion log. Delete
  removes the row, the Applications key or Shift+F10 opens every command;
  the same commands are buttons, and on a set Open Folder, Cancel Waiting,
  Retry, Copy Details and Remove from List act on the whole set.
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
from quill.core.scribe import sets
from quill.core.scribe.model import formats_phrase
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
    if job.eta_seconds:
        lines.append(f"About {max(1, round(job.eta_seconds / 60))} minutes left.")
    if job.message:
        lines.append(f"Latest: {job.message}")
    if job.outputs:
        lines.append("Made: " + "; ".join(str(p) for p in job.outputs.values()))
    if job.folder:
        lines.append(f"Folder: {job.folder}")
    if job.error_code:
        lines.append(f"Code: {job.error_code}")
    return "\n".join(lines)


def job_row(job: q.Job) -> str:
    """A job's row: its name, formats and stage."""
    words = job.state_words
    if job.state == q.CONVERTING and job.stage:
        from quill.core.scribe.model import format_label, stage_words

        stage = stage_words(job.stage)
        stage = stage[:1].upper() + stage[1:]  # not capitalize(): it lowers "Scribe's"
        words = f"{stage}: {format_label(job.format)}"
    return f"{job.display_name}, {formats_phrase(job.formats)}: {words}"


class ScribeConversionsWindow(wx.Frame):
    #: Stage feedback, when chosen, plays while this window is in front
    #: (quill.core.scribe.feedback.SCRIBE_WINDOW_ATTR).
    is_scribe_window = True

    def __init__(self, parent: Any, controller: Any) -> None:
        super().__init__(parent, title=TITLE, style=wx.DEFAULT_FRAME_STYLE)
        self.SetName("scribe_conversions_window")  # F1 finds its topic by this name (topics.json)
        self._controller = controller
        self._opener: Any = None
        #: Each row's key ("job:<id>" or "set:<id>"), its item and its text.
        self._items: dict[str, Any] = {}
        self._texts: dict[str, str] = {}

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(panel, label="Conv&ersions:"), 0, wx.LEFT | wx.TOP, 6)
        self.tree = wx.TreeCtrl(
            panel,
            style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE,
        )
        self._root = self.tree.AddRoot(TITLE)
        self.tree.SetHelpText(
            "Every Scribe for Documents job on this computer, from every QUILL app. A set of "
            "documents is one row: Right arrow shows its documents, Left hides them, and Enter "
            "opens Set Details with its conversion log. On a document, Enter opens the result. "
            "Delete removes the row, the Applications key lists every command."
        )
        sizer.Add(self.tree, 1, wx.EXPAND | wx.ALL, 6)
        self.empty_label = wx.StaticText(panel, label="Status:")
        sizer.Add(self.empty_label, 0, wx.LEFT, 6)
        self.empty = wx.TextCtrl(panel, style=wx.TE_READONLY, value=EMPTY)
        self.empty.SetHelpText("Nothing is waiting or finished. Convert a file to see it here.")
        sizer.Add(self.empty, 0, wx.EXPAND | wx.ALL, 6)
        sizer.Add(wx.StaticText(panel, label="&Details:"), 0, wx.LEFT, 6)
        self.details = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.details.SetMinSize(self.FromDIP(wx.Size(-1, 110)))
        self.details.SetHelpText(
            "The chosen job's progress, estimated time, Scribe's latest message and any "
            "error; for a set, how many are done and which were not made."
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
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, lambda _e: self._moved())
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, lambda _e: self.activate())
        self.tree.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self.tree.Bind(wx.EVT_TREE_KEY_DOWN, self._on_tree_key)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.tree.Hide()  # shown by refresh() once there is a row
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda _e: self.refresh(), self._timer)
        self.refresh()

    # ------------------------------------------------------------- showing

    def show_from(self, opener: Any) -> None:
        """Show (or raise) the window, remembering where to return focus."""
        self._opener = opener
        if self.IsShown():
            self.Raise()
            (self.tree if self._items else self.empty).SetFocus()
            return
        self._timer.Start(2000)
        show_modeless_surface(self, TITLE, focus=True)
        self._focus_rows()

    def _focus_rows(self) -> None:
        if not self._items:
            self.empty.SetFocus()
            return
        if not self.tree.GetSelection().IsOk():
            first, _cookie = self.tree.GetFirstChild(self._root)
            if first.IsOk():
                self.tree.SelectItem(first)
        self.tree.SetFocus()

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

    def _key_of(self, item: Any) -> str:
        if item is None or not item.IsOk() or item == self._root:
            return ""
        return str(self.tree.GetItemData(item) or "")

    def _reading(self, key: str) -> bool:
        """The row the person is on, in the focused tree: not rewritten now."""
        return wx.Window.FindFocus() is self.tree and self._key_of(self.tree.GetSelection()) == key

    def _row(self, key: str, text: str, parent: Any) -> None:
        """Add the row, or change its text in place (never while it is read)."""
        item = self._items.get(key)
        if item is None:
            item = self.tree.AppendItem(parent, text)
            self.tree.SetItemData(item, key)
            self._items[key] = item
            self._texts[key] = text
            return
        self._texts[key] = text
        if self.tree.GetItemText(item) != text and not self._reading(key):
            self.tree.SetItemText(item, text)

    def _remove_row(self, key: str) -> None:
        item = self._items.pop(key, None)
        self._texts.pop(key, None)
        if item is None:
            return
        for child in [k for k, i in self._items.items() if self.tree.GetItemParent(i) == item]:
            self._items.pop(child, None)
            self._texts.pop(child, None)
        if self.tree.GetSelection() == item:
            after = self.tree.GetNextSibling(item)
            if not after.IsOk():
                after = self.tree.GetPrevSibling(item)
            if not after.IsOk():
                parent = self.tree.GetItemParent(item)
                if parent.IsOk() and parent != self._root:
                    after = parent
            if after.IsOk():
                self.tree.SelectItem(after)
        self.tree.Delete(item)

    def refresh(self, _job_id: str = "") -> None:
        """Bring the rows up to date in place; never move focus or announce."""
        try:
            jobs = self._controller.queue.jobs()
            named = {made.id: made for made in self._controller.queue.sets()}
        except (OSError, TimeoutError):
            return
        keys = {f"job:{job.id}" for job in jobs}
        keys |= {f"set:{set_id}" for set_id in named if any(j.batch == set_id for j in jobs)}
        for key in [k for k in self._items if k not in keys]:
            if key in self._items:
                self._remove_row(key)
        for job in jobs:
            parent = self._root
            batch_set = named.get(job.batch)
            if batch_set is not None:
                members = [j for j in jobs if j.batch == batch_set.id]
                self._row(f"set:{batch_set.id}", sets.set_progress(batch_set, members), self._root)
                parent = self._items[f"set:{batch_set.id}"]
            self._row(f"job:{job.id}", job_row(job), parent)
        has_rows = bool(self._items)
        if self.empty.IsShown() == has_rows:
            focused = wx.Window.FindFocus()
            self.empty.Show(not has_rows)
            self.empty_label.Show(not has_rows)
            self.tree.Show(has_rows)
            self.Layout()
            if has_rows and focused is self.empty:
                self._focus_rows()
            elif not has_rows and focused is self.tree:
                self.empty.SetFocus()
        self._show_details()

    def _moved(self) -> None:
        """The person moved: rows held back while read catch up, then Details."""
        for key, item in self._items.items():
            text = self._texts.get(key, "")
            if self.tree.GetItemText(item) != text and not self._reading(key):
                self.tree.SetItemText(item, text)
        self._show_details()

    def selected(self) -> tuple[str, Any]:
        """``("set", BatchSet)``, ``("job", Job)`` or ``("", None)``."""
        key = self._key_of(self.tree.GetSelection())
        kind, _sep, ident = key.partition(":")
        try:
            if kind == "set":
                return kind, self._controller.queue.get_set(ident)
            if kind == "job":
                return kind, self._controller.queue.get(ident)
        except (OSError, TimeoutError):
            pass
        return "", None

    def selected_job(self) -> q.Job | None:
        kind, found = self.selected()
        return found if kind == "job" else None

    def _show_details(self) -> None:
        if wx.Window.FindFocus() is self.details:
            return  # never rewrite what is being read
        kind, found = self.selected()
        text = ""
        if kind == "job" and found is not None:
            text = job_details(found)
        elif kind == "set" and found is not None:
            from quill.ui.scribe_set_details import set_details_text

            text = set_details_text(found, self._controller.set_jobs(found.id))
        if self.details.GetValue() != text:
            self.details.SetValue(text)
            self.details.SetInsertionPoint(0)
        self._enable_buttons(kind, found)

    def _enable_buttons(self, kind: str, found: Any) -> None:
        job = found if kind == "job" else None
        state = job.state if job is not None else ""
        if kind == "set" and found is not None:
            states = {j.state for j in self._controller.set_jobs(found.id)}
            rules = {
                "open_folder": True,
                "cancel_waiting": bool(states & (q.ACTIVE | q.NEEDS_PERSON)),
                "retry": bool(states & {q.FAILED, q.STOPPED, q.NEEDS_SIGNIN, q.GONE}),
                "buy_pages": True,
                "copy_details": True,
                "remove": True,
            }
        else:
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

    def _on_tree_key(self, event: wx.TreeEvent) -> None:
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

    def activate(self) -> None:
        """Enter: Set Details on a set, the result on a document."""
        kind, found = self.selected()
        if kind == "set" and found is not None:
            # After the tree's own key handling, so nothing else acts on the key.
            wx.CallAfter(self._controller.open_set_details, found.id, self)
        elif kind == "job":
            self.run("open_result")

    def run(self, method: str) -> None:
        kind, found = self.selected()
        if kind == "set" and found is not None:
            self._run_on_set(method, found)
            self.refresh()
            return
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
            _copy(job_details(job))
            controller.host.scribe_announce("Details copied.")
        elif method == "remove":
            self._remove(f"job:{job.id}", job.display_name, lambda: controller.remove(job.id))
        self.refresh()

    def _run_on_set(self, method: str, batch_set: Any) -> None:
        """A command on a set's row acts on the whole set, where that makes sense."""
        controller = self._controller
        if method == "open_folder":
            _open_folder(Path(batch_set.folder))
        elif method == "cancel_waiting":
            controller.stop_waiting_set(batch_set.id)
        elif method == "retry":
            controller.retry_failed(batch_set.id)
        elif method == "buy_pages":
            controller.buy_pages("")
        elif method == "copy_details":
            from quill.ui.scribe_set_details import set_details_text

            _copy(set_details_text(batch_set, controller.set_jobs(batch_set.id)))
            controller.host.scribe_announce("Details copied.")
        elif method == "remove":
            self._remove(
                f"set:{batch_set.id}", batch_set.name, lambda: controller.remove_set(batch_set.id)
            )
        elif method == "sign_in":
            controller.sign_in()
        else:
            controller.host.scribe_announce(
                f"Choose a document in {batch_set.name} first: Right arrow shows them."
            )

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

    def _remove(self, key: str, name: str, remove: Any) -> None:
        remove()
        self._remove_row(key)
        self._controller.host.scribe_announce(f"{name} removed from the list.")


def _copy(text: str) -> None:
    if wx.TheClipboard.Open():
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(text))
        finally:
            wx.TheClipboard.Close()


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


__all__ = ["COMMANDS", "EMPTY", "ScribeConversionsWindow", "job_details", "job_row"]
