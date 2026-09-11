"""What a feature profile *does*, in words, computed rather than written.

The paragraph on an ``AppProfile`` says what a profile is. It cannot say what
choosing it would do to the app in front of you, because that changes every time
somebody adds an area -- and a paragraph that has to be re-edited whenever the
code moves is a paragraph that is wrong the first time nobody remembers to.
:func:`~quill.core.app_features.profile_impact` reads the areas instead.

wx-free, so the words two windows both show can be asserted without a display.
"""

from __future__ import annotations

from quill.core.app_features import AppArea, AppProfile, profile_impact, profile_summary

AREAS = (
    AppArea("rich_text", "Rich text and the Format menu", "Bold, italic and headings."),
    AppArea("spelling", "Spell check", "Check as you type."),
    AppArea("backups", "Timestamped backups", "A dated copy on every save."),
)

SMALL = AppProfile(
    "small",
    "Small",
    "The plain one.",
    frozenset({"rich_text", "backups"}),
    settings=(("default_mode", "plain"),),
)
EVERYTHING = AppProfile("everything", "Everything", "All of it.", frozenset())
WORDS = {"default_mode": "New documents will be {value} text."}


def test_the_profiles_own_words_come_first() -> None:
    """Whatever else is computed, the author's paragraph is still the opening."""
    assert profile_impact(SMALL, AREAS, WORDS).startswith("The plain one.")


def test_it_counts_what_survives_and_names_it() -> None:
    text = profile_impact(SMALL, AREAS, WORDS)
    assert "Keeps 1 of 3: Spell check." in text


def test_it_counts_what_goes_and_names_it() -> None:
    text = profile_impact(SMALL, AREAS, WORDS)
    assert "Removes 2: Rich text and the Format menu and Timestamped backups." in text


def test_a_profile_that_removes_nothing_says_so_rather_than_going_quiet() -> None:
    """An empty list read as "the section is missing", which is not the same fact."""
    assert "Removes nothing" in profile_impact(EVERYTHING, AREAS, WORDS)


def test_a_claimed_setting_is_spelled_out_in_english() -> None:
    assert "New documents will be plain text." in profile_impact(SMALL, AREAS, WORDS)


def test_a_setting_with_no_words_is_left_out_rather_than_named_as_a_variable() -> None:
    """ "default_mode = plain" tells a listener nothing they can act on."""
    text = profile_impact(SMALL, AREAS, {})
    assert "default_mode" not in text
    assert "It also changes" not in text


def test_an_app_that_entrusts_no_settings_hears_no_promise_about_them() -> None:
    """None, not {}: claiming a change the caller will not make is a lie."""
    assert "It also changes" not in profile_impact(SMALL, AREAS, None)


def test_a_new_area_lands_in_every_old_profiles_keeps_list() -> None:
    """The whole reason this is computed: profiles are written as what they take
    away, so an area added later is on in all of them and has to read that way."""
    grown = (*AREAS, AppArea("zoom", "Text size", "Bigger or smaller on screen."))
    text = profile_impact(SMALL, grown, WORDS)
    assert "Keeps 2 of 4: Spell check and Text size." in text


def test_the_spoken_version_is_one_line_and_leads_with_the_count() -> None:
    """The box is for reading; this is what is said over a reader already
    announcing the profile's name, so it is the outcome and nothing else."""
    said = profile_summary(SMALL, AREAS, WORDS)
    assert said == "Small profile: 1 of 3 features on. New documents will be plain text."
    assert "\n" not in said


def test_the_spoken_version_does_not_repeat_the_paragraph() -> None:
    assert "The plain one." not in profile_summary(SMALL, AREAS, WORDS)
