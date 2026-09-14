"""Customize Features dialog for the standalone apps.

One checkbox per switchable app area, each with a short description. Unchecking
an area turns it off; the app omits that area's menu the next time it launches.
Shared by Quill Radio, Quill Weather and QuillLite, which is why the areas and
the profiles arrive as arguments and nothing about any one app is written here.
wx lives only here; the state is the wx-free ``core/app_features`` model the
caller passes in and saves.

Two things were added in 2026-09 after QuillLite's list reached seventeen
entries, and both are QUILL's own answers to the same problem in
``quill/core/feature_catalog.py``:

**A search box, because a list you walk is a list you pay for.** Seventeen
checkboxes each with a paragraph under it is a long way to Tab, and a listener
pays that cost on every visit whether or not the thing they came for is near the
top. Typing filters the list to what matches -- the area's name, its
description, or its id -- and a count is announced so the number of things left
is a fact rather than something to count by arrowing. Down from the search box
lands on the first surviving checkbox, which is the idiom every filtered list on
Windows already uses.

**Profiles, because "the small one" is a real request.** A profile is a named
set of areas to switch off (:class:`~quill.core.app_features.AppProfile`).
Applying one ticks and unticks every box and then the boxes are the truth again:
there is no mode to escape from, and the next change is an ordinary per-area
override. The Choice reads back which profile the current boxes match, or
"Custom" when they match none, so the control answers "what am I on?" as well as
"what could I be on?". An app that passes no profiles gets no profile row at
all -- Radio and Weather are unchanged by any of this.

**Choosing a profile changes the boxes there and then.** It used to take a
second step -- pick the profile, then press Use Profile -- and the step was
invisible: a user who chose Notepad, read the description that appeared under
it and pressed Save got their old feature set back and a Format menu they had
just been told would be gone. Nothing announced the omission, because nothing
had happened. So the Choice now applies as you move through it, and **Custom**
is a real destination rather than only a readback: selecting it puts every box
back to what it was when the dialog opened, which is the undo for an arrow
press somebody did not mean. Nothing reaches disk until Save either way.

**Every profile's full impact is on screen, in a box you can read.** The
paragraph ``AppProfile`` has always carried says what a profile *is*; under it,
computed from the areas themselves so it cannot drift
(:func:`~quill.core.app_features.profile_impact`), is what it *does* -- which
areas it keeps, which it removes, and what else it changes. It lives in a
read-only multi-line text control rather than a static label on purpose: a
label is not in the tab ring and cannot be arrowed through, so on a
seventeen-area profile it was a paragraph a screen-reader user could hear only
as one uninterruptible block, if at all. It is the Choice's **help text** too,
so F1 answers "what is this one?" wherever you are.

Spoken, though, is the *one-line* version
(:func:`~quill.core.app_features.profile_summary`): how many areas survive and
what else moved. A reader already says the profile's name as you arrow onto it,
and a paragraph spoken over that on every arrow press is what GATE-13 exists to
stop -- but the boxes changing behind an unfocused control is exactly what it
cannot know, so silence is not an option either.

**A profile may also carry settings**, and the caller opts in by passing
``app_settings``. Some names promise more than a list of menus can express:
"Notepad" means the thing you type in is plain text, not merely that the Format
menu is gone. Those changes are announced by name when the profile is applied,
because they are the part of the change the user is not looking at -- a Ctrl+N
that quietly starts making something else is a thing you find out one document
later.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from quill.core.app_features import (
    AppArea,
    AppFeatureSettings,
    AppProfile,
    apply_profile_settings,
    profile_impact,
    profile_summary,
)
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

__all__ = [
    "CUSTOM_PROFILE",
    "SETTING_WORDS",
    "AppFeaturesDialog",
    "matching_areas",
]

#: What the profile Choice says when the boxes match no profile. Not an error
#: and not a warning: hand-picking areas is the whole point of the checklist,
#: and a profile is only ever a starting point for it.
CUSTOM_PROFILE = "Custom"

#: What Custom *means*, so the one entry in the list without a description of
#: its own still has one. Reassurance rather than a definition: a reader who has
#: just heard "Custom" where they expected "Notepad" should be told that is a
#: normal place to be, not left to wonder what they broke.
_CUSTOM_DESCRIPTION = (
    "Your own mix. You get this as soon as you tick or untick anything yourself, "
    "and it is a perfectly good place to stay -- picking your own is what the "
    "list below is for."
)

#: The part of the Choice's help that is true whichever profile is selected. The
#: selected profile's own description is appended, so F1 answers both "what is
#: this control" and "what is this one".
_PROFILE_HELP = (
    "A named starting point. Choosing one ticks and unticks every box below "
    "straight away, and Custom puts them back to how you found them. After that "
    "the boxes are the truth, so you can change any one of them without having "
    "to leave the profile first. Nothing is saved until you press Save."
)

#: Lines of the read-only impact box. Tall enough for the longest shipped
#: profile's four blocks without scrolling, short enough that the checkbox list
#: below it is still on screen.
_IMPACT_LINES = 7

#: The dialog stops growing here and scrolls instead. Seventeen areas with a
#: paragraph each is taller than a laptop screen.
_MAX_HEIGHT = 640

#: Pixels per scroll step in the area list.
_SCROLL_STEP = 12

#: How wide the profile-impact box is. Wide enough that most lines do not wrap,
#: narrow enough that the dialog does not open wider than the window behind it.
#: It used to size the per-checkbox description hints too; those moved into F1
#: on 2026-09-12, because a fixed wrap width inside a scrolling list is a
#: sentence that gets cut off.
_HINT_WRAP = 560

#: How a profile's settings are said out loud. Keyed by attribute name, because
#: the value alone ("plain") is not a sentence and the attribute alone
#: ("default_mode") is not English. A setting with no entry here is applied
#: silently rather than announced as a variable name.
#:
#: Public, because Preferences offers the same profiles from its own window and
#: has to say the same words about them: two descriptions of one profile that
#: disagreed would be worse than either.
SETTING_WORDS: dict[str, str] = {
    "default_mode": "New documents will be {value} text.",
}

#: The historical spelling, kept so nothing that imported it breaks.
_SETTING_WORDS = SETTING_WORDS


class _PendingSettings:
    """The app's settings as they *would* be with one profile applied.

    A read-only overlay, so the profile readback can compare against a state
    nothing has been written into yet. Cheaper and safer than applying the
    settings early and undoing them on Cancel, which is the version of this that
    leaves a user's Ctrl+N rewritten because they pressed Escape.
    """

    __slots__ = ("_base", "_overrides")

    def __init__(self, base: object, profile: AppProfile) -> None:
        self._base = base
        self._overrides = dict(profile.settings)

    def __getattr__(self, name: str) -> object:
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._base, name)


def matching_areas(areas: Sequence[AppArea], query: str) -> list[AppArea]:
    """The areas *query* matches, in the order they were declared.

    Every word has to appear somewhere in the area's label, description or id,
    so "line spell" finds nothing and "spell dictionary" finds spell check.
    Matching the description as well as the label is what makes a box findable
    by what a feature *does* -- somebody looking for curly quotes will not type
    "autocorrect". Matching the id is for a bug report that quotes one.

    wx-free, so the filtering rule is testable without a display.
    """
    words = query.lower().split()
    if not words:
        return list(areas)
    found = []
    for area in areas:
        haystack = f"{area.label} {area.description} {area.id}".lower()
        if all(word in haystack for word in words):
            found.append(area)
    return found


class AppFeaturesDialog:
    def __init__(
        self,
        parent: object,
        *,
        app_title: str,
        areas: Sequence[AppArea],
        settings: AppFeatureSettings,
        profiles: Sequence[AppProfile] = (),
        app_settings: object = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._areas = list(areas)
        self._profiles = list(profiles)
        self._settings = settings
        #: The app's own settings object, when it has entrusted one to a
        #: profile. None means profiles here only ever touch areas.
        self._app_settings = app_settings
        #: The profile whose settings Save should apply. Held rather than
        #: applied on the spot so Cancel really is a cancel: a user who presses
        #: Use Profile, reads what it did and changes their mind must not find
        #: Ctrl+N already rewritten.
        self._pending_profile: AppProfile | None = None
        self._announce = announce_cb or (lambda _m: None)
        self._saved = False
        self._checks: dict[str, object] = {}
        self._rows: dict[str, list[object]] = {}
        #: The areas as they were when the dialog opened. Custom is a
        #: destination, not only a readback: selecting it restores this, which
        #: is the undo for an arrow press onto a profile somebody did not want.
        self._opening_disabled = {
            area.id for area in self._areas if not settings.is_enabled(area.id)
        }

        self.dialog = wx.Dialog(
            parent,
            title=f"Customize {app_title} Features",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Turn parts of the app on or off. Unchecking an area removes its "
                    "whole menu the next time you open the app."
                ),
            ),
            0,
            wx.ALL,
            12,
        )

        if self._profiles:
            root.Add(self._build_profile_row(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        root.Add(self._build_search_row(), 0, wx.EXPAND | wx.ALL, 12)
        root.Add(self._build_list(), 1, wx.EXPAND)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer()
        # No access key on either: Enter and Escape already serve them, and
        # every letter they give up resolves a collision elsewhere (GATE-14).
        ok = wx.Button(self.dialog, wx.ID_OK, "Save")
        btn_row.Add(ok, 0, wx.RIGHT, 6)
        btn_row.Add(wx.Button(self.dialog, wx.ID_CANCEL, "Cancel"))
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)
        root.Fit(self.dialog)
        width, height = self.dialog.GetSize()
        self.dialog.SetSize(width, min(_MAX_HEIGHT, height))
        ok.Bind(wx.EVT_BUTTON, lambda _e: self._save())
        self._sync_profile_choice()
        self._apply_filter("")

    # -- construction -------------------------------------------------------- #

    def _build_profile_row(self):  # type: ignore[no-untyped-def]
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self.dialog, label="&Profile:")
        self.profile_choice = wx.Choice(
            self.dialog, choices=[p.name for p in self._profiles] + [CUSTOM_PROFILE]
        )
        set_accessible_name(self.profile_choice, "Profile")
        # Inline at the construction site, which is the only place a help audit
        # can see it. _show_profile_description replaces it with this plus the
        # selected profile's impact, so F1 answers "what is this one?" too.
        self.profile_choice.SetHelpText(_PROFILE_HELP)
        self.profile_choice.Bind(wx.EVT_CHOICE, lambda _e: self._on_profile_chosen())
        # "Use Profile" rather than "Apply": Apply on a dialog means "commit what
        # I have changed", and this commits nothing -- it fills the boxes in, and
        # Save is still the only thing that writes them. It is no longer the only
        # way in (the Choice applies as you move through it), but it is still the
        # way to get back to a profile you have since hand-edited without
        # arrowing away from its name and back again.
        use = wx.Button(self.dialog, label="&Use Profile")
        use.SetHelpText(
            "Set every checkbox below to what the chosen profile says. Choosing a "
            "profile above already does this; use it to start over after you have "
            "changed boxes by hand."
        )
        use.Bind(wx.EVT_BUTTON, lambda _e: self._use_profile())
        row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        row.Add(self.profile_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        row.Add(use, 0, wx.ALIGN_CENTER_VERTICAL)

        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(row, 0, wx.EXPAND)
        # Read-only, multi-line and in the tab ring: a StaticText is none of
        # those, so the paragraph that explains a seventeen-area profile could
        # be reached only by hearing it all at once. This one can be arrowed
        # through a line at a time, and copied.
        self.profile_description = wx.TextCtrl(
            self.dialog,
            value="",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP,
            size=(_HINT_WRAP, self.dialog.GetCharHeight() * _IMPACT_LINES),
        )
        set_accessible_name(self.profile_description, "What this profile does")
        column.Add(self.profile_description, 0, wx.EXPAND | wx.TOP, 4)
        return column

    def _build_search_row(self):  # type: ignore[no-untyped-def]
        wx = self._wx
        row = wx.BoxSizer(wx.VERTICAL)
        line = wx.BoxSizer(wx.HORIZONTAL)
        line.Add(
            wx.StaticText(self.dialog, label="&Search features:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.search = wx.TextCtrl(self.dialog)
        set_accessible_name(self.search, "Search features")
        self.search.SetHelpText(
            "Type part of a feature's name, or of what it does, and the list below "
            "narrows to what matches. Press Down to move into the list."
        )
        self.search.Bind(wx.EVT_TEXT, lambda _e: self._apply_filter(self.search.GetValue()))
        self.search.Bind(wx.EVT_KEY_DOWN, self._on_search_key)
        line.Add(self.search, 1, wx.ALIGN_CENTER_VERTICAL)
        row.Add(line, 0, wx.EXPAND)
        self.count_label = wx.StaticText(self.dialog, label="")
        set_accessible_name(self.count_label, "Features shown")
        row.Add(self.count_label, 0, wx.TOP, 4)
        return row

    def _build_list(self):  # type: ignore[no-untyped-def]
        wx = self._wx
        self.list_panel = wx.ScrolledWindow(self.dialog, style=wx.TAB_TRAVERSAL)
        self.list_panel.SetScrollRate(0, _SCROLL_STEP)
        self.list_panel.SetName("Features")
        sizer = wx.BoxSizer(wx.VERTICAL)
        for area in self._areas:
            box = wx.CheckBox(self.list_panel, label=f"Enable {area.label}")
            box.SetValue(self._settings.is_enabled(area.id))
            box.SetHelpText(area.description or f"Whether {area.label} is available.")
            set_accessible_name(box, f"Enable {area.label}")
            box.Bind(wx.EVT_CHECKBOX, lambda _e: self._sync_profile_choice())
            sizer.Add(box, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
            self._checks[area.id] = box
            self._rows[area.id] = [box]
            # The description lives in **F1 only** (2026-09-12, reported by
            # Jeff: "the descriptions are cut off"). It used to be a StaticText
            # under each box as well, wrapped at a fixed width that the dialog
            # does not honour once the list scrolls, so the sentence a user most
            # needed was the one they could not finish reading.
            #
            # Help is the better home for it in any case. A screen-reader user
            # arrowing the list heard every description whether or not they
            # wanted it -- fourteen paragraphs to walk past to reach the
            # fourteenth checkbox -- and now hears the box, and asks F1 when the
            # label is not enough. The text itself is unchanged and still
            # searchable: matching_areas() reads the AppArea, not the widget.
        self.list_panel.SetSizer(sizer)
        return self.list_panel

    # -- filtering ----------------------------------------------------------- #

    def _apply_filter(self, query: str) -> None:
        """Show the areas that match, hide the rest, and say how many are left.

        Hidden rather than removed, because a hidden control is out of the tab
        ring: Tab from the search box reaches the first *matching* checkbox and
        never walks through fourteen it cannot see.
        """
        shown = {area.id for area in matching_areas(self._areas, query)}
        for area_id, widgets in self._rows.items():
            for widget in widgets:
                widget.Show(area_id in shown)
        self.list_panel.Layout()
        self.list_panel.FitInside()
        text = self._count_text(len(shown), query)
        if self.count_label.GetLabel() == text:
            return
        self.count_label.SetLabel(text)
        # A label change on an unfocused control is exactly what a reader does
        # not say by itself (GATE-12), and the filter is a thing the user did:
        # not announcing the result would leave them arrowing to count.
        if query:
            self._announce(text)

    def _count_text(self, shown: int, query: str) -> str:
        if not query:
            return f"{len(self._areas)} features."
        if shown == 0:
            return "No features match. Clear the box to see them all."
        return f"{shown} of {len(self._areas)} features shown."

    def _on_search_key(self, event) -> None:  # type: ignore[no-untyped-def]
        """Down from the search box lands on the first surviving checkbox."""
        if event.GetKeyCode() == self._wx.WXK_DOWN:
            first = self._first_visible_check()
            if first is not None:
                first.SetFocus()
                return
        event.Skip()

    def _first_visible_check(self):  # type: ignore[no-untyped-def]
        for area in self._areas:
            box = self._checks[area.id]
            if box.IsShown():
                return box
        return None

    # -- profiles ------------------------------------------------------------ #

    def _on_profile_chosen(self) -> None:
        """The Choice moved: apply what it now names, and say what changed.

        The whole of the fix for the bug that made this dialog lie. Choosing
        Notepad used to change nothing at all until a second, undiscoverable
        press of Use Profile -- so somebody who chose it, read what it promised
        and pressed Save kept every feature they had, and the Format menu the
        description had just told them would be gone was still on the bar.

        Custom is not a profile and does not fill the boxes in from one: it puts
        them back to what they were when the dialog opened, which is what an
        arrow press onto the wrong name needs to be undoable.
        """
        index = self.profile_choice.GetSelection()
        if 0 <= index < len(self._profiles):
            self._apply_profile(self._profiles[index])
            return
        self._restore_opening_areas()

    def _use_profile(self) -> None:
        index = self.profile_choice.GetSelection()
        if index < 0 or index >= len(self._profiles):
            self._announce("Choose a profile first.")
            return
        self._apply_profile(self._profiles[index])

    def _apply_profile(self, profile: AppProfile) -> None:
        """Set every box to what *profile* says, and announce the outcome."""
        for area in self._areas:
            self._checks[area.id].SetValue(area.id not in profile.disabled)
        self._pending_profile = profile
        self._show_profile_description()
        # An outcome, which is the one thing the reader cannot know here:
        # seventeen checkboxes just changed and none of them has focus. One
        # line, not the paragraph: the paragraph is on screen to be read, and
        # speaking it over the name the reader is already saying on every arrow
        # press is the chattiness GATE-13 exists to stop. The settings half is
        # spelled out rather than counted, because "and one setting" tells
        # nobody which one.
        self._announce(
            profile_summary(profile, self._areas, self._setting_words())
            + " Nothing is saved until you press Save."
        )

    def _restore_opening_areas(self) -> None:
        """Custom: put the boxes back to the set the dialog opened with."""
        for area in self._areas:
            self._checks[area.id].SetValue(area.id not in self._opening_disabled)
        self._pending_profile = None
        self._show_profile_description()
        self._announce(
            "Custom: your own mix, as you had it when this window opened. "
            "Nothing is saved until you press Save."
        )

    def _show_profile_description(self) -> None:
        """Put the selected profile's full impact under the Choice, and on its F1.

        Silently -- the announcing is :meth:`_apply_profile`'s, and only when
        something actually changed. What goes in the box is computed from the
        areas (:func:`~quill.core.app_features.profile_impact`) rather than
        written beside them, so an area added in a later version appears in
        every profile's "keeps" list without anyone editing a paragraph.
        """
        index = self.profile_choice.GetSelection()
        if 0 <= index < len(self._profiles):
            text = profile_impact(self._profiles[index], self._areas, self._setting_words())
        else:
            text = _CUSTOM_DESCRIPTION
        self.profile_description.SetValue(text)
        # The help text is one paragraph, not the box's blank-line layout: F1
        # reads it as a single utterance and the blank lines buy nothing there.
        self.profile_choice.SetHelpText(f"{_PROFILE_HELP} {' '.join(text.split())}")
        self.dialog.Layout()

    def _setting_words(self) -> dict[str, str] | None:
        """The settings vocabulary, or None when this app entrusted no settings.

        None rather than an empty map, so a profile's ``settings`` are described
        only to an app that actually handed its settings object over -- claiming
        "new documents will be plain text" to an app that will not change them
        would be a promise the dialog cannot keep.
        """
        return SETTING_WORDS if self._app_settings is not None else None

    def _settings_sentence(self, profile: AppProfile) -> str:
        """What else this profile changes, in words, or "" when it changes nothing.

        Kept as the one-line form for a caller that wants it appended to a
        sentence of its own; the impact box and the announcement both go through
        ``core.app_features`` instead.
        """
        words = self._setting_words()
        if not words or not profile.settings:
            return ""
        said = [
            words[name].format(value=value) for name, value in profile.settings if name in words
        ]
        return (" " + " ".join(said)) if said else ""

    def _sync_profile_choice(self) -> None:
        """Point the Choice at whatever the boxes currently say, or at Custom."""
        if not self._profiles:
            return
        current = AppFeatureSettings(
            self._settings.app_id,
            {area.id for area in self._areas if not self._checks[area.id].GetValue()},
        )
        # The pending profile's settings, not the saved ones: between Use
        # Profile and Save the boxes are Notepad's and Ctrl+N is not yet, and
        # reading back "Custom" in that gap would be telling the user their own
        # click did not take.
        compare_against = self._app_settings
        if self._pending_profile is not None:
            compare_against = _PendingSettings(self._app_settings, self._pending_profile)
        for index, profile in enumerate(self._profiles):
            if current.matches_profile(profile, self._areas, compare_against):
                self.profile_choice.SetSelection(index)
                self._show_profile_description()
                return
        self.profile_choice.SetSelection(len(self._profiles))
        self._show_profile_description()

    # -- saving -------------------------------------------------------------- #

    def _save(self) -> None:
        for area_id, box in self._checks.items():
            self._settings.set_enabled(area_id, bool(box.GetValue()))
        if self._app_settings is not None and self._pending_profile is not None:
            apply_profile_settings(self._app_settings, self._pending_profile)
        self._saved = True
        if self.dialog.IsModal():
            self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> bool:
        """Modal; returns True if the user saved (caller then persists)."""
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Save",
            cancel_id=self._wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        # Focus starts in the search box, so a user who knows what they came for
        # types it and a user who does not presses Tab, which is where they were
        # going to start anyway.
        self.search.SetFocus()
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Customize Features", announce=self._announce)
        finally:
            self.dialog.Destroy()
        return self._saved
