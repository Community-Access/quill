"""The surface-purpose catalogue behind Quill Radio's F1 help (pure)."""

from __future__ import annotations

from quill.core.radio import surface_help


def test_every_purpose_is_prose_worth_reading() -> None:
    for title, purpose in surface_help.PURPOSES.items():
        assert purpose.strip(), f"{title!r} has an empty purpose"
        assert purpose.rstrip().endswith("."), f"{title!r} must end as a sentence"
        assert len(purpose) >= 60, f"{title!r} is too thin to orient anybody: {purpose!r}"
    for prefix, purpose in surface_help.PREFIX_PURPOSES:
        assert prefix.strip() and purpose.rstrip().endswith(".")


def test_purpose_lookup_exact_prefix_and_generic() -> None:
    assert (
        surface_help.purpose_for_title("Browse Stations")
        == (surface_help.PURPOSES["Browse Stations"])
    )
    assert "snapshot" in surface_help.purpose_for_title("Now Playing: WQXR")
    assert "Details:" in dict(surface_help.PREFIX_PURPOSES)
    assert surface_help.purpose_for_title("Some Window Nobody Wrote Yet") == (
        surface_help.GENERIC_PURPOSE
    )
    # Whitespace around a title must not defeat the lookup.
    assert surface_help.purpose_for_title("  Player  ") == surface_help.PURPOSES["Player"]


def test_is_known_title_matches_the_lookup() -> None:
    assert surface_help.is_known_title("Radio Recordings")
    assert surface_help.is_known_title("Details: WQXR")
    assert not surface_help.is_known_title("Some Window Nobody Wrote Yet")


def test_role_usage_teaches_known_roles_and_degrades_generically() -> None:
    assert "tree" in surface_help.role_usage("TreeCtrl").lower()
    assert "button" in surface_help.role_usage("Button").lower()
    assert surface_help.role_usage("SomeCustomWidget")  # never empty


def test_compose_control_body_layers_name_help_and_usage() -> None:
    body = surface_help.compose_control_body(
        accessible_name="Reload the highlighted source",
        help_text="Fetches the source again from the internet.",
        usage="A button: press Enter or Space to press it.",
    )
    assert "Reload the highlighted source." in body
    assert "Fetches the source again" in body
    assert body.index("Reload") < body.index("Fetches") < body.index("A button")


def test_compose_control_body_never_repeats_a_name_the_help_contains() -> None:
    body = surface_help.compose_control_body(
        accessible_name="Volume",
        help_text="Volume level. Press Enter to mute or unmute.",
        usage="",
    )
    assert body.count("Volume") == 1


def test_compose_control_body_is_never_empty() -> None:
    assert surface_help.compose_control_body(accessible_name="", help_text="", usage="")


def test_the_windows_this_repo_ships_are_all_in_the_catalogue() -> None:
    # The gate proper scans source; this pins the headline set so a rename
    # shows up as a readable failure here first.
    for title in (
        "Quill Radio",
        "Browse Stations",
        "Internet Radio",
        "Manage Favorite Stations",
        "Schedule Recording",
        "Radio Recordings",
        "Downloads",
        "Song History",
        "Player",
        "Go To",
        "Sleep Timer",
        "Wake-Up Timer",
        "Quill Radio Preferences",
    ):
        assert surface_help.is_known_title(title), f"{title!r} missing from PURPOSES"
