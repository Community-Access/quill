"""Episode Filters for one podcast: the rules, a dry run, and a gated save.

The window a listener opens when a podcast they follow also publishes
something they do not want. Five things are on it, in the order the decision
is actually made: the switch, the mode, the rules, **where the answer counts**,
and a **Preview** that says what those rules would do to the fifty newest
episodes already stored.

Four of its behaviours are load-bearing and none of them is obvious:

* **Preview runs against the draft even while the switch is off**, and while
  no scope is ticked. Previewing before activating is the only safe way to
  write a Keep-only rule, and a preview that agreed with you whenever the
  switch was off would agree right up until it mattered. This was the first
  defect device testing found in the feature it was ported from, and both
  halves are pinned by tests.
* **The scopes are eight real checkboxes**, not a check-list: a screen reader
  does not announce a check-list row's ticked state as you arrow past it, and
  that state is the entire content of these rows (A11Y-SR-1).
* **Save is gated, not merely validated.** Switched on with nothing switched on
  inside it, an unreadable regular expression, nowhere to apply, or a
  minimum-length rule against a feed that publishes no lengths are all
  *refused*, with the reason and the fix. Partial length coverage and any
  hiding scope are allowed but ask first -- the first with the exact count,
  the second naming the two ways back.
* **The Play Queue is the only thing that needs asking.** Every other surface
  consults the filter as it is drawn, so saving is already in force there. The
  queue is the one ordered list somebody built by hand, so it is changed once,
  when asked, and says exactly what it did.

Nothing in this window deletes an episode, and every message says so.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.podcasts import episode_filter_maintenance as maintenance
from quill.core.podcasts import episode_filters as filters
from quill.core.podcasts import settings_help
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_filters import (
    FILTER_MODES,
    FILTER_SCOPES,
    MODE_LABELS,
    SCOPE_LABELS,
    SCOPE_QUEUE,
    EpisodeFilterConfiguration,
)
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.dialog_contract import show_message_box

#: The title's stable opening; the podcast's name follows it. Answered by
#: prefix in ``core/podcasts/surface_help.py`` (GATE-CAST-HELP).
TITLE = "Episode Filters"

_MODE_CHOICES = tuple(MODE_LABELS[mode] for mode in FILTER_MODES)

__all__ = ["TITLE", "EpisodeFiltersWindow", "open_episode_filters"]


class EpisodeFiltersWindow:
    """Edits one podcast's rule set -- a peer window (qc.md Phase 4).

    Made once. Save stores the rules and the window stays open; Close (or
    Escape) leaves what is stored exactly as it was. Asked for again while it
    is showing the same podcast it is only raised, so a draft in progress
    survives; otherwise it is rebuilt from what is stored, for whichever
    podcast was asked about.
    """

    TITLE = TITLE
    MENU_TITLE = "Filter R&ules"

    def __init__(
        self,
        parent: object,
        *,
        library: PodcastLibrary,
        show: PodcastShow,
        announce_cb: Callable[[str], None] | None = None,
        playing: tuple[str, str] | None = None,
        suggestion: object = None,
        on_saved: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._panel: Any = None
        self.frame = wx.Frame(parent, title=TITLE, size=(660, 760))
        self.frame.SetMinSize((620, 620))
        self.load(
            library=library, show=show, playing=playing, suggestion=suggestion, on_saved=on_saved
        )
        self.frame.CentreOnParent()

    def load(
        self,
        *,
        library: PodcastLibrary,
        show: PodcastShow,
        playing: tuple[str, str] | None = None,
        suggestion: object = None,
        on_saved: Callable[[], None] | None = None,
    ) -> None:
        """Build the window's contents for *show*, from what is stored."""
        wx = self._wx
        self._on_saved = on_saved
        self._library = library
        self._show = show
        self._playing = playing
        #: A drafted rule from "Filter Episodes Like This" (a
        #: ``filter_suggestions.FilterSuggestion``), opened in the rule editor
        #: as soon as this window is up; ``None`` for the ordinary way in.
        self._suggestion = suggestion
        self._saved = False
        self._title = f"{TITLE} -- {show.title}"
        stored = maintenance.filter_for(library, show)
        # A draft, so Cancel genuinely leaves the stored rules alone -- rules
        # are mutable records and editing them in place would "cancel" into a
        # library that had already changed.
        self._draft: EpisodeFilterConfiguration = (
            stored.copy() if stored is not None else EpisodeFilterConfiguration()
        )

        self.frame.SetTitle(self._title)
        if self._panel is not None:
            self._panel.Destroy()
        self._panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self._panel,
            label=(
                f"Rules that decide what happens to {show.title}'s episodes, and "
                "where that answer counts. A filtered episode is never deleted: it "
                "keeps its played mark, its position, its downloaded file and its "
                "place in this podcast's list. Choose Filtered out in the episode "
                "list's filter to see whatever these rules are holding back."
            ),
        )
        intro.Wrap(580)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        self._notice: Any = None
        if maintenance.needs_review(library, show):
            # A status line, not an announcement: this may have been raised by
            # a background check hours ago, and the reader speaks a StaticText
            # when focus reaches it. Announcing it on open would be telling
            # somebody something they came here to read.
            notice = wx.StaticText(
                self._panel,
                label=(
                    "Needs review: a refresh found these rules filtering out every "
                    "single new episode. Nothing was lost. Saving clears this notice."
                ),
            )
            notice.Wrap(580)
            notice.SetHelpText(settings_help.FILTER_HELP["needs_review"])
            self._notice = notice
            root.Add(notice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._enabled = wx.CheckBox(self._panel, label="&Filter new episodes of this podcast")
        self._enabled.SetValue(self._draft.enabled)
        self._enabled.SetHelpText(settings_help.FILTER_HELP["enabled"])
        root.Add(self._enabled, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        root.Add(
            wx.StaticText(self._panel, label="&When a rule matches:"),
            0,
            wx.LEFT | wx.RIGHT,
            10,
        )
        self._mode = wx.Choice(self._panel, choices=list(_MODE_CHOICES))
        self._mode.SetName("When a rule matches")
        self._mode.SetHelpText(settings_help.FILTER_HELP["mode"])
        self._mode.SetSelection(
            FILTER_MODES.index(self._draft.mode) if self._draft.mode in FILTER_MODES else 0
        )
        root.Add(self._mode, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        root.Add(wx.StaticText(self._panel, label="&Rules:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._rules = wx.ListBox(self._panel, choices=[], style=wx.LB_SINGLE)
        self._rules.SetName("Rules")
        self._rules.SetHelpText(settings_help.FILTER_HELP["rules"])
        root.Add(self._rules, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        rule_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._add_btn = wx.Button(self._panel, label="&Add Rule...")
        self._add_btn.SetHelpText(settings_help.FILTER_HELP["add_rule"])
        self._edit_btn = wx.Button(self._panel, label="&Edit Rule...")
        self._edit_btn.SetHelpText(settings_help.FILTER_HELP["edit_rule"])
        self._toggle_btn = wx.Button(self._panel, label="Switch Rule &On or Off")
        self._toggle_btn.SetHelpText(settings_help.FILTER_HELP["toggle_rule"])
        self._delete_btn = wx.Button(self._panel, label="&Delete Rule")
        self._delete_btn.SetHelpText(settings_help.FILTER_HELP["delete_rule"])
        for button in (self._add_btn, self._edit_btn, self._toggle_btn, self._delete_btn):
            rule_buttons.Add(button, 0, wx.RIGHT, 6)
        root.Add(rule_buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Where the verdict counts: eight real checkboxes in a scrolled group,
        # not a wx.CheckListBox. A check-list *looks* like the right control
        # and is the wrong one -- screen readers do not announce a row's
        # checked state as you arrow past it, so the one fact each of these
        # rows exists to carry would be the one fact it did not say
        # (A11Y-SR-1). Eight Tab stops is the price, and it is the right price.
        root.Add(
            wx.StaticText(self._panel, label="W&here this applies:"), 0, wx.LEFT | wx.RIGHT, 10
        )
        scope_panel = wx.ScrolledWindow(self._panel, style=wx.VSCROLL | wx.BORDER_SIMPLE)
        scope_panel.SetScrollRate(0, 10)
        scope_sizer = wx.BoxSizer(wx.VERTICAL)
        self._scope_boxes: dict[str, object] = {}
        for scope in FILTER_SCOPES:
            box = wx.CheckBox(scope_panel, label=SCOPE_LABELS[scope])
            box.SetValue(scope in self._draft.scopes)
            box.SetHelpText(settings_help.FILTER_HELP["scopes"])
            scope_sizer.Add(box, 0, wx.EXPAND | wx.ALL, 4)
            self._scope_boxes[scope] = box
        scope_panel.SetSizer(scope_sizer)
        scope_panel.SetMinSize((-1, 180))
        root.Add(scope_panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        preview_row = wx.BoxSizer(wx.HORIZONTAL)
        self._preview_btn = wx.Button(self._panel, label="Pre&view")
        self._preview_btn.SetHelpText(settings_help.FILTER_HELP["preview"])
        preview_row.Add(self._preview_btn, 0, wx.RIGHT, 6)
        root.Add(preview_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        root.Add(wx.StaticText(self._panel, label="Preview resu&lts:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._preview_list = wx.ListBox(self._panel, choices=[], style=wx.LB_SINGLE)
        self._preview_list.SetName("Preview results")
        self._preview_list.SetHelpText(settings_help.FILTER_HELP["preview_results"])
        root.Add(self._preview_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        ok_btn = wx.Button(self._panel, label="Save")
        ok_btn.SetHelpText(
            "Saves these rules for this podcast. Every list you ticked takes "
            "effect at once, on episodes you already have as well as new ones; "
            "nothing is deleted. The Play Queue is the only thing not touched "
            "without asking, and saving asks about it separately."
        )
        cancel_btn = wx.Button(self._panel, label="Close")
        cancel_btn.SetHelpText(
            "Closes this window and returns to where you were. Anything not saved "
            "is left exactly as it was."
        )
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, cancel_btn, modeless=True)
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self._panel.SetSizer(root)
        self._add_btn.Bind(wx.EVT_BUTTON, self._on_add_rule)
        self._edit_btn.Bind(wx.EVT_BUTTON, self._on_edit_rule)
        self._toggle_btn.Bind(wx.EVT_BUTTON, self._on_toggle_rule)
        self._delete_btn.Bind(wx.EVT_BUTTON, self._on_delete_rule)
        self._preview_btn.Bind(wx.EVT_BUTTON, self._on_preview)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        self._fill_rules()
        self._sizer_for_frame()
        if self._suggestion is not None:
            wx.CallAfter(self._offer_suggestion)

    def _sizer_for_frame(self) -> None:
        sizer = self.frame.GetSizer()
        if sizer is None:
            sizer = self._wx.BoxSizer(self._wx.VERTICAL)
            self.frame.SetSizer(sizer)
        sizer.Clear()
        sizer.Add(self._panel, 1, self._wx.EXPAND)
        self.frame.Layout()

    def focus_target(self) -> Any:
        return self._rules if self._rules.GetCount() else self._enabled

    def menu_rows(self) -> list[tuple[str, Callable[[], None]]]:
        # A frame has no default button, so Save gets a key of its own.
        return [("&Save\tCtrl+S", lambda: self._on_ok(None))]

    def shows(self, show: PodcastShow) -> bool:
        """Whether this window is up, on *show*."""
        return bool(self.frame.IsShown()) and self._show.id == show.id

    # -- the rules list ------------------------------------------------------

    def _fill_rules(self, *, select: int = -1) -> None:
        """Rebuild the rules list, keeping (or moving) the selection.

        Each row is :func:`~quill.core.podcasts.episode_filters.describe_rule`
        -- name, state, then criteria -- so the list reads the same way it is
        spoken elsewhere, and a rule's on/off state arrives by the second word
        rather than after a clause about wildcards.
        """
        wanted = select if select >= 0 else self._rules.GetSelection()
        self._rules.Set([filters.describe_rule(rule) for rule in self._draft.rules])
        count = len(self._draft.rules)
        if count:
            self._rules.SetSelection(max(0, min(wanted if wanted >= 0 else 0, count - 1)))
        for button in (self._edit_btn, self._toggle_btn, self._delete_btn):
            button.Enable(bool(count))

    def _selected_index(self) -> int:
        index = self._rules.GetSelection()
        return index if 0 <= index < len(self._draft.rules) else -1

    def _sync_draft(self) -> None:
        """Fold the top-level controls into the draft before it is used.

        Called by Preview and by Save rather than bound to every control's
        change event: a draft that updated itself on each keystroke would need
        the preview list invalidating on each keystroke too, and a preview that
        silently goes stale is worse than one you press a button for.
        """
        self._draft.enabled = self._enabled.GetValue()
        self._draft.mode = FILTER_MODES[max(0, self._mode.GetSelection())]
        self._draft.scopes = {scope for scope, box in self._scope_boxes.items() if box.GetValue()}

    # -- rule verbs ----------------------------------------------------------

    def _rule_dialog(self, rule: object = None, *, intro: str = "") -> object:
        from quill.ui.podcasts.episode_filter_rule_dialog import EpisodeFilterRuleDialog

        return EpisodeFilterRuleDialog(
            self.frame,
            rule=rule,
            announce_cb=self._announce,
            episodes=self._show.episodes,
            intro=intro,
        ).show()

    def _offer_suggestion(self) -> None:
        """Open the rule editor on the drafted rule; add it if it is kept.

        Filtering is switched on in the draft with it -- the listener asked
        to filter episodes like this one -- but nothing is stored until Save,
        and the save gate and Preview are exactly as they always are.
        """
        suggestion = self._suggestion
        self._suggestion = None
        if suggestion is None:
            return
        drafted = self._rule_dialog(
            getattr(suggestion, "rule", None), intro=str(getattr(suggestion, "reason", ""))
        )
        if drafted is None:
            self._announce("No rule added.")
            return
        self._draft.rules.append(drafted)
        self._draft.enabled = True
        self._enabled.SetValue(True)
        self._fill_rules(select=len(self._draft.rules) - 1)
        self._announce(
            "Rule added and filtering switched on. Preview to check it, then Save to keep it."
        )

    def _on_add_rule(self, _event: object) -> None:
        drafted = self._rule_dialog()
        if drafted is None:
            return
        self._draft.rules.append(drafted)
        self._fill_rules(select=len(self._draft.rules) - 1)
        # The outcome, not the row: the reader speaks the row when selection
        # lands on it, and what it cannot say is that the list just grew.
        self._announce(f"Rule added. {len(self._draft.rules)} rule(s). Nothing saved yet.")

    def _on_edit_rule(self, _event: object) -> None:
        index = self._selected_index()
        if index < 0:
            return
        drafted = self._rule_dialog(self._draft.rules[index])
        if drafted is None:
            return
        self._draft.rules[index] = drafted
        self._fill_rules(select=index)
        self._announce("Rule updated. Nothing saved yet.")

    def _on_toggle_rule(self, _event: object) -> None:
        index = self._selected_index()
        if index < 0:
            return
        rule = self._draft.rules[index]
        rule.enabled = not rule.enabled
        self._fill_rules(select=index)
        state = "switched on" if rule.enabled else "switched off"
        self._announce(f"{filters.rule_name(rule)} {state}. Nothing saved yet.")

    def _on_delete_rule(self, _event: object) -> None:
        index = self._selected_index()
        if index < 0:
            return
        rule = self._draft.rules[index]
        wx = self._wx
        answer = show_message_box(
            f"Delete the rule {filters.rule_name(rule)}? This removes the rule only. "
            "No episode is deleted, and episodes it filtered out before stay out until "
            "you queue them yourself.",
            "Delete Rule",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.frame,
            announce=None,
        )
        if answer != wx.YES:
            return
        del self._draft.rules[index]
        self._fill_rules(select=min(index, len(self._draft.rules) - 1))
        self._announce(f"Rule deleted. {len(self._draft.rules)} rule(s) left. Nothing saved yet.")

    # -- preview -------------------------------------------------------------

    def _on_preview(self, _event: object) -> None:
        """A dry run over the newest stored episodes; changes nothing."""
        self._sync_draft()
        rows = filters.preview(self._draft, self._show.episodes)
        # Name the rule that decided it only when there is more than one to
        # choose between: with a single rule the name is a clause on every row
        # answering a question nobody has.
        with_reason = len(self._draft.usable_rules) > 1
        self._preview_list.Set([
            filters.describe_preview_row(row, with_reason=with_reason) for row in rows
        ])
        if rows:
            self._preview_list.SetSelection(0)
        # The summary is the whole reason the button exists: a list somebody
        # would have to arrow through to count is not an answer.
        self._announce(filters.preview_summary(rows))

    # -- saving --------------------------------------------------------------

    def _refuse(self, message: str) -> None:
        show_message_box(
            message, self._title, self._wx.OK | self._wx.ICON_WARNING, self.frame, announce=None
        )

    def _ask_apply_to_existing(self) -> int:
        """Save for new episodes only, save and apply once, or go back.

        Three answers rather than a checkbox, because the middle one reaches
        back over episodes somebody already triaged and that is not a thing to
        leave in whatever state it was in last time.

        ``NO_DEFAULT``, so Enter pressed reflexively answers **Save for new
        episodes only** -- the answer that changes nothing you already have.
        """
        wx = self._wx
        dialog = wx.MessageDialog(
            self.frame,
            f"Also take {self._show.title}'s matching episodes out of the Play "
            "Queue now?\n\n"
            "Everywhere else takes effect the moment you save. The Play Queue is "
            "the one list you built by hand, so it is only changed when you ask.\n\n"
            "It removes queue slots and nothing else: no episode is deleted, played "
            "marks, positions and downloads are untouched, and the episode playing "
            "right now keeps its place.",
            "Save Episode Filter",
            wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_QUESTION,
        )
        try:
            dialog.SetYesNoCancelLabels(
                "Save and &clear them from the queue",
                "Save, &leave the queue alone",
                "Cancel",
            )
        except Exception:  # noqa: BLE001 - labels are a nicety; the buttons work regardless
            pass
        try:
            return dialog.ShowModal()
        finally:
            dialog.Destroy()

    def _on_ok(self, _event: object) -> None:
        wx = self._wx
        self._sync_draft()
        assessment = filters.assess_save(self._draft, self._show.episodes)
        if not assessment.ok:
            self._refuse(assessment.blocked)
            return
        if assessment.confirm:
            answer = show_message_box(
                assessment.confirm,
                self._title,
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self.frame,
                announce=None,
            )
            if answer != wx.YES:
                return
        apply_existing = False
        # Only asked when the Play Queue is in scope and this podcast has
        # something queued. Every other surface asks the filter as it is
        # drawn, so saving is already in force there -- the queue is the one
        # ordered list somebody built by hand, and the one that is therefore
        # never rearranged without being asked.
        if self._draft.governs(SCOPE_QUEUE) and self._queued_here():
            answer = self._ask_apply_to_existing()
            if answer == wx.ID_CANCEL:
                return
            apply_existing = answer == wx.ID_YES
        self._commit(apply_existing=apply_existing)

    def _queued_here(self) -> bool:
        """Whether this podcast has anything in the Play Queue at all."""
        return any(item.show_id == self._show.id for item in self._library.queue)

    def _commit(self, *, apply_existing: bool) -> None:
        """Write the draft, optionally reach back once, and say what happened."""
        maintenance.set_filter(self._library, self._show, self._draft)
        # Reviewing and *saving* is what clears the warning: opening the window
        # proves somebody read the title bar, saving proves they decided.
        maintenance.clear_needs_review(self._library, self._show)
        self._saved = True
        if not apply_existing:
            self._announce(
                f"Filter saved for {self._show.title}. "
                f"{filters.describe_configuration(self._draft)}"
            )
            self._saved_and_open()
            return
        outcome = maintenance.apply_to_existing(
            self._library, self._show, self._draft, playing=self._playing
        )
        self._announce(
            filters.describe_apply_result(
                self._show.title, outcome.queue_removed, outcome.playing_kept
            )
        )
        self._saved_and_open()

    def _saved_and_open(self) -> None:
        """Saved: tell the caller, and stay open (a peer acts; it does not end)."""
        # What was stored is the draft object itself; go on editing a copy, so
        # Close after further changes still leaves the saved rules alone.
        self._draft = self._draft.copy()
        if self._notice is not None:
            self._notice.Hide()  # saving is what clears the review notice
            self._panel.Layout()
        if self._on_saved is not None:
            self._on_saved()


def open_episode_filters(
    host: Any,
    show: PodcastShow,
    *,
    library: PodcastLibrary,
    parent: object,
    on_saved: Callable[[], None] | None = None,
    playing: tuple[str, str] | None = None,
    suggestion: object = None,
    opener: Any = None,
) -> EpisodeFiltersWindow:
    """Open, or raise, the one Episode Filters window, on *show*."""
    from quill.ui.podcasts.peer_window import open_peer

    content = {
        "library": library,
        "show": show,
        "playing": playing,
        "suggestion": suggestion,
        "on_saved": on_saved,
    }
    existing = getattr(host, "_episode_filters_window", None)
    if (
        existing is not None
        and existing.frame
        and (suggestion is not None or not existing.shows(show))
    ):
        existing.load(**content)

    def _make(owner: Any) -> EpisodeFiltersWindow:
        return EpisodeFiltersWindow(parent, announce_cb=owner._announce, **content)

    window: EpisodeFiltersWindow = open_peer(host, "_episode_filters_window", _make, opener=opener)
    return window
