"""The Customize Features dialog: searching it, and the profile row.

The dialog is shared by Quill Radio, Quill Weather and QUILL Lite, so two things
are asserted here that no one app's tests would cover: that an app passing no
profiles gets no profile row at all, and that the filter is a pure function
anybody can check without a display.
"""

from __future__ import annotations

import contextlib

import pytest
import wx

from quill.core.app_features import AppArea, AppFeatureSettings, AppProfile
from quill.ui.app_features_dialog import CUSTOM_PROFILE, AppFeaturesDialog, matching_areas

AREAS = (
    AppArea("rich_text", "Rich text and the Format menu", "Bold, italic, headings and bullets."),
    AppArea("spelling", "Spell check", "Check as you type, and review with F7."),
    AppArea("backups", "Timestamped backups", "Keep a dated copy of each file every save."),
    AppArea("zoom", "Text size", "Make the text bigger or smaller on screen."),
)

PROFILES = (
    AppProfile("everything", "Everything", "All four.", frozenset()),
    AppProfile("small", "Small", "Plain text only.", frozenset({"rich_text", "spelling"})),
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture()
def parent(wx_app):
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()
    wx_app.Yield()


@contextlib.contextmanager
def _dialog(parent, settings, announce=None):
    """Build the dialog over the module's demo areas, and destroy it after.

    Every test below drives the dialog's own methods rather than wx events,
    because a Choice cannot be arrowed without a real message loop and what is
    being asserted is the decision, not wx's event plumbing.
    """
    dialog = AppFeaturesDialog(
        parent,
        app_title="Demo",
        areas=AREAS,
        settings=settings,
        profiles=PROFILES,
        announce_cb=announce,
    )
    try:
        yield dialog
    finally:
        dialog.dialog.Destroy()


# ---------------------------------------------------------------------------
# matching_areas is wx-free, so most of the rule is checkable without a display


def test_an_empty_query_matches_everything() -> None:
    assert matching_areas(AREAS, "") == list(AREAS)
    assert matching_areas(AREAS, "   ") == list(AREAS)


def test_a_query_matches_the_label() -> None:
    assert [a.id for a in matching_areas(AREAS, "spell")] == ["spelling"]


def test_a_query_matches_the_description() -> None:
    """Somebody looking for bullets will not type "rich text"."""
    assert [a.id for a in matching_areas(AREAS, "bullets")] == ["rich_text"]


def test_a_query_matches_the_id() -> None:
    """For a bug report that quotes one."""
    assert [a.id for a in matching_areas(AREAS, "rich_text")] == ["rich_text"]


def test_matching_is_case_insensitive() -> None:
    assert [a.id for a in matching_areas(AREAS, "SPELL")] == ["spelling"]


def test_every_word_has_to_match() -> None:
    assert matching_areas(AREAS, "spell bullets") == []
    assert [a.id for a in matching_areas(AREAS, "spell type")] == ["spelling"]


def test_results_keep_the_declared_order() -> None:
    assert [a.id for a in matching_areas(AREAS, "e")] == [
        a.id for a in AREAS if "e" in f"{a.label} {a.description} {a.id}".lower()
    ]


def test_no_match_is_an_empty_list_not_an_error() -> None:
    assert matching_areas(AREAS, "zzzz") == []


# ---------------------------------------------------------------------------
# the dialog


def test_typing_hides_the_rows_that_do_not_match(parent) -> None:
    dialog = AppFeaturesDialog(
        parent, app_title="Test", areas=AREAS, settings=AppFeatureSettings("test")
    )
    try:
        dialog._apply_filter("spell")
        assert dialog._checks["spelling"].IsShown()
        assert not dialog._checks["rich_text"].IsShown()
    finally:
        dialog.dialog.Destroy()


def test_clearing_the_box_brings_them_all_back(parent) -> None:
    dialog = AppFeaturesDialog(
        parent, app_title="Test", areas=AREAS, settings=AppFeatureSettings("test")
    )
    try:
        dialog._apply_filter("spell")
        dialog._apply_filter("")
        assert all(box.IsShown() for box in dialog._checks.values())
    finally:
        dialog.dialog.Destroy()


def test_the_count_says_how_many_are_left(parent) -> None:
    dialog = AppFeaturesDialog(
        parent, app_title="Test", areas=AREAS, settings=AppFeatureSettings("test")
    )
    try:
        dialog._apply_filter("spell")
        assert dialog.count_label.GetLabel() == "1 of 4 features shown."
        dialog._apply_filter("zzzz")
        assert "No features match" in dialog.count_label.GetLabel()
    finally:
        dialog.dialog.Destroy()


def test_a_filtered_count_is_announced(parent) -> None:
    """A label change on an unfocused control is what a reader does not say."""
    said: list[str] = []
    dialog = AppFeaturesDialog(
        parent,
        app_title="Test",
        areas=AREAS,
        settings=AppFeatureSettings("test"),
        announce_cb=said.append,
    )
    try:
        dialog._apply_filter("spell")
        assert said == ["1 of 4 features shown."]
    finally:
        dialog.dialog.Destroy()


def test_the_unfiltered_count_is_not_announced(parent) -> None:
    """Opening the dialog is not an event worth speaking over the title."""
    said: list[str] = []
    dialog = AppFeaturesDialog(
        parent,
        app_title="Test",
        areas=AREAS,
        settings=AppFeatureSettings("test"),
        announce_cb=said.append,
    )
    try:
        assert said == []
    finally:
        dialog.dialog.Destroy()


def test_a_hidden_checkbox_is_out_of_the_tab_ring(parent) -> None:
    dialog = AppFeaturesDialog(
        parent, app_title="Test", areas=AREAS, settings=AppFeatureSettings("test")
    )
    try:
        dialog._apply_filter("spell")
        assert dialog._first_visible_check() is dialog._checks["spelling"]
    finally:
        dialog.dialog.Destroy()


# ---------------------------------------------------------------------------
# profiles


def test_an_app_with_no_profiles_gets_no_profile_row(parent) -> None:
    """Radio and Weather pass none and must be unchanged by all of this."""
    dialog = AppFeaturesDialog(
        parent, app_title="Test", areas=AREAS, settings=AppFeatureSettings("test")
    )
    try:
        assert not hasattr(dialog, "profile_choice")
    finally:
        dialog.dialog.Destroy()


def test_using_a_profile_sets_every_box(parent) -> None:
    dialog = AppFeaturesDialog(
        parent,
        app_title="Test",
        areas=AREAS,
        settings=AppFeatureSettings("test"),
        profiles=PROFILES,
    )
    try:
        dialog.profile_choice.SetSelection(1)  # Small
        dialog._use_profile()
        assert not dialog._checks["rich_text"].GetValue()
        assert not dialog._checks["spelling"].GetValue()
        assert dialog._checks["backups"].GetValue()
    finally:
        dialog.dialog.Destroy()


def test_using_a_profile_saves_nothing_by_itself(parent) -> None:
    settings = AppFeatureSettings("test")
    dialog = AppFeaturesDialog(
        parent, app_title="Test", areas=AREAS, settings=settings, profiles=PROFILES
    )
    try:
        dialog.profile_choice.SetSelection(1)
        dialog._use_profile()
        assert settings.disabled == set()  # untouched until Save
        dialog._save()
        assert settings.disabled == {"rich_text", "spelling"}
    finally:
        dialog.dialog.Destroy()


def test_a_profile_change_is_announced(parent) -> None:
    """Four checkboxes just changed and none of them has focus."""
    said: list[str] = []
    dialog = AppFeaturesDialog(
        parent,
        app_title="Test",
        areas=AREAS,
        settings=AppFeatureSettings("test"),
        profiles=PROFILES,
        announce_cb=said.append,
    )
    try:
        dialog.profile_choice.SetSelection(1)
        dialog._use_profile()
        assert said and "Small profile: 2 of 4 features on." in said[-1]
        assert "Nothing is saved until you press Save." in said[-1]
    finally:
        dialog.dialog.Destroy()


def test_the_choice_reads_back_the_current_boxes(parent) -> None:
    dialog = AppFeaturesDialog(
        parent,
        app_title="Test",
        areas=AREAS,
        settings=AppFeatureSettings("test", {"rich_text", "spelling"}),
        profiles=PROFILES,
    )
    try:
        assert dialog.profile_choice.GetStringSelection() == "Small"
    finally:
        dialog.dialog.Destroy()


def test_a_hand_edit_shows_as_custom(parent) -> None:
    dialog = AppFeaturesDialog(
        parent,
        app_title="Test",
        areas=AREAS,
        settings=AppFeatureSettings("test"),
        profiles=PROFILES,
    )
    try:
        assert dialog.profile_choice.GetStringSelection() == "Everything"
        dialog._checks["zoom"].SetValue(False)
        dialog._sync_profile_choice()
        assert dialog.profile_choice.GetStringSelection() == CUSTOM_PROFILE
    finally:
        dialog.dialog.Destroy()


def test_a_stored_marker_does_not_break_the_readback(parent) -> None:
    """QUILL Lite stores a private seeding marker in the same disabled set."""
    dialog = AppFeaturesDialog(
        parent,
        app_title="Test",
        areas=AREAS,
        settings=AppFeatureSettings("test", {"_seeded"}),
        profiles=PROFILES,
    )
    try:
        assert dialog.profile_choice.GetStringSelection() == "Everything"
    finally:
        dialog.dialog.Destroy()


def test_saving_never_touches_an_id_that_is_not_an_area(parent) -> None:
    settings = AppFeatureSettings("test", {"_seeded"})
    dialog = AppFeaturesDialog(
        parent, app_title="Test", areas=AREAS, settings=settings, profiles=PROFILES
    )
    try:
        dialog._save()
        assert "_seeded" in settings.disabled
    finally:
        dialog.dialog.Destroy()


# ---------------------------------------------------------------------------
# a profile that claims a setting, not only a set of areas


class _AppSettings:
    """The one field the test profiles claim, plus one they never touch."""

    def __init__(self) -> None:
        self.default_mode = "plain"
        self.theme = "dark"


PROFILES_WITH_SETTINGS = (
    AppProfile("everything", "Everything", "All four.", frozenset()),
    AppProfile(
        "small",
        "Small",
        "Plain text only.",
        frozenset({"rich_text", "spelling"}),
        settings=(("default_mode", "plain"),),
    ),
    AppProfile(
        "rich",
        "Rich",
        "Rich text.",
        frozenset({"backups"}),
        settings=(("default_mode", "rich"),),
    ),
)


def _with_settings(parent, app_settings, said=None, disabled=frozenset()):
    return AppFeaturesDialog(
        parent,
        app_title="Test",
        areas=AREAS,
        settings=AppFeatureSettings("test", set(disabled)),
        profiles=PROFILES_WITH_SETTINGS,
        app_settings=app_settings,
        announce_cb=said.append if said is not None else None,
    )


def test_a_profiles_setting_is_applied_on_save(parent) -> None:
    app_settings = _AppSettings()
    dialog = _with_settings(parent, app_settings)
    try:
        dialog.profile_choice.SetSelection(2)  # Rich
        dialog._use_profile()
        assert app_settings.default_mode == "plain", "nothing before Save"
        dialog._save()
        assert app_settings.default_mode == "rich"
    finally:
        dialog.dialog.Destroy()


def test_cancelling_leaves_the_setting_alone(parent) -> None:
    """Use Profile, read what it did, change your mind -- Ctrl+N must be untouched."""
    app_settings = _AppSettings()
    dialog = _with_settings(parent, app_settings)
    try:
        dialog.profile_choice.SetSelection(2)
        dialog._use_profile()
        # No _save(): this is the Cancel path.
        assert app_settings.default_mode == "plain"
    finally:
        dialog.dialog.Destroy()


def test_the_setting_is_announced_in_words(parent) -> None:
    """ "and one setting" tells nobody which one."""
    said: list[str] = []
    dialog = _with_settings(parent, _AppSettings(), said)
    try:
        dialog.profile_choice.SetSelection(2)
        dialog._use_profile()
        assert "New documents will be rich text." in said[-1]
    finally:
        dialog.dialog.Destroy()


def test_a_profile_that_claims_nothing_says_nothing_extra(parent) -> None:
    said: list[str] = []
    dialog = _with_settings(parent, _AppSettings(), said)
    try:
        dialog.profile_choice.SetSelection(0)  # Everything: areas only
        dialog._use_profile()
        assert "New documents" not in said[-1]
    finally:
        dialog.dialog.Destroy()


def test_a_setting_the_profile_does_not_claim_is_untouched(parent) -> None:
    app_settings = _AppSettings()
    dialog = _with_settings(parent, app_settings)
    try:
        dialog.profile_choice.SetSelection(2)
        dialog._use_profile()
        dialog._save()
        assert app_settings.theme == "dark"
    finally:
        dialog.dialog.Destroy()


def test_the_readback_reflects_the_profile_you_just_chose(parent) -> None:
    """Between Use Profile and Save the boxes are Rich's and Ctrl+N is not yet.

    Reading back "Custom" in that gap would be telling the user their own click
    did not take.
    """
    dialog = _with_settings(parent, _AppSettings())
    try:
        dialog.profile_choice.SetSelection(2)
        dialog._use_profile()
        dialog._sync_profile_choice()
        assert dialog.profile_choice.GetStringSelection() == "Rich"
    finally:
        dialog.dialog.Destroy()


def test_a_setting_that_no_longer_matches_reads_as_custom(parent) -> None:
    """Somebody on Notepad who switches Ctrl+N to rich has left what it promises."""
    app_settings = _AppSettings()
    app_settings.default_mode = "rich"
    dialog = _with_settings(parent, app_settings, disabled={"rich_text", "spelling"})
    try:
        # The areas are exactly Small's; the setting is not.
        assert dialog.profile_choice.GetStringSelection() == CUSTOM_PROFILE
    finally:
        dialog.dialog.Destroy()


def test_an_app_that_entrusts_no_settings_is_unchanged(parent) -> None:
    """Radio and Weather pass none, and profiles there touch areas only."""
    dialog = AppFeaturesDialog(
        parent,
        app_title="Test",
        areas=AREAS,
        settings=AppFeatureSettings("test"),
        profiles=PROFILES_WITH_SETTINGS,
    )
    try:
        dialog.profile_choice.SetSelection(2)
        dialog._use_profile()
        dialog._save()  # must not raise with no settings object
    finally:
        dialog.dialog.Destroy()


# ---------------------------------------------------------------------------
# Choosing a profile is the whole gesture -- there is no invisible second step


def test_choosing_a_profile_sets_the_boxes_without_a_second_press(parent) -> None:
    """The bug this fixes: pick Notepad, press Save, keep every feature you had.

    Applying used to need Use Profile, and nothing said so. Somebody who chose a
    profile, read the description that appeared under it and saved got their old
    feature set back -- and a Format menu the description had just promised
    would be gone.
    """
    settings = AppFeatureSettings("demo")
    with _dialog(parent, settings) as dialog:
        dialog.profile_choice.SetSelection(1)  # Small
        dialog._on_profile_chosen()
        assert not dialog._checks["rich_text"].GetValue()
        assert not dialog._checks["spelling"].GetValue()
        assert dialog._checks["backups"].GetValue()


def test_choosing_a_profile_still_saves_nothing_by_itself(parent) -> None:
    settings = AppFeatureSettings("demo")
    with _dialog(parent, settings) as dialog:
        dialog.profile_choice.SetSelection(1)
        dialog._on_profile_chosen()
        assert settings.disabled == set()


def test_choosing_custom_puts_the_boxes_back_to_how_you_found_them(parent) -> None:
    """Custom is a destination, not only a readback: it is the undo for an
    arrow press onto a profile somebody did not mean to land on."""
    settings = AppFeatureSettings("demo", {"backups"})
    with _dialog(parent, settings) as dialog:
        dialog.profile_choice.SetSelection(1)  # Small
        dialog._on_profile_chosen()
        assert not dialog._checks["rich_text"].GetValue()
        dialog.profile_choice.SetSelection(len(PROFILES))  # Custom
        dialog._on_profile_chosen()
        assert dialog._checks["rich_text"].GetValue()
        assert not dialog._checks["backups"].GetValue()


def test_choosing_a_profile_announces_one_line_not_the_paragraph(parent) -> None:
    """A reader is already saying the profile's name as you arrow onto it.
    Speaking the paragraph over that on every press is GATE-13's whole subject;
    saying nothing leaves four checkboxes changing behind an unfocused control.
    """
    said: list[str] = []
    settings = AppFeatureSettings("demo")
    with _dialog(parent, settings, announce=said.append) as dialog:
        dialog.profile_choice.SetSelection(1)
        dialog._on_profile_chosen()
    assert said
    assert "Small profile: 2 of 4 features on." in said[-1]
    assert "Plain text only." not in said[-1]
    assert "\n" not in said[-1]


# ---------------------------------------------------------------------------
# The impact box


def test_the_impact_box_is_readable_rather_than_a_label(parent) -> None:
    """A StaticText is not in the tab ring and cannot be arrowed through, so a
    paragraph in one is a paragraph a screen-reader user hears all at once."""
    with _dialog(parent, AppFeatureSettings("demo")) as dialog:
        assert isinstance(dialog.profile_description, wx.TextCtrl)
        assert not dialog.profile_description.IsEditable()
        assert dialog.profile_description.IsMultiLine()


def test_the_impact_box_says_what_the_profile_would_do(parent) -> None:
    with _dialog(parent, AppFeatureSettings("demo")) as dialog:
        dialog.profile_choice.SetSelection(1)
        dialog._on_profile_chosen()
        text = dialog.profile_description.GetValue()
        assert "Plain text only." in text
        assert "Keeps 2 of 4" in text
        assert "Removes 2" in text


def test_the_impact_box_explains_custom_rather_than_going_blank(parent) -> None:
    """A reader who hears "Custom" where they expected "Notepad" should be told
    that is a normal place to be, not left to wonder what they broke."""
    with _dialog(parent, AppFeatureSettings("demo")) as dialog:
        dialog.profile_choice.SetSelection(len(PROFILES))
        dialog._on_profile_chosen()
        assert "Your own mix" in dialog.profile_description.GetValue()


def test_f1_on_the_choice_answers_what_this_one_is(parent) -> None:
    # Without a provider every SetHelpText in the app silently stores nothing,
    # which is why the apps install one at activation -- and why a test that
    # asserts help text has to as well.
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)
    with _dialog(parent, AppFeatureSettings("demo")) as dialog:
        dialog.profile_choice.SetSelection(1)
        dialog._on_profile_chosen()
        help_text = dialog.profile_choice.GetHelpText()
        assert "Plain text only." in help_text
        assert "Keeps 2 of 4" in help_text
