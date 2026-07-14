"""Agent Catalog: validation, parsing, bundled load, and schema/code agreement."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.ai import agent_catalog
from quill.core.ai.agent_catalog import (
    SCHEMA_ID,
    AgentSpecError,
    bundled_agents_dir,
    load_catalog,
    load_full_catalog,
    parse_agent,
    save_user_agent,
    validate_agent,
)
from quill.core.ai.permissions import Decision, PermissionCategory, RiskLevel

_GOOD = {
    "schema": "quill.agent/1",
    "id": "writing-companion",
    "display_name": "Writing Companion",
    "system_prompt": "Improve the text.",
    "risk": "low",
    "default_scope": "selection",
    "recommended_file_types": ["md"],
    "tools": ["edit.undo"],
    "permissions": {"modify_selection": "preview_required"},
}


_AGENT_MD = """---
id: topic-mapper
display_name: Topic Mapper
description: Map and summarise topics.
risk: low
default_scope: full_document
---

You are Topic Mapper. Help the user map and summarise topics.
"""


def test_save_user_agent_writes_and_load_full_catalog_finds_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_catalog, "user_agents_dir", lambda: tmp_path / "agents")
    spec = save_user_agent(_AGENT_MD)
    assert spec.id == "topic-mapper"
    # The file landed in the user agents dir and the combined catalog includes it.
    assert (tmp_path / "agents" / "topic-mapper.md").is_file()
    full = load_full_catalog()
    assert "topic-mapper" in full.ids()
    # Bundled agents are still present (user agents are additive).
    assert len(full.agents) > 1


def test_save_user_agent_rejects_invalid_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_catalog, "user_agents_dir", lambda: tmp_path / "agents")
    with pytest.raises(AgentSpecError):
        save_user_agent("---\nid: bad\n---\n\nMissing display_name and a usable spec.")
    # Nothing was written on failure.
    assert not (tmp_path / "agents").exists() or not list((tmp_path / "agents").glob("*.md"))


def test_valid_spec_has_no_problems() -> None:
    assert validate_agent(_GOOD) == []


def test_parse_builds_agentspec_with_overrides() -> None:
    spec = parse_agent(_GOOD)
    assert spec.id == "writing-companion"
    assert spec.risk is RiskLevel.LOW
    assert spec.tools == ("edit.undo",)
    assert spec.overrides_map() == {PermissionCategory.MODIFY_SELECTION: Decision.PREVIEW_REQUIRED}


def test_missing_required_fields_reported() -> None:
    problems = validate_agent({"schema": SCHEMA_ID})
    assert any("id" in p for p in problems)
    assert any("display_name" in p for p in problems)
    assert any("system_prompt" in p for p in problems)


def test_unknown_key_rejected() -> None:
    bad = dict(_GOOD, surprise=1)
    assert any("Unknown key" in p for p in validate_agent(bad))


def test_bad_id_pattern_rejected() -> None:
    bad = dict(_GOOD, id="Not Valid")
    assert any("id" in p for p in validate_agent(bad))


def test_bad_enum_values_rejected() -> None:
    assert any("risk" in p for p in validate_agent(dict(_GOOD, risk="spicy")))
    assert any("default_scope" in p for p in validate_agent(dict(_GOOD, default_scope="moon")))


def test_bad_permission_values_rejected() -> None:
    bad = dict(_GOOD, permissions={"modify_selection": "whenever", "bogus": "allow"})
    problems = validate_agent(bad)
    assert any("decision" in p for p in problems)
    assert any("category" in p for p in problems)


def test_parse_raises_on_invalid() -> None:
    with pytest.raises(AgentSpecError) as exc:
        parse_agent({"schema": SCHEMA_ID})
    assert exc.value.problems


def test_non_object_is_invalid() -> None:
    assert validate_agent([1, 2, 3]) == ["Agent spec must be a JSON object."]


def test_bundled_catalog_loads_clean() -> None:
    result = load_catalog()
    assert result.errors == ()
    ids = set(result.ids())
    # The PRD launch set must be present.
    for expected in {
        "writing-companion",
        "accessibility-editor",
        "summarizer",
        "researcher",
        "reviewer",
        "markdown-publisher",
        "code-doctor",
        "github-maintainer",
        "prd-architect",
        "release-notes-builder",
        "quill-concierge",
    }:
        assert expected in ids


def test_load_catalog_skips_bad_file_without_aborting(tmp_path: Path) -> None:
    (tmp_path / "good.json").write_text(json.dumps(_GOOD), encoding="utf-8")
    (tmp_path / "bad.json").write_text("{ not json", encoding="utf-8")
    (tmp_path / "invalid.json").write_text(json.dumps({"schema": SCHEMA_ID}), encoding="utf-8")
    result = load_catalog(tmp_path)
    assert result.ids() == ["writing-companion"]
    assert len(result.errors) >= 2


def test_later_dir_overrides_earlier_id(tmp_path: Path) -> None:
    d1 = tmp_path / "bundled"
    d2 = tmp_path / "user"
    d1.mkdir()
    d2.mkdir()
    (d1 / "a.json").write_text(json.dumps(dict(_GOOD, display_name="Bundled")), encoding="utf-8")
    (d2 / "a.json").write_text(json.dumps(dict(_GOOD, display_name="User")), encoding="utf-8")
    result = load_catalog(d1, d2)
    assert len(result.agents) == 1
    assert result.agents[0].display_name == "User"


def test_schema_enums_match_code() -> None:
    # The published JSON schema and the hand-rolled validator must agree on enums.
    schema = json.loads((bundled_agents_dir().parent.parent / "schemas" / "agent.json").read_text())
    props = schema["properties"]
    assert set(props["risk"]["enum"]) == {m.value for m in RiskLevel}
    assert set(props["permissions"]["additionalProperties"]["enum"]) == {m.value for m in Decision}
    perm_cats = set(props["permissions"]["propertyNames"]["enum"])
    assert perm_cats == {m.value for m in PermissionCategory}


def test_needs_tool_use_field() -> None:
    # Schema advertises it, validator type-checks it, and it round-trips to AgentSpec.
    schema = json.loads((bundled_agents_dir().parent.parent / "schemas" / "agent.json").read_text())
    assert schema["properties"]["needs_tool_use"]["type"] == "boolean"
    bad = validate_agent(dict(_GOOD, needs_tool_use="yes"))
    assert bad == ["needs_tool_use must be a boolean."]
    assert parse_agent(dict(_GOOD, needs_tool_use=True)).needs_tool_use is True
    assert parse_agent(_GOOD).needs_tool_use is False  # defaults off
