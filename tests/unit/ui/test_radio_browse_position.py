"""Browse position memory (quill.ui.radio.browse_position) with a fake tree."""

from __future__ import annotations

import pytest

from quill.ui.radio import browse_position


class FakeItem:
    def __init__(self, label: str, parent: FakeItem | None = None, ok: bool = True) -> None:
        self.label = label
        self.parent = parent
        self._ok = ok

    def IsOk(self) -> bool:  # noqa: N802 - mimics wx.TreeItemId
        return self._ok


class FakeTree:
    """The minimal slice of wx.TreeCtrl that browse_position uses."""

    def __init__(self, top_labels: list[str]) -> None:
        self.root = FakeItem("root")
        self.children = [FakeItem(label, self.root) for label in top_labels]
        self.selected: FakeItem | None = None

    def GetRootItem(self) -> FakeItem:  # noqa: N802
        return self.root

    def GetItemParent(self, node: FakeItem) -> FakeItem:  # noqa: N802
        return node.parent if node.parent is not None else FakeItem("nil", ok=False)

    def GetItemText(self, node: FakeItem) -> str:  # noqa: N802
        return node.label

    def GetFirstChild(self, _root: FakeItem) -> tuple[FakeItem, int]:  # noqa: N802
        return (self.children[0], 0) if self.children else (FakeItem("nil", ok=False), 0)

    def GetNextChild(self, _root: FakeItem, cookie: int) -> tuple[FakeItem, int]:  # noqa: N802
        i = cookie + 1
        return (self.children[i], i) if i < len(self.children) else (FakeItem("nil", ok=False), i)

    def SelectItem(self, node: FakeItem) -> None:  # noqa: N802
        self.selected = node


@pytest.fixture(autouse=True)
def _reset_memory() -> None:
    browse_position._last_top_source = None


def test_restore_selects_first_when_nothing_remembered() -> None:
    tree = FakeTree(["Favorites", "Popular Stations", "Networks"])
    browse_position.restore_selection(tree, tree.root)
    assert tree.selected is tree.children[0]  # Favorites


def test_remember_then_restore_returns_to_that_source() -> None:
    tree = FakeTree(["Favorites", "Popular Stations", "Networks"])
    browse_position.remember(tree, tree.children[2])  # user was on Networks
    tree2 = FakeTree(["Favorites", "Popular Stations", "Networks"])  # reopened
    browse_position.restore_selection(tree2, tree2.root)
    assert tree2.selected.label == "Networks"


def test_remember_walks_up_to_the_top_level_source() -> None:
    tree = FakeTree(["Favorites", "Networks"])
    networks = tree.children[1]
    group = FakeItem("Public broadcasters", networks)
    station = FakeItem("BBC Radio 4", group)  # a deep node
    browse_position.remember(tree, station)
    assert browse_position._last_top_source == "Networks"


def test_restore_falls_back_when_remembered_source_is_gone() -> None:
    browse_position._last_top_source = "A Source That No Longer Exists"
    tree = FakeTree(["Favorites", "Popular Stations"])
    browse_position.restore_selection(tree, tree.root)
    assert tree.selected is tree.children[0]
