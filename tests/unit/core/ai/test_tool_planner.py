"""Prompt-based tool-calling planner: parsing + end-to-end loop drive."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.context_builder import ContextScope
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.harness import AgentSpec, AIContext
from quill.core.ai.permissions import PermissionBroker, RiskLevel, SafetyProfile
from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway
from quill.core.ai.tool_loop import ToolResult, run_tool_loop
from quill.core.ai.tool_planner import (
    PromptToolPlanner,
    model_responder_from_backend,
)


def _agent() -> AgentSpec:
    return AgentSpec(
        id="x",
        display_name="X",
        system_prompt="Improve the document.",
        default_scope=ContextScope.SELECTION,
    )


def _ctx() -> AIContext:
    return AIContext(prompt="make it better", context_text="the cat sat on the mat")


def test_parse_tool_action() -> None:
    planner = PromptToolPlanner(lambda p: '{"action":"tool","tool":"read_selection","args":{}}')
    step = planner.next_step(_agent(), _ctx(), ())
    assert step.kind == "tool"
    assert step.tool == "read_selection"


def test_parse_action_is_tool_name_with_top_level_args() -> None:
    # Deviant but common: the tool name is the action and args are at the top level
    # (mid-size models do this). It must still be recognized as a tool call.
    planner = PromptToolPlanner(
        lambda p: '```json\n{"action": "insert", "text": "hello there"}\n```'
    )
    step = planner.next_step(_agent(), _ctx(), ())
    assert step.kind == "tool"
    assert step.tool == "insert"
    assert step.args == {"text": "hello there"}


def test_parse_bare_tool_field() -> None:
    planner = PromptToolPlanner(lambda p: '{"tool": "read_document", "args": {"scope": "full"}}')
    step = planner.next_step(_agent(), _ctx(), ())
    assert step.kind == "tool"
    assert step.tool == "read_document"
    assert step.args == {"scope": "full"}


def test_parse_tool_with_args() -> None:
    planner = PromptToolPlanner(
        lambda p: 'sure: {"action":"tool","tool":"replace_selection","args":{"text":"HELLO"}} done'
    )
    step = planner.next_step(_agent(), _ctx(), ())
    assert step.tool == "replace_selection"
    assert step.args == {"text": "HELLO"}


def test_parse_final_action() -> None:
    planner = PromptToolPlanner(lambda p: '{"action":"final","final_text":"all done"}')
    step = planner.next_step(_agent(), _ctx(), ())
    assert step.kind == "final"
    assert step.final_text == "all done"


def test_malformed_json_degrades_to_final() -> None:
    planner = PromptToolPlanner(lambda p: "I cannot produce JSON, but here is the answer.")
    step = planner.next_step(_agent(), _ctx(), ())
    assert step.kind == "final"
    assert "answer" in step.final_text


def test_broken_json_object_degrades_to_final() -> None:
    planner = PromptToolPlanner(lambda p: '{"action": "tool", "tool": ')  # truncated
    step = planner.next_step(_agent(), _ctx(), ())
    assert step.kind == "final"


def test_prompt_includes_tools_and_transcript() -> None:
    captured: dict[str, str] = {}

    def responder(prompt: str) -> str:
        captured["p"] = prompt
        return '{"action":"final","final_text":"x"}'

    planner = PromptToolPlanner(responder)
    transcript = (ToolResult("read_selection", ok=True, output="the cat"),)
    planner.next_step(_agent(), _ctx(), transcript)
    assert "read_selection" in captured["p"]
    assert "replace_selection" in captured["p"]
    assert "the cat" in captured["p"]  # transcript surfaced
    assert "make it better" in captured["p"]  # task surfaced


# -- end to end: planner drives the real loop + gateway -----------------------


@dataclass
class FakeHost:
    selection: str = "the cat sat on the mat"
    replacements: list[str] = field(default_factory=list)

    def get_document(self) -> str:
        return self.selection

    def get_selection(self) -> str:
        return self.selection

    def get_outline(self) -> list[str]:
        return []

    def get_file_type(self) -> str:
        return "md"

    def create_undo_checkpoint(self, label: str) -> None: ...

    def apply_replacement(self, text: str) -> None:
        self.replacements.append(text)
        self.selection = text

    def apply_insert(self, text: str) -> None: ...
    def apply_document_text(self, text: str) -> None: ...
    def run_command(self, command_id: str) -> None: ...

    def confirm(self, message: str) -> bool:
        return True

    def preview_diff(self, review: object) -> bool:
        return True

    def announce(self, message: str) -> None: ...


class ScriptedBackend:
    """A fake model: returns scripted JSON steps in order (read -> replace -> final)."""

    def __init__(self) -> None:
        self._script = [
            '{"action":"tool","tool":"read_selection","args":{}}',
            '{"action":"tool","tool":"replace_selection","args":{"text":"A cozy cat."}}',
            '{"action":"final","final_text":"done"}',
        ]
        self._i = 0

    def respond(self, prompt: str) -> str:
        out = self._script[min(self._i, len(self._script) - 1)]
        self._i += 1
        return out


def test_planner_drives_loop_end_to_end(tmp_path: Path) -> None:
    host = FakeHost()
    events: list[AgentEvent] = []
    gw = SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(SafetyProfile.POWER_USER),
        activity=ActivityLog(tmp_path / "a.json"),
        identity=AgentIdentity(agent_id="x", risk=RiskLevel.LOW),
        emit=events.append,
    )
    planner = PromptToolPlanner(model_responder_from_backend(ScriptedBackend()))
    result = run_tool_loop(planner, _agent(), _ctx(), gw, events.append)
    assert result.status == "completed"
    assert result.final_text == "done"
    assert host.selection == "A cozy cat."  # the agent edited the document via the gateway
    assert AgentEventKind.PATCH_APPLIED in [e.kind for e in events]
