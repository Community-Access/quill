"""The feature-profile row at the top of the Preferences window.

Split out of :mod:`quill.apps.lite_preferences` under GATE-11, and it stands on
its own: everything here is about *one control* -- the Choice that says "make
this Notepad", the read-only box that says what that would cost, and what OK
does with the answer -- while the module it came from is the settings model.

Why the row exists at all is in that module's docstring: the profiles were
reachable only from Tools > Customize Features, behind a name that describes a
mechanism rather than a wish, and somebody who wants the small editor does not
know they are looking for a customization dialog.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import wx

from quill.apps.lite_dialogs import _stack
from quill.core.app_features import (
    AppArea,
    AppFeatureSettings,
    AppProfile,
    apply_profile,
    profile_impact,
    profile_summary,
)
from quill.ui.app_features_dialog import CUSTOM_PROFILE, SETTING_WORDS
from quill.ui.dialog_contract import set_accessible_name

__all__ = ["ProfileRow"]

#: Uniform padding, matching the dialog this row sits in.
_PAD = 8

#: How wide the profile impact box is, and how many lines of it are on screen
#: before it scrolls. Matched to the Customize Features dialog's, because it is
#: the same text and two different shapes of the same paragraph is a thing
#: somebody has to read twice.
_IMPACT_WIDTH = 560
_IMPACT_LINES = 7

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


class ProfileRow:
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
