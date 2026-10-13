"""Edit Rule: what one rule looks for, and when its items go.

Built from Cast's Episode Filter dialogs, which listeners already know: the
parts of a rule in labelled groups, in the order the rule's sentence reads --
**Look for**, **Narrow by**, **Tests**, **Order and amount**, **When they go**.

Three things are deliberate:

* **The count lives where focus goes.** Try It fills the Matches list, moves
  the cursor to it, and the list's own name carries the count ("Matches, 7
  items"); a count in a label that changes silently is never heard.
* **A bad test is fixed where it is.** OK stays open, the cursor goes to the
  test at fault, and the problem is said and written into its row.
* **Changing what the rule looks for warns first** when tests would be lost,
  because a field one kind has (Played) means nothing to another (a station).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from quill.core.lineups.conditions import NO, YES, Condition, describe, ops_for_type
from quill.core.lineups.describe import count_text, row_text
from quill.core.lineups.fields import GROUP_FIELDS, LIST, TEXT, YESNO, ItemFacts, fields_for
from quill.core.lineups.model import Row
from quill.core.lineups.refs import FINISHABLE_KINDS, KIND_PLURALS, KINDS, Presence
from quill.core.lineups.rules import (
    KEEP_LABELS,
    KEEP_MODES,
    MATCH_ALL,
    MATCH_ANY,
    SORT_LABELS,
    SORTS,
    Keep,
    Rule,
    default_keep,
    evaluate,
    scope_values,
    with_scope,
)
from quill.core.podcasts.filter_conditions import OP_PHRASES
from quill.ui.lineups.host import LineupsHost

TITLE = "Edit Rule"
TEST_TITLE = "Test"

_DAY_MODES = ("for_days", "until_done_or_days")
_DONE_MODES = ("until_done", "until_done_or_days")


def _keep_modes(kind: str) -> list[str]:
    """A station is never finished, so it is not offered "Until finished"."""
    if kind in FINISHABLE_KINDS:
        return list(KEEP_MODES)
    return [mode for mode in KEEP_MODES if mode not in _DONE_MODES]


def _scope_fields(kind: str) -> list[tuple[str, str]]:
    return [(f.id, f.label) for f in fields_for(kind) if f.type in (TEXT, LIST) and f.id != "name"]


def edit_test(
    host: LineupsHost, parent: Any, kind: str, test: Condition | None
) -> Condition | None:
    """One test: field, comparison, value. ``None`` when cancelled."""
    import wx

    fields = [f for f in fields_for(kind)]
    if not fields:
        return None
    dialog = wx.Dialog(parent, title=TEST_TITLE)
    sizer = wx.BoxSizer(wx.VERTICAL)
    grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
    grid.Add(wx.StaticText(dialog, label="&Field:"), 0, wx.ALIGN_CENTER_VERTICAL)
    field_choice = wx.Choice(dialog, choices=[f.label for f in fields])
    field_choice.SetHelpText("What this test looks at.")
    grid.Add(field_choice, 1, wx.EXPAND)
    grid.Add(wx.StaticText(dialog, label="T&est:"), 0, wx.ALIGN_CENTER_VERTICAL)
    op_choice = wx.Choice(dialog)
    op_choice.SetHelpText("How it compares. A number test never matches an item that does not say.")
    grid.Add(op_choice, 1, wx.EXPAND)
    value_label = wx.StaticText(dialog, label="&Value:")
    grid.Add(value_label, 0, wx.ALIGN_CENTER_VERTICAL)
    value_box = wx.TextCtrl(dialog)
    value_box.SetHelpText("What to look for: words, a wildcard, a pattern, or a whole number.")
    grid.Add(values_box := wx.BoxSizer(wx.HORIZONTAL), 1, wx.EXPAND)
    values_box.Add(value_box, 1, wx.EXPAND)
    yesno_label = wx.StaticText(dialog, label="&Yes or no:")
    value_yesno = wx.Choice(dialog, choices=["Yes", "No"])
    value_yesno.SetHelpText("Yes or no.")
    grid.Add(yesno_label, 0, wx.ALIGN_CENTER_VERTICAL)
    grid.Add(value_yesno, 0)
    grid.AddGrowableCol(1)
    sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 10)
    case = wx.CheckBox(dialog, label="Ca&pitals must match")
    case.SetHelpText("Off: News and news are the same. On: they are not.")
    sizer.Add(case, 0, wx.LEFT | wx.RIGHT, 10)
    unit = wx.StaticText(dialog, label="")
    sizer.Add(unit, 0, wx.ALL, 10)
    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    dialog.SetSizerAndFit(sizer)

    def ops_of(index: int) -> list[str]:
        return list(ops_for_type(fields[index].type))

    def refresh(keep_op: str = "") -> None:
        index = max(0, field_choice.GetSelection())
        field = fields[index]
        choices = ops_of(index)
        op_choice.Set([OP_PHRASES.get(op, op) for op in choices])
        op_choice.SetSelection(choices.index(keep_op) if keep_op in choices else 0)
        is_yesno = field.type == YESNO
        value_box.Show(not is_yesno)
        value_label.Show(not is_yesno)
        value_yesno.Show(is_yesno)
        yesno_label.Show(is_yesno)
        case.Show(field.type in (TEXT, LIST))
        unit.SetLabel(f"In {field.unit}." if field.unit else "")
        dialog.Layout()
        dialog.Fit()

    start = 0
    if test is not None:
        start = next((i for i, f in enumerate(fields) if f.id == test.field), 0)
    field_choice.SetSelection(start)
    refresh(test.op if test is not None else "")
    if test is not None:
        value_box.SetValue(test.value if fields[start].type != YESNO else "")
        value_yesno.SetSelection(0 if test.value != NO else 1)
        case.SetValue(test.case_sensitive)
    field_choice.Bind(wx.EVT_CHOICE, lambda _e: refresh())
    field_choice.SetFocus()
    try:
        while True:
            from quill.ui import dialog_contract

            dialog_contract.apply_modal_ids(dialog)
            if host.show_modal_dialog(dialog, TEST_TITLE) != wx.ID_OK:
                return None
            index = max(0, field_choice.GetSelection())
            field = fields[index]
            op = ops_of(index)[max(0, op_choice.GetSelection())]
            value = (
                (YES if value_yesno.GetSelection() == 0 else NO)
                if field.type == YESNO
                else value_box.GetValue().strip()
            )
            made = Condition(
                field.id, op, value, bool(case.GetValue()) and field.type in (TEXT, LIST)
            )
            error = made.error(kind)
            if not error:
                return made
            problem = f"{field.label}: {error}."
            unit.SetLabel(problem)  # written where it is, not only said (review S4)
            wx.CallLater(400, host.announce, problem)  # after the dialog is back
            (value_yesno if field.type == YESNO else value_box).SetFocus()
    finally:
        dialog.Destroy()


class RuleEditor:
    """The Edit Rule dialog for one rule."""

    def __init__(
        self,
        host: LineupsHost,
        parent: Any,
        rule: Rule,
        catalogue_items: Mapping[str, Sequence[ItemFacts]] | None,
    ) -> None:
        import wx

        self._wx = wx
        self._host = host
        self._rule = rule
        self._items = catalogue_items or {}
        self._scope_field = ""
        self._closed = False
        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._build()
        self._load(rule)

    # -- building ----------------------------------------------------------------------

    def _group(self, title: str) -> Any:
        wx = self._wx
        box = wx.StaticBoxSizer(wx.VERTICAL, self.dialog, title)
        self._root.Add(box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        return box

    def _place(self, sizer: Any, label: Any, control: Any) -> Any:
        """Put *label* then *control* in *sizer*.

        The label is always built *before* its control (``_label``): a screen
        reader names a control from the static text that precedes it, so a
        label made afterwards is one nobody ever hears. Help is set inline
        where each control is built, which is what the F1 audit verifies.
        """
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        row.Add(control, 1, wx.EXPAND)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 4)
        return control

    def _build(self) -> None:
        wx = self._wx
        self._root = wx.BoxSizer(wx.VERTICAL)
        kind = self._group("What it looks for")
        box = kind.GetStaticBox()
        _kind_label = wx.StaticText(box, label="&Look for:")
        self._kind = wx.Choice(box, choices=[KIND_PLURALS[k] for k in KINDS])
        self._kind.SetHelpText(
            "The kind of thing this rule brings in. One kind per rule; "
            "a lineup can have many rules."
        )
        self._place(kind, _kind_label, self._kind)
        where = self._group("Where to look")
        box = where.GetStaticBox()
        _scope_by_label = wx.StaticText(box, label="&Narrow by:")
        self._scope_by = wx.Choice(box)
        self._scope_by.SetHelpText(
            "Look only in some folders, podcasts, channels or other groups: choose one "
            "here, then select values below. With nothing selected, the rule looks everywhere."
        )
        self._place(where, _scope_by_label, self._scope_by)
        _filter_label = wx.StaticText(box, label="&Filter values:")
        self._filter = wx.TextCtrl(box)
        self._filter.SetHelpText("Type part of a name to shorten the list of values below.")
        self._place(where, _filter_label, self._filter)
        _values_label = wx.StaticText(box, label="&Values:")
        # A multiple-selection list, not a CheckListBox (banned, A11Y-SR-1: readers do
        # not say a check box's state as you arrow). Selected is said on every row.
        self._values = wx.ListBox(box, size=(-1, 110), style=wx.LB_MULTIPLE)
        self._values.SetHelpText(
            "Select every value to look in: Space selects or deselects the value under the cursor. "
            "Any selected value counts."
        )
        self._place(where, _values_label, self._values)
        tests = self._group("Tests")
        box = tests.GetStaticBox()
        _tests_label = wx.StaticText(box, label="T&ests:")
        self._tests = wx.ListBox(box, size=(-1, 90))
        self._tests.SetHelpText(
            "What an item must be. With no tests, everything in the places above is found."
        )
        self._place(tests, _tests_label, self._tests)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler, help_text in (
            ("&Add Test...", self._add_test, "Add a test: a field, a comparison and a value."),
            ("Ed&it Test...", self._edit_test, "Change the selected test."),
            ("&Remove Test", self._remove_test, "Remove the selected test."),
        ):
            button = wx.Button(box, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            buttons.Add(button, 0, wx.RIGHT, 6)
        tests.Add(buttons, 0, wx.ALL, 4)
        _match_label = wx.StaticText(box, label="&Match:")
        self._match = wx.Choice(box, choices=["All of the tests", "Any of the tests"])
        self._match.SetHelpText("All: an item must pass every test. Any: one is enough.")
        self._place(tests, _match_label, self._match)
        amount = self._group("Order and amount")
        box = amount.GetStaticBox()
        _sort_label = wx.StaticText(box, label="&Order:")
        self._sort = wx.Choice(box, choices=[SORT_LABELS[s] for s in SORTS])
        self._sort.SetHelpText(
            "The order this rule's items arrive in. You can move them afterwards."
        )
        self._place(amount, _sort_label, self._sort)
        _limit_label = wx.StaticText(box, label="&Count limit (0 for none):")
        self._limit = wx.SpinCtrl(box, min=0, max=10_000)
        self._limit.SetHelpText("At most this many items from this rule.")
        self._place(amount, _limit_label, self._limit)
        _per_group_label = wx.StaticText(box, label="Per &group limit (0 for none):")
        self._per_group = wx.SpinCtrl(box, min=0, max=1_000)
        self._per_group.SetHelpText(
            "At most this many from each podcast, channel, album or folder."
        )
        self._place(amount, _per_group_label, self._per_group)
        _budget_label = wx.StaticText(box, label="&Up to minutes in all (0 for none):")
        self._budget = wx.SpinCtrl(box, min=0, max=100_000)
        self._budget.SetHelpText("Stop adding once this many minutes are found.")
        self._place(amount, _budget_label, self._budget)
        going = self._group("When they go")
        box = going.GetStaticBox()
        _keep_label = wx.StaticText(box, label="&Keep:")
        self._keep = wx.Choice(box)
        self._keep.SetHelpText(
            "How long this rule's items stay. While it matches: they go when they stop "
            "matching. Until finished: they go once heard. For days: they go after that "
            "many days. Always: never."
        )
        self._place(going, _keep_label, self._keep)
        _days_label = wx.StaticText(box, label="&Days:")
        self._days = wx.SpinCtrl(box, min=1, max=365)
        self._days.SetHelpText("How many days an item stays.")
        self._place(going, _days_label, self._days)
        _percent_label = wx.StaticText(box, label="&Percent heard that counts as finished:")
        self._percent = wx.SpinCtrl(box, min=1, max=100)
        self._percent.SetHelpText(
            "Heard past this much counts as finished. Played in Cast always counts."
        )
        self._place(going, _percent_label, self._percent)
        _max_kept_label = wx.StaticText(box, label="Ma&x kept (0 for no cap):")
        self._max_kept = wx.SpinCtrl(box, min=0, max=10_000)
        self._max_kept.SetHelpText(
            "Keep at most this many from the rule; the oldest arrivals go first."
        )
        self._place(going, _max_kept_label, self._max_kept)
        self._enabled = wx.CheckBox(box, label="Rule &switched on")
        self._enabled.SetHelpText(
            "Off: the rule finds nothing new and lets nothing go until it is on again."
        )
        going.Add(self._enabled, 0, wx.ALL, 4)
        trial = self._group("Try it")
        box = trial.GetStaticBox()
        self._try = wx.Button(box, label="&Try It")
        self._try.SetHelpText("Show what this rule finds right now, without saving it.")
        self._try.Bind(wx.EVT_BUTTON, lambda _e: self._try_it())
        trial.Add(self._try, 0, wx.ALL, 4)
        self._matches_label = _matches_label = wx.StaticText(box, label="Matc&hes:")
        self._matches = wx.ListBox(box, size=(-1, 90))
        self._matches.SetHelpText("What the rule finds now, in its order.")
        self._place(trial, _matches_label, self._matches)
        self._matches.SetName("Matches")
        self._root.Add(
            self.dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10
        )
        self.dialog.SetSizerAndFit(self._root)
        # Not EVT_CHOICE: arrowing a closed Choice fires it on every press, and a
        # change of kind clears tests -- so it waits until the cursor leaves the
        # control, or OK, and keeps every other edit (review S2).
        self._kind.Bind(wx.EVT_KILL_FOCUS, self._on_kind_left)
        self._scope_by.Bind(wx.EVT_CHOICE, lambda _e: self._scope_field_changed())
        self._filter.Bind(wx.EVT_TEXT, lambda _e: self._fill_values())
        self._values.Bind(wx.EVT_LISTBOX, lambda _e: self._values_checked())
        self._keep.Bind(wx.EVT_CHOICE, lambda _e: self._keep_changed())
        self._tests.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._edit_test())

    # -- loading and reading ------------------------------------------------------------

    def _load(self, rule: Rule) -> None:
        self._kind.SetSelection(KINDS.index(rule.kind) if rule.kind in KINDS else 0)
        self._fill_kind_parts()
        self._fill_tests()
        self._match.SetSelection(1 if rule.match == MATCH_ANY else 0)
        self._sort.SetSelection(SORTS.index(rule.sort) if rule.sort in SORTS else 0)
        self._limit.SetValue(rule.limit)
        self._per_group.SetValue(rule.per_group)
        self._budget.SetValue(rule.budget_minutes)
        modes = _keep_modes(rule.kind)
        keep = rule.keep.effective(rule.kind)
        self._keep.SetSelection(modes.index(keep.mode) if keep.mode in modes else 0)
        self._days.SetValue(keep.days)
        self._percent.SetValue(keep.percent)
        self._max_kept.SetValue(keep.max_kept)
        self._enabled.SetValue(rule.enabled)
        self._keep_changed()

    def _fill_kind_parts(self) -> None:
        kind = self._rule.kind
        fields = _scope_fields(kind)
        self._scope_by.Set(["Choose what to narrow by", *(label for _fid, label in fields)])
        current = next(
            (i + 1 for i, (fid, _l) in enumerate(fields) if scope_values(self._rule, fid)), 0
        )
        self._scope_by.SetSelection(current)
        self._scope_field = fields[current - 1][0] if current else ""
        self._fill_values()
        self._keep.Set([KEEP_LABELS[mode] for mode in _keep_modes(kind)])
        has_group = kind in GROUP_FIELDS
        self._per_group.Enable(has_group)

    def _known_values(self) -> list[str]:
        found: dict[str, str] = {}
        for item in self._items.get(self._rule.kind, ()):
            fact = item.fact(self._scope_field)
            for value in fact if isinstance(fact, tuple) else (fact,):
                text = str(value or "").strip()
                if text:
                    found.setdefault(text.casefold(), text)
        for value in scope_values(self._rule, self._scope_field):
            found.setdefault(value.casefold(), value)  # a checked value that no longer exists stays
        return sorted(found.values(), key=str.casefold)

    def _fill_values(self) -> None:
        wanted = self._filter.GetValue().strip().casefold()
        values = (
            [v for v in self._known_values() if wanted in v.casefold()] if self._scope_field else []
        )
        self._shown_values = values
        self._values.Set(values)
        checked = {v.casefold() for v in scope_values(self._rule, self._scope_field)}
        for index, value in enumerate(values):
            if value.casefold() in checked:
                self._values.SetSelection(index)
        self._values.Enable(bool(self._scope_field))
        self._filter.Enable(bool(self._scope_field))

    def _values_checked(self) -> None:
        current = {v.casefold(): v for v in scope_values(self._rule, self._scope_field)}
        for index, value in enumerate(self._shown_values):
            if self._values.IsSelected(index):
                current[value.casefold()] = value
            else:
                current.pop(value.casefold(), None)
        self._rule = with_scope(self._rule, self._scope_field, list(current.values()))

    def _scope_field_changed(self) -> None:
        fields = _scope_fields(self._rule.kind)
        index = self._scope_by.GetSelection()
        # Only which field's values are shown changes: nothing selected under
        # another field is lost by arrowing past it (review S2).
        self._scope_field = fields[index - 1][0] if index > 0 else ""
        self._filter.ChangeValue("")
        self._fill_values()

    def _on_kind_left(self, event: Any) -> None:
        event.Skip()
        self._wx.CallAfter(self._kind_changed)

    def _kind_changed(self) -> bool:
        """Apply a new kind. ``False`` when the listener kept the old one."""
        if not self.dialog:
            return True
        if self._closed or not self.dialog.IsShown():
            return True  # Cancel, Escape or Alt+Tab left the control: nothing to ask (R2)
        kind = KINDS[max(0, self._kind.GetSelection())]
        if kind == self._rule.kind:
            return True
        self._rule = self.read()  # keep order, limits and Keep as edited
        if self._rule.tests or self._rule.scope:
            from quill.ui.lineups.dialogs import confirm

            if not confirm(
                self._host,
                self.dialog,
                f"Looking for {KIND_PLURALS[kind].lower()} instead clears this rule's "
                "tests and places. Change it?",
                "Change What It Looks For",
            ):
                self._kind.SetSelection(KINDS.index(self._rule.kind))
                return False
        self._rule = replace(
            self._rule, kind=kind, tests=(), scope=(), per_group=0, keep=default_keep(kind)
        )
        self._fill_kind_parts()
        self._fill_tests()
        self._load(self._rule)
        return True

    def _keep_changed(self) -> None:
        modes = _keep_modes(self._rule.kind)
        mode = modes[max(0, self._keep.GetSelection())]
        self._days.Enable(mode in _DAY_MODES)
        self._percent.Enable(mode in _DONE_MODES)

    def _fill_tests(self, select: int = 0) -> None:
        kind = self._rule.kind
        self._tests.Set([describe(test, kind) for test in self._rule.tests])
        if self._rule.tests:
            self._tests.SetSelection(max(0, min(select, len(self._rule.tests) - 1)))

    def _add_test(self) -> None:
        made = edit_test(self._host, self.dialog, self._rule.kind, None)
        if made is not None:
            self._rule = replace(self._rule, tests=(*self._rule.tests, made))
            self._fill_tests(len(self._rule.tests) - 1)
            self._tests.SetFocus()

    def _edit_test(self) -> None:
        index = self._tests.GetSelection()
        if index < 0:
            return
        made = edit_test(self._host, self.dialog, self._rule.kind, self._rule.tests[index])
        if made is not None:
            tests = list(self._rule.tests)
            tests[index] = made
            self._rule = replace(self._rule, tests=tuple(tests))
            self._fill_tests(index)
            self._tests.SetFocus()

    def _remove_test(self) -> None:
        index = self._tests.GetSelection()
        if index < 0:
            return
        tests = list(self._rule.tests)
        del tests[index]
        self._rule = replace(self._rule, tests=tuple(tests))
        self._fill_tests(index)
        self._host.announce("Test removed.")

    def read(self) -> Rule:
        modes = _keep_modes(self._rule.kind)
        return replace(
            self._rule,
            match=MATCH_ANY if self._match.GetSelection() == 1 else MATCH_ALL,
            sort=SORTS[max(0, self._sort.GetSelection())],
            limit=int(self._limit.GetValue()),
            per_group=int(self._per_group.GetValue()) if self._rule.kind in GROUP_FIELDS else 0,
            budget_minutes=int(self._budget.GetValue()),
            keep=Keep(
                modes[max(0, self._keep.GetSelection())],
                days=int(self._days.GetValue()),
                percent=int(self._percent.GetValue()),
                max_kept=int(self._max_kept.GetValue()),
            ),
            enabled=bool(self._enabled.GetValue()),
        )

    def _try_it(self) -> None:
        rule = replace(self.read(), enabled=True)
        found = evaluate(rule, self._items.get(rule.kind, ()))
        self._matches.Set([
            row_text(Row(ref=item.ref, name=item.name), item, Presence.PRESENT) for item in found
        ])
        count = len(found)
        # The count is in the list's label, made before the cursor moves there, so
        # the reader says it as the list is reached. SetName is inert on Windows,
        # and a sentence said just before a focus move is cut off (review S1).
        self._matches_label.SetLabel(f"Matc&hes, {count_text(count, 'item')}:")
        if not self._items:
            self._host.announce_soon(
                "Nothing could be read yet; the lineup will find matches once it has refreshed."
            )
        self._matches.SetFocus()
        if count:
            self._matches.SetSelection(0)

    def run(self) -> Rule | None:
        wx = self._wx
        self._kind.SetFocus()
        try:
            while True:
                from quill.ui import dialog_contract

                dialog_contract.apply_modal_ids(self.dialog)
                answer = self._host.show_modal_dialog(self.dialog, TITLE)
                if answer != wx.ID_OK:
                    self._closed = True
                    return None
                if not self._kind_changed():
                    continue  # the listener kept the old kind; the dialog stays
                rule = self.read()
                bad = next(
                    (i for i, t in enumerate(rule.tests) if not t.is_usable(rule.kind)), None
                )
                if bad is None:
                    return rule
                self._fill_tests(bad)  # the row itself says why it cannot be used
                problem = describe(rule.tests[bad], rule.kind) + "."
                self._wx.CallLater(400, self._host.announce, problem)  # once it is back (S4)
                self._tests.SetFocus()
        finally:
            self._closed = True
            self.dialog.Destroy()


__all__ = ["TEST_TITLE", "TITLE", "RuleEditor", "edit_test"]
