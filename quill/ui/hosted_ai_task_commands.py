"""Do a Document Task, shared by QUILL and QUILL Lite (codex.md 6.2, 11 Phase 4a).

A base of :class:`quill.ui.hosted_ai_commands.HostedAiMixin`, like the Choose
Your AI commands, so both editors get the handler the moment they get the rest
and QUILL's adapter keeps having no commands of its own.

**Do a Document Task** (Ctrl+3 in both editors) opens the agent window
(:mod:`quill.ui.agent_window`) on the document. It needs agent tools, which only
My GitHub Copilot and Codex have (codex.md 10A.7), so it is capability-gated
like every AI command (10A.8): the menu row says "(needs Copilot or Codex)"
when the connection in use cannot, and pressing it sends nothing and offers the
switch in one Yes/No.

**The engine is the connection in use**: Copilot's tool harness on this app's
own GitHub sign-in, or Codex given this app's own ChatGPT access token
(:meth:`quill.ui.hosted_ai_copilot_route.CopilotRouteMixin.agent_harness`).
"""

from __future__ import annotations

from typing import Any

__all__ = ["AgentTaskMixin"]

_TASK_WINDOW = "task"


class AgentTaskMixin:
    """The Do a Document Task command, and the editor half of its window."""

    def cmd_ai_task(self) -> None:
        """Open Do a Document Task on this document, when the connection runs tasks."""
        from quill.core.ai.connection_caps import AGENT_TOOLS

        if not self._ai_switched_on():
            return
        if self._ai_safe_mode():
            from quill.core.ai.connection_words import SAFE_MODE_ABOUT

            self._announce(SAFE_MODE_ABOUT)
            return
        if not self._ai_capable(AGENT_TOOLS):
            return  # nothing sent; the switch was offered (codex.md 10A.8)
        service = self._ai_service()
        connection = str(getattr(service, "connection_in_use", "") or "")
        harness = service.agent_harness(connection)
        if harness is None:
            from quill.core.ai.agent_task_words import NO_ENGINE

            self._announce(NO_ENGINE)
            return
        from quill.ui.agent_window import AgentTaskHooks, AgentWindow

        hooks = AgentTaskHooks(
            announce=self._announce,
            connection=connection,
            make_runner=lambda approver, host: self._ai_task_runner(harness, approver, host),
            make_host=self._ai_task_host,
        )
        self._open_ai_window(_TASK_WINDOW, lambda: AgentWindow(self._ai_parent(), hooks))

    # -- the editor half -------------------------------------------------------- #

    def _ai_task_runner(self, harness: Any, approver: Any, host: Any) -> Any:
        """A :class:`DocumentTaskRunner` on *harness*, with the default broker and log."""
        from quill.core.ai.activity_log import ActivityLog
        from quill.core.ai.document_task import DocumentTaskRunner
        from quill.core.ai.permissions import PermissionBroker

        return DocumentTaskRunner(
            harness=harness,
            host=host,
            approver=approver,
            broker=PermissionBroker(),
            activity=ActivityLog(),
        )

    def _ai_task_host(self, bridge: Any, note: Any) -> Any:
        """The document as the task's tools see it (:class:`AgentTaskHost`)."""
        from quill.ui.agent_task_host import AgentTaskHost

        return AgentTaskHost(
            bridge,
            control=self._ai_control,
            parent=self._ai_parent,
            note=note,
            run_command=self._ai_run_command,
            title=self._ai_document_title,
        )

    def _ai_run_command(self, command_id: str) -> None:
        """Run one of the task's allowed commands (``SAFE_TOOL_IDS``) in this editor.

        QUILL runs it through its command registry; QUILL Lite through the
        handler the parity table pairs with that id.
        """
        run = getattr(getattr(self, "commands", None), "run", None)
        if callable(run):
            run(command_id)
            return
        from quill.core.lite.parity import COMMAND_EQUIVALENTS

        for handler, quill_id in COMMAND_EQUIVALENTS.items():
            if quill_id == command_id and callable(getattr(self, handler, None)):
                getattr(self, handler)()
                return
        raise ValueError(f"{command_id} is not a command this editor has.")
