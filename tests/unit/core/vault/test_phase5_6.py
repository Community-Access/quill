"""Tests for Vault Phase 5 (embeds) and Phase 6 (templates + daily notes)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from quill.core.vault.dailynotes import daily_note_relpath, shift_daily
from quill.core.vault.render import expand_embeds, resolve_embed_content
from quill.core.vault.resolve import build_resolver
from quill.core.vault.templates import render_template, template_prompts
from quill.core.vault.vault import scan_vault

# --- Phase 5: embeds -------------------------------------------------------


def _embed_vault(tmp_path: Path):
    (tmp_path / "src.md").write_text("# Source\n\nUse ![[Target]] here.\n", encoding="utf-8")
    (tmp_path / "target.md").write_text(
        "# Target\n\nWhole body.\n\n## Section\n\nSection body.\n\nA claim. ^c1\n",
        encoding="utf-8",
    )
    return scan_vault(tmp_path)


def test_resolve_embed_whole_heading_and_block(tmp_path: Path) -> None:
    vault = _embed_vault(tmp_path)
    whole = resolve_embed_content(vault, "target.md", None, None)
    assert "Whole body." in whole and "Section body." in whole
    section = resolve_embed_content(vault, "target.md", "Section", None)
    assert section.startswith("## Section") and "Whole body." not in section
    block = resolve_embed_content(vault, "target.md", None, "c1")
    assert block == "A claim." and "^c1" not in block


def test_expand_embeds_inlines_content_with_boundary(tmp_path: Path) -> None:
    vault = _embed_vault(tmp_path)
    out = expand_embeds(vault.texts["src.md"], vault, build_resolver(vault), "src.md")
    assert "embedded from Target" in out
    assert "Whole body." in out  # target content pulled in
    assert "![[Target]]" not in out  # embed marker replaced


def test_expand_embeds_detects_cycles(tmp_path: Path) -> None:
    (tmp_path / "x.md").write_text("# X\n\n![[Y]]\n", encoding="utf-8")
    (tmp_path / "y.md").write_text("# Y\n\n![[X]]\n", encoding="utf-8")
    vault = scan_vault(tmp_path)
    out = expand_embeds(vault.texts["x.md"], vault, build_resolver(vault), "x.md")
    assert "circular embed" in out  # does not recurse forever


# --- Phase 6: templates ----------------------------------------------------


def test_render_template_substitutes_tokens_and_cursor() -> None:
    now = dt.datetime(2026, 7, 1, 9, 5, 0)
    text = "# {{title}}\n\nCreated {{date}} at {{time}}.\n\n{{cursor}}Start here.\n"
    out, cursor = render_template(text, now=now, title="My Note")
    assert "# My Note" in out
    assert "2026-07-01" in out and "09:05" in out
    assert cursor >= 0 and out[cursor:].startswith("Start here.")  # cursor marker removed


def test_template_prompts_and_answers() -> None:
    text = "Topic: {{prompt:What topic?}} / {{prompt:What topic?}} / {{prompt:Mood?}}"
    assert template_prompts(text) == ["What topic?", "Mood?"]  # deduped, in order
    out, _ = render_template(
        text, now=dt.datetime(2026, 7, 1), answers={"What topic?": "Foxes", "Mood?": "Calm"}
    )
    assert out == "Topic: Foxes / Foxes / Calm"


def test_render_template_custom_date_format() -> None:
    out, _ = render_template("{{date:YYYY/MM/DD}}", now=dt.datetime(2026, 7, 1))
    assert out == "2026/07/01"


# --- Phase 6: daily notes --------------------------------------------------


def test_daily_note_relpath() -> None:
    assert daily_note_relpath("Journal/{{date:YYYY-MM-DD}}.md", dt.date(2026, 7, 1)) == (
        "Journal/2026-07-01.md"
    )


def test_shift_daily_walks_the_calendar() -> None:
    rel, day = shift_daily("Journal/{{date:YYYY-MM-DD}}.md", dt.date(2026, 7, 1), -1)
    assert rel == "Journal/2026-06-30.md" and day == dt.date(2026, 6, 30)
    rel2, day2 = shift_daily("Journal/{{date:YYYY-MM-DD}}.md", dt.date(2026, 7, 1), 1)
    assert rel2 == "Journal/2026-07-02.md" and day2 == dt.date(2026, 7, 2)
