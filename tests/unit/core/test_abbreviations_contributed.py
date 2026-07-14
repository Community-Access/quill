"""Unit tests for building an in-memory library from Quillin-contributed
abbreviations (manifest ``contributes.abbreviations``)."""

from __future__ import annotations

from quill.core.abbreviations import (
    build_contributed_library,
    contributed_abbreviation_id,
    try_expand,
)


def _contribs():
    return [
        (
            "com.quill.smartinsert",
            [
                {"trigger": "qbug", "expansion": "Bug:\n${cursor}", "description": "Bug"},
                {"trigger": "qlog", "expansion": "${date}", "enabled_by_default": True},
                # Handler-based: cannot expand inline, must be skipped.
                {"trigger": "qbrf", "handler": "insert_brf_test"},
            ],
        )
    ]


class TestBuildContributedLibrary:
    def test_includes_static_expansions(self) -> None:
        lib = build_contributed_library(_contribs())
        triggers = {a.abbreviation for a in lib.abbreviations}
        assert triggers == {"qbug", "qlog"}

    def test_handler_based_entries_are_skipped(self) -> None:
        lib = build_contributed_library(_contribs())
        assert all(a.abbreviation != "qbrf" for a in lib.abbreviations)

    def test_ids_are_deterministic_and_namespaced(self) -> None:
        lib = build_contributed_library(_contribs())
        qbug = next(a for a in lib.abbreviations if a.abbreviation == "qbug")
        assert qbug.id == contributed_abbreviation_id("com.quill.smartinsert", "qbug")

    def test_is_enabled_callback_filters(self) -> None:
        lib = build_contributed_library(
            _contribs(),
            is_enabled=lambda quillin_id, trigger, default: trigger != "qbug",
        )
        assert {a.abbreviation for a in lib.abbreviations} == {"qlog"}

    def test_enabled_by_default_false_is_dropped_without_callback(self) -> None:
        contribs = [("q", [{"trigger": "x", "expansion": "y", "enabled_by_default": False}])]
        lib = build_contributed_library(contribs)
        assert lib.abbreviations == []

    def test_malformed_entries_are_skipped(self) -> None:
        contribs = [
            ("q", [{"expansion": "no trigger"}, "junk", {"trigger": "ok", "expansion": "v"}])
        ]
        lib = build_contributed_library(contribs)
        assert {a.abbreviation for a in lib.abbreviations} == {"ok"}

    def test_result_is_usable_by_try_expand(self) -> None:
        lib = build_contributed_library(_contribs())
        # Typing "qbug " triggers expansion via the standard engine.
        match = try_expand("qbug ", 5, lib)
        assert match is not None
        assert match.resolved_text.startswith("Bug:")
