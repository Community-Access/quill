"""Scenario-based verbosity preview renderer (§23).

The Preview Lab lets a user (or a QVP author) hear how a profile, template, or
channel mix behaves against canned, representative scenarios — plain-text
editing, long-document navigation, a search, an error, a print-page jump, and so
on — without having to reproduce each situation for real. This module owns the
fourteen built-in scenarios and renders each through a supplied
:class:`~quill.core.verbosity.engine.VerbosityEngine`, surfacing the per-channel
output and the decision metadata. The Lab dialog (sub-PR 1.4) presents it.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quill.core.verbosity.engine import VerbosityEngine

__all__ = ["Scenario", "PreviewOutput", "BUILTIN_SCENARIOS", "preview_scenario", "preview_all"]


@dataclass(frozen=True, slots=True)
class Scenario:
    """A canned situation: a verb to fire and the context to fire it with."""

    id: str
    name: str
    verb_id: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PreviewOutput:
    """What a scenario produces under the previewed engine settings."""

    scenario_id: str
    scenario_name: str
    speech: str
    braille: str
    visual: str
    sound_event: str | None
    suppressed: str
    profile: str
    template_source: str
    channels: str


#: The fourteen built-in Preview Lab scenarios (§23).
BUILTIN_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "plain_text_editing",
        "Plain text editing",
        "edit.insert_text",
        {"text": "The quick brown fox", "count": 4},
    ),
    Scenario(
        "long_document_navigation",
        "Long document navigation",
        "nav.next_line",
        {"line": 128, "total": 540, "text": "chapter two"},
    ),
    Scenario(
        "markdown_document",
        "Markdown document",
        "doc.open",
        {"name": "README.md", "encoding": "utf-8"},
    ),
    Scenario("code_file", "Code file", "doc.open", {"name": "engine.py", "encoding": "utf-8"}),
    Scenario(
        "search_results", "Search results", "search.find", {"query": "widget", "match_total": 12}
    ),
    Scenario(
        "replace_operation",
        "Replace operation",
        "search.replace_all",
        {"query": "colour", "replacements": 7},
    ),
    Scenario("save_file", "Save file", "doc.save", {"name": "report.md"}),
    Scenario("open_file", "Open file", "doc.open", {"name": "report.md", "encoding": "utf-8"}),
    Scenario("error_state", "Error state", "system.error", {"message": "Disk full"}),
    Scenario("warning_state", "Warning state", "system.warning", {"message": "Unsaved changes"}),
    Scenario(
        "selection_movement",
        "Selection movement",
        "edit.select_word_right",
        {"word": "announcement", "count": 1},
    ),
    Scenario(
        "print_page_navigation",
        "Print page navigation",
        "nav.next_print_page",
        {"page": "7", "total": 87},
    ),
    Scenario(
        "status_progress_update",
        "Status / progress update",
        "system.progress",
        {"message": "Converting", "percent": 40},
    ),
    Scenario(
        "braille_workflow_sample",
        "Braille workflow sample",
        "doc.open",
        {"name": "primer.brf", "encoding": "utf-8"},
    ),
)


def preview_scenario(scenario: Scenario, engine: VerbosityEngine) -> PreviewOutput:
    """Render one scenario through ``engine`` and surface every channel + meta."""
    result = engine.speak(scenario.verb_id, scenario.context, trigger=scenario.name)
    return PreviewOutput(
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        speech=result.speech,
        braille=result.braille,
        visual=result.visual,
        sound_event=result.sound_event,
        # When speech was suppressed, surface what *would* have been said.
        suppressed=result.visual if result.suppressed else "",
        profile=result.profile,
        template_source=result.template_source,
        channels=result.trace.channels,
    )


def preview_all(engine: VerbosityEngine) -> tuple[PreviewOutput, ...]:
    """Render every built-in scenario through ``engine``."""
    return tuple(preview_scenario(scenario, engine) for scenario in BUILTIN_SCENARIOS)
