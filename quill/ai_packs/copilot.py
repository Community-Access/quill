"""Copilot SDK harness pack (PRD §18.5).

Optional extra ``quill[ai-copilot]`` (PyPI package
``microsoft-copilot-sdk``, import ``copilot``). The SDK's native runtime is
loaded in-process from QUILL's verified ``runtime.node``; a missing runtime is
reported instead of triggering the SDK's automatic download.

Integration note: the Copilot SDK is itself an agent that can edit files and run
shell commands, governed by an ``on_permission_request`` handler. QUILL must own
every edit. Two paths:

- **Text only** (:meth:`CopilotHarness.start_session`, ``_make_invoke``): the
  SDK is offered none of its own tools, every permission request is refused,
  and the session only produces text, which QUILL applies through its
  reviewed Safe Editor Tool Gateway (permission broker + diff preview +
  one-step undo).
- **Family tools** (:meth:`CopilotHarness.start_tool_session`, Phase 4a): the
  session is offered exactly QUILL's family tools as Copilot custom tools,
  each call answered by the :class:`~quill.core.ai.family_tools.FamilyToolRegistry`
  (so the same gateway, broker, log and diff review apply), and a
  ``custom-tool`` request is approved only for those names, only after the
  broker and the approver agree. See :mod:`quill.ai_packs.copilot_tool_session`.

How a session is made, and why (checked against the SDK 2.0.1 source):

- **The answer, not a request id.** ``session.send`` returns a message id and
  does not wait; the pack calls ``send_and_wait(prompt, timeout=...)``, which
  returns the final ``assistant.message`` event (or None). Its default timeout
  is 60 seconds and a timeout does *not* stop the agent, so the pack passes
  :data:`SEND_TIMEOUT_SECONDS` and calls ``session.abort()`` when it expires.
- **The system prompt is appended, not glued on.** It travels as
  ``system_message={"mode": "append", "content": ...}``, keeping the runtime's own
  safety sections; ``"replace"`` would remove them.
- **The token is explicit.** It is read from this app's own Copilot store entry
  (:func:`quill.core.ai.copilot_auth.stored_token`) when the client is made and
  passed as ``github.token`` with ``github.use_logged_in_user=False``. It is
  never placed in the process environment or implicitly borrowed from a CLI
  sign-in.
- **The runtime is local and verified.** The app resolves the pinned
  ``runtime.node`` under ``tools\\copilot`` and sets the SDK's
  ``COPILOT_CLI_PATH`` runtime override. It does not search ``PATH`` or allow
  the SDK to download a runtime at first use.
- **Never an empty tool list.** An empty ``available_tools`` has been seen to
  expose every built-in (Copilot CLI issue #5306), so a text-only session still
  passes a non-empty allowlist that names only QUILL-owned tools -- today a
  single QUILL name that matches no built-in (:data:`TEXT_ONLY_TOOL_NAME`).
  Names must match ``^[a-zA-Z0-9_-]+$``; a bare ``"*"`` is rejected.

SDK 2.0.1 facts recorded for later phases (read from source):

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

import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.ai_packs._base import Invoke, SdkHarness
from quill.core.ai import copilot_auth
from quill.core.ai.agent_workdir import AgentFolders, agent_folders
from quill.core.ai.copilot_runtime import (
    prepare_inprocess_runtime,
    resolve_runtime_path,
)
from quill.core.ai.harness import AgentSpec, AIContext, HarnessCapabilities, TurnUsage
from quill.stability.safe_mode import should_enable_safe_mode

if TYPE_CHECKING:
    from quill.ai_packs.copilot_tool_session import SdkParts
    from quill.core.ai.approvals import Approver
    from quill.core.ai.copilot_byok import CopilotByokConnection
    from quill.core.ai.family_tools import FamilyToolRegistry
    from quill.core.ai.harness import ToolSession
    from quill.core.ai.tool_gateway import Emit

__all__ = [
    "CopilotHarness",
    "SEND_TIMEOUT_SECONDS",
    "TEXT_ONLY_TOOL_NAME",
    "available_tools_for",
    "answer_text",
    "client_kwargs",
    "session_safety_options",
    "reject_class",
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


class CopilotNoReplyError(RuntimeError):
    """The session went idle without an assistant message, or with an empty one."""


def _reject_class() -> Any:
    """``PermissionDecisionReject``, from the public ``copilot.rpc`` namespace.

    It is generated into ``copilot.generated.rpc`` and re-exported by
    ``copilot.rpc``; ``copilot.session`` never exported it.
    """
    from copilot.rpc import PermissionDecisionReject  # type: ignore[import-not-found]

    return PermissionDecisionReject


def _client_kwargs(copilot: Any, agent_name: str, base_directory: str) -> dict[str, Any]:
    """Create an isolated in-process client using only this app's stored token."""
    prepare_inprocess_runtime()
    github: dict[str, object] = {"use_logged_in_user": False}
    token = copilot_auth.stored_token(agent_name)
    if token:
        github["token"] = token
    return {
        "mode": "empty",
        "runtime": copilot.RuntimeConnection.for_inprocess(base_directory=base_directory),
        "github": github,
    }


def session_safety_options() -> dict[str, Any]:
    """Privacy defaults shared by text and tool sessions."""
    return {
        "enable_config_discovery": False,
        "github": {"capi": {"enabled": True}, "telemetry_enabled": False},
        "skills": {"enabled": False},
        "state": {
            "embedding_cache_storage": "in-memory",
            "enable_cross_session_store": False,
            "infinite_sessions": {"enabled": False},
            "memory": {"enabled": False},
        },
    }


def _sdk_parts() -> SdkParts:
    """The SDK classes a tool session needs (imports the SDK; call lazily)."""
    from copilot.rpc import PermissionDecisionApproveOnce  # type: ignore[import-not-found]
    from copilot.tools import (  # type: ignore[import-not-found]
        Tool,
        ToolBinaryResult,
        ToolResult,
    )

    from quill.ai_packs.copilot_tool_session import SdkParts

    return SdkParts(
        tool_cls=Tool,
        result_cls=ToolResult,
        binary_cls=ToolBinaryResult,
        reject_cls=_reject_class(),
        approve_cls=PermissionDecisionApproveOnce,
    )


#: Public names for the hosted-AI route (:mod:`quill.core.ai.copilot_chat`),
#: which makes its clients exactly the way this pack does.
client_kwargs = _client_kwargs
reject_class = _reject_class


def system_message_for(system_prompt: str) -> dict[str, str] | None:
    """The ``system_message`` option: QUILL's prompt appended to the runtime's."""
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
        data_dir: Path | None = None,
    ) -> None:
        super().__init__(invoke)
        self.agent_name = agent_name
        self.data_dir = data_dir

    def _agent_folders(self) -> AgentFolders:
        base = self.data_dir / "ai" if self.data_dir is not None else None
        return agent_folders("copilot", self.agent_name, base=base)

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
            app_tools=True,
            images=True,  # a tool may return a picture (G6, binary_results_for_llm)
        )

    def _tool_client(self, folders: AgentFolders) -> Any:
        """A ``CopilotClient`` for one tool task (not yet started).

        Its state (``COPILOT_HOME``) sits in this app's folders, emptied after
        the task. The session gets its working directory separately.
        """
        import copilot  # type: ignore[import-not-found]

        return copilot.CopilotClient(**self._client_options(copilot, str(folders.home)))

    def _client_options(self, copilot: Any, base_directory: str) -> dict[str, Any]:
        return _client_kwargs(copilot, self.agent_name, base_directory)

    def _session_provider_options(self, model: str = "") -> dict[str, Any]:
        return {"model": model} if model else {}

    def is_available(self) -> tuple[bool, str | None]:
        """Report a missing SDK or runtime without trying to download either."""
        available, reason = super().is_available()
        if not available:
            return available, reason
        try:
            if resolve_runtime_path() is None:
                return False, "The in-process Copilot runtime is not installed with this build."
        except OSError:
            return False, "The in-process Copilot runtime could not be read."
        return True, None

    def start_tool_session(
        self,
        agent: AgentSpec,
        ctx: AIContext,
        tools: FamilyToolRegistry,
        approver: Approver,
        emit: Emit,
        *,
        keep_open: bool = False,
        on_usage: Callable[[TurnUsage], None] | None = None,
        model: str | None = None,
        folders: AgentFolders | None = None,
    ) -> ToolSession:
        """A multi-turn session over QUILL's family tools (codex.md 5.2).

        Refused (an error result, never a launch) in Safe Mode (G4) or when the
        SDK pack or native runtime is not installed. ``keep_open`` keeps the task alive for
        follow-ups until ``end()``; ``on_usage`` receives token counts per call.
        """
        from quill.ai_packs.copilot_tool_session import CopilotToolSession, RefusedToolSession

        if should_enable_safe_mode(sys.argv, os.environ):
            return RefusedToolSession("Safe Mode is on, so AI agents are off.", emit)
        available, reason = self.is_available()
        if not available:
            return RefusedToolSession(reason or "GitHub Copilot is not available.", emit)
        options: dict[str, Any] = {}
        options.update(self._session_provider_options(model or ""))
        return CopilotToolSession(
            agent=agent,
            ctx=ctx,
            tools=tools,
            approver=approver,
            emit=emit,
            sdk=_sdk_parts(),
            client_factory=self._tool_client,
            folders=folders or self._agent_folders(),
            session_options=options,
            keep_open=keep_open,
            on_usage=on_usage,
            display_name=self.display_name,
        )

    def _make_invoke(self) -> Invoke:
        """Transport over the SDK's async session API; imports stay lazy."""
        import asyncio

        reject = _reject_class()

        def _deny_own_tools(request: object, invocation: object) -> object:
            # QUILL owns the editor: every kind (shell, write, read, url, mcp,
            # memory, custom-tool, ...) is refused, never approved.
            return reject(feedback=_REFUSAL)

        def invoke(agent: AgentSpec, ctx: AIContext) -> str:
            prompt = f"{ctx.prompt}\n\n{ctx.context_text}".strip()
            session_kwargs: dict[str, Any] = session_safety_options()
            session_kwargs["permissions"] = {"on_request": _deny_own_tools}
            session_kwargs["tools"] = {"available_tools": available_tools_for()}
            session_kwargs["events"] = {"streaming": False}
            session_kwargs.update(self._session_provider_options())
            system_message = system_message_for(agent.system_prompt)
            if system_message is not None:
                session_kwargs["system_message"] = system_message

            async def _run() -> str:
                folders = self._agent_folders().prepare()
                client: Any | None = None
                try:
                    client = self._tool_client(folders)
                    await client.start()
                    session = await client.create_session(
                        **session_kwargs, working_directory=str(folders.work)
                    )
                    try:
                        result = await session.send_and_wait(prompt, timeout=SEND_TIMEOUT_SECONDS)
                    except TimeoutError:
                        await session.abort()
                        raise
                    finally:
                        await session.disconnect()
                    text = answer_text(result)
                    if not text.strip():
                        raise CopilotNoReplyError(
                            "GitHub Copilot finished without an answer. Try again."
                        )
                    return text
                finally:
                    try:
                        if client is not None:
                            await client.stop()
                    finally:
                        folders.clear()

            return asyncio.run(_run())

        return invoke


class CopilotByokHarness(CopilotHarness):
    """Copilot SDK agent tools using only the user's explicitly selected provider."""

    pack_id = "copilot_byok"
    pack_name = "Copilot SDK (your provider)"

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        agent_name: str = copilot_auth.DEFAULT_AGENT_NAME,
        data_dir: Path | None = None,
    ) -> None:
        super().__init__(agent_name=agent_name, data_dir=data_dir)
        from quill.core.ai.copilot_byok import load_selected_connection

        self._connection: CopilotByokConnection | None
        try:
            self._connection = load_selected_connection(provider, model)
            self._connection_error = ""
        except (OSError, ValueError) as exc:
            self._connection = None
            self._connection_error = str(exc)

    def capabilities(self) -> HarnessCapabilities:
        base = super().capabilities()
        local = bool(self._connection and self._connection.local_only)
        return replace(
            base,
            requires_oauth=False,
            requires_api_key=not local,
            local_only=local,
        )

    def is_available(self) -> tuple[bool, str | None]:
        available, reason = super().is_available()
        if not available:
            return available, reason
        if self._connection is None:
            return False, self._connection_error or "The selected provider is not ready."
        return True, None

    def _client_options(self, copilot: Any, base_directory: str) -> dict[str, Any]:
        prepare_inprocess_runtime()
        return {
            "mode": "empty",
            "runtime": copilot.RuntimeConnection.for_inprocess(base_directory=base_directory),
            "github": {"use_logged_in_user": False},
        }

    def _session_provider_options(self, model: str = "") -> dict[str, Any]:
        if self._connection is None:
            return {}
        return {
            "github": {"capi": {"enabled": False}, "telemetry_enabled": False},
            "inference": self._connection.inference_options(),
            "model": model or self._connection.model,
        }
