"""Rules for a Lineup: the list of rules, and the Lineup's own settings.

Each row is the rule's whole sentence, including how long its items stay and
what it finds now. Two questions are asked before anything is changed, because
nothing should vanish without the listener knowing:

* **Deleting a rule that brought items in** asks whether to keep them (they
  become Kept) or let them go (to Recently Left).
* **A change that would let items go** says how many first; Cancel leaves the
  rules as they were.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from quill.core.lineups.describe import count_text, known_scope_values, rule_sentence
from quill.core.lineups.merge import Catalogue, refresh
from quill.core.lineups.model import NEW_ITEMS_LABELS, NEW_ITEMS_PLACES, Lineup
from quill.core.lineups.ops import items_of_rule
from quill.core.lineups.refs import KIND_EPISODE
from quill.core.lineups.rules import Rule, evaluate, new_rule
from quill.ui.lineups import dialogs
from quill.ui.lineups.rule_edit_dialog import RuleEditor

TITLE = "Rules"

Result = tuple[tuple[Rule, ...], bool, dict[str, object]]


class RulesDialog:
    def __init__(self, window: Any, lineup: Lineup) -> None:
        import wx

        self._wx = wx
        self._window = window
        self._host = window._lineups_host
        self._lineup = lineup
        self._catalogue: Catalogue | None = window._catalogue
        self._rules: list[Rule] = list(lineup.rules)
        self.dialog = wx.Dialog(
            window._win, title="Rules", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(self.dialog, label=f"&Rules for {lineup.name}:"), 0, wx.LEFT | wx.TOP, 10
        )
        self._list = wx.ListBox(self.dialog, size=(640, 180))
        self._list.SetName(f"Rules for {lineup.name}")
        self._list.SetHelpText(
            "Each rule as one sentence: what it brings in, how long its items stay, and "
            "what it finds now. Rules add to each other; anything any rule finds is in "
            "the lineup. Enter edits the selected rule."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler, help_text in (
            (
                "&Add Rule...",
                self._add,
                "Add a rule: what to look for, where, and how long it stays.",
            ),
            ("&Edit Rule...", self._edit, "Change the selected rule."),
            (
                "Re&move Rule",
                self._remove,
                "Remove the selected rule. You choose what happens to its items.",
            ),
            ("Move &Up", lambda: self._move(-1), "Move the rule up. Its new items go with it."),
            ("Move &Down", lambda: self._move(1), "Move the rule down."),
        ):
            button = wx.Button(self.dialog, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            buttons.Add(button, 0, wx.RIGHT, 6)
        root.Add(buttons, 0, wx.LEFT | wx.RIGHT, 10)

        settings = wx.StaticBoxSizer(wx.VERTICAL, self.dialog, "This lineup")
        box = settings.GetStaticBox()
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(box, label="&New items go:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._new_items = wx.Choice(box, choices=[NEW_ITEMS_LABELS[p] for p in NEW_ITEMS_PLACES])
        self._new_items.SetSelection(NEW_ITEMS_PLACES.index(lineup.new_items))
        self._new_items.SetHelpText(
            "Where a rule's new items appear. Items already here never move by themselves."
        )
        row.Add(self._new_items, 1)
        settings.Add(row, 0, wx.EXPAND | wx.ALL, 4)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(box, label="Play-through &budget in minutes (0 for none):"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._budget = wx.SpinCtrl(box, min=0, max=100_000, initial=lineup.budget_minutes)
        self._budget.SetHelpText(
            "Playing the whole lineup stops adding rule items once this many minutes are "
            "reached. Items you kept, added or moved are never left out."
        )
        row.Add(self._budget, 0)
        settings.Add(row, 0, wx.EXPAND | wx.ALL, 4)
        self._skip_live = wx.CheckBox(box, label="S&kip live items when playing through")
        self._skip_live.SetValue(lineup.skip_live)
        self._skip_live.SetHelpText(
            "A live station never ends; off, it plays until you press Next."
        )
        settings.Add(self._skip_live, 0, wx.ALL, 4)
        root.Add(settings, 0, wx.EXPAND | wx.ALL, 10)
        root.Add(
            self.dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10
        )
        self.dialog.SetSizerAndFit(root)
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._edit())
        # On the dialog, not the list: in a dialog the default OK button can take
        # Enter before a list's key-down ever sees it (review N10).
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        self._fill()

    def _on_key(self, event: Any) -> None:
        if self._wx.Window.FindFocus() is not self._list:
            event.Skip()
            return
        if event.GetKeyCode() in (self._wx.WXK_RETURN, self._wx.WXK_NUMPAD_ENTER):
            self._edit()
            return
        if event.GetKeyCode() in (self._wx.WXK_DELETE, self._wx.WXK_NUMPAD_DELETE):
            self._remove()
            return
        event.Skip()

    def _items_by_kind(self) -> dict[str, list[Any]]:
        found: dict[str, list[Any]] = {}
        if self._catalogue is not None:
            for item in self._catalogue.all_items():
                found.setdefault(item.ref.kind, []).append(item)
        return found

    def _fill(self, select: int = 0) -> None:
        by_kind = self._items_by_kind()
        rows = []
        for number, rule in enumerate(self._rules, 1):
            items = by_kind.get(rule.kind, [])
            finds = len(evaluate(rule, items)) if self._catalogue is not None else None
            known = known_scope_values(items, rule.kind) if items else None
            rows.append(f"{number}. {rule_sentence(rule, finds=finds, known=known)}")
        if not rows:
            rows = [
                "No rules yet. Add Rule makes the first; "
                "without rules this lineup holds only what you add."
            ]
        self._list.Set(rows)
        self._list.SetSelection(max(0, min(select, len(rows) - 1)))

    def _editor(self, rule: Rule) -> Rule | None:
        return RuleEditor(self._host, self.dialog, rule, self._items_by_kind()).run()

    def _add(self) -> None:
        rule = self._editor(new_rule(KIND_EPISODE))
        if rule is not None:
            self._rules.append(rule)
            self._fill(len(self._rules) - 1)
            self._list.SetFocus()

    def _edit(self) -> None:
        index = self._list.GetSelection()
        if not (0 <= index < len(self._rules)):
            self._add()
            return
        rule = self._editor(self._rules[index])
        if rule is not None:
            self._rules[index] = rule
            self._fill(index)
            self._list.SetFocus()

    def _remove(self) -> None:
        index = self._list.GetSelection()
        if not (0 <= index < len(self._rules)):
            return
        del self._rules[index]
        self._fill(index)
        self._host.announce("Rule removed. Nothing changes until OK.")

    def _move(self, delta: int) -> None:
        index = self._list.GetSelection()
        target = index + delta
        if not (0 <= index < len(self._rules)) or not (0 <= target < len(self._rules)):
            self._host.announce("Already at the top." if delta < 0 else "Already at the end.")
            return
        self._rules[index], self._rules[target] = self._rules[target], self._rules[index]
        self._fill(target)
        self._host.announce(f"Moved to {target + 1} of {len(self._rules)}.")

    def _settings(self) -> dict[str, object]:
        return {
            "new_items": NEW_ITEMS_PLACES[max(0, self._new_items.GetSelection())],
            "budget_minutes": int(self._budget.GetValue()),
            "skip_live": bool(self._skip_live.GetValue()),
        }

    def _questions(self) -> bool | None:
        """``True`` / ``False`` keep or let go a deleted rule's items; ``None`` to stay open.

        Also says how many items the change lets go, and asks before making it.
        """
        kept_ids = {rule.id for rule in self._rules}
        orphaned = [
            row
            for rule in self._lineup.rules
            if rule.id not in kept_ids
            for row in items_of_rule(self._lineup, rule.id)
        ]
        keep_items = True
        if orphaned:
            count = len(orphaned)
            answer = dialogs.ask_keep_or_let_go(
                self._host,
                self.dialog,
                f"The removed rules brought in {count_text(count, 'item')}. "
                "Keep them, or let them go?",
                "Removed Rules",
            )
            if answer is None:
                return None
            keep_items = answer
        if self._catalogue is not None:
            trial = replace(self._lineup, rules=tuple(self._rules))
            leaving = len([
                d
                for d in refresh(trial, self._catalogue, self._host.now()).left
                if d.reason != "its rule was deleted"
            ])
            if leaving and not dialogs.confirm(
                self._host,
                self.dialog,
                f"This change lets {count_text(leaving, 'item')} go. "
                "They will be in Recently Left. Make the change?",
                "Change the Rules",
            ):
                return None
        return keep_items

    def run(self) -> Result | None:
        wx = self._wx
        self._list.SetFocus()
        try:
            while True:
                from quill.ui import dialog_contract

                dialog_contract.apply_modal_ids(self.dialog)
                if self._host.show_modal_dialog(self.dialog, TITLE) != wx.ID_OK:
                    return None
                answer = self._questions()
                if answer is not None:
                    return tuple(self._rules), answer, self._settings()
        finally:
            self.dialog.Destroy()


def edit_rules(window: Any, lineup: Lineup) -> Result | None:
    """Show Rules for *lineup*; the new rules, keep-items choice and settings, or ``None``."""
    return RulesDialog(window, lineup).run()


__all__ = ["TITLE", "RulesDialog", "edit_rules"]
