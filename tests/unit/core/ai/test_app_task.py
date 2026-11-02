"""Agent tasks in the QuillVille apps: the shared runner (codex.md 6, Phase 4c)."""

from __future__ import annotations

from typing import Any

from quill.core.ai.app_task import FAMILY_TASK_RULES, AppTaskRunner, AppTaskSpec
from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.family_tools import FamilyTool
from quill.core.ai.harness import HarnessCapabilities, HarnessResult
from quill.core.ai.permissions import PermissionCategory


class _Session:
    def __init__(self, registry, approver, script) -> None:
        self.registry = registry
        self.approver = approver
        self.script = script
        self.cancelled = False

    @property
    def session_id(self) -> str:
        return "s"

    def run(self) -> HarnessResult:
        self.registry.gate.begin_task(self.approver)
        try:
            for name, args in self.script:
                self.registry.call(name, args)
            return HarnessResult("completed", "All set.")
        finally:
            self.registry.gate.end_task()

    def cancel(self) -> None:
        self.cancelled = True

    def send(self, _text: str) -> None:
        pass

    def end(self) -> None:
        pass


class _Harness:
    id = "copilot"
    display_name = "GitHub Copilot"

    def __init__(self, script) -> None:
        self.script = script
        self.started: list[Any] = []

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities(app_tools=True)

    def start_tool_session(self, agent, ctx, tools, approver, emit, **_kw):
        self.started.append((agent, ctx, tools))
        return _Session(tools, approver, self.script)


class _Approver:
    def __init__(self, choice: ApprovalChoice) -> None:
        self.choice = choice
        self.asked: list[str] = []

    def ask(self, tool, summary: str) -> ApprovalChoice:
        self.asked.append(summary)
        return self.choice


def _tools(log: list[str]) -> list[FamilyTool]:
    return [
        FamilyTool(
            name="radio.find",
            description="Find stations.",
            handler=lambda a: "1. Jazz FM",
            app="radio",
            category=PermissionCategory.READ_WORKSPACE,
        ),
        FamilyTool(
            name="radio.schedule",
            description="Schedule a recording.",
            handler=lambda a: log.append("scheduled") or "Scheduled.",
            app="radio",
            category=PermissionCategory.SCHEDULE,
            mutating=True,
            summarize=lambda a: "Record Jazz FM tonight at 8 for an hour.",
        ),
    ]


_SPEC = AppTaskSpec(
    app="radio",
    agent_id="radio-task",
    title="Find and Record",
    instructions="Help the listener find stations.",
    done_words={"radio.schedule": "Scheduled a recording"},
    noun="change",
)


def test_reads_run_without_asking_and_writes_ask_then_are_summarized() -> None:
    log: list[str] = []
    harness = _Harness([("radio_find", {}), ("radio_schedule", {})])
    approver = _Approver(ApprovalChoice.ONCE)
    runner = AppTaskRunner(harness, approver, _SPEC, tools=lambda: _tools(log))

    outcome = runner.run("Record some jazz tonight")

    assert approver.asked == ["Record Jazz FM tonight at 8 for an hour."]
    assert log == ["scheduled"]
    assert outcome.summary == "Done. 1 change made: Scheduled a recording."
    assert outcome.answer == "All set."
    agent, ctx, _tools_registry = harness.started[0]
    assert agent.system_prompt.endswith(FAMILY_TASK_RULES)
    assert "charts" in FAMILY_TASK_RULES
    assert ctx.prompt == "Record some jazz tonight"


def test_a_refused_step_never_runs_and_is_counted() -> None:
    log: list[str] = []
    harness = _Harness([("radio_schedule", {})])
    runner = AppTaskRunner(
        harness, _Approver(ApprovalChoice.DENY), _SPEC, tools=lambda: _tools(log)
    )
    outcome = runner.run("Record it")
    assert log == []
    assert outcome.summary == "Done. Nothing was changed. 1 proposed step was not taken."


def test_the_context_goes_with_the_first_instruction() -> None:
    harness = _Harness([])
    runner = AppTaskRunner(
        harness,
        _Approver(ApprovalChoice.DENY),
        _SPEC,
        tools=lambda: _tools([]),
        context=lambda: "Playing: Jazz FM",
    )
    runner.run("What is on?")
    assert harness.started[0][1].context_text == "Playing: Jazz FM"


def test_tools_are_built_afresh_for_each_task() -> None:
    built: list[int] = []

    def tools() -> list[FamilyTool]:
        built.append(1)
        return _tools([])

    runner = AppTaskRunner(_Harness([]), _Approver(ApprovalChoice.DENY), _SPEC, tools=tools)
    runner.run("one")
    runner.run("two")
    assert len(built) == 2
