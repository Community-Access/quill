"""Move to Folder picker: the wx-free filter logic plus source contracts for
the dialog's accessibility and the manager's position-preserving move."""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.folder_picker_dialog import _visible_folder_ids

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui" / "podcasts"


def _library() -> PodcastLibrary:
    library = PodcastLibrary()
    tech = library.add_folder("Tech")
    library.add_folder("Deep Dives", parent_folder_id=tech.id)
    news = library.add_folder("News")
    library.add_folder("Politics", parent_folder_id=news.id)
    return library


def test_empty_search_shows_every_folder() -> None:
    library = _library()
    assert _visible_folder_ids(library.folders, "") == {f.id for f in library.folders}


def test_search_matches_by_substring_case_insensitive() -> None:
    library = _library()
    visible = _visible_folder_ids(library.folders, "poli")
    names = {f.name for f in library.folders if f.id in visible}
    # Politics matches; News is its ancestor and stays visible for context.
    assert names == {"Politics", "News"}


def test_search_keeps_every_ancestor_of_a_deep_match() -> None:
    library = PodcastLibrary()
    a = library.add_folder("A")
    b = library.add_folder("B", parent_folder_id=a.id)
    c = library.add_folder("Target C", parent_folder_id=b.id)
    visible = _visible_folder_ids(library.folders, "target")
    assert visible == {a.id, b.id, c.id}


def test_search_with_no_match_shows_nothing() -> None:
    library = _library()
    assert _visible_folder_ids(library.folders, "zzz-no-such-folder") == set()


def test_picker_dialog_meets_the_dialog_contract() -> None:
    src = (_UI / "folder_picker_dialog.py").read_text(encoding="utf-8")
    assert "apply_modal_ids(" in src
    assert "show_modal_dialog(" in src
    # Search field and tree carry accessible names.
    assert 'SetName("Search folders by name")' in src
    assert 'SetName("Folders")' in src
    # New Folder creates at the SELECTED level and selects the new folder.
    assert "parent_folder_id=parent_folder_id" in src
    assert "select_folder_id=folder.id" in src


def test_manager_move_preserves_tree_position() -> None:
    """#move-to-folder: after the show disappears into its folder, selection
    lands on its nearest former neighbor, never snapping to the top."""
    src = (_UI / "manager_dialog.py").read_text(encoding="utf-8")
    assert "def _on_move_show_to_folder(" in src
    assert "_neighbor_anchor_for_show(" in src
    assert "_restore_tree_anchor(" in src
    assert '"&Move to Folder..."' in src


def test_picker_offers_rename_and_delete_management() -> None:
    """Folder management lives in the picker too (Radio's only surface for
    it): Rename... and Delete buttons, enabled only when a real folder is
    selected, with delete always the safe move-contents-up variant."""
    src = (_UI / "folder_picker_dialog.py").read_text(encoding="utf-8")
    assert 'label="&Rename..."' in src
    assert 'label="De&lete"' in src
    assert 'contents="promote"' in src
    assert "delete_inbox_folder(" in src


def test_manager_offers_folder_rename_and_delete_with_contents_choice() -> None:
    """Delete Folder... always asks what to do with the podcasts inside —
    move them up to the parent, or unsubscribe them — never a silent choice.
    F2 renames whatever the tree/list selection is (folder, show, episode)."""
    src = (_UI / "manager_dialog.py").read_text(encoding="utf-8")
    assert "def _on_rename_folder(" in src
    assert "def _on_delete_folder(" in src
    assert "def _on_rename_show(" in src
    assert "def _on_rename_episode(" in src
    assert "def _on_delete_inbox_folder(" in src
    assert "WXK_F2" in src
    assert 'contents = "promote" if picker.GetSelection() == 0 else "remove"' in src
    assert "_delete_downloaded_files_for_removed_shows(" in src
