"""Harness registry, capabilities, and the Native harness end-to-end."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.context_builder import ContextScope
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.harness import (
    AgentSpec,
    AIContext,
    HarnessCapabilities,
    HarnessRegistry,
)
from quill.core.ai.harness.native import NativeHarness, register
from quill.core.ai.permissions import PermissionBroker, RiskLevel, SafetyProfile
from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway


@dataclass
class FakeHost:
    selection: str = "old"
    document: str = "old document"
    replacements: list[str] = field(default_factory=list)
    inserts: list[str] = field(default_factory=list)
    checkpoints: list[str] = field(default_factory=list)
    announcements: list[str] = field(default_factory=list)

    def get_document(self) -> str:
        return self.document

    def get_selection(self) -> str:
        return self.selection

    def get_outline(self) -> list[str]:
        return []

    def get_file_type(self) -> str:
        return "markdown"

    def create_undo_checkpoint(self, label: str) -> None:
        self.checkpoints.append(label)

    def apply_replacement(self, text: str) -> None:
        self.replacements.append(text)

    def apply_insert(self, text: str) -> None:
        self.inserts.append(text)

    def apply_document_text(self, text: str) -> None:
        self.document = text

    def run_command(self, command_id: str) -> None: ...

    def confirm(self, message: str) -> bool:
        return True

    def preview_diff(self, review: object) -> bool:
        return True

    def announce(self, message: str) -> None:
        self.announcements.append(message)


def _gateway(tmp_path: Path, host: FakeHost, events: list[AgentEvent]) -> SafeEditorToolGateway:
    return SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(SafetyProfile.POWER_USER),
        activity=ActivityLog(tmp_path / "a.json"),
        identity=AgentIdentity(agent_id="writing-companion", risk=RiskLevel.LOW),
        emit=events.append,
    )


def _agent(scope: ContextScope = ContextScope.SELECTION) -> AgentSpec:
    return AgentSpec(
        id="writing-companion",
        display_name="Writing Companion",
        system_prompt="Improve the text.",
        default_scope=scope,
    )


def test_registry_register_get_all() -> None:
    reg = HarnessRegistry()
    h = register(reg, lambda a, c: "x")
    assert reg.get("native") is h
    assert [x.id for x in reg.all()] == ["native"]
    assert [x.id for x in reg.available()] == ["native"]


def test_registry_resolve_auto_falls_back_to_native() -> None:
    reg = HarnessRegistry()
    register(reg, lambda a, c: "x")
    assert reg.resolve("auto").id == "native"
    assert reg.resolve("nonexistent").id == "native"  # unknown -> first available


def test_native_capabilities_baseline() -> None:
    caps = NativeHarness(lambda a, c: "x").capabilities()
    assert isinstance(caps, HarnessCapabilities)
    assert caps.chat and caps.tool_calling and caps.patch_generation
    assert caps.requires_api_key is False


def test_native_session_replaces_selection_via_gateway(tmp_path: Path) -> None:
    host = FakeHost(selection="old")
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)
    harness = NativeHarness(lambda agent, ctx: "improved text")
    session = harness.start_session(
        _agent(), AIContext(prompt="make it better"), gw, PermissionBroker(), events.append
    )
    result = session.run()
    assert result.ok
    assert result.final_text == "improved text"
    assert host.replacements == ["improved text"]
    kinds = [e.kind for e in events]
    assert AgentEventKind.AGENT_STARTED in kinds
    assert AgentEventKind.AGENT_COMPLETED in kinds


def test_native_session_inserts_for_nonselection_scope(tmp_path: Path) -> None:
    host = FakeHost()
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)
    harness = NativeHarness(lambda agent, ctx: "drafted")
    session = harness.start_session(
        _agent(ContextScope.FULL_DOCUMENT),
        AIContext(prompt="draft"),
        gw,
        PermissionBroker(),
        events.append,
    )
    session.run()
    assert host.inserts == ["drafted"]


def test_native_session_cancel_before_run(tmp_path: Path) -> None:
    host = FakeHost()
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)
    harness = NativeHarness(lambda agent, ctx: "x")
    session = harness.start_session(
        _agent(), AIContext(prompt="p"), gw, PermissionBroker(), events.append
    )
    session.cancel()
    result = session.run()
    assert result.status == "cancelled"
    assert host.replacements == []
    assert AgentEventKind.AGENT_CANCELLED in [e.kind for e in events]


def test_native_session_responder_error_is_contained(tmp_path: Path) -> None:
    host = FakeHost()
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, host, events)

    def boom(agent: AgentSpec, ctx: AIContext) -> str:
        raise RuntimeError("model down")

    harness = NativeHarness(boom)
    session = harness.start_session(
        _agent(), AIContext(prompt="p"), gw, PermissionBroker(), events.append
    )
    result = session.run()
    assert result.status == "error"
    assert "model down" in result.error
    assert AgentEventKind.ERROR in [e.kind for e in events]
