"""The Copilot pack's SDK transport, driven against a fake ``copilot`` module.

No network and no real SDK: a stand-in module is placed in ``sys.modules`` so
``CopilotHarness._make_invoke`` runs its real code path -- the lazy import,
the client and session options, ``send_and_wait`` -- and records every call.

The fake mirrors the SDK 2.0.1 grouped client/session options, in-process
runtime connection, tool allowlist, and ``copilot.rpc`` permission decisions.
"""

from __future__ import annotations

import os
import re
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import pytest

import quill.ai_packs.copilot as pack
from quill.core.ai import copilot_auth, copilot_runtime
from quill.core.ai.harness import AgentSpec, AIContext

_TOOL_NAME = re.compile(r"^(?:(?:builtin|custom|mcp):)?(?:[a-zA-Z0-9_-]+|\*)$")

#: Every ``request.kind`` the 1.0.28 ``PermissionRequest`` union can carry.
PERMISSION_KINDS = (
    "shell",
    "write",
    "read",
    "mcp",
    "url",
    "memory",
    "custom-tool",
    "hook",
    "extension-management",
    "workflow",
    "extension-permission-access",
    "extension-env-access",
)


@dataclass
class AssistantMessageData:
    content: str
    message_id: str = "m1"


class _Event:
    """A ``SessionEvent``: ``type`` plus typed ``data``."""

    def __init__(self, content: str) -> None:
        self.type = "assistant.message"
        self.data = AssistantMessageData(content=content)


@dataclass
class PermissionDecisionReject:
    kind: ClassVar[str] = "reject"
    feedback: str | None = None


@dataclass
class PermissionDecisionApproveOnce:
    kind: ClassVar[str] = "approve-once"


class _Recorder:
    def __init__(self) -> None:
        self.client_kwargs: dict[str, object] = {}
        self.session_kwargs: dict[str, object] = {}
        self.sent: list[str] = []
        self.send_kwargs: dict[str, object] = {}
        self.calls: list[str] = []
        self.env_during_call: dict[str, str] = {}
        self.reply: object = _Event("The answer.")
        self.raise_on_wait: BaseException | None = None


def _fake_sdk(rec: _Recorder) -> types.ModuleType:
    @dataclass
    class RuntimeConnection:
        @staticmethod
        def for_inprocess(*, base_directory: str | None = None) -> Any:
            return InProcessRuntimeConnection(base_directory=base_directory)

    @dataclass
    class InProcessRuntimeConnection(RuntimeConnection):
        base_directory: str | None = None

    class CopilotSession:
        async def send(
            self, prompt: str, *, attachments: list[dict[str, Any]] | None = None
        ) -> str:
            rec.calls.append("send")
            return "message-id-123"

        async def send_and_wait(
            self,
            prompt: str,
            *,
            attachments: list[dict[str, Any]] | None = None,
            timeout: float = 60.0,
        ) -> object:
            rec.calls.append("send_and_wait")
            rec.sent.append(prompt)
            rec.send_kwargs = {"attachments": attachments, "timeout": timeout}
            rec.env_during_call = dict(os.environ)
            if rec.raise_on_wait is not None:
                raise rec.raise_on_wait
            return rec.reply

        async def abort(self) -> None:
            rec.calls.append("abort")

        async def disconnect(self) -> None:
            rec.calls.append("disconnect")

    class CopilotClient:
        def __init__(
            self,
            *,
            mode: str,
            runtime: RuntimeConnection,
            github: dict[str, Any],
            network: dict[str, Any] | None = None,
        ) -> None:
            assert mode == "empty"
            assert isinstance(runtime, InProcessRuntimeConnection)
            assert runtime.base_directory
            rec.client_kwargs = {
                "mode": mode,
                "runtime": runtime,
                "github": github,
                "network": network,
            }

        async def start(self) -> None:
            rec.calls.append("start")

        async def stop(self) -> None:
            rec.calls.append("stop")

        async def create_session(self, **kwargs: Any) -> CopilotSession:
            tools = kwargs.get("tools")
            system_message = kwargs.get("system_message")
            available_tools = (tools or {}).get("available_tools", [])
            for name in available_tools:
                if name == "*" or not _TOOL_NAME.match(name):
                    raise ValueError(f"invalid available_tools entry {name!r}")
            if system_message is not None:
                assert system_message.get("mode", "append") in ("append", "replace", "customize")
            rec.session_kwargs = kwargs
            return CopilotSession()

    module = types.ModuleType("copilot")
    module.CopilotClient = CopilotClient  # type: ignore[attr-defined]
    module.RuntimeConnection = RuntimeConnection  # type: ignore[attr-defined]
    module.InProcessRuntimeConnection = InProcessRuntimeConnection  # type: ignore[attr-defined]
    return module


@pytest.fixture
def rec(monkeypatch: pytest.MonkeyPatch, absent_env) -> _Recorder:
    recorder = _Recorder()
    rpc = types.ModuleType("copilot.rpc")
    rpc.PermissionDecisionReject = PermissionDecisionReject  # type: ignore[attr-defined]
    rpc.PermissionDecisionApproveOnce = PermissionDecisionApproveOnce  # type: ignore[attr-defined]
    module = _fake_sdk(recorder)
    module.rpc = rpc  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "copilot", module)
    monkeypatch.setitem(sys.modules, "copilot.rpc", rpc)
    absent_env(
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "COPILOT_GITHUB_TOKEN",
        "COPILOT_CLI_PATH",
        "COPILOT_SDK_AUTH_TOKEN",
        "COPILOT_SDK_DEFAULT_CONNECTION",
    )
    monkeypatch.setattr(pack, "resolve_runtime_path", lambda: Path("runtime.node"))
    monkeypatch.setattr(pack, "prepare_inprocess_runtime", lambda: Path("runtime.node"))
    return recorder


def _agent(system_prompt: str = "Be brief.") -> AgentSpec:
    return AgentSpec(id="t", display_name="Test", system_prompt=system_prompt)


def _ctx() -> AIContext:
    return AIContext(prompt="Say hi", context_text="")


def _run(agent_name: str = "QUILL", system_prompt: str = "Be brief.") -> str:
    harness = pack.CopilotHarness(agent_name=agent_name)
    return harness._make_invoke()(_agent(system_prompt), _ctx())


@pytest.fixture
def no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": None)


def test_uses_send_and_wait_and_returns_the_answer(rec: _Recorder, no_token) -> None:
    assert _run() == "The answer."
    assert rec.calls == ["start", "send_and_wait", "disconnect", "stop"]
    assert rec.sent == ["Say hi"]


def test_send_and_wait_gets_a_longer_timeout_than_the_sdk_default(rec: _Recorder, no_token) -> None:
    _run()
    assert rec.send_kwargs["timeout"] == pack.SEND_TIMEOUT_SECONDS
    assert pack.SEND_TIMEOUT_SECONDS > 60.0


def test_a_timeout_aborts_the_turn_before_closing(rec: _Recorder, no_token) -> None:
    rec.raise_on_wait = TimeoutError("Timeout after 600s waiting for session.idle")
    with pytest.raises(TimeoutError):
        _run()
    assert rec.calls == ["start", "send_and_wait", "abort", "disconnect", "stop"]


def test_system_prompt_is_appended_not_glued_onto_the_prompt(rec: _Recorder, no_token) -> None:
    _run()
    assert rec.session_kwargs["system_message"] == {"mode": "append", "content": "Be brief."}
    assert "Be brief." not in rec.sent[0]


def test_blank_system_prompt_sends_no_system_message(rec: _Recorder, no_token) -> None:
    _run(system_prompt="  ")
    assert "system_message" not in rec.session_kwargs
    assert pack.system_message_for("") is None


def test_token_passed_explicitly_and_never_in_environ(rec: _Recorder, monkeypatch) -> None:
    seen: list[str] = []

    def fake_stored(name: str = "QUILL") -> str:
        seen.append(name)
        return "gho_explicit"

    monkeypatch.setattr(copilot_auth, "stored_token", fake_stored)
    _run("QUILL Lite")
    assert seen == ["QUILL Lite"]  # read from this app's own entry at session start
    assert rec.client_kwargs["github"] == {
        "token": "gho_explicit",
        "use_logged_in_user": False,
    }
    for name in ("GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN", "COPILOT_SDK_AUTH_TOKEN"):
        assert name not in os.environ
        assert name not in rec.env_during_call


def test_no_stored_token_never_borrows_a_cli_sign_in(rec: _Recorder, no_token) -> None:
    _run()
    assert rec.client_kwargs["github"] == {"use_logged_in_user": False}
    assert rec.client_kwargs["network"]["scope"] == "connection"
    assert rec.client_kwargs["network"]["resolve_proxy"].__name__ == "resolve_system_proxy"


def test_byok_uses_the_selected_saved_provider_without_github_auth(
    rec: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core import assistant_ai
    from quill.core.ai import own_key_providers

    monkeypatch.setattr(
        own_key_providers, "host_for", lambda _provider: "https://api.openai.com/v1"
    )
    monkeypatch.setattr(assistant_ai, "stored_provider_api_key", lambda _provider: "sk-stored")
    monkeypatch.setattr(
        copilot_auth,
        "stored_token",
        lambda *_a: pytest.fail("BYOK must not read a GitHub token"),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-ambient")
    harness = pack.CopilotByokHarness(provider="openai", model="gpt-selected")

    assert harness._make_invoke()(_agent(), _ctx()) == "The answer."
    assert rec.client_kwargs["github"] == {"use_logged_in_user": False}
    assert rec.session_kwargs["github"] == {
        "capi": {"enabled": False},
        "telemetry_enabled": False,
    }
    assert rec.session_kwargs["model"] == "gpt-selected"
    assert rec.session_kwargs["inference"] == {
        "default_provider": "quill_user",
        "providers": [
            {
                "name": "quill_user",
                "type": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-stored",
            }
        ],
    }
    assert rec.env_during_call["OPENAI_API_KEY"] == "sk-ambient"
    assert "token" not in rec.client_kwargs["github"]


def test_inherited_token_vars_are_not_used_for_github_auth(
    rec: _Recorder, no_token, monkeypatch
) -> None:
    monkeypatch.setenv("GH_TOKEN", "gho_from_shell")
    _run()
    assert "GH_TOKEN" in rec.env_during_call
    assert rec.client_kwargs["github"]["use_logged_in_user"] is False


def test_transport_is_always_explicit_inprocess(rec: _Recorder, no_token, monkeypatch) -> None:
    monkeypatch.setenv("COPILOT_SDK_DEFAULT_CONNECTION", "inprocess")
    assert _run() == "The answer."
    assert rec.client_kwargs["mode"] == "empty"
    connection = rec.client_kwargs["runtime"]
    assert type(connection).__name__ == "InProcessRuntimeConnection"
    assert connection.base_directory  # type: ignore[attr-defined]
    assert "env" not in rec.client_kwargs


def test_available_tools_is_never_empty(rec: _Recorder, no_token) -> None:
    _run()
    tools = rec.session_kwargs["tools"]["available_tools"]
    assert tools == [pack.TEXT_ONLY_TOOL_NAME]
    assert pack.available_tools_for([]) == [pack.TEXT_ONLY_TOOL_NAME]
    assert pack.available_tools_for(["quill_insert"]) == ["quill_insert"]


@pytest.mark.parametrize("kind", PERMISSION_KINDS)
def test_every_permission_request_is_refused(rec: _Recorder, no_token, kind: str) -> None:
    _run()
    handler = rec.session_kwargs["permissions"]["on_request"]
    request = types.SimpleNamespace(kind=kind)
    decision = handler(request, {"session_id": "s1"})  # type: ignore[operator]
    assert isinstance(decision, PermissionDecisionReject)
    assert decision.kind == "reject"
    assert decision.feedback


def test_verified_runtime_is_used_without_a_cli(
    rec: _Recorder, no_token, monkeypatch, tmp_path: Path
) -> None:
    runtime = tmp_path / "runtime.node"
    monkeypatch.setattr(pack, "prepare_inprocess_runtime", lambda: runtime)
    _run()
    assert rec.client_kwargs["mode"] == "empty"
    assert type(rec.client_kwargs["runtime"]).__name__ == "InProcessRuntimeConnection"
    assert "env" not in rec.client_kwargs


def test_an_unavailable_runtime_is_never_launched(
    rec: _Recorder, no_token, monkeypatch, tmp_path: Path
) -> None:
    def unavailable() -> Path:
        raise copilot_runtime.CopilotRuntimeUnavailable("runtime missing")

    monkeypatch.setattr(pack, "prepare_inprocess_runtime", unavailable)
    with pytest.raises(copilot_runtime.CopilotRuntimeUnavailable):
        _run()
    assert rec.client_kwargs == {}  # no client was ever made
    assert rec.calls == []


@pytest.mark.parametrize("reply", [None, _Event(""), _Event("   ")])
def test_an_empty_reply_is_an_error_not_an_empty_insert(rec: _Recorder, no_token, reply) -> None:
    rec.reply = reply
    with pytest.raises(pack.CopilotNoReplyError, match="without an answer"):
        _run()


def test_answer_text_shapes() -> None:
    assert pack.answer_text(None) == ""
    assert pack.answer_text("plain") == "plain"
    assert pack.answer_text(_Event("from data")) == "from data"
    assert pack.answer_text(types.SimpleNamespace(text="from text")) == "from text"
    assert pack.answer_text(object()) == ""


def test_sdk_import_stays_lazy() -> None:
    source = Path(pack.__file__).read_text(encoding="utf-8")
    module_level = source.split("class CopilotHarness", 1)[0]
    assert "\nimport copilot" not in module_level
    assert "\nfrom copilot" not in module_level
