"""The markdown renderer must pass vault-resolved markup through, not escape it.

``resolve_for_preview`` (in-app preview) and ``note_to_html_fragment`` (site export,
publish) inject ``<a class="vault-link">`` anchors, ``<span class="vault-link-broken">``
markers, and ``<!-- embedded from -->`` boundaries *before* the Markdown pass. The
hand-rolled renderer escapes all other HTML, so without an explicit passthrough the
preview showed the anchors as literal raw HTML (user report, 2026-07-14).
"""

from __future__ import annotations

from pathlib import Path

from quill.core.browser_preview import render_preview_body
from quill.core.vault.preview import resolve_for_preview
from quill.core.vault.resolve import build_resolver
from quill.core.vault.vault import scan_vault


def test_vault_link_anchor_survives_markdown_pass() -> None:
    body = render_preview_body('See <a class="vault-link" href="#">Target</a> now.', "markdown")
    assert '<a class="vault-link" href="#">Target</a>' in body
    assert "&lt;a" not in body


def test_vault_broken_link_span_survives_markdown_pass() -> None:
    marker = '<span class="vault-link-broken" title="No note named Ghost">Ghost</span>'
    body = render_preview_body(f"A {marker} link.", "markdown")
    assert marker in body
    assert "&lt;span" not in body


def test_embed_boundaries_render_as_announced_text() -> None:
    text = "Intro.\n\n<!-- embedded from B -->\nB body.\n<!-- end embed -->\n"
    body = render_preview_body(text, "markdown")
    assert "&lt;!--" not in body  # never shown as raw escaped comment text
    assert "Embedded from B" in body  # the boundary is visible and announceable
    assert "End of embed" in body
    assert "B body." in body


def test_other_user_typed_html_is_still_escaped() -> None:
    body = render_preview_body('<script>alert(1)</script> and <a href="x">y</a>.', "markdown")
    assert "<script>" not in body
    assert "&lt;script&gt;" in body
    assert '<a href="x">' not in body  # only the vault-link shape passes through


def test_full_vault_preview_pipeline_shows_no_raw_html(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text(
        "# A\n\nSee [[B|see B]] and [[Ghost]].\n\n![[B]]\n", encoding="utf-8"
    )
    (tmp_path / "b.md").write_text("# B\n\nB body.\n", encoding="utf-8")
    vault = scan_vault(tmp_path)
    resolved = resolve_for_preview(vault.texts["a.md"], vault, build_resolver(vault), "a.md")
    body = render_preview_body(resolved, "markdown")
    assert "&lt;a" not in body and "&lt;span" not in body and "&lt;!--" not in body
    assert '<a class="vault-link" href="#">see B</a>' in body
    assert 'class="vault-link-broken"' in body
    assert "B body." in body
    assert "Embedded from B" in body
