"""QUILL Lite's Activity and Repeat Last Result (qc.md F-10).

The window and the model are the family's (:mod:`quill.ui.activity_window`,
:mod:`quill.core.activity`): the same two keys as QUILL and every other app,
F9 and Shift+F9, and the same rows. QUILL Lite's windows share one log, so a
settings write that failed while you were in another document is in every
window's Activity.
"""

from __future__ import annotations

from quill.ui.activity_window import repeat_last_result, show_activity


class DocumentActivityMixin:
    """Help > Activity... and Help > Repeat Last Result for a document window."""

    def cmd_activity(self) -> None:
        """Shift+F9: this session's results, each with what can be done about it."""
        show_activity(self)

    def cmd_repeat_last_result(self) -> None:
        """F9: say the newest important result again."""
        repeat_last_result(self)


__all__ = ["DocumentActivityMixin"]
