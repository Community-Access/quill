"""What every group of Lineups commands shares: the window's parts and small helpers.

The verbs themselves live in :mod:`quill.ui.lineups.commands` (the Lineups and
their items) and :mod:`quill.ui.lineups.commands_play` (arranging and playing).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.lineups import ops
from quill.core.lineups.model import Lineup
from quill.core.lineups.refs import ItemRef
from quill.core.lineups.store import LineupStore


class LineupsCommandBase:
    """Helpers shared by the command mixins. The window supplies the parts."""

    _win: Any
    _wx: Any
    _lineups_host: Any
    _clip: tuple[ItemRef, ...]
    _items: Any
    _show: Any
    _book: Any

    if TYPE_CHECKING:  # provided by the window (``quill.ui.lineups.window``)

        def current_lineup(self) -> Lineup | None: ...
        def selected_refs(self) -> list[ItemRef]: ...
        def focused_ref(self) -> ItemRef | None: ...
        def visible_refs(self) -> list[ItemRef]: ...
        def facts_for(self, ref: ItemRef) -> Any: ...
        def apply(self, operation: ops.Operation) -> ops.Outcome | None: ...
        def reload(self, **kwargs: Any) -> None: ...
        def request_refresh(self, *, speak: bool) -> None: ...
        def lineups_focused(self) -> bool: ...
        def summary_sentence(self) -> str: ...

    # -- helpers -----------------------------------------------------------------------

    def _say(self, text: str) -> None:
        # After the focus move the command just made: said at once, the reader's
        # own focus announcement would cut it off (review M5).
        self._lineups_host.announce_soon(text)

    def _done(self, text: str) -> None:
        self._lineups_host.say_outcome_soon(text)

    def _need_lineup(self) -> Lineup | None:
        lineup = self.current_lineup()
        if lineup is None:
            self._say("No lineup is selected.")
        return lineup

    def _need_items(self) -> tuple[Lineup, list[ItemRef]] | None:
        lineup = self._need_lineup()
        if lineup is None:
            return None
        refs = self.selected_refs() or ([self.focused_ref()] if self.focused_ref() else [])
        refs = [ref for ref in refs if ref is not None]
        if not refs:
            self._say("No item is selected.")
            return None
        return lineup, refs

    def _remember(self, verb: str, subject: str, restores: str, inverse: ops.Operation) -> None:
        store_dir = self._lineups_host.data_dir

        def undo() -> None:
            LineupStore(store_dir).update(inverse)
            from quill.ui.lineups.window import open_window_of

            window = open_window_of(self._lineups_host.app_key)
            if window is not None:
                window._book = window._load_book()
                window._stamp = window._store.stamp()
                window.reload()

        self._lineups_host.remember_undo(verb, subject, restores, undo)

    def _name_of(self, lineup: Lineup, ref: ItemRef) -> str:
        _presence, facts = self.facts_for(ref)
        row = lineup.row_for(ref)
        return (facts.name if facts is not None else "") or (row.name if row is not None else "")


__all__ = ["LineupsCommandBase"]
