"""Concierge suggestions, agent recommendation, and the Selection Action Ring."""

from __future__ import annotations

from quill.core.ai.agent_catalog import load_catalog
from quill.core.ai.concierge import (
    ConciergeContext,
    RingAction,
    recommend_agents,
    ring_actions,
    suggest,
    write_kind,
)
from quill.core.ai.harness import AgentSpec
from quill.core.ai.permissions import Decision, PermissionCategory

AGENTS = load_catalog().agents


def _by_id(agent_id: str) -> AgentSpec:
    return next(a for a in AGENTS if a.id == agent_id)


def test_write_kind_from_catalog() -> None:
    assert write_kind(_by_id("writing-companion")) == "selection"
    assert write_kind(_by_id("accessibility-editor")) == "document"
    assert write_kind(_by_id("summarizer")) == "produce"


def test_recommend_agents_selection_prefers_selection_and_produce() -> None:
    recs = recommend_agents(list(AGENTS), file_type="md", has_selection=True)
    kinds = {write_kind(a) for a in recs}
    assert "document" not in kinds  # document-transform agents excluded for selection
    assert any(a.id == "writing-companion" for a in recs)


def test_recommend_agents_document_includes_document_transformers() -> None:
    recs = recommend_agents(list(AGENTS), file_type="md", has_selection=False)
    ids = {a.id for a in recs}
    assert "accessibility-editor" in ids or "markdown-publisher" in ids
    assert all(write_kind(a) in {"document", "produce"} for a in recs)


def test_recommend_agents_file_type_specific_first() -> None:
    # code-doctor recommends py/js/...; for a .py selection it should rank before
    # general selection agents.
    recs = recommend_agents(list(AGENTS), file_type="py", has_selection=True)
    assert recs[0].recommended_file_types  # first entry is file-type-specific
    assert any(a.id == "code-doctor" for a in recs[:2])


def test_suggest_ai_off_offers_enable() -> None:
    ctx = ConciergeContext(ai_enabled=False, outline_headings=0)
    out = suggest(ctx, list(AGENTS))
    assert out[0].target == "tools.ai_hub"
    assert "off" in out[0].reason.lower()


def test_suggest_includes_outline_navigation() -> None:
    ctx = ConciergeContext(file_type="md", has_selection=False, outline_headings=5)
    out = suggest(ctx, list(AGENTS))
    assert any(s.target == "navigate.outline_navigator" for s in out)
    assert any("5 headings" in s.reason for s in out)


def test_suggest_selection_agents_target_palette_commands() -> None:
    ctx = ConciergeContext(file_type="md", has_selection=True)
    out = suggest(ctx, list(AGENTS))
    agent_suggestions = [s for s in out if s.kind == "agent"]
    assert agent_suggestions
    assert all(s.target.startswith("tools.run_agent.") for s in agent_suggestions)


def test_suggest_surfaces_github_maintainer_in_a_repo_without_duplicates() -> None:
    ctx = ConciergeContext(file_type="md", has_selection=False, in_git_repo=True)
    out = suggest(ctx, list(AGENTS), limit=12)
    gh_target = "tools.run_agent.github_maintainer"
    gh = [s for s in out if s.target == gh_target]
    assert len(gh) == 1  # surfaced once, not duplicated by the recommend loop
    assert "git repository" in gh[0].reason


def test_suggest_respects_limit() -> None:
    ctx = ConciergeContext(file_type="md", has_selection=True, outline_headings=3)
    assert len(suggest(ctx, list(AGENTS), limit=2)) == 2


def test_ring_actions_text_vs_code() -> None:
    text_ring = ring_actions("md", list(AGENTS))
    assert any(a.label == "Rewrite clearly" for a in text_ring)
    assert all(isinstance(a, RingAction) for a in text_ring)

    code_ring = ring_actions("py", list(AGENTS))
    assert any(a.label == "Explain" for a in code_ring)
    assert all(a.agent_id == "code-doctor" for a in code_ring)


def test_ring_actions_only_returns_available_agents() -> None:
    # A catalog without code-doctor yields an empty code ring.
    trimmed = [a for a in AGENTS if a.id != "code-doctor"]
    assert ring_actions("py", trimmed) == []


def test_ring_actions_bind_real_agent_ids() -> None:
    ids = {a.id for a in AGENTS}
    for action in ring_actions("md", list(AGENTS)) + ring_actions("py", list(AGENTS)):
        assert action.agent_id in ids
        assert action.instruction


def test_unknown_permission_overrides_default_to_produce() -> None:
    bare = AgentSpec(id="b", display_name="B", system_prompt="x")
    assert write_kind(bare) == "produce"
    # An agent that only reads is a produce agent.
    reader = AgentSpec(
        id="r",
        display_name="R",
        system_prompt="x",
        permission_overrides=((PermissionCategory.READ_DOCUMENT, Decision.ASK),),
    )
    assert write_kind(reader) == "produce"
