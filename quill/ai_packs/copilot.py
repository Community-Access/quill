"""GitHub Copilot SDK harness pack (PRD §18.5).

Optional extra ``quill[ai-copilot]`` (PyPI package ``github-copilot-sdk``, import
``copilot``). The Copilot SDK exposes the same agent runtime behind Copilot CLI;
it is imported lazily only when a session runs. Copilot authenticates via the
user's GitHub account (OAuth) by default, and also supports BYOK.

Integration note: the Copilot SDK is itself an agent that can edit files and run
shell commands, governed by an ``on_permission_request`` handler. QUILL must own
every edit, so this bridge **denies the SDK's own mutating tools** and uses the
session purely to produce text, which QUILL then applies through its reviewed
Safe Editor Tool Gateway (permission broker + diff preview + one-step undo). A
deeper integration — registering QUILL's editor tools as Copilot custom tools and
routing ``on_permission_request`` into the QUILL :class:`PermissionBroker` — is a
follow-up. Validated when ``quill[ai-copilot]`` is installed and authenticated.
"""

from __future__ import annotations

from quill.ai_packs._base import Invoke, SdkHarness
from quill.core.ai.harness import AgentSpec, AIContext, HarnessCapabilities

__all__ = ["CopilotHarness"]


class CopilotHarness(SdkHarness):
    pack_id = "copilot"
    pack_name = "GitHub Copilot SDK"
    extra = "ai-copilot"
    sdk_modules = ("copilot",)

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities(
            chat=True,
            streaming=True,
            tool_calling=True,
            patch_generation=True,
            mcp=True,
            skills=True,
            subagents=True,
            requires_oauth=True,  # default use_logged_in_user; BYOK also supported
            long_context=True,
        )

    def _make_invoke(self) -> Invoke:  # pragma: no cover - requires the SDK installed
        """Transport over the Copilot SDK's documented async session API.

        ``CopilotClient().create_session(on_permission_request=...)`` then
        ``session.send(prompt)``. The permission handler denies the SDK's own
        file/shell tools so QUILL applies the resulting text through its gateway.
        """
        import asyncio

        from copilot import CopilotClient  # type: ignore[import-not-found]
        from copilot.session import (  # type: ignore[import-not-found]
            PermissionDecisionReject,
        )

        def _deny_own_tools(request: object, invocation: object) -> object:
            # QUILL owns the editor: never let the SDK mutate files/shell directly.
            return PermissionDecisionReject(
                feedback="QUILL applies edits through its own reviewed editor gateway."
            )

        def invoke(agent: AgentSpec, ctx: AIContext) -> str:
            prompt = f"{agent.system_prompt}\n\n{ctx.prompt}\n\n{ctx.context_text}".strip()

            async def _run() -> str:
                async with CopilotClient() as client:
                    async with await client.create_session(
                        on_permission_request=_deny_own_tools
                    ) as session:
                        result = await session.send(prompt)
                        text = (
                            getattr(result, "text", None)
                            or getattr(result, "content", None)
                            or result
                        )
                        return str(text or "")

            return asyncio.run(_run())

        return invoke
