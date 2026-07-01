from __future__ import annotations

from pathlib import Path

from quill.core.vault.links import parse_links
from quill.core.vault.resolve import build_resolver, resolve_link
from quill.core.vault.vault import scan_vault


def _vault(tmp_path: Path, files: dict[str, str]):
    for name, text in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return scan_vault(tmp_path)


def _link(text: str):
    return parse_links(text)[0]


def test_resolve_by_title(tmp_path: Path) -> None:
    vault = _vault(tmp_path, {"a.md": "# Alpha\n", "other.md": "x"})
    resolver = build_resolver(vault)
    target = resolve_link(vault, resolver, _link("[[Alpha]]"), "other.md")
    assert target is not None and target.path == "a.md" and target.offset == 0


def test_resolve_by_stem_case_insensitive(tmp_path: Path) -> None:
    vault = _vault(tmp_path, {"MyNote.md": "no heading here"})
    resolver = build_resolver(vault)
    target = resolve_link(vault, resolver, _link("[[mynote]]"), "MyNote.md")
    assert target is not None and target.path == "MyNote.md"


def test_resolve_heading_offset(tmp_path: Path) -> None:
    text = "# Top\n\n## Sub Section\n\nbody"
    vault = _vault(tmp_path, {"n.md": text, "s.md": "x"})
    resolver = build_resolver(vault)
    target = resolve_link(vault, resolver, _link("[[n#Sub Section]]"), "s.md")
    assert target is not None and target.offset == text.index("## Sub Section")


def test_resolve_block_offset(tmp_path: Path) -> None:
    text = "A paragraph. ^b1\n"
    vault = _vault(tmp_path, {"n.md": text, "s.md": "x"})
    resolver = build_resolver(vault)
    target = resolve_link(vault, resolver, _link("[[n#^b1]]"), "s.md")
    assert target is not None and target.offset == text.index("^b1")


def test_unresolved_target_returns_none(tmp_path: Path) -> None:
    vault = _vault(tmp_path, {"a.md": "# Alpha\n"})
    resolver = build_resolver(vault)
    assert resolve_link(vault, resolver, _link("[[Nonexistent]]"), "a.md") is None


def test_ambiguous_lists_candidates(tmp_path: Path) -> None:
    vault = _vault(tmp_path, {"one/Draft.md": "# Draft\n", "two/Draft.md": "# Draft\n"})
    resolver = build_resolver(vault)
    target = resolve_link(vault, resolver, _link("[[Draft]]"), "other.md")
    assert target is not None and target.ambiguous is True
    assert set(target.candidates) == {"one/Draft.md", "two/Draft.md"}


def test_same_note_link_has_empty_target(tmp_path: Path) -> None:
    text = "# Here\n\n## There\n"
    vault = _vault(tmp_path, {"n.md": text})
    resolver = build_resolver(vault)
    target = resolve_link(vault, resolver, _link("[[#There]]"), "n.md")
    assert target is not None and target.path == "n.md"
    assert target.offset == text.index("## There")
