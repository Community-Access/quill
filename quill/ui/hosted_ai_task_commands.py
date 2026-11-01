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
        self._open_document_task()

    def cmd_ai_alt_text(self) -> None:
        """Propose Alt Text: Do a Document Task with the alt-text request filled in.

        codex.md 6.4 and 10B.5: the document's own images, the one picture
        feature the editors keep (decision 13). Each proposal is set through
        Review AI Changes, one image at a time, and is one Control Z.
        """
        from quill.core.ai.doc_images import ALT_TEXT_INSTRUCTION

        self._open_document_task(starter=ALT_TEXT_INSTRUCTION)

    def _ai_task_engine(self) -> tuple[str, Any] | None:
        """``(connection, harness)`` when an agent task may start here, else None.

        Behind the switch, Safe Mode and the capability gate: nothing is sent,
        and the switch is offered, when the connection cannot run tasks
        (codex.md 10A.8).
        """
        from quill.core.ai.connection_caps import AGENT_TOOLS

        if not self._ai_switched_on():
            return None
        if self._ai_safe_mode():
            from quill.core.ai.connection_words import SAFE_MODE_ABOUT

            self._announce(SAFE_MODE_ABOUT)
            return None
        if not self._ai_capable(AGENT_TOOLS):
            return None  # nothing sent; the switch was offered (codex.md 10A.8)
        service = self._ai_service()
        connection = str(getattr(service, "connection_in_use", "") or "")
        harness = service.agent_harness(connection)
        if harness is None:
            from quill.core.ai.agent_task_words import no_engine

            self._announce(no_engine(str(getattr(self._ai_host(), "ai_choose_key", "") or "")))
            return None
        return connection, harness

    def _open_document_task(self, starter: str = "") -> None:
        engine = self._ai_task_engine()
        if engine is None:
            return
        connection, harness = engine
        from quill.ui.agent_window import AgentTaskHooks, AgentWindow

        hooks = AgentTaskHooks(
            announce=self._announce,
            connection=connection,
            make_runner=lambda approver, host: self._ai_task_runner(harness, approver, host),
            make_host=self._ai_task_host,
            starter=starter,
        )
        self._open_ai_window(_TASK_WINDOW, lambda: AgentWindow(self._ai_parent(), hooks))

    def _open_app_task(
        self,
        spec: Any,
        tools: Any,
        *,
        instruction_help: str,
        starter: str = "",
        context: Any = None,
    ) -> None:
        """Open an app's agent task (codex.md Phase 4c) in the shared agent window.

        *spec* is an :class:`~quill.core.ai.app_task.AppTaskSpec`; *tools* is
        ``(AppTaskContext) -> list[FamilyTool]``, called afresh for each task;
        *context* is ``() -> str``, the facts sent with the first instruction.
        """
        engine = self._ai_task_engine()
        if engine is None:
            return
        connection, harness = engine
        from quill.core.ai.app_task import AppTaskRunner
        from quill.ui.agent_window import AgentTaskHooks, AgentWindow
        from quill.ui.app_agent_task import AppTaskContext

        hooks = AgentTaskHooks(
            announce=self._announce,
            connection=connection,
            make_runner=lambda approver, ctx: AppTaskRunner(
                harness=harness,
                approver=approver,
                spec=spec,
                tools=lambda: tools(ctx),
                context=context,
            ),
            make_host=lambda bridge, note: AppTaskContext(bridge, note, self._ai_parent),
            title=spec.title,
            instruction_help=instruction_help,
            starter=starter,
        )
        name = f"{_TASK_WINDOW}:{spec.agent_id}"
        self._open_ai_window(name, lambda: AgentWindow(self._ai_parent(), hooks))

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
            pictures=self._ai_doc_pictures(getattr(host, "bridge", None)),
        )

    def _ai_document_path(self) -> Any:
        """The open document's file, for images named relative to it; None if unsaved."""
        from pathlib import Path

        document = getattr(self, "document", None)  # QUILL
        path = getattr(document, "path", None) if document is not None else None
        if path is None:
            path = getattr(self, "path", None)  # QUILL Lite
        return Path(str(path)) if path else None

    def _ai_doc_pictures(self, bridge: Any) -> Any:
        """The picture loader for ``doc.image``, when the connection in use sees.

        Runs on the task's worker: the 10B.4 consent is asked on the UI thread
        through *bridge*, the picture is read from this computer only (a web
        address is never fetched) and fitted to the connection before it goes.
        """
        from quill.core.ai.connection_caps import PICTURES

        service = self._ai_service()
        can_do = getattr(service, "can_do", None)
        if bridge is None or not callable(can_do) or not can_do(PICTURES):
            return None
        connection = str(getattr(service, "connection_in_use", "") or "")
        document_path = self._ai_document_path()

        def load(image: Any) -> Any:
            from quill.core.ai.doc_images import resolve_image_source
            from quill.core.ai.family_tools import ToolImage
            from quill.core.ai.picture_prep import PicturePrepError, fit_image, longest_side_for
            from quill.ui.hosted_ai_picture_consent import ask_picture_consent

            found = resolve_image_source(image.source, document_path)
            if found is None:
                return (
                    f"Image {image.number}, {image.name}, is not on this computer, so it "
                    "cannot be looked at. Propose alt text from the words around it, "
                    "and say that you could not see it."
                )
            if not bridge.call(lambda: ask_picture_consent(self, connection), default=False):
                return "The person has not agreed to send pictures on this connection."
            try:
                data = found if isinstance(found, bytes) else found.read_bytes()
                prepared = fit_image(data, longest_side_for(connection))
            except (OSError, PicturePrepError) as error:
                return f"Image {image.number} could not be read: {error}"
            return ToolImage(
                prepared.data, prepared.mime, description=f"Image {image.number}, {image.name}."
            )

        return load

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
