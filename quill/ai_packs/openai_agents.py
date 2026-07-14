"""OpenAI Agents SDK harness pack (PRD §18.5).

Optional extra ``quill[ai-openai]``. Bridges the OpenAI Agents SDK (import name
``agents``) to QUILL's gateway; imported lazily only when a session runs.
"""

from __future__ import annotations

from quill.ai_packs._base import Invoke, SdkHarness
from quill.core.ai.harness import AgentSpec, AIContext, HarnessCapabilities

__all__ = ["OpenAIAgentsHarness"]


class OpenAIAgentsHarness(SdkHarness):
    pack_id = "openai_agents"
    pack_name = "OpenAI Agents SDK"
    extra = "ai-openai"
    sdk_modules = ("agents",)

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities(
            chat=True,
            streaming=True,
            tool_calling=True,
            patch_generation=True,
            mcp=True,
            subagents=True,  # handoffs
            requires_api_key=True,
            images=True,
            long_context=True,
        )

    def _make_invoke(self) -> Invoke:  # pragma: no cover - requires the SDK installed
        """Transport over the OpenAI Agents SDK's documented Agent + Runner API.

        Validated when ``quill[ai-openai]`` is installed; the SDK's function tools
        are wired to the gateway's typed tools. This first transport runs the
        agent synchronously and returns its final output for the gateway to apply.
        """
        from agents import Agent, Runner  # type: ignore[import-not-found]

        def invoke(agent: AgentSpec, ctx: AIContext) -> str:
            sdk_agent = Agent(name=agent.display_name, instructions=agent.system_prompt)
            user_input = f"{ctx.prompt}\n\n{ctx.context_text}".strip()
            result = Runner.run_sync(sdk_agent, user_input)
            return str(getattr(result, "final_output", "") or "")

        return invoke
