"""Tests for the Vault Phase 4 tag index (wx-free)."""

from __future__ import annotations

from pathlib import Path

from quill.core.vault.tags import (
    build_tag_index,
    notes_for_tag,
    tag_counts,
    tag_suggestions,
)
from quill.core.vault.vault import scan_vault


def _vault(tmp_path: Path):
    (tmp_path / "a.md").write_text("# A\n\n#project and #area/sub here.\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("---\ntags: [project, area/deep]\n---\n# B\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("# C\n\njust #project\n", encoding="utf-8")
    return scan_vault(tmp_path)


def test_tag_counts_ordered_by_count(tmp_path: Path) -> None:
    index = build_tag_index(_vault(tmp_path))
    counts = dict(tag_counts(index))
    assert counts["project"] == 3  # a, b, c
    assert counts["area"] == 2  # a (area/sub) + b (area/deep), via nesting
    # Ordered most-used first.
    assert tag_counts(index)[0][0] == "project"


def test_nested_tags_roll_up_to_ancestors(tmp_path: Path) -> None:
    index = build_tag_index(_vault(tmp_path))
    area = {n.path for n in notes_for_tag(index, "area")}
    assert area == {"a.md", "b.md"}  # both, from area/sub and area/deep
    assert {n.path for n in notes_for_tag(index, "area/sub")} == {"a.md"}


def test_frontmatter_flow_list_tags_split(tmp_path: Path) -> None:
    index = build_tag_index(_vault(tmp_path))
    # b.md's front-matter "[project, area/deep]" split into two tags.
    assert any(n.path == "b.md" for n in notes_for_tag(index, "project"))
    assert any(n.path == "b.md" for n in notes_for_tag(index, "area/deep"))


def test_tag_suggestions_prefix_and_ranking(tmp_path: Path) -> None:
    index = build_tag_index(_vault(tmp_path))
    assert tag_suggestions(index, "pro") == ["project"]
    assert tag_suggestions(index, "#are")[0] == "area"  # leading # tolerated
    assert tag_suggestions(index, "zzz") == []


def test_notes_for_tag_tolerates_hash(tmp_path: Path) -> None:
    index = build_tag_index(_vault(tmp_path))
    assert notes_for_tag(index, "#project") == notes_for_tag(index, "project")
