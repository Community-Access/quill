"""The engines added for project tasks: Ollama practice mode and Claude on your own key."""

from __future__ import annotations

import types
from pathlib import Path
from typing import Any

import pytest

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.family_tools import FamilyTool, FamilyToolRegistry
from quill.core.ai.harness import AgentSpec, AIContext
from quill.core.ai.harness.loop_session import ChatStep, LoopToolSession
from quill.core.ai.harness.ollama_tools import (
    PRACTICE_LABEL,
    OllamaToolHarness,
    parse_ollama_reply,
)
from quill.core.ai.permissions import PermissionBroker, PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import AgentIdentity


class _Approver:
    def ask(self, _tool: Any, _summary: str) -> ApprovalChoice:
        return ApprovalChoice.ONCE


def _registry(seen: list[dict[str, Any]]) -> FamilyToolRegistry:
    registry = FamilyToolRegistry(
        PermissionBroker(),
        ActivityLog(),
        AgentIdentity("t", RiskLevel.MEDIUM, harness="ollama"),
        app_scope="project",
    )
    registry.register_app(
        "project",
        [
            FamilyTool(
                name="project.read",
                description="Read a file.",
                handler=lambda args: seen.append(args) or "1: print(1)",
                parameters={"type": "object", "properties": {"path": {"type": "string"}}},
                category=PermissionCategory.READ_WORKSPACE,
                app="project",
            )
        ],
    )
    return registry


_AGENT = AgentSpec(id="p", display_name="P", system_prompt="Be careful.")


def test_the_loop_runs_each_tool_through_the_registry_and_ends_on_text() -> None:
    seen: list[dict[str, Any]] = []
    registry = _registry(seen)
    replies = iter([
        ChatStep(tool_calls=(("c1", "project_read", {"path": "cli.py"}),)),
        ChatStep(text="cli.py prints 1."),
    ])
    sent: list[list[dict[str, Any]]] = []

    def chat(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ChatStep:
        sent.append(list(messages))
        assert tools[0]["function"]["name"] == "project_read"
        return next(replies)

    session = LoopToolSession(
        _AGENT,
        AIContext(prompt="What does cli.py do?"),
        registry,
        _Approver(),
        lambda _e: None,
        chat,
    )
    result = session.run()
    assert result.status == "completed" and result.final_text == "cli.py prints 1."
    assert seen == [{"path": "cli.py"}]
    assert sent[1][-1] == {
        "role": "tool",
        "tool_call_id": "c1",
        "name": "project_read",
        "content": "1: print(1)",
    }
    assert sent[0][0] == {"role": "system", "content": "Be careful."}


def test_stop_ends_the_loop_before_the_next_request() -> None:
    registry = _registry([])
    calls = 0

    def chat(_m: Any, _t: Any) -> ChatStep:
        nonlocal calls
        calls += 1
        session.cancel()
        return ChatStep(tool_calls=(("c", "project_read", {}),))

    session = LoopToolSession(
        _AGENT, AIContext(prompt="x"), registry, _Approver(), lambda _e: None, chat
    )
    assert session.run().status == "cancelled" and calls == 1


def test_a_model_that_never_stops_is_capped() -> None:
    registry = _registry([])
    session = LoopToolSession(
        _AGENT,
        AIContext(prompt="x"),
        registry,
        _Approver(),
        lambda _e: None,
        lambda _m, _t: ChatStep(tool_calls=(("c", "project_read", {}),)),
        max_steps=3,
    )
    result = session.run()
    assert result.status == "error" and "stopped after 3 requests" in result.error


def test_ollama_practice_mode_talks_only_to_this_computer() -> None:
    from quill.core.ai.harness.ollama_tools import _post

    with pytest.raises(ValueError, match="only to Ollama on this computer"):
        _post("https://example.com/api/chat", {})
    assert "Nothing is sent" in PRACTICE_LABEL


def test_ollama_reply_and_request_shapes() -> None:
    step = parse_ollama_reply({
        "message": {
            "content": "",
            "tool_calls": [{"function": {"name": "project_read", "arguments": {"path": "a"}}}],
        }
    })
    assert step.tool_calls == (("call-0", "project_read", {"path": "a"}),)
    posted: list[dict[str, Any]] = []
    harness = OllamaToolHarness(
        "qwen3",
        post=lambda url, body: (
            posted.append({"url": url, **body}) or {"message": {"content": "hi"}}
        ),
    )
    assert harness.capabilities().app_tools and harness.capabilities().local_only
    registry = _registry([])
    session = harness.start_tool_session(
        _AGENT, AIContext(prompt="hello"), registry, _Approver(), lambda _e: None
    )
    assert session.run().final_text == "hi"
    assert posted[0]["url"] == "http://127.0.0.1:11434/api/chat"
    assert posted[0]["model"] == "qwen3" and posted[0]["stream"] is False
    assert posted[0]["tools"][0]["function"]["name"] == "project_read"


# -- Claude --------------------------------------------------------------------- #


def _fake_claude(record: dict[str, Any]) -> types.ModuleType:
    sdk = types.ModuleType("claude_agent_sdk")

    class Text:
        def __init__(self, text: str) -> None:
            self.text = text

    class Assistant:
        def __init__(self, blocks: list[Any]) -> None:
            self.content = blocks

    class Allow:
        pass

    class Deny:
        def __init__(self, message: str = "") -> None:
            self.message = message

    def tool(name: str, description: str, schema: dict[str, Any]):
        def wrap(fn):
            record.setdefault("tools", {})[name] = fn
            return fn

        return wrap

    class Options:
        def __init__(self, **kw: Any) -> None:
            record["options"] = kw

    class Client:
        def __init__(self, options: Any) -> None:
            self.options = options

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a: Any) -> None:
            return None

        async def query(self, prompt: str) -> None:
            record.setdefault("prompts", []).append(prompt)

        async def receive_response(self):
            handler = record["tools"]["project_read"]
            out = await handler({"path": "cli.py"})
            record["tool_out"] = out
            decision = await record["options"]["can_use_tool"](
                "Bash", {"command": "rm -rf /"}, None
            )
            record["bash"] = decision
            yield Assistant([Text("Read it.")])

    sdk.tool = tool
    sdk.create_sdk_mcp_server = lambda **kw: ("server", kw["name"])
    sdk.ClaudeAgentOptions = Options
    sdk.ClaudeSDKClient = Client
    sdk.AssistantMessage = Assistant
    sdk.TextBlock = Text
    sdk.PermissionResultAllow = Allow
    sdk.PermissionResultDeny = Deny
    return sdk


def test_claude_sees_only_quills_tools_and_its_builtins_are_denied(tmp_path: Path) -> None:
    from quill.ai_packs.claude_tool_session import CLAUDE_BUILTINS, ClaudeToolHarness

    record: dict[str, Any] = {}
    seen: list[dict[str, Any]] = []
    registry = _registry(seen)
    harness = ClaudeToolHarness(api_key="sk-test", sdk=_fake_claude(record))
    session = harness.start_tool_session(
        _AGENT, AIContext(prompt="Look."), registry, _Approver(), lambda _e: None
    )
    result = session.run()
    assert result.status == "completed" and result.final_text == "Read it."
    options = record["options"]
    assert options["allowed_tools"] == ["mcp__quill__project_read"]
    assert set(options["disallowed_tools"]) == set(CLAUDE_BUILTINS)
    assert "*" not in options["disallowed_tools"]  # it would deny QUILL's MCP tools too
    assert options["permission_mode"] == "default"
    assert options["env"] == {"ANTHROPIC_API_KEY": "sk-test"}
    assert (
        seen == [{"path": "cli.py"}] and record["tool_out"]["content"][0]["text"] == "1: print(1)"
    )
    assert type(record["bash"]).__name__ == "Deny"


def test_claude_builtin_turned_on_is_let_through_and_asked(tmp_path: Path) -> None:
    from quill.ai_packs.claude_tool_session import session_options

    registry = _registry([])
    registry.vendor_tools = frozenset({"Bash"})
    registry.vendor_kinds = frozenset({"shell"})
    registry.vendor_cwd = str(tmp_path)
    options = session_options(registry, "")
    assert "Bash" not in options["disallowed_tools"] and "Edit" in options["disallowed_tools"]
    assert options["cwd"] == str(tmp_path)


def test_the_text_pack_keeps_its_star_deny() -> None:
    from quill.ai_packs.claude import TEXT_ONLY_OPTIONS

    assert TEXT_ONLY_OPTIONS["disallowed_tools"] == ["*"]
