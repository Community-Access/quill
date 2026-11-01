"""The Copilot pack's SDK transport, driven against a fake ``copilot`` module.

No network and no real SDK: a stand-in module is placed in ``sys.modules`` so
``CopilotHarness._make_invoke`` runs its real code path -- the lazy import,
the client and session options, ``send_and_wait`` -- and records every call.
"""

from __future__ import annotations

import hashlib
import os
import sys
import types
from pathlib import Path

import pytest

import quill.ai_packs.copilot as pack
from quill.core.ai import copilot_auth, copilot_runtime
from quill.core.ai.harness import AgentSpec, AIContext


class _Event:
    def __init__(self, content: str) -> None:
        self.data = types.SimpleNamespace(content=content)


class _Reject:
    def __init__(self, feedback: str) -> None:
        self.feedback = feedback


class _Recorder:
    def __init__(self) -> None:
        self.client_kwargs: dict[str, object] = {}
        self.session_kwargs: dict[str, object] = {}
        self.sent: list[str] = []
        self.calls: list[str] = []
        self.env_during_call: dict[str, str] = {}
        self.reply: object = _Event("The answer.")


def _fake_sdk(rec: _Recorder) -> types.ModuleType:
    class _Session:
        async def __aenter__(self) -> _Session:
            return self

        async def __aexit__(self, *exc: object) -> None:
            return None

        async def send(self, prompt: str) -> str:
            rec.calls.append("send")
            return "request-id-123"

        async def send_and_wait(self, prompt: str) -> object:
            rec.calls.append("send_and_wait")
            rec.sent.append(prompt)
            rec.env_during_call = dict(os.environ)
            return rec.reply

    class CopilotClient:
        def __init__(self, **kwargs: object) -> None:
            rec.client_kwargs = kwargs

        async def __aenter__(self) -> CopilotClient:
            return self

        async def __aexit__(self, *exc: object) -> None:
            return None

        async def create_session(self, **kwargs: object) -> _Session:
            rec.session_kwargs = kwargs
            return _Session()

    class RuntimeConnection:
        def __init__(self, path: str) -> None:
            self.path = path

        @classmethod
        def for_stdio(cls, path: str | None = None) -> RuntimeConnection:
            return cls(path or "")

    module = types.ModuleType("copilot")
    module.CopilotClient = CopilotClient  # type: ignore[attr-defined]
    module.RuntimeConnection = RuntimeConnection  # type: ignore[attr-defined]
    return module


@pytest.fixture
def rec(monkeypatch: pytest.MonkeyPatch, absent_env) -> _Recorder:
    recorder = _Recorder()
    rpc = types.ModuleType("copilot.rpc")
    rpc.PermissionDecisionReject = _Reject  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "copilot", _fake_sdk(recorder))
    monkeypatch.setitem(sys.modules, "copilot.rpc", rpc)
    absent_env("GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN", "COPILOT_CLI_PATH")
    monkeypatch.setattr(copilot_runtime, "find_copilot_cli", lambda: None)
    return recorder


def _agent() -> AgentSpec:
    return AgentSpec(id="t", display_name="Test", system_prompt="Be brief.")


def _ctx() -> AIContext:
    return AIContext(prompt="Say hi", context_text="")


def _run(agent_name: str = "QUILL") -> str:
    return pack.CopilotHarness(agent_name=agent_name)._make_invoke()(_agent(), _ctx())


def test_uses_send_and_wait_and_returns_the_answer(rec: _Recorder, monkeypatch) -> None:
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": None)
    assert _run() == "The answer."
    assert rec.calls == ["send_and_wait"]
    assert "Say hi" in rec.sent[0]


def test_none_reply_is_empty_text_not_a_repr(rec: _Recorder, monkeypatch) -> None:
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": None)
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
    for name in ("GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN"):
        assert name not in os.environ
        assert name not in rec.env_during_call
        assert name not in child_env


def test_no_stored_token_leaves_the_cli_sign_in(rec: _Recorder, monkeypatch) -> None:
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": None)
    _run()
    assert "github_token" not in rec.client_kwargs


def test_inherited_token_vars_are_stripped_from_the_child(rec: _Recorder, monkeypatch) -> None:
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": None)
    monkeypatch.setenv("GH_TOKEN", "gho_from_shell")
    _run()
    assert "GH_TOKEN" not in rec.client_kwargs["env"]  # type: ignore[operator]


def test_available_tools_is_never_empty(rec: _Recorder, monkeypatch) -> None:
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": None)
    _run()
    tools = rec.session_kwargs["available_tools"]
    assert tools == [pack.TEXT_ONLY_TOOL_NAME]
    assert pack.available_tools_for([]) == [pack.TEXT_ONLY_TOOL_NAME]
    assert pack.available_tools_for(["quill_insert"]) == ["quill_insert"]


def test_every_permission_request_is_refused(rec: _Recorder, monkeypatch) -> None:
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": None)
    _run()
    handler = rec.session_kwargs["on_permission_request"]
    decision = handler(object(), object())  # type: ignore[operator]
    assert isinstance(decision, _Reject)


def test_bundled_cli_is_used_and_download_switched_off(
    rec: _Recorder, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": None)
    exe = tmp_path / "copilot.exe"
    exe.write_bytes(b"MZ pinned")
    monkeypatch.setattr(
        copilot_runtime, "COPILOT_EXE_SHA256", hashlib.sha256(b"MZ pinned").hexdigest()
    )
    monkeypatch.setattr(copilot_runtime, "find_copilot_cli", lambda: exe)
    _run()
    assert rec.client_kwargs["connection"].path == str(exe)  # type: ignore[union-attr]
    env = rec.client_kwargs["env"]
    assert env["COPILOT_SKIP_CLI_DOWNLOAD"] == "1"  # type: ignore[index]


def test_a_bundle_that_fails_the_pin_is_never_launched(
    rec: _Recorder, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": None)
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
