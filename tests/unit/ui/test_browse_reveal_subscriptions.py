"""Reloading the Subscriptions branch after a subscription changes.

Reported 2026-08-18: the three "you have no subscriptions yet" filler rows sat
there after subscribing, and the new show was nowhere until Refresh was pressed
by hand. The cause was narrow and exact -- the reload looked for the
Subscriptions node by walking *up from the cursor*, and Subscribe is pressed on
an Apple show, which is not underneath it.
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio import browse_reveal


class _Item:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.children: list[_Item] = []
        self.data: dict = {"node_id": node_id, "loaded": True}
        self.expanded = False

    def IsOk(self) -> bool:  # noqa: N802 - wx's own casing
        return True


class _Missing:
    def IsOk(self) -> bool:  # noqa: N802
        return False


class _Tree:
    def __init__(self, root: _Item) -> None:
        self.root = root
        self.selection: Any = _Missing()

    def GetRootItem(self) -> _Item:  # noqa: N802
        return self.root

    def GetSelection(self):  # noqa: N802
        return self.selection

    def GetItemParent(self, item: _Item):  # noqa: N802
        stack = [self.root]
        while stack:
            node = stack.pop()
            if item in node.children:
                return node
            stack.extend(node.children)
        return _Missing()

    def GetFirstChild(self, item: _Item):  # noqa: N802
        return (item.children[0], 0) if item.children else (_Missing(), 0)

    def GetNextChild(self, item: _Item, cookie: int):  # noqa: N802
        index = cookie + 1
        return (item.children[index], index) if index < len(item.children) else (_Missing(), index)

    def DeleteChildren(self, item: _Item) -> None:  # noqa: N802
        item.children = []

    def AppendItem(self, parent: _Item, _text: str) -> _Item:  # noqa: N802
        child = _Item("placeholder")
        parent.children.append(child)
        return child

    def SetItemData(self, item: _Item, data: dict) -> None:  # noqa: N802
        item.data = data

    def Collapse(self, item: _Item) -> None:  # noqa: N802
        # A refetch collapses before it expands: wx fires no expanding event
        # for a node it already considers open, and that event is the reload.
        item.expanded = False

    def Expand(self, item: _Item) -> None:  # noqa: N802
        item.expanded = True


class _Dialog:
    def __init__(self, tree: _Tree) -> None:
        self._tree = tree
        self._pending_reveal: dict | None = None

    def _node_data(self, node: Any) -> dict | None:
        return getattr(node, "data", None)


def _tree_with_subscriptions() -> tuple[_Dialog, _Item, _Item]:
    """Apple Podcasts holding Subscriptions, and a show row well away from it."""
    root = _Item("root")
    apple = _Item("apple")
    subscriptions = _Item("mypodcasts")
    apple.children = [subscriptions]
    tunein = _Item("tunein")
    a_show = _Item("appleshow:42")
    tunein.children = [a_show]
    root.children = [apple, tunein]
    return _Dialog(_Tree(root)), subscriptions, a_show


def test_subscribing_from_elsewhere_still_reloads_subscriptions() -> None:
    dialog, subscriptions, a_show = _tree_with_subscriptions()
    subscriptions.children = [_Item("addpodcasturl")]  # the filler rows
    dialog._tree.selection = a_show

    assert browse_reveal.refetch_subscriptions(dialog) is True
    assert subscriptions.data["loaded"] is False  # it will fetch again
    assert subscriptions.expanded
    # The filler rows are gone; one lazy placeholder stands in their place
    # until the expand handler refills the branch from the library.
    assert [child.data for child in subscriptions.children] == [{"kind": "placeholder"}]


def test_the_cursor_is_not_dragged_across_the_tree() -> None:
    # Reloading is the fix; yanking the cursor away from the list somebody is
    # working through is not. A reveal is only queued when they were already
    # inside the Subscriptions subtree.
    dialog, _subscriptions, a_show = _tree_with_subscriptions()
    dialog._tree.selection = a_show

    assert browse_reveal.refetch_and_reveal(dialog, feed_url="https://f") is True
    assert dialog._pending_reveal is None


def test_a_reveal_is_queued_when_the_edit_was_made_inside_subscriptions() -> None:
    dialog, subscriptions, _a_show = _tree_with_subscriptions()
    show_row = _Item("mypodcastshow:https://f")
    subscriptions.children = [show_row]
    dialog._tree.selection = show_row

    assert browse_reveal.refetch_and_reveal(dialog, feed_url="https://f") is True
    assert dialog._pending_reveal == {"feed_url": "https://f", "folder_id": ""}


def test_a_branch_that_was_never_opened_reports_honestly() -> None:
    # Nothing stale to correct, and the caller falls back to its spoken
    # "Refresh Podcasts to update." rather than claiming it refreshed.
    root = _Item("root")
    root.children = [_Item("tunein")]
    dialog = _Dialog(_Tree(root))

    assert browse_reveal.refetch_subscriptions(dialog) is False
