from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.release_readiness import (
    EPUB_SOURCE_DATE_EPOCH,
    _epub_identifier,
    _pandoc_sources,
)

_DOC_RENDER_PS1 = Path("scripts/DocRender.ps1")


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("standalone/radio/docs/prd.md", "urn:quill:standalone-radio-docs-prd"),
        ("docs/user guide/userguide.md", "urn:quill:docs-user-guide-userguide"),
        ("docs/release-notes-2.2.md", "urn:quill:docs-release-notes-2-2"),
        ("docs/CHANGELOG.md", "urn:quill:docs-changelog"),
    ],
)
def test_identifier_is_derived_from_the_path(source: str, expected: str) -> None:
    assert _epub_identifier(Path(source)) == expected


def test_identifier_is_urn_safe() -> None:
    """Spaces and punctuation must not survive into the URN."""
    identifier = _epub_identifier(Path("docs/Product Requirement Documents/QUILL-PRD.md"))
    assert identifier.startswith("urn:quill:")
    assert re.fullmatch(r"urn:quill:[a-z0-9-]+", identifier)


def test_identifier_is_stable_across_calls() -> None:
    """The whole point: no randomness, so a rebuild reproduces the same bytes."""
    source = Path("standalone/weather/docs/prd.md")
    assert _epub_identifier(source) == _epub_identifier(source)


def test_identifiers_are_unique_across_the_real_docs_tree() -> None:
    """Two documents collapsing to one identifier would give them one identity.

    Slugging is lossy -- "release-notes.md" and "release notes.md" both become
    "release-notes" -- so guard the actual tree rather than assume.
    """
    sources = _pandoc_sources(Path("docs"))
    assert sources, "expected to find Markdown under docs/"
    by_identifier: dict[str, list[str]] = {}
    for source in sources:
        by_identifier.setdefault(_epub_identifier(source), []).append(source.as_posix())
    collisions = {key: paths for key, paths in by_identifier.items() if len(paths) > 1}
    assert not collisions, f"identifier collisions: {collisions}"


def test_epoch_matches_the_powershell_implementation() -> None:
    """The two renderers must agree, or output depends on which one ran."""
    source = _DOC_RENDER_PS1.read_text(encoding="utf-8")
    match = re.search(r'\$script:QuillSourceDateEpoch\s*=\s*"(\d+)"', source)
    assert match, "QuillSourceDateEpoch not found in scripts/DocRender.ps1"
    assert match.group(1) == EPUB_SOURCE_DATE_EPOCH


def test_powershell_scripts_pin_the_epoch_and_identifier() -> None:
    """Every render script must go through both determinism controls."""
    for app in ("radio", "weather", "cast", "social", "studio"):
        script = Path(f"standalone/{app}/scripts/render_docs.ps1").read_text(encoding="utf-8")
        assert "Invoke-WithSourceDateEpoch" in script, f"{app} does not pin SOURCE_DATE_EPOCH"
        assert "Get-QuillEpubIdentifier" in script, f"{app} does not pin the EPUB identifier"
        assert "identifier=$epubId" in script, f"{app} does not pass the identifier to Pandoc"
