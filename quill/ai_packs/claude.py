"""Claude Agent SDK harness pack (PRD §18.5).

Optional extra ``quill[ai-claude]`` (PyPI package ``claude-agent-sdk``, import
``claude_agent_sdk``). The SDK wraps Anthropic's Claude Code agent runtime (a
bundled Claude Code CLI over stdio) and authenticates via ``ANTHROPIC_API_KEY``.
Imported lazily only when a session runs.

Integration note: like Copilot, the Claude Agent SDK is itself a tool-using agent
that can read/write files and run shell commands. QUILL must own every edit, so
this bridge runs it **text-only** — ``ClaudeAgentOptions(allowed_tools=[])`` — and
applies the resulting text through QUILL's reviewed Safe Editor Tool Gateway
(permission broker + diff preview + one-step undo). Wiring the SDK's own tools to
the QUILL gateway/broker is a follow-up. Validated when ``quill[ai-claude]`` is
installed and ``ANTHROPIC_API_KEY`` is set.
"""

from __future__ import annotations

from quill.ai_packs._base import Invoke, SdkHarness
from quill.core.ai.harness import AgentSpec, AIContext, HarnessCapabilities

__all__ = ["ClaudeAgentHarness"]


class ClaudeAgentHarness(SdkHarness):
    pack_id = "claude_agent_sdk"
    pack_name = "Claude Agent SDK"
    extra = "ai-claude"
    sdk_modules = ("claude_agent_sdk",)

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities(
            chat=True,
            streaming=True,
            tool_calling=True,
            patch_generation=True,
            mcp=True,
            skills=True,
            subagents=True,
            requires_api_key=True,
            images=True,
            long_context=True,
        )

    def _make_invoke(self) -> Invoke:  # pragma: no cover - requires the SDK installed
        """Transport over the Claude Agent SDK's documented ``query`` API.

        ``async for message in query(prompt=..., options=...)`` yields
        ``AssistantMessage`` objects whose ``content`` is a list of blocks; the
        ``TextBlock`` text is collected. Tools are disabled so the SDK never
        touches the filesystem/shell — QUILL applies the text via its gateway.
        """
        import asyncio

        from claude_agent_sdk import (  # type: ignore[import-not-found]
            AssistantMessage,
            ClaudeAgentOptions,
            TextBlock,
            query,
        )

        def invoke(agent: AgentSpec, ctx: AIContext) -> str:
            prompt = f"{agent.system_prompt}\n\n{ctx.prompt}\n\n{ctx.context_text}".strip()
            options = ClaudeAgentOptions(allowed_tools=[])  # text-only; no file/shell tools

            async def _run() -> str:
                chunks: list[str] = []
                async for message in query(prompt=prompt, options=options):
                    if isinstance(message, AssistantMessage):
                        for block in getattr(message, "content", []):
                            if isinstance(block, TextBlock):
                                chunks.append(block.text)
                return "".join(chunks)

            return asyncio.run(_run())

        return invoke
