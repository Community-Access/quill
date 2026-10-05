"""Toggle Task Done, shared by QUILL and QUILL Lite (Ctrl+Alt+Enter in both).

Ticks ``- [ ]`` to ``- [x]`` (and back) on the caret's line, or on every task
line in a selection, and says the one thing a listener cannot get by reading:
how many of the list are done. The idea is PlanCake's (Andre of Oire
Software); the logic is :mod:`quill.core.task_lists`; this is the edit.

No confirmation, unlike PlanCake, which is a reader: in an editor the change is
visible, unsaved until you save, and goes through the ordinary undo stack, so
Ctrl+Z takes it back like any typing.
"""

from __future__ import annotations

from quill.core.task_lists import NOT_A_TASK, toggle_tasks
from quill.ui.atomic_edit import replace_as_one_undo
from quill.ui.editor_host import EditorHostMixin

__all__ = ["TaskListCommandsMixin"]


class TaskListCommandsMixin(EditorHostMixin):
    """``cmd_toggle_task_done``. Mixed into both editors."""

    def cmd_toggle_task_done(self) -> None:
        """Ctrl+Alt+Enter: tick or untick the task on this line or in the selection."""
        if self._host_read_only():
            self._host_say("Document is read-only")
            return
        control = self._host_control()
        text = control.GetValue()
        start, end = control.GetSelection()
        caret = control.GetInsertionPoint()
        result = toggle_tasks(text, int(start), int(end))
        if result is None:
            self._host_say(NOT_A_TASK)
            return
        replace_as_one_undo(control, result.start, result.end, result.text)
        if start != end:
            control.SetSelection(start, end)
        else:
            control.SetInsertionPoint(caret)
        self._host_after_edit()
        self._host_say(result.announcement)
