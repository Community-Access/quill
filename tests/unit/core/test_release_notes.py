"""Tests for the abbreviated release-notes extractor (quill.core.release_notes)."""

from __future__ import annotations

from quill.core.release_notes import (
    extract_version_section,
    release_notes_for,
)

CHANGELOG = """\
# Changelog

## 0.8.0 Beta 1 (in development)

Top summary line.

### Section A

- **Bold** feature with `code`.
- Another change.

## 0.7.0

Older release.

### Things

- Old item.
"""


def test_extracts_section_body_without_heading() -> None:
    section = extract_version_section(CHANGELOG, "0.8.0 Beta 1")
    assert section.startswith("Top summary line.")
    assert "Another change." in section
    # Stops before the next ## heading.
    assert "Older release." not in section
    assert "## 0.8.0" not in section


def test_matches_git_tag_form() -> None:
    # A git tag (v0.8.0-beta1) must resolve to the human "0.8.0 Beta 1" heading.
    section = extract_version_section(CHANGELOG, "v0.8.0-beta1")
    assert "Top summary line." in section
    assert "Older release." not in section


def test_matches_by_base_version() -> None:
    section = extract_version_section(CHANGELOG, "0.7.0")
    assert "Older release." in section
    assert "Top summary line." not in section


# A changelog with two prereleases of the same base version; the newer one
# sits on top, exactly like CHANGELOG.md during the Beta 2 cycle.
TWO_BETAS = """\
# Changelog

## 0.8.0 Beta 2 (in development)

Beta two body.

## 0.8.0 Beta 1 (in development)

Beta one body.
"""


def test_exact_match_wins_over_newer_same_base_section() -> None:
    # The running Beta 1 build must get Beta 1 notes even though Beta 2 is on top.
    assert "Beta one body." in extract_version_section(TWO_BETAS, "0.8.0 Beta 1")
    assert "Beta two body." not in extract_version_section(TWO_BETAS, "0.8.0 Beta 1")
    # ...and the Beta 1 git-tag form resolves the same way.
    assert "Beta one body." in extract_version_section(TWO_BETAS, "v0.8.0-beta1")


def test_beta2_resolves_to_its_own_section() -> None:
    for version in ("0.8.0 Beta 2", "v0.8.0-beta2"):
        assert "Beta two body." in extract_version_section(TWO_BETAS, version)
        assert "Beta one body." not in extract_version_section(TWO_BETAS, version)


def test_bare_base_version_picks_newest_same_base() -> None:
    # A stable-looking 0.8.0 with no exact heading falls back to the newest 0.8.0.x.
    assert "Beta two body." in extract_version_section(TWO_BETAS, "0.8.0")


def test_unknown_version_returns_empty() -> None:
    assert extract_version_section(CHANGELOG, "9.9.9") == ""


def test_release_notes_for_flattens_markdown(monkeypatch) -> None:
    monkeypatch.setattr("quill.core.release_notes.load_changelog_text", lambda: CHANGELOG)
    notes = release_notes_for("0.8.0 Beta 1")
    # Markdown emphasis/code markers are stripped for the plain-text edit.
    assert "**" not in notes
    assert "`" not in notes
    assert "Bold feature with code." in notes
    assert "Section A" in notes


def test_release_notes_for_unknown_is_empty(monkeypatch) -> None:
    monkeypatch.setattr("quill.core.release_notes.load_changelog_text", lambda: CHANGELOG)
    assert release_notes_for("9.9.9") == ""
