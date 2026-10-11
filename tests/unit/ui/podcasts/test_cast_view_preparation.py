from __future__ import annotations

import gc
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from quill.core.podcasts import places
from quill.core.podcasts.filter_conditions import FIELD_PEOPLE, OP_CONTAINS, FilterCondition
from quill.core.podcasts.filtering import EPISODE_FILTER_MODES
from quill.core.podcasts.models import (
    Playlist,
    PlaylistRules,
    PodcastEpisode,
    PodcastFolder,
    PodcastShow,
    QueueItem,
)
from quill.core.podcasts.models_filters import (
    SCOPE_INBOX,
    SCOPE_LIBRARY,
    SCOPE_PLAYLISTS,
    SCOPE_VIEWS,
    EpisodeFilterConfiguration,
    EpisodeFilterRule,
)
from quill.core.podcasts.namespace_tags import Person
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.view_preparation import CastViewPreparationMixin, prepare_view
from quill.ui.podcasts.view_snapshot import (
    RECORDS_PER_CHUNK,
    WORKER_PAUSE_SECONDS,
    ViewCaptureJob,
    discard_view_snapshot,
    prepare_worker_snapshot,
    resolve_view_pairs,
    view_snapshot_chunks,
)


def finish(chunks):
    while True:
        try:
            next(chunks)
        except StopIteration as result:
            return result.value


@pytest.fixture
def library():
    library = PodcastLibrary(folders=[PodcastFolder(id="folder", name="News")])
    for show_id, title in (("a", "Same title"), ("b", "same TITLE")):
        show = PodcastShow(
            id=show_id,
            title=title,
            folder_id="folder" if show_id == "a" else None,
            is_favorite=show_id == "a",
            is_local=show_id == "b",
            route_to_inbox=True,
        )
        for number in range(6):
            episode = PodcastEpisode(
                guid=str(number),
                title=f"Episode {number % 3}",
                audio_url=f"https://example.invalid/{show_id}/{number}.mp3",
                published=f"Wed, {number + 1:02d} Jul 2026 06:00:00 GMT",
                duration_seconds=300 + number * 60,
                description="Guest show notes",
                downloaded_path=f"download-{number}" if number in (0, 2) else "",
                played=number == 3,
                position_ms=20_000 if number == 1 else 0,
                season=1,
                episode_number=number,
                episode_type="trailer" if number == 2 else "full",
            )
            episode.tags.people.append(Person("Alice" if number in (0, 2) else "Bob"))
            show.episodes.append(episode)
        library.shows.append(show)
    library.show_labels["a"] = ["News"]
    library.queue = [
        QueueItem(show_id="b", episode_guid="2"),
        QueueItem(show_id="a", episode_guid="0"),
        QueueItem(show_id="missing", episode_guid="0"),
    ]
    library.playlists = [
        Playlist(id="manual", name="Manual", items=list(library.queue)),
        Playlist(
            id="smart",
            name="Smart",
            kind="smart",
            rules=PlaylistRules(text_contains="Guest", labels=["news"]),
        ),
    ]
    library.episode_filters["a"] = EpisodeFilterConfiguration(
        enabled=True,
        scopes={SCOPE_LIBRARY, SCOPE_INBOX, SCOPE_VIEWS, SCOPE_PLAYLISTS},
        rules=[
            EpisodeFilterRule(
                conditions=[FilterCondition(field=FIELD_PEOPLE, op=OP_CONTAINS, value="Alice")]
            )
        ],
    )
    library.episode_filter_exceptions["a"] = ["0"]
    return library


def test_view_capture_detaches_scalars_metadata_and_people_without_cloning_episodes(
    library, monkeypatch
):
    def forbidden_copy(_episode, _memo):
        pytest.fail("View preparation copied an episode model")

    monkeypatch.setattr(PodcastEpisode, "__deepcopy__", forbidden_copy, raising=False)
    captured = finish(view_snapshot_chunks(library))
    episode = captured.shows[0].episodes[2]
    library.shows[0].title = "Changed"
    library.shows[0].episodes[2].played = True
    library.shows[0].episodes[2].tags.people.clear()
    library.settings.episode_sort_mode = "title_za"
    library.episode_filter_exceptions["a"].clear()
    assert captured.shows[0].title == "Same title"
    assert not episode.played
    assert [person.name for person in episode.tags.people] == ["Alice"]
    assert captured.settings.episode_sort_mode != "title_za"
    assert captured.episode_filter_exceptions["a"] == ["0"]
    assert captured.metadata.shows == []
    assert captured.find_show("a") is captured.shows[0]
    assert captured.shows[0].find_episode("2") == episode
    gc.collect()
    assert all(
        type(row) is tuple and not gc.is_tracked(row) for row in captured.shows[0].episodes.rows
    )


def test_discard_splits_a_single_large_show_into_bounded_releases(library):
    captured = finish(view_snapshot_chunks(library))
    batches = []

    class Rows(list):
        def __delitem__(self, key):
            batches.append(len(self[key]))
            super().__delitem__(key)

    rows = Rows([captured.shows[0].episodes.rows[0]] * (RECORDS_PER_CHUNK * 5 + 7))
    captured.shows[0].episodes.rows = rows
    discard_view_snapshot(captured)
    assert len(batches) == 6
    assert max(batches) == RECORDS_PER_CHUNK
    assert rows == []
    assert captured.shows == []
    assert captured.find_show("a") is None


def test_worker_scan_and_cleanup_yield_after_their_shared_cpu_budget(library, monkeypatch):
    from quill.ui.podcasts import view_snapshot

    captured = finish(view_snapshot_chunks(library))
    ticks = iter(range(1000))
    pauses = []
    monkeypatch.setattr(view_snapshot, "perf_counter", lambda: next(ticks))
    monkeypatch.setattr(view_snapshot, "sleep", pauses.append)
    prepare_worker_snapshot(captured)
    list(captured.shows[0].episodes)
    assert pauses == [WORKER_PAUSE_SECONDS]
    list(captured.shows[1].episodes)
    assert pauses == [WORKER_PAUSE_SECONDS] * 2
    discard_view_snapshot(captured)
    assert pauses == [WORKER_PAUSE_SECONDS] * 6


def test_worker_cleanup_retires_each_show_instead_of_bulk_metadata_clear(library):
    captured = finish(view_snapshot_chunks(library))
    pops = []

    class Shows(list):
        def pop(self):
            pops.append(len(self))
            return super().pop()

        def clear(self):
            pytest.fail("Show metadata must be retired between worker turns")

    class Index(dict):
        def clear(self):
            pytest.fail("Do not release all indexed shows in one worker turn")

    captured.shows = Shows(captured.shows)
    captured._shows = Index(captured._shows)
    discard_view_snapshot(captured)
    assert pops == [2, 1]
    assert captured.shows == []
    assert captured._shows == {}


def test_worker_scan_cancellation_does_not_interrupt_input_cleanup(library):
    from quill.stability.task_manager import CancellationToken, CancelledError

    captured = finish(view_snapshot_chunks(library))
    token = CancellationToken()
    prepare_worker_snapshot(captured, token)
    token.cancel()
    with pytest.raises(CancelledError):
        list(captured.shows[0].episodes)
    discard_view_snapshot(captured)
    assert captured.shows == []


@pytest.mark.parametrize("place", [place.id for place in places.PLACES])
@pytest.mark.parametrize("mode", ["all", "unplayed", "in_progress", "downloaded"])
def test_projected_views_keep_domain_counts_filters_order_and_folder_headers(
    library, tmp_path, place, mode
):
    captured = finish(view_snapshot_chunks(library))
    options = dict(episode_filter=mode, notifications_path=tmp_path / "notices.json", limit=3)
    assert prepare_view(captured, place, **options) == prepare_view(library, place, **options)


@pytest.mark.parametrize(
    "context",
    [
        {"show_id": "a"},
        {"playlist_id": "manual"},
        {"playlist_id": "smart"},
        {"inbox_folder": "folder"},
    ],
)
@pytest.mark.parametrize("mode", EPISODE_FILTER_MODES)
def test_projected_opened_show_playlist_and_inbox_folder_keep_policy(
    library, tmp_path, context, mode
):
    captured = finish(view_snapshot_chunks(library))
    options = dict(episode_filter=mode, notifications_path=tmp_path / "notices.json", **context)
    assert prepare_view(captured, "inbox", **options) == prepare_view(library, "inbox", **options)


@pytest.mark.parametrize("layout", ["episodes", "folders_first", "folders_only"])
@pytest.mark.parametrize("limit", [0, 1, 1000])
def test_streamed_inbox_layout_matches_its_existing_rows(library, tmp_path, layout, limit):
    from quill.core.podcasts.library_view import inbox_rows, set_setting
    from quill.core.podcasts.sorting import sort_pairs
    from quill.core.podcasts.virtual_views import virtual_view_pairs

    set_setting(library, "inbox_layout", layout)
    rows = inbox_rows(library, virtual_view_pairs(library, "inbox"))
    expected_pairs = sort_pairs(
        library,
        [row.pair for row in rows if row.pair is not None],
        view_mode=library.settings.episode_list_view_mode,
        limit=limit,
    )
    prepared = prepare_view(
        finish(view_snapshot_chunks(library)),
        "inbox",
        episode_filter="all",
        notifications_path=tmp_path / "notices.json",
        limit=limit,
    )
    assert prepared.lead_rows == [
        (row.kind, row.folder_id, row.label) for row in rows if row.kind == "inbox_folder"
    ]
    assert prepared.pairs == [(show.id, episode.guid) for show, episode in expected_pairs]


def test_live_resolution_uses_offsets_without_scanning_episode_catalogues(library, tmp_path):
    prepared = prepare_view(
        finish(view_snapshot_chunks(library)),
        "downloads",
        episode_filter="all",
        notifications_path=tmp_path / "notices.json",
    )

    class IndexOnly:
        def __init__(self, episodes):
            self.episodes = episodes

        def __len__(self):
            return len(self.episodes)

        def __getitem__(self, index):
            return self.episodes[index]

        def __iter__(self):
            pytest.fail("Publishing a view scanned a whole episode catalogue")

    for show in library.shows:
        show.episodes = IndexOnly(show.episodes)
    resolved = finish(resolve_view_pairs(library, prepared.pairs, prepared.offsets))
    assert [(show.id, episode.guid) for show, episode in resolved] == prepared.pairs
    assert all(
        episode is show.episodes[offset]
        for (show, episode), offset in zip(resolved, prepared.offsets, strict=True)
    )


@pytest.mark.parametrize("change", ["move", "remove", "rename"])
def test_live_resolution_rejects_stale_rows_without_partial_publication(library, tmp_path, change):
    prepared = prepare_view(
        finish(view_snapshot_chunks(library)),
        "downloads",
        episode_filter="all",
        notifications_path=tmp_path / "notices.json",
    )
    show = library.find_show(prepared.pairs[0][0])
    if change == "move":
        show.episodes.reverse()
    elif change == "remove":
        show.episodes.clear()
    else:
        show.episodes[prepared.offsets[0]].guid = "changed"
    assert finish(resolve_view_pairs(library, prepared.pairs, prepared.offsets)) is None


class Scheduler:
    def __init__(self):
        self.pending = deque()

    def CallLater(self, _delay, callback):
        timer = SimpleNamespace(stopped=False)
        timer.Stop = lambda: setattr(timer, "stopped", True)
        self.pending.append((timer, callback))
        return timer

    def drain(self):
        while self.pending:
            self.tick()

    def tick(self):
        timer, callback = self.pending.popleft()
        if not timer.stopped:
            callback()


class Manager:
    def __init__(self):
        self.pending = deque()
        self.cancelled = []

    def submit(self, _name, work, **callbacks):
        task = SimpleNamespace(operation_id=str(len(self.pending)))
        self.pending.append((task, work, callbacks))
        return task

    def cancel(self, operation_id):
        self.cancelled.append(operation_id)


class Host(CastViewPreparationMixin):
    def __init__(self, library):
        self._podcast_library = library
        self._podcast_library_revision = 0
        self._cast_closed = self._cast_closing = False
        self._wx = Scheduler()
        self._task_manager = Manager()
        self.frame = SimpleNamespace(IsBeingDeleted=lambda: False)
        self._current_place = "downloads"
        self._episode_show_filter = lambda: "all"
        self._selected_tree_data = lambda: ("episode", "a\x002")
        self._refresh_window_title = lambda: None
        self._refresh_place_counts = lambda: None
        self._place_count_chunks = lambda: iter(())
        self._say_empty_place_once = lambda _place: None
        self._content_is_list = lambda: False
        self._place_heading = lambda place: place
        self._content = SimpleNamespace(set_heading=lambda _heading: None)
        self._refresh_selection_buttons = lambda: None
        self._refresh_notes_pane = lambda: None
        self._set_status = self.status.append
        self._announce = self.said.append
        self.applied = []
        self.retired = []

    @property
    def status(self):
        return self.__dict__.setdefault("_status", [])

    @property
    def said(self):
        return self.__dict__.setdefault("_said", [])

    def _fill_episodes_from_pairs(self, pairs, **_kwargs):
        self.applied.append(pairs)

    def _episode_pair_row_chunks(self, pairs, **kwargs):
        self._fill_episodes_from_pairs(pairs, **kwargs)
        yield

    def _retire_cast_view_snapshot(self, snapshot):
        self.retired.append(snapshot)

    def _selection_button_chunks(self):
        self._refresh_selection_buttons()
        yield

    def capture(self):
        self._request_cast_view_preparation("downloads")
        self._wx.drain()
        return self._task_manager.pending.popleft()


def test_startup_prepared_view_opens_lists_without_preparing_library_again(library, tmp_path):
    host = Host(library)
    prepared = prepare_view(
        library,
        "downloads",
        episode_filter="all",
        notifications_path=tmp_path / "notices.json",
    )

    host._apply_cast_prepared_view(prepared, ("downloads", "", "", ""), None)
    host._wx.drain()

    assert [episode.guid for _show, episode in host.applied[0]] == [
        guid for _show_id, guid in prepared.pairs
    ]
    assert not host._task_manager.pending
    assert host._cast_view_snapshot is None


@pytest.mark.parametrize("checking", [False, True])
def test_counts_publication_defers_the_tree_until_refresh_all_finishes(
    library, tmp_path, monkeypatch, checking
):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    host = Host(library)
    host._current_place = "podcasts"
    host._check_run = object() if checking else None
    updates = []
    host._reload_library_tree = lambda: updates.append("tree")
    host._request_cast_view_preparation("podcasts", counts_only=True)
    host._wx.drain()
    _task, work, callbacks = host._task_manager.pending.popleft()
    callbacks["on_success"]("test", work())
    host._wx.drain()
    assert updates == ([] if checking else ["tree"])
    assert bool(getattr(host, "_tree_reload_pending", False)) == checking
    assert host._cast_place_counts
    assert host._cast_counts_revision == host._podcast_library_revision


def test_place_initialization_precedes_capture_and_restarts_on_a_revision_change(
    library, monkeypatch
):
    from quill.ui.podcasts import storage_snapshot

    monkeypatch.setattr(storage_snapshot, "ITEMS_PER_TURN", 1)
    host = Host(library)
    calls = []

    def initialize():
        try:
            calls.append("page")
            yield
            calls.append("heading")
            yield
        finally:
            calls.append("closed")

    host._request_cast_view_preparation("downloads", initialize=initialize)
    assert calls == []
    host._wx.tick()
    assert calls == ["page"]
    assert host._cast_view_snapshot._retained is None
    host._podcast_library_revision += 1
    host._wx.drain()
    assert calls == ["page", "closed", "page", "heading", "closed"]
    assert len(host._task_manager.pending) == 1


def test_cancelled_place_initialization_never_starts_capture(library, monkeypatch):
    from quill.ui.podcasts import storage_snapshot

    monkeypatch.setattr(storage_snapshot, "ITEMS_PER_TURN", 1)
    host = Host(library)
    calls = []

    def initialize():
        try:
            calls.append("page")
            yield
            pytest.fail("Cancelled initialization resumed")
        finally:
            calls.append("closed")

    host._request_cast_view_preparation("downloads", initialize=initialize)
    host._wx.tick()
    host._cancel_cast_view_preparation()
    host._wx.drain()
    assert calls == ["page", "closed"]
    assert host._task_manager.pending == deque()
    assert host.retired == []


def test_cancelled_capture_hands_off_partial_input_once_without_releasing_it_on_ui(
    library, monkeypatch
):
    from quill.ui.podcasts import storage_snapshot

    monkeypatch.setattr(storage_snapshot, "ITEMS_PER_TURN", 1)
    scheduler = Scheduler()
    retired = []
    job = ViewCaptureJob(
        library,
        scheduler,
        completed=lambda _result: pytest.fail("Cancelled capture was published"),
        retire=retired.append,
        failed=lambda _error: pytest.fail("Cancellation is not a capture failure"),
        alive=lambda: True,
    )
    job.start()
    while (
        job._retained is None or not job._retained.shows or not job._retained.shows[0].episodes.rows
    ):
        scheduler.tick()
    captured = job._retained
    rows = list(captured.shows[0].episodes.rows)
    job.cancel()
    job.cancel()
    scheduler.drain()
    assert retired == [captured]
    assert captured.shows[0].episodes.rows == rows
    assert job._chunks.gi_frame is None


def test_partial_input_retirement_uses_a_noncancelable_worker(library, monkeypatch):
    from quill.ui.podcasts import view_preparation

    host = Host(library)
    captured = finish(view_snapshot_chunks(library))
    started = threading.Event()
    release = threading.Event()
    workers = []
    native_discard = view_preparation.discard_view_snapshot

    def discard(snapshot):
        workers.append(threading.get_ident())
        started.set()
        assert release.wait(timeout=3)
        native_discard(snapshot)

    monkeypatch.setattr(view_preparation, "discard_view_snapshot", discard)
    CastViewPreparationMixin._retire_cast_view_snapshot(host, captured)
    pool = host._cast_view_retirement_pool
    try:
        assert started.wait(timeout=3)
        task = pool.snapshot()[0]
        assert not task.safe_to_cancel
        assert len(workers) == 1
        assert workers[0] != threading.get_ident()
        release.set()
        task.future.result(timeout=3)
        assert captured.shows == []
        assert captured._shows == {}
        assert len(library.shows[0].episodes) == 6
    finally:
        release.set()
        pool.shutdown(wait=True, cancel_pending=False)


@pytest.mark.parametrize("fail", [False, True])
def test_worker_releases_its_large_input_before_delivering_success_or_failure(
    library, monkeypatch, fail
):
    from quill.ui.podcasts import view_preparation

    host = Host(library)
    _task, work, _callbacks = host.capture()
    captured = []
    worker = []
    ui_thread = threading.get_ident()
    original = view_preparation.prepare_view

    def prepare(snapshot, *args, **kwargs):
        captured.append(snapshot)
        worker.append(threading.get_ident())
        if fail:
            raise ValueError("synthetic worker failure")
        return original(snapshot, *args, **kwargs)

    monkeypatch.setattr(view_preparation, "prepare_view", prepare)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(work)
        if fail:
            with pytest.raises(ValueError, match="synthetic worker failure"):
                future.result()
        else:
            assert future.result().pairs
    assert worker[0] != ui_thread
    assert captured[0].shows == []
    assert captured[0].find_show("a") is None


def test_superseded_capture_and_worker_delivery_never_publish(library):
    host = Host(library)
    host._request_cast_view_preparation("downloads")
    generation = host._cast_view_generation
    host._podcast_library_revision += 1
    host._wx.drain()
    assert host._cast_view_generation > generation
    _task, work, callbacks = host._task_manager.pending.popleft()
    result = work()
    host._podcast_library_revision += 1
    callbacks["on_success"]("test", result)
    assert host.applied == []
    host._wx.drain()
    _task, work, callbacks = host._task_manager.pending.popleft()
    callbacks["on_success"]("test", work())
    host._wx.drain()
    assert len(host.applied) == 1
    assert all(episode is show.find_episode(episode.guid) for show, episode in host.applied[0])


@pytest.mark.parametrize("stage", ["capture", "publication"])
def test_view_work_waits_for_a_yielding_feed_commit_then_rechecks_its_generation(library, stage):
    host = Host(library)
    if stage == "capture":
        host._podcast_commit_depth = 1
        host._request_cast_view_preparation("downloads")
    else:
        _task, work, callbacks = host.capture()
        result = work()
        host._podcast_commit_depth = 1
        callbacks["on_success"]("test", result)
    _timer, advance = host._wx.pending.popleft()
    advance()
    assert host._task_manager.pending == deque()
    assert host.applied == []
    assert not hasattr(host, "_cast_place_counts")
    host._podcast_commit_depth = 0
    host._podcast_library_revision += 1
    host._wx.drain()
    _task, work, callbacks = host._task_manager.pending.popleft()
    callbacks["on_success"]("test", work())
    host._wx.drain()
    assert len(host.applied) == 1


def test_unreported_row_movement_retries_instead_of_publishing_the_wrong_episode(library):
    host = Host(library)
    _task, work, callbacks = host.capture()
    result = work()
    callbacks["on_success"]("test", result)
    library.shows[0].episodes.reverse()
    host._wx.drain()
    assert host.applied == []
    _task, work, callbacks = host._task_manager.pending.popleft()
    callbacks["on_success"]("test", work())
    host._wx.drain()
    assert len(host.applied) == 1
    assert [(show.id, episode.guid) for show, episode in host.applied[0]] == result.pairs


def test_cursor_movement_during_publication_is_not_replaced_by_the_old_selection(
    library, monkeypatch
):
    from quill.ui.podcasts import storage_snapshot

    monkeypatch.setattr(storage_snapshot, "ITEMS_PER_TURN", 1)
    host = Host(library)
    restored = []
    host._cast_cursor_revision = 0
    host._content_is_list = lambda: True
    host._select_list_key = lambda key: restored.append(key) or True
    _task, work, callbacks = host.capture()
    callbacks["on_success"]("test", work())
    while not host.applied:
        host._wx.tick()
    host._cast_cursor_revision += 1
    host._wx.drain()
    assert restored == []
    assert not host._cast_list_mutating
    assert host._cast_view_snapshot is None


def test_cancelling_publication_cannot_leave_selection_events_suppressed(library, monkeypatch):
    from quill.ui.podcasts import storage_snapshot

    monkeypatch.setattr(storage_snapshot, "ITEMS_PER_TURN", 1)
    host = Host(library)
    _task, work, callbacks = host.capture()
    callbacks["on_success"]("test", work())
    while not host.applied:
        host._wx.tick()
    host._cancel_cast_view_preparation()
    host._wx.drain()
    assert not host._cast_list_mutating
    assert host._cast_view_snapshot is None


@pytest.mark.parametrize("cursor_moved", [False, True])
def test_retry_between_native_row_updates_keeps_only_an_unmoved_cursor(
    library, monkeypatch, cursor_moved
):
    from quill.ui.podcasts import storage_snapshot

    monkeypatch.setattr(storage_snapshot, "ITEMS_PER_TURN", 1)
    host = Host(library)
    original = host._selected_tree_data()
    host._cast_cursor_revision = 0

    def clear_rows(pairs, **_kwargs):
        host._selected_tree_data = lambda: None
        host.applied.append(pairs)
        yield

    host._episode_pair_row_chunks = clear_rows
    _task, work, callbacks = host.capture()
    callbacks["on_success"]("test", work())
    while not host.applied:
        host._wx.tick()
    host._podcast_library_revision += 1
    if cursor_moved:
        host._cast_cursor_revision += 1
    retries = []
    host._request_cast_view_preparation = lambda _place, **kwargs: retries.append(kwargs["keep"])
    host._wx.drain()
    assert retries == [None if cursor_moved else original]
    assert not host._cast_list_mutating


def test_places_publication_yields_between_labels_and_stops_when_superseded(library, monkeypatch):
    from quill.ui.podcasts import storage_snapshot
    from quill.ui.podcasts.places_host import CastPlacesHostMixin

    monkeypatch.setattr(storage_snapshot, "ITEMS_PER_TURN", 1)
    host = Host(library)
    relabelled = []
    host._place_count_chunks = lambda: CastPlacesHostMixin._place_count_chunks(host)
    host._places = SimpleNamespace(relabel=lambda place, label: relabelled.append((place, label)))
    host._visible_places = lambda: places.PLACES
    host._place_label = lambda place: place
    host._podcast_library_is_large = lambda: True
    _task, work, callbacks = host.capture()
    callbacks["on_success"]("test", work())
    while not relabelled:
        host._wx.tick()
    assert relabelled == [(places.PLACES[0].id, places.PLACES[0].id)]
    host._cancel_cast_view_preparation()
    host._wx.drain()
    assert len(relabelled) == 1


@pytest.mark.parametrize("stage", ["capture", "worker", "publication"])
def test_closing_suppresses_each_view_preparation_stage(library, stage):
    host = Host(library)
    if stage == "capture":
        host._request_cast_view_preparation("downloads")
    else:
        _task, work, callbacks = host.capture()
        result = work()
        if stage == "publication":
            callbacks["on_success"]("test", result)
    host._cast_closing = True
    if stage == "worker":
        callbacks["on_success"]("test", result)
    host._wx.drain()
    assert host.applied == []
    assert host.said == []


def test_view_failure_reports_an_outcome_instead_of_empty_success(library):
    host = Host(library)
    _task, _work, callbacks = host.capture()
    callbacks["on_failure"]("test", ValueError("synthetic preparation error"))
    assert host.applied == []
    assert host.status == ["Could not prepare this view. Try opening it again."]
    assert "synthetic preparation error" in host.said[0]
