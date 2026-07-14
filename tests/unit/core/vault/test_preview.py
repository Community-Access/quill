"""Tests for the in-app preview link/embed resolution core (wx-free)."""

from __future__ import annotations

from pathlib import Path

from quill.core.vault.preview import resolve_for_preview
from quill.core.vault.resolve import build_resolver
from quill.core.vault.vault import scan_vault


def test_resolve_for_preview_expands_embeds_and_titles_links(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text(
        "# A\n\n![[B]] then [[B|see B]] and [[Ghost]].\n", encoding="utf-8"
    )
    (tmp_path / "b.md").write_text("# B\n\nB body.\n", encoding="utf-8")
    vault = scan_vault(tmp_path)
    out = resolve_for_preview(vault.texts["a.md"], vault, build_resolver(vault), "a.md")
    assert "B body." in out  # embed inlined
    assert 'class="vault-link"' in out and ">see B<" in out  # link titled by alias
    assert 'href="#"' in out  # inert preview links
    assert 'class="vault-link-broken"' in out  # [[Ghost]] flagged, not left raw
    assert "[[B]]" not in out and "![[B]]" not in out  # markup resolved


def test_resolve_for_preview_plain_text_untouched(tmp_path: Path) -> None:
    (tmp_path / "n.md").write_text("# N\n\nJust prose, no links.\n", encoding="utf-8")
    vault = scan_vault(tmp_path)
    out = resolve_for_preview(vault.texts["n.md"], vault, build_resolver(vault), "n.md")
    assert out == vault.texts["n.md"]  # nothing to resolve = byte-identical
