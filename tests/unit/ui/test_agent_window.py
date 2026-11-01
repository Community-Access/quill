"""Do a Document Task: the agent window with a fake engine (codex.md 5.2, 5.3, 6.2).

The window, the approval bridge, the editor host, the task runner, the tool
registry and the gateway are all real; only the engine is a script, and the
worker runs inline so each assertion sees the finished task. The approval
dialog's answer is patched where the window asks it (``ask_approval``).
"""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.document_task import DocumentTaskRunner
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.harness import HarnessCapabilities, HarnessResult
from quill.core.ai.permissions import PermissionBroker
from quill.ui import agent_window as module
from quill.ui.agent_task_host import AgentTaskHost
from quill.ui.agent_window import AgentTaskHooks, AgentWindow


class _Session:
    """Calls each scripted tool through the registry, the way an engine does."""

    def __init__(self, tools, approver, emit, script, *, block: threading.Event | None):
        self.tools = tools
        self.approver = approver
        self.emit = emit
        self.script = script
        self.block = block
        self.cancelled = False
        self.sent: list[str] = []

    @property
    def session_id(self) -> str:
        return "fake"

    def run(self) -> HarnessResult:
        self.tools.gate.begin_task(self.approver)
        try:
            for name, args in self.script:
                if self.cancelled:
                    break
                self.tools.call(name, args)
            if self.block is not None and not self.cancelled:
                return HarnessResult("cancelled")
            self.emit(AgentEvent(AgentEventKind.AGENT_TEXT_DELTA, "I bolded the "))
            self.emit(AgentEvent(AgentEventKind.AGENT_TEXT_DELTA, "selection."))
            return HarnessResult("cancelled" if self.cancelled else "completed", "I bolded it.")
        finally:
            self.tools.gate.end_task()

    def cancel(self) -> None:
        self.cancelled = True

    def send(self, follow_up: str) -> None:
        self.sent.append(follow_up)

    def end(self) -> None:
        pass


class _Harness:
    id = "copilot"
    display_name = "GitHub Copilot"

    def __init__(self, script, block: threading.Event | None = None) -> None:
        self.script = script
        self.block = block
        self.sessions: list[_Session] = []

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities(app_tools=True)

    def start_tool_session(self, agent, ctx, tools, approver, emit, **_kwargs) -> _Session:
        session = _Session(tools, approver, emit, self.script, block=self.block)
        self.sessions.append(session)
        return session


@pytest.fixture
def world(wx_session_app, monkeypatch, wx_call_after, tmp_path: Path):
    wx_call_after()  # the approval bridge and the host post inline, as the UI thread would
    editor_frame = wx.Frame(None)
    editor = wx.TextCtrl(editor_frame, value="Hello world.", style=wx.TE_MULTILINE)
    commands: list[str] = []
    said: list[str] = []
    answers: list[ApprovalChoice] = []
    asked: list[str] = []

    def answer(_parent, summary):
        asked.append(summary)
        return answers.pop(0) if answers else ApprovalChoice.DENY

    monkeypatch.setattr(module, "ask_approval", answer)
    built: list[AgentWindow] = []

    def make(harness: _Harness, *, submit=None) -> AgentWindow:
        hooks = AgentTaskHooks(
            announce=said.append,
            connection="copilot",
            make_runner=lambda approver, host: DocumentTaskRunner(
                harness=harness,
                host=host,
                approver=approver,
                broker=PermissionBroker(),
                activity=ActivityLog(tmp_path / "activity.json"),
            ),
            make_host=lambda bridge, note: AgentTaskHost(
                bridge,
                control=lambda: editor,
                parent=lambda: editor_frame,
                note=note,
                run_command=commands.append,
            ),
            submit=submit or _inline,
        )
        window = AgentWindow(None, hooks)
        built.append(window)
        return window

    yield SimpleNamespace(
        make=make, commands=commands, said=said, answers=answers, asked=asked, editor=editor
    )
    for window in built:
        if window:
            window.Destroy()
    editor_frame.Destroy()


def _inline(name, work, *, on_success, on_failure):
    try:
        result = work()
    except BaseException as error:  # noqa: BLE001 - as the worker would
        on_failure(name, error)
    else:
        on_success(name, result)


_BOLD = [("doc.run_command", {"command_id": "format.bold"})]


def _type(window: AgentWindow, text: str) -> None:
    window.instruction.SetValue(text)
    window.send()


def test_the_controls_and_the_status_line_name_the_engine(world) -> None:
    window = world.make(_Harness([]))
    assert window.GetTitle() == "Do a Document Task"
    assert window.status.GetValue() == "Using GitHub Copilot"
    assert window._focus_target is window.instruction
    assert not window.stop_button.IsEnabled()


def test_allow_once_runs_the_step_and_the_summary_is_spoken_once(world) -> None:
    world.answers.append(ApprovalChoice.ONCE)
    window = world.make(_Harness(_BOLD))

    _type(window, "Bold the selection.")

    assert world.asked and "format.bold" in world.asked[0]
    assert world.commands == ["format.bold"]
    assert world.said == [
        "Done. 1 change applied: Ran a command. Each can be undone with Control Z."
    ]
    transcript = window.transcript.GetValue()
    assert "You: Bold the selection." in transcript
    assert "GitHub Copilot: I bolded the selection." in transcript
    assert transcript.rstrip().endswith(world.said[0])


def test_dont_allow_runs_nothing_and_says_so_in_the_summary(world) -> None:
    world.answers.append(ApprovalChoice.DENY)
    window = world.make(_Harness(_BOLD))

    _type(window, "Bold it.")

    assert world.commands == []
    assert world.said == [
        "Done. No changes were made to the document. 1 proposed change was not applied."
    ]


def test_allow_for_this_task_asks_once_for_two_steps_and_afresh_next_task(world) -> None:
    world.answers.extend([ApprovalChoice.TASK, ApprovalChoice.ONCE, ApprovalChoice.ONCE])
    harness = _Harness(_BOLD * 2)
    window = world.make(harness)

    _type(window, "Bold it twice.")
    assert len(world.asked) == 1 and world.commands == ["format.bold", "format.bold"]

    _type(window, "And again.")  # a new task: nothing carried over
    assert len(world.asked) == 3


def test_stop_cancels_the_session_and_releases_an_open_question(world) -> None:
    jobs: list[Any] = []
    harness = _Harness([], block=threading.Event())
    window = world.make(harness, submit=lambda name, work, **k: jobs.append((name, work, k)))

    _type(window, "A long task.")
    assert window.stop_button.IsEnabled()
    assert window.status.GetValue() == "Using GitHub Copilot. Working."

    window.stop()

    assert harness.sessions[0].cancelled is True
    assert window._approval.thread_bridge.cancelled is True
    assert window.status.GetValue() == "Using GitHub Copilot. Stopping."
    name, work, callbacks = jobs[0]
    callbacks["on_success"](name, work())  # the worker returns once stopped
    assert world.said[-1].startswith("Stopped.")
    assert not window.stop_button.IsEnabled()


def test_typing_while_a_task_runs_sends_a_follow_up(world) -> None:
    jobs: list[Any] = []
    harness = _Harness([], block=threading.Event())
    window = world.make(harness, submit=lambda name, work, **k: jobs.append(work))

    _type(window, "Start.")
    _type(window, "Also fix the title.")

    assert harness.sessions[0].sent == ["Also fix the title."]
    assert len(harness.sessions) == 1


def test_an_edit_is_reviewed_before_it_is_applied_and_is_one_undo(world, monkeypatch) -> None:
    import quill.ui.ai_diff_review_dialog as review

    shown: list[tuple[str, str]] = []

    class _Review:
        def __init__(self, _parent, *, title, original_text, revised_text, on_apply, announce):
            shown.append((original_text, revised_text))
            self.apply = lambda: on_apply(revised_text)

        def show_modal(self) -> None:
            self.apply()  # Accept All

    monkeypatch.setattr(review, "DiffReviewDialog", _Review)
    patch = [("doc.apply_patch", {"original": "Hello world.", "proposed": "Hello, world."})]
    window = world.make(_Harness(patch))

    _type(window, "Add a comma.")

    assert shown == [("Hello world.", "Hello, world.")]
    assert world.editor.GetValue() == "Hello, world."  # applied once, not twice
    assert world.said[0].startswith("Done. 1 change applied: Changed the document.")


def test_closing_a_running_task_stops_it(world) -> None:
    harness = _Harness([], block=threading.Event())
    window = world.make(harness, submit=lambda *a, **k: None)
    _type(window, "Start.")

    window.Close()

    assert harness.sessions[0].cancelled is True
