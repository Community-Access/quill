"""One test inside an Episode Filter rule: a field, a comparison and a value.

Its own small window rather than three more rows in the rule editor, because a
rule can hold several tests and a form that grew three controls per test would
be read one control at a time, forever. The rule editor lists the tests as
sentences ("Show notes contains 'sponsor'"); this is where one sentence is
written.

The comparison list follows the field: a number field offers at least, at most,
is and is not; the episode type offers its three values as whole phrases ("is a
trailer"), so there is no value box to fill in wrongly; a text field offers
words, wildcards and regular expressions. Saving is refused, with focus put
back on the value, for a regular expression that does not compile or a number
that is not one -- the only moments a test can be wrong.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts import settings_help
from quill.core.podcasts.filter_conditions import (
    EPISODE_TYPE_LABELS,
    EPISODE_TYPES,
    FIELD_LABELS,
    FIELD_TYPE,
    FIELDS,
    NUMBER_FIELDS,
    OP_IS,
    OP_IS_NOT,
    OP_PHRASES,
    FilterCondition,
    ops_for,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

#: The window title, answered by F1 through ``core/podcasts/surface_help.py``.
TITLE = "Episode Filter Test"

__all__ = ["TITLE", "EpisodeFilterTestDialog", "comparison_choices"]


def comparison_choices(field: str) -> list[tuple[str, str, str]]:
    """``(label, op, fixed value)`` rows for *field*'s comparison list.

    The episode type's rows carry their value, so choosing "is a trailer" is
    the whole test; every other row leaves the value to the value box.
    """
    if field == FIELD_TYPE:
        rows: list[tuple[str, str, str]] = []
        for op in (OP_IS, OP_IS_NOT):
            for kind in EPISODE_TYPES:
                rows.append((f"{OP_PHRASES[op]} {EPISODE_TYPE_LABELS[kind]}", op, kind))
        return rows
    return [(OP_PHRASES[op], op, "") for op in ops_for(field)]


class EpisodeFilterTestDialog:
    """Edit one test; ``show()`` returns the test, or ``None`` on cancel."""

    def __init__(
        self,
        parent: object,
        *,
        condition: FilterCondition | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: FilterCondition | None = None
        source = condition or FilterCondition()

        self.dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(self.dialog, label="&Look at:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._field = wx.Choice(self.dialog, choices=[FIELD_LABELS[f] for f in FIELDS])
        self._field.SetName("Look at")
        self._field.SetHelpText(settings_help.FILTER_HELP["test_field"])
        self._field.SetSelection(FIELDS.index(source.field) if source.field in FIELDS else 1)
        grid.Add(self._field, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="&Test:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._op = wx.Choice(self.dialog)
        self._op.SetName("Test")
        self._op.SetHelpText(settings_help.FILTER_HELP["test_op"])
        grid.Add(self._op, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="&Value:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._value = wx.TextCtrl(self.dialog)
        self._value.SetName("Value")
        self._value.SetHelpText(settings_help.FILTER_HELP["test_value"])
        if source.field != FIELD_TYPE:
            self._value.SetValue(source.value)
        grid.Add(self._value, 1, wx.EXPAND)
        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        self._case = wx.CheckBox(self.dialog, label="&Capital letters have to match too")
        self._case.SetValue(source.case_sensitive)
        self._case.SetHelpText(settings_help.FILTER_HELP["test_case"])
        root.Add(self._case, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "Save")
        ok_btn.SetHelpText(
            "Keeps this test in the rule. Nothing is applied until the filter is saved."
        )
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetHelpText("Leaves the test as it was.")
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizerAndFit(root)
        self._fill_ops(source)
        self._field.Bind(wx.EVT_CHOICE, self._on_field)
        self._op.Bind(wx.EVT_CHOICE, lambda _e: self._sync_enabled())
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Save",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )

    # -- the comparison list follows the field -------------------------------

    def _current_field(self) -> str:
        return FIELDS[max(0, self._field.GetSelection())]

    def _fill_ops(self, source: FilterCondition | None = None) -> None:
        self._rows = comparison_choices(self._current_field())
        self._op.Set([label for label, _op, _value in self._rows])
        chosen = 0
        if source is not None:
            for index, (_label, op, value) in enumerate(self._rows):
                if op == source.op and (not value or value == source.value):
                    chosen = index
                    break
        self._op.SetSelection(chosen)
        self._sync_enabled()

    def _sync_enabled(self) -> None:
        """The value box and the capitals box only where they mean something."""
        field = self._current_field()
        self._value.Enable(field != FIELD_TYPE)
        self._case.Enable(field not in NUMBER_FIELDS and field != FIELD_TYPE)

    def _on_field(self, _event: object) -> None:
        self._fill_ops()

    # -- reading the form ------------------------------------------------------

    def _drafted(self) -> FilterCondition:
        field = self._current_field()
        _label, op, fixed = self._rows[max(0, self._op.GetSelection())]
        value = fixed if field == FIELD_TYPE else self._value.GetValue().strip()
        case = self._case.GetValue() and field not in NUMBER_FIELDS and field != FIELD_TYPE
        return FilterCondition(field=field, op=op, value=value, case_sensitive=case)

    def _on_ok(self, _event: object) -> None:
        draft = self._drafted()
        error = draft.error
        if error:
            from quill.ui.dialog_contract import show_message_box

            wx = self._wx
            show_message_box(
                f"This test cannot be saved: {error}.",
                TITLE,
                wx.OK | wx.ICON_WARNING,
                self.dialog,
                announce=None,
            )
            try:
                self._value.SetFocus()
            except Exception:  # noqa: BLE001 - focus is best-effort
                pass
            return
        self._result = draft
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> FilterCondition | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        wx.CallAfter(self._field.SetFocus)
        try:
            if show_modal_dialog(self.dialog, TITLE, announce=self._announce) != wx.ID_OK:
                return None
            return self._result
        finally:
            self.dialog.Destroy()
