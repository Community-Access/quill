"""Every verb of the Lineups window, as ``cmd_<verb>`` methods on the window.

Each edit is one operation on the shared file (``quill.core.lineups.ops``), named
by references, and each that can be undone leaves its inverse with the app's
ten-step Undo. What is said follows the house rules: the new position after a
move, never the row text; counts and failures always; nothing the screen reader
already says.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from quill.core.lineups import ops
from quill.core.lineups.describe import count_text, list_sentence, why_text
from quill.core.lineups.examples import examples
from quill.core.lineups.model import HELD_KEPT, Lineup, Row
from quill.core.lineups.refs import ItemRef, Presence
from quill.core.lineups.rules import Rule, new_rule_id
from quill.ui.lineups import dialogs
from quill.ui.lineups.commands_base import LineupsCommandBase

#: The format of an exported rules file, so a newer one can be told apart.
RULES_FILE_VERSION = 1


class LineupsCommandsMixin(LineupsCommandBase):
    """The Lineups themselves, and editing their items."""

    # -- the Lineups themselves --------------------------------------------------------

    def cmd_new_lineup(self) -> None:
        name = dialogs.ask_text(
            self._lineups_host, self._win, "Name for the new lineup:", "New Lineup"
        )
        if not name:
            return
        outcome = self.apply(ops.create_lineup(name))
        if outcome is None:
            return
        self.reload(select_lineup=outcome.lineup_id, focus="lineups")
        self._done(
            f"Made {name}. Add to Lineup in any list fills it; Edit Rules, Ctrl+Alt+R, "
            "gives it rules."
        )

    def cmd_new_example(self) -> None:
        starters = examples()
        index = dialogs.choose(
            self._lineups_host,
            self._win,
            "Choose a lineup to start from. Its rules become yours to change.",
            "New from an Example",
            [f"{example.name}: {example.summary}" for example in starters],
        )
        if index is None:
            return
        chosen = starters[index]
        outcome = self.apply(ops.create_lineup(chosen.name, rules=chosen.rules))
        if outcome is None:
            return
        self.reload(select_lineup=outcome.lineup_id, focus="lineups")
        self._done(f"Made {chosen.name}. Its rules are running now.")
        self.request_refresh(speak=False)

    def cmd_duplicate(self) -> None:
        lineup = self._need_lineup()
        if lineup is None:
            return
        outcome = self.apply(ops.duplicate_lineup(lineup.id))
        if outcome is not None:
            self.reload(select_lineup=outcome.lineup_id, focus="lineups")
            self._done("Duplicated.")

    def cmd_rename(self) -> None:
        lineup = self._need_lineup()
        if lineup is None:
            return
        name = dialogs.ask_text(
            self._lineups_host, self._win, "New name for the lineup:", "Rename Lineup", lineup.name
        )
        if not name or name == lineup.name:
            return
        if self.apply(ops.rename_lineup(lineup.id, name)) is not None:
            self._remember(
                "Rename", lineup.name, "its old name", ops.rename_lineup(lineup.id, lineup.name)
            )
            self.reload(focus="lineups")
            self._done(self._lineups_host.offer_undo("Renamed."))

    def cmd_delete_lineup(self) -> None:
        lineup = self._need_lineup()
        if lineup is None:
            return
        rules = len(lineup.rules)
        detail = f"{count_text(rules, 'rule')} and {count_text(len(lineup.rows), 'item')}"
        question = f"Delete {lineup.name}, its {detail}? The items themselves are not deleted."
        if not dialogs.confirm(self._lineups_host, self._win, question, "Delete Lineup"):
            return
        outcome = self.apply(ops.delete_lineup(lineup.id))
        if outcome is None or outcome.deleted is None:
            return
        if self._lineups_host.start_lineup_id() == lineup.id:
            self._lineups_host.set_start_lineup_id("")
        self._remember(
            "Delete",
            lineup.name,
            "the lineup",
            ops.restore_lineup(outcome.deleted, outcome.deleted_index),
        )
        self.reload(focus="lineups")
        self._done(self._lineups_host.offer_undo(f"Deleted {lineup.name}."))

    def cmd_edit_rules(self) -> None:
        lineup = self._need_lineup()
        if lineup is None:
            return
        from quill.ui.lineups.rules_dialog import edit_rules

        result = edit_rules(self, lineup)
        if result is None:
            return
        rules, keep_items, settings = result
        before = lineup.rules
        if self.apply(ops.set_rules(lineup.id, rules, keep_items_of_deleted=keep_items)) is None:
            return
        if settings:
            self.apply(ops.set_settings(lineup.id, **settings))
        self._remember(
            "Rule change", lineup.name, "the rules it had", ops.set_rules(lineup.id, before)
        )
        self.reload()
        self.request_refresh(speak=True)

    def cmd_start_here(self) -> None:
        lineup = self._need_lineup()
        if lineup is None:
            return
        host = self._lineups_host
        if host.start_lineup_id() == lineup.id:
            host.set_start_lineup_id("")
            self._done(f"{host.app_name} opens as usual.")
        else:
            host.set_start_lineup_id(lineup.id)
            self._done(f"{lineup.name} opens when {host.app_name} starts.")
        self.reload()

    def cmd_removed_items(self) -> None:
        self._restore_from("removed")

    def cmd_recently_left(self) -> None:
        self._restore_from("left")

    def _restore_from(self, which: str) -> None:
        lineup = self._need_lineup()
        if lineup is None:
            return
        from quill.ui.lineups.lists_dialog import choose_entries

        choice = choose_entries(self, lineup, which)
        if choice is None:
            return
        refs, clear = choice
        if clear:
            what = "Removed Items" if which == "removed" else "Recently Left"
            question = f"Clear {what} for {lineup.name}? This cannot be undone" + (
                ", and removed items could then come back through a rule."
                if which == "removed"
                else "."
            )
            if not dialogs.confirm(self._lineups_host, self._win, question, f"Clear {what}"):
                return
            if self.apply(ops.clear_list(lineup.id, which)) is not None:
                self._done(f"{what} cleared.")
            return
        if not refs:
            return
        operation = ops.restore_removed if which == "removed" else ops.restore_left
        outcome = self.apply(operation(lineup.id, refs))
        if outcome is not None:
            self.reload(select=list(outcome.select), focus="items")
            count = len(outcome.select)
            self._done(
                f"Brought back {count_text(count, 'item')}; "
                + ("it stays" if count == 1 else "they stay")
                + " whatever the rules say."
            )

    def cmd_export_rules(self) -> None:
        lineup = self._need_lineup()
        if lineup is None:
            return
        path = dialogs.ask_path(
            self._lineups_host, self._win, "Export Rules", save=True, name=f"{lineup.name}.json"
        )
        if not path:
            return
        data = {
            "quill_lineup_rules": RULES_FILE_VERSION,
            "name": lineup.name,
            "rules": [rule.to_dict() for rule in lineup.rules],
            "new_items": lineup.new_items,
            "skip_live": lineup.skip_live,
            "budget_minutes": lineup.budget_minutes,
        }
        try:
            from quill.core.storage import write_json_atomic

            write_json_atomic(Path(path), data)
        except OSError as exc:
            self._say(f"The rules could not be saved: {exc}.")
            return
        self._done("Rules exported. Importing them makes a lineup that finds the same things.")

    def cmd_import_rules(self) -> None:
        path = dialogs.ask_path(self._lineups_host, self._win, "Import Rules", save=False)
        if not path:
            return
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            self._say(f"That file could not be read: {exc}.")
            return
        if not isinstance(raw, dict) or not isinstance(raw.get("quill_lineup_rules"), int):
            self._say("That file is not a lineup rules file.")
            return
        rules = tuple(
            rule
            for rule in (Rule.from_dict(entry) for entry in raw.get("rules") or [])
            if rule is not None
        )
        rules = tuple(Rule(**{**_fields(rule), "id": new_rule_id()}) for rule in rules)
        outcome = self.apply(
            ops.create_lineup(str(raw.get("name") or "Imported lineup"), rules=rules)
        )
        if outcome is None:
            return
        self.apply(
            ops.set_settings(
                outcome.lineup_id,
                new_items=str(raw.get("new_items", "rule")),
                skip_live=bool(raw.get("skip_live", False)),
                budget_minutes=max(0, int(raw.get("budget_minutes", 0) or 0)),
            )
        )
        self.reload(select_lineup=outcome.lineup_id, focus="lineups")
        self._done(
            f"Imported {len(rules)} rule{'s' if len(rules) != 1 else ''}. They are running now."
        )
        self.request_refresh(speak=False)

    def cmd_close(self) -> None:
        self._win.Close()

    # -- editing items -------------------------------------------------------------------

    def cmd_undo(self) -> None:
        if not self._lineups_host.undo_last():
            self._say("There is nothing to undo.")

    def cmd_select_all(self) -> None:
        for row in range(self._items.GetItemCount()):
            self._items.Select(row, True)

    def cmd_keep(self) -> None:
        found = self._need_items()
        if found is None:
            return
        lineup, refs = found
        rows = [lineup.row_for(ref) for ref in refs]
        keep = not all(row is not None and row.held == HELD_KEPT for row in rows)
        if self.apply(ops.set_kept(lineup.id, refs, keep)) is None:
            return
        self._remember(
            "Keep" if keep else "Stop keeping",
            lineup.name,
            "how it was",
            ops.set_kept(lineup.id, refs, not keep),
        )
        self.reload(select=refs)
        if len(refs) == 1:
            self._done(
                "Kept. It stays whatever the rules say."
                if keep
                else "No longer kept: its rules decide again."
            )
        else:  # counts, always (review N1)
            self._done(
                f"Kept {count_text(len(refs), 'item')}. They stay whatever the rules say."
                if keep
                else f"{count_text(len(refs), 'item')} no longer kept: their rules decide again."
            )

    def cmd_remove(self) -> None:
        found = self._need_items()
        if found is None:
            return
        lineup, refs = found
        sentence = (
            "Removed. Removed Items can bring it back."
            if len(refs) == 1
            else f"Removed {count_text(len(refs), 'item')}. Removed Items can bring them back."
        )
        self._remove(lineup, refs, sentence)

    def cmd_remove_missing(self) -> None:
        lineup = self._need_lineup()
        if lineup is None:
            return
        missing = [row.ref for row in lineup.rows if self.facts_for(row.ref)[0] is Presence.MISSING]
        if not missing:
            self._say("Nothing in this lineup is missing.")
            return
        self._remove(
            lineup,
            missing,
            f"Removed {len(missing)} missing item{'s' if len(missing) != 1 else ''}.",
        )

    def _remove(self, lineup: Lineup, refs: Sequence[ItemRef], sentence: str) -> None:
        wanted = set(refs)
        entries: list[Row] = []
        anchors: dict[ItemRef, ItemRef | None] = {}
        previous: ItemRef | None = None
        for row in lineup.rows:
            if row.ref in wanted:
                entries.append(row)
                anchors[row.ref] = previous
            else:
                previous = row.ref
        outcome = self.apply(ops.remove_rows(lineup.id, refs))
        if outcome is None:
            return
        self._remember(
            "Remove",
            list_sentence([row.name for row in entries]),
            "where it was",
            ops.restore_rows(lineup.id, entries, at=anchors),
        )
        self.reload(select=list(outcome.select))
        self._done(self._lineups_host.offer_undo(sentence))

    def cmd_cut(self) -> None:
        found = self._need_items()
        if found is None:
            return
        _lineup, refs = found
        self._clip = tuple(refs)
        count = len(refs)
        self._done(
            f"Cut {count_text(count, 'item')}. Paste puts them before or after the item you choose."
        )

    def cmd_paste_before(self) -> None:
        self._paste(after_target=False)

    def cmd_paste_after(self) -> None:
        self._paste(after_target=True)

    def _paste(self, *, after_target: bool) -> None:
        lineup = self._need_lineup()
        target = self.focused_ref()
        if lineup is None or target is None:
            return
        if not self._clip:
            self._say("Nothing is cut. Cut, Ctrl+X, marks items to move.")
            return
        if target in self._clip:
            self._say("Choose an item that is not one of those being moved.")
            return
        order = [row.ref for row in lineup.rows]
        if after_target:
            anchor: ItemRef | None = target
        else:
            rest = [ref for ref in order if ref not in self._clip]
            index = rest.index(target) if target in rest else 0
            anchor = rest[index - 1] if index > 0 else None
        outcome = self.apply(
            ops.move_rows(lineup.id, self._clip, after=anchor, to_top=anchor is None)
        )
        if outcome is None or outcome.stale:
            self._say("Those items have left the lineup since they were cut.")
            self._clip = ()
            return
        self._remember("Move", lineup.name, "the order it had", ops.restore_order(lineup.id, order))
        moved = self._clip
        self._clip = ()
        self.reload(select=list(moved))
        self._say_position(list(moved))

    def cmd_why(self) -> None:
        lineup = self._need_lineup()
        ref = self.focused_ref()
        if lineup is None or ref is None:
            return
        row = lineup.row_for(ref)
        if row is None:
            return
        _presence, facts = self.facts_for(ref)
        text = why_text(lineup, row, facts, now=self._lineups_host.now())
        dialogs.show_why(self._lineups_host, self._win, text)

    def cmd_refresh(self) -> None:
        self._say("Refreshing.")
        self.request_refresh(speak=True)


def _fields(rule: Rule) -> dict[str, Any]:
    return {name: getattr(rule, name) for name in Rule.__dataclass_fields__}


__all__ = ["RULES_FILE_VERSION", "LineupsCommandsMixin"]
