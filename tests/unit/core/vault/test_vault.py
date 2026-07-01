from __future__ import annotations

from pathlib import Path

from quill.core.vault.vault import scan_vault


def test_scan_collects_and_parses_notes(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# Alpha\n\n[[b]]", encoding="utf-8")
    (tmp_path / "b.md").write_text("---\ntitle: Bravo\n---\nbody", encoding="utf-8")
    (tmp_path / "cover.png").write_bytes(b"\x89PNG")
    vault = scan_vault(tmp_path)
    assert set(vault.notes) == {"a.md", "b.md"}
    assert vault.notes["a.md"].title == "Alpha"
    assert vault.notes["b.md"].title == "Bravo"
    assert vault.notes["a.md"].links[0].target == "b"


def test_scan_recurses_subfolders_with_posix_keys(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.md").write_text("# Charlie", encoding="utf-8")
    vault = scan_vault(tmp_path)
    assert "sub/c.md" in vault.notes
    assert vault.notes["sub/c.md"].title == "Charlie"


def test_scan_ignores_the_quill_cache_and_dotdirs(tmp_path: Path) -> None:
    (tmp_path / ".quill").mkdir()
    (tmp_path / ".quill" / "index.json").write_text("{}", encoding="utf-8")
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    vault = scan_vault(tmp_path)
    assert set(vault.notes) == {"a.md"}


def test_title_falls_back_to_stem(tmp_path: Path) -> None:
    (tmp_path / "no-heading.md").write_text("just text", encoding="utf-8")
    vault = scan_vault(tmp_path)
    assert vault.notes["no-heading.md"].title == "no-heading"
