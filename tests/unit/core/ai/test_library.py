"""Tests for the unified AI Library view + Promote continuum."""

from __future__ import annotations

from pathlib import Path

from quill.core.ai.agent_catalog import parse_agent, parse_agent_markdown, validate_agent
from quill.core.ai.library import (
    LibraryItem,
    list_agents,
    list_prompts,
    list_skills,
    prompt_to_skill_source,
    skill_to_agent_markdown,
)
from quill.core.prompt_library import PromptLibrary
from quill.core.skill_pack import parse_skill
from quill.core.skill_store import SkillStore


def _skill_source(name: str = "My Skill") -> str:
    from quill.core.skill_pack import SQP_SCHEMA

    return (
        f"---\nschema: {SQP_SCHEMA}\nname: {name}\ndescription: A skill.\n"
        "author: T\nversion: 1.0.0\n---\n\n# Step 1: Analyse\n\nList topics in {selection}.\n\n"
        "# Step 2: Summarise\n\nSummarise {step1.output}.\n"
    )


def test_list_prompts_maps_uniformly(tmp_path: Path) -> None:
    lib = PromptLibrary(tmp_path / "prompts.json")
    items = list_prompts(lib)
    assert items
    assert all(isinstance(i, LibraryItem) and i.kind == "prompt" for i in items)
    assert all(i.can_promote and i.promote_label == "Promote to Skill" for i in items)


def test_list_skills_maps_uniformly(tmp_path: Path) -> None:
    store = SkillStore(tmp_path / "skills")
    store.add_source(_skill_source())
    items = list_skills(store)
    assert [i.kind for i in items] == ["skill"]
    assert items[0].name == "My Skill"
    assert items[0].promote_label == "Promote to Agent"


def test_list_agents_maps_uniformly() -> None:
    from quill.core.ai.agent_catalog import load_catalog

    items = list_agents(list(load_catalog().agents))
    assert len(items) >= 15
    assert all(i.kind == "agent" and i.is_builtin for i in items)
    assert all(not i.can_promote for i in items)  # agents are the top tier
    # sorted by name (case-insensitive)
    assert [i.name for i in items] == sorted((i.name for i in items), key=str.lower)


def test_prompt_to_skill_source_parses_as_valid_skill() -> None:
    source = prompt_to_skill_source("Warm Rewrite", "Rewrite {selection} warmly.")
    pack = parse_skill(source)  # must not raise
    assert pack.name == "Warm Rewrite"
    assert len(pack.steps) == 1
    assert "warmly" in pack.steps[0].prompt_template


def test_prompt_to_skill_source_handles_empty_text() -> None:
    source = prompt_to_skill_source("", "")
    pack = parse_skill(source)
    assert pack.name == "Untitled Skill"
    assert len(pack.steps) == 1


def test_skill_to_agent_markdown_parses_and_validates() -> None:
    store_source = _skill_source(name="Topic Mapper")

    class _S:
        name = "Topic Mapper"
        description = "Map and summarise topics."
        source = store_source

    md = skill_to_agent_markdown(_S())
    raw = parse_agent_markdown(md)
    assert validate_agent(raw) == []  # generated agent is structurally valid
    spec = parse_agent(raw)
    assert spec.id == "topic-mapper"
    assert spec.display_name == "Topic Mapper"
    # step headings carried into the system prompt
    assert "Analyse" in spec.system_prompt and "Summarise" in spec.system_prompt
