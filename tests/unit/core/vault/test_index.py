from __future__ import annotations

from pathlib import Path

from quill.core.vault.index import backlinks, build_index, unlinked_mentions
from quill.core.vault.resolve import build_resolver
from quill.core.vault.vault import scan_vault


def _vault(tmp_path: Path, files: dict[str, str]):
    for name, text in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    vault = scan_vault(tmp_path)
    return vault, build_resolver(vault)


def test_forward_and_reverse_adjacency(tmp_path: Path) -> None:
    vault, resolver = _vault(
        tmp_path,
        {"a.md": "# A\n[[B]]", "c.md": "# C\n[[B]]", "b.md": "# B\n"},
    )
    index = build_index(vault, resolver)
    assert index.forward["a.md"] == ("b.md",)
    assert {bl.source_path for bl in backlinks(index, "b.md")} == {"a.md", "c.md"}


def test_backlink_context_is_the_linking_line(tmp_path: Path) -> None:
    vault, resolver = _vault(
        tmp_path,
        {"a.md": "Intro line\nSee [[Bravo]] for more.\nEnd", "b.md": "---\ntitle: Bravo\n---\n"},
    )
    index = build_index(vault, resolver)
    (bl,) = backlinks(index, "b.md")
    assert bl.source_path == "a.md"
    assert bl.context == "See [[Bravo]] for more."


def test_self_and_unresolved_links_are_not_backlinks(tmp_path: Path) -> None:
    vault, resolver = _vault(tmp_path, {"a.md": "# A\n[[#Section]] and [[Ghost]]"})
    index = build_index(vault, resolver)
    assert index.forward["a.md"] == ()
    assert backlinks(index, "a.md") == ()


def test_unlinked_mention_found(tmp_path: Path) -> None:
    vault, resolver = _vault(
        tmp_path,
        {"b.md": "---\ntitle: Bravo\n---\n", "c.md": "I mention Bravo without a link."},
    )
    mentions = unlinked_mentions(vault, resolver, "b.md")
    assert [m.source_path for m in mentions] == ["c.md"]
    assert "Bravo" in mentions[0].context


def test_unlinked_mention_excludes_actual_links(tmp_path: Path) -> None:
    vault, resolver = _vault(
        tmp_path, {"b.md": "---\ntitle: Bravo\n---\n", "d.md": "Here is [[Bravo]] linked."}
    )
    assert unlinked_mentions(vault, resolver, "b.md") == ()


def test_unlinked_mention_is_whole_word(tmp_path: Path) -> None:
    vault, resolver = _vault(
        tmp_path, {"b.md": "---\ntitle: Cat\n---\n", "e.md": "concatenate is not a mention"}
    )
    assert unlinked_mentions(vault, resolver, "b.md") == ()
