from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_docs_artifacts import _is_docs_markdown, _validate_docs_artifacts


@pytest.mark.parametrize(
    "path",
    [
        "docs/overview.md",
        "docs/qa/checklist.md",
        "docs/engineering/notes/deep.md",
        "standalone/radio/docs/prd.md",
        "standalone/weather/docs/release-notes-2.2.md",
        "standalone/social/docs/nested/topic.md",
    ],
)
def test_guarded_markdown_roots(path: str) -> None:
    assert _is_docs_markdown(Path(path))


@pytest.mark.parametrize(
    "path",
    [
        "docs/overview.html",
        "docs/overview.epub",
        "standalone/radio/scripts/render_docs.md",
        "standalone/radio/docs.md",
        "standalone/radio/README.md",
        "quill/core/notes.md",
        "README.md",
    ],
)
def test_unguarded_paths(path: str) -> None:
    assert not _is_docs_markdown(Path(path))


def test_standalone_markdown_requires_regenerated_artifacts() -> None:
    """The standalone root was previously unguarded, letting artifacts drift stale."""
    errors = _validate_docs_artifacts({"standalone/radio/docs/prd.md"})
    assert len(errors) == 1
    assert "standalone/radio/docs/prd.epub" in errors[0]
    assert "standalone/radio/docs/prd.html" in errors[0]


def test_standalone_markdown_with_both_artifacts_passes() -> None:
    assert not _validate_docs_artifacts({
        "standalone/radio/docs/prd.md",
        "standalone/radio/docs/prd.html",
        "standalone/radio/docs/prd.epub",
    })


def test_partial_artifact_regeneration_is_reported() -> None:
    errors = _validate_docs_artifacts({
        "standalone/weather/docs/prd.md",
        "standalone/weather/docs/prd.html",
    })
    assert len(errors) == 1
    assert "standalone/weather/docs/prd.epub" in errors[0]
    assert "standalone/weather/docs/prd.html" not in errors[0]


def test_deleted_markdown_does_not_demand_artifacts() -> None:
    assert not _validate_docs_artifacts({"standalone/radio/docs/removed-doc.md"})
