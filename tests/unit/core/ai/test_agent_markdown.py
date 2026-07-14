"""Markdown-with-front-matter agent authoring (the agent standard)."""

from __future__ import annotations

from pathlib import Path

from quill.core.ai.agent_catalog import (
    SCHEMA_ID,
    bundled_agents_dir,
    load_catalog,
    parse_agent,
    parse_agent_markdown,
    validate_agent,
)

_SAMPLE = """\
---
id: tidy-editor
display_name: Tidy Editor
description: Tighten prose without changing meaning.
risk: medium
default_scope: full_document
recommended_file_types: [md, txt]
default_harness: auto
permissions:
  read_document: ask
  modify_document: preview_required
---

You are a careful copy editor. Tighten the prose, keep the author's voice, and
never change the meaning.

Return the full revised document.
"""


def test_body_becomes_system_prompt() -> None:
    data = parse_agent_markdown(_SAMPLE)
    assert data["system_prompt"].startswith("You are a careful copy editor.")
    assert "Return the full revised document." in data["system_prompt"]
    # Schema is implied for Markdown agents.
    assert data["schema"] == SCHEMA_ID


def test_front_matter_scalars_lists_and_nested_map() -> None:
    data = parse_agent_markdown(_SAMPLE)
    assert data["id"] == "tidy-editor"
    assert data["risk"] == "medium"
    assert data["recommended_file_types"] == ["md", "txt"]
    assert data["permissions"] == {
        "read_document": "ask",
        "modify_document": "preview_required",
    }


def test_markdown_agent_validates_and_parses_to_spec() -> None:
    data = parse_agent_markdown(_SAMPLE)
    assert validate_agent(data) == []
    spec = parse_agent(data)
    assert spec.id == "tidy-editor"
    assert spec.default_scope.value == "full_document"
    assert spec.recommended_file_types == ("md", "txt")
    assert {c.value: d.value for c, d in spec.overrides_map().items()} == {
        "read_document": "ask",
        "modify_document": "preview_required",
    }


def test_missing_body_is_reported_as_missing_system_prompt() -> None:
    no_body = "---\nid: x\ndisplay_name: X\n---\n"
    problems = validate_agent(parse_agent_markdown(no_body))
    assert any("system_prompt" in p for p in problems)


def test_load_catalog_reads_markdown(tmp_path: Path) -> None:
    (tmp_path / "tidy-editor.md").write_text(_SAMPLE, encoding="utf-8")
    result = load_catalog(tmp_path)
    assert result.errors == ()
    assert result.ids() == ["tidy-editor"]


def test_readme_is_skipped_not_parsed_as_agent(tmp_path: Path) -> None:
    (tmp_path / "tidy-editor.md").write_text(_SAMPLE, encoding="utf-8")
    (tmp_path / "README.md").write_text("# docs, not an agent\n", encoding="utf-8")
    (tmp_path / "_template.md").write_text("# partial\n", encoding="utf-8")
    result = load_catalog(tmp_path)
    assert result.errors == ()
    assert result.ids() == ["tidy-editor"]


def test_bundled_agents_are_markdown() -> None:
    # The shipped catalog is authored in Markdown now (no JSON left behind).
    agents_dir = bundled_agents_dir()
    assert list(agents_dir.glob("*.json")) == []
    md_files = [p for p in agents_dir.glob("*.md") if p.stem.lower() != "readme"]
    assert len(md_files) >= 15
