"""Claude Agent SDK harness pack (PRD §18.5).

Optional extra ``quill[ai-claude]`` (PyPI package ``claude-agent-sdk``, import
``claude_agent_sdk``). The SDK wraps Anthropic's Claude Code agent runtime (a
bundled Claude Code CLI over stdio) and authenticates via ``ANTHROPIC_API_KEY``.
Imported lazily only when a session runs.

Integration note: like Copilot, the Claude Agent SDK is itself a tool-using agent
that can read/write files and run shell commands. QUILL must own every edit, so
this bridge runs it **text-only** -- ``disallowed_tools=["*"]`` (see
:data:`TEXT_ONLY_OPTIONS`) -- and
applies the resulting text through QUILL's reviewed Safe Editor Tool Gateway
(permission broker + diff preview + one-step undo). Wiring the SDK's own tools to
the QUILL gateway/broker is a follow-up. Validated when ``quill[ai-claude]`` is
installed and ``ANTHROPIC_API_KEY`` is set.
"""

from __future__ import annotations

from quill.ai_packs._base import Invoke, SdkHarness
from quill.core.ai.harness import AgentSpec, AIContext, HarnessCapabilities

__all__ = ["TEXT_ONLY_OPTIONS", "ClaudeAgentHarness"]

#: How the SDK is told to use no tool of its own (code.md 1.5). ``allowed_tools``
#: only *pre-approves* tools; it hides nothing, so ``allowed_tools=[]`` alone
#: left every built-in tool visible to the model. Removing a tool means naming
#: it in ``disallowed_tools``, and ``"*"`` names them all; ``default`` mode then
#: refuses anything that slips through rather than running it.
TEXT_ONLY_OPTIONS: dict[str, object] = {
    "allowed_tools": [],
    "disallowed_tools": ["*"],
    "permission_mode": "default",
}


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

    def _make_invoke(self) -> Invoke:
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
            options = ClaudeAgentOptions(**TEXT_ONLY_OPTIONS)  # no file or shell tools

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
