"""Conversion profile tests (issue #262)."""

from __future__ import annotations

from quill.core import convert_profiles


def test_seven_profiles_match_issue_262() -> None:
    names = {p.name for p in convert_profiles.PROFILES}
    expected = {
        "clean_word_document",
        "accessible_html_page",
        "epub_book",
        "github_readme",
        "print_pdf",
        "instructor_handout",
        "plain_text_for_screen_readers",
    }
    assert names == expected


def test_each_profile_has_display_name_and_description() -> None:
    for profile in convert_profiles.PROFILES:
        assert profile.label
        assert profile.description
        assert (
            profile.description.endswith(
                (".", ")", ")", "?", "!"),
            )
            or len(profile.description) > 40
        )
        # All seven issue #262 profiles have descriptions ending in a period.
        assert profile.description.rstrip().endswith("."), f"{profile.name} missing period"


def test_each_profile_locks_target_format() -> None:
    for profile in convert_profiles.PROFILES:
        assert profile.target_format in {
            "docx",
            "html",
            "epub",
            "gfm",
            "pdf",
            "plain_text",
        }, f"{profile.name} has unexpected target_format {profile.target_format!r}"


def test_get_profile_round_trip() -> None:
    for profile in convert_profiles.PROFILES:
        assert convert_profiles.get_profile(profile.name) is profile


def test_get_profile_none_returns_none() -> None:
    assert convert_profiles.get_profile(None) is None
    assert convert_profiles.get_profile("") is None


def test_get_profile_unknown_returns_none() -> None:
    assert convert_profiles.get_profile("not-a-profile") is None


def test_flags_for_profile_returns_tuple() -> None:
    for profile in convert_profiles.PROFILES:
        flags = convert_profiles.flags_for_profile(profile.name)
        assert isinstance(flags, tuple)
        for flag in flags:
            assert isinstance(flag, str)


def test_flags_for_no_profile_returns_empty() -> None:
    assert convert_profiles.flags_for_profile(None) == ()


def test_print_pdf_locks_to_pdf() -> None:
    pdf = convert_profiles.get_profile("print_pdf")
    assert pdf is not None
    assert pdf.target_format == "pdf"


def test_plain_text_profile_locks_to_plain_text() -> None:
    plain = convert_profiles.get_profile("plain_text_for_screen_readers")
    assert plain is not None
    assert plain.target_format == "plain_text"
    # No flags that would inject markup into the output.
    for flag in plain.flags:
        assert not flag.startswith("--html"), flag
