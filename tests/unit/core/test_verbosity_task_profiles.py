"""Tests for task-aware profile suggestions (§31)."""

from __future__ import annotations

from quill.core.verbosity.task_profiles import TaskProfileSuggester


def test_default_is_off_no_suggestions() -> None:
    suggester = TaskProfileSuggester()
    assert not suggester.enabled
    assert suggester.suggestion_for("notes.md") is None


def test_enabled_suggests_for_mapped_extension() -> None:
    suggester = TaskProfileSuggester(enabled=True)
    assert suggester.suggestion_for("notes.md") == "Normal"
    assert suggester.suggestion_for("script.py") == "Expert"


def test_unmapped_extension_returns_none() -> None:
    suggester = TaskProfileSuggester(enabled=True)
    assert suggester.suggestion_for("photo.png") is None


def test_reject_silences_extension() -> None:
    suggester = TaskProfileSuggester(enabled=True)
    suggester.reject(".md")
    assert suggester.suggestion_for("notes.md") is None


def test_accept_maps_and_clears_rejection() -> None:
    suggester = TaskProfileSuggester(enabled=True)
    suggester.reject(".md")
    suggester.accept(".md", "Beginner")
    assert suggester.suggestion_for("notes.md") == "Beginner"


def test_round_trip() -> None:
    suggester = TaskProfileSuggester(enabled=True)
    suggester.accept(".rst", "Expert")
    suggester.reject(".md")
    restored = TaskProfileSuggester.from_dict(suggester.to_dict())
    assert restored.enabled
    assert restored.suggestion_for("doc.rst") == "Expert"
    assert restored.suggestion_for("notes.md") is None
