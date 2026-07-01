"""Seam tests for StoryElementFormDialog (no live wx control tree).

Guards the wx-free logic: which rows the form shows for an element, and how the
edited control values map back to a fields dict. The control layout and keyboard
behavior are exercised by hand with a screen reader.
"""

from __future__ import annotations

from quill.core.story.model import ElementKind
from quill.ui.story_element_form_dialog import StoryElementFormDialog


def _form(kind: ElementKind, fields: dict | None = None, on_save=None):
    return StoryElementFormDialog(wx=object(), kind=kind, fields=fields or {}, on_save=on_save)


def test_rows_match_the_kind_schema() -> None:
    form = _form(ElementKind.CHARACTER, {"goal": "Win"})
    assert [r.key for r in form.rows] == ["role", "goal", "motivation", "arc", "tags"]
    assert next(r for r in form.rows if r.key == "goal").value == "Win"


def test_result_fields_merges_edits_and_preserves_type() -> None:
    form = _form(ElementKind.PLOT, {"type": "plot", "mood": "tense"})
    result = form.result_fields({"status": "resolved", "mood": "calm", "tags": "a, b"})
    assert result == {"type": "plot", "status": "resolved", "mood": "calm", "tags": ["a", "b"]}


def test_result_fields_drops_cleared_values() -> None:
    form = _form(ElementKind.CHARACTER, {"role": "protagonist"})
    result = form.result_fields({"role": "", "goal": "", "tags": ""})
    assert result == {}
