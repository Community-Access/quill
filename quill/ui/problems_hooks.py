"""The hooks each editor supplies to the shared problem commands.

:class:`quill.ui.problems_commands.ProblemsCommandsMixin` is the commands;
these are its defaults, one method per thing it asks the editor, split out of
it on 2026-11-09 to keep it under the module size budget (GATE-11). QUILL's
``quill/ui/main_frame_code_nav.py`` and QUILL Lite's
``quill/apps/lite_window_code_nav.py`` override them.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.problems.pane import OpenProblemDocument

if TYPE_CHECKING:
    from quill.ui.problems_pane import ProblemsPane

__all__ = ["ProblemsHooksMixin"]


class ProblemsHooksMixin:
    """The defaults: what an editor that supplies nothing gets."""

    def _problems_text(self) -> str:
        raise NotImplementedError

    def _problems_caret(self) -> int:
        raise NotImplementedError

    def _problems_language(self) -> str:
        """A :func:`quill.core.problems.language_key`."""
        raise NotImplementedError

    def _problems_path(self) -> Path | None:
        raise NotImplementedError

    def _problems_modified(self) -> bool:
        return True

    def _problems_change_token(self) -> object:
        """Something cheap that changes whenever the text does, or ``None``.

        The pane's timer compares it twice a second instead of copying the
        text out of the control. ``None`` means the host has nothing cheaper,
        and the text itself is compared.
        """
        return None

    def _problems_window_alive(self) -> bool:
        """False once this window has closed: late background results are dropped."""
        return True

    def _problems_is_active(self) -> bool:
        """True when this is the window in front, the only one a quiet check speaks in."""
        return True

    def _problems_outside_allowed(self) -> bool:
        return False

    def _problems_go_to(self, offset: int) -> None:
        raise NotImplementedError

    def _problems_say(self, message: str) -> None:
        raise NotImplementedError

    def _problems_choose(
        self, summary: str, rows: list[str], *, title: str = "Problems"
    ) -> int | None:
        """Show the Problems list (or, titled "Quick Fix", the fixes for one).

        The index chosen, or ``None`` on Escape.
        """
        raise NotImplementedError

    def _problems_in_background(self, work: Callable[[], Any], done: Callable[[Any], None]) -> None:
        done(work())

    def _problems_can_check(self) -> bool:
        """False where this document has nothing a checker reads."""
        return True

    def _problems_all_files_setting(self) -> bool:
        """``problems_all_open_files``: the default, set in Settings or Preferences."""
        return False

    def _problems_mark_all_files(self, all_files: bool) -> None:
        """Check the View > Problems row that matches; nothing is saved."""

    def _problems_replace(self, start: int, end: int, text: str) -> None:
        """Replace ``[start, end)`` of the document with *text* as one undo step."""
        raise NotImplementedError

    def _problems_open_documents(self) -> list[OpenProblemDocument]:
        """Every open document, for the pane's All open files; [] means just this one."""
        return []

    def _problems_document_key(self) -> object:
        """This document's key among :meth:`_problems_open_documents`."""
        return None

    def _problems_go_to_document(self, key: object, line: int, column: int) -> None:
        """Bring another open document forward with its caret at *line*, *column*."""

    def _problems_pause_enabled(self) -> bool:
        """Check After a Pause: the ``problems_check_after_pause`` setting."""
        return False

    def _problems_set_pause_enabled(self, enabled: bool) -> None:
        """The pane's check box: remember the choice."""

    def _problems_pane(self, *, create: bool) -> ProblemsPane | None:
        """The docked pane; built (hidden) on first use when *create*."""
        return None

    def _problems_pane_set_shown(self, shown: bool) -> None:
        """Show or hide the pane, lay the window out, remember the choice."""
        raise NotImplementedError

    def _problems_back_to_editor(self) -> None:
        """Escape in the pane: focus to the text, the caret where it was."""
        raise NotImplementedError

    def _problems_copy(self, text: str) -> None:
        raise NotImplementedError
