from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from quill.core.podcasts.models import PodcastFolder, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts import manager_filing
from quill.ui.podcasts.folder_picker_dialog import FolderPickerResult
from quill.ui.podcasts.manager_lookups import item_key


@pytest.fixture
def filing_tree():
    app = wx.GetApp() or wx.App()
    frame = wx.Frame(None)
    tree = wx.TreeCtrl(frame)
    root = tree.AddRoot("Podcasts")
    primary = tree.AppendItem(root, "Primary")
    copied = tree.AppendItem(root, "Copied")
    first = tree.AppendItem(primary, "Shared")
    selected = tree.AppendItem(copied, "Shared")
    neighbor_primary = tree.AppendItem(primary, "Neighbor")
    neighbor_copy = tree.AppendItem(copied, "Neighbor")
    tree.SelectItem(selected)
    library = PodcastLibrary(
        shows=[
            PodcastShow(id="shared", title="Shared", folder_id="primary"),
            PodcastShow(id="neighbor", title="Neighbor", folder_id="primary"),
        ],
        folders=[PodcastFolder("primary", "Primary"), PodcastFolder("copied", "Copied")],
        show_folder_copies={"shared": ["copied"], "neighbor": ["copied"]},
    )
    dialog = SimpleNamespace(
        _tree=tree,
        _library=library,
        _tree_item_folder={item_key(primary): "primary", item_key(copied): "copied"},
        _tree_item_show={
            item_key(first): "shared",
            item_key(selected): "shared",
            item_key(neighbor_primary): "neighbor",
            item_key(neighbor_copy): "neighbor",
        },
        _selected_show_sort_mode=lambda: "custom",
    )
    try:
        yield dialog, neighbor_copy
    finally:
        frame.Destroy()
        app.ProcessPendingEvents()


def test_native_item_identity_finds_the_selected_copy(filing_tree) -> None:
    dialog, _neighbor = filing_tree
    assert manager_filing.source_folder(dialog, dialog._library.shows[0]) == "copied"


def test_neighbor_anchor_returns_to_the_same_copy_folder(filing_tree) -> None:
    dialog, neighbor = filing_tree
    anchor = manager_filing.neighbor_anchor(dialog, "shared")
    assert anchor == ("show", "neighbor", "copied")

    manager_filing.restore_anchor(dialog, anchor)

    assert item_key(dialog._tree.GetSelection()) == item_key(neighbor)


def test_manager_move_keeps_picker_folder_edits_after_cancel(monkeypatch) -> None:
    from quill.ui.podcasts import folder_picker_dialog, move_shows_dialog

    library = PodcastLibrary(shows=[PodcastShow(id="shared", title="Shared")])
    saves: list[bool] = []
    refreshes: list[bool] = []
    dialog = SimpleNamespace(
        dialog=None,
        _tree=None,
        _library=library,
        _announce=lambda _message: None,
        _on_library_changed=lambda: saves.append(True),
        _neighbor_anchor_for_show=lambda _id: None,
        refresh_tree=lambda: refreshes.append(True),
        _restore_tree_anchor=lambda _anchor: None,
    )

    class Picker:
        def __init__(self, _parent, **kwargs):
            self.on_change = kwargs["on_library_changed"]

        def show(self):
            library.add_folder("Kept folder")
            self.on_change()
            return FolderPickerResult(False)

    monkeypatch.setattr(folder_picker_dialog, "FolderPickerDialog", Picker)
    monkeypatch.setattr("quill.ui.podcasts.show_filing.FolderPickerDialog", Picker)
    move_shows_dialog.move_one_show(dialog, library.shows[0])

    assert len(library.folders) == 1
    assert saves == [True]
    assert refreshes == [True]
    assert library.shows[0].folder_id is None


def test_bulk_move_does_not_restore_an_unfollowed_show(monkeypatch) -> None:
    from quill.ui.podcasts import folder_picker_dialog, move_shows_dialog

    kept = PodcastShow(id="kept", title="Kept")
    removed = PodcastShow(id="removed", title="Removed")
    library = PodcastLibrary(
        shows=[kept, removed], folders=[PodcastFolder("destination", "Destination")]
    )
    messages: list[str] = []
    dialog = SimpleNamespace(
        dialog=None,
        _library=library,
        _announce=messages.append,
        _on_library_changed=lambda: None,
        refresh_tree=lambda: None,
    )
    monkeypatch.setattr(
        move_shows_dialog.MoveShowsDialog, "__init__", lambda self, *_args, **_kwargs: None
    )
    monkeypatch.setattr(move_shows_dialog.MoveShowsDialog, "show", lambda _self: [kept, removed])

    class Picker:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self):
            library.remove_show(removed.id)
            return FolderPickerResult(True, "destination")

    monkeypatch.setattr(folder_picker_dialog, "FolderPickerDialog", Picker)
    move_shows_dialog.open_move_shows(dialog)

    assert kept.folder_id == "destination"
    assert library.find_show(removed.id) is None
    assert messages == [
        "Moved 1 podcast to Destination.",
        "Skipped 1 podcast(s) that are no longer followed.",
    ]
