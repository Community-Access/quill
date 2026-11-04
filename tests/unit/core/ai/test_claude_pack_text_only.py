"""The Claude pack hides every built-in tool, not just pre-approves none (code.md 1.5).

``allowed_tools=[]`` only says "pre-approve nothing"; the model still saw
Claude Code's file and shell tools. A fake SDK records the options the pack
builds, so this runs without the real package.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from quill.ai_packs.claude import TEXT_ONLY_OPTIONS, ClaudeAgentHarness
from quill.core.ai.harness import AgentSpec, AIContext


class _Text:
    def __init__(self, text: str) -> None:
        self.text = text


class _Assistant:
    def __init__(self, blocks: list[Any]) -> None:
        self.content = blocks


def _fake_sdk(seen: list[dict[str, Any]]) -> types.ModuleType:
    module = types.ModuleType("claude_agent_sdk")

    class ClaudeAgentOptions:
        def __init__(self, **kwargs: Any) -> None:
            seen.append(kwargs)

    async def query(*, prompt: str, options: Any):  # noqa: ARG001 - the SDK's shape
        yield _Assistant([_Text("hello")])

    module.ClaudeAgentOptions = ClaudeAgentOptions  # type: ignore[attr-defined]
    module.AssistantMessage = _Assistant  # type: ignore[attr-defined]
    module.TextBlock = _Text  # type: ignore[attr-defined]
    module.query = query  # type: ignore[attr-defined]
    return module


def test_every_builtin_tool_is_disallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, Any]] = []
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", _fake_sdk(seen))
    invoke = ClaudeAgentHarness()._make_invoke()
    agent = AgentSpec(id="t", display_name="T", system_prompt="Be brief.")
    assert invoke(agent, AIContext(prompt="Hi")) == "hello"
    assert seen == [TEXT_ONLY_OPTIONS]
    assert seen[0]["disallowed_tools"] == ["*"]
    assert seen[0]["permission_mode"] == "default"
