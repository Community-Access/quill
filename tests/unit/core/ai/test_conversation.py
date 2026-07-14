"""Multi-turn conversational session: Q&A vs edit, memory, error propagation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.context_builder import ContextScope
from quill.core.ai.conversation import ConversationSession, TurnResult
from quill.core.ai.harness import AgentSpec
from quill.core.ai.permissions import PermissionBroker, RiskLevel, SafetyProfile
from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway
from quill.core.ai.tool_loop import ToolStep


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
        self.seen_prompts: list[str] = []

    def next_step(self, agent, ctx, transcript):  # type: ignore[no-untyped-def]
        self.seen_prompts.append(ctx.prompt)
        step = self._steps[self._i]
        self._i += 1
        return step


def _gateway(tmp_path: Path, host: FakeHost, profile=SafetyProfile.POWER_USER):
    return SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(profile),
        activity=ActivityLog(tmp_path / "a.json"),
        identity=AgentIdentity(agent_id="x", risk=RiskLevel.LOW),
    )


def _agent() -> AgentSpec:
    return AgentSpec(
        id="x", display_name="X", system_prompt="do", default_scope=ContextScope.SELECTION
    )


def test_question_turn_answers_without_editing(tmp_path: Path) -> None:
    host = FakeHost(document="The shuttle launched in 1981.")
    planner = ScriptedPlanner([
        ToolStep("tool", "read_document"),
        ToolStep("final", final_text="It launched in 1981."),
    ])
    session = ConversationSession(_agent(), _gateway(tmp_path, host), planner)

    result = session.ask("When did it launch?", context_text=host.document)

    assert isinstance(result, TurnResult)
    assert result.status == "completed"
    assert result.answer == "It launched in 1981."
    assert result.edited is False
    assert result.tools_used == ("read_document",)
    assert host.replacements == [] and host.doc_writes == []


def test_edit_turn_reports_edited(tmp_path: Path) -> None:
    host = FakeHost(selection="teh cat")
    planner = ScriptedPlanner([
        ToolStep("tool", "replace_selection", {"text": "the cat"}),
        ToolStep("final", final_text="Fixed the typo."),
    ])
    session = ConversationSession(_agent(), _gateway(tmp_path, host), planner)

    result = session.ask("Fix the typo in the selection.", context_text=host.selection)

    assert result.edited is True
    assert host.replacements == ["the cat"]
    assert "replace_selection" in result.tools_used


def test_declined_preview_is_not_an_edit(tmp_path: Path) -> None:
    # BALANCED profile makes a whole-document patch preview-required; a host that
    # declines the preview means nothing applied -> not an edit.
    host = FakeHost(document="old")
    host.preview_diff = lambda review: False  # type: ignore[assignment]
    planner = ScriptedPlanner([
        ToolStep("tool", "apply_patch", {"original": "old", "proposed": "new"}),
        ToolStep("final", final_text="Proposed a rewrite."),
    ])
    session = ConversationSession(
        _agent(), _gateway(tmp_path, host, profile=SafetyProfile.BALANCED), planner
    )

    result = session.ask("Rewrite the whole thing.", context_text=host.document)

    assert result.edited is False
    assert host.doc_writes == []


def test_memory_threads_prior_turns_into_prompt(tmp_path: Path) -> None:
    host = FakeHost()
    planner = ScriptedPlanner([
        ToolStep("final", final_text="The shuttle."),
        ToolStep("final", final_text="Challenger, in 1986."),
    ])
    session = ConversationSession(_agent(), _gateway(tmp_path, host), planner)

    session.ask("What is this about?")
    session.ask("Which disaster?")

    # The first turn's prompt is just the question; the second carries memory.
    assert "Conversation so far" not in planner.seen_prompts[0]
    second = planner.seen_prompts[1]
    assert "What is this about?" in second
    assert "The shuttle." in second
    assert second.rstrip().endswith("User: Which disaster?")
    assert len(session.turns) == 4  # user/assistant x2


def test_empty_message_is_rejected(tmp_path: Path) -> None:
    host = FakeHost()
    planner = ScriptedPlanner([])
    session = ConversationSession(_agent(), _gateway(tmp_path, host), planner)

    result = session.ask("   ")

    assert result.status == "error"
    assert result.answer == ""
    assert session.turns == ()


def test_loop_error_propagates(tmp_path: Path) -> None:
    host = FakeHost()
    planner = ScriptedPlanner([ToolStep("tool", "frobnicate")])  # unknown tool
    session = ConversationSession(_agent(), _gateway(tmp_path, host), planner)

    result = session.ask("do a thing")

    assert result.status == "error"
    assert "frobnicate" in result.error
    assert result.edited is False
