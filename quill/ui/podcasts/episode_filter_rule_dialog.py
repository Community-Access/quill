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

from collections.abc import Callable

from quill.core.podcasts import settings_help
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
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: EpisodeFilterRule | None = None
        source = rule or EpisodeFilterRule(name="", pattern_kind=PATTERN_WILDCARD)

        self.dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "A rule can match on the episode title, on how long it is, or on "
                "both -- both have to match. Rules never delete anything."
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

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        self._case = wx.CheckBox(self.dialog, label="&Capital letters have to match too")
        self._case.SetValue(source.case_sensitive)
        self._case.SetHelpText(settings_help.FILTER_HELP["rule_case"])
        root.Add(self._case, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._enabled = wx.CheckBox(self.dialog, label="This rule is switched &on")
        self._enabled.SetValue(source.enabled)
        self._enabled.SetHelpText(settings_help.FILTER_HELP["rule_enabled"])
        root.Add(self._enabled, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

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
        )

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
        error = draft.pattern_error
        if error:
            self._refuse(
                f"That regular expression cannot be read: {error}. "
                "Fix it, or switch the title match to wildcards.",
                self._pattern,
            )
            return
        if not draft.has_title_criterion and not draft.has_duration_criterion:
            self._refuse(
                "This rule asks nothing about an episode, so it would never match. "
                "Give it a title pattern, a minimum length, or both.",
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
