"""Tests for the persistent skill store (AI Library, Phase 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.skill_pack import SQP_SCHEMA, SkillValidationError
from quill.core.skill_store import InstalledSkill, SkillStore, slugify_skill_name


def _skill_source(name: str = "My Skill", description: str = "A test skill.") -> str:
    return (
        "---\n"
        f"schema: {SQP_SCHEMA}\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "author: Tester\n"
        "version: 2.1.0\n"
        "---\n"
        "\n"
        "# Step 1: Do something\n"
        "\n"
        "Write one sentence about {selection}.\n"
    )


def _store(tmp_path: Path) -> SkillStore:
    return SkillStore(tmp_path / "skills")


def test_slugify_is_stable_and_safe() -> None:
    assert slugify_skill_name("My Skill!") == "my-skill"
    assert slugify_skill_name("  Hello   World  ") == "hello-world"
    assert slugify_skill_name("***") == "skill"


def test_empty_store_lists_nothing(tmp_path: Path) -> None:
    assert _store(tmp_path).all() == []


def test_add_source_installs_and_lists(tmp_path: Path) -> None:
    store = _store(tmp_path)
    skill = store.add_source(_skill_source())

    assert isinstance(skill, InstalledSkill)
    assert skill.id == "my-skill"
    assert skill.name == "My Skill"
    assert skill.description == "A test skill."
    assert skill.author == "Tester"
    assert skill.version == "2.1.0"
    assert skill.enabled is True

    listed = store.all()
    assert [s.id for s in listed] == ["my-skill"]


def test_reimporting_same_name_replaces_not_duplicates(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.add_source(_skill_source(description="v1"))
    store.add_source(_skill_source(description="v2"))

    listed = store.all()
    assert len(listed) == 1
    assert listed[0].description == "v2"


def test_invalid_source_raises_and_installs_nothing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(SkillValidationError):
        store.add_source("---\nschema: quill.skill/99\nname: Bad\n---\n\nNo steps.\n")
    assert store.all() == []


def test_source_is_preserved_verbatim(tmp_path: Path) -> None:
    store = _store(tmp_path)
    source = _skill_source()
    store.add_source(source)
    assert store.get_source("my-skill") == source


def test_enable_disable_persists(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.add_source(_skill_source())
    store.disable("my-skill")

    # A fresh store instance reads the persisted enabled-state.
    reopened = _store(tmp_path)
    skill = reopened.find_by_id("my-skill")
    assert skill is not None
    assert skill.enabled is False

    reopened.enable("my-skill")
    assert _store(tmp_path).find_by_id("my-skill").enabled is True


def test_remove_deletes_skill_and_state(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.add_source(_skill_source())
    store.disable("my-skill")
    store.remove("my-skill")

    assert store.all() == []
    assert store.find_by_id("my-skill") is None
    with pytest.raises(KeyError):
        store.remove("my-skill")


def test_import_and_export_round_trip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    src_path = tmp_path / "incoming.sqp"
    src_path.write_text(_skill_source(name="Round Trip"), encoding="utf-8")
    store.import_sqp(src_path)

    out_path = tmp_path / "out.sqp"
    store.export_sqp("round-trip", out_path)
    assert out_path.read_text(encoding="utf-8") == _skill_source(name="Round Trip")


def test_find_by_name(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.add_source(_skill_source(name="Find Me"))
    found = store.find_by_name("Find Me")
    assert found is not None
    assert found.id == "find-me"


def test_unparseable_file_is_skipped_not_fatal(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.add_source(_skill_source())
    # Drop a junk .sqp next to the good one; all() must not raise.
    (tmp_path / "skills" / "junk.sqp").write_text("not a skill", encoding="utf-8")
    listed = store.all()
    assert [s.id for s in listed] == ["my-skill"]
