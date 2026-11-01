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

How a session is made, and why (checked against the SDK 1.0.28 source):

- **The answer, not a request id.** ``session.send`` returns a message id and
  does not wait; the pack calls ``send_and_wait(prompt, timeout=...)``, which
  returns the final ``assistant.message`` event (or None). Its default timeout
  is 60 seconds and a timeout does *not* stop the agent, so the pack passes
  :data:`SEND_TIMEOUT_SECONDS` and calls ``session.abort()`` when it expires.
- **The system prompt is appended, not glued on.** It travels as
  ``system_message={"mode": "append", "content": ...}``, keeping the CLI's own
  safety sections; ``"replace"`` would remove them.
- **The token is explicit.** It is read from this app's own Copilot store entry
  (:func:`quill.core.ai.copilot_auth.stored_token`) when the session starts and
  passed as ``github_token=`` with ``use_logged_in_user=False``; it is never
  placed in ``os.environ``. The SDK hands it to the child as
  ``COPILOT_SDK_AUTH_TOKEN`` with ``--auth-token-env`` (and adds
  ``--no-auto-login``). With no stored token the SDK falls back to the CLI's
  own signed-in user.
- **The child inherits no other credential.** ``env=`` is
  :func:`quill.core.ai.copilot_runtime.copilot_child_env`, which strips every
  GitHub and cloud token variable.
- **The transport is pinned to stdio.** ``connection=`` is always
  ``RuntimeConnection.for_stdio(path=...)``: left unset, the SDK reads
  ``COPILOT_SDK_DEFAULT_CONNECTION`` and an ``inprocess`` value there would
  reject ``env=`` outright.
- **The bundled CLI.** When the build carries the SDK's hostless runtime
  bundle in ``tools\\copilot`` (entrypoint ``copilot.exe``, the alias of
  ``copilot-runtime.exe``; or ``COPILOT_CLI_PATH`` names one), it is the stdio
  ``path``, so the SDK never reaches its own download. A bundled entrypoint and
  its ``runtime.node`` must match the build's SHA-256 pins first, or the session
  fails with a coded error instead of launching it.
- **Never an empty tool list.** An empty ``available_tools`` has been seen to
  expose every built-in (Copilot CLI issue #5306), so a text-only session still
  passes a non-empty allowlist that names only QUILL-owned tools -- today a
  single QUILL name that matches no built-in (:data:`TEXT_ONLY_TOOL_NAME`).
  Names must match ``^[a-zA-Z0-9_-]+$``; a bare ``"*"`` is rejected.

SDK 1.0.28 facts recorded for later phases (read from source, not built here):

- **Permission requests** arrive as ``(request, invocation)``; ``request.kind``
  is one of ``shell``, ``write``, ``read``, ``url``, ``mcp``, ``memory``,
  ``custom-tool``, ``hook``, ``workflow``, ``extension-management``,
  ``extension-permission-access``, ``extension-env-access``. Answers are
  ``copilot.rpc.PermissionDecisionReject(feedback=...)`` /
  ``PermissionDecisionApproveOnce()`` (``copilot.PermissionNoResult()``
  abstains). A QUILL custom tool will also be asked about as ``custom-tool``
  unless it is declared with ``Tool(skip_permission=True)``.
- **Custom tools** are ``copilot.tools.Tool(name, description, handler,
  parameters, skip_permission=...)`` (or ``define_tool``); the handler takes a
  ``ToolInvocation`` and returns ``ToolResult(text_result_for_llm=...,
  result_type="success", binary_results_for_llm=[ToolBinaryResult(data=<b64>,
  mime_type="image/png", type="image")])`` -- so a tool *can* hand the model an
  image (gate G6), subject to the model's ``capabilities.supports.vision``.
- **Attachments** go on ``send``/``send_and_wait(..., attachments=[...])``:
  ``{"type": "blob", "data": <b64>, "mimeType": ...}`` or
  ``{"type": "file", "path": ...}``.
- **Events** (``session.on(handler)``, returns an unsubscribe):
  ``assistant.message_delta`` (``data.delta_content``, needs
  ``create_session(streaming=True)``), ``assistant.message``
  (``data.content``), ``session.idle``, ``session.error``, ``assistant.usage``
  (per call: ``data.model``, tokens, ``cost``, ``copilot_usage``) and
  ``session.usage_info``.
- **Stopping (G4):** ``await session.abort()`` cancels the turn and keeps the
  session; ``await session.disconnect()`` releases it (the ``async with`` exit);
  ``await client.stop()`` is graceful (the ``async with`` exit),
  ``await client.force_stop()`` kills the child.
- **Quota and models (Phase 2):** ``await client.rpc.account.get_quota(
  copilot.rpc.AccountGetQuotaRequest())`` (wire ``account.getQuota``) returns
  ``quota_snapshots`` keyed by ``chat`` / ``completions`` /
  ``premium_interactions``; ``await client.list_models()`` (wire
  ``models.list``, cached per connection) returns ``ModelInfo`` with ``id``,
  ``name``, ``capabilities``, ``policy`` and ``billing``.
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
    "SEND_TIMEOUT_SECONDS",
    "TEXT_ONLY_TOOL_NAME",
    "available_tools_for",
    "answer_text",
    "system_message_for",
]

#: A QUILL-owned tool name that matches no Copilot built-in. Listing it alone
#: is how a text-only session says "no vendor tools" without the empty list.
TEXT_ONLY_TOOL_NAME = "quill_text_only"

_REFUSAL = "QUILL applies edits through its own reviewed editor gateway."

#: How long one answer may take. The SDK's own default is 60 seconds, short
#: enough to cut off an ordinary long answer.
SEND_TIMEOUT_SECONDS = 600.0


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
    """``PermissionDecisionReject``, from the public ``copilot.rpc`` namespace.

    It is generated into ``copilot.generated.rpc`` and re-exported by
    ``copilot.rpc``; ``copilot.session`` never exported it.
    """
    from copilot.rpc import PermissionDecisionReject  # type: ignore[import-not-found]

    return PermissionDecisionReject


def system_message_for(system_prompt: str) -> dict[str, str] | None:
    """The ``system_message`` option: QUILL's prompt appended to the CLI's own."""
    text = system_prompt.strip()
    return {"mode": "append", "content": text} if text else None


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
        ``create_session(available_tools=[...], system_message=...,
        on_permission_request=...)``, then ``session.send_and_wait(prompt,
        timeout=...)``. The SDK is imported here, never at module import.
        """
        import asyncio

        import copilot  # type: ignore[import-not-found]

        reject = _reject_class()
        agent_name = self.agent_name

        def _deny_own_tools(request: object, invocation: object) -> object:
            # QUILL owns the editor: every kind (shell, write, read, url, mcp,
            # memory, custom-tool, ...) is refused, never approved.
            return reject(feedback=_REFUSAL)

        def _client_kwargs() -> dict[str, object]:
            cli_path = cli_path_for_launch()  # raises on a bundle that fails the pin
            kwargs: dict[str, object] = {
                "env": copilot_child_env(cli_path),
                # Always explicit stdio: path=None means the SDK's own runtime.
                "connection": copilot.RuntimeConnection.for_stdio(
                    path=str(cli_path) if cli_path is not None else None
                ),
            }
            token = copilot_auth.stored_token(agent_name)
            if token:
                kwargs["github_token"] = token
                kwargs["use_logged_in_user"] = False
            return kwargs

        def invoke(agent: AgentSpec, ctx: AIContext) -> str:
            prompt = f"{ctx.prompt}\n\n{ctx.context_text}".strip()
            session_kwargs: dict[str, object] = {
                "available_tools": available_tools_for(),
                "on_permission_request": _deny_own_tools,
            }
            system_message = system_message_for(agent.system_prompt)
            if system_message is not None:
                session_kwargs["system_message"] = system_message

            async def _run() -> str:
                async with copilot.CopilotClient(**_client_kwargs()) as client:
                    async with await client.create_session(**session_kwargs) as session:
                        try:
                            result = await session.send_and_wait(
                                prompt, timeout=SEND_TIMEOUT_SECONDS
                            )
                        except TimeoutError:
                            # The SDK's timeout only stops waiting; stop the turn too.
                            await session.abort()
                            raise
                        return answer_text(result)

            return asyncio.run(_run())

        return invoke
