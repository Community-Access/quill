"""The editor, as a document task's tools see it: one host for both editors.

:class:`~quill.core.ai.tool_gateway.SafeEditorToolGateway` reads and changes the
document through an ``EditorHost``. QUILL's older agent path has its own
(:class:`quill.ui.agent_editor_host.MainFrameEditorHost`), built on MainFrame's
private helpers; the agent window (codex.md 5.2, 6.2) needs one that QUILL and
QUILL Lite share, so it is built only on what the shared hosted-AI mixin already
asks of both editors: the document's text control, the window to parent a
dialog to, and a way to run a command.

**Threading.** Tool handlers run on a worker thread; every wx touch here goes
through a :class:`~quill.core.ai.approvals.UiThreadBridge`, which posts to the
UI thread and waits. A Stop releases every waiter with a safe default, so a
worker never hangs behind a closed window.

**Every edit is one Control Z.** Changes go in with
:func:`quill.ui.atomic_edit.replace_as_one_undo`, the mechanism both editors
already use for AI answers.

**Every change is reviewed as text first** (decision 13). ``preview_diff``
opens the existing Review AI Changes window
(:class:`quill.ui.ai_diff_review_dialog.DiffReviewDialog`) on the gateway's
:func:`~quill.core.ai.diff_review.build_diff_review`. Accepting some of the
changes applies exactly those, there and then; the gateway's own apply that
follows is then a no-op for that turn, so nothing is applied twice.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.ai.approvals import UiThreadBridge
from quill.core.ai.diff_review import DiffReview
from quill.ui.atomic_edit import replace_as_one_undo

__all__ = ["AgentTaskHost"]


class AgentTaskHost:
    """An ``EditorHost`` over one text control, safe to call from a worker."""

    def __init__(
        self,
        bridge: UiThreadBridge,
        *,
        control: Callable[[], Any],
        parent: Callable[[], Any],
        note: Callable[[str], None],
        run_command: Callable[[str], None],
        title: Callable[[], str] = lambda: "",
    ) -> None:
        self._bridge = bridge
        self._control = control
        self._parent = parent
        self._note = note
        self._run_command = run_command
        self._title = title
        self._applied_in_preview = False

    @property
    def bridge(self) -> UiThreadBridge:
        """The task's UI bridge, for a tool that must ask on the UI thread."""
        return self._bridge

    # -- reads ------------------------------------------------------------ #

    def _read(self, fn: Callable[[Any], Any], default: Any) -> Any:
        def on_ui() -> Any:
            try:
                return fn(self._control())
            except RuntimeError:  # the document closed under the task
                return default

        return self._bridge.call(on_ui, default=default)

    def get_document(self) -> str:
        return str(self._read(lambda c: c.GetValue(), ""))

    def get_selection(self) -> str:
        def selected(control: Any) -> str:
            start, end = control.GetSelection()
            return str(control.GetValue()[start:end]) if end > start else ""

        return str(self._read(selected, ""))

    def get_outline(self) -> list[str]:
        from quill.core.ai.ask_context import ask_context

        text = self.get_document()
        return list(ask_context(text, "", 0).outline)

    def get_file_type(self) -> str:
        title = str(self._bridge.call(self._title, default=""))
        return title.rsplit(".", 1)[-1].lower() if "." in title else ""

    def get_cursor_position(self) -> tuple[int, int]:
        def where(control: Any) -> tuple[int, int]:
            result = control.PositionToXY(control.GetInsertionPoint())
            if isinstance(result, tuple) and len(result) == 3:
                _ok, column, line = result
            else:
                column, line = result
            return int(line) + 1, int(column) + 1

        value = self._read(where, (0, 0))
        return (int(value[0]), int(value[1]))

    # -- changes ---------------------------------------------------------- #

    def create_undo_checkpoint(self, label: str) -> None:
        """Nothing to do: each change below is already one undo step."""

    def _change(self, fn: Callable[[Any], None]) -> None:
        if self._applied_in_preview:
            self._applied_in_preview = False  # the review already applied it
            return

        def on_ui() -> None:
            fn(self._control())

        self._bridge.call(on_ui, default=None)

    def apply_replacement(self, text: str) -> None:
        def replace(control: Any) -> None:
            start, end = control.GetSelection()
            replace_as_one_undo(control, start, end, text)

        self._change(replace)

    def apply_insert(self, text: str) -> None:
        def insert(control: Any) -> None:
            at = control.GetInsertionPoint()
            replace_as_one_undo(control, at, at, text)

        self._change(insert)

    def apply_document_text(self, text: str) -> None:
        self._change(lambda c: replace_as_one_undo(c, 0, c.GetLastPosition(), text))

    def run_command(self, command_id: str) -> None:
        self._bridge.call(lambda: self._run_command(command_id), default=None)

    # -- asking ------------------------------------------------------------ #

    def confirm(self, message: str) -> bool:
        """Never reached during a task: the gate routes every confirm to the approver."""
        return False

    def preview_diff(self, review: DiffReview) -> bool:
        """Review AI Changes on the proposed text; apply what is accepted, there."""
        self._applied_in_preview = False

        def on_ui() -> bool:
            from quill.ui.ai_diff_review_dialog import DiffReviewDialog

            applied: dict[str, bool] = {"yes": False}

            def accept(text: str) -> None:
                control = self._control()
                if review.original == control.GetValue():
                    start, end = 0, control.GetLastPosition()  # the whole document
                elif not review.original:
                    start = end = control.GetInsertionPoint()  # an insert at the caret
                else:
                    start, end = control.GetSelection()  # a change to the selection
                replace_as_one_undo(control, start, end, text)
                applied["yes"] = True

            DiffReviewDialog(
                self._parent(),
                title="Review AI Changes",
                original_text=review.original,
                revised_text=review.accept_all(),
                on_apply=accept,
                announce=self._note,
            ).show_modal()
            return applied["yes"]

        approved = bool(self._bridge.call(on_ui, default=False))
        self._applied_in_preview = approved
        return approved

    def announce(self, message: str) -> None:
        """A step's outcome goes into the transcript; the summary is what is spoken."""
        self._bridge.call(lambda: self._note(message), default=None)
