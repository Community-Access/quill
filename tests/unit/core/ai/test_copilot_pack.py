"""The Copilot pack's SDK transport, driven against a fake ``copilot`` module.

No network and no real SDK: a stand-in module is placed in ``sys.modules`` so
``CopilotHarness._make_invoke`` runs its real code path -- the lazy import,
the client and session options, ``send_and_wait`` -- and records every call.

The fake mirrors ``github-copilot-sdk`` 1.0.28 as read from its source:
keyword-only signatures (so a misspelt argument fails here as it would there),
``RuntimeConnection.for_stdio(*, path=None, args=())`` returning a
``StdioRuntimeConnection``, the ``COPILOT_SDK_DEFAULT_CONNECTION`` check that
rejects ``env=`` for an in-process default, the tool-filter validation, the
60-second ``send_and_wait`` default, and ``PermissionDecisionReject`` living in
``copilot.rpc`` (with a ``ClassVar`` kind) and nowhere else.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
import types
from collections.abc import Sequence
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
        def for_stdio(*, path: str | None = None, args: Sequence[str] = ()) -> Any:
            return StdioRuntimeConnection(path=path, args=tuple(args))

        @staticmethod
        def for_inprocess() -> Any:
            return InProcessRuntimeConnection()

    @dataclass
    class StdioRuntimeConnection(RuntimeConnection):
        path: str | None = None
        args: Sequence[str] = ()
        env: dict[str, str] | None = None

    @dataclass
    class InProcessRuntimeConnection(RuntimeConnection):
        pass

    class CopilotSession:
        async def __aenter__(self) -> CopilotSession:
            return self

        async def __aexit__(self, *exc: object) -> None:
            await self.disconnect()

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
            connection: RuntimeConnection | None = None,
            working_directory: str | None = None,
            log_level: str = "info",
            env: dict[str, str] | None = None,
            github_token: str | None = None,
            base_directory: str | None = None,
            use_logged_in_user: bool | None = None,
        ) -> None:
            if connection is None:
                default = os.environ.get("COPILOT_SDK_DEFAULT_CONNECTION", "").strip().lower()
                connection = (
                    RuntimeConnection.for_inprocess()
                    if default == "inprocess"
                    else RuntimeConnection.for_stdio()
                )
            if isinstance(connection, InProcessRuntimeConnection) and env is not None:
                raise ValueError("env is not supported with RuntimeConnection.for_inprocess()")
            rec.client_kwargs = {
                key: value
                for key, value in {
                    "connection": connection,
                    "working_directory": working_directory,
                    "env": env,
                    "github_token": github_token,
                    "use_logged_in_user": use_logged_in_user,
                }.items()
                if value is not None
            }

        async def __aenter__(self) -> CopilotClient:
            return self

        async def __aexit__(self, *exc: object) -> None:
            rec.calls.append("stop")

        async def create_session(
            self,
            *,
            on_permission_request: Any = None,
            model: str | None = None,
            tools: list[Any] | None = None,
            system_message: dict[str, str] | None = None,
            available_tools: list[str] | None = None,
            excluded_tools: list[str] | None = None,
            working_directory: str | None = None,
            streaming: bool | None = None,
        ) -> CopilotSession:
            if isinstance(available_tools, str):
                raise TypeError("tool filter must be a ToolSet or list[str], not str")
            for name in available_tools or ():
                if name == "*" or not _TOOL_NAME.match(name):
                    raise ValueError(f"invalid available_tools entry {name!r}")
            if system_message is not None:
                assert system_message.get("mode", "append") in ("append", "replace", "customize")
            rec.session_kwargs = {
                key: value
                for key, value in {
                    "on_permission_request": on_permission_request,
                    "model": model,
                    "system_message": system_message,
                    "available_tools": available_tools,
                    "streaming": streaming,
                }.items()
                if value is not None
            }
            return CopilotSession()

    module = types.ModuleType("copilot")
    module.CopilotClient = CopilotClient  # type: ignore[attr-defined]
    module.RuntimeConnection = RuntimeConnection  # type: ignore[attr-defined]
    module.StdioRuntimeConnection = StdioRuntimeConnection  # type: ignore[attr-defined]
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
    monkeypatch.setattr(copilot_runtime, "find_copilot_cli", lambda: None)
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
    assert rec.calls == ["send_and_wait", "disconnect", "stop"]
    assert rec.sent == ["Say hi"]


def test_send_and_wait_gets_a_longer_timeout_than_the_sdk_default(rec: _Recorder, no_token) -> None:
    _run()
    assert rec.send_kwargs["timeout"] == pack.SEND_TIMEOUT_SECONDS
    assert pack.SEND_TIMEOUT_SECONDS > 60.0


def test_a_timeout_aborts_the_turn_before_closing(rec: _Recorder, no_token) -> None:
    rec.raise_on_wait = TimeoutError("Timeout after 600s waiting for session.idle")
    with pytest.raises(TimeoutError):
        _run()
    assert rec.calls == ["send_and_wait", "abort", "disconnect", "stop"]


def test_system_prompt_is_appended_not_glued_onto_the_prompt(rec: _Recorder, no_token) -> None:
    _run()
    assert rec.session_kwargs["system_message"] == {"mode": "append", "content": "Be brief."}
    assert "Be brief." not in rec.sent[0]


def test_blank_system_prompt_sends_no_system_message(rec: _Recorder, no_token) -> None:
    _run(system_prompt="  ")
    assert "system_message" not in rec.session_kwargs
    assert pack.system_message_for("") is None


def test_none_reply_is_empty_text_not_a_repr(rec: _Recorder, no_token) -> None:
    rec.reply = None
    assert _run() == ""


def test_token_passed_explicitly_and_never_in_environ(rec: _Recorder, monkeypatch) -> None:
    seen: list[str] = []

    def fake_stored(name: str = "QUILL") -> str:
        seen.append(name)
        return "gho_explicit"

    monkeypatch.setattr(copilot_auth, "stored_token", fake_stored)
    _run("QUILL Lite")
    assert seen == ["QUILL Lite"]  # read from this app's own entry at session start
    assert rec.client_kwargs["github_token"] == "gho_explicit"
    assert rec.client_kwargs["use_logged_in_user"] is False
    child_env = rec.client_kwargs["env"]
    assert isinstance(child_env, dict)
    assert "gho_explicit" not in child_env.values()
    for name in ("GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN", "COPILOT_SDK_AUTH_TOKEN"):
        assert name not in os.environ
        assert name not in rec.env_during_call
        assert name not in child_env


def test_no_stored_token_leaves_the_cli_sign_in(rec: _Recorder, no_token) -> None:
    _run()
    assert "github_token" not in rec.client_kwargs
    assert "use_logged_in_user" not in rec.client_kwargs  # SDK default: logged-in user


def test_inherited_token_vars_are_stripped_from_the_child(
    rec: _Recorder, no_token, monkeypatch
) -> None:
    monkeypatch.setenv("GH_TOKEN", "gho_from_shell")
    monkeypatch.setenv("COPILOT_SDK_AUTH_TOKEN", "gho_sdk_channel")
    _run()
    env = rec.client_kwargs["env"]
    assert "GH_TOKEN" not in env  # type: ignore[operator]
    assert "COPILOT_SDK_AUTH_TOKEN" not in env  # type: ignore[operator]


def test_transport_is_always_explicit_stdio(rec: _Recorder, no_token, monkeypatch) -> None:
    # An in-process default would make the real SDK reject env= with ValueError.
    monkeypatch.setenv("COPILOT_SDK_DEFAULT_CONNECTION", "inprocess")
    assert _run() == "The answer."
    connection = rec.client_kwargs["connection"]
    assert type(connection).__name__ == "StdioRuntimeConnection"
    assert connection.path is None  # type: ignore[attr-defined]  # no bundle: SDK's own


def test_available_tools_is_never_empty(rec: _Recorder, no_token) -> None:
    _run()
    tools = rec.session_kwargs["available_tools"]
    assert tools == [pack.TEXT_ONLY_TOOL_NAME]
    assert pack.available_tools_for([]) == [pack.TEXT_ONLY_TOOL_NAME]
    assert pack.available_tools_for(["quill_insert"]) == ["quill_insert"]


@pytest.mark.parametrize("kind", PERMISSION_KINDS)
def test_every_permission_request_is_refused(rec: _Recorder, no_token, kind: str) -> None:
    _run()
    handler = rec.session_kwargs["on_permission_request"]
    request = types.SimpleNamespace(kind=kind)
    decision = handler(request, {"session_id": "s1"})  # type: ignore[operator]
    assert isinstance(decision, PermissionDecisionReject)
    assert decision.kind == "reject"
    assert decision.feedback


def test_bundled_cli_is_used_and_download_switched_off(
    rec: _Recorder, no_token, monkeypatch, tmp_path: Path
) -> None:
    # A hostless bundle: the copilot.exe alias is a byte copy of the wrapper.
    exe = tmp_path / copilot_runtime.COPILOT_EXE
    exe.write_bytes(b"MZ pinned")
    (tmp_path / copilot_runtime.COPILOT_RUNTIME_WRAPPER).write_bytes(b"MZ pinned")
    (tmp_path / copilot_runtime.COPILOT_RUNTIME_NODE).write_bytes(b"MZ runtime")
    monkeypatch.setattr(
        copilot_runtime, "COPILOT_WRAPPER_SHA256", hashlib.sha256(b"MZ pinned").hexdigest()
    )
    monkeypatch.setattr(
        copilot_runtime, "COPILOT_RUNTIME_NODE_SHA256", hashlib.sha256(b"MZ runtime").hexdigest()
    )
    monkeypatch.setattr(copilot_runtime, "find_copilot_cli", lambda: exe)
    _run()
    connection = rec.client_kwargs["connection"]
    assert type(connection).__name__ == "StdioRuntimeConnection"
    assert connection.path == str(exe)  # type: ignore[attr-defined]
    env = rec.client_kwargs["env"]
    assert env["COPILOT_SKIP_CLI_DOWNLOAD"] == "1"  # type: ignore[index]
    assert env["COPILOT_CLI_PATH"] == str(exe)  # type: ignore[index]


def test_a_bundle_that_fails_the_pin_is_never_launched(
    rec: _Recorder, no_token, monkeypatch, tmp_path: Path
) -> None:
    exe = tmp_path / "copilot.exe"
    exe.write_bytes(b"MZ tampered")
    monkeypatch.setattr(copilot_runtime, "find_copilot_cli", lambda: exe)
    with pytest.raises(copilot_runtime.CopilotCliUnverified):
        _run()
    assert rec.client_kwargs == {}  # no client was ever made
    assert rec.calls == []


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
