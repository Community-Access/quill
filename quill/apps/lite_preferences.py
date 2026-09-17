"""The Preferences window: every setting QuillLite has, in one place.

Split from :mod:`quill.apps.lite_dialogs` because it is the only dialog that
edits state rather than answering a question, and because it is the one window
whose *contents* are the product's settings model -- it grows when the model
does, and the other dialogs do not.

Everything on the View menu is here too -- theme, wrap, the editor font -- because
a Preferences window that answers half the question is a Preferences window
people stop opening. But three settings live *only* here, and they are the reason
it exists: what Control N creates, how often unsaved work is copied aside,
whether last session's documents reopen, whether spelling is checked as you
type, and whether abbreviations and taught words come from QuillLite's own
lists or QUILL's shared ones.
Before this they could be changed only by hand-editing ``settings.json``, which
is not a setting anyone has.

**The feature profile is offered here too**, at the top, because Preferences is
where somebody goes to make the app theirs and "make this Notepad" is the
largest single thing they can say. It was reachable only from Tools > Customize
Features, behind a name that describes a mechanism rather than a wish: a person
who wants the small editor does not know they are looking for a customization
dialog. The Choice here is the same four profiles, reading back "Custom" when
the areas match none of them, and it shows the same computed impact
(:func:`~quill.core.app_features.profile_impact`) in the same read-only box, so
the two windows can never describe one profile differently. The checklist stays
where it is: this window offers the whole answers, and the per-area picking is
still Customize Features' job.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, NamedTuple

import wx

from quill.apps.lite_dialogs import _stack
from quill.core.action_feedback import ACTION_FEEDBACK_LABELS
from quill.core.action_feedback import coerce as coerce_feedback
from quill.core.app_features import (
    AppArea,
    AppFeatureSettings,
    AppProfile,
    apply_profile,
    profile_impact,
    profile_summary,
)
from quill.core.structure_announce import HEADING_POSITION_LABELS, HEADING_POSITIONS
from quill.ui.app_features_dialog import CUSTOM_PROFILE, SETTING_WORDS
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog

__all__ = ["PreferencesResult", "edit_preferences"]

#: Uniform padding, matching the other dialogs. One number, so nothing drifts.
_PAD = 8

#: How wide the profile impact box is, and how many lines of it are on screen
#: before it scrolls. Matched to the Customize Features dialog's, because it is
#: the same text and two different shapes of the same paragraph is a thing
#: somebody notices and cannot explain.
_IMPACT_WIDTH = 560
_IMPACT_LINES = 7

#: What the impact box says when the areas match no profile. The same words the
#: Customize Features dialog uses, for the same reason.
_CUSTOM_DESCRIPTION = (
    "Your own mix of features, picked one at a time in Tools, Customize "
    "Features. Choosing a profile above replaces it; leaving this alone keeps "
    "it exactly as it is."
)

_PROFILE_HELP = (
    "A named starting point for which parts of the app exist at all. Choosing "
    "one here does everything the Customize Features checklist would do, in one "
    "go, and the box below says exactly what it would change. Leave it on "
    "Custom to keep the features you have."
)


class PreferencesResult(NamedTuple):
    """What the window changed: ordinary settings, feature areas, or neither.

    Two flags rather than one, because they are saved to different files and
    cost different things: settings are re-applied to the open documents, and a
    changed feature set means every window's menu bar has to be built again.
    """

    changed: bool
    features_changed: bool


def edit_preferences(
    parent: wx.Window,
    settings: Any,
    *,
    features: AppFeatureSettings | None = None,
    areas: Sequence[AppArea] = (),
    profiles: Sequence[AppProfile] = (),
    announce: Callable[[str], None] | None = None,
) -> PreferencesResult:
    """Edit the settings that have no menu item of their own.

    Everything on the View menu -- theme, wrap, text size -- is here too, because
    a Preferences window that answers half the question is a Preferences window
    people stop opening. But two settings live *only* here, and they are the
    reason it exists: what Ctrl+N creates, and how often unsaved work is copied
    aside. Before this they could be changed only by hand-editing settings.json,
    which is not a setting anyone has.

    The dialog mutates *settings* in place and reports whether anything moved, so
    the caller saves and re-applies exactly once.

    *features*, *areas* and *profiles* are optional and arrive together: given
    all three, the window grows a profile Choice that can switch whole areas of
    the app on and off in one move, and the second half of
    :class:`PreferencesResult` says whether it did. Given none of them the
    window is exactly what it was.
    """
    dialog = wx.Dialog(parent, title="Preferences", style=wx.DEFAULT_DIALOG_STYLE)
    root = wx.BoxSizer(wx.VERTICAL)

    profile_row = _ProfileRow(dialog, root, features, areas, profiles, settings, announce)

    mode_label = wx.StaticText(dialog, label="&New documents are:")
    mode_choice = wx.Choice(dialog, choices=["Plain text", "Rich text"])
    set_accessible_name(mode_choice, "New documents are")
    mode_choice.SetHelpText("What Control N creates. New Plain Text and New Rich Text ignore this.")
    mode_choice.SetSelection(1 if settings.default_mode == "rich" else 0)
    _stack(root, mode_label, mode_choice)

    def _profile_claimed(values: dict[str, object]) -> None:
        """Move the controls a profile claims, rather than overruling them later.

        Notepad does not only mean "these menus": it means Ctrl+N makes a plain
        text file. The alternative -- writing the profile's settings behind the
        window on OK -- loses either way round: apply them first and the New
        documents Choice, still showing what it showed on open, writes the old
        answer back over them; apply them last and a user who deliberately set
        rich text in the same visit is overruled by a profile they picked
        first. Moving the control instead makes the claim visible while the
        window is still open, and leaves the last word with whoever types last.
        """
        mode = values.get("default_mode")
        if mode in ("plain", "rich"):
            mode_choice.SetSelection(1 if mode == "rich" else 0)

    profile_row.on_settings = _profile_claimed

    theme_label = wx.StaticText(dialog, label="&Theme:")
    theme_choice = wx.Choice(dialog, choices=["Dark", "Follow the system"])
    set_accessible_name(theme_choice, "Theme")
    theme_choice.SetHelpText(
        "Dark is the default. It changes the view only and is never saved into your documents."
    )
    theme_choice.SetSelection(0 if settings.theme == "dark" else 1)
    _stack(root, theme_label, theme_choice)

    # &R rather than &t: Theme above already claims T, and Windows *cycles*
    # focus between two controls with the same access key instead of pressing
    # either, so one of the pair silently cannot be reached (GATE-14).
    restore = wx.CheckBox(dialog, label="&Reopen the documents I had open last time")
    restore.SetHelpText(
        "Reopen last session's files, in the same numbered order. Different from "
        "recovering unsaved work, which happens whether this is on or not."
    )
    restore.SetValue(bool(settings.restore_session))
    root.Add(restore, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)

    # Beside Reopen last session's documents, because the two together are the
    # whole answer to "what do I get when I start?" -- and somebody turning one
    # off is often reaching for the other.
    blank = wx.CheckBox(dialog, label="Start with a &blank document")
    blank.SetHelpText(
        "On: a new Untitled document is waiting when the app opens, the way "
        "Notepad and WordPad do it. Off: the app opens with nothing, and Control "
        "N or Open makes the first document -- which is what you want if you "
        "always open an existing file and were closing an empty one every time. "
        "Files you open by double-clicking, last session's documents and "
        "recovered work all still appear either way."
    )
    blank.SetValue(bool(getattr(settings, "open_blank_document_at_startup", True)))
    root.Add(blank, 0, wx.LEFT | wx.RIGHT, _PAD)

    share = wx.CheckBox(dialog, label="Share QUILL's abbre&viation library")
    share.SetHelpText(
        "Off: abbreviations are QuillLite's own. On: read and write the same "
        "library QUILL and Quill Inkwell use, so an abbreviation added in any of "
        "them works in all of them. Turning this on creates a QUILL data folder "
        "if you do not already have one."
    )
    share.SetValue(bool(settings.share_quill_abbreviations))
    root.Add(share, 0, wx.LEFT | wx.RIGHT, _PAD)

    # Beside the abbreviation switch on purpose: they are the same decision
    # asked twice, and two switches that behave differently would be two
    # switches to remember.
    share_dict = wx.CheckBox(dialog, label="Share QUILL's &dictionary of taught words")
    share_dict.SetHelpText(
        "Off: words you teach the spell checker are QuillLite's own. On: read "
        "and write the same dictionary QUILL uses, so a word taught in either "
        "is known to both. Turning this on creates a QUILL data folder if you "
        "do not already have one."
    )
    share_dict.SetValue(bool(settings.share_quill_dictionary))
    root.Add(share_dict, 0, wx.LEFT | wx.RIGHT, _PAD)

    # Beside the two sharing switches because it is the third question of the
    # same kind -- what QuillLite keeps, and where. Off by default, and the
    # help text says plainly what "everything" means rather than selling the
    # feature: somebody turning this on should know what they are turning on.
    keep_clips = wx.CheckBox(dialog, label="&Keep everything I copy in the clip library")
    keep_clips.SetHelpText(
        "Off: the clip library holds only what you put there with Keep Clip. "
        "On: every piece of text you copy or cut inside a QuillLite document is "
        "added to it automatically, up to the last two hundred, and Recent "
        "Clips offers them all. That includes anything you had pasted into a "
        "document and copied back out -- a password, a licence key, a private "
        "address -- and it is written to a file in QuillLite's data folder. It "
        "never sees what you copy in other programs."
    )
    keep_clips.SetValue(bool(getattr(settings, "clip_library_autocapture", False)))
    root.Add(keep_clips, 0, wx.LEFT | wx.RIGHT, _PAD)

    # &U, because every other letter in "Look for updates" is spoken for in
    # this window and Windows cycles focus between two controls with the same
    # access key rather than pressing either (GATE-14).
    updates = wx.CheckBox(dialog, label="Look for &updates when QuillLite starts")
    updates.SetHelpText(
        "Once a day, when the app opens, ask GitHub whether a newer QuillLite "
        "has been published. Nothing is said unless there is one, and nothing "
        "is downloaded or installed without being asked -- a new version shows "
        "you what changed and offers it. Off means Check for Updates on the "
        "Help menu is the only check that ever runs."
    )
    updates.SetValue(bool(getattr(settings, "check_updates_on_launch", True)))
    root.Add(updates, 0, wx.LEFT | wx.RIGHT, _PAD)

    spell_typing = wx.CheckBox(dialog, label="Check &spelling as I type")
    spell_typing.SetHelpText(
        "Report a misspelling in the status bar shortly after you finish a "
        "word. Never in a source or configuration file, whatever this says: "
        "every identifier in one would be a false alarm. F7 reviews the whole "
        "document either way."
    )
    spell_typing.SetValue(bool(settings.spell_check_while_typing))
    root.Add(spell_typing, 0, wx.LEFT | wx.RIGHT, _PAD)

    # The two feedback choosers are built from ACTION_FEEDBACK_LABELS rather
    # than from four typed strings, so this pane and QUILL's cannot describe the
    # same four modes in different words -- which would read as two settings.
    feedback_values = [mode for mode, _label in ACTION_FEEDBACK_LABELS]
    feedback_words = [label for _mode, label in ACTION_FEEDBACK_LABELS]

    def _feedback_index(value: object) -> int:
        return feedback_values.index(coerce_feedback(value))

    action_label = wx.StaticText(dialog, label="When a command does something, &give me:")
    action_choice = wx.Choice(dialog, choices=feedback_words)
    set_accessible_name(action_choice, "When a command does something, give me")
    action_choice.SetHelpText(
        "How a copy, paste, undo or started selection reports back. Play a "
        "sound is what the app has always done. Speak the action says the word "
        "instead, which is what you want before you have learned the tones. A "
        "command that has no tone in the sound pack speaks either way, and a "
        "command that could not do what you asked always says so in words."
    )
    action_choice.SetSelection(_feedback_index(getattr(settings, "action_feedback", "sound")))
    _stack(root, action_label, action_choice)

    miss_label = wx.StaticText(dialog, label="When a search &misses:")
    miss_choice = wx.Choice(dialog, choices=feedback_words)
    set_accessible_name(miss_choice, "When a search misses")
    miss_choice.SetHelpText(
        "Asked separately from the setting above because F3 is pressed in runs: "
        "hearing Not found spoken on every press is the fastest way to end up "
        "turning speech off. The status bar carries the words whichever you "
        "pick, so nothing is lost by choosing the tone."
    )
    miss_choice.SetSelection(_feedback_index(getattr(settings, "find_not_found_feedback", "sound")))
    _stack(root, miss_label, miss_choice)

    heading_words = [HEADING_POSITION_LABELS[key] for key in HEADING_POSITIONS]
    heading_label = wx.StaticText(dialog, label="Say a &heading's level:")
    heading_choice = wx.Choice(dialog, choices=heading_words)
    set_accessible_name(heading_choice, "Say a heading's level")
    heading_choice.SetHelpText(
        "Where the level goes relative to the heading itself. Before the text "
        "is one sentence QuillLite says on its own -- Heading 2, Installing -- "
        "and it is the one that survives a jump: pressing Control Home or "
        "landing on a search hit makes a screen reader cancel whatever it was "
        "about to say, and a level waiting its turn behind that is never heard. "
        "After the text lets your reader read the line and adds the level "
        "behind it, which is quieter on ordinary line-by-line reading."
    )
    heading_choice.SetSelection(
        HEADING_POSITIONS.index(
            "after"
            if str(getattr(settings, "heading_announce_position", "before")) == "after"
            else "before"
        )
    )
    _stack(root, heading_label, heading_choice)

    wrap_find = wx.CheckBox(dialog, label="Searching carries on from the other &end")
    wrap_find.SetHelpText(
        "On: Find Next reaching the end of the document starts again at the "
        "top. Off: it stops and tells you which end you are at, so you know to "
        "go to the other one and press again rather than that the word is "
        "absent."
    )
    wrap_find.SetValue(bool(getattr(settings, "wrap_find", True)))
    root.Add(wrap_find, 0, wx.LEFT | wx.RIGHT, _PAD)

    wrap = wx.CheckBox(dialog, label="&Wrap long lines to the window")
    wrap.SetHelpText("When off, long lines run past the right edge and scroll instead.")
    wrap.SetValue(bool(settings.word_wrap))
    root.Add(wrap, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)

    autosave_label = wx.StaticText(dialog, label="&Copy unsaved work aside every (seconds):")
    autosave = wx.SpinCtrl(dialog, min=15, max=600, initial=int(settings.autosave_seconds))
    set_accessible_name(autosave, "Copy unsaved work aside every, seconds")
    autosave.SetHelpText(
        "How often a modified document is copied to the recovery folder. The copy "
        "is beside your file, never over it, and is removed when you save."
    )
    _stack(root, autosave_label, autosave)

    font_row = wx.BoxSizer(wx.HORIZONTAL)
    font_label = wx.StaticText(dialog, label="Editor &font:")
    chosen = {"name": settings.font_name, "size": int(settings.font_size)}
    font_field = wx.TextCtrl(dialog, value=_font_summary(chosen), style=wx.TE_READONLY)
    set_accessible_name(font_field, "Editor font")
    font_field.SetHelpText(
        "The face and size the editor draws in. Change Font opens the chooser; "
        "this box reads back whatever you pick."
    )
    # "Change Font...", not "Choose...". A button is announced on its own -- the
    # label above it is not read with it -- so "Choose button" was a button that
    # named no noun, and the only way to find out what it chose was to press it
    # and listen to the dialog that opened.
    choose_btn = wx.Button(dialog, label="C&hange Font...")
    choose_btn.SetHelpText("Open the font chooser and pick a face and size for the editor.")
    font_row.Add(font_field, 1, wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, _PAD)
    font_row.Add(choose_btn, 0)
    root.Add(font_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
    root.Add(font_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

    def _pick_font(_event: wx.CommandEvent) -> None:
        data = wx.FontData()
        data.SetInitialFont(
            wx.Font(
                chosen["size"],
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                faceName=str(chosen["name"]),
            )
        )
        with wx.FontDialog(dialog, data) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            font = picker.GetFontData().GetChosenFont()
        chosen["name"], chosen["size"] = font.GetFaceName(), font.GetPointSize()
        # The read-out is an unfocused label change, which is exactly what a
        # screen reader does *not* announce -- so the caller's announce hook
        # says it instead (GATE-12's cure, not GATE-13's fault).
        font_field.SetValue(_font_summary(chosen))
        if announce is not None:
            announce(_font_summary(chosen))

    choose_btn.Bind(wx.EVT_BUTTON, _pick_font)

    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)
    dialog.SetSizerAndFit(root)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    mode_choice.SetFocus()
    try:
        if show_modal_dialog(dialog, "Preferences") != wx.ID_OK:
            return PreferencesResult(False, False)
        features_changed = profile_row.apply()
        before = (
            settings.default_mode,
            settings.theme,
            settings.word_wrap,
            settings.autosave_seconds,
            settings.font_name,
            settings.font_size,
            settings.restore_session,
            settings.share_quill_abbreviations,
            settings.share_quill_dictionary,
            getattr(settings, "clip_library_autocapture", False),
            settings.spell_check_while_typing,
            settings.open_blank_document_at_startup,
            getattr(settings, "check_updates_on_launch", True),
            getattr(settings, "action_feedback", "sound"),
            getattr(settings, "find_not_found_feedback", "sound"),
            getattr(settings, "wrap_find", True),
        )
        settings.default_mode = "rich" if mode_choice.GetSelection() == 1 else "plain"
        settings.theme = "dark" if theme_choice.GetSelection() == 0 else "system"
        settings.word_wrap = bool(wrap.GetValue())
        settings.restore_session = bool(restore.GetValue())
        settings.share_quill_abbreviations = bool(share.GetValue())
        settings.share_quill_dictionary = bool(share_dict.GetValue())
        settings.clip_library_autocapture = bool(keep_clips.GetValue())
        settings.spell_check_while_typing = bool(spell_typing.GetValue())
        settings.open_blank_document_at_startup = bool(blank.GetValue())
        settings.check_updates_on_launch = bool(updates.GetValue())
        settings.autosave_seconds = int(autosave.GetValue())
        settings.action_feedback = str(feedback_values[action_choice.GetSelection()])
        settings.find_not_found_feedback = str(feedback_values[miss_choice.GetSelection()])
        settings.wrap_find = bool(wrap_find.GetValue())
        settings.heading_announce_position = HEADING_POSITIONS[
            max(0, heading_choice.GetSelection())
        ]
        settings.font_name = str(chosen["name"])
        settings.font_size = int(chosen["size"])
        settings.normalized()
        return PreferencesResult(
            features_changed
            or before
            != (
                settings.default_mode,
                settings.theme,
                settings.word_wrap,
                settings.autosave_seconds,
                settings.font_name,
                settings.font_size,
                settings.restore_session,
                settings.share_quill_abbreviations,
                settings.share_quill_dictionary,
                settings.clip_library_autocapture,
                settings.spell_check_while_typing,
                settings.open_blank_document_at_startup,
                settings.check_updates_on_launch,
                settings.action_feedback,
                settings.find_not_found_feedback,
                settings.wrap_find,
            ),
            features_changed,
        )
    finally:
        dialog.Destroy()


class _ProfileRow:
    """The feature-profile Choice, its impact box, and what OK does with them.

    A class rather than a closure because it owns three questions that have to
    stay in step: which profile the current areas match, what the box should
    say, and whether OK has anything to write. An app that passes no features
    gets an inert instance that builds nothing and applies nothing, so the one
    caller needs no branch.
    """

    def __init__(
        self,
        dialog: wx.Dialog,
        root: wx.Sizer,
        features: AppFeatureSettings | None,
        areas: Sequence[AppArea],
        profiles: Sequence[AppProfile],
        settings: Any,
        announce: Callable[[str], None] | None,
    ) -> None:
        self._features = features
        self._areas = list(areas)
        self._profiles = list(profiles)
        self._settings = settings
        self._announce = announce
        #: Called with a chosen profile's settings pairs, so the window can move
        #: the controls that show them. Set by the caller once those controls
        #: exist; a profile that claims nothing never calls it.
        self.on_settings: Callable[[dict[str, object]], None] | None = None
        self._live = bool(features is not None and self._areas and self._profiles)
        if not self._live:
            return

        label = wx.StaticText(dialog, label="Feature pro&file:")
        self.choice = wx.Choice(dialog, choices=[p.name for p in self._profiles] + [CUSTOM_PROFILE])
        set_accessible_name(self.choice, "Feature profile")
        # Inline at the construction site, which is the only place the help
        # audit can see it. _show replaces it with this plus the selected
        # profile's own impact, so F1 answers "what is this one?" as well.
        self.choice.SetHelpText(_PROFILE_HELP)
        _stack(root, label, self.choice)
        # Read-only, multi-line and in the tab ring, exactly as in Customize
        # Features: a static label is not reachable by a screen reader's arrow
        # keys, and this is a paragraph, not a caption.
        self.impact = wx.TextCtrl(
            dialog,
            value="",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP,
            size=(_IMPACT_WIDTH, dialog.GetCharHeight() * _IMPACT_LINES),
        )
        set_accessible_name(self.impact, "What this profile does")
        self.impact.SetHelpText(
            "What the profile above would change: which parts of the app it "
            "keeps, which it removes, and anything else it sets."
        )
        root.Add(self.impact, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)
        self.choice.Bind(wx.EVT_CHOICE, lambda _e: self._on_choice())
        self._select_matching()

    # -- state ------------------------------------------------------------ #

    def _select_matching(self) -> None:
        """Point the Choice at the profile the current areas are, or Custom."""
        assert self._features is not None
        for index, profile in enumerate(self._profiles):
            if self._features.matches_profile(profile, self._areas, self._settings):
                self.choice.SetSelection(index)
                self._show()
                return
        self.choice.SetSelection(len(self._profiles))
        self._show()

    def _chosen(self) -> AppProfile | None:
        index = self.choice.GetSelection()
        if 0 <= index < len(self._profiles):
            return self._profiles[index]
        return None

    def _show(self) -> None:
        profile = self._chosen()
        text = (
            profile_impact(profile, self._areas, SETTING_WORDS)
            if profile is not None
            else _CUSTOM_DESCRIPTION
        )
        self.impact.SetValue(text)
        self.choice.SetHelpText(f"{_PROFILE_HELP} {' '.join(text.split())}")

    def _on_choice(self) -> None:
        """Update the box, and say the one-line version.

        The box is an unfocused control whose text just changed, which is
        precisely what a screen reader does not read (GATE-12); the profile's
        *name* is what it does read as you arrow, so what gets spoken is the
        outcome and not the name again (GATE-13). Nothing is applied yet --
        this window has an OK button and it means it.
        """
        self._show()
        profile = self._chosen()
        if profile is not None and profile.settings and self.on_settings is not None:
            self.on_settings(dict(profile.settings))
        if self._announce is None:
            return
        if profile is None:
            self._announce("Custom: the features you already have. Nothing will change.")
            return
        self._announce(
            profile_summary(profile, self._areas, SETTING_WORDS)
            + " Nothing is applied until you press OK."
        )

    # -- OK ---------------------------------------------------------------- #

    def apply(self) -> bool:
        """Write the chosen profile into the feature settings. True if it moved.

        Custom applies nothing at all -- it is what the Choice reads when the
        areas are somebody's own mix, and treating it as an instruction would
        make "leave my features alone" impossible to express.

        Areas only. Whatever else a profile claims has already been put into the
        controls that show it (see ``on_settings``), and those controls are what
        the window writes -- so the settings half is applied exactly once, by
        the code that owns it, and is visible before it happens.
        """
        if not self._live:
            return False
        assert self._features is not None
        profile = self._chosen()
        if profile is None:
            return False
        # Compared over the areas alone: the settings half is the controls'
        # business by now, and a profile whose only outstanding difference is a
        # setting somebody has since changed back has still not moved an area.
        if self._features.matches_profile(profile, self._areas):
            return False
        apply_profile(self._features, profile, self._areas)
        return True


def _font_summary(chosen: dict[str, Any]) -> str:
    """How the font read-out reads: "Consolas, 12 point" or "System default, 12 point"."""
    name = str(chosen["name"]).strip() or "System default"
    return f"{name}, {int(chosen['size'])} point"
