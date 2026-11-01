"""Phase 4a: the family tool registry and the approval rules (codex.md 5.3).

Engine-free: the registry is called the way any engine calls it.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.agent import SAFE_TOOL_IDS
from quill.core.ai.agent_tools import TOOL_DESCRIPTORS
from quill.core.ai.agent_workdir import agent_folders, agent_slug
from quill.core.ai.approvals import (
    ApprovalChoice,
    ApprovalGate,
    ApprovalRequest,
    UiApprovalBridge,
    UiThreadBridge,
)
from quill.core.ai.document_task import (
    DOCUMENT_TASK_TOOLS,
    build_document_tools,
    summarize_outcome,
)
from quill.core.ai.family_tools import (
    FamilyTool,
    FamilyToolError,
    FamilyToolRegistry,
    ToolCallResult,
    ToolImage,
    codex_tool_response,
    editor_tools,
    to_codex_dynamic_tools,
)
from quill.core.ai.harness import HarnessResult
from quill.core.ai.permissions import (
    Decision,
    PermissionBroker,
    PermissionCategory,
    PermissionRequest,
    RiskLevel,
    SafetyProfile,
)
from quill.core.ai.tool_gateway import AgentIdentity
from tests.unit.core.ai.test_copilot_tool_session import FakeHost, ScriptedApprover


def _registry(tmp_path: Path, profile: SafetyProfile = SafetyProfile.BALANCED, app: str = "studio"):
    return FamilyToolRegistry(
        PermissionBroker(profile),
        ActivityLog(tmp_path / "activity.json"),
        AgentIdentity("a", RiskLevel.LOW, harness="copilot"),
        app_scope=app,
    )


def _tool(
    name: str,
    category: PermissionCategory,
    *,
    app: str = "studio",
    handler: Callable[[dict[str, Any]], Any] | None = None,
) -> FamilyTool:
    return FamilyTool(
        name=name,
        description=f"{name} tool.",
        handler=handler or (lambda args: f"{name} ran"),
        category=category,
        app=app,
        mutating=category not in {PermissionCategory.READ_DOCUMENT},
    )


# -- approvals: once, task, deny, and reset between tasks ----------------------


def test_once_asks_again_next_time(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    reg.register(_tool("studio.record", PermissionCategory.RECORD_AUDIO))
    approver = ScriptedApprover(ApprovalChoice.ONCE, ApprovalChoice.ONCE)
    reg.gate.begin_task(approver)
    assert reg.call("studio_record").ok
    assert reg.call("studio.record").ok
    assert len(approver.asked) == 2


def test_task_grant_lasts_the_task_and_no_longer(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    reg.register(_tool("studio.record", PermissionCategory.RECORD_AUDIO))
    approver = ScriptedApprover(ApprovalChoice.TASK, ApprovalChoice.DENY)
    reg.gate.begin_task(approver)
    assert reg.call("studio.record").ok
    assert reg.call("studio.record").ok
    assert len(approver.asked) == 1  # granted for this task
    reg.gate.end_task()
    reg.gate.begin_task(approver)
    result = reg.call("studio.record")
    assert not result.ok and len(approver.asked) == 2  # a new task asks again


def test_deny_refuses_and_logs(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    ran: list[bool] = []
    reg.register(
        _tool(
            "studio.schedule", PermissionCategory.SCHEDULE, handler=lambda a: ran.append(True) or ""
        )
    )
    reg.gate.begin_task(ScriptedApprover(ApprovalChoice.DENY))
    result = reg.call("studio.schedule")
    assert not result.ok and ran == []
    assert any(e.kind == "tool_call_denied" for e in ActivityLog(tmp_path / "activity.json").all())


def test_reads_in_scope_never_ask_but_out_of_scope_reads_do(tmp_path: Path) -> None:
    reg = _registry(tmp_path, app="studio")
    reg.register(_tool("studio.read_preflight", PermissionCategory.READ_DOCUMENT))
    reg.register(_tool("radio.read_schedule", PermissionCategory.READ_DOCUMENT, app="radio"))
    approver = ScriptedApprover(ApprovalChoice.DENY)
    reg.gate.begin_task(approver)
    assert reg.call("studio.read_preflight").ok
    assert not reg.call("radio.read_schedule").ok
    assert [name for name, _ in approver.asked] == ["radio.read_schedule"]


def test_locked_down_denies_without_asking(tmp_path: Path) -> None:
    reg = _registry(tmp_path, profile=SafetyProfile.LOCKED_DOWN)
    reg.register(_tool("studio.read_preflight", PermissionCategory.READ_DOCUMENT))
    approver = ScriptedApprover(ApprovalChoice.ONCE)
    reg.gate.begin_task(approver)
    assert not reg.call("studio.read_preflight").ok
    assert approver.asked == []


def test_authorize_ahead_leaves_one_pass_for_that_call_only(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    reg.register(_tool("studio.capture", PermissionCategory.CAPTURE_SCREEN))
    approver = ScriptedApprover(ApprovalChoice.ONCE, ApprovalChoice.DENY)
    reg.gate.begin_task(approver)
    allowed, _reason = reg.authorize("studio_capture", {}, "c1")
    assert allowed
    assert reg.call("studio_capture", {}, "c1").ok  # the pass, no second question
    assert not reg.call("studio_capture", {}, "c2").ok  # a different call asks again
    assert len(approver.asked) == 2


def test_no_approver_means_no(tmp_path: Path) -> None:
    gate = ApprovalGate()
    tool = _tool("studio.record", PermissionCategory.RECORD_AUDIO)
    assert gate.check(tool, "Record?") is False


def test_new_categories_ask_except_locked_down() -> None:
    for category in (
        PermissionCategory.CAPTURE_SCREEN,
        PermissionCategory.RECORD_AUDIO,
        PermissionCategory.SCHEDULE,
    ):
        for profile in SafetyProfile:
            decision = (
                PermissionBroker(profile)
                .resolve(PermissionRequest(category, "a", RiskLevel.LOW))
                .decision
            )
            expected = Decision.DENY if profile is SafetyProfile.LOCKED_DOWN else Decision.ASK
            assert decision is expected, (category, profile)


# -- the UI bridge: cancel unblocks a pending question -------------------------


def test_cancel_unblocks_a_pending_approval() -> None:
    posted: list[Callable[[], None]] = []
    shown: list[ApprovalRequest] = []
    bridge = UiApprovalBridge(posted.append, shown.append)
    gate = ApprovalGate(bridge, app_scope="studio")
    tool = _tool("studio.record", PermissionCategory.RECORD_AUDIO)
    out: list[bool] = []
    worker = threading.Thread(target=lambda: out.append(gate.check(tool, "Record?")))
    worker.start()
    deadline = time.monotonic() + 5
    while not posted and time.monotonic() < deadline:
        time.sleep(0.01)
    posted[0]()  # the UI thread shows the question and nobody answers
    assert len(shown) == 1 and not shown[0].answered
    time.sleep(0.05)
    assert worker.is_alive()  # really waiting
    bridge.cancel()
    worker.join(2)
    assert not worker.is_alive() and out == [False]
    # After a cancel no new question is posted until the next task resets it.
    assert bridge.ask(tool, "Again?") is ApprovalChoice.DENY
    bridge.reset()


def test_ui_answer_reaches_the_worker() -> None:
    def post(fn: Callable[[], None]) -> None:
        threading.Timer(0.01, fn).start()

    bridge = UiApprovalBridge(post, lambda req: req.answer(ApprovalChoice.TASK))
    tool = _tool("studio.record", PermissionCategory.RECORD_AUDIO)
    assert bridge.ask(tool, "Record?") is ApprovalChoice.TASK


def test_thread_bridge_returns_the_value_and_raises_errors() -> None:
    bridge = UiThreadBridge(lambda fn: fn())
    assert bridge.call(lambda: 42, default=0) == 42

    def boom() -> int:
        raise RuntimeError("no")

    with pytest.raises(RuntimeError):
        bridge.call(boom, default=0)


# -- the registry ------------------------------------------------------------


def test_names_must_sit_in_their_app_namespace(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    with pytest.raises(FamilyToolError):
        reg.register_app("studio", [_tool("radio.x", PermissionCategory.READ_DOCUMENT)])
    reg.register(_tool("studio.x", PermissionCategory.READ_DOCUMENT))
    with pytest.raises(FamilyToolError):
        reg.register(_tool("studio.x", PermissionCategory.READ_DOCUMENT))
    with pytest.raises(FamilyToolError):
        reg.register(_tool("studio.bad name", PermissionCategory.READ_DOCUMENT))


def test_unknown_tool_and_handler_failure_are_results_not_raises(tmp_path: Path) -> None:
    reg = _registry(tmp_path)

    def broken(args: dict[str, Any]) -> str:
        raise OSError("disk")

    reg.register(_tool("studio.read", PermissionCategory.READ_DOCUMENT, handler=broken))
    assert not reg.call("nope").ok
    result = reg.call("studio.read")
    assert not result.ok and "could not run" in result.text


def test_editor_tools_mirror_the_descriptors(tmp_path: Path) -> None:
    host = FakeHost()
    registry, gateway = build_document_tools(
        host,
        PermissionBroker(),
        ActivityLog(tmp_path / "a.json"),
        AgentIdentity("a", RiskLevel.LOW),
    )
    assert registry.names() == [
        f"doc.{n}" for n in (d.name for d in TOOL_DESCRIPTORS) if n in DOCUMENT_TASK_TOOLS
    ]
    every = editor_tools(gateway)
    assert {t.name for t in every} == {
        f"doc.{d.name}" for d in TOOL_DESCRIPTORS if not d.name.startswith("web_")
    }
    run = registry.get("doc_run_command")
    assert run is not None
    assert run.parameters["properties"]["command_id"]["enum"] == list(SAFE_TOOL_IDS)
    assert run.parameters["required"] == ["command_id"]


def test_codex_serializers(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    reg.register(_tool("studio.read", PermissionCategory.READ_DOCUMENT))
    tools = to_codex_dynamic_tools(reg)
    assert tools == [
        {
            "name": "studio_read",
            "description": "studio.read tool.",
            "inputSchema": reg.tools()[0].parameters,
        }
    ]
    picture = ToolCallResult("A still.", image=ToolImage(b"ab", "image/jpeg"))
    response = codex_tool_response(picture)
    assert response["success"] is True
    assert response["contentItems"][0] == {"type": "inputText", "text": "A still."}
    assert response["contentItems"][1]["imageUrl"] == "data:image/jpeg;base64,YWI="
    assert codex_tool_response(ToolCallResult("no", ok=False))["success"] is False


def test_summary_counts_what_happened_not_what_the_model_said(tmp_path: Path) -> None:
    host = FakeHost()
    registry, _gw = build_document_tools(
        host,
        PermissionBroker(),
        ActivityLog(tmp_path / "a.json"),
        AgentIdentity("a", RiskLevel.LOW),
    )
    registry.gate.begin_task(ScriptedApprover())
    host.accept_preview = False
    registry.call("doc.apply_patch", {"original": host.text, "proposed": "x"})
    outcome = summarize_outcome(HarnessResult("completed", final_text="I changed it."), registry)
    assert outcome.changes == ()
    assert outcome.summary == (
        "Done. No changes were made to the document. 1 proposed change was not applied."
    )


def test_agent_folders_are_per_engine_and_per_app(tmp_path: Path) -> None:
    folders = agent_folders("copilot", "QUILL Lite", base=tmp_path)
    assert folders.root == tmp_path / "copilot" / "quill-lite"
    assert agent_slug("  ") == "quill"
    folders.prepare()
    (folders.home / "f").write_text("x", encoding="utf-8")
    folders.clear()
    assert not folders.root.exists()
