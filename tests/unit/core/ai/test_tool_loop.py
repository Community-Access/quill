"""Native tool-calling loop: dispatch, permission recovery, caps, events."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.context_builder import ContextScope
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.harness import AgentSpec, AIContext
from quill.core.ai.permissions import PermissionBroker, RiskLevel, SafetyProfile
from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway
from quill.core.ai.tool_loop import ToolResult, ToolStep, run_tool_loop


@dataclass
class FakeHost:
    selection: str = "hello"
    document: str = "hello world"
    replacements: list[str] = field(default_factory=list)
    inserts: list[str] = field(default_factory=list)
    doc_writes: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    announces: list[str] = field(default_factory=list)

    def get_document(self) -> str:
        return self.document

    def get_selection(self) -> str:
        return self.selection

    def get_outline(self) -> list[str]:
        return ["Intro", "Body"]

    def get_file_type(self) -> str:
        return "md"

    def create_undo_checkpoint(self, label: str) -> None: ...

    def apply_replacement(self, text: str) -> None:
        self.replacements.append(text)

    def apply_insert(self, text: str) -> None:
        self.inserts.append(text)

    def apply_document_text(self, text: str) -> None:
        self.doc_writes.append(text)

    def run_command(self, command_id: str) -> None:
        self.commands.append(command_id)

    def confirm(self, message: str) -> bool:
        return True

    def preview_diff(self, review: object) -> bool:
        return True

    def announce(self, message: str) -> None:
        self.announces.append(message)


class ScriptedPlanner:
    """Returns a fixed list of steps in order, ignoring the transcript."""

    def __init__(self, steps: list[ToolStep]) -> None:
        self._steps = steps
        self._i = 0
        self.seen_transcripts: list[tuple[ToolResult, ...]] = []

    def next_step(self, agent, ctx, transcript):  # type: ignore[no-untyped-def]
        self.seen_transcripts.append(transcript)
        step = self._steps[self._i]
        self._i += 1
        return step


def _gateway(tmp_path: Path, host: FakeHost, events: list, profile=SafetyProfile.POWER_USER):
    return SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(profile),
        activity=ActivityLog(tmp_path / "a.json"),
        identity=AgentIdentity(agent_id="x", risk=RiskLevel.LOW),
        emit=events.append,
    )


def _agent() -> AgentSpec:
    return AgentSpec(
        id="x", display_name="X", system_prompt="do", default_scope=ContextScope.SELECTION
    )


def test_loop_reads_then_replaces_then_finishes(tmp_path: Path) -> None:
    host = FakeHost(selection="hello")
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)
    planner = ScriptedPlanner([
        ToolStep("tool", "read_selection"),
        ToolStep("tool", "replace_selection", {"text": "HELLO"}),
        ToolStep("final", final_text="done"),
    ])
    result = run_tool_loop(planner, _agent(), AIContext(prompt="p"), gw, events.append)
    assert result.status == "completed"
    assert result.final_text == "done"
    assert host.replacements == ["HELLO"]
    kinds = [e.kind for e in events]
    assert AgentEventKind.AGENT_STARTED in kinds
    assert AgentEventKind.TOOL_CALL_COMPLETED in kinds
    assert AgentEventKind.AGENT_COMPLETED in kinds


def test_loop_feeds_tool_output_into_transcript(tmp_path: Path) -> None:
    host = FakeHost(selection="abc")
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)
    planner = ScriptedPlanner([
        ToolStep("tool", "read_selection"),
        ToolStep("final", final_text="ok"),
    ])
    run_tool_loop(planner, _agent(), AIContext(prompt="p"), gw, events.append)
    # On the second call the planner saw the read result in the transcript.
    second_transcript = planner.seen_transcripts[1]
    assert second_transcript[-1].tool == "read_selection"
    assert second_transcript[-1].output == "abc"
    assert second_transcript[-1].ok is True


def test_loop_run_command_floor(tmp_path: Path) -> None:
    host = FakeHost()
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)
    planner = ScriptedPlanner([
        ToolStep("tool", "run_command", {"command_id": "file.delete_everything"}),
        ToolStep("final", final_text="stopped"),
    ])
    run_tool_loop(planner, _agent(), AIContext(prompt="p"), gw, events.append)
    assert host.commands == []  # blocked by SAFE_TOOL_IDS floor (returns False)


def test_loop_denied_permission_is_recoverable(tmp_path: Path) -> None:
    # Careful profile + read_document => ASK; host.confirm False => denied -> raise
    # inside the gateway -> recorded, loop continues to the next step.
    host_confirm_false = FakeHost()
    host_confirm_false.confirm = lambda m: False  # type: ignore[assignment]
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host_confirm_false, events, profile=SafetyProfile.BALANCED)
    planner = ScriptedPlanner([
        ToolStep("tool", "read_document"),  # will be denied
        ToolStep("final", final_text="recovered"),
    ])
    result = run_tool_loop(planner, _agent(), AIContext(prompt="p"), gw, events.append)
    assert result.status == "completed"
    assert result.final_text == "recovered"
    kinds = [e.kind for e in events]
    assert AgentEventKind.TOOL_CALL_DENIED in kinds


def test_loop_unknown_tool_errors(tmp_path: Path) -> None:
    host = FakeHost()
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)
    planner = ScriptedPlanner([ToolStep("tool", "frobnicate")])
    result = run_tool_loop(planner, _agent(), AIContext(prompt="p"), gw, events.append)
    assert result.status == "error"
    assert "frobnicate" in result.error
    assert AgentEventKind.ERROR in [e.kind for e in events]


def test_loop_respects_max_steps(tmp_path: Path) -> None:
    host = FakeHost()
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)
    # A planner that never finishes; the cap must stop it.
    planner = ScriptedPlanner([ToolStep("tool", "read_selection")] * 10)
    result = run_tool_loop(planner, _agent(), AIContext(prompt="p"), gw, events.append, max_steps=3)
    assert result.status == "completed"
    assert AgentEventKind.WARNING in [e.kind for e in events]


def test_loop_stops_after_one_applied_edit(tmp_path: Path) -> None:
    # A planner that keeps trying to insert (the real-world looping bug): the loop
    # must apply exactly one edit, then finish instead of duplicating it.
    host = FakeHost()
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)
    planner = ScriptedPlanner([
        ToolStep("tool", "insert", {"text": "para. "}),
        ToolStep("tool", "insert", {"text": "para again. "}),
        ToolStep("tool", "insert", {"text": "and again. "}),
    ])
    result = run_tool_loop(planner, _agent(), AIContext(prompt="p"), gw, events.append)
    assert result.status == "completed"
    assert host.inserts == ["para. "]  # only the first edit applied
    assert "Done." in result.final_text  # human completion, not a raw "True"
    assert AgentEventKind.AGENT_COMPLETED in [e.kind for e in events]


def test_loop_allows_read_after_edit_then_final(tmp_path: Path) -> None:
    # An edit followed by a read then a final answer is allowed (only a *second
    # edit* is blocked), so the model can still finish with a useful answer.
    host = FakeHost(selection="x")
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)
    planner = ScriptedPlanner([
        ToolStep("tool", "replace_selection", {"text": "y"}),
        ToolStep("tool", "read_document"),
        ToolStep("final", final_text="I replaced the selection."),
    ])
    result = run_tool_loop(planner, _agent(), AIContext(prompt="p"), gw, events.append)
    assert result.status == "completed"
    assert result.final_text == "I replaced the selection."
    assert host.replacements == ["y"]


def test_loop_apply_patch_writes_document(tmp_path: Path) -> None:
    host = FakeHost(document="old doc")
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)
    planner = ScriptedPlanner([
        ToolStep("tool", "apply_patch", {"original": "old doc", "proposed": "new doc"}),
        ToolStep("final", final_text="done"),
    ])
    run_tool_loop(planner, _agent(), AIContext(prompt="p"), gw, events.append)
    assert host.doc_writes == ["new doc"]
