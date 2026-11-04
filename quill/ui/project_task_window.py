"""Do a Project Task: the agent window, on a whole project folder (code.md 2.1, 5.2, 5.3).

The document task's window (:class:`~quill.ui.agent_window.AgentWindow`),
grown rather than copied: the same conversation, status line, instruction
field, Send, Stop and Close, the same approvals, the same engines. What a
project adds is reachable by keys, never by a second place to learn:

- **Plan** (Alt+P) and **Changes** (Alt+H) put the cursor on the latest plan
  or list of changes in the conversation.
- **Output** (Alt+O) opens the last command's full output as a document.
- **Transcript** (Alt+R) opens the whole task as a document with a heading per
  turn, so H and Shift+H move through it.
- **Undo Last Turn** (Alt+U) puts every file the last turn changed back.
- **Explain Last Turn** (Alt+X) asks the agent what it changed and why, in
  plain words, without changing anything.
- **Coach mode** (Alt+A): the agent teaches and points, and the person types.
- **Allowed Commands** (Alt+W) and **Engine Tools** (Alt+L) are this
  project's own settings, kept in QUILL and never in the repository.

**One task, many turns.** The runner lives as long as the window, so each
turn hears what the earlier ones did and Undo Last Turn knows which turn was
last.

**Focus (5.3).** Nothing here moves focus except a question the person is
waiting on in this window. When the task needs an answer while the person is
elsewhere in QUILL, it says once "The project task is waiting for you. Press
Ctrl+3 to answer." and waits; the question opens when the window is active
again. When QUILL itself is in the background, nothing is spoken at all.

**Spoken (GATE-13):** the plan is ready, the task needs you, a command's
result sentence, a turn applied, undone or done. Everything else fills in
silently, and every spoken line goes through the editor's announcement
service, so it is brailled too (GATE-BRAILLE).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import wx

from quill.core.ai import agent_task_words as task_words
from quill.core.ai import project_task_words as words
from quill.ui.agent_window import AgentTaskHooks, AgentWindow

__all__ = ["ProjectTaskHooks", "ProjectTaskWindow", "ProjectWindowUi"]

_PAD = 8


@dataclass
class ProjectTaskHooks(AgentTaskHooks):
    """The document task's hooks, plus what a project needs from the editor."""

    #: ``(path) -> None``: open a file (the output, the transcript) as a document.
    open_file: Callable[[Path], None] = field(default=lambda _p: None)
    #: ``(paths) -> None``: reload files the task changed, keeping the cursor.
    files_changed: Callable[[list[Path]], None] = field(default=lambda _p: None)
    #: ``(name) -> None``: play a sound-scheme cue, when the editor has one.
    cue: Callable[[str], None] = field(default=lambda _n: None)
    #: The project's name, for the status line.
    project: str = ""
    #: Coach mode at the start, and whether the turn should explain the last one.
    coach: bool = False
    explain_first: bool = False
    #: ``(runner) -> None``: the project's allowed commands and its bypass.
    edit_allowed: Callable[[Any], None] = field(default=lambda _r: None)
    #: ``(runner) -> None``: decision 4's per-engine opt-in for the vendor's tools.
    edit_engine_tools: Callable[[Any], None] = field(default=lambda _r: None)


class _Waiting:
    """One question the task is waiting on, held until the person is in the window."""

    def __init__(self, ask: Callable[[], Any], default: Any) -> None:
        self.ask = ask
        self.default = default
        self.future: Future[Any] = Future()

    def answer(self, value: Any) -> None:
        if not self.future.done():
            self.future.set_result(value)


class ProjectWindowUi:
    """What :class:`~quill.core.ai.project_task.ProjectTaskRunner` asks of the window.

    Every method is called on the engine's worker; each one hands its work to
    the UI thread with ``wx.CallAfter``, and the ones that need an answer wait
    for it -- or for Stop, which answers every waiting question with "no".
    """

    def __init__(self, window: ProjectTaskWindow) -> None:
        self._window = window
        self._lock = threading.Lock()
        self._waiting: list[_Waiting] = []
        self._cancelled = False

    # -- answers ---------------------------------------------------------------- #

    def _ask(self, ask: Callable[[], Any], default: Any) -> Any:
        waiting = _Waiting(ask, default)
        with self._lock:
            if self._cancelled:
                return default
            self._waiting.append(waiting)
        wx.CallAfter(self._window.present, waiting)
        try:
            return waiting.future.result()
        finally:
            with self._lock:
                if waiting in self._waiting:
                    self._waiting.remove(waiting)

    def cancel(self) -> None:
        """Stop: every question still waiting is answered with its default."""
        with self._lock:
            self._cancelled = True
            pending = list(self._waiting)
        for waiting in pending:
            waiting.answer(waiting.default)

    def reset(self) -> None:
        with self._lock:
            self._cancelled = False

    def review(self, changes: Any) -> bool:
        from quill.ui.project_review_dialog import review_project_changes

        window = self._window
        return bool(
            self._ask(lambda: review_project_changes(window, changes, window.announce), False)
        )

    def approve_command(self, assessment: Any, question: str) -> str:
        from quill.ui.project_command_dialog import ask_command

        return str(self._ask(lambda: ask_command(self._window, assessment, question), "deny"))

    def keep_waiting(self, seconds: float) -> bool:
        from quill.ui.project_command_dialog import ask_keep_waiting

        return bool(self._ask(lambda: ask_keep_waiting(self._window, seconds), False))

    def keep_going(self, steps: int) -> bool:
        from quill.ui.dialog_contract import show_message_box

        text = f"The task stopped after {steps} steps. Continue?"
        return bool(
            self._ask(
                lambda: show_message_box(text, "Continue?", wx.YES_NO, self._window) == wx.YES,
                False,
            )
        )

    # -- news -------------------------------------------------------------------- #

    def plan_ready(self, steps: list[str]) -> None:
        wx.CallAfter(self._window.show_plan, list(steps))

    def note(self, text: str) -> None:
        wx.CallAfter(self._window.write, text)

    def command_done(self, sentence: str, output: Path, ok: bool) -> None:
        wx.CallAfter(self._window.command_finished, sentence, output, ok)

    def files_changed(self, paths: list[Path]) -> None:
        wx.CallAfter(self._window.files_were_changed, list(paths))


class ProjectTaskWindow(AgentWindow):
    """The agent window on a project, with its plan, changes, output and undo."""

    def __init__(self, parent: Any, hooks: ProjectTaskHooks) -> None:
        hooks.title = words.TITLE
        super().__init__(parent, hooks)
        self._project_hooks = hooks
        self.ui = ProjectWindowUi(self)
        self._marks: dict[str, int] = {}
        self._present_next: list[_Waiting] = []
        self._told_waiting = False
        self.SetTitle(f"{words.TITLE}: {hooks.project}" if hooks.project else words.TITLE)
        self.instruction.SetHelpText(
            "Type what you want done in this project, then press Enter: a change, a "
            "question about the code, or what to test. While a task runs, what you "
            "type here goes to it as a follow-up."
        )
        self._add_project_controls()
        self._set_status("")
        self.Bind(wx.EVT_ACTIVATE, self._on_activate)
        if hooks.explain_first:
            wx.CallAfter(self.explain_last_turn)

    # -- the controls a project adds ---------------------------------------------- #

    def _add_project_controls(self) -> None:
        panel = self.instruction.GetParent()
        sizer = panel.GetSizer()
        self.coach = wx.CheckBox(panel, label="Co&ach mode")
        self.coach.SetValue(self._project_hooks.coach)
        self.coach.SetHelpText(
            "When checked, the agent does not change files or run commands. It reads "
            "the project, explains, and points you to the file and line, and you make "
            "the change yourself. Good for learning."
        )
        sizer.Insert(sizer.GetItemCount() - 1, self.coach, 0, wx.LEFT | wx.RIGHT, _PAD)
        row = wx.BoxSizer(wx.HORIZONTAL)
        specs = (
            ("&Plan", "Puts the cursor on the latest plan in the conversation.", self.go_to_plan),
            (
                "C&hanges",
                "Puts the cursor on the latest list of changes in the conversation.",
                self.go_to_changes,
            ),
            ("&Output", "Opens the last command's full output as a document.", self.open_output),
            (
                "T&ranscript",
                "Opens this whole task as a document, one heading per turn, so heading "
                "keys move through it. It is kept in QUILL, not in your project.",
                self.open_transcript,
            ),
            (
                "&Undo Last Turn",
                "Puts every file the last turn changed back as it was, and removes files "
                "it made. It refuses, and says which file, if you have edited one since.",
                self.undo_last_turn,
            ),
            (
                "E&xplain Last Turn",
                "Asks the agent what it changed in the last turn and why, in plain "
                "words. Nothing is changed.",
                self.explain_last_turn,
            ),
            (
                "Allo&wed Commands...",
                "This project's commands that run without asking, and the switch to run "
                "commands without asking at all.",
                lambda: self._project_hooks.edit_allowed(self._runner),
            ),
            (
                "Engine Too&ls...",
                "Which of the engine's own tools this project may use, as well as "
                "QUILL's. All off until you check them.",
                lambda: self._project_hooks.edit_engine_tools(self._runner),
            ),
        )
        self.project_buttons: dict[str, wx.Button] = {}
        for label, help_text, action in specs:
            button = wx.Button(panel, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, run=action: run())
            row.Add(button, 0, wx.RIGHT, _PAD)
            self.project_buttons[label.replace("&", "").rstrip(".")] = button
        sizer.Insert(sizer.GetItemCount() - 1, row, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        panel.Layout()

    # -- the task ------------------------------------------------------------------ #

    def _start(self, instruction: str) -> None:
        """Start a turn; the runner, and so the task's history, lives with the window."""
        self._approval.reset()
        self.ui.reset()
        coach = self.coach.GetValue()
        try:
            if self._runner is None:
                from quill.core.ai.approvals import UiThreadBridge

                self._host_bridge = UiThreadBridge(wx.CallAfter)
                runner = self._hooks.make_runner(self._approval, self.ui)
                runner.emit = self._emit
                self._runner = runner
            session = self._runner.start(instruction, coach=coach)
        except Exception as error:  # noqa: BLE001 - a task that cannot start says why
            said = str(error) or task_words.NO_ENGINE
            self._write(said)
            self._hooks.announce(said)
            return
        self._write(words.turn_started(len(self._runner.turns), coach))
        self._launch(session)

    def _launch(self, session: Any) -> None:
        runner = self._runner
        self._running = True
        self._reply = []
        self._replied = False
        self._told_waiting = False
        self.stop_button.Enable()
        self._set_status(task_words.WORKING)
        self._project_hooks.cue("ai_thinking_started")
        submit = self._hooks.submit or _thread_submit
        submit(
            "quill-ai-project-task",
            lambda **_k: runner.finish(session.run()),
            on_success=lambda _n, outcome: wx.CallAfter(self._turn_finished, outcome),
            on_failure=lambda _n, error: wx.CallAfter(self._failed, error),
        )

    def _turn_finished(self, outcome: Any) -> None:
        if self._runner is not None and self._runner.current_turn is not None:
            changes = self._runner.current_turn.changes
            if changes:
                self._mark("changes")
                self._write("Changes:\n" + "\n".join(f"- {c}" for c in changes))
        self._project_hooks.cue("ai_error" if outcome.error else "task_complete")
        self._finished(outcome)

    def stop(self) -> None:
        """Stop: the session, the running command's whole tree, and every open question."""
        if not self._running:
            return
        self.ui.cancel()
        for waiting in self._present_next:
            waiting.answer(waiting.default)
        self._present_next = []
        super().stop()

    def explain_last_turn(self) -> None:
        if self._running:
            return
        if self._runner is None or not self._runner.turns:
            self._hooks.announce(words.NOTHING_TO_EXPLAIN)
            return
        self._approval.reset()
        self.ui.reset()
        self._write(task_words.transcript_line("You", words.EXPLAIN_REQUEST))
        session = self._runner.explain_last_turn()
        if session is not None:
            self._launch(session)

    def undo_last_turn(self) -> None:
        if self._running:
            self._hooks.announce(words.UNDO_WHILE_RUNNING)
            return
        if self._runner is None:
            self._hooks.announce(words.NOTHING_TO_UNDO)
            return
        report = self._runner.undo_last_turn()
        self._write(report.sentence)
        self._hooks.announce(report.sentence)

    # -- what the runner sends ------------------------------------------------------ #

    def present(self, waiting: _Waiting) -> None:
        """Ask now if the person is in this window; otherwise say so once and wait."""
        if not self:
            waiting.answer(waiting.default)
            return
        if waiting.future.done():
            return
        if self.IsActive():
            self._ask_now(waiting)
            return
        self._present_next.append(waiting)
        self._set_status(words.WAITING_STATUS)
        if not self._told_waiting and wx.GetActiveWindow() is not None:
            # Elsewhere in QUILL: say it once. Outside QUILL: say nothing (5.3).
            self._told_waiting = True
            self._project_hooks.cue("question")
            self._hooks.announce(words.WAITING_ELSEWHERE)

    def _ask_now(self, waiting: _Waiting) -> None:
        value = waiting.default
        try:
            value = waiting.ask()
        finally:
            waiting.answer(value)
            if self and self._running:
                self._set_status(task_words.WORKING)

    def _on_activate(self, event: Any) -> None:
        event.Skip()
        if event.GetActive() and self._present_next:
            queued, self._present_next = self._present_next, []
            for waiting in queued:
                wx.CallAfter(self._ask_now, waiting)

    def show_plan(self, steps: list[str]) -> None:
        if not self:
            return
        self._flush_reply()
        self._mark("plan")
        self._write("Plan:\n" + "\n".join(f"{n}. {s}" for n, s in enumerate(steps, 1)))
        self._hooks.announce(words.plan_ready(len(steps)))

    def write(self, text: str) -> None:
        if self:
            self._flush_reply()
            self._write(text)

    def command_finished(self, sentence: str, output: Path, ok: bool) -> None:
        if not self:
            return
        self._flush_reply()
        self._write(sentence)
        self._project_hooks.cue("task_complete" if ok else "ai_error")
        self._hooks.announce(sentence)  # counts and failures are always spoken

    def files_were_changed(self, paths: list[Path]) -> None:
        self._project_hooks.files_changed(paths)

    # -- keys ------------------------------------------------------------------------- #

    def _mark(self, name: str) -> None:
        """Remember where the next block starts, for Plan and Changes."""
        end = self.transcript.GetLastPosition()
        self._marks[name] = end + (2 if end else 0)

    def _go_to(self, name: str, missing: str) -> None:
        where = self._marks.get(name)
        if where is None:
            self._hooks.announce(missing)
            return
        self.transcript.SetFocus()
        self.transcript.SetInsertionPoint(min(where, self.transcript.GetLastPosition()))

    def go_to_plan(self) -> None:
        self._go_to("plan", words.NO_PLAN_YET)

    def go_to_changes(self) -> None:
        self._go_to("changes", words.NO_CHANGES_YET)

    def open_output(self) -> None:
        output = getattr(self._runner, "last_output", None)
        if output is None or not Path(output).is_file():
            self._hooks.announce(words.NO_OUTPUT)
            return
        self._project_hooks.open_file(Path(output))

    def open_transcript(self) -> None:
        runner = self._runner
        if runner is None or not runner.turns:
            self._hooks.announce(words.NO_TRANSCRIPT_YET)
            return
        runner.save_history()
        self._project_hooks.open_file(runner.history_path)

    def _set_status(self, state: str) -> None:
        hooks = self._project_hooks if hasattr(self, "_project_hooks") else None
        if hooks is None:
            super()._set_status(state)
            return
        parts = [state] if state else []
        allow = getattr(self._runner, "allow_list", None)
        if allow is not None and allow.bypass:
            parts.append(words.BYPASS_ON_STATUS)
        if self.coach.GetValue():
            parts.append(words.COACH_STATUS)
        self.status.SetValue(
            words.status_line(
                hooks.connection, hooks.project, ". ".join(p.rstrip(".") for p in parts)
            )
        )


def _thread_submit(name: str, work: Any, *, on_success: Any, on_failure: Any) -> None:
    from quill.ui.update_download import thread_submit

    thread_submit(name, work, on_success=on_success, on_failure=on_failure)
