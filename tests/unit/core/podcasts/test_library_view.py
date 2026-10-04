"""Rich library and Inbox views (Jeff, 2026-10-03): every layout, nothing hidden."""

from __future__ import annotations

from quill.core.podcasts import library_view as lv
from quill.core.podcasts.models import PodcastFolder, PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library() -> PodcastLibrary:
    library = PodcastLibrary()
    library.folders = [
        PodcastFolder(id="news", name="News"),
        PodcastFolder(id="local", name="Local", parent_folder_id="news"),
        PodcastFolder(id="art", name="Arts"),
        PodcastFolder(id="empty", name="Empty"),
    ]
    for sid, title, folder, unheard in (
        ("a", "Daily", "news", 2),
        ("b", "City Hall", "local", 1),
        ("c", "Gallery", "art", 0),
        ("d", "Loose", None, 3),
    ):
        show = PodcastShow(id=sid, title=title, feed_url=f"https://x/{sid}", folder_id=folder)
        show.episodes = [
            PodcastEpisode(guid=f"{sid}{n}", title=f"{title} {n}", audio_url="u")
            for n in range(unheard)
        ]
        library.shows.append(show)
    return library


def _ids(nodes: list[lv.Node]) -> list[str]:
    return [node.id for node in nodes]


def _every_show(nodes: list[lv.Node]) -> set[str]:
    found: set[str] = set()
    for node in nodes:
        if node.kind == "show":
            found.add(node.id)
        found |= _every_show(node.children)
    return found


def test_folders_first_is_the_default_and_keeps_what_was_there() -> None:
    library = _library()
    nodes = lv.library_nodes(library, library.shows)
    assert _ids(nodes) == ["news", "art", "empty", "d"]
    assert nodes[0].label == "News (2 podcasts, 3 unheard)"
    assert _ids(nodes[0].children) == ["local", "a"]
    assert nodes[0].open


def test_every_layout_reaches_every_podcast() -> None:
    library = _library()
    for layout, _words in lv_layouts():
        lv.set_setting(library, "library_layout", layout)
        assert _every_show(lv.library_nodes(library, library.shows)) == {"a", "b", "c", "d"}, layout


def lv_layouts():
    from quill.core.podcasts.settings_defs_views import LIBRARY_LAYOUTS

    return LIBRARY_LAYOUTS


def test_folders_only_puts_loose_podcasts_in_their_own_group_closed() -> None:
    library = _library()
    lv.set_setting(library, "library_layout", "folders_only")
    nodes = lv.library_nodes(library, library.shows)
    assert all(node.kind == "folder" for node in nodes)
    assert nodes[-1].id == lv.NO_FOLDER and _ids(nodes[-1].children) == ["d"]
    assert not any(node.open for node in nodes)


def test_podcasts_only_and_mixed() -> None:
    library = _library()
    lv.set_setting(library, "library_layout", "podcasts_only")
    assert _ids(lv.library_nodes(library, library.shows)) == ["a", "b", "c", "d"]
    lv.set_setting(library, "library_layout", "mixed")
    labels = [node.label for node in lv.library_nodes(library, library.shows)]
    assert labels == sorted(labels, key=str.casefold)


def test_folder_order_counts_and_empty_folders() -> None:
    library = _library()
    lv.set_setting(library, "folder_sort_mode", "most_unheard")
    lv.set_setting(library, "library_counts", "none")
    lv.set_setting(library, "library_hide_empty_folders", True)
    nodes = lv.library_nodes(library, library.shows)
    assert _ids(nodes) == ["news", "art", "d"]
    assert nodes[0].label == "News"


def test_the_inbox_folders_first_and_folders_only() -> None:
    library = _library()
    pairs = [(show, ep) for show in library.shows for ep in show.episodes]
    assert all(row.kind == "episode" for row in lv.inbox_rows(library, pairs))
    lv.set_setting(library, "inbox_layout", "folders_first")
    rows = lv.inbox_rows(library, pairs)
    assert [r.folder_id for r in rows if r.kind == "inbox_folder"] == ["news"]
    assert rows[0].label == "News, folder, 3 in the Inbox"
    assert [r.pair[0].id for r in rows if r.kind == "episode"] == ["d", "d", "d"]
    assert len(lv.inbox_folder_pairs(library, pairs, "news")) == 3
    lv.set_setting(library, "inbox_layout", "folders_only")
    rows = lv.inbox_rows(library, pairs)
    assert [r.folder_id for r in rows] == ["news", lv.NO_FOLDER]
    assert len(lv.inbox_folder_pairs(library, pairs, lv.NO_FOLDER)) == 3
