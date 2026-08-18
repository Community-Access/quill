"""The browse-visibility setting actually reaches the tree.

The rule the setting promises -- a branch that is off is not in the tree at
all, and is never contacted -- is only true if the dialog builds its roots from
``visible_roots`` rather than the unfiltered registry. That wiring was missing
for a while: ``browse_visibility`` existed, was tested, and changed nothing,
because ``_populate_sources`` never asked it. These tests pin the wiring, the
persistence semantics underneath it, and the one honest message an all-hidden
tree must show.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from quill.core.radio import browse_sources as bs
from quill.core.radio import browse_visibility as bv
from quill.core.radio import history as radio_history
from quill.core.radio.favorites import RadioFavoritesStore
from quill.ui.radio.browse_tree_dialog import BrowseTreeDialog


@pytest.fixture(scope="module")
def _app() -> wx.App:
    return wx.App()


def _make(visible_sources: object | None) -> BrowseTreeDialog:
    controller = SimpleNamespace(state=SimpleNamespace(volume_percent=100, muted=False))
    return BrowseTreeDialog(
        None,
        controller=controller,
        favorites_store=RadioFavoritesStore(),
        task_manager=SimpleNamespace(),
        safe_mode=True,  # no live source fetches during construction
        announce_cb=lambda _m: None,
        visible_sources=visible_sources,
    )


def _root_labels(dlg: BrowseTreeDialog) -> list[str]:
    tree = dlg._tree
    root = tree.GetRootItem()
    labels: list[str] = []
    child, cookie = tree.GetFirstChild(root)
    while child.IsOk():
        labels.append(tree.GetItemText(child))
        child, cookie = tree.GetNextChild(root, cookie)
    return labels


def test_a_hidden_branch_is_not_built(_app: wx.App) -> None:
    chosen = bv.toggle(bv.enable_all(), "librivox")
    dlg = _make(chosen)
    try:
        labels = _root_labels(dlg)
        assert "LibriVox Audiobooks" not in labels
        assert "Favorites" in labels  # the rest of the tree is untouched
    finally:
        dlg._win.Destroy()


def test_never_set_shows_the_defaults(_app: wx.App) -> None:
    dlg = _make(None)
    try:
        labels = _root_labels(dlg)
        for _sid, label in bs.visible_roots(None):
            assert label in labels
    finally:
        dlg._win.Destroy()


def test_everything_hidden_says_the_way_back(_app: wx.App) -> None:
    # Search All Sources... is deliberately outside Choose Browse Sources
    # (hiding every SOURCE should not also hide the way to search), so with
    # everything hidden the tree is exactly: search, and the way back.
    dlg = _make(())
    try:
        labels = _root_labels(dlg)
        assert len(labels) == 2
        assert labels[0] == "Search All Sources..."
        assert "Choose Browse Sources" in labels[1]
    finally:
        dlg._win.Destroy()


def test_the_search_row_leads_the_tree(_app: wx.App) -> None:
    dlg = _make(None)
    try:
        assert _root_labels(dlg)[0] == "Search All Sources..."
    finally:
        dlg._win.Destroy()


def test_history_round_trips_the_choice(tmp_path) -> None:
    history = radio_history.RadioHistory()
    history.browse_sources_enabled = bv.toggle(None, "wikidata")
    radio_history.save_history(tmp_path, history)
    loaded = radio_history.load_history(tmp_path)
    assert loaded.browse_sources_enabled == history.browse_sources_enabled


def test_history_never_set_stays_none(tmp_path) -> None:
    """Absent must stay None, so a branch added in a later release can appear
    for people who never touched the setting."""
    radio_history.save_history(tmp_path, radio_history.RadioHistory())
    assert radio_history.load_history(tmp_path).browse_sources_enabled is None
