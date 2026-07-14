"""Tests for verbosity Safe Mode and scoped resets (§29)."""

from __future__ import annotations

from quill.core.verbosity.profiles import CustomProfile
from quill.core.verbosity.safe_mode import (
    VerbositySafeMode,
    reset_chord,
    reset_verb,
    restore_builtin,
)


def test_toggle_state() -> None:
    safe = VerbositySafeMode()
    assert not safe.is_active
    safe.enter()
    assert safe.is_active
    safe.exit()
    assert not safe.is_active


def test_from_env_truthy_values() -> None:
    assert VerbositySafeMode.from_env({"QUILL_SAFE_MODE": "1"})
    assert VerbositySafeMode.from_env({"QUILL_VERBOSITY_SAFE_MODE": "true"})
    assert not VerbositySafeMode.from_env({"QUILL_SAFE_MODE": "0"})
    assert not VerbositySafeMode.from_env({})


def _custom() -> CustomProfile:
    return CustomProfile(
        name="Mine",
        per_verb_overrides={"nav.next_line": "L{line}", "doc.save": "S"},
        per_chord_overrides={"ctrl+s": "save"},
        templates={"Concise": "{line}"},
        data_order={"nav.next_line": ["line"]},
    )


def test_reset_verb_scoped() -> None:
    result = reset_verb(_custom(), "nav.next_line")
    assert "nav.next_line" not in result.per_verb_overrides
    assert "doc.save" in result.per_verb_overrides  # untouched
    assert "nav.next_line" not in result.data_order


def test_reset_chord_scoped() -> None:
    result = reset_chord(_custom(), "ctrl+s")
    assert "ctrl+s" not in result.per_chord_overrides
    assert result.per_verb_overrides == _custom().per_verb_overrides


def test_restore_builtin_clears_all_overrides() -> None:
    result = restore_builtin(_custom())
    assert result.per_verb_overrides == {}
    assert result.per_chord_overrides == {}
    assert result.templates == {}
    assert result.data_order == {}
    assert result.name == "Mine"  # identity preserved, overrides cleared


def test_reset_is_nondestructive_to_original() -> None:
    original = _custom()
    reset_verb(original, "doc.save")
    assert "doc.save" in original.per_verb_overrides  # original unchanged
