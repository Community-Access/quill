"""SafeEditorToolGateway: permission enforcement, preview routing, audit, events."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.agent import SAFE_TOOL_IDS
from quill.core.ai.diff_review import DiffReview
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.permissions import PermissionBroker, RiskLevel, SafetyProfile
from quill.core.ai.tool_gateway import (
    AgentIdentity,
    PermissionDeniedError,
    SafeEditorToolGateway,
)


@dataclass
class FakeHost:
    """In-memory EditorHost for tests."""

    document: str = "line one\nline two\n"
    selection: str = "line one"
    outline: list[str] = field(default_factory=lambda: ["Heading A", "Heading B"])
    file_type: str = "markdown"
    confirm_returns: bool = True
    preview_returns: bool = True

    checkpoints: list[str] = field(default_factory=list)
    replacements: list[str] = field(default_factory=list)
    inserts: list[str] = field(default_factory=list)
    document_writes: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    announcements: list[str] = field(default_factory=list)
    previews: list[DiffReview] = field(default_factory=list)

    def get_document(self) -> str:
        return self.document

    def get_selection(self) -> str:
        return self.selection

    def get_outline(self) -> list[str]:
        return self.outline

    def get_file_type(self) -> str:
        return self.file_type

    def create_undo_checkpoint(self, label: str) -> None:
        self.checkpoints.append(label)

    def apply_replacement(self, text: str) -> None:
        self.replacements.append(text)

    def apply_insert(self, text: str) -> None:
        self.inserts.append(text)

    def apply_document_text(self, text: str) -> None:
        self.document_writes.append(text)

    def run_command(self, command_id: str) -> None:
        self.commands.append(command_id)

    def confirm(self, message: str) -> bool:
        return self.confirm_returns

    def preview_diff(self, review: DiffReview) -> bool:
        self.previews.append(review)
        return self.preview_returns

    def announce(self, message: str) -> None:
        self.announcements.append(message)


def _gateway(
    tmp_path: Path,
    host: FakeHost,
    *,
    profile: SafetyProfile = SafetyProfile.BALANCED,
    risk: RiskLevel = RiskLevel.LOW,
) -> tuple[SafeEditorToolGateway, list[AgentEvent], ActivityLog]:
    events: list[AgentEvent] = []
    log = ActivityLog(tmp_path / "activity.json")
    gw = SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(profile),
        activity=log,
        identity=AgentIdentity(agent_id="tester", risk=risk),
        emit=events.append,
    )
    return gw, events, log


def test_read_selection_allowed_and_logged(tmp_path: Path) -> None:
    host = FakeHost()
    gw, _events, log = _gateway(tmp_path, host)
    assert gw.read_selection() == "line one"
    assert log.all()[-1].kind == "tool_call_completed"


def test_read_document_asks_and_can_be_declined(tmp_path: Path) -> None:
    host = FakeHost(confirm_returns=False)
    gw, _events, log = _gateway(tmp_path, host)
    with pytest.raises(PermissionDeniedError):
        gw.read_current_document()
    assert log.all()[-1].kind == "tool_call_denied"


def test_replace_selection_requires_preview_under_balanced(tmp_path: Path) -> None:
    host = FakeHost()
    gw, events, log = _gateway(tmp_path, host)
    assert gw.replace_selection("better text", label="Rewrite") is True
    # Preview was shown and accepted, then applied with a checkpoint.
    assert len(host.previews) == 1
    assert host.checkpoints == ["Rewrite"]
    assert host.replacements == ["better text"]
    kinds = [e.kind for e in events]
    assert AgentEventKind.PATCH_PROPOSED in kinds
    assert AgentEventKind.PATCH_APPLIED in kinds
    last = log.last_undoable()
    assert last is not None and last.undo_label == "Rewrite"


def test_replace_selection_cancelled_at_preview_does_not_apply(tmp_path: Path) -> None:
    host = FakeHost(preview_returns=False)
    gw, events, _log = _gateway(tmp_path, host)
    assert gw.replace_selection("nope") is False
    assert host.checkpoints == []
    assert host.replacements == []
    assert AgentEventKind.TOOL_CALL_DENIED in [e.kind for e in events]


def test_power_user_applies_selection_without_preview(tmp_path: Path) -> None:
    host = FakeHost()
    gw, _events, _log = _gateway(tmp_path, host, profile=SafetyProfile.POWER_USER)
    assert gw.replace_selection("instant", label="Quick") is True
    assert host.previews == []  # ALLOW -> no preview
    assert host.replacements == ["instant"]


def test_apply_text_patch_previews_by_default(tmp_path: Path) -> None:
    host = FakeHost()
    gw, _events, _log = _gateway(tmp_path, host)
    ok = gw.apply_text_patch("old\n", "new\n", label="Clean up")
    assert ok is True
    assert len(host.previews) == 1
    assert host.document_writes == ["new\n"]


def test_run_quill_command_floor_blocks_unlisted(tmp_path: Path) -> None:
    host = FakeHost()
    gw, events, log = _gateway(tmp_path, host, profile=SafetyProfile.POWER_USER)
    assert gw.run_quill_command("file.delete_everything") is False
    assert host.commands == []
    assert log.all()[-1].kind == "tool_call_denied"
    assert AgentEventKind.TOOL_CALL_DENIED in [e.kind for e in events]


def test_run_quill_command_allows_safe_tool(tmp_path: Path) -> None:
    host = FakeHost()
    gw, _events, _log = _gateway(tmp_path, host, profile=SafetyProfile.POWER_USER)
    safe_id = SAFE_TOOL_IDS[0]
    assert gw.run_quill_command(safe_id) is True
    assert host.commands == [safe_id]


def test_critical_risk_agent_is_denied_everything(tmp_path: Path) -> None:
    host = FakeHost()
    gw, _events, _log = _gateway(tmp_path, host, risk=RiskLevel.CRITICAL)
    with pytest.raises(PermissionDeniedError):
        gw.read_selection()
    assert gw.replace_selection("x") is False
