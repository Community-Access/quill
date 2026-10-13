"""The one window, driven as a listener drives it (qc.md Phase 2).

A real ``PodcastsAppFrame`` over an isolated data folder with a small library,
so every place can be shown, every selection helper read, Find flattened and
restored, the Preferences window and the Places chooser built. Marked
``machine_global`` because the frame registers global hotkeys and touches the
clipboard-adjacent speech bridges; one worker at a time.
"""

from __future__ import annotations

import gc
import os
import threading
from pathlib import Path
from time import monotonic, perf_counter, sleep, thread_time
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

#: Serialized onto one worker: building the real frame registers system-wide
#: hotkeys and starts the screen-reader bridges, which race between workers.
pytestmark = pytest.mark.machine_global

_UI_DIAGNOSTIC_SECONDS = 0.016
_UI_STALL_SECONDS = 0.100


def _rows(frame) -> list[str]:
    box = frame._places.box
    return [box.GetString(i) for i in range(box.GetCount())]


@pytest.fixture
def cast_frame(
    quill_data_dir: Path, monkeypatch: pytest.MonkeyPatch, wx_app, quiet_cast_startup, close_cast
):
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.models_episode import PodcastEpisode
    from quill.core.podcasts.subscriptions import PodcastLibrary, save_library

    library = PodcastLibrary()
    for index in range(1, 4):
        show = PodcastShow(
            id=f"s{index}", title=f"Show {index}", feed_url=f"http://x.invalid/{index}"
        )
        show.is_favorite = index == 1
        show.route_to_inbox = True
        for ep in range(1, 4):
            show.episodes.append(
                PodcastEpisode(
                    guid=f"s{index}e{ep}",
                    title=f"Episode {ep} of {index}",
                    audio_url=f"http://x.invalid/{index}/{ep}.mp3",
                    published=f"2026-09-{ep:02d}T06:00:00+00:00",
                    duration_seconds=600 * ep,
                    played=ep == 3,
                    position_ms=30_000 if ep == 2 else 0,
                )
            )
        library.add_show(show)
    save_library(quill_data_dir, library)
    previous_loop = wx.EventLoop.GetActive()
    loop = wx.GUIEventLoop()
    wx.EventLoop.SetActive(loop)
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    monkeypatch.setattr(PodcastsAppFrame, "_announce", lambda self, *a, **kw: None)
    frame = PodcastsAppFrame()
    try:
        yield frame
    finally:
        set_transition_announcement_policy(None)
        try:
            closed = close_cast(frame, loop=loop)
            assert closed, "Cast did not finish its responsive shutdown"
        finally:
            wx.EventLoop.SetActive(previous_loop)


def test_every_place_shows_names_itself_and_counts(cast_frame) -> None:
    from quill.core.podcasts import places as places_model

    frame = cast_frame
    for place in places_model.PLACES:
        assert frame.show_place(place.id, focus=False), place.id
        assert frame._current_place == place.id
        heading = frame._content.heading.GetLabel()
        assert heading.startswith(places_model.label(frame._podcast_library, place.id)), heading
    # the counts the rows carry
    assert "Inbox (6)" in [
        frame._places.box.GetString(i) for i in range(frame._places.box.GetCount())
    ]
    assert frame._content.showing == frame._content.TREE


def test_new_folder_and_mark_all_have_distinct_shortcuts_and_menu_handlers(
    cast_frame, monkeypatch
) -> None:
    frame = cast_frame
    bar = frame.frame.GetMenuBar()
    items = [
        item for index in range(bar.GetMenuCount()) for item in bar.GetMenu(index).GetMenuItems()
    ]
    folder = next(item for item in items if item.GetItemLabelText() == "New Folder...")
    played = next(item for item in items if item.GetItemLabelText() == "Mark All as Played...")
    assert folder.GetItemLabel().split("\t")[1] == "Ctrl+Shift+E"
    assert played.GetItemLabel().split("\t")[1] == "Alt+Shift+E"
    assert frame._binding_for("podcasts.mark_all_played") == "Alt+Shift+E"
    for command_id, binding in (
        ("podcasts.new_folder", "Ctrl+Shift+E"),
        ("podcasts.mark_all_played", "Alt+Shift+E"),
    ):
        command = frame.commands.get(command_id)
        assert command is not None
        assert command.keybinding == binding
    for item in (folder, played):
        assert wx.AcceleratorEntry().FromString(item.GetItemLabel())
    calls = []
    monkeypatch.setattr(frame, "_on_library_new_folder", lambda: calls.append("folder"))
    monkeypatch.setattr(frame, "podcast_mark_all_played", lambda: calls.append("played"))
    for item in (folder, played):
        frame.frame.ProcessWindowEvent(wx.CommandEvent(wx.EVT_MENU.typeId, item.GetId()))
    assert calls == ["folder", "played"]


def _pump_cast_until(predicate, timeout: float = 3) -> None:
    app = wx.GetApp()
    loop = wx.EventLoop.GetActive()
    deadline = monotonic() + timeout
    while not predicate() and monotonic() < deadline:
        for action in (app.ProcessPendingEvents, wx.YieldIfNeeded, loop.ProcessIdle):
            started = perf_counter()
            action()
            duration = perf_counter() - started
            if duration > 0.050 and os.environ.get("QUILL_PROFILE_CAST_PUMP") == "1":
                print(f"Slow Cast event pump {action.__name__}: {duration * 1000:.2f} ms")
        sleep(0.002)
    assert predicate()


def _run_cast_until(predicate, timeout: float = 3) -> None:
    """Use native dispatch, not Yield's draining of repeatedly scheduled timers."""
    app = wx.GetApp()
    deadline = monotonic() + timeout

    def check():
        if predicate() or monotonic() >= deadline:
            app.ExitMainLoop()

    timer = wx.PyTimer(check)
    timer.Start(10)
    try:
        app.MainLoop()
    finally:
        timer.Stop()
    assert predicate()


@pytest.mark.parametrize(("moved_id", "neighbor_id"), [("s2", "s3"), ("s3", "s2")])
def test_move_through_folder_picker_keeps_next_or_previous_native_row(
    cast_frame, monkeypatch, moved_id, neighbor_id
) -> None:
    from quill.core.podcasts.models import PodcastFolder
    from quill.ui.podcasts.folder_picker_dialog import FolderPickerDialog
    from quill.ui.podcasts.library_tree_updates import row_key

    frame = cast_frame
    frame._podcast_library.folders.append(PodcastFolder(id="destination", name="Destination"))
    frame.frame.Show()
    frame.show_place("podcasts")
    _run_cast_until(lambda: getattr(frame, "_cast_tree_chunks", None) is None)
    tree = frame._shows_tree
    rows = dict(frame._cast_tree_items)
    tree.SelectItem(rows[("show", moved_id)])
    tree.SetFocus()
    native_show = FolderPickerDialog.show

    def choose(picker):
        def accept():
            picker._rebuild_tree(select_folder_id="destination")
            picker._on_move(None)

        timer = wx.CallLater(50, accept)
        try:
            return native_show(picker)
        finally:
            timer.Stop()

    monkeypatch.setattr(FolderPickerDialog, "show", choose)
    monkeypatch.setattr(
        tree, "DeleteAllItems", lambda: pytest.fail("A folder move cleared the native library")
    )
    frame._on_library_move_to_folder()
    _run_cast_until(
        lambda: (
            getattr(frame, "_cast_tree_chunks", None) is None
            and not getattr(frame, "_cast_selection_refresh_pending", False)
        )
    )
    assert frame._podcast_library.find_show(moved_id).folder_id == "destination"
    assert row_key(frame, tree.GetSelection()) == ("show", neighbor_id)
    assert tree.GetSelection() == rows[("show", neighbor_id)]
    assert tree.HasFocus()


def test_prepared_episode_rows_separate_native_clear_count_and_repaint(cast_frame, monkeypatch):
    frame = cast_frame
    show = frame._podcast_library.shows[0]
    pairs = [(show, episode) for episode in show.episodes]
    frame._fill_episodes_from_pairs(pairs, prepared=True)
    frame._episodes.Select(0)
    for name in ("InsertItem", "DeleteItem"):
        monkeypatch.setattr(
            frame._episodes, name, lambda *_a, **_kw: pytest.fail("Use native virtual rows")
        )
    chunks = frame._cast_list_update_chunks(frame._episode_pair_row_chunks(pairs, prepared=True))
    next(chunks)
    assert frame._episodes.GetItemCount() == 0
    assert frame._episodes.GetFirstSelected() == -1
    assert not frame._cast_list_mutating
    next(chunks)
    assert frame._episodes.GetItemCount() == 0
    assert all(a is b for a, b in zip(frame._current_episodes, show.episodes, strict=True))
    next(chunks)
    assert frame._episodes.GetItemCount() == len(pairs)
    assert frame._episodes.GetItemText(0) == pairs[0][1].title
    next(chunks)
    with pytest.raises(StopIteration):
        next(chunks)
    assert not frame._cast_list_mutating


@pytest.mark.perf
@pytest.mark.timeout(180)
@pytest.mark.skipif(os.environ.get("RUN_PERF") != "1", reason="Opt-in native catalogue budget")
def test_large_downloads_place_uses_the_real_cast_route_with_bounded_ui_turns(
    cast_frame, quill_data_dir, monkeypatch
) -> None:
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.models_episode import PodcastEpisode
    from quill.core.podcasts.subscriptions import PodcastLibrary
    from quill.core.transport_button import object_label

    frame = cast_frame
    original_library = frame._podcast_library
    library = PodcastLibrary()
    for index in range(1300):
        episodes = [
            PodcastEpisode(
                guid=f"episode-{number}",
                title=f"Synthetic episode {number}",
                audio_url="https://example.invalid/synthetic.mp3",
                published="2026-10-07T06:00:00+00:00",
            )
            for number in range(150)
        ]
        episodes[0].downloaded_path = str(quill_data_dir / f"synthetic-{index}.mp3")
        episodes[0].played = index % 2 == 0
        library.shows.append(PodcastShow(id=str(index), title=f"Show {index}", episodes=episodes))
    frame._cancel_cast_view_preparation()
    frame._podcast_library = library
    frame._podcast_library_revision = int(getattr(frame, "_podcast_library_revision", 0)) + 1
    frame._cast_place_counts = {}
    phase = "showing-window"
    turns: dict[str, list[float]] = {}
    heartbeats: list[float] = []
    replies: list[tuple[str, float]] = []
    collections: list[tuple[int, float]] = []
    collection_started: dict[int, float] = {}
    method_times: list[tuple[str, str, float]] = []
    tree_times: list[tuple[str, str, float, float]] = []
    timers = []
    native_later, native_after = wx.CallLater, wx.CallAfter
    from quill.ui.podcasts import storage_snapshot
    from quill.ui.podcasts.storage_snapshot import TurnJob

    def measured_method(name, method):
        def invoke(*args, **kwargs):
            started = perf_counter()
            try:
                return method(*args, **kwargs)
            finally:
                method_times.append((phase, name, perf_counter() - started))

        return invoke

    for name in (
        "show_place",
        "_fill_place",
        "_request_cast_view_preparation",
        "_cancel_cast_view_preparation",
        "_say_empty_place_once",
        "_refresh_window_title",
        "_fill_episodes_from_pairs",
        "_select_list_key",
        "_select_list_row",
        "_place_heading",
        "_refresh_selection_buttons",
        "_reload_library_tree",
        "_visible_library_shows",
        "_refresh_transport_controls",
        "_refresh_cast_status_bar",
        "_refresh_notes_pane",
        "_refresh_place_counts",
        "_place_label",
        "_episode_row_values",
    ):
        monkeypatch.setattr(frame, name, measured_method(name, getattr(frame, name)))
    monkeypatch.setattr(TurnJob, "start", measured_method("TurnJob.start", TurnJob.start))
    for name in ("show", "focus", "set_heading"):
        monkeypatch.setattr(
            frame._content,
            name,
            measured_method(f"content.{name}", getattr(frame._content, name)),
        )
    for name in ("DeleteAllItems", "SetItemCount", "Refresh", "set_rows"):
        monkeypatch.setattr(
            frame._episodes,
            name,
            measured_method(f"episodes.{name}", getattr(frame._episodes, name)),
        )
    for name in (
        "Freeze",
        "Thaw",
        "DeleteAllItems",
        "AddRoot",
        "AppendItem",
        "SetItemData",
        "SetItemText",
        "DeleteChildren",
        "Delete",
        "PrependItem",
        "InsertItem",
        "SelectItem",
        "Expand",
    ):
        method = getattr(frame._shows_tree, name)

        def tree_method(*args, _method=method, _name=name, **kwargs):
            started, cpu_started = perf_counter(), thread_time()
            try:
                return _method(*args, **kwargs)
            finally:
                tree_times.append((
                    phase,
                    _name,
                    perf_counter() - started,
                    thread_time() - cpu_started,
                ))

        monkeypatch.setattr(frame._shows_tree, name, tree_method)
    native_capture = storage_snapshot.capture_chunks

    def measured_capture(*args, **kwargs):
        chunks = native_capture(*args, **kwargs)
        try:
            while True:
                line = chunks.gi_frame.f_lineno
                started = perf_counter()
                try:
                    next(chunks)
                except StopIteration as result:
                    return result.value
                finally:
                    duration = perf_counter() - started
                    if duration > 0.002:
                        method_times.append((phase, f"storage.capture_chunks:{line}", duration))
                yield
        finally:
            chunks.close()

    monkeypatch.setattr(storage_snapshot, "capture_chunks", measured_capture)

    def timed(callback, args, kwargs):
        def invoke():
            owner = getattr(callback, "__self__", None)
            chunks = getattr(owner, "_chunks", None)
            code = getattr(chunks, "gi_code", None)
            stage = chunks
            while getattr(stage, "gi_yieldfrom", None) is not None:
                stage = stage.gi_yieldfrom
            stage_frame = getattr(stage, "gi_frame", None)
            stage_line = stage_frame.f_lineno if stage_frame is not None else None
            tree_started = len(tree_times)
            started = perf_counter()
            cpu_started = thread_time()
            try:
                callback(*args, **kwargs)
            finally:
                duration = perf_counter() - started
                turns.setdefault(phase, []).append(duration)
                if duration > _UI_DIAGNOSTIC_SECONDS:
                    name = getattr(callback, "__qualname__", type(callback).__name__)
                    inner = callback
                    for _ in range(3):
                        candidates = [
                            cell.cell_contents
                            for cell in (getattr(inner, "__closure__", None) or ())
                            if callable(cell.cell_contents)
                        ]
                        if len(candidates) != 1:
                            break
                        inner = candidates[0]
                        name += f" -> {getattr(inner, '__qualname__', type(inner).__name__)}"
                    if code is not None:
                        name += f"[{code.co_name}]"
                        if stage_line is not None:
                            name += f":{stage_line}"
                    print(
                        f"Slow Cast {phase} {name}: {duration * 1000:.2f} ms; "
                        f"{(thread_time() - cpu_started) * 1000:.2f} ms UI CPU"
                    )
                    native_steps = tree_times[tree_started:]
                    if native_steps:
                        _phase, operation, elapsed, cpu = max(
                            native_steps, key=lambda step: step[2]
                        )
                        print(
                            f"  Native tree {operation}: {elapsed * 1000:.2f} ms; "
                            f"{cpu * 1000:.2f} ms UI CPU; "
                            f"{len(native_steps)} calls / "
                            f"{sum(step[2] for step in native_steps) * 1000:.2f} ms total"
                        )

        return invoke

    def later(delay, callback, *args, **kwargs):
        timer = native_later(delay, timed(callback, args, kwargs))
        timers.append(timer)
        return timer

    def after(callback, *args, **kwargs):
        return native_after(timed(callback, args, kwargs))

    def collection_timing(when, info):
        generation = info["generation"]
        if when == "start":
            collection_started[generation] = perf_counter()
        elif generation in collection_started:
            collections.append((generation, perf_counter() - collection_started.pop(generation)))

    monkeypatch.setattr(wx, "CallLater", later)
    monkeypatch.setattr(wx, "CallAfter", after)
    heartbeat = wx.Timer(frame.frame)
    frame.frame.Bind(wx.EVT_TIMER, lambda _event: heartbeats.append(perf_counter()), heartbeat)
    heartbeat.Start(25)
    pulse_stop = threading.Event()

    def pulse_reply(posted_at, posted_phase):
        if not pulse_stop.is_set():
            replies.append((posted_phase, perf_counter() - posted_at))

    def pulse_sender():
        while not pulse_stop.wait(0.025):
            native_after(pulse_reply, perf_counter(), phase)

    pulse_thread = threading.Thread(target=pulse_sender, name="cast-view-ui-pulse")
    pulse_thread.start()
    gc.callbacks.append(collection_timing)
    try:
        started = perf_counter()
        frame.frame.Show()
        print(f"Native Cast window show: {(perf_counter() - started) * 1000:.2f} ms")
        phase = "downloads-all"
        started = monotonic()
        later(1, frame.open_podcast_downloads)
        _run_cast_until(
            lambda: (
                frame._current_place == "downloads"
                and frame._episodes.GetItemCount() == 1000
                and frame._cast_place_counts.get("downloads") == 1300
                and frame._cast_view_snapshot is None
                and frame._cast_view_task is None
            ),
            timeout=120,
        )
        print(
            f"Native Cast Downloads All: {len(turns[phase])} UI callbacks; "
            f"maximum {max(turns[phase]) * 1000:.2f} ms; {monotonic() - started:.2f} s total"
        )
        phase = "downloads-unheard"
        frame._podcast_history.episode_filter = "unplayed"
        started = monotonic()
        later(1, frame._refresh_place)
        _run_cast_until(
            lambda: (
                frame._episodes.GetItemCount() == 650
                and frame._cast_view_snapshot is None
                and frame._cast_view_task is None
            ),
            timeout=120,
        )
        assert all(not episode.played for episode in frame._current_episodes)
        assert all(
            any(candidate is episode for candidate in show.episodes)
            for show, episode in zip(frame._pair_shows, frame._current_episodes, strict=True)
        )
        print(
            f"Native Cast Downloads Unheard: {len(turns[phase])} UI callbacks; "
            f"maximum {max(turns[phase]) * 1000:.2f} ms; {monotonic() - started:.2f} s total"
        )
        phase = "partial-capture-cancel"

        def captured_most_shows():
            job = frame._cast_view_snapshot
            chunks = getattr(job, "_chunks", None)
            state = getattr(chunks, "gi_frame", None)
            captured = state.f_locals.get("captured") if state is not None else None
            return captured is not None and len(captured.shows) >= 1200

        later(1, frame._refresh_place)
        _run_cast_until(captured_most_shows, timeout=30)
        later(1, frame._cancel_cast_view_preparation)
        _run_cast_until(
            lambda: (
                frame._cast_view_snapshot is None
                and not frame._cast_view_retirement_pool.snapshot()
            )
        )
        assert frame._cast_view_task is None
        print(
            f"Native Cast partial capture cancellation: maximum {max(turns[phase]) * 1000:.2f} ms"
        )
        phase = "library-open"
        frame._podcast_history.episode_filter = "all"
        later(1, lambda: frame.show_place("podcasts", focus=False))
        _run_cast_until(
            lambda: (
                frame._current_place == "podcasts"
                and frame._cast_view_snapshot is None
                and frame._cast_view_task is None
                and getattr(frame, "_cast_tree_chunks", None) is None
                and len(frame._cast_tree_items) == 1300
            ),
            timeout=120,
        )
        print(
            f"Native Cast library open: {len(turns[phase])} UI callbacks; "
            f"maximum {max(turns[phase]) * 1000:.2f} ms"
        )
        phase = "library-arrows"
        rows = list(frame._cast_tree_items.values())
        selection_refresh = frame._refresh_selection_buttons
        status_refresh = frame._cast_status_bar_chunks
        selections = 0
        selection_refreshes = 0
        status_refreshes = 0

        def status_chunks():
            nonlocal status_refreshes
            status_refreshes += 1
            return status_refresh()

        def refresh_selection():
            nonlocal selection_refreshes
            selection_refreshes += 1
            with monkeypatch.context() as patch:
                patch.setattr(frame, "_cast_status_bar_chunks", status_chunks)
                selection_refresh()

        monkeypatch.setattr(frame, "_refresh_selection_buttons", refresh_selection)

        def arrow():
            nonlocal selections
            selections += 1
            frame._shows_tree.SelectItem(rows[selections])
            if selections < 100:
                later(1, arrow)

        later(1, arrow)
        _run_cast_until(
            lambda: (
                selections == 100 and not getattr(frame, "_cast_selection_refresh_pending", False)
            ),
            timeout=10,
        )
        assert frame._shows_tree.GetSelection() == rows[100]
        assert 1 <= selection_refreshes <= selections
        assert status_refreshes == 0, "Arrow selection refreshed library/status readouts"
        selected_show = frame._selected_show()
        assert selected_show is not None
        assert frame._unfollow_btn.GetLabel() == object_label("&Unfollow", selected_show.title)
        print(
            f"Native Cast library arrows: {selections} selections; {selection_refreshes} "
            "button refreshes; "
            f"maximum {max(turns[phase]) * 1000:.2f} ms"
        )
        if len(heartbeats) > 1:
            gap = max(b - a for a, b in zip(heartbeats, heartbeats[1:], strict=False))
            print(f"Maximum Cast listener gap: {gap * 1000:.2f} ms")
        if replies:
            for reply_phase in (
                "showing-window",
                "downloads-all",
                "downloads-unheard",
                "partial-capture-cancel",
            ):
                durations = [duration for name, duration in replies if name == reply_phase]
                if durations:
                    print(
                        f"Maximum queued Cast UI response {reply_phase}: "
                        f"{max(durations) * 1000:.2f} ms"
                    )
        if collections:
            generation, duration = max(collections, key=lambda item: item[1])
            print(f"Longest Cast GC: generation {generation}, {duration * 1000:.2f} ms")
        method_peaks = {}
        for method_phase, name, duration in method_times:
            key = (method_phase, name)
            method_peaks[key] = max(method_peaks.get(key, 0.0), duration)
        for (method_phase, name), duration in sorted(
            method_peaks.items(), key=lambda item: item[1], reverse=True
        )[:12]:
            print(f"Cast UI method {method_phase} {name}: {duration * 1000:.2f} ms")
        tree_peaks = {}
        for tree_phase, name, duration, cpu in tree_times:
            key = (tree_phase, name)
            if duration > tree_peaks.get(key, (0.0, 0.0))[0]:
                tree_peaks[key] = (duration, cpu)
        for (tree_phase, name), (duration, cpu) in sorted(
            tree_peaks.items(), key=lambda item: item[1][0], reverse=True
        )[:12]:
            print(
                f"Cast native tree {tree_phase} {name}: {duration * 1000:.2f} ms; "
                f"{cpu * 1000:.2f} ms UI CPU"
            )
        maxima = {name: max(values) for name, values in turns.items()}
        assert all(value <= _UI_STALL_SECONDS for value in maxima.values()), {
            name: round(value * 1000, 2) for name, value in maxima.items()
        }
    finally:
        pulse_stop.set()
        pulse_thread.join(timeout=3)
        gc.callbacks.remove(collection_timing)
        heartbeat.Stop()
        frame._cancel_cast_view_preparation()
        for timer in timers:
            timer.Stop()
        frame._podcast_library = original_library
        assert not pulse_thread.is_alive(), "Cast view heartbeat thread did not stop"


@pytest.mark.timeout(180)
@pytest.mark.skipif(os.environ.get("RUN_PERF") != "1", reason="Opt-in native catalogue budget")
def test_large_library_folder_moves_preserve_focus_without_native_churn(
    cast_frame, monkeypatch
) -> None:
    from quill.core.podcasts.models import PodcastFolder, PodcastShow
    from quill.core.podcasts.models_episode import PodcastEpisode
    from quill.core.podcasts.subscriptions import PodcastLibrary
    from quill.ui.podcasts import show_filing
    from quill.ui.podcasts.folder_picker_dialog import FolderPickerResult
    from quill.ui.podcasts.library_tree_updates import row_key

    frame = cast_frame
    library = PodcastLibrary(
        folders=[PodcastFolder(id="destination", name="Destination")],
        shows=[
            PodcastShow(
                id=str(index),
                title=f"Show {index:04}",
                episodes=[
                    PodcastEpisode(guid=str(number), title="Episode", audio_url="u")
                    for number in range(150)
                ],
            )
            for index in range(1300)
        ],
    )
    frame._cancel_cast_view_preparation()
    frame._podcast_library = library
    frame._podcast_library_revision = int(getattr(frame, "_podcast_library_revision", 0)) + 1
    frame.frame.Show()
    frame.show_place("podcasts")
    _run_cast_until(
        lambda: (
            frame._cast_view_snapshot is None
            and frame._cast_view_task is None
            and getattr(frame, "_cast_tree_chunks", None) is None
            and len(frame._cast_tree_items) == 1301
        ),
        timeout=60,
    )
    tree = frame._shows_tree
    # Real picker keyboard/focus behavior is covered above. Here only the
    # listener's choice is automated; saving and counts publication stay real.
    monkeypatch.setattr(
        show_filing,
        "FolderPickerDialog",
        lambda *_a, **_kw: SimpleNamespace(show=lambda: FolderPickerResult(True, "destination")),
    )
    native_later, native_after = wx.CallLater, wx.CallAfter
    samples = []
    operations = []
    phase = "middle"

    def timed(callback, args, kwargs):
        def invoke():
            started = perf_counter()
            try:
                return callback(*args, **kwargs)
            finally:
                samples.append((phase, callback.__qualname__, perf_counter() - started))

        return invoke

    monkeypatch.setattr(
        wx, "CallLater", lambda delay, cb, *a, **kw: native_later(delay, timed(cb, a, kw))
    )
    monkeypatch.setattr(wx, "CallAfter", lambda cb, *a, **kw: native_after(timed(cb, a, kw)))
    for name in ("DeleteAllItems", "Delete", "InsertItem", "PrependItem"):
        method = getattr(tree, name)

        def counted(*args, _method=method, _name=name, **kwargs):
            operations.append(_name)
            return _method(*args, **kwargs)

        monkeypatch.setattr(tree, name, counted)
    results = []
    for name, moved_id, next_id in (("middle", "650", "651"), ("bottom", "1299", "1298")):
        phase = name
        operations.clear()
        before = dict(frame._cast_tree_items)
        tree.SelectItem(before[("show", moved_id)])
        tree.SetFocus()
        moved = library.find_show(moved_id)
        started = monotonic()
        wx.CallLater(1, frame._on_library_move_to_folder)
        _run_cast_until(
            lambda moved=moved: (
                moved.folder_id == "destination"
                and frame._cast_tree_chunks is None
                and not getattr(frame, "_cast_selection_refresh_pending", False)
            ),
            timeout=10,
        )
        elapsed = monotonic() - started
        assert tree.GetSelection() == before[("show", next_id)]
        assert tree.HasFocus()
        _run_cast_until(
            lambda: (
                frame._cast_view_snapshot is None
                and frame._cast_view_task is None
                and frame._cast_tree_chunks is None
            ),
            timeout=30,
        )
        assert row_key(frame, tree.GetSelection()) == ("show", next_id)
        assert tree.GetSelection() == before[("show", next_id)]
        assert "DeleteAllItems" not in operations
        assert sum(operations.count(op) for op in ("InsertItem", "PrependItem")) == 1
        assert operations.count("Delete") == 1
        print(f"Cast move {name}: {elapsed:.3f} s; neighbor retained after counts publication")
        results.append(elapsed)
    frame._flush_podcast_library()
    _run_cast_until(lambda: not frame._podcast_library_dirty, timeout=60)
    print("Cast moves: final library write completed")
    for sample_phase, callback, duration in sorted(samples, key=lambda row: row[2], reverse=True)[
        :8
    ]:
        print(f"Cast move {sample_phase} {callback}: {duration * 1000:.2f} ms")
    assert max(results) < 1.0, results
    assert max(sample[2] for sample in samples) <= _UI_STALL_SECONDS


def test_feed_progress_is_modeless_nonactivating_traversable_and_stoppable(cast_frame) -> None:
    from quill.ui.dialog_contract import set_transition_announcement_policy
    from quill.ui.podcasts import check_run

    host = cast_frame
    host.frame.Show()
    host.frame.Raise()
    host._places.box.SetFocus()
    _pump_cast_until(lambda: wx.Window.FindFocus() is host._places.box)
    spoken: list[str] = []
    host._announce = lambda message, **_kwargs: spoken.append(message)
    set_transition_announcement_policy(lambda: True)
    run = check_run.start(host, ["s1", "s2"])
    peer = host._podcast_feed_progress_window
    _pump_cast_until(lambda: peer.frame.IsShown())
    assert wx.Window.FindFocus() is host._places.box
    assert not any(message.startswith("Entered") for message in spoken)
    check_run.started(host, "s1", "Show 1")
    assert "Show 1" in peer.status.GetValue()
    host._windows.activate(host._windows.key_for(peer.frame))
    _pump_cast_until(lambda: wx.Window.FindFocus() is peer.status)
    check_run.cancel_remaining(host)
    assert run.cancelled and not run.pending
    assert "Stopped" in peer.status.GetValue()
    assert not peer.stop.IsEnabled()
    peer.frame.Close()
    _pump_cast_until(lambda: not peer.frame.IsShown())
    assert host.frame.IsShown() and host.frame.IsEnabled()


def test_opml_import_and_report_reuse_window_numbers_and_keep_cast_enabled(
    cast_frame,
    tmp_path,
    monkeypatch,
) -> None:
    from quill.ui.podcasts.opml_import_dialog import open_import_window

    host = cast_frame
    path = tmp_path / "subscriptions.opml"
    path.write_text(
        '<opml version="2.0"><body><outline text="Imported" '
        'type="rss" xmlUrl="https://import.example/feed"/></body></opml>',
        encoding="utf-8",
    )
    refreshes: list[Any] = []
    monkeypatch.setattr(
        host,
        "_start_new_podcast_feed_check",
        lambda ids, **kwargs: refreshes.append((ids, kwargs)),
    )
    host.frame.Show()
    window = open_import_window(host, path)
    identifier = window.frame.GetId()
    window._check_feeds.SetValue(False)
    window._on_start(None)
    _pump_cast_until(lambda: not window._running, timeout=5)
    assert host.frame.IsEnabled()
    assert host._podcast_library.shows[-1].feed_url == "https://import.example/feed"
    assert refreshes[-1][1]["only_if_automatic_checks_enabled"] is True
    report = host._opml_import_report_window
    report_identifier = report.frame.GetId()
    assert "No feed checks" in report._list.GetString(0)
    assert open_import_window(host, path).frame.GetId() == identifier
    window._check_feeds.SetValue(False)
    window._on_start(None)
    _pump_cast_until(lambda: not window._running, timeout=5)
    assert host._opml_import_report_window.frame.GetId() == report_identifier
    assert report._list.GetCount() == 1
    assert "Skipped duplicate" in report._list.GetString(0)
    host._windows.activate(host._windows.key_for(report.frame))
    _pump_cast_until(lambda: wx.Window.FindFocus() is report._list)
    report.frame.Close()
    _pump_cast_until(lambda: not report.frame.IsShown())


def test_the_selection_contract_reads_whichever_pane_is_up(cast_frame) -> None:
    frame = cast_frame
    frame.show_place("inbox", focus=False)
    assert frame._content.showing == frame._content.LIST
    selected = frame._selected_tree_data()
    assert selected is not None and selected[0] == "episode"
    pair = frame._selected_episode()
    assert pair is not None and pair[1].guid.startswith("s")
    assert frame._winamp_rows() and frame._winamp_selected_index() == 0
    frame.show_place("favorites", focus=False)
    selected = frame._selected_tree_data()
    assert selected == ("show", "s1")
    assert frame._selected_show().title == "Show 1"
    frame.show_place("podcasts", focus=False)
    selected = frame._selected_tree_data()
    assert selected is not None and selected[0] in ("show", "folder")


def test_favorites_enter_opens_the_podcast_in_place_and_backspace_returns(cast_frame) -> None:
    frame = cast_frame
    frame.show_place("favorites", focus=False)
    frame._activate_content_row(("show", "s1"))
    assert frame._place_opened_show_id == "s1"
    assert frame._content.heading.GetLabel().startswith("Show 1")
    assert len(frame._current_episodes) == 3
    assert frame._back_from_show_in_place() is True
    assert frame._place_opened_show_id == ""
    assert frame._selected_tree_data() == ("show", "s1")


def test_delete_removes_from_this_place_and_never_the_episode(cast_frame) -> None:
    frame = cast_frame
    frame.show_place("inbox", focus=False)
    before = len(frame._current_episodes)
    frame._remove_from_place(frame._selected_tree_data())
    assert len(frame._current_episodes) == before - 1
    assert sum(len(s.episodes) for s in frame._podcast_library.shows) == 9
    frame.show_place("favorites", focus=False)
    frame._remove_from_place(("show", "s1"))
    assert frame._podcast_library.find_show("s1").is_favorite is False
    assert frame._podcast_library.find_show("s1") is not None


def test_space_queues_and_the_queue_place_lists_it(cast_frame) -> None:
    frame = cast_frame
    frame.show_place("new_episodes", focus=False)
    frame._queue_selected_episode()
    assert len(frame._podcast_library.queue) == 1
    frame.show_place("queue", focus=False)
    assert len(frame._current_episodes) == 1


def test_the_places_list_is_the_listeners(cast_frame) -> None:
    frame = cast_frame
    frame.show_place("inbox", focus=False)
    frame._move_place("inbox", 1)
    rows = _rows(frame)
    assert rows[1].startswith("Inbox")
    assert frame._podcast_library.settings.places_layout
    frame._on_place_hide("downloads")
    assert "downloads" in frame._places_layout().hidden
    assert not any(
        row.startswith("Downloads")
        for row in [frame._places.box.GetString(i) for i in range(frame._places.box.GetCount())]
    )
    frame._on_place_show("downloads")
    assert "downloads" not in frame._places_layout().hidden


@pytest.mark.parametrize("place", ["inbox", "podcasts"])
def test_find_flattens_the_pane_and_escape_restores_the_place(cast_frame, place) -> None:
    frame = cast_frame
    frame.show_place(place, focus=False)
    frame._find_box.ChangeValue("Show 2")
    frame._run_library_find()
    assert frame._content.showing == frame._content.TREE
    assert frame._content.heading.GetLabel() == "Matches"
    assert frame._library_find_active()
    assert not frame._cast_tree_items
    assert not frame._cast_tree_children
    frame._find_box.ChangeValue("")
    frame._end_library_find(announce=False)
    assert frame._current_place == place
    if place == "inbox":
        assert frame._content.showing == frame._content.LIST
    else:
        _run_cast_until(lambda: frame._cast_tree_chunks is None)
        assert frame._content.showing == frame._content.TREE
        assert {key[1] for key in frame._cast_tree_items} == {"s1", "s2", "s3"}
        for key, item in frame._cast_tree_items.items():
            assert frame._shows_tree.GetItemData(item) == key


def test_the_doors_of_the_old_windows_lead_to_places(cast_frame) -> None:
    frame = cast_frame
    frame.open_podcast_manager()
    assert frame._current_place == "podcasts"
    frame._open_play_queue()
    assert frame._current_place == "queue"
    frame.open_podcast_downloads()
    assert frame._current_place == "downloads"
    frame.open_continue_listening()
    assert frame._current_place == "continue_listening"
    frame.open_cast_notifications()
    assert frame._current_place == "notifications"


def test_the_menu_bar_has_the_places_and_no_manager(cast_frame) -> None:
    bar = cast_frame.frame.GetMenuBar()
    labels: list[str] = []

    def walk(menu) -> None:
        for item in menu.GetMenuItems():
            labels.append(item.GetItemLabelText())
            if item.GetSubMenu() is not None:
                walk(item.GetSubMenu())

    for index in range(bar.GetMenuCount()):
        walk(bar.GetMenu(index))
    assert "Open Podcast Manager..." not in labels
    assert "Podcast Settings..." not in labels
    assert "Skip Settings..." not in labels
    wanted_rows = (
        "Inbox",
        "New Episodes",
        "Continue Listening",
        "Favorites",
        "Play Queue",
        "Downloads",
        "Notifications",
        "Podcasts",
        "Places...",
        "Show",
        "Sort Episodes",
        "Settings for This Podcast...",
        "Refresh All Now",
    )
    for wanted in wanted_rows:
        assert wanted in labels, wanted


def test_a_feature_switched_off_is_absent(cast_frame) -> None:
    frame = cast_frame
    frame._cast_app_features().set_enabled("queue", False)
    frame._build_menu_bar()
    frame._rebuild_places()
    rows = _rows(frame)
    assert not any(row.startswith("Play Queue") for row in rows)
    probe = frame._cast_command_unavailable_reason
    assert probe("podcasts.open_queue") == "off in Customize Features"
    assert probe("podcasts.play_pause") == ""
    assert frame.commands.unavailable_reason("podcasts.open_queue") == "off in Customize Features"
    frame._cast_app_features().set_enabled("queue", True)


def test_preferences_and_the_places_chooser_build(cast_frame) -> None:
    from quill.apps.podcasts_preferences import app_rows
    from quill.ui.podcasts.places_chooser import PlacesChooser
    from quill.ui.podcasts.preferences_window import CastPreferencesWindow

    frame = cast_frame
    window = CastPreferencesWindow(
        frame.frame,
        library=frame._podcast_library,
        history=frame._podcast_history,
        app_rows=app_rows(frame),
        announce=lambda _m: None,
        summary=lambda: "summary",
    )
    for index in range(window._section.GetCount()):
        window._section.SetSelection(index)
        window._on_section()
        assert window._built or index in (4,), (
            index
        )  # every section has rows (Chapters may be defs only)
    window.dialog.Destroy()
    chooser = PlacesChooser(
        frame.frame,
        layout=frame._places_layout(),
        label_for=lambda place_id: place_id,
        enabled=frame._cast_area_enabled,
        announce=lambda _m: None,
    )
    assert chooser._list.GetCount() == 11
    chooser.dialog.Destroy()


def test_cast_never_takes_ctrl_alt_shift_q_system_wide(cast_frame) -> None:
    """qc.md C2-01: Ctrl+Alt+Shift+Q is QUILL's show/hide key. Cast must not
    claim it as a second show/hide while it runs, even when Windows refuses
    Cast's own chord."""
    from quill.apps.podcasts_routes import CAST_TRAY_HOTKEY

    assert cast_frame._own_tray_hotkey == CAST_TRAY_HOTKEY
    cast_frame._tray_hotkey_registered = False  # as if Windows refused it
    assert "Ctrl+Alt+Shift+Q" not in cast_frame._global_hotkey_bindings().values()


def test_mark_as_played_and_next_shows_its_own_key(cast_frame) -> None:
    """It was Ctrl+Alt+Shift+Q, QUILL's show/hide key, and never fired while
    QUILL ran. It now follows Next in Queue's key, through the app keymap."""
    labels = []
    bar = cast_frame.frame.GetMenuBar()
    for index in range(bar.GetMenuCount()):
        for item in bar.GetMenu(index).GetMenuItems():
            if item.GetSubMenu() is not None:
                labels += [sub.GetItemLabel() for sub in item.GetSubMenu().GetMenuItems()]
    assert "Mark as Played and Ne&xt\tCtrl+Alt+Shift+Down" in labels


def test_player_information_and_carry_my_place_have_menu_rows(cast_frame) -> None:
    """qc.md C2-03: both were reachable only through the Command Palette."""
    labels = []
    bar = cast_frame.frame.GetMenuBar()
    for index in range(bar.GetMenuCount()):
        labels += [item.GetItemLabel() for item in bar.GetMenu(index).GetMenuItems()]
    assert any(label.startswith("Player Information...\tCtrl+I") for label in labels)
    assert any("Carry My Place Between Mac&hines..." in label for label in labels)


def test_delete_lands_on_the_row_that_moved_into_its_place(cast_frame) -> None:
    """qc.md F-10: after a row leaves, the cursor is on its neighbour, not the top."""
    frame = cast_frame
    frame.show_place("inbox", focus=False)
    frame._select_list_row(2)
    assert frame._episodes.GetFirstSelected() == 2, frame._list_rows
    following = frame._list_rows[3]
    removed = frame._selected_tree_data()
    frame._remove_from_place(removed)
    assert removed not in frame._list_rows, (removed, frame._list_rows)
    assert frame._episodes.GetFirstSelected() == 2
    assert frame._list_rows[2] == following


def test_dismissing_from_the_inbox_deletes_the_download_when_done_means_deleted(
    cast_frame, tmp_path
) -> None:
    """Earshot R4: with Delete downloads when done on, Delete in the Inbox frees the file."""
    frame = cast_frame
    frame._podcast_library.settings.delete_after_play = True
    frame.show_place("inbox", focus=False)
    pair = frame._selected_episode()
    assert pair is not None
    _show, episode = pair
    copy = tmp_path / "episode.mp3"
    copy.write_bytes(b"audio")
    episode.downloaded_path = str(copy)
    frame._remove_from_place(frame._selected_tree_data())
    assert episode.downloaded_path == ""
    assert not copy.exists()


def test_the_palette_says_casts_menu_names_not_quills(cast_frame) -> None:
    """The shared mixin registers QUILL's titles; Cast speaks its own words and
    has no Open Manager (it only led back to the Podcasts place)."""
    commands = cast_frame.commands
    assert commands.get("podcasts.open_manager") is None
    expected = {
        "podcasts.acb_media": "Podcasts: Follow ACB Media Podcasts",
        "podcasts.add_local": "Podcasts: Add Personal Audio...",
        "podcasts.settings": "Podcasts: Fetching Preferences...",
        "podcasts.skip_settings": "Podcasts: Playing Preferences...",
    }
    for command_id, title in expected.items():
        command = commands.get(command_id)
        assert command is not None, command_id
        assert command.title == title


def test_play_next_episode_from_the_managers_verbs_plays_in_the_one_window(
    cast_frame, monkeypatch
) -> None:
    """The Manager's play verb was never defined on the one window, so its
    Play Next Episode (and chapter jump) raised there."""
    from quill.ui.podcasts import show_actions

    started: list[tuple[str, int | None]] = []
    monkeypatch.setattr(
        show_actions,
        "start_episode_playback",
        lambda _c, _l, show, episode, *, resume_ms=None, announce=None: (
            started.append((episode.guid, resume_ms)) or True
        ),
    )
    frame = cast_frame
    show = frame._podcast_library.find_show("s2")
    frame._play_next_unplayed(show)
    assert started and started[0][0].startswith("s2e")
