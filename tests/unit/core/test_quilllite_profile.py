"""The QuillLite profile in QUILL (bad.md P2.4).

One feature profile that shows QuillLite's menus and nothing else, so somebody
who is used to the small editor can have QUILL be that shape without giving up
the option of the rest.

Two things it gets right that a list of feature names cannot:

**Off, not hidden.** Everything the profile takes away is still reachable from
Customize Features and from the command palette. Somebody who chose "the small
one" and then wants one thing back has to be able to find it, and a hidden
feature cannot be found by looking.

**It carries a setting.** QuillLite makes a plain text document on Ctrl+N, and a
profile named after it that made a rich text one would keep the letter of its
name and break its promise -- the user finding out one document later, at the
Save As dialog, offering a format they thought they had turned off. QuillLite's
own Notepad and WordPad profiles have carried their ``default_mode`` since they
shipped, for exactly this reason.
"""

from __future__ import annotations

from quill.core.features import (
    FEATURE_DEFINITIONS,
    FEATURE_STATE_OFF,
    PROFILE_DEFINITIONS,
    PROFILE_QUILLLITE,
    FeatureManager,
)


def _profile() -> object:
    return PROFILE_DEFINITIONS[PROFILE_QUILLLITE]


def test_the_profile_exists_and_is_named_for_the_product() -> None:
    assert str(_profile().name) == "QuillLite"


def test_everything_quilllite_has_is_still_on() -> None:
    """Editing, files, spelling, formatting, navigation, clipboard, help."""
    manager = FeatureManager(active_profile_id=PROFILE_QUILLLITE)
    for feature_id in (
        "core.editor",
        "core.file",
        "core.edit",
        "core.format",
        "core.search",
        "core.navigate",
        "core.spellcheck",
        "core.abbreviations",
        "core.recovery",
        "core.help",
        "core.palette",
        "core.view",
        "core.window",
        "core.text_encoding",
    ):
        assert manager.is_enabled(feature_id), f"{feature_id} should stay on"


def test_what_quilllite_does_not_have_is_off() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_QUILLLITE)
    for feature_id in (
        "future.ai",
        "core.radio",
        "core.podcasts",
        "core.glow",
        "future.quillins_menu",
        "core.remote",
        "core.github_remote",
        "core.notebook",
        "core.read_aloud",
        "core.dictation",
        "core.macros",
    ):
        assert not manager.is_enabled(feature_id), f"{feature_id} should be off"


def test_the_bundled_quillins_stay_because_quill_needs_them() -> None:
    """Locked on, and rightly: the bundled extensions carry commands QUILL uses.

    What QuillLite lacks is the Quillins *menu*, which is a different feature and
    is off. A profile that tried to switch off a locked feature would be a
    profile making a promise the feature manager will not keep.
    """
    manager = FeatureManager(active_profile_id=PROFILE_QUILLLITE)
    assert manager.is_enabled("core.bundled_quillins")
    assert FEATURE_DEFINITIONS["core.bundled_quillins"].locked_on


def test_the_profile_never_claims_to_switch_off_a_locked_feature() -> None:
    for feature_id in _profile().states:
        assert not FEATURE_DEFINITIONS[feature_id].locked_on, feature_id


def test_nothing_is_hidden_only_switched_off() -> None:
    """The whole difference between "the small one" and "a smaller product"."""
    states = _profile().states
    assert states, "the profile must say something"
    assert set(states.values()) == {FEATURE_STATE_OFF}


def test_the_profile_is_written_as_a_subtraction() -> None:
    """A feature added to QUILL later is ON here until somebody decides.

    The safe direction: a new feature silently missing is a bug nobody can see,
    while a new feature unexpectedly present is one press of Customize Features
    away.
    """
    states = _profile().states
    assert len(states) < len(FEATURE_DEFINITIONS)
    for feature_id in states:
        assert feature_id in FEATURE_DEFINITIONS, f"{feature_id} is not a feature"


def test_ctrl_n_makes_the_document_quilllite_would_make() -> None:
    assert _profile().settings == (("default_new_document_format", "txt"),)


def test_every_other_profile_promises_nothing_about_settings() -> None:
    """Only a profile named after a product makes a claim about the document."""
    for profile_id, profile in PROFILE_DEFINITIONS.items():
        if profile_id == PROFILE_QUILLLITE:
            continue
        assert profile.settings == (), f"{profile_id} should not carry settings"


def test_a_profiles_promised_settings_are_a_real_settings_field() -> None:
    from quill.core.settings import Settings

    settings = Settings()
    for profile in PROFILE_DEFINITIONS.values():
        for field_name, _value in profile.settings:
            assert hasattr(settings, field_name), field_name
