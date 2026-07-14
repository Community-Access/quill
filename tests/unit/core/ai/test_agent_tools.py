"""Shared agent tool surface: descriptors + execute_tool through the gateway."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.agent_tools import TOOL_DESCRIPTORS, execute_tool, tool_names
from quill.core.ai.events import AgentEvent
from quill.core.ai.permissions import PermissionBroker, RiskLevel, SafetyProfile
from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway


@dataclass
class FakeHost:
    selection: str = "sel"
    document: str = "doc body"
    replacements: list[str] = field(default_factory=list)
    doc_writes: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)

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

    def apply_insert(self, text: str) -> None: ...

    def apply_document_text(self, text: str) -> None:
        self.doc_writes.append(text)

    def run_command(self, command_id: str) -> None:
        self.commands.append(command_id)

    def confirm(self, message: str) -> bool:
        return True

    def preview_diff(self, review: object) -> bool:
        return True

    def announce(self, message: str) -> None: ...


def _gateway(tmp_path: Path, host: FakeHost) -> SafeEditorToolGateway:
    events: list[AgentEvent] = []
    return SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(SafetyProfile.POWER_USER),
        activity=ActivityLog(tmp_path / "a.json"),
        identity=AgentIdentity(agent_id="x", risk=RiskLevel.LOW),
        emit=events.append,
    )


def test_descriptors_and_names_consistent() -> None:
    assert tool_names() == tuple(d.name for d in TOOL_DESCRIPTORS)
    # Every descriptor has a non-empty name + description.
    for d in TOOL_DESCRIPTORS:
        assert d.name and d.description


def test_execute_read_tools(tmp_path: Path) -> None:
    host = FakeHost(selection="hello", document="the whole doc")
    gw = _gateway(tmp_path, host)
    assert execute_tool(gw, "read_selection", {}) == "hello"
    assert execute_tool(gw, "read_document", {}) == "the whole doc"
    assert execute_tool(gw, "read_outline", {}) == "Intro\nBody"


def test_execute_mutating_tools(tmp_path: Path) -> None:
    host = FakeHost()
    gw = _gateway(tmp_path, host)
    assert execute_tool(gw, "replace_selection", {"text": "NEW"}) == "True"
    assert host.replacements == ["NEW"]
    assert execute_tool(gw, "apply_patch", {"original": "a", "proposed": "b"}) == "True"
    assert host.doc_writes == ["b"]


def test_execute_run_command_floor(tmp_path: Path) -> None:
    host = FakeHost()
    gw = _gateway(tmp_path, host)
    # Not on the safe allowlist -> blocked (returns "False"); host never called.
    assert execute_tool(gw, "run_command", {"command_id": "file.delete_all"}) == "False"
    assert host.commands == []


def test_execute_unknown_tool_raises(tmp_path: Path) -> None:
    gw = _gateway(tmp_path, FakeHost())
    with pytest.raises(ValueError):
        execute_tool(gw, "frobnicate", {})
