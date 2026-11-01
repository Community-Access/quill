"""GitHub Copilot SDK harness pack (PRD §18.5).

Optional extra ``quill[ai-copilot]`` (PyPI package ``github-copilot-sdk``, import
``copilot``). The Copilot SDK exposes the same agent runtime behind Copilot CLI;
it is imported lazily only when a session runs.

Integration note: the Copilot SDK is itself an agent that can edit files and run
shell commands, governed by an ``on_permission_request`` handler. QUILL must own
every edit, so this bridge **offers the SDK none of its own tools and refuses
every permission request**, and uses the session purely to produce text, which
QUILL then applies through its reviewed Safe Editor Tool Gateway (permission
broker + diff preview + one-step undo). Registering QUILL's editor tools as
Copilot custom tools is the follow-up (the agent engines phase).

How a session is made, and why:

- **The answer, not a request id.** ``session.send`` returns a request id and
  does not wait; the pack calls ``send_and_wait``, which waits for the session
  to go idle and returns the final assistant message (or None).
- **The token is explicit.** It is read from this app's own Copilot store entry
  (:func:`quill.core.ai.copilot_auth.stored_token`) when the session starts and
  passed as ``github_token=``; it is never placed in ``os.environ``. With no
  stored token the SDK falls back to the CLI's own signed-in user.
- **The child inherits no credential.** ``env=`` is
  :func:`quill.core.ai.copilot_runtime.copilot_child_env`, which strips every
  GitHub and cloud token variable.
- **The bundled CLI.** When the build carries ``tools\\copilot\\copilot.exe``
  (or ``COPILOT_CLI_PATH`` names one), the SDK is pointed at it over stdio and
  told not to download its own. A bundled exe must match the build's SHA-256
  pin first, or the session fails with a coded error instead of launching it.
- **Never an empty tool list.** An empty ``available_tools`` has been seen to
  expose every built-in (Copilot CLI issue #5306), so a text-only session still
  passes a non-empty allowlist that names only QUILL-owned tools -- today a
  single QUILL name that matches no built-in (:data:`TEXT_ONLY_TOOL_NAME`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.ai_packs._base import Invoke, SdkHarness
from quill.core.ai import copilot_auth
from quill.core.ai.copilot_runtime import cli_path_for_launch, copilot_child_env
from quill.core.ai.harness import AgentSpec, AIContext, HarnessCapabilities

__all__ = [
    "CopilotHarness",
    "TEXT_ONLY_TOOL_NAME",
    "available_tools_for",
    "answer_text",
]

#: A QUILL-owned tool name that matches no Copilot built-in. Listing it alone
#: is how a text-only session says "no vendor tools" without the empty list.
TEXT_ONLY_TOOL_NAME = "quill_text_only"

_REFUSAL = "QUILL applies edits through its own reviewed editor gateway."


def available_tools_for(quill_tool_names: Sequence[str] = ()) -> list[str]:
    """The ``available_tools`` allowlist: QUILL's own names, never empty."""
    names = [name for name in quill_tool_names if name.strip()]
    return names or [TEXT_ONLY_TOOL_NAME]


def answer_text(result: object) -> str:
    """The assistant's text from a ``send_and_wait`` result ("" for None).

    The SDK returns the final ``assistant.message`` event, whose text is
    ``event.data.content``; plain ``text``/``content`` attributes and a bare
    string are accepted too, so a minor SDK shape change degrades to text
    rather than to an object's repr.
    """
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    data = getattr(result, "data", None)
    for holder in (data, result):
        if holder is None:
            continue
        for attr in ("content", "text"):
            value = getattr(holder, attr, None)
            if isinstance(value, str):
                return value
    return ""


def _reject_class() -> Any:
    """``PermissionDecisionReject``; its module moved between SDK releases."""
    try:
        from copilot.rpc import PermissionDecisionReject  # type: ignore[import-not-found]
    except ImportError:
        from copilot.session import PermissionDecisionReject  # type: ignore[import-not-found]
    return PermissionDecisionReject


class CopilotHarness(SdkHarness):
    pack_id = "copilot"
    pack_name = "GitHub Copilot SDK"
    extra = "ai-copilot"
    sdk_modules = ("copilot",)

    def __init__(
        self,
        invoke: Invoke | None = None,
        *,
        agent_name: str = copilot_auth.DEFAULT_AGENT_NAME,
    ) -> None:
        super().__init__(invoke)
        self.agent_name = agent_name

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

    def _make_invoke(self) -> Invoke:
        """Transport over the Copilot SDK's async session API.

        ``CopilotClient(github_token=..., env=..., connection=...)``, then
        ``create_session(available_tools=[...], on_permission_request=...)``,
        then ``session.send_and_wait(prompt)``. The SDK is imported here, never
        at module import.
        """
        import asyncio

        import copilot  # type: ignore[import-not-found]

        reject = _reject_class()
        agent_name = self.agent_name

        def _deny_own_tools(request: object, invocation: object) -> object:
            # QUILL owns the editor: never let the SDK mutate files/shell directly.
            return reject(feedback=_REFUSAL)

        def _client_kwargs() -> dict[str, object]:
            cli_path = cli_path_for_launch()  # raises on a bundle that fails the pin
            kwargs: dict[str, object] = {"env": copilot_child_env(cli_path)}
            token = copilot_auth.stored_token(agent_name)
            if token:
                kwargs["github_token"] = token
                kwargs["use_logged_in_user"] = False
            if cli_path is not None:
                connection_cls = getattr(copilot, "RuntimeConnection", None)
                if connection_cls is not None:
                    kwargs["connection"] = connection_cls.for_stdio(path=str(cli_path))
            return kwargs

        def invoke(agent: AgentSpec, ctx: AIContext) -> str:
            prompt = f"{agent.system_prompt}\n\n{ctx.prompt}\n\n{ctx.context_text}".strip()

            async def _run() -> str:
                async with copilot.CopilotClient(**_client_kwargs()) as client:
                    async with await client.create_session(
                        available_tools=available_tools_for(),
                        on_permission_request=_deny_own_tools,
                    ) as session:
                        result = await session.send_and_wait(prompt)
                        return answer_text(result)

            return asyncio.run(_run())

        return invoke
