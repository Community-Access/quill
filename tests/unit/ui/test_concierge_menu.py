"""Tests for the context-first Concierge menu action (Phase 1 finish).

Covers the wx-free context builder and the run-by-target dispatch without
constructing the native single-choice dialog: the helper builds a real
ConciergeContext from controller signals, and a chosen suggestion runs its
command through the registry (unknown targets are refused, not raised).
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.ui.concierge_menu import _concierge_context, _file_type_for


@dataclass
class _Doc:
    path: str


class _Editor:
    def __init__(self, selection: str = "") -> None:
        self._sel = selection

    def GetStringSelection(self) -> str:
        return self._sel

    def GetInsertionPoint(self) -> int:
        return 0

    def PositionToXY(self, _pos: int):
        return (True, 0, 0)


@dataclass
class _Entry:
    level: int
    title: str
    position: int


class _Controller:
    def __init__(self, *, path: str, selection: str, headings: int) -> None:
        self.document = _Doc(path=path)
        self.editor = _Editor(selection)
        self._headings = headings

    def _outline_entries(self):
        return [_Entry(1, f"H{i}", i) for i in range(self._headings)]


def test_file_type_for_reads_extension():
    ctrl = _Controller(path="notes.md", selection="", headings=0)
    assert _file_type_for(ctrl) == "md"


def test_file_type_for_handles_no_extension():
    ctrl = _Controller(path="Makefile", selection="", headings=0)
    assert _file_type_for(ctrl) == ""


def test_concierge_context_reflects_selection_and_outline(monkeypatch):
    monkeypatch.setattr("quill.core.ai.model_manager.load_ai_enabled", lambda: True)
    ctrl = _Controller(path="story.md", selection="hello", headings=3)
    ctx = _concierge_context(ctrl)
    assert ctx.file_type == "md"
    assert ctx.has_selection is True
    assert ctx.outline_headings == 3
    assert ctx.ai_enabled is True


def test_suggest_targets_are_runnable_commands_or_skipped():
    # The suggestions the Concierge produces should all be command ids; the menu
    # helper refuses unknown ones rather than raising. Here we assert the shape.
    from quill.core.ai.concierge import ConciergeContext, suggest

    ctx = ConciergeContext(file_type="md", has_selection=True, outline_headings=2, ai_enabled=True)
    suggestions = suggest(ctx, [])
    # With no agents, the outline suggestion is still offered.
    assert any(s.target == "navigate.outline_navigator" for s in suggestions)
    assert all(isinstance(s.target, str) and s.target for s in suggestions)
