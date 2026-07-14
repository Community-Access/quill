"""A folder tree of the vault's notes for the Vault Explorer (wx-free).

Turns the flat ``vault.notes`` map (posix-relative paths) into a nested
:class:`ExplorerNode` tree — folders first, then notes, each sorted for a stable,
predictable reading order — so the wx shell can drop it straight into a ``wx.TreeCtrl``.
Notes are labelled by title; folders by their name. Pure and unit-tested; the wx layer
only walks the tree.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.vault.vault import Vault


@dataclass(frozen=True, slots=True)
class ExplorerNode:
    """One tree node: a folder (``path is None``) or a note (``path`` = rel path)."""

    label: str
    path: str | None
    children: tuple[ExplorerNode, ...]

    @property
    def is_folder(self) -> bool:
        return self.path is None


def build_note_tree(vault: Vault) -> ExplorerNode:
    """Build the folder tree of every note under the vault root.

    Returns the (unlabelled) root node; its children are the top-level folders and notes.
    Folders sort before notes; folders by name, notes by title (case-insensitive).
    """
    root: dict = {}
    for rel in sorted(vault.notes):
        parts = rel.split("/")
        cursor = root
        for folder in parts[:-1]:
            existing = cursor.get(folder)
            if not isinstance(existing, dict):
                existing = {}
                cursor[folder] = existing
            cursor = existing
        cursor[parts[-1]] = rel  # leaf: filename -> rel note path (a str)

    def build(name: str, node: object) -> ExplorerNode:
        if isinstance(node, str):  # a note
            title = vault.notes[node].title if node in vault.notes else name
            return ExplorerNode(label=title, path=node, children=())
        assert isinstance(node, dict)
        folders = sorted(
            ((k, v) for k, v in node.items() if isinstance(v, dict)),
            key=lambda kv: kv[0].casefold(),
        )
        notes = sorted(
            ((k, v) for k, v in node.items() if isinstance(v, str)),
            key=lambda kv: vault.notes[kv[1]].title.casefold() if kv[1] in vault.notes else kv[0],
        )
        children = tuple(build(k, v) for k, v in folders) + tuple(build(k, v) for k, v in notes)
        return ExplorerNode(label=name, path=None, children=children)

    return build("", root)


def flatten_notes(node: ExplorerNode) -> list[str]:
    """Every note path under ``node``, in tree (reading) order — for tests/navigation."""
    out: list[str] = []
    if node.path is not None:
        out.append(node.path)
    for child in node.children:
        out.extend(flatten_notes(child))
    return out
