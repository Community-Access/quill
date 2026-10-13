"""Arranging and playing in the Lineups window: ``cmd_move_*`` and ``cmd_play*``.

Moves are computed on the rows as shown (``local_media_edit.move_by`` and
``move_to``, the same arithmetic Local Media uses) and applied by reference, so a
move in a filtered view lands where the listener heard it land. The new
position is said; the row is not -- the screen reader reads the row.

Playing goes to the app (:class:`~quill.ui.lineups.host.LineupsHost`): Radio
plays every kind; Cast plays episodes and hands the rest to Radio.
"""

from __future__ import annotations

from collections.abc import Sequence

from quill.core.lineups import ops
from quill.core.lineups.describe import rule_sentence
from quill.core.lineups.merge import budget_cut
from quill.core.lineups.model import Lineup
from quill.core.lineups.refs import ItemRef
from quill.core.radio.local_media_edit import move_by, move_to, moved_sentence
from quill.ui.lineups import dialogs
from quill.ui.lineups.commands_base import LineupsCommandBase


class LineupsArrangePlayMixin(LineupsCommandBase):
    """Moves, playing, and the summary."""

    # -- arranging -------------------------------------------------------------------------

    def cmd_move_up(self) -> None:
        self._move("up")

    def cmd_move_down(self) -> None:
        self._move("down")

    def cmd_move_top(self) -> None:
        self._move("top")

    def cmd_move_bottom(self) -> None:
        self._move("bottom")

    def cmd_move_to(self) -> None:
        visible = self.visible_refs()
        if self.lineups_focused():
            lineup = self._need_lineup()
            if lineup is None:
                return
            count = len(self._book.lineups)
            number = dialogs.ask_number(
                self._lineups_host,
                self._win,
                f"Move to position, 1 to {count}:",
                "Move to Position",
                value=[item.id for item in self._book.lineups].index(lineup.id) + 1,
                low=1,
                high=max(1, count),
            )
            if number is not None:
                self._move_lineup(lineup, to=number - 1)
            return
        if not visible:
            return
        number = dialogs.ask_number(
            self._lineups_host,
            self._win,
            f"Move to position, 1 to {len(visible)}:",
            "Move to Position",
            value=(visible.index(self.focused_ref()) + 1) if self.focused_ref() in visible else 1,
            low=1,
            high=len(visible),
        )
        if number is not None:
            self._move("to", position=number - 1)

    def _move_lineup(self, lineup: Lineup, *, delta: int = 0, to: int | None = None) -> None:
        ids = [item.id for item in self._book.lineups]
        before = ids.index(lineup.id)
        if self.apply(ops.move_lineup(lineup.id, delta=delta, to=to)) is None:
            return
        after = [item.id for item in self._book.lineups].index(lineup.id)
        self.reload(select_lineup=lineup.id, focus="lineups")
        if after == before:
            self._say("Already at the top." if after == 0 else "Already at the end.")
        else:
            self._say(moved_sentence([after], len(ids)))

    def _move(self, how: str, *, position: int = 0) -> None:
        if self.lineups_focused():
            lineup = self._need_lineup()
            if lineup is not None:
                deltas = {"up": -1, "down": 1, "top": -10_000, "bottom": 10_000}
                self._move_lineup(lineup, delta=deltas.get(how, 0))
            return
        found = self._need_items()
        if found is None:
            return
        lineup, refs = found
        visible = self.visible_refs()
        rows = sorted(visible.index(ref) for ref in refs if ref in visible)
        if how in ("up", "down"):
            arranged, new_rows = move_by(visible, rows, -1 if how == "up" else 1)
        else:
            target = {"top": 0, "bottom": len(visible)}.get(how, position)
            arranged, new_rows = move_to(visible, rows, target)
        if new_rows == rows:
            self._say("Already at the top." if not rows or rows[0] == 0 else "Already at the end.")
            return
        block = arranged[new_rows[0] : new_rows[-1] + 1]
        order = [row.ref for row in lineup.rows]
        anchor: ItemRef | None = arranged[new_rows[0] - 1] if new_rows[0] > 0 else None
        if anchor is None and len(visible) != len(order):
            # Filtered: before the first visible row is just after whatever
            # hidden row precedes it in the whole lineup (or the very top).
            rest = [ref for ref in order if ref not in block]
            first = next((ref for ref in arranged if ref not in block), None)
            index = rest.index(first) if first in rest else 0
            anchor = rest[index - 1] if index > 0 else None
        outcome = self.apply(ops.move_rows(lineup.id, block, after=anchor, to_top=anchor is None))
        if outcome is None or outcome.stale:
            self._say("The lineup changed while you were moving; try again.")
            self.reload()
            return
        self._remember("Move", lineup.name, "the order it had", ops.restore_order(lineup.id, order))
        self.reload(select=block)
        self._say_position(block)

    def _say_position(self, block: Sequence[ItemRef]) -> None:
        visible = self.visible_refs()
        rows = [visible.index(ref) for ref in block if ref in visible]
        sentence = moved_sentence(rows, len(visible))
        filtered = self._show.GetSelection() > 0
        if filtered and sentence:
            sentence = sentence.rstrip(".") + " shown."
        self._say(sentence)

    # -- playing ----------------------------------------------------------------------------

    def _playable(
        self, lineup: Lineup, refs: Sequence[ItemRef], start: int
    ) -> tuple[list[ItemRef], int]:
        """*refs* without what a play-through leaves out: the budget, live items if asked."""
        lengths = {}
        for ref in refs:
            _presence, facts = self.facts_for(ref)
            lengths[ref] = facts.length_seconds if facts is not None else 0
        cut = budget_cut(lineup, lengths)
        chosen = refs[start] if 0 <= start < len(refs) else None
        kept = []
        for ref in refs:
            _presence, facts = self.facts_for(ref)
            if ref != chosen and (
                ref in cut or (lineup.skip_live and facts is not None and facts.live)
            ):
                continue
            kept.append(ref)
        return kept, kept.index(chosen) if chosen in kept else 0

    def cmd_play(self) -> None:
        lineup = self._need_lineup()
        ref = self.focused_ref()
        if lineup is None:
            return
        if ref is None:
            self.cmd_play_all()
            return
        visible = self.visible_refs()
        refs, start = self._playable(lineup, visible, visible.index(ref))
        self._play(lineup, refs, start)

    def cmd_play_all(self) -> None:
        lineup = self._need_lineup()
        if lineup is None:
            return
        if not lineup.rows:
            self._say(f"{lineup.name} is empty.")
            return
        refs, start = self._playable(lineup, [row.ref for row in lineup.rows], 0)
        self._play(lineup, refs, start)

    def _play(self, lineup: Lineup, refs: Sequence[ItemRef], start: int) -> None:
        facts = [self.facts_for(ref)[1] for ref in refs]
        message = self._lineups_host.play(lineup, refs, start, facts)
        if message:
            self._say(message)

    def cmd_play_next(self) -> None:
        self._queue(at_end=False)

    def cmd_up_next(self) -> None:
        self._queue(at_end=True)

    def _queue(self, *, at_end: bool) -> None:
        found = self._need_items()
        if found is None:
            return
        _lineup, refs = found
        message = self._lineups_host.play_next(
            refs, [self.facts_for(ref)[1] for ref in refs], at_end=at_end
        )
        if message:
            self._done(message)

    def cmd_pause(self) -> None:
        self._lineups_host.pause()

    def cmd_next(self) -> None:
        message = self._lineups_host.step(1)
        if message:
            self._say(message)

    def cmd_previous(self) -> None:
        message = self._lineups_host.step(-1)
        if message:
            self._say(message)

    def cmd_stop_after(self) -> None:
        message = self._lineups_host.stop_after_current()
        if message:
            self._done(message)

    def cmd_skip_live(self) -> None:
        lineup = self._need_lineup()
        if lineup is None:
            return
        on = not lineup.skip_live
        if self.apply(ops.set_settings(lineup.id, skip_live=on)) is not None:
            self.reload()
            self._done(
                "Live items are left out when the lineup plays through."
                if on
                else "Live items play too."
            )

    def cmd_summary(self) -> None:
        lineup = self.current_lineup()
        if lineup is not None and lineup.rules:
            sentences = " ".join(
                f"Rule {n}: {rule_sentence(rule)}" for n, rule in enumerate(lineup.rules, 1)
            )
            self._say(f"{self.summary_sentence()} {sentences}")
            return
        self._say(self.summary_sentence())


__all__ = ["LineupsArrangePlayMixin"]
