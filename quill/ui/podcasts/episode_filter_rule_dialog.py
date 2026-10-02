"""One Episode Filter rule, on its own, with focus already on the name.

Split out of the filter editor rather than living inside it for two reasons.
The editor is a list plus a preview -- a *survey* of the rules -- and this is a
*form*; putting the form inside the survey would mean arrowing past six
controls to reach the list every time. And a rule has exactly one moment where
it can be wrong (a regular expression that does not compile, or a rule that
asks nothing at all), which is when this dialog is dismissed: keeping it here
means the check happens where the thing being checked is, and the message can
put focus back on the field that caused it.

Nothing here touches an episode, a queue, or the library. It builds a record
and hands it back.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.podcasts import settings_help
from quill.core.podcasts.filter_conditions import FilterCondition, describe_condition
from quill.core.podcasts.models_filters import (
    PATTERN_NONE,
    PATTERN_REGEX,
    PATTERN_WILDCARD,
    EpisodeFilterRule,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

#: The window title. Named in ``core/podcasts/surface_help.py`` so F1 answers
#: here (GATE-CAST-HELP).
TITLE = "Episode Filter Rule"

_KIND_LABELS = (
    "No title rule -- match on length only",
    "Wildcard -- star for any text, question mark for one character",
    "Regular expression",
)
_KIND_VALUES = (PATTERN_NONE, PATTERN_WILDCARD, PATTERN_REGEX)

__all__ = ["TITLE", "EpisodeFilterRuleDialog"]


class EpisodeFilterRuleDialog:
    """Edit one rule; ``show()`` returns the new rule, or ``None`` on cancel."""

    def __init__(
        self,
        parent: object,
        *,
        rule: EpisodeFilterRule | None = None,
        announce_cb: Callable[[str], None] | None = None,
        episodes: Sequence[Any] = (),
        intro: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: EpisodeFilterRule | None = None
        source = rule or EpisodeFilterRule(name="", pattern_kind=PATTERN_WILDCARD)
        #: The podcast's newest episodes, for Try It; empty when the caller has none.
        self._episodes = list(episodes)
        self._conditions: list[FilterCondition] = list(source.conditions)

        self.dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=intro
            or (
                "A rule can match on the episode title, on how long it is, and on "
                "more tests below -- the show notes, the people on it, its type, "
                "age, season or number. Rules never delete anything."
            ),
        )
        intro.Wrap(430)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        def label(text: str) -> None:
            """The static label, added *before* the control it labels.

            A screen reader associates a label with the control created after
            it, so a control built before its own label reads as unlabelled
            (the z-order contract). Written out control by control rather than
            hidden behind a factory, because a control constructed inside a
            lambda is one the F1-help gate cannot verify inline -- and help
            that a gate has to be told about is help that can quietly rot.
            """
            grid.Add(wx.StaticText(self.dialog, label=text), 0, wx.ALIGN_CENTER_VERTICAL)

        label("&Name for this rule:")
        self._name = wx.TextCtrl(self.dialog)
        self._name.SetValue(source.name)
        self._name.SetName("Name for this rule")
        self._name.SetHelpText(settings_help.FILTER_HELP["rule_name"])
        grid.Add(self._name, 1, wx.EXPAND)

        label("&Title match:")
        self._kind = wx.Choice(self.dialog, choices=list(_KIND_LABELS))
        self._kind.SetName("Title match")
        self._kind.SetHelpText(settings_help.FILTER_HELP["rule_kind"])
        self._kind.SetSelection(
            _KIND_VALUES.index(source.pattern_kind) if source.pattern_kind in _KIND_VALUES else 1
        )
        grid.Add(self._kind, 1, wx.EXPAND)

        label("&Pattern:")
        self._pattern = wx.TextCtrl(self.dialog)
        self._pattern.SetValue(source.pattern)
        self._pattern.SetName("Pattern")
        self._pattern.SetHelpText(settings_help.FILTER_HELP["rule_pattern"])
        grid.Add(self._pattern, 1, wx.EXPAND)

        label("&Minimum length in minutes (0 = any):")
        self._duration = wx.SpinCtrl(self.dialog, min=0, max=1440)
        self._duration.SetValue(source.min_duration_minutes)
        self._duration.SetName("Minimum length in minutes")
        self._duration.SetHelpText(settings_help.FILTER_HELP["rule_duration"])
        grid.Add(self._duration, 1, wx.EXPAND)

        label("Match &when:")
        self._match_any = wx.Choice(
            self.dialog, choices=["Every test has to match", "Any one test is enough"]
        )
        self._match_any.SetName("Match when")
        self._match_any.SetHelpText(settings_help.FILTER_HELP["rule_match_any"])
        self._match_any.SetSelection(1 if source.match_any else 0)
        grid.Add(self._match_any, 1, wx.EXPAND)

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        root.Add(wx.StaticText(self.dialog, label="More test&s:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._tests = wx.ListBox(self.dialog, size=(-1, 90))
        self._tests.SetName("More tests")
        self._tests.SetHelpText(settings_help.FILTER_HELP["rule_tests"])
        root.Add(self._tests, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        test_row = wx.BoxSizer(wx.HORIZONTAL)
        add_test = wx.Button(self.dialog, label="&Add Test...")
        add_test.SetHelpText(settings_help.FILTER_HELP["rule_add_test"])
        edit_test = wx.Button(self.dialog, label="&Edit Test...")
        edit_test.SetHelpText(settings_help.FILTER_HELP["rule_edit_test"])
        remove_test = wx.Button(self.dialog, label="&Remove Test")
        remove_test.SetHelpText(settings_help.FILTER_HELP["rule_remove_test"])
        for button in (add_test, edit_test, remove_test):
            test_row.Add(button, 0, wx.RIGHT, 6)
        root.Add(test_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self._fill_tests()

        self._case = wx.CheckBox(self.dialog, label="&Capital letters have to match too")
        self._case.SetValue(source.case_sensitive)
        self._case.SetHelpText(settings_help.FILTER_HELP["rule_case"])
        root.Add(self._case, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._enabled = wx.CheckBox(self.dialog, label="This rule is switched &on")
        self._enabled.SetValue(source.enabled)
        self._enabled.SetHelpText(settings_help.FILTER_HELP["rule_enabled"])
        root.Add(self._enabled, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        try_btn = wx.Button(self.dialog, label="Tr&y It on Recent Episodes")
        try_btn.SetHelpText(settings_help.FILTER_HELP["rule_try"])
        root.Add(try_btn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        root.Add(wx.StaticText(self.dialog, label="Try it res&ult:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._trial = wx.TextCtrl(
            self.dialog, size=(440, 70), style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self._trial.SetName("Try it result")
        self._trial.SetHelpText(settings_help.FILTER_HELP["rule_try_result"])
        root.Add(self._trial, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "Save")
        ok_btn.SetHelpText("Keeps this rule in the filter. Nothing is applied until you save it.")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetHelpText("Leaves the rule as it was.")
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizerAndFit(root)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        add_test.Bind(wx.EVT_BUTTON, self._on_add_test)
        edit_test.Bind(wx.EVT_BUTTON, self._on_edit_test)
        remove_test.Bind(wx.EVT_BUTTON, self._on_remove_test)
        self._tests.Bind(wx.EVT_LISTBOX_DCLICK, self._on_edit_test)
        try_btn.Bind(wx.EVT_BUTTON, self._on_try)
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Save",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )

    # -- reading the form ----------------------------------------------------

    def _drafted(self) -> EpisodeFilterRule:
        """The rule the controls currently describe."""
        kind = _KIND_VALUES[max(0, self._kind.GetSelection())]
        return EpisodeFilterRule(
            name=self._name.GetValue().strip(),
            enabled=self._enabled.GetValue(),
            pattern_kind=kind,
            pattern=self._pattern.GetValue().strip(),
            case_sensitive=self._case.GetValue(),
            min_duration_minutes=int(self._duration.GetValue()),
            conditions=list(self._conditions),
            match_any=self._match_any.GetSelection() == 1,
        )

    # -- the tests -----------------------------------------------------------

    def _fill_tests(self, select: int = -1) -> None:
        rows = [describe_condition(condition) for condition in self._conditions]
        self._tests.Set(rows or ["No more tests. The title and length above are the whole rule."])
        if rows and 0 <= select < len(rows):
            self._tests.SetSelection(select)

    def _test_dialog(self, condition: FilterCondition | None) -> FilterCondition | None:
        from quill.ui.podcasts.episode_filter_test_dialog import EpisodeFilterTestDialog

        return EpisodeFilterTestDialog(
            self.dialog, condition=condition, announce_cb=self._announce
        ).show()

    def _selected_test(self) -> int:
        index = self._tests.GetSelection()
        return index if 0 <= index < len(self._conditions) else -1

    def _on_add_test(self, _event: object) -> None:
        made = self._test_dialog(None)
        if made is None:
            return
        self._conditions.append(made)
        self._fill_tests(select=len(self._conditions) - 1)
        self._tests.SetFocus()
        self._announce(f"Test added. {len(self._conditions)} more test(s).")

    def _on_edit_test(self, _event: object) -> None:
        index = self._selected_test()
        if index < 0:
            return
        made = self._test_dialog(self._conditions[index])
        if made is None:
            return
        self._conditions[index] = made
        self._fill_tests(select=index)
        self._announce("Test updated.")

    def _on_remove_test(self, _event: object) -> None:
        index = self._selected_test()
        if index < 0:
            return
        del self._conditions[index]
        self._fill_tests(select=min(index, len(self._conditions) - 1))
        self._announce(f"Test removed. {len(self._conditions)} more test(s) left.")

    def _on_try(self, _event: object) -> None:
        """Say what this rule, as written now, would catch. Changes nothing."""
        from quill.core.podcasts.episode_filters import newest_episodes, rule_matches
        from quill.core.podcasts.filter_suggestions import describe_trial

        draft = self._drafted()
        draft.enabled = True
        said = describe_trial(draft, newest_episodes(self._episodes), rule_matches)
        self._trial.SetValue(said)
        # The text box is not focused, so the reader would not say it.
        self._announce(said)

    def _refuse(self, message: str, focus: object) -> None:
        """Say why this rule cannot be saved, and put focus where the fix is.

        A validation message that dismisses back to the OK button makes
        somebody find the offending field again, which for a form read one
        control at a time is the expensive half of the correction.

        The message box is not *also* announced: the reader speaks a dialog's
        own text when it opens, and saying it twice is the over-announcement
        GATE-13 exists to stop.
        """
        from quill.ui.dialog_contract import show_message_box

        wx = self._wx
        show_message_box(message, TITLE, wx.OK | wx.ICON_WARNING, self.dialog, announce=None)
        try:
            focus.SetFocus()
        except Exception:  # noqa: BLE001 - focus is best-effort, the message is not
            pass

    def _on_ok(self, _event: object) -> None:
        draft = self._drafted()
        title_only = EpisodeFilterRule(pattern_kind=draft.pattern_kind, pattern=draft.pattern)
        error = title_only.pattern_error
        if error:
            self._refuse(
                f"That regular expression cannot be read: {error}. "
                "Fix it, or switch the title match to wildcards.",
                self._pattern,
            )
            return
        error = draft.pattern_error
        if error:
            self._refuse(
                f"One of the tests cannot be used: {error}. Edit or remove it.", self._tests
            )
            return
        if not draft.is_usable:
            self._refuse(
                "This rule asks nothing about an episode, so it would never match. "
                "Give it a title pattern, a minimum length, or another test.",
                self._pattern,
            )
            return
        self._result = draft
        self.dialog.EndModal(self._wx.ID_OK)

    # -- showing -------------------------------------------------------------

    def show(self) -> EpisodeFilterRule | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        # The name field, not the OK button: this is a form somebody opened to
        # fill in, and the first thing they type is what it is called.
        wx.CallAfter(self._name.SetFocus)
        try:
            if show_modal_dialog(self.dialog, TITLE, announce=self._announce) != wx.ID_OK:
                return None
            return self._result
        finally:
            self.dialog.Destroy()
