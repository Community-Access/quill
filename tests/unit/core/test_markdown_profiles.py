"""Unit tests for quill.core.markdown_profiles (issue #257)."""

from __future__ import annotations

from quill.core.markdown_profiles import (
    CITATION_STYLES,
    MARKDOWN_EXTENSIONS,
    MARKDOWN_PROFILES,
    describe_profile,
    extension_names,
)


def test_eight_built_in_profiles_exist() -> None:
    assert len(MARKDOWN_PROFILES) == 8
    assert "standard" in MARKDOWN_PROFILES
    assert "custom" in MARKDOWN_PROFILES


def test_every_profile_extension_id_is_in_the_catalog() -> None:
    for profile in MARKDOWN_PROFILES.values():
        for ext_id in profile.extensions:
            assert ext_id in MARKDOWN_EXTENSIONS, f"{profile.id} references unknown {ext_id!r}"


def test_documentation_profile_enables_toc() -> None:
    assert "toc" in MARKDOWN_PROFILES["documentation"].extensions


def test_standard_profile_enables_nothing_extra() -> None:
    assert MARKDOWN_PROFILES["standard"].extensions == frozenset()


def test_extension_names_returns_friendly_names() -> None:
    names = extension_names("poetry_and_lyrics")
    assert names == ["Preserve Single Line Breaks"]


def test_extension_names_unknown_profile_is_empty() -> None:
    assert extension_names("not-a-real-profile") == []


def test_describe_profile_includes_count_and_description() -> None:
    summary = describe_profile("documentation")
    assert "Documentation" in summary
    assert "5 extensions enabled" in summary


def test_describe_profile_unknown_id() -> None:
    assert "No Markdown profile" in describe_profile("nope")


def test_citation_styles_are_footnotes_and_academic() -> None:
    values = [value for value, _label in CITATION_STYLES]
    assert values == ["footnotes", "academic"]
