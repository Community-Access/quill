"""Do a Document Task: the agent window, shared by QUILL and QUILL Lite (codex.md 5.2, 6.2).

One window for both agent engines, named for neither. The person types what
they want done -- "Fix the heading levels, then build a table of contents" --
and the connection in use carries it out with the editor's own tools: GitHub
Copilot's tool harness, or Codex on this app's ChatGPT plan.

**The controls, in tab order.** The conversation (a read-only transcript), the
status line ("Using GitHub Copilot"), the instruction field, Send, Stop and
Close. Focus starts in the instruction field. Enter there sends: the first
instruction starts a task, and anything typed while it runs goes to it as a
follow-up. Stop ends the task within a second, releasing any question still on
screen. Close stops a running task, too.

**Approvals (5.3).** A step that changes something asks first, in one small
dialog through ``show_modal_dialog``: one sentence on what will happen, then
Allow once (the default, Enter), Allow for this task, and Don't allow
(Escape). An edit is then shown in Review AI Changes before anything is
applied, and every applied change is one Control Z. Nothing carries over
between tasks.

**What is spoken (GATE-13).** Only outcomes: the task's closing text summary
(decision 13), or why it could not start. The transcript and status line fill
in silently -- a reader reaches them with Shift+Tab -- and the approval
question is the dialog's own text, which the reader says as focus lands on it.
Everything spoken goes through the editor's announcement service, so it is
brailled too (GATE-BRAILLE).

**Threading.** The task runs on a worker (the family's ``thread_submit``); its
events, the approval questions and every editor touch come back to the UI
thread through ``wx.CallAfter`` (:class:`~quill.core.ai.approvals.UiApprovalBridge`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import wx

from quill.core.ai import agent_task_words as words
from quill.core.ai.approvals import ApprovalChoice, ApprovalRequest, UiApprovalBridge
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size
from quill.ui.hosted_ai_dialogs import _PAD, _close_row, _read_only, focus_on

__all__ = ["AgentTaskHooks", "AgentWindow", "ApprovalDialog", "ask_approval"]

#: Events whose summary belongs in the transcript as a line of its own.
_STEP_EVENTS = frozenset({
    AgentEventKind.TOOL_CALL_DENIED,
    AgentEventKind.PATCH_APPLIED,
    AgentEventKind.WARNING,
    AgentEventKind.ERROR,
})


@dataclass
class AgentTaskHooks:
    """What the window needs from the editor, and nothing more."""

    announce: Callable[[str], None]
    #: The connection in use: ``copilot`` or ``codex``.
    connection: str
    #: ``(approver, host) -> DocumentTaskRunner``; the editor builds the engine.
    make_runner: Callable[[Any, Any], Any]
    #: ``(bridge, note) -> EditorHost`` over the document (AgentTaskHost).
    make_host: Callable[[Any, Callable[[str], None]], Any]
    #: ``(name, work, on_success=, on_failure=)``: one worker job.
    submit: Callable[..., None] | None = None


class ApprovalDialog(wx.Dialog):
    """One step, one sentence, three answers (codex.md 5.3)."""

    def __init__(self, parent: Any, summary: str) -> None:
        super().__init__(parent, title="Allow This Step?")  # words.APPROVAL_TITLE
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        label = wx.StaticText(self, label="What will happen")
        # Single-line and read-only: the reader says the sentence as focus lands
        # here, and Enter still presses the default button, Allow once.
        self.summary = wx.TextCtrl(self, value=summary, style=wx.TE_READONLY)
        set_accessible_name(self.summary, "What will happen")
        self.summary.SetHelpText(
            "What the task wants to do next, in one sentence. Enter allows it once; "
            "Escape does not allow it."
        )
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self.summary, 0, wx.EXPAND | wx.ALL, _PAD)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer(1)
        self.once = wx.Button(self, wx.ID_OK, "Allow &once")
        self.once.SetHelpText("Lets this one step happen. The next step asks again.")
        self.task = wx.Button(self, wx.ID_YES, "Allow for this &task")
        self.task.SetHelpText(
            "Lets steps like this one happen until this task ends, without asking "
            "again. The next task asks afresh."
        )
        self.task.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_YES))
        self.deny = wx.Button(self, wx.ID_CANCEL, "&Don't allow")
        self.deny.SetHelpText("Stops this step. The task carries on without it, or ends.")
        for button in (self.once, self.task, self.deny):
            row.Add(button, 0, wx.LEFT, _PAD)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)
        self.once.SetDefault()
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Allow &once",
            cancel_id=wx.ID_CANCEL,
            cancel_label="&Don't allow",
        )
        self.SetInitialSize(dip_size(self, 560, 160))
        self.Centre()
        self.summary.SetFocus()


def ask_approval(parent: Any, summary: str) -> ApprovalChoice:
    """Show :class:`ApprovalDialog` and say which answer was chosen."""
    dialog = ApprovalDialog(parent, summary)
    try:
        result = show_modal_dialog(dialog, words.APPROVAL_TITLE)
    finally:
        dialog.Destroy()
    if result == wx.ID_OK:
        return ApprovalChoice.ONCE
    if result == wx.ID_YES:
        return ApprovalChoice.TASK
    return ApprovalChoice.DENY


class AgentWindow(wx.Frame):
    """The conversation, the status line, the instruction, Send, Stop and Close."""

    def __init__(self, parent: Any, hooks: AgentTaskHooks) -> None:
        super().__init__(parent, title="Do a Document Task")  # words.TITLE
        self._hooks = hooks
        self._approval = UiApprovalBridge(post=wx.CallAfter, present=self._present)
        self._runner: Any = None
        self._host_bridge: Any = None
        self._running = False
        self._reply: list[str] = []
        self._replied = False

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)
        transcript_label = wx.StaticText(panel, label="&Conversation")
        self.transcript = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        set_accessible_name(self.transcript, "Conversation")
        self.transcript.SetHelpText(
            "Everything said in this task: what you asked, each step taken, and the "
            "summary at the end. Read it with the arrow keys."
        )
        sizer.Add(transcript_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self.transcript, 1, wx.EXPAND | wx.ALL, _PAD)
        self.status = _read_only(
            panel,
            sizer,
            "Status",
            words.status_line(hooks.connection),
            "Which AI is doing the task, and whether it is working, stopping or done.",
            grow=False,
        )
        field_label = wx.StaticText(panel, label="&Instruction")
        self.instruction = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self.instruction, "Instruction")
        self.instruction.SetHelpText(
            "Type what you want done to this document, then press Enter. While a "
            "task runs, what you type here goes to it as a follow-up."
        )
        self.instruction.Bind(wx.EVT_TEXT_ENTER, lambda _e: self.send())
        sizer.Add(field_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self.instruction, 0, wx.EXPAND | wx.ALL, _PAD)

        self.send_button = wx.Button(panel, label="&Send")
        self.send_button.SetHelpText(
            "Starts a task with what you typed, or sends it to the task that is running."
        )
        self.send_button.Bind(wx.EVT_BUTTON, lambda _e: self.send())
        self.stop_button = wx.Button(panel, label="S&top")
        self.stop_button.SetHelpText(
            "Stops the task now. Changes already applied stay, and each can be undone "
            "with Control Z."
        )
        self.stop_button.Bind(wx.EVT_BUTTON, lambda _e: self.stop())
        self.stop_button.Disable()
        close = _close_row(self, sizer, self.send_button, self.stop_button)
        close.SetHelpText("Closes this window, stopping a task that is still running.")

        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.SetInitialSize(dip_size(self, 640, 520))
        self.Centre()
        focus_on(self, self.instruction)

    # -- what the person does ------------------------------------------------ #

    def send(self) -> None:
        """Start a task with the instruction, or send it to the one running."""
        text = self.instruction.GetValue().strip()
        if not text:
            return
        self.instruction.Clear()
        self._write(words.transcript_line("You", text))
        if self._running and self._runner is not None:
            self._runner.send(text)
            return
        self._start(text)

    def stop(self) -> None:
        """Stop: the session's cancel, and every open question answered Don't allow."""
        if not self._running or self._runner is None:
            return
        self._set_status(words.STOPPING)
        self._approval.cancel()
        if self._host_bridge is not None:
            self._host_bridge.cancel()  # a worker waiting on the editor is released too
        self._runner.cancel()

    # -- the task ------------------------------------------------------------- #

    def _start(self, instruction: str) -> None:
        from quill.core.ai.approvals import UiThreadBridge

        self._approval.reset()
        self._host_bridge = UiThreadBridge(wx.CallAfter)
        host = self._hooks.make_host(self._host_bridge, self._write)
        try:
            runner = self._hooks.make_runner(self._approval, host)
            runner.emit = self._emit
            session = runner.start(instruction)
        except Exception as error:  # noqa: BLE001 - a task that cannot start says why
            said = str(error) or words.NO_ENGINE
            self._write(said)
            self._hooks.announce(said)
            return
        self._runner = runner
        self._running = True
        self._reply = []
        self._replied = False
        self.stop_button.Enable()
        self._set_status(words.WORKING)
        submit = self._hooks.submit or _thread_submit
        submit(
            "quill-ai-document-task",
            lambda **_k: runner.finish(session.run()),
            on_success=lambda _n, outcome: wx.CallAfter(self._finished, outcome),
            on_failure=lambda _n, error: wx.CallAfter(self._failed, error),
        )

    def _emit(self, event: AgentEvent) -> None:
        """Called on the worker: hand each event to the UI thread."""
        wx.CallAfter(self._on_event, event)

    def _on_event(self, event: AgentEvent) -> None:
        if not self:
            return
        if event.kind is AgentEventKind.AGENT_TEXT_DELTA:
            self._reply.append(event.summary)
            self._replied = True
        elif event.kind in _STEP_EVENTS and event.summary:
            self._flush_reply()
            self._write(event.summary)

    def _flush_reply(self) -> None:
        text = "".join(self._reply).strip()
        self._reply = []
        if text:
            from quill.core.ai.text_only import as_text

            name = words.engine_name(self._hooks.connection)
            self._write(words.transcript_line(name, as_text(text)))

    def _finished(self, outcome: Any) -> None:
        self._running = False
        if not self:
            return
        self._flush_reply()
        if outcome.answer and not self._replied:  # an engine that sent no pieces
            self._reply = [str(outcome.answer)]
            self._flush_reply()
        summary = str(outcome.summary)
        if outcome.error:
            summary = f"{summary} {outcome.error}".strip()
        self._write(summary)
        self.stop_button.Disable()
        self._set_status(summary.split(".", 1)[0] + ".")
        self._hooks.announce(summary)  # the outcome: spoken and brailled once
        self.instruction.SetFocus()

    def _failed(self, error: BaseException) -> None:
        self._running = False
        said = str(getattr(error, "sentence", "") or error) or "The task could not finish."
        if self:
            self._write(said)
            self.stop_button.Disable()
            self._set_status("Stopped.")
        self._hooks.announce(said)

    # -- the approval question ------------------------------------------------ #

    def _present(self, request: ApprovalRequest) -> None:
        """On the UI thread: ask, and answer the waiting worker whatever happens."""
        choice = ApprovalChoice.DENY
        try:
            if self:
                choice = ask_approval(self, request.summary)
        finally:
            request.answer(choice)

    # -- plumbing ---------------------------------------------------------------- #

    def _write(self, line: str) -> None:
        """Add a line to the transcript, silently (the reader reaches it by Shift+Tab)."""
        if not self or not line.strip():
            return
        where = self.transcript.GetInsertionPoint()
        prefix = "\n\n" if self.transcript.GetLastPosition() else ""
        self.transcript.AppendText(prefix + line.strip())
        self.transcript.SetInsertionPoint(where)

    def _set_status(self, state: str) -> None:
        self.status.SetValue(words.status_line(self._hooks.connection, state))

    def _on_close(self, event: Any) -> None:
        if self._running:
            self.stop()
        event.Skip()


def _thread_submit(name: str, work: Any, *, on_success: Any, on_failure: Any) -> None:
    from quill.ui.update_download import thread_submit

    thread_submit(name, work, on_success=on_success, on_failure=on_failure)
