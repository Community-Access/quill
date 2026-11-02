"""Phase 4a: QUILL's family tools on Copilot, against a fake SDK.

No network and no real SDK. A stand-in ``copilot`` package (with
``copilot.tools`` and ``copilot.rpc``) mirrors ``github-copilot-sdk`` 1.0.28 as
read from its source: ``Tool(name, description, handler, parameters,
skip_permission=...)``, a handler that receives a ``ToolInvocation`` and
returns a ``ToolResult`` (``binary_results_for_llm`` for pictures),
``custom-tool`` permission requests carrying ``tool_name``/``args``/
``tool_call_id``, ``send`` returning before the turn ends, and the
``assistant.message_delta`` / ``assistant.message`` / ``assistant.usage`` /
``session.idle`` / ``session.error`` events. A scripted "model" drives each
turn, so the real session code -- the loop on the worker thread, the
permission callback, the handler adapter, Stop -- runs end to end.
"""

from __future__ import annotations

import asyncio
import importlib.machinery
import sys
import threading
import time
import types
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import pytest

import quill.ai_packs.copilot as pack
from quill.ai_packs.copilot_tool_session import REFUSAL_FEEDBACK, CopilotToolSession
from quill.core.ai import copilot_auth, copilot_runtime
from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.agent_workdir import AgentFolders, agent_folders
from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.diff_review import DiffReview
from quill.core.ai.document_task import DocumentTaskRunner, build_document_tools
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.family_tools import FamilyTool, FamilyToolRegistry, ToolImage
from quill.core.ai.harness import AgentSpec, AIContext, TurnUsage, supports_app_tools
from quill.core.ai.permissions import PermissionBroker, PermissionCategory, SafetyProfile
from quill.core.ai.tool_gateway import AgentIdentity
from tests.unit.core.ai.test_copilot_pack import (
    PERMISSION_KINDS,
    PermissionDecisionApproveOnce,
    PermissionDecisionReject,
)

#: Built-in tool names the Copilot CLI and Codex offer; none may reach the engine (G3).
VENDOR_BUILTINS = {
    "bash",
    "powershell",
    "shell",
    "view",
    "edit",
    "create",
    "write",
    "read",
    "glob",
    "grep",
    "apply_patch",
    "str_replace_editor",
    "web_fetch",
    "web_search",
    "view_image",
    "image_generation",
    "task",
}


# -- the fake SDK ------------------------------------------------------------


class SessionEventType(Enum):
    ASSISTANT_MESSAGE_DELTA = "assistant.message_delta"
    ASSISTANT_MESSAGE = "assistant.message"
    ASSISTANT_USAGE = "assistant.usage"
    SESSION_IDLE = "session.idle"
    SESSION_ERROR = "session.error"


@dataclass
class _Event:
    type: SessionEventType
    data: Any


@dataclass
class ToolBinaryResult:
    data: str = ""
    mime_type: str = ""
    type: str = "image"
    description: str = ""


@dataclass
class ToolResult:
    text_result_for_llm: str = ""
    result_type: str = "success"
    error: str | None = None
    binary_results_for_llm: list[ToolBinaryResult] | None = None


@dataclass
class ToolInvocation:
    session_id: str = ""
    tool_call_id: str = ""
    tool_name: str = ""
    arguments: Any = None


@dataclass
class Tool:
    name: str
    description: str
    handler: Any = None
    parameters: dict[str, Any] | None = None
    overrides_built_in_tool: bool = False
    skip_permission: bool = False


@dataclass
class PermissionRequestCustomTool:
    tool_description: str
    tool_name: str
    args: Any = None
    tool_call_id: str | None = None
    kind: str = "custom-tool"


@dataclass
class Rec:
    """Everything the fake saw, and the script it plays."""

    turns: list[list[tuple[Any, ...]]] = field(default_factory=list)
    client_kwargs: dict[str, Any] = field(default_factory=dict)
    session_kwargs: dict[str, Any] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)
    sent: list[str] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    permission_answers: list[Any] = field(default_factory=list)
    stop_hangs: bool = False
    clients_made: int = 0
    turn_started: threading.Event = field(default_factory=threading.Event)


def _fake_sdk(rec: Rec) -> types.ModuleType:
    class RuntimeConnection:
        @staticmethod
        def for_stdio(*, path: str | None = None, args: tuple[str, ...] = ()) -> Any:
            return types.SimpleNamespace(path=path, args=args)

    class CopilotSession:
        session_id = "sess-1"

        def __init__(self, kwargs: dict[str, Any]) -> None:
            self._kwargs = kwargs
            self._handlers: list[Callable[[Any], None]] = []
            self._tools = {t.name: t for t in kwargs.get("tools") or []}
            self._turn = 0
            self._abort = asyncio.Event()

        def on(self, handler: Callable[[Any], None]) -> Callable[[], None]:
            self._handlers.append(handler)
            return lambda: self._handlers.remove(handler)

        def _fire(self, kind: SessionEventType, data: Any) -> None:
            for handler in list(self._handlers):
                handler(_Event(kind, data))

        async def send(self, prompt: str, *, attachments: Any = None) -> str:
            rec.calls.append("send")
            rec.sent.append(prompt)
            script = rec.turns[self._turn] if self._turn < len(rec.turns) else [("text", "ok")]
            self._turn += 1
            asyncio.ensure_future(self._play(script))
            return f"msg-{self._turn}"

        async def _play(self, script: list[tuple[Any, ...]]) -> None:
            rec.turn_started.set()
            on_permission = self._kwargs["on_permission_request"]
            for step in script:
                if step[0] == "tool":
                    _, name, args = step
                    call_id = f"call-{len(rec.tool_results)}-{name}"
                    request = PermissionRequestCustomTool(
                        tool_description="", tool_name=name, args=args, tool_call_id=call_id
                    )
                    answer = await on_permission(request, {"session_id": self.session_id})
                    rec.permission_answers.append(answer)
                    if isinstance(answer, PermissionDecisionApproveOnce):
                        tool = self._tools[name]
                        result = await tool.handler(
                            ToolInvocation(self.session_id, call_id, name, args)
                        )
                        rec.tool_results.append(result)
                elif step[0] == "permission":
                    answer = await on_permission(
                        types.SimpleNamespace(kind=step[1]), {"session_id": self.session_id}
                    )
                    rec.permission_answers.append(answer)
                elif step[0] == "text":
                    self._fire(
                        SessionEventType.ASSISTANT_MESSAGE_DELTA,
                        types.SimpleNamespace(delta_content=step[1], message_id="m"),
                    )
                    self._fire(
                        SessionEventType.ASSISTANT_MESSAGE,
                        types.SimpleNamespace(content=step[1], message_id="m"),
                    )
                    self._fire(
                        SessionEventType.ASSISTANT_USAGE,
                        types.SimpleNamespace(model="gpt-test", input_tokens=10, output_tokens=4),
                    )
                elif step[0] == "error":
                    self._fire(
                        SessionEventType.SESSION_ERROR, types.SimpleNamespace(message=step[1])
                    )
                    return
                elif step[0] == "hang":
                    await self._abort.wait()
                    return
            self._fire(SessionEventType.SESSION_IDLE, types.SimpleNamespace())

        async def abort(self) -> None:
            rec.calls.append("abort")
            self._abort.set()

        async def disconnect(self) -> None:
            rec.calls.append("disconnect")

    class CopilotClient:
        def __init__(self, **kwargs: Any) -> None:
            rec.clients_made += 1
            rec.client_kwargs = kwargs

        async def start(self) -> None:
            rec.calls.append("start")

        async def create_session(self, **kwargs: Any) -> CopilotSession:
            rec.session_kwargs = kwargs
            home = Path(rec.client_kwargs["base_directory"])
            state = home / "session-state" / "sess-1"
            state.mkdir(parents=True, exist_ok=True)
            (state / "events.jsonl").write_text("{}", encoding="utf-8")
            return CopilotSession(kwargs)

        async def stop(self) -> None:
            rec.calls.append("stop")
            if rec.stop_hangs:
                await asyncio.sleep(30)

        async def force_stop(self) -> None:
            rec.calls.append("force_stop")

    module = types.ModuleType("copilot")
    module.__spec__ = importlib.machinery.ModuleSpec("copilot", None)
    module.CopilotClient = CopilotClient  # type: ignore[attr-defined]
    module.RuntimeConnection = RuntimeConnection  # type: ignore[attr-defined]
    return module


@pytest.fixture
def rec(monkeypatch: pytest.MonkeyPatch, absent_env) -> Rec:
    recorder = Rec()
    module = _fake_sdk(recorder)
    tools_mod = types.ModuleType("copilot.tools")
    for cls in (Tool, ToolResult, ToolBinaryResult, ToolInvocation):
        setattr(tools_mod, cls.__name__, cls)
    rpc = types.ModuleType("copilot.rpc")
    rpc.PermissionDecisionReject = PermissionDecisionReject  # type: ignore[attr-defined]
    rpc.PermissionDecisionApproveOnce = PermissionDecisionApproveOnce  # type: ignore[attr-defined]
    module.tools = tools_mod  # type: ignore[attr-defined]
    module.rpc = rpc  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "copilot", module)
    monkeypatch.setitem(sys.modules, "copilot.tools", tools_mod)
    monkeypatch.setitem(sys.modules, "copilot.rpc", rpc)
    absent_env("QUILL_SAFE_MODE", "COPILOT_CLI_PATH", "COPILOT_SDK_DEFAULT_CONNECTION")
    monkeypatch.setattr(copilot_runtime, "find_copilot_cli", lambda: None)
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": None)
    return recorder


# -- the editor and the approver ---------------------------------------------


class FakeHost:
    def __init__(self, text: str = "# Title\n\nbody\n") -> None:
        self.text = text
        self.previews: list[DiffReview] = []
        self.accept_preview = True
        self.commands: list[str] = []
        self.confirms: list[str] = []

    def get_document(self) -> str:
        return self.text

    def get_selection(self) -> str:
        return ""

    def get_outline(self) -> list[str]:
        return ["Title"]

    def get_file_type(self) -> str:
        return "markdown"

    def get_current_section(self) -> str:
        return "body"

    def create_undo_checkpoint(self, label: str) -> None:
        pass

    def apply_replacement(self, text: str) -> None:
        self.text = text

    def apply_insert(self, text: str) -> None:
        self.text += text

    def apply_document_text(self, text: str) -> None:
        self.text = text

    def run_command(self, command_id: str) -> None:
        self.commands.append(command_id)

    def confirm(self, message: str) -> bool:
        self.confirms.append(message)
        return False  # the host's own confirm must never be reached in a task

    def preview_diff(self, review: DiffReview) -> bool:
        self.previews.append(review)
        return self.accept_preview

    def announce(self, message: str) -> None:
        pass


class ScriptedApprover:
    def __init__(self, *answers: ApprovalChoice) -> None:
        self.answers = list(answers)
        self.asked: list[tuple[str, str]] = []
        self.cancelled = 0

    def ask(self, tool: FamilyTool, summary: str) -> ApprovalChoice:
        self.asked.append((tool.name, summary))
        return self.answers.pop(0) if self.answers else ApprovalChoice.DENY

    def cancel(self) -> None:
        self.cancelled += 1


def _agent() -> AgentSpec:
    return AgentSpec(id="doc-agent", display_name="Doc", system_prompt="Be careful.")


def _registry(tmp_path: Path, host: FakeHost, profile=SafetyProfile.BALANCED):
    identity = AgentIdentity("doc-agent", _agent().risk, harness="copilot")
    return build_document_tools(
        host, PermissionBroker(profile), ActivityLog(tmp_path / "activity.json"), identity
    )


def _folders(tmp_path: Path) -> AgentFolders:
    return agent_folders("copilot", "QUILL", base=tmp_path / "ai")


def _session(
    tmp_path: Path,
    registry: FamilyToolRegistry,
    approver: ScriptedApprover,
    events: list[AgentEvent] | None = None,
    **kw: Any,
) -> CopilotToolSession:
    sink = events if events is not None else []
    session = pack.CopilotHarness().start_tool_session(
        _agent(),
        AIContext(prompt="Fix the headings."),
        registry,
        approver,
        sink.append,
        folders=_folders(tmp_path),
        **kw,
    )
    assert isinstance(session, CopilotToolSession)
    return session


# -- tests -------------------------------------------------------------------


def test_copilot_declares_app_tools() -> None:
    assert supports_app_tools(pack.CopilotHarness())
    assert pack.CopilotHarness().capabilities().app_tools


def test_tool_round_trip_reads_then_applies_a_reviewed_patch(rec: Rec, tmp_path: Path) -> None:
    host = FakeHost()
    registry, _gw = _registry(tmp_path, host)
    original = host.text
    rec.turns = [
        [
            ("tool", "doc_read_outline", {}),
            ("tool", "doc_read_document", {}),
            ("tool", "doc_apply_patch", {"original": original, "proposed": "# Title\n\nfixed\n"}),
            ("text", "I fixed the body."),
        ]
    ]
    events: list[AgentEvent] = []
    usage: list[TurnUsage] = []
    approver = ScriptedApprover()
    result = _session(tmp_path, registry, approver, events, on_usage=usage.append).run()
    assert result.status == "completed"
    assert result.final_text == "I fixed the body."
    assert rec.tool_results[0].text_result_for_llm == "Title"
    assert rec.tool_results[1].text_result_for_llm == original
    assert rec.tool_results[2].result_type == "success"
    assert host.text == "# Title\n\nfixed\n"
    assert len(host.previews) == 1  # the edit was reviewed as a diff
    assert approver.asked == []  # reads in scope, and the preview was the question
    assert host.confirms == []
    assert any(e.kind is AgentEventKind.AGENT_TEXT_DELTA for e in events)
    assert events[-1].kind is AgentEventKind.AGENT_COMPLETED
    assert usage == [TurnUsage("copilot", "gpt-test", 10, 4)]


def test_session_options_stream_append_and_stay_in_the_app_folder(rec: Rec, tmp_path: Path) -> None:
    registry, _gw = _registry(tmp_path, FakeHost())
    _session(tmp_path, registry, ScriptedApprover()).run()
    folders = _folders(tmp_path)
    assert rec.session_kwargs["streaming"] is True
    assert rec.session_kwargs["system_message"]["mode"] == "append"
    assert "Be careful." in rec.session_kwargs["system_message"]["content"]
    assert rec.session_kwargs["working_directory"] == str(folders.work)
    assert rec.client_kwargs["working_directory"] == str(folders.work)
    assert rec.client_kwargs["base_directory"] == str(folders.home)
    assert all(t.skip_permission is False for t in rec.session_kwargs["tools"])


def test_g3_the_offered_tool_list_holds_only_quill_tools(rec: Rec, tmp_path: Path) -> None:
    registry, _gw = _registry(tmp_path, FakeHost())
    session = _session(tmp_path, registry, ScriptedApprover())
    session.run()
    offered = rec.session_kwargs["available_tools"]
    defined = [t.name for t in rec.session_kwargs["tools"]]
    assert offered and offered == defined == registry.wire_names()
    assert offered == session.recorded_tool_names
    assert all(name.startswith("doc_") for name in offered)
    assert not VENDOR_BUILTINS & set(offered)


@pytest.mark.parametrize("kind", [k for k in PERMISSION_KINDS if k != "custom-tool"])
def test_every_non_custom_permission_kind_is_rejected_and_logged(
    rec: Rec, tmp_path: Path, kind: str
) -> None:
    registry, _gw = _registry(tmp_path, FakeHost())
    rec.turns = [[("permission", kind), ("text", "done")]]
    events: list[AgentEvent] = []
    _session(tmp_path, registry, ScriptedApprover(), events).run()
    answer = rec.permission_answers[0]
    assert isinstance(answer, PermissionDecisionReject)
    assert answer.feedback == REFUSAL_FEEDBACK
    log = ActivityLog(tmp_path / "activity.json").all()
    assert any(e.kind == "engine_defect" and kind in e.summary for e in log)
    assert any(e.kind is AgentEventKind.WARNING for e in events)


def test_a_custom_tool_that_is_not_ours_is_rejected(rec: Rec, tmp_path: Path) -> None:
    registry, _gw = _registry(tmp_path, FakeHost())
    on_permission = None
    session = _session(tmp_path, registry, ScriptedApprover())
    rec.turns = [[("text", "x")]]
    session.run()
    on_permission = rec.session_kwargs["on_permission_request"]
    # The session is over; call the callback directly on a fresh loop.
    answer = asyncio.run(
        on_permission(PermissionRequestCustomTool("", "bash", {}, "c1"), {"session_id": "s"})
    )
    assert isinstance(answer, PermissionDecisionReject)


def test_run_command_asks_once_through_the_approver_not_twice(rec: Rec, tmp_path: Path) -> None:
    host = FakeHost()
    registry, _gw = _registry(tmp_path, host)
    rec.turns = [[("tool", "doc_run_command", {"command_id": "format.bold"}), ("text", "ok")]]
    approver = ScriptedApprover(ApprovalChoice.ONCE)
    _session(tmp_path, registry, approver).run()
    assert [name for name, _ in approver.asked] == ["doc.run_command"]
    assert host.commands == ["format.bold"]
    assert isinstance(rec.permission_answers[0], PermissionDecisionApproveOnce)


def test_run_command_outside_the_floor_is_rejected_before_the_call(
    rec: Rec, tmp_path: Path
) -> None:
    host = FakeHost()
    registry, _gw = _registry(tmp_path, host)
    rec.turns = [[("tool", "doc_run_command", {"command_id": "file.delete"}), ("text", "ok")]]
    approver = ScriptedApprover(ApprovalChoice.ONCE)
    _session(tmp_path, registry, approver).run()
    assert isinstance(rec.permission_answers[0], PermissionDecisionReject)
    assert approver.asked == [] and host.commands == []


def test_a_declined_run_command_is_rejected(rec: Rec, tmp_path: Path) -> None:
    host = FakeHost()
    registry, _gw = _registry(tmp_path, host)
    rec.turns = [[("tool", "doc_run_command", {"command_id": "format.bold"}), ("text", "ok")]]
    _session(tmp_path, registry, ScriptedApprover(ApprovalChoice.DENY)).run()
    assert isinstance(rec.permission_answers[0], PermissionDecisionReject)
    assert host.commands == []


def test_safe_mode_refuses_to_start(rec: Rec, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    registry, _gw = _registry(tmp_path, FakeHost())
    events: list[AgentEvent] = []
    session = pack.CopilotHarness().start_tool_session(
        _agent(), AIContext(prompt="x"), registry, ScriptedApprover(), events.append
    )
    result = session.run()
    assert result.status == "error"
    assert "Safe Mode" in result.error
    assert rec.clients_made == 0
    assert events[0].kind is AgentEventKind.ERROR


def test_session_files_are_swept_at_start_and_deleted_at_task_end(rec: Rec, tmp_path: Path) -> None:
    folders = _folders(tmp_path)
    stale = folders.home / "session-state" / "old" / "events.jsonl"
    stale.parent.mkdir(parents=True)
    stale.write_text("left by a crash", encoding="utf-8")
    seen_at_create: list[bool] = []
    real_factory = pack.CopilotHarness._tool_client

    def factory(self: Any, f: AgentFolders) -> Any:
        seen_at_create.append(stale.exists())
        return real_factory(self, f)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pack.CopilotHarness, "_tool_client", factory)
        registry, _gw = _registry(tmp_path, FakeHost())
        _session(tmp_path, registry, ScriptedApprover()).run()
    assert seen_at_create == [False]  # swept before the child started
    assert not folders.root.exists()  # and nothing left after the task


def _run_in_thread(session: CopilotToolSession) -> tuple[threading.Thread, list[Any]]:
    out: list[Any] = []
    thread = threading.Thread(target=lambda: out.append(session.run()), daemon=True)
    thread.start()
    return thread, out


def test_stop_ends_the_turn_within_a_second_and_cleans_up(rec: Rec, tmp_path: Path) -> None:
    registry, _gw = _registry(tmp_path, FakeHost())
    rec.turns = [[("hang",)]]
    approver = ScriptedApprover()
    session = _session(tmp_path, registry, approver)
    thread, out = _run_in_thread(session)
    assert rec.turn_started.wait(5)
    started = time.monotonic()
    session.cancel()
    thread.join(5)
    assert time.monotonic() - started < 1.0
    assert out[0].status == "cancelled"
    assert rec.calls.index("abort") < rec.calls.index("stop")
    assert approver.cancelled == 1
    assert not _folders(tmp_path).root.exists()


def test_a_child_that_will_not_stop_is_killed_within_two_seconds(rec: Rec, tmp_path: Path) -> None:
    registry, _gw = _registry(tmp_path, FakeHost())
    rec.turns = [[("hang",)]]
    rec.stop_hangs = True
    session = _session(tmp_path, registry, ScriptedApprover())
    thread, out = _run_in_thread(session)
    assert rec.turn_started.wait(5)
    started = time.monotonic()
    session.cancel()
    thread.join(5)
    assert time.monotonic() - started < 2.0
    assert "force_stop" in rec.calls
    assert out[0].status == "cancelled"


def test_follow_ups_run_in_the_same_session_until_end(rec: Rec, tmp_path: Path) -> None:
    registry, _gw = _registry(tmp_path, FakeHost())
    rec.turns = [[("text", "first")], [("text", "second")]]
    session = _session(tmp_path, registry, ScriptedApprover(), keep_open=True)
    thread, out = _run_in_thread(session)
    deadline = time.monotonic() + 5
    while rec.sent == [] and time.monotonic() < deadline:
        time.sleep(0.01)
    session.send("And the second part.")
    while len(rec.sent) < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    session.end()
    thread.join(5)
    assert rec.sent == ["Fix the headings.", "And the second part."]
    assert rec.clients_made == 1
    assert out[0].status == "completed" and out[0].final_text == "second"


def test_a_session_error_ends_the_task_as_an_error(rec: Rec, tmp_path: Path) -> None:
    registry, _gw = _registry(tmp_path, FakeHost())
    rec.turns = [[("error", "Rate limited.")]]
    result = _session(tmp_path, registry, ScriptedApprover()).run()
    assert result.status == "error" and result.error == "Rate limited."


def test_a_tool_can_hand_the_model_a_picture(rec: Rec, tmp_path: Path) -> None:
    registry, _gw = _registry(tmp_path, FakeHost())
    registry.register(
        FamilyTool(
            name="doc.image",
            description="One image from the document.",
            handler=lambda args: ToolImage(b"\x89PNG", "image/png", "A chart."),
            category=PermissionCategory.READ_DOCUMENT,
        )
    )
    rec.turns = [[("tool", "doc_image", {}), ("text", "ok")]]
    _session(tmp_path, registry, ScriptedApprover()).run()
    binary = rec.tool_results[0].binary_results_for_llm
    assert binary and binary[0].data == "iVBORw==" and binary[0].mime_type == "image/png"
    assert binary[0].type == "image"


def test_document_task_runner_ends_with_a_text_summary(rec: Rec, tmp_path: Path) -> None:
    host = FakeHost()
    original = host.text
    rec.turns = [
        [
            ("tool", "doc_read_document", {}),
            ("tool", "doc_apply_patch", {"original": original, "proposed": "# Title\n"}),
            ("text", "Removed the empty body."),
        ]
    ]
    runner = DocumentTaskRunner(
        harness=pack.CopilotHarness(),
        host=host,
        approver=ScriptedApprover(),
        broker=PermissionBroker(),
        activity=ActivityLog(tmp_path / "activity.json"),
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pack, "agent_folders", lambda engine, name: _folders(tmp_path))
        outcome = runner.run("Tidy it.")
    assert outcome.ok
    assert outcome.summary.startswith("Done. 1 change applied: Changed the document.")
    assert outcome.answer == "Removed the empty body."
    assert "doc_apply_patch" in rec.session_kwargs["system_message"]["content"]
