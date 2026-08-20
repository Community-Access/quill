"""Search All Sources answers inside the browse tree, not somewhere else.

Reported 2026-08-18: *"search all sources is taking me somewhere else, I would
prefer to stay in the browse dialog and show the results in a general list with
its type showing and rich context menu options as though it was done from that
folder."* -- and, separately, that escaping out of the old search left focus
nowhere.

A stand-in tree rather than a wx.App: everything asserted here is about what
rows are built and where the cursor lands, which a fake ``TreeCtrl`` answers
exactly and a real one only answers slowly.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import federated_browse
from quill.core.radio.browse_helpers import row_label
from quill.core.radio.browse_nodes import folder, leaf
from quill.core.radio.models import RadioStation
from quill.ui.radio import browse_search_all


class _Item:
    """One tree row."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.data: Any = None
        self.children: list[_Item] = []
        self.expanded = False

    def IsOk(self) -> bool:  # noqa: N802 - wx's own casing
        return True


class _Tree:
    """Enough wx.TreeCtrl to build and clear a results branch."""

    def __init__(self) -> None:
        self.root = _Item("Sources")
        self.selected: _Item | None = None
        self.focused = False

    def GetRootItem(self) -> _Item:  # noqa: N802
        return self.root

    def _parent_of(self, item: _Item) -> _Item:
        stack = [self.root]
        while stack:
            node = stack.pop()
            if item in node.children:
                return node
            stack.extend(node.children)
        return self.root

    def GetFirstChild(self, item: _Item):  # noqa: N802
        return (item.children[0], 0) if item.children else (_Missing(), 0)

    def GetNextChild(self, item: _Item, cookie: int):  # noqa: N802
        index = cookie + 1
        return (item.children[index], index) if index < len(item.children) else (_Missing(), index)

    def AppendItem(self, parent: _Item, text: str) -> _Item:  # noqa: N802
        child = _Item(text)
        parent.children.append(child)
        return child

    def PrependItem(self, parent: _Item, text: str) -> _Item:  # noqa: N802
        child = _Item(text)
        parent.children.insert(0, child)
        return child

    def InsertItem(self, parent: _Item, previous: _Item, text: str) -> _Item:  # noqa: N802
        child = _Item(text)
        parent.children.insert(parent.children.index(previous) + 1, child)
        return child

    def SetItemData(self, item: _Item, data: Any) -> None:  # noqa: N802
        item.data = data

    def GetItemData(self, item: _Item) -> Any:  # noqa: N802
        return item.data

    def Delete(self, item: _Item) -> None:  # noqa: N802
        self._parent_of(item).children.remove(item)

    def Expand(self, item: _Item) -> None:  # noqa: N802
        item.expanded = True

    def SelectItem(self, item: _Item) -> None:  # noqa: N802
        self.selected = item

    def SetFocus(self) -> None:  # noqa: N802
        self.focused = True


class _Missing:
    """What wx hands back for "no such child"."""

    def IsOk(self) -> bool:  # noqa: N802
        return False


class _Tasks:
    def submit(self, _name, work, *, on_success=None, on_failure=None):
        result = work()
        if on_success is not None:
            on_success(_name, result)


class _Entry:
    def __init__(self, value: str, ok: bool) -> None:
        self._value, self._ok = value, ok

    def ShowModal(self) -> int:  # noqa: N802
        return 5100 if self._ok else 5101

    def GetValue(self) -> str:  # noqa: N802
        return self._value

    def Destroy(self) -> None:  # noqa: N802
        return None


class _Wx:
    ID_OK = 5100

    def __init__(self, typed: str = "", ok: bool = True) -> None:
        self.typed, self.ok = typed, ok

    def TextEntryDialog(self, _parent, _prompt, _title, value: str = "") -> _Entry:  # noqa: N802
        return _Entry(self.typed, self.ok)


class _Host:
    """The browse dialog's surface that browse_search_all actually touches."""

    def __init__(self, *, typed: str = "jazz", ok: bool = True) -> None:
        self._wx = _Wx(typed, ok)
        self._win = object()
        self._tree = _Tree()
        self._safe_mode = False
        self._task_manager = _Tasks()
        self._find_active = False
        self._find_return_node = None
        self.said: list[str] = []
        # The first row of a real tree is always Search All Sources...
        search_row = self._tree.AppendItem(self._tree.root, "Search All Sources...")
        self._tree.SetItemData(search_row, {"node_id": "searchall", "is_action": True})

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _node_data(self, node: Any) -> Any:
        return self._tree.GetItemData(node)

    def _placeholder(self) -> dict:
        return {"kind": "placeholder"}

    def _row_label(self, child: Any) -> str:
        return row_label(child)

    def _row_data(self, child: Any) -> dict:
        if child.is_folder:
            return {"node_id": child.node_id, "label": child.label, "loaded": False}
        return {"node_id": child.node_id, "label": child.label, "station": child.station}


def _rows(host: _Host) -> list[str]:
    return [item.text for item in host._tree.root.children]


def _found(rows: list) -> federated_browse.FederatedBrowse:
    found = federated_browse.FederatedBrowse()
    found.rows = rows
    for row in rows:
        kind = row.note.split(",", 1)[0]
        found.counts[kind] = found.counts.get(kind, 0) + 1
    return found


def _station(name: str) -> RadioStation:
    return RadioStation(name=name, stream_url=f"https://s/{name}")


def test_results_land_in_this_tree_directly_under_the_search_row() -> None:
    host = _Host()
    rows = [leaf(_station("Jazz FM"), note="Station, TuneIn")]

    browse_search_all.show_results(host, "jazz", _found(rows))

    assert _rows(host) == ["Search All Sources...", 'Search Results: "jazz"  (1)']


def test_every_result_row_says_what_it_is() -> None:
    host = _Host()
    rows = [
        leaf(_station("Jazz FM"), note="Station, TuneIn"),
        folder("appleshow:1", "Jazz Talk", note="Podcast, Apple Podcasts"),
    ]

    browse_search_all.show_results(host, "jazz", _found(rows))

    labels = [item.text for item in host._tree.root.children[1].children]
    assert labels == ["Jazz FM  (Station, TuneIn)", "Jazz Talk  (Podcast, Apple Podcasts)"]


def test_a_found_folder_keeps_its_id_and_its_expander() -> None:
    # This is what makes the context menu the browsed one: the row carries the
    # node id its own source would have produced, so Subscribe and the episode
    # list both work from a search result.
    host = _Host()
    browse_search_all.show_results(
        host, "jazz", _found([folder("appleshow:99", "A Show", note="Podcast, Apple Podcasts")])
    )

    show_row = host._tree.root.children[1].children[0]
    assert show_row.data["node_id"] == "appleshow:99"
    assert [child.text for child in show_row.children] == ["Loading..."]


def test_the_cursor_lands_on_the_first_result() -> None:
    host = _Host()
    browse_search_all.show_results(
        host, "jazz", _found([leaf(_station("Jazz FM"), note="Station")])
    )

    assert host._tree.selected is host._tree.root.children[1].children[0]
    assert host._tree.focused


def test_searching_again_replaces_the_previous_results() -> None:
    host = _Host()
    browse_search_all.show_results(
        host, "jazz", _found([leaf(_station("Jazz FM"), note="Station")])
    )
    browse_search_all.show_results(
        host, "rock", _found([leaf(_station("Rock FM"), note="Station")])
    )

    assert _rows(host) == ["Search All Sources...", 'Search Results: "rock"  (1)']


def test_nothing_found_still_leaves_a_row_that_says_so() -> None:
    host = _Host()
    browse_search_all.show_results(host, "zzz", _found([]))

    results = host._tree.root.children[1]
    assert [child.text for child in results.children] == ["Nothing found for zzz."]
    assert any("Nothing found for zzz" in said for said in host.said)


def test_clearing_takes_the_branch_and_the_cursor_somewhere_real() -> None:
    # The dead-focus report: the row the cursor was on is one of the rows being
    # deleted, so clearing has to put it somewhere that still exists.
    host = _Host()
    browse_search_all.show_results(
        host, "jazz", _found([leaf(_station("Jazz FM"), note="Station")])
    )

    host._tree.focused = False

    assert browse_search_all.clear_results(host) is True
    assert _rows(host) == ["Search All Sources..."]
    assert host._tree.selected is host._tree.root.children[0]
    # ...but focus is NOT dragged into the tree: clearing is a refresh, not a
    # destination, and somebody who cleared from the Find box is still typing
    # there ("let the user move", 2026-08-18).
    assert host._tree.focused is False
    assert browse_search_all.clear_results(host) is False


def test_cancelling_the_prompt_searches_nothing_and_returns_focus() -> None:
    host = _Host(typed="", ok=False)

    browse_search_all.run(host)

    assert host.said == []
    assert _rows(host) == ["Search All Sources..."]
    assert host._tree.focused  # not left in the closed dialog


def test_escape_can_reach_the_clear_because_the_results_count_as_active() -> None:
    # browse_find.clear_find only runs when a search is active; without this
    # flag Escape in the Find box would not clear these results at all.
    host = _Host()
    browse_search_all.show_results(
        host, "jazz", _found([leaf(_station("Jazz FM"), note="Station")])
    )

    assert host._find_active is True
