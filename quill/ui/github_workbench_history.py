"""Change History and Undo GitHub Change in the GitHub Workbench (GitHub PRD 16.5, 18.5).

Split out of :mod:`quill.ui.github_workbench_properties` (GATE-11). Every
proven change is a row in :class:`quill.core.github.change_log.ChangeLog`;
Edit > Undo GitHub Change (Ctrl+Z in the list) reverses the newest one GitHub
allows, Redo (Ctrl+Y) makes it again, and Change History's own Undo reverses
any row. In a text box, Ctrl+Z and Ctrl+Y undo and redo the typing instead.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.github.sheet_catalog import SHEETS, Target
from quill.core.github.sheet_engine import SaveOutcome, inverse, sentence
from quill.core.workbench.properties import FieldChange

__all__ = ["GitHubWorkbenchHistoryMixin"]


class GitHubWorkbenchHistoryMixin:
    """History, Undo and Redo for the GitHub provider."""

    frame: Any
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]

    def github_api(self) -> Any:
        raise NotImplementedError

    def account_name(self) -> str:
        raise NotImplementedError

    def tier_of(self, target: Target, changes: Sequence[FieldChange]) -> Any:
        raise NotImplementedError

    # -- history and undo ------------------------------------------------------------

    def change_log(self) -> Any:
        from quill.core.github.change_log import ChangeLog

        if getattr(self, "_change_log", None) is None:
            self._change_log = ChangeLog.load()
        return self._change_log

    def record_change(
        self, target: Target, done: Sequence[FieldChange], said: str, confirmed: bool
    ) -> None:
        """One Change History row, naming the object where the save left it (renamed or not)."""
        back, cannot = inverse(target.sheet, done)
        try:
            self.change_log().record(
                account=self.account_name(),
                kind=target.kind,
                ident=target.sheet.ident_after(target.ident, done),
                target=target.sheet.title(target.ident) or target.kind,
                summary=said,
                changes=done,
                tier=int(self.tier_of(target, done)),
                confirmed=confirmed,
                can_undo=bool(back) and not cannot,
            )
        except OSError:
            pass  # a history that cannot be written must not undo the save itself

    def undo_entry(self, index: int) -> None:
        """Reverse one Change History row, where GitHub allows it (16.5).

        The object is read fresh and the pickers' choices loaded first
        (:func:`quill.core.github.sheet_replay.undo`), so a milestone goes back
        as its number and a ruleset is rebuilt from what it is now.
        """
        from quill.core.github.sheet_replay import undo, undo_refusal

        log = self.change_log()
        if not 0 <= index < len(log.entries):
            self._say("Nothing to undo.")
            return
        entry = log.entries[index]
        sheet = SHEETS.get(entry.kind)
        if entry.undone:
            self._say(f"{entry.summary} is already undone.")
            return
        why = undo_refusal(sheet, entry.as_changes()) if sheet is not None else ""
        if sheet is None or not entry.can_undo or why:
            self._say(why or f"{entry.summary} cannot be undone.")
            return
        api = self.github_api()

        def done(outcome: SaveOutcome) -> None:
            if outcome.conflicts:
                self._say(sentence(entry.target, outcome) + " Undo needs the newer value back.")
                return
            log.mark_undone(index)
            self._undone_stack().append(index)
            self._say("Undone. " + sentence(entry.target, outcome))
            if self.frame is not None:
                self.frame.reload()

        self._background(
            "undo the change", lambda: undo(api, sheet, entry.ident, entry.as_changes()), done
        )

    def _text_box_undo(self, verb: str) -> bool:
        frame = self.frame
        if frame is None:
            return False
        focused = frame._wx.Window.FindFocus()
        if isinstance(focused, frame._wx.TextCtrl):
            getattr(focused, verb)()
            return True
        return False

    def _undone_stack(self) -> list[int]:
        if getattr(self, "_undone", None) is None:
            self._undone: list[int] = []
        return self._undone

    def _do_undo_change(self, _ref: Any, _row: object) -> None:
        """Ctrl+Z: a text box undoes its own typing; anywhere else, the last GitHub change."""
        if self._text_box_undo("Undo"):
            return
        index = self.change_log().newest_undoable(self.account_name())
        if index < 0:
            self._say("Nothing to undo.")
            return
        self.undo_entry(index)

    def _do_redo_change(self, _ref: Any, _row: object) -> None:
        """Ctrl+Y: make the change Undo last reversed again, and it can be undone again."""
        from quill.core.github.sheet_replay import redo

        if self._text_box_undo("Redo"):
            return
        stack = self._undone_stack()
        log = self.change_log()
        if not stack or not 0 <= stack[-1] < len(log.entries):
            self._say("Nothing to redo.")
            return
        index = stack.pop()
        entry = log.entries[index]
        sheet = SHEETS.get(entry.kind)
        if sheet is None:
            self._say("Nothing to redo.")
            return
        api = self.github_api()

        def done(outcome: SaveOutcome) -> None:
            if outcome.conflicts:
                stack.append(index)
                self._say(sentence(entry.target, outcome) + " Redo needs the older value back.")
                return
            if outcome.done:
                log.mark_undone(index, False)
            self._say("Redone. " + sentence(entry.target, outcome))
            if self.frame is not None:
                self.frame.reload()

        self._background(
            "redo the change", lambda: redo(api, sheet, entry.ident, entry.as_changes()), done
        )
