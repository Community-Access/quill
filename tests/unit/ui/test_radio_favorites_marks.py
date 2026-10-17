"""Mark many favourites with ".", then Delete removes them after one question.

xradio2 4.10 (todo P3 Radio extras 1). Built on a real in-memory TreeCtrl; the
yes/no question is a fake, so nothing modal opens and no input is sent.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.core.radio.row_marks import RowMarks
from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.ui.radio import favorites_marks  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = shared_wx_app()
    yield app
    app.Destroy()


@pytest.fixture
def frame():
    window = wx.Frame(None)
    yield window
    window.Destroy()


def _store(count: int = 5) -> RadioFavoritesStore:
    store = RadioFavoritesStore()
    for index in range(count):
        store.add(RadioStation(name=f"Station {index}", stream_url=f"https://s{index}.test/"))
    return store


def _tree(frame, store: RadioFavoritesStore, marks: RowMarks):
    tree = wx.TreeCtrl(frame, style=wx.TR_HIDE_ROOT)
    root = tree.AddRoot("Favorites")
    for favorite in store.favorites:
        label = favorites_marks.label_for(marks, favorite.key, favorite.display_label)
        item = tree.AppendItem(root, label)
        tree.SetItemData(item, ("station", favorite.key))
    return tree


def _select(tree, index: int) -> None:
    root = tree.GetRootItem()
    child, cookie = tree.GetFirstChild(root)
    for _ in range(index):
        child, cookie = tree.GetNextChild(root, cookie)
    tree.SelectItem(child)


def _key(code: int, *, ctrl: bool = False, shift: bool = False):
    return SimpleNamespace(
        GetKeyCode=lambda: code,
        ControlDown=lambda: ctrl,
        ShiftDown=lambda: shift,
        AltDown=lambda: False,
    )


def test_period_marks_the_row_and_says_how_many(frame) -> None:
    store, marks, said = _store(), RowMarks(), []
    tree = _tree(frame, store, marks)
    _select(tree, 1)

    used = favorites_marks.handle_key(
        wx,
        _key(ord(".")),
        tree=tree,
        marks=marks,
        store=store,
        parent=frame,
        announce=said.append,
        changed=lambda _key: None,
    )

    assert used
    assert said == ["Marked. 1 marked."]
    assert tree.GetItemText(tree.GetSelection()) == "Station 1 (marked)"


def test_delete_with_marks_asks_once_with_the_count(frame, monkeypatch) -> None:
    store, marks, said, asked, landed = _store(), RowMarks(), [], [], []
    tree = _tree(frame, store, marks)
    for index in (1, 2, 3):
        _select(tree, index)
        favorites_marks.toggle_selected(tree, marks, store, announce=said.append)
    _select(tree, 2)

    def ask(question: str) -> bool:
        asked.append(question)
        return True

    monkeypatch.setattr(favorites_marks, "_ask_with_message_box", lambda _parent: ask)
    used = favorites_marks.handle_key(
        wx,
        _key(wx.WXK_DELETE),
        tree=tree,
        marks=marks,
        store=store,
        parent=frame,
        announce=said.append,
        changed=landed.append,
    )

    assert used
    assert asked == ["Delete 3 stations?"]
    assert said[-1] == "Deleted 3 stations."
    assert [f.display_label for f in store.favorites] == ["Station 0", "Station 4"]
    assert landed == ["https://s4.test/"], "the cursor lands on the next survivor"
    assert len(marks) == 0


def test_saying_no_deletes_nothing_and_keeps_the_marks(frame) -> None:
    store, marks, said = _store(), RowMarks(), []
    marks.toggle(store.favorites[0].key)

    removed = favorites_marks.remove_marked(
        frame, store, marks, announce=said.append, ask=lambda _q: False
    )

    assert removed is False
    assert len(store.favorites) == 5
    assert said == ["Nothing was deleted."]
    assert len(marks) == 1


def test_delete_without_marks_is_left_to_the_single_row_remove(frame) -> None:
    store, marks = _store(), RowMarks()
    tree = _tree(frame, store, marks)
    _select(tree, 0)

    used = favorites_marks.handle_key(
        wx,
        _key(wx.WXK_DELETE),
        tree=tree,
        marks=marks,
        store=store,
        parent=frame,
        announce=lambda _m: None,
        changed=lambda _key: None,
    )

    assert used is False


def test_ctrl_shift_delete_clears_every_mark(frame) -> None:
    store, marks, said = _store(), RowMarks(), []
    tree = _tree(frame, store, marks)
    marks.toggle(store.favorites[0].key)
    marks.toggle(store.favorites[1].key)

    used = favorites_marks.handle_key(
        wx,
        _key(wx.WXK_DELETE, ctrl=True, shift=True),
        tree=tree,
        marks=marks,
        store=store,
        parent=frame,
        announce=said.append,
        changed=lambda _key: None,
    )

    assert used
    assert said == ["Cleared 2 marks."]
    assert len(marks) == 0


def test_the_menu_shows_the_keys_and_one_claimant_for_delete() -> None:
    marks = RowMarks()
    rows = favorites_marks.mark_menu_entries(
        marks, toggle=lambda: None, remove=lambda: None, clear=lambda: None
    )
    assert [label for label, _h in rows] == ["Mark &for Deleting\t."]
    marks.toggle("a")
    marks.toggle("b")
    rows = favorites_marks.mark_menu_entries(
        marks, toggle=lambda: None, remove=lambda: None, clear=lambda: None
    )
    assert [label for label, _h in rows] == [
        "Mark &for Deleting\t.",
        "&Remove 2 Marked...\tDelete",
        "&Clear Marks\tCtrl+Shift+Delete",
    ]
