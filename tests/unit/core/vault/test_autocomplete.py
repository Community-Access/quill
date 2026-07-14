"""Tests for the wikilink/tag completion core (wx-free)."""

from __future__ import annotations

from pathlib import Path

from quill.core.vault.autocomplete import (
    active_trigger,
    completion_edit,
    wikilink_candidates,
)
from quill.core.vault.vault import scan_vault

# --- trigger detection -----------------------------------------------------


def test_wikilink_trigger_detected_with_prefix() -> None:
    text = "See [[Al here"
    trig = active_trigger(text, len("See [[Al"))
    assert trig is not None
    assert trig.kind == "wikilink" and trig.prefix == "Al" and trig.start == len("See [[")
    assert trig.has_close is False


def test_wikilink_trigger_notices_existing_close() -> None:
    text = "See [[Al]]"
    trig = active_trigger(text, len("See [[Al"))
    assert trig is not None and trig.has_close is True


def test_closed_wikilink_is_not_a_trigger() -> None:
    text = "See [[Note]] and more"
    assert active_trigger(text, len(text)) is None


def test_tag_trigger_detected() -> None:
    trig = active_trigger("a line with #pro", len("a line with #pro"))
    assert trig is not None and trig.kind == "tag" and trig.prefix == "pro"


def test_hash_inside_wikilink_is_not_a_tag() -> None:
    text = "[[Note#Sec"
    trig = active_trigger(text, len(text))
    assert trig is not None and trig.kind == "wikilink"  # the # is a heading ref, not a tag


# --- candidates ------------------------------------------------------------


def test_wikilink_candidates_prefix_then_substring(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# Alpha\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("# Beta Alpha\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("# Gamma\n", encoding="utf-8")
    vault = scan_vault(tmp_path)
    assert wikilink_candidates(vault, "al") == ["Alpha", "Beta Alpha"]  # prefix first
    assert "Gamma" in wikilink_candidates(vault, "")  # empty = all


# --- edit computation ------------------------------------------------------


def test_completion_edit_wikilink_adds_close() -> None:
    trig = active_trigger("x [[Al", len("x [[Al"))
    assert trig is not None
    start, end, new = completion_edit(trig, "Alpha", len("x [[Al"))
    assert (start, end, new) == (len("x [["), len("x [[Al"), "Alpha]]")


def test_completion_edit_wikilink_keeps_existing_close() -> None:
    trig = active_trigger("x [[Al]]", len("x [[Al"))
    assert trig is not None
    _s, _e, new = completion_edit(trig, "Alpha", len("x [[Al"))
    assert new == "Alpha"  # no extra ]] since one already follows


def test_completion_edit_tag() -> None:
    trig = active_trigger("see #pr", len("see #pr"))
    assert trig is not None
    start, end, new = completion_edit(trig, "project", len("see #pr"))
    assert (start, end, new) == (len("see #"), len("see #pr"), "project")
