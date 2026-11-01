"""Phase 4b: the Codex engine against a fake app-server child (codex.md 2, 5.2, G2-G4).

The child is a real process -- ``codex_fake_app_server.py`` beside this file,
run by this interpreter -- speaking the pinned binary's wire format, so the
real launcher, pipes, reader thread, close and kill are all exercised. Only
the binary lookup and the pin check are swapped, and the hash-mismatch test
keeps the real pin check.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.agent_workdir import AgentFolders, agent_folders
from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.codex_app_server import (
    DISABLED_FEATURES,
    TOKEN_ENV,
    CodexAppServer,
    CodexBinaryError,
    CodexSafeModeError,
    child_env,
    command_line,
)
from quill.core.ai.codex_binary import codex_app_server_matches_pin
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.family_tools import FamilyTool, FamilyToolRegistry
from quill.core.ai.harness import AgentSpec, AIContext, TurnUsage, supports_app_tools
from quill.core.ai.harness.codex import SINGLE_REQUEST_SENTENCE, CodexHarness, CodexToolSession
from quill.core.ai.permissions import PermissionBroker, PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import AgentIdentity
from quill.stability.redaction import format_args_for_log, redact_text_for_bundle
from quill.stability.safe_subprocess import spawn_subprocess_safely

FAKE = Path(__file__).with_name("codex_fake_app_server.py")
AGENT = "QUILL Studio"
#: Shaped like a real plan token (a JWT), so the redaction checks are honest.
TOKEN = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJmYWtlLXVzZXIifQ.c2lnbmF0dXJlLWZha2UtZmFrZQ"


class Approver:
    def __init__(self, choice: ApprovalChoice = ApprovalChoice.ONCE) -> None:
        self.choice = choice
        self.asked: list[str] = []
        self.cancelled = False

    def ask(self, tool: FamilyTool, summary: str) -> ApprovalChoice:
        self.asked.append(tool.name)
        return self.choice

    def cancel(self) -> None:
        self.cancelled = True

    def reset(self) -> None:
        self.cancelled = False


class Child:
    """Builds CodexAppServers that launch the fake, and reads what it saw."""

    def __init__(self, tmp_path: Path, scenario: str = "answer", tool: str = "") -> None:
        self.log = tmp_path / f"fake-{scenario}.jsonl"
        self.scenario = scenario
        self.tool = tool
        self.launches: list[dict[str, Any]] = []
        self.servers: list[CodexAppServer] = []

    def spawn(self, argv: list[str], *, cwd: str, env: dict[str, str]) -> Any:
        self.launches.append({"argv": list(argv), "cwd": cwd, "env": dict(env)})
        fake_env = dict(env)
        fake_env.update({
            "FAKE_CODEX_LOG": str(self.log),
            "FAKE_CODEX_SCENARIO": self.scenario,
            "FAKE_CODEX_TOOL": self.tool,
        })
        return spawn_subprocess_safely(
            [sys.executable, "-I", str(FAKE), *argv[1:]], cwd=cwd, env=fake_env
        )

    def server(
        self, folders: AgentFolders, token: str, on_note: Any, on_req: Any
    ) -> CodexAppServer:
        server = CodexAppServer(
            agent_name=AGENT,
            folders=folders,
            token=token,
            on_notification=on_note,
            on_request=on_req,
            binary_resolver=lambda: Path(sys.executable),
            pin_check=lambda _path: True,
            spawn=self.spawn,
            argv=["quill"],
            request_timeout=10.0,
        )
        self.servers.append(server)
        return server

    def entries(self) -> list[dict[str, Any]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def received(self, method: str) -> list[dict[str, Any]]:
        return [e for e in self.entries() if e.get("in", {}).get("method") == method]

    def answers(self) -> list[dict[str, Any]]:
        return [e["in"] for e in self.entries() if "in" in e and "method" not in e["in"]]


def _registry(tmp_path: Path, tools: list[FamilyTool] = ()) -> FamilyToolRegistry:  # type: ignore[assignment]
    registry = FamilyToolRegistry(
        PermissionBroker(),
        ActivityLog(tmp_path / "activity.json"),
        AgentIdentity("studio-check", RiskLevel.LOW, harness="codex"),
        app_scope="studio",
    )
    registry.register_app("studio", tools)
    return registry


def _levels_tool(calls: list[dict[str, Any]]) -> FamilyTool:
    def handler(args: dict[str, Any]) -> str:
        calls.append(args)
        return "Microphone peaks at minus 12 dB."

    return FamilyTool(
        name="studio.read_levels",
        description="Read the input levels.",
        handler=handler,
        category=PermissionCategory.READ_DOCUMENT,
        app="studio",
    )


def _session(
    tmp_path: Path,
    child: Child,
    *,
    registry: FamilyToolRegistry | None = None,
    tokens: list[str] | None = None,
    events: list[AgentEvent] | None = None,
    usage: list[TurnUsage] | None = None,
    approver: Approver | None = None,
) -> tuple[CodexToolSession, AgentFolders]:
    folders = agent_folders("codex", AGENT, base=tmp_path / "ai")
    queue = list(tokens or [TOKEN])

    def token_provider() -> str:
        return queue.pop(0) if len(queue) > 1 else queue[0]

    session = CodexToolSession(
        agent=AgentSpec(id="studio-check", display_name="Check", system_prompt="Be brief."),
        ctx=AIContext(prompt="Check my recording setup."),
        tools=registry if registry is not None else _registry(tmp_path),
        approver=approver or Approver(),
        emit=(events.append if events is not None else lambda _e: None),
        token_provider=token_provider,
        server_factory=child.server,
        folders=folders,
        on_usage=(usage.append if usage is not None else None),
    )
    return session, folders


# -- launch shape --------------------------------------------------------------


def test_command_line_is_stdio_with_every_switch(tmp_path: Path) -> None:
    argv = command_line(tmp_path / "codex-app-server.exe")
    assert argv[1:3] == ["--listen", "stdio://"]
    assert "app-server" not in argv  # the standalone exe takes no subcommand
    overrides = [argv[i + 1] for i, a in enumerate(argv) if a == "-c"]
    for name in DISABLED_FEATURES:
        assert f"features.{name}=false" in overrides
    assert 'model_provider="openai_chatgpt_plan"' in overrides
    assert 'model_providers.openai_chatgpt_plan.env_key="ACCESS_TOKEN"' in overrides
    assert 'model_providers.openai_chatgpt_plan.base_url="https://api.openai.com/v1"' in overrides
    assert 'web_search="disabled"' in overrides
    assert not any(TOKEN in a for a in argv)


def test_child_env_is_an_allowlist_plus_home_and_token(tmp_path: Path) -> None:
    base = {
        "SystemRoot": r"C:\Windows",
        "TEMP": r"C:\t",
        "OPENAI_API_KEY": "sk-leak",
        "GITHUB_TOKEN": "gho_leak",
        "QUILL_DATA_DIR": "x",
    }
    env = child_env(TOKEN, tmp_path / "home", base=base)
    assert env == {
        "SystemRoot": r"C:\Windows",
        "TEMP": r"C:\t",
        "CODEX_HOME": str(tmp_path / "home"),
        TOKEN_ENV: TOKEN,
    }


# -- refusals ------------------------------------------------------------------


def _bare_server(tmp_path: Path, **kwargs: Any) -> tuple[CodexAppServer, list[Any]]:
    spawned: list[Any] = []
    defaults: dict[str, Any] = {
        "agent_name": AGENT,
        "folders": agent_folders("codex", AGENT, base=tmp_path / "ai"),
        "token": TOKEN,
        "on_notification": lambda _m, _p: None,
        "on_request": lambda _m, _p: {},
        "spawn": lambda *a, **k: spawned.append(a),
        "argv": ["quill"],
    }
    defaults.update(kwargs)
    return CodexAppServer(**defaults), spawned


def test_hash_mismatch_refuses_before_launch(tmp_path: Path) -> None:
    impostor = tmp_path / "codex-app-server.exe"
    impostor.write_bytes(b"not the pinned binary")
    server, spawned = _bare_server(
        tmp_path, binary_resolver=lambda: impostor, pin_check=codex_app_server_matches_pin
    )
    with pytest.raises(CodexBinaryError) as caught:
        server.start()
    assert caught.value.code == "QUILL-AI-CODEX-BINARY-UNVERIFIED"
    assert spawned == []


def test_missing_binary_refuses(tmp_path: Path) -> None:
    server, spawned = _bare_server(tmp_path, binary_resolver=lambda: None)
    with pytest.raises(CodexBinaryError):
        server.start()
    assert spawned == []


def test_safe_mode_refuses_server_and_harness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server, spawned = _bare_server(
        tmp_path,
        argv=["quill", "--safe-mode"],
        binary_resolver=lambda: Path(sys.executable),
        pin_check=lambda _p: True,
    )
    with pytest.raises(CodexSafeModeError):
        server.start()
    assert spawned == []

    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    built: list[Any] = []
    harness = CodexHarness(
        agent_name=AGENT,
        token_provider=lambda: TOKEN,
        server_factory=lambda *a: built.append(a),  # type: ignore[arg-type,return-value]
        binary_resolver=lambda: Path(sys.executable),
    )
    events: list[AgentEvent] = []
    session = harness.start_tool_session(
        AgentSpec(id="a", display_name="A", system_prompt=""),
        AIContext(prompt="hi"),
        _registry(tmp_path),
        Approver(),
        events.append,
    )
    result = session.run()
    assert result.status == "error" and "Safe Mode" in result.error
    assert built == []


# -- a task, end to end -----------------------------------------------------------


def test_handshake_turn_streaming_and_usage(tmp_path: Path) -> None:
    child = Child(tmp_path)
    events: list[AgentEvent] = []
    usage: list[TurnUsage] = []
    session, _folders = _session(tmp_path, child, events=events, usage=usage)
    result = session.run()
    assert result.status == "completed" and result.final_text == "Hello"
    methods = [e["in"].get("method") for e in child.entries() if "in" in e]
    assert methods[:3] == ["initialize", "initialized", "thread/start"]
    init = child.received("initialize")[0]["in"]["params"]
    assert init["clientInfo"]["name"] == AGENT
    assert init["capabilities"]["experimentalApi"] is True
    deltas = [e.summary for e in events if e.kind is AgentEventKind.AGENT_TEXT_DELTA]
    assert "".join(deltas) == "Hello"
    assert usage == [TurnUsage(engine="codex", input_tokens=120, output_tokens=30)]
    assert session.rate_limits and session.rate_limits["rateLimits"]["primary"]["usedPercent"] == 12
    assert not child.servers[0].running


def test_tool_call_round_trips_through_the_registry(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(tmp_path, [_levels_tool(calls)])
    child = Child(tmp_path, "tool", tool="studio_read_levels")
    session, _folders = _session(tmp_path, child, registry=registry)
    result = session.run()
    assert result.status == "completed"
    assert calls == [{"what": "levels"}]
    answer = next(a for a in child.answers() if a.get("id") == "srv-tool")["result"]
    assert answer == {
        "contentItems": [{"type": "inputText", "text": "Microphone peaks at minus 12 dB."}],
        "success": True,
    }
    assert registry.calls[0].name == "studio.read_levels" and registry.calls[0].ok


def test_only_quill_tools_reach_the_thread(tmp_path: Path) -> None:
    """G3, as far as a fake can show it: the recorded thread config."""
    registry = _registry(tmp_path, [_levels_tool([])])
    child = Child(tmp_path)
    session, _folders = _session(tmp_path, child, registry=registry)
    session.run()
    params = child.received("thread/start")[0]["in"]["params"]
    assert [t["name"] for t in params["dynamicTools"]] == ["studio_read_levels"]
    assert session.recorded_tool_names == ["studio_read_levels"]
    assert params["sandbox"] == "read-only" and params["approvalPolicy"] == "untrusted"
    assert params["ephemeral"] is False
    for name in DISABLED_FEATURES:
        assert params["config"][f"features.{name}"] is False
    assert params["config"]["web_search"] == "disabled"
    launch = next(e for e in child.entries() if e.get("launch"))
    assert "features.shell_tool=false" in launch["argv"]


def test_builtin_approval_is_declined_and_logged_as_a_defect(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    events: list[AgentEvent] = []
    child = Child(tmp_path, "approval")
    session, _folders = _session(tmp_path, child, registry=registry, events=events)
    assert session.run().status == "completed"
    answer = next(a for a in child.answers() if a.get("id") == "srv-approval")
    assert answer["result"] == {"decision": "decline"}
    defects = [
        e for e in ActivityLog(tmp_path / "activity.json").all() if e.kind == "engine_defect"
    ]
    assert defects and "requestApproval" in defects[0].summary
    assert any(e.kind is AgentEventKind.WARNING for e in events)


def test_stop_interrupts_within_a_second_and_closes_the_child(tmp_path: Path) -> None:
    child = Child(tmp_path, "hang")
    approver = Approver()
    session, folders = _session(tmp_path, child, approver=approver)
    outcome: dict[str, Any] = {}
    runner = threading.Thread(target=lambda: outcome.update(result=session.run()))
    runner.start()
    deadline = time.monotonic() + 10
    while not child.received("turn/start") and time.monotonic() < deadline:
        time.sleep(0.02)
    assert child.received("turn/start")
    asked_at = time.monotonic()
    session.cancel()
    runner.join(timeout=3.0)
    assert not runner.is_alive(), "run() must return after Stop"
    assert time.monotonic() - asked_at < 1.0 + 2.0
    assert outcome["result"].status == "cancelled"
    interrupts = child.received("turn/interrupt")
    assert interrupts and interrupts[0]["t"] - asked_at < 1.0
    assert interrupts[0]["in"]["params"] == {"threadId": "thr_1", "turnId": "turn_1"}
    assert approver.cancelled
    assert child.servers[0].process is None
    assert not folders.root.exists()  # cleared on Stop (decision 4)


def test_close_kills_a_child_that_ignores_stdin(tmp_path: Path) -> None:
    child = Child(tmp_path, "stubborn")
    folders = agent_folders("codex", AGENT, base=tmp_path / "ai").prepare()
    server = child.server(folders, TOKEN, lambda _m, _p: None, lambda _m, _p: {})
    server.start()
    proc = server.process
    assert proc is not None and proc.poll() is None
    started = time.monotonic()
    server.close()
    assert time.monotonic() - started < 2.0
    assert proc.poll() is not None


def test_renewed_token_restarts_and_resumes_the_thread(tmp_path: Path) -> None:
    """G2 with a fake: an unauthorized turn renews once, restarts, resumes."""
    child = Child(tmp_path, "unauthorized_once")
    session, _folders = _session(tmp_path, child, tokens=["old-token", "old-token", "new-token"])
    result = session.run()
    assert result.status == "completed" and result.final_text == "Hello"
    assert session.restarts == 1
    assert [launch["env"][TOKEN_ENV] for launch in child.launches] == ["old-token", "new-token"]
    resume = child.received("thread/resume")
    assert resume and resume[0]["in"]["params"]["threadId"] == "thr_1"
    assert any(e.get("resume_found_thread_file") is True for e in child.entries())
    assert session.thread_id == "thr_1"
    assert len(child.received("thread/start")) == 1


def test_thread_files_are_swept_at_start_and_cleared_at_end(tmp_path: Path) -> None:
    child = Child(tmp_path)
    session, folders = _session(tmp_path, child)
    folders.home.mkdir(parents=True)
    (folders.home / "stale-thread.jsonl").write_text("{}", encoding="utf-8")
    session.run()
    launch = next(e for e in child.entries() if e.get("launch"))
    assert launch["home"] == str(folders.home)
    assert "stale-thread.jsonl" not in launch["home_listing"]
    assert not folders.root.exists()


def test_token_never_in_parent_environment_or_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-parent-secret-value-0123456789")
    child = Child(tmp_path)
    session, _folders = _session(tmp_path, child)
    with caplog.at_level(logging.DEBUG):
        assert session.run().status == "completed"
        time.sleep(0.1)  # let the stderr drain log what the child wrote
    assert TOKEN_ENV not in os.environ
    assert all(TOKEN not in value for value in os.environ.values())
    assert TOKEN not in caplog.text
    env = child.launches[0]["env"]
    assert env[TOKEN_ENV] == TOKEN and "OPENAI_API_KEY" not in env
    assert next(e for e in child.entries() if e.get("launch"))["token"] == TOKEN


def test_the_token_is_redacted_in_argv_logs_and_bundles() -> None:
    assert TOKEN not in format_args_for_log(["codex", f"{TOKEN_ENV}={TOKEN}", TOKEN])
    assert TOKEN not in redact_text_for_bundle(f"env {TOKEN_ENV}={TOKEN}\nplain {TOKEN}\n")


# -- the harness -------------------------------------------------------------------


def test_harness_is_registered_with_the_right_capabilities() -> None:
    from quill.core.ai.engines import build_engine_registry

    harness = build_engine_registry().get("codex")
    assert isinstance(harness, CodexHarness)
    caps = harness.capabilities()
    assert caps.tool_calling and caps.images and caps.requires_oauth and caps.app_tools
    assert not caps.mcp and not caps.audio
    assert supports_app_tools(harness)


def test_harness_reports_a_missing_engine_and_refuses_single_requests(tmp_path: Path) -> None:
    harness = CodexHarness(binary_resolver=lambda: None)
    assert harness.is_available() == (False, "This build does not include the Codex engine.")
    events: list[AgentEvent] = []
    session = harness.start_session(
        AgentSpec(id="a", display_name="A", system_prompt=""),
        AIContext(prompt="rewrite"),
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        events.append,
    )
    assert session.run().error == SINGLE_REQUEST_SENTENCE
