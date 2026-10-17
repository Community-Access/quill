"""Selection and close sequencing for Cast's podcast list."""

# ruff: noqa: E402

from __future__ import annotations

from time import monotonic, sleep
from types import SimpleNamespace

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.apps.podcasts import PodcastsAppFrame
from quill.apps.podcasts_library_actions import CastLibraryActionsMixin
from quill.core.podcasts import folder_membership
from quill.core.podcasts.models import PodcastFolder, PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.close_tasks import advance_close
from quill.ui.podcasts.library_tree_updates import cancel_tree_update, reload_tree, row_key
from quill.ui.podcasts.main_panel import CastMainPanelMixin
from quill.ui.podcasts.places import CastPlacesMixin


class _Item:
    def __init__(self, name: str) -> None:
        self.name = name

    def IsOk(self) -> bool:
        return True


class _Tree:
    def __init__(self) -> None:
        self.folder = _Item("folder")
        self.rows = [_Item(name) for name in ("before", "moved", "after")]
        self.data = {self.folder: ("folder", "folder-id")}
        self.data.update({row: ("show", row.name) for row in self.rows})
        self.selection = self.rows[1]

    def GetSelection(self):
        return self.selection

    def GetItemParent(self, _item):
        return self.folder

    def GetFirstChild(self, _parent):
        return self.rows[0], 1

    def GetNextChild(self, _parent, cookie):
        if cookie < len(self.rows):
            return self.rows[cookie], cookie + 1
        return SimpleNamespace(IsOk=lambda: False), cookie

    def GetItemData(self, item):
        return self.data[item]

    def GetNextSibling(self, item):
        index = self.rows.index(item) + 1
        return self.rows[index] if index < len(self.rows) else SimpleNamespace(IsOk=lambda: False)

    def GetPrevSibling(self, item):
        index = self.rows.index(item) - 1
        return self.rows[index] if index >= 0 else SimpleNamespace(IsOk=lambda: False)


def test_move_anchor_selects_next_sibling_then_previous_then_folder() -> None:
    tree = _Tree()
    host = SimpleNamespace(_shows_tree=tree, _podcast_library=SimpleNamespace())
    anchor = CastLibraryActionsMixin._neighbor_of_selected_placement
    assert anchor(host) == ("show", "after")
    tree.selection = tree.rows[-1]
    assert anchor(host) == ("show", "moved")
    tree.rows = [tree.selection]
    assert anchor(host) == ("folder", "folder-id")


def test_close_runs_one_step_per_event_turn() -> None:
    calls: list[str] = []
    scheduled = []
    host = SimpleNamespace(
        _cast_closed=False,
        _cast_close_steps=iter((
            ("one", "best_effort", lambda: calls.append("one")),
            ("two", "best_effort", lambda: calls.append("two")),
        )),
        _cast_close_report=SimpleNamespace(step=lambda _name, _category, action: action()),
        _wx=SimpleNamespace(CallLater=lambda _ms, fn, owner: scheduled.append(lambda: fn(owner))),
    )
    advance_close(host)
    assert calls == ["one"]
    assert len(scheduled) == 1
    scheduled.pop(0)()
    assert calls == ["one", "two"]


def test_arrow_selection_does_not_refresh_status_cells() -> None:
    calls = []
    host = SimpleNamespace(
        _unfollow_btn=None,
        _transport_control_chunks=lambda **kwargs: (calls.append(kwargs) for _ in (None,)),
    )
    list(CastPlacesMixin._selection_button_chunks(host))
    assert calls == [{"include_status": False}]


@pytest.fixture
def queued_selection_refresh():
    callbacks = []
    refreshed = []
    host = SimpleNamespace(
        frame=SimpleNamespace(IsBeingDeleted=lambda: False),
        _wx=SimpleNamespace(CallAfter=callbacks.append),
        _cast_closing=False,
        _cast_closed=False,
        _cast_cursor_revision=0,
        selected="before",
        _refresh_selection_buttons=lambda: refreshed.append(host.selected),
        _refresh_notes_pane=lambda: None,
    )
    return host, callbacks, refreshed


def test_rapid_selection_queues_one_button_refresh_for_the_latest_cursor(
    queued_selection_refresh,
) -> None:
    host, callbacks, refreshed = queued_selection_refresh
    event = SimpleNamespace(Skip=lambda: None)
    for selected in ("before", "after", "last"):
        host.selected = selected
        CastMainPanelMixin._on_cast_content_selected(host, event)
    assert host._cast_cursor_revision == 3
    assert len(callbacks) == 1
    assert not refreshed
    callbacks.pop(0)()
    assert refreshed == ["last"]
    assert not host._cast_selection_refresh_pending
    host.selected = "next"
    CastMainPanelMixin._on_cast_content_selected(host, event)
    assert len(callbacks) == 1
    callbacks.pop(0)()
    assert refreshed == ["last", "next"]


def test_selection_button_refresh_without_call_after_is_synchronous(
    queued_selection_refresh,
) -> None:
    host, callbacks, refreshed = queued_selection_refresh
    del host._wx.CallAfter
    CastMainPanelMixin._on_cast_content_selected(host, SimpleNamespace(Skip=lambda: None))
    assert refreshed == ["before"]
    assert not callbacks
    assert not host._cast_selection_refresh_pending


@pytest.mark.parametrize("state", ["_cast_closing", "_cast_closed"])
def test_queued_selection_button_refresh_does_not_touch_a_closing_window(
    queued_selection_refresh, state
) -> None:
    host, callbacks, refreshed = queued_selection_refresh
    CastMainPanelMixin._on_cast_content_selected(host, SimpleNamespace(Skip=lambda: None))
    setattr(host, state, True)
    callbacks.pop(0)()
    assert not refreshed
    assert not host._cast_selection_refresh_pending


def test_periodic_save_waits_for_the_feed_run_before_redrawing(monkeypatch) -> None:
    from quill.ui.main_frame_podcast_save import PodcastLibrarySaveMixin

    monkeypatch.setattr(PodcastLibrarySaveMixin, "_save_podcast_library", lambda _host: None)
    monkeypatch.setattr(PodcastLibrarySaveMixin, "_flush_podcast_library", lambda _host: None)
    host = PodcastsAppFrame.__new__(PodcastsAppFrame)
    host._shows_tree = _Tree()
    host._check_run = object()
    host._current_place = "podcasts"
    host._podcast_library_is_large = lambda: False
    updates = []
    host._reload_library_tree = lambda **kwargs: updates.append(kwargs["keep_key"])
    host._refresh_place_counts = lambda: pytest.fail("Counts redrawn during the feed run")
    keep = ("show", "after")

    host._save_podcast_library(keep_key=keep)
    host._flush_podcast_library()
    assert host._tree_reload_pending
    assert not updates
    host._check_run = None
    host._flush_podcast_library()
    host._flush_podcast_library()
    assert updates == [keep]
    assert not host._tree_reload_pending
    assert host._tree_reload_keep_key is None


def test_explicit_folder_move_does_not_wait_for_refresh_all_to_finish(monkeypatch) -> None:
    from quill.ui.main_frame_podcast_save import PodcastLibrarySaveMixin

    monkeypatch.setattr(PodcastLibrarySaveMixin, "_save_podcast_library", lambda _host: None)
    host = PodcastsAppFrame.__new__(PodcastsAppFrame)
    host._shows_tree = _Tree()
    host._check_run = object()
    host._current_place = "podcasts"
    host._podcast_library_is_large = lambda: True
    updates = []
    host._reload_library_tree = lambda **kwargs: updates.append(kwargs["keep_key"])
    host._refresh_place_counts = lambda: None
    host._save_podcast_library(keep_key=("show", "after"), refresh_now=True)
    assert updates == [("show", "after")]
    assert not host._tree_reload_pending


@pytest.mark.parametrize("state", ["_cast_closing", "_cast_closed"])
def test_closing_does_not_plan_another_native_tree_update(state) -> None:
    host = SimpleNamespace(
        _library_find_active=lambda: pytest.fail("A closing tree was read"),
    )
    setattr(host, state, True)
    reload_tree(host)


@pytest.fixture
def native_tree():
    app = wx.GetApp() or shared_wx_app()
    previous_loop = wx.EventLoop.GetActive()
    loop = wx.GUIEventLoop()
    wx.EventLoop.SetActive(loop)
    owners = []

    def create(library: PodcastLibrary):
        frame = wx.Frame(None)
        tree = wx.TreeCtrl(frame, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT)
        host = SimpleNamespace(
            _wx=wx,
            _shows_tree=tree,
            _podcast_library=library,
            _library_find_active=lambda: False,
            _visible_library_shows=lambda: library.shows,
            _podcast_library_is_large=lambda: False,
            _cast_cursor_revision=0,
            _cast_closed=False,
            _cast_closing=False,
            _EPISODES_PER_SHOW_NODE=200,
            _announce=lambda message: pytest.fail(message),
        )
        tree.Bind(
            wx.EVT_TREE_ITEM_EXPANDING,
            lambda event: PodcastsAppFrame._on_library_expanding(host, event),
        )

        def selected(event):
            if not getattr(host, "_cast_tree_mutating", False):
                host._cast_cursor_revision += 1
            event.Skip()

        tree.Bind(wx.EVT_TREE_SEL_CHANGED, selected)
        owners.append((frame, host))
        frame.Show()
        app.Yield()
        return tree, host

    try:
        yield create
    finally:
        for frame, host in owners:
            cancel_tree_update(host)
            frame.Destroy()
        app.ProcessPendingEvents()
        loop.ProcessIdle()
        wx.EventLoop.SetActive(previous_loop)


def _wait_for_tree(host) -> None:
    deadline = monotonic() + 5
    while host._cast_tree_chunks is not None:
        assert monotonic() < deadline, "The native library tree did not finish drawing"
        wx.YieldIfNeeded()
        sleep(0.001)


def _reload_native_tree(host, **kwargs) -> None:
    reload_tree(host, **kwargs)
    _wait_for_tree(host)


@pytest.mark.parametrize(("moved", "neighbor"), [("middle", "last"), ("last", "middle")])
def test_filing_keeps_native_neighbors_and_focus_during_count_publication(
    native_tree, monkeypatch, moved, neighbor
) -> None:
    library = PodcastLibrary(
        shows=[PodcastShow(id=name, title=name) for name in ("first", "middle", "last")],
        folders=[PodcastFolder(id="destination", name="Destination")],
    )
    tree, host = native_tree(library)
    _reload_native_tree(host)
    before = dict(host._cast_tree_items)
    tree.SelectItem(before[("show", moved)])
    tree.SetFocus()
    deleted_all = []
    original_delete = tree.DeleteAllItems

    def delete_all():
        deleted_all.append(True)
        original_delete()

    monkeypatch.setattr(tree, "DeleteAllItems", delete_all)
    folder_membership.move_to(library, library.find_show(moved), "destination", source=None)
    host._podcast_library_is_large = lambda: True
    reload_tree(host, keep_key=("show", neighbor))
    # A counts result can arrive before the first scheduled drawing turn.
    reload_tree(host)
    _wait_for_tree(host)
    assert row_key(host, tree.GetSelection()) == ("show", neighbor)
    assert not deleted_all, "Moving one podcast rebuilt the entire native tree"
    assert tree.GetSelection() == before[("show", neighbor)]
    assert tree.HasFocus()


def test_large_library_first_tree_batch_waits_for_its_own_ui_turn(native_tree) -> None:
    library = PodcastLibrary(
        shows=[
            PodcastShow(
                id="show",
                title="Show",
                episodes=[PodcastEpisode(guid="one", title="One", audio_url="u")],
            )
        ],
        extra_settings={"library_counts": "both", "library_layout": "podcasts_only"},
    )
    original_settings = library.extra_settings
    tree, host = native_tree(library)
    callbacks = []
    host._wx = SimpleNamespace(CallLater=lambda _delay, callback: callbacks.append(callback))
    host._podcast_library_is_large = lambda: True
    reload_tree(host)
    assert len(callbacks) == 1
    assert not host._cast_tree_items
    first, _cookie = tree.GetFirstChild(tree.GetRootItem())
    assert not first.IsOk()
    while callbacks:
        callbacks.pop(0)()
    assert host._cast_tree_chunks is None
    assert row_key(host, tree.GetSelection()) == ("show", "show")
    assert tree.GetItemText(tree.GetSelection()) == "Show"
    assert library.extra_settings is original_settings
    assert library.extra_settings == {
        "library_counts": "both",
        "library_layout": "podcasts_only",
    }


def test_first_episode_adds_expander_without_rebuilding_or_moving_focus(native_tree) -> None:
    library = PodcastLibrary(shows=[PodcastShow(id="new", title="New show")])
    tree, host = native_tree(library)
    _reload_native_tree(host)
    selected = host._cast_tree_items[("show", "new")]
    tree.SelectItem(selected)
    library.shows[0].episodes.append(
        PodcastEpisode(guid="one", title="First episode", audio_url="https://example.test/1")
    )
    _reload_native_tree(host)
    assert tree.GetSelection() == selected
    assert host._cast_tree_items[("show", "new")] == selected
    child, _cookie = tree.GetFirstChild(selected)
    assert tree.GetItemData(child) == ("placeholder", "new")


def test_refreshed_expanded_show_keeps_episode_focus_and_updates_children(native_tree) -> None:
    show = PodcastShow(
        id="show",
        title="Show",
        episodes=[
            PodcastEpisode(
                guid="one", title="Older", audio_url="u", published="Thu, 01 Oct 2026 00:00:00 GMT"
            )
        ],
    )
    library = PodcastLibrary(shows=[show])
    tree, host = native_tree(library)
    _reload_native_tree(host)
    item = host._cast_tree_items[("show", "show")]
    tree.Expand(item)
    older = host._cast_tree_episode_items[("episode", "show\x00one")]
    tree.SelectItem(older)
    changes = []

    def selected(event):
        changes.append(row_key(host, event.GetItem()))
        event.Skip()

    tree.Bind(wx.EVT_TREE_SEL_CHANGED, selected)
    show.episodes[0].title = "Updated older title"
    show.episodes.append(
        PodcastEpisode(
            guid="two", title="Newer", audio_url="u", published="Fri, 02 Oct 2026 00:00:00 GMT"
        )
    )
    _reload_native_tree(host)
    assert tree.GetSelection() == older
    assert tree.GetItemText(older) == "Updated older title"
    assert tree.IsExpanded(item)
    assert not changes
    first, cookie = tree.GetFirstChild(item)
    second, _cookie = tree.GetNextChild(item, cookie)
    assert [tree.GetItemData(row)[1] for row in (first, second)] == ["show\x00two", "show\x00one"]


def test_structural_refresh_restores_an_expanded_episode(native_tree) -> None:
    library = PodcastLibrary(
        shows=[
            PodcastShow(
                id="show",
                title="Show",
                episodes=[PodcastEpisode(guid="one", title="Episode", audio_url="u")],
            ),
        ]
    )
    tree, host = native_tree(library)
    _reload_native_tree(host)
    tree.Expand(host._cast_tree_items[("show", "show")])
    tree.SelectItem(host._cast_tree_episode_items[("episode", "show\x00one")])
    library.folders.append(PodcastFolder(id="folder", name="New folder"))
    _reload_native_tree(host)
    assert row_key(host, tree.GetSelection()) == ("episode", "show\x00one")
    assert tree.IsExpanded(host._cast_tree_items[("show", "show")])


def test_refresh_preserves_the_selected_folder_copy(native_tree) -> None:
    show = PodcastShow(
        id="show",
        title="Show",
        folder_id="first",
        episodes=[
            PodcastEpisode(
                guid="one", title="Older", audio_url="u", published="Thu, 01 Oct 2026 00:00:00 GMT"
            )
        ],
    )
    library = PodcastLibrary(
        shows=[show],
        folders=[
            PodcastFolder(id="first", name="First"),
            PodcastFolder(id="second", name="Second"),
        ],
    )
    folder_membership.copy_to(library, show, "second")
    tree, host = native_tree(library)
    _reload_native_tree(host)
    for folder in ("first", "second"):
        tree.Expand(host._cast_tree_items[("show", "show", folder)])
    key = ("episode", "show\x00one", "second")
    selected = host._cast_tree_episode_items[key]
    tree.SelectItem(selected)
    show.episodes.append(
        PodcastEpisode(
            guid="two", title="Newer", audio_url="u", published="Fri, 02 Oct 2026 00:00:00 GMT"
        )
    )
    _reload_native_tree(host)
    assert tree.GetSelection() == selected
    assert row_key(host, selected) == key
    assert host._cast_tree_episode_items[("episode", "show\x00one", "first")] != selected


def test_copy_then_merge_preserves_existing_expanded_rows_and_indexes(native_tree) -> None:
    show = PodcastShow(
        id="show",
        title="Show",
        folder_id="first",
        episodes=[PodcastEpisode(guid="one", title="Episode", audio_url="u")],
    )
    library = PodcastLibrary(
        shows=[show],
        folders=[
            PodcastFolder(id="first", name="First"),
            PodcastFolder(id="second", name="Second"),
        ],
    )
    tree, host = native_tree(library)
    _reload_native_tree(host)
    original = host._cast_tree_items[("show", "show")]
    tree.Expand(original)
    episode = host._cast_tree_episode_items[("episode", "show\x00one")]
    tree.SelectItem(episode)
    folder_membership.copy_to(library, show, "second")
    _reload_native_tree(host)
    assert tree.GetSelection() == episode
    assert host._cast_tree_episode_items == {("episode", "show\x00one", "first"): episode}
    assert host._cast_tree_items[("show", "show", "first")] == original
    folder_membership.move_to(library, show, "first", source="second")
    _reload_native_tree(host)
    assert tree.GetSelection() == episode
    assert host._cast_tree_episode_items == {("episode", "show\x00one"): episode}
    assert host._cast_tree_items[("show", "show")] == original
    assert ("show", "show", "second") not in host._cast_tree_items


def test_refresh_drops_capped_episode_keys_and_keeps_a_valid_selection(native_tree) -> None:
    show = PodcastShow(
        id="show",
        title="Show",
        episodes=[
            PodcastEpisode(
                guid="one", title="Older", audio_url="u", published="Thu, 01 Oct 2026 00:00:00 GMT"
            )
        ],
    )
    tree, host = native_tree(PodcastLibrary(shows=[show]))
    _reload_native_tree(host)
    item = host._cast_tree_items[("show", "show")]
    tree.Expand(item)
    tree.SelectItem(host._cast_tree_episode_items[("episode", "show\x00one")])
    host._EPISODES_PER_SHOW_NODE = 1
    show.episodes.append(
        PodcastEpisode(
            guid="two", title="Newer", audio_url="u", published="Fri, 02 Oct 2026 00:00:00 GMT"
        )
    )
    _reload_native_tree(host)
    assert tree.GetSelection() == item
    assert ("episode", "show\x00one") not in host._cast_tree_episode_items
    first, cookie = tree.GetFirstChild(item)
    more, _cookie = tree.GetNextChild(item, cookie)
    assert tree.GetItemData(first) == ("episode", "show\x00two")
    assert tree.GetItemData(more) == ("more", "show")
    assert tree.GetItemText(more).startswith("1 older episode(s)")
    assert len(show.episodes) == 2


def test_changed_publication_order_keeps_unique_rows_and_valid_episode_keys(native_tree) -> None:
    show = PodcastShow(
        id="show",
        title="Show",
        episodes=[
            PodcastEpisode(
                guid="one",
                title="Older",
                audio_url="u",
                published="Thu, 01 Oct 2026 00:00:00 GMT",
            ),
            PodcastEpisode(
                guid="two",
                title="Newer",
                audio_url="u",
                published="Fri, 02 Oct 2026 00:00:00 GMT",
            ),
        ],
    )
    tree, host = native_tree(PodcastLibrary(shows=[show]))
    _reload_native_tree(host)
    item = host._cast_tree_items[("show", "show")]
    tree.Expand(item)
    unchanged = host._cast_tree_episode_items[("episode", "show\x00two")]
    tree.SelectItem(host._cast_tree_episode_items[("episode", "show\x00one")])
    show.episodes[0].published = "Sat, 03 Oct 2026 00:00:00 GMT"
    _reload_native_tree(host)
    assert row_key(host, tree.GetSelection()) == ("episode", "show\x00one")
    assert tree.GetChildrenCount(item, recursively=False) == 2
    first, cookie = tree.GetFirstChild(item)
    second, _cookie = tree.GetNextChild(item, cookie)
    assert row_key(host, first) == ("episode", "show\x00one")
    assert second == unchanged
    assert host._cast_tree_episode_items[("episode", "show\x00one")] == first
    assert len(host._cast_tree_episode_items) == 2


def test_arrow_movement_during_yielding_redraw_wins_over_saved_selection(
    native_tree, monkeypatch
) -> None:
    library = PodcastLibrary(
        shows=[
            PodcastShow(id="first", title="First"),
            PodcastShow(id="second", title="Second"),
        ]
    )
    tree, host = native_tree(library)
    _reload_native_tree(host)
    tree.SelectItem(host._cast_tree_items[("show", "second")])
    library.shows.append(PodcastShow(id="third", title="Third"))
    monkeypatch.setattr("quill.ui.podcasts.library_tree_updates.TURN_BUDGET_SECONDS", 0)
    reload_tree(host)
    assert host._cast_tree_chunks is not None
    tree.SelectItem(host._cast_tree_items[("show", "first")])
    _wait_for_tree(host)
    assert row_key(host, tree.GetSelection()) == ("show", "first")
