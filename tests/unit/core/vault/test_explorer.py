"""Tests for the Vault Explorer folder-tree core (wx-free)."""

from __future__ import annotations

from pathlib import Path

from quill.core.vault.explorer import build_note_tree, flatten_notes
from quill.core.vault.vault import scan_vault


def _vault(tmp_path: Path):
    (tmp_path / "zeta.md").write_text("# Zeta\n", encoding="utf-8")
    (tmp_path / "alpha.md").write_text("# Alpha\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text("# Bravo\n", encoding="utf-8")
    (tmp_path / "sub" / "a.md").write_text("# Anna\n", encoding="utf-8")
    return scan_vault(tmp_path)


def test_tree_groups_folders_first_then_notes_by_title(tmp_path: Path) -> None:
    tree = build_note_tree(_vault(tmp_path))
    labels = [c.label for c in tree.children]
    # Folder "sub" sorts before the top-level notes; notes ordered by title.
    assert labels == ["sub", "Alpha", "Zeta"]
    assert tree.children[0].is_folder
    assert not tree.children[1].is_folder


def test_folder_children_sorted_by_title(tmp_path: Path) -> None:
    tree = build_note_tree(_vault(tmp_path))
    sub = next(c for c in tree.children if c.label == "sub")
    assert [c.label for c in sub.children] == ["Anna", "Bravo"]  # a.md=Anna, b.md=Bravo
    assert all(not c.is_folder for c in sub.children)


def test_flatten_notes_reading_order(tmp_path: Path) -> None:
    tree = build_note_tree(_vault(tmp_path))
    assert flatten_notes(tree) == ["sub/a.md", "sub/b.md", "alpha.md", "zeta.md"]


def test_empty_vault_tree(tmp_path: Path) -> None:
    tree = build_note_tree(scan_vault(tmp_path))
    assert tree.is_folder and tree.children == ()
