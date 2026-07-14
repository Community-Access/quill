"""Tests for the Vault Phase 0-2 deferred core: render, neighborhood, rename, incremental."""

from __future__ import annotations

from pathlib import Path

from quill.core.vault.index import build_index, neighborhood
from quill.core.vault.refactor import (
    apply_replacements,
    plan_note_rename,
    rename_link_count,
    retitle_heading,
)
from quill.core.vault.render import relative_site_url, render_links_html
from quill.core.vault.resolve import build_resolver
from quill.core.vault.vault import apply_note_change, scan_vault


def _vault(tmp_path: Path):
    (tmp_path / "a.md").write_text(
        "# Alpha\n\nSee [[Beta]] and [[Beta|the second]] and [[Ghost]].\n", encoding="utf-8"
    )
    (tmp_path / "b.md").write_text("# Beta\n\nBack to [[Alpha]].\n", encoding="utf-8")
    return scan_vault(tmp_path)


# --- render (preview/export link resolution) -------------------------------


def test_render_resolves_links_and_marks_broken(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    resolver = build_resolver(vault)
    out = render_links_html(
        vault.texts["a.md"], vault, resolver, "a.md", url_for=lambda p, a: f"/{p}#{a}"
    )
    assert '<a class="vault-link" href="/b.md#">Beta</a>' in out
    assert '<a class="vault-link" href="/b.md#">the second</a>' in out  # alias shown
    assert 'class="vault-link-broken"' in out and ">Ghost<" in out  # unresolved marked
    assert "[[Beta]]" not in out  # the literal wikilink is gone


def test_render_leaves_embeds_untouched(tmp_path: Path) -> None:
    (tmp_path / "n.md").write_text("# N\n\n![[Beta]] stays.\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("# Beta\n", encoding="utf-8")
    vault = scan_vault(tmp_path)
    out = render_links_html(
        vault.texts["n.md"], vault, build_resolver(vault), "n.md", url_for=lambda p, a: p
    )
    assert "![[Beta]]" in out  # embed left for Phase 5


def test_relative_site_url_computes_relative_html_paths() -> None:
    assert relative_site_url("a/b.md", "c/d.md", "") == "../c/d.html"
    assert relative_site_url("index.md", "notes/x.md", "top") == "notes/x.html#top"
    assert relative_site_url("notes/x.md", "notes/y.md", "") == "y.html"


# --- neighborhood ----------------------------------------------------------


def test_neighborhood_reports_outgoing_and_incoming(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    index = build_index(vault, build_resolver(vault))
    hood = neighborhood(vault, index, "b.md")
    assert hood.title == "Beta"
    assert ("a.md", "Alpha") in hood.outgoing  # b -> a
    assert any(bl.source_path == "a.md" for bl in hood.incoming)  # a -> b


# --- rename with link update -----------------------------------------------


def test_plan_note_rename_retargets_inbound_links_preserving_alias(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    edits = plan_note_rename(vault, "Beta", "Gamma")
    total, notes = rename_link_count(edits)
    assert total == 2 and notes == 1  # two links to Beta, both in a.md
    updated = apply_replacements(vault.texts["a.md"], edits[0].replacements)
    assert "[[Gamma]]" in updated
    assert "[[Gamma|the second]]" in updated  # alias preserved
    assert "[[Beta" not in updated


def test_plan_note_rename_noop_when_titles_equivalent(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    assert plan_note_rename(vault, "Beta", "  beta ") == []
    assert plan_note_rename(vault, "Beta", "") == []


def test_retitle_heading_rewrites_matching_h1_only() -> None:
    text = "# Beta\n\nBody mentioning Beta.\n\n# Beta\n"
    out = retitle_heading(text, "Beta", "Gamma")
    assert out.startswith("# Gamma\n")  # first H1 retitled
    assert "Body mentioning Beta." in out  # body text untouched
    assert out.count("# Gamma") == 1 and "# Beta" in out  # only the first H1 changed


def test_retitle_heading_no_match_returns_unchanged() -> None:
    text = "# Alpha\n\nno beta heading here\n"
    assert retitle_heading(text, "Beta", "Gamma") == text


# --- incremental reparse ---------------------------------------------------


def test_apply_note_change_reparses_one_note(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    updated = apply_note_change(vault, "b.md", "# Beta Renamed\n\nnew body\n")
    assert updated.notes["b.md"].title == "Beta Renamed"
    assert vault.notes["b.md"].title == "Beta"  # original untouched (copy)


def test_apply_note_change_add_and_remove(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    added = apply_note_change(vault, "c.md", "# Gamma\n")
    assert "c.md" in added.notes and added.notes["c.md"].title == "Gamma"
    removed = apply_note_change(added, "c.md", None)
    assert "c.md" not in removed.notes and "c.md" not in removed.texts
