"""Pure-logic coverage for manager_dialog.py's folder-subtree helper, used
by the per-folder "set all shows here to stream/download" bulk toggle --
wx-free, no dialog construction needed."""

from __future__ import annotations

from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.manager_dialog import _item_key, _shows_in_folder_subtree


def test_item_key_is_stable_across_getid_calls() -> None:
    # #1189: wx's TreeItemId.GetID() returns a fresh sip.voidptr wrapper on
    # every call, so keying the item->show dict by the wrapper missed every
    # lookup and no episodes loaded. _item_key must key by the raw int, so the
    # store-time key and the lookup-time key are equal.
    class _VoidPtr:
        def __init__(self, ptr: int) -> None:
            self._ptr = ptr

        def __int__(self) -> int:
            return self._ptr

    class _Item:
        def __init__(self, ptr: int) -> None:
            self._ptr = ptr

        def GetID(self) -> _VoidPtr:
            return _VoidPtr(self._ptr)  # a fresh, non-equal wrapper each call

    item = _Item(0xABCD)
    assert _item_key(item) == _item_key(item) == 0xABCD  # stable, not identity-of-wrapper
    plain = object()
    assert _item_key(plain) == id(plain)  # no GetID -> id() fallback


def test_finds_shows_directly_in_the_folder() -> None:
    library = PodcastLibrary()
    folder = library.add_folder("News")
    show = PodcastShow(id="s1", title="Show A", feed_url="https://a/feed.xml", folder_id=folder.id)
    library.add_show(show)
    assert _shows_in_folder_subtree(library, folder.id) == [show]


def test_recurses_into_nested_subfolders() -> None:
    library = PodcastLibrary()
    parent = library.add_folder("Tech")
    child = library.add_folder("Deep Dives", parent_folder_id=parent.id)
    grandchild = library.add_folder("Archive", parent_folder_id=child.id)
    top_show = PodcastShow(id="s1", title="Top", feed_url="https://a/feed.xml", folder_id=parent.id)
    nested_show = PodcastShow(
        id="s2", title="Nested", feed_url="https://b/feed.xml", folder_id=child.id
    )
    deep_show = PodcastShow(
        id="s3", title="Deep", feed_url="https://c/feed.xml", folder_id=grandchild.id
    )
    library.add_show(top_show)
    library.add_show(nested_show)
    library.add_show(deep_show)

    found = _shows_in_folder_subtree(library, parent.id)
    assert {s.id for s in found} == {"s1", "s2", "s3"}


def test_excludes_shows_in_sibling_folders() -> None:
    library = PodcastLibrary()
    folder_a = library.add_folder("A")
    folder_b = library.add_folder("B")
    show_a = PodcastShow(
        id="s1", title="A Show", feed_url="https://a/feed.xml", folder_id=folder_a.id
    )
    show_b = PodcastShow(
        id="s2", title="B Show", feed_url="https://b/feed.xml", folder_id=folder_b.id
    )
    library.add_show(show_a)
    library.add_show(show_b)

    assert _shows_in_folder_subtree(library, folder_a.id) == [show_a]


def test_empty_folder_returns_empty_list() -> None:
    library = PodcastLibrary()
    folder = library.add_folder("Empty")
    assert _shows_in_folder_subtree(library, folder.id) == []
