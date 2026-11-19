"""Lists that stay still (FUX-06, Cast PRD 23.33), driven on the real Cast window.

"A feed refresh, a finished download or a new arrival never moves the selected
row or focus in Episodes, Continue Listening or the Play Queue. New items wait
to be reached, with their count said once."

Every list is tested the same way: select an episode, change the library the
way something in the background would (rows arrive above the reader, another
row goes), then let a **real** feed refresh -- ``feed_refresh.refresh_feed``
with only the network replaced -- do the refill it does after every check. Then:
the same episode is selected and focused, it is on the same line of the screen,
nothing took keyboard focus, and the count was said once ("3 new episodes in
The Daily."). A refresh that brings nothing says nothing and moves nothing.
"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

#: Serialized onto one worker: the real frame registers system-wide hotkeys
#: and starts the screen-reader bridges (as test_cast_one_window.py).
pytestmark = pytest.mark.machine_global

DAILY = "daily"
SELECTED = ("episode", f"{DAILY}\x00d3")


def _episode(guid: str, title: str, day: int, **extra: Any) -> Any:
    from quill.core.podcasts.models_episode import PodcastEpisode

    return PodcastEpisode(
        guid=guid,
        title=title,
        audio_url=f"http://x.invalid/{guid}.mp3",
        # RFC 2822, as a feed writes it, so newest-first really sorts by date.
        published=f"{day:02d} Sep 2026 06:00:00 GMT",
        duration_seconds=3600,
        **extra,
    )


@pytest.fixture
def cast_frame(
    quill_data_dir: Path, monkeypatch: pytest.MonkeyPatch, wx_app, quiet_cast_startup, close_cast
):
    """The real Cast window over The Daily (d1..d6) and a long Zebra Talk below it."""
    from quill.core.podcasts import queue as queue_ops
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.subscriptions import PodcastLibrary, save_library

    library = PodcastLibrary()
    daily = PodcastShow(id=DAILY, title="The Daily", feed_url="http://x.invalid/daily")
    daily.route_to_inbox = True
    daily.is_favorite = True
    for day in range(1, 7):
        # d2..d4 are part-heard: Continue Listening.
        daily.episodes.append(
            _episode(f"d{day}", f"Daily {day}", day, position_ms=60_000 if 2 <= day <= 4 else 0)
        )
    library.add_show(daily)
    # Enough rows below that the list scrolls, so "the same line" means something.
    zebra = PodcastShow(id="zebra", title="Zebra Talk", feed_url="http://x.invalid/zebra")
    zebra.route_to_inbox = True
    # Zebra is in every list -- part-heard, downloaded, queued -- for that reason.
    for day in range(1, 29):
        zebra.episodes.append(
            _episode(
                f"z{day}",
                f"Zebra {day}",
                day,
                position_ms=60_000,
                downloaded_path=str(quill_data_dir / f"z{day}.mp3"),
            )
        )
    library.add_show(zebra)
    for day in range(1, 5):
        queue_ops.add_to_queue(library, DAILY, f"d{day}")
    for day in range(1, 29):
        queue_ops.add_to_queue(library, "zebra", f"z{day}")
    # Nothing here reaches the network: a queued episode is not fetched.
    library.settings.auto_download_queued = False
    save_library(quill_data_dir, library)

    previous_loop = wx.EventLoop.GetActive()
    loop = wx.GUIEventLoop()
    wx.EventLoop.SetActive(loop)
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    monkeypatch.setattr(PodcastsAppFrame, "_announce", lambda self, *a, **kw: None)
    # No desktop toast from a test.
    monkeypatch.setattr(PodcastsAppFrame, "_podcast_notify_new_episodes", lambda *a, **kw: None)
    frame = PodcastsAppFrame()
    frame.said = []
    frame._announce = lambda message, *a, **kw: frame.said.append(str(message))
    try:
        yield frame
    finally:
        set_transition_announcement_policy(None)
        try:
            assert close_cast(frame, loop=loop), "Cast did not finish its responsive shutdown"
        finally:
            wx.EventLoop.SetActive(previous_loop)


class _Now:
    """The feed-check pool, run on this thread so the test sees the whole refresh."""

    def submit(self, _name: str, func: Any, *, on_success: Any, on_failure: Any) -> None:
        try:
            result = func()
        except Exception as error:  # noqa: BLE001
            on_failure("op", error)
        else:
            on_success("op", result)


def _pump() -> None:
    app = wx.GetApp()
    loop = wx.EventLoop.GetActive()
    for _ in range(5):
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        if loop is not None:
            loop.ProcessIdle()


def _background_refresh(frame: Any, monkeypatch: pytest.MonkeyPatch, arrivals: int) -> None:
    """A real refresh of The Daily whose feed has *arrivals* episodes newer than any."""
    from quill.core.podcasts import feed_reader
    from quill.core.podcasts.feed_reader import FeedInfo
    from quill.ui.podcasts import feed_refresh

    show = frame._podcast_library.find_show(DAILY)
    published = [_episode(ep.guid, ep.title, int(ep.published[:2])) for ep in show.episodes] + [
        _episode(f"new{n}", f"Breaking {n}", 20 + n) for n in range(1, arrivals + 1)
    ]
    monkeypatch.setattr(
        feed_reader,
        "fetch_and_parse_feed",
        lambda *_a, **_k: FeedInfo(
            title="The Daily", homepage="", artwork_url="", episodes=published
        ),
    )
    monkeypatch.setattr(feed_refresh, "feed_check_pool", lambda _host: _Now())
    feed_refresh.refresh_feed(frame, DAILY)
    _pump()


def _watch_focus(frame: Any, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every way a refill could take keyboard focus."""
    taken: list[str] = []
    monkeypatch.setattr(frame._content, "focus", lambda: taken.append("content pane"))
    for name, control in (
        ("episode list", frame._episodes),
        ("library tree", frame._shows_tree),
    ):
        monkeypatch.setattr(control, "SetFocus", lambda name=name: taken.append(name))
    return taken


def _new_episode_lines(frame: Any) -> list[str]:
    return [line for line in frame.said if "new episode" in line.lower()]


# -- the main window's report list: Episodes, Continue Listening, the Play Queue -- #


def _scroll_selected_to_line(frame: Any, line: int) -> None:
    """Put the selected row *line* rows below the top of the view."""
    episodes = frame._episodes
    index = episodes.GetFirstSelected()
    top = max(0, index - line)
    current = episodes.GetTopItem()
    height = episodes.GetItemRect(current).height
    episodes.ScrollList(0, (top - current) * height)


def _place_rows(frame: Any) -> list[tuple[str, str]]:
    return list(frame._list_rows)


def _assert_still(frame: Any, before_index: int, before_line: int, *, moved: bool) -> None:
    episodes = frame._episodes
    assert frame._list_selected_data() == SELECTED
    index = episodes.GetFirstSelected()
    assert episodes.GetNextSelected(index) == -1, "exactly one row stays selected"
    assert episodes.GetFocusedItem() == index, "the focused item is the selected episode"
    if moved:
        assert index != before_index, "the refill was meant to move the row"
    else:
        assert index == before_index
    rows_on_screen = episodes.GetCountPerPage()
    assert 0 < rows_on_screen < episodes.GetItemCount(), "the list scrolls, so the line is real"
    assert index - episodes.GetTopItem() == before_line, "the row stays on its line"


def _silently(frame: Any, place: str) -> None:
    """What the background did before the refresh: rows above appear, another goes."""
    from quill.core.podcasts import queue as queue_ops
    from quill.core.podcasts.inbox import REMOVED_MARKER, inbox_key

    library = frame._podcast_library
    show = library.find_show(DAILY)
    by_guid = {ep.guid: ep for ep in show.episodes}
    if place == "new_episodes":
        by_guid["d5"].played = True  # finished in another window; leaves the list
    elif place == "inbox":
        library.inbox_assignments[inbox_key(DAILY, "d5")] = REMOVED_MARKER
    elif place == "continue_listening":
        by_guid["d5"].position_ms = 60_000  # started elsewhere: newer, so above d3
        by_guid["d6"].position_ms = 60_000
        by_guid["d4"].position_ms = 0  # forgotten elsewhere: leaves the list
    elif place == "queue":
        queue_ops.pop_next_playable(library)  # an episode finished; the next was taken
        queue_ops.play_next(library, DAILY, "d6")  # Play Next from a notification
        queue_ops.play_next(library, DAILY, "d5")
    elif place == "downloads":
        for guid in ("d5", "d6"):  # two downloads finish, newer than d3
            by_guid[guid].downloaded_path = _download(frame, guid)
        by_guid["d1"].downloaded_path = ""  # one removed by the cleanup


def _download(frame: Any, guid: str) -> str:
    return str(Path(frame._podcast_download_root()) / f"{guid}.mp3")


@pytest.mark.parametrize(
    "place", ["new_episodes", "inbox", "continue_listening", "queue", "downloads"]
)
def test_a_background_refresh_keeps_the_selected_episode_focus_and_line(
    cast_frame, monkeypatch, place
) -> None:
    frame = cast_frame
    assert frame.show_place(place, focus=False)
    if place == "downloads":
        for ep in frame._podcast_library.find_show(DAILY).episodes:
            if ep.guid in ("d3", "d1"):
                ep.downloaded_path = _download(frame, ep.guid)
        frame._refresh_place(keep=False)
    assert frame._select_list_key(SELECTED), f"{place} lists d3"
    _scroll_selected_to_line(frame, 1)
    before_index = frame._episodes.GetFirstSelected()
    before_line = before_index - frame._episodes.GetTopItem()
    taken = _watch_focus(frame, monkeypatch)
    frame.said.clear()

    _silently(frame, place)
    _background_refresh(frame, monkeypatch, arrivals=3)

    _assert_still(frame, before_index, before_line, moved=True)
    assert taken == [], f"the refill took focus: {taken}"
    assert _new_episode_lines(frame) == ["3 new episodes in The Daily."]


@pytest.mark.parametrize("place", ["new_episodes", "continue_listening", "queue"])
def test_a_refresh_with_nothing_new_says_nothing_and_moves_nothing(
    cast_frame, monkeypatch, place
) -> None:
    frame = cast_frame
    assert frame.show_place(place, focus=False)
    assert frame._select_list_key(SELECTED)
    _scroll_selected_to_line(frame, 1)
    episodes = frame._episodes
    before_index = episodes.GetFirstSelected()
    before_line = before_index - episodes.GetTopItem()
    taken = _watch_focus(frame, monkeypatch)
    selections: list[int] = []
    episodes.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda event: selections.append(event.GetIndex()))
    frame.said.clear()

    _background_refresh(frame, monkeypatch, arrivals=0)

    _assert_still(frame, before_index, before_line, moved=False)
    assert taken == []
    assert frame.said == []
    assert selections == [], "nothing re-selected a row that never moved"


def test_a_refill_keeps_rows_instead_of_emptying_the_list(cast_frame, monkeypatch) -> None:
    """Emptying the list is what scrolled it to the top and dropped the row."""
    frame = cast_frame
    assert frame.show_place("new_episodes", focus=False)
    assert frame._select_list_key(SELECTED)
    monkeypatch.setattr(
        frame._episodes,
        "DeleteAllItems",
        lambda: pytest.fail("a refill emptied the list"),
    )
    _background_refresh(frame, monkeypatch, arrivals=2)
    assert frame._list_selected_data() == SELECTED


def test_an_open_inbox_folder_is_refilled_without_taking_focus(cast_frame, monkeypatch) -> None:
    from quill.core.podcasts.models import PodcastFolder
    from quill.ui.podcasts.inbox_view import open_inbox_folder

    frame = cast_frame
    library = frame._podcast_library
    library.folders.append(PodcastFolder(id="news", name="News"))
    library.find_show(DAILY).folder_id = "news"
    assert frame.show_place("inbox", focus=False)
    open_inbox_folder(frame, "news")
    assert frame._select_list_key(SELECTED)
    taken = _watch_focus(frame, monkeypatch)
    frame.said.clear()

    _background_refresh(frame, monkeypatch, arrivals=3)

    assert frame._place_opened_inbox_folder == "news"
    assert frame._list_selected_data() == SELECTED
    assert frame._episodes.GetFocusedItem() == frame._episodes.GetFirstSelected()
    assert taken == [], f"the refill took focus: {taken}"
    assert _new_episode_lines(frame) == ["3 new episodes in The Daily."]


# -- the library tree (the Podcasts place) ------------------------------------------- #


def test_the_library_tree_keeps_the_selected_episode_row(cast_frame, monkeypatch) -> None:
    from quill.core.podcasts import places as places_model

    frame = cast_frame
    assert places_model.place("podcasts") is not None
    frame.show_place("podcasts", focus=False)
    _pump()
    tree = frame._shows_tree
    show_item = frame._cast_tree_items[("show", DAILY)]
    tree.Expand(show_item)
    _pump()
    rows = frame._cast_tree_episode_items
    item = rows[SELECTED]
    tree.SelectItem(item)
    taken = _watch_focus(frame, monkeypatch)
    frame.said.clear()
    show = frame._podcast_library.find_show(DAILY)
    show.episodes = [ep for ep in show.episodes if ep.guid != "d5"]  # pruned elsewhere

    _background_refresh(frame, monkeypatch, arrivals=3)

    selected = tree.GetSelection()
    assert tree.GetItemData(selected) == SELECTED
    assert selected == item, "the native row itself was kept, not rebuilt"
    first, _cookie = tree.GetFirstChild(show_item)
    assert tree.GetItemData(first) != SELECTED, "the new episodes are above it"
    assert taken == []
    assert _new_episode_lines(frame) == ["3 new episodes in The Daily."]


# -- the Play Queue window --------------------------------------------------------------- #


def _caret(box: Any) -> int:
    if sys.platform != "win32":
        return min(box.GetSelections())
    return int(ctypes.windll.user32.SendMessageW(int(box.GetHandle()), 0x019F, 0, 0))


@pytest.fixture
def queue_window(cast_frame):
    from quill.ui.podcasts.play_queue_dialog import PlayQueueDialog

    frame = cast_frame
    window = PlayQueueDialog(
        frame.frame,
        library=frame._podcast_library,
        announce_cb=frame.said.append,
        on_library_changed=frame._save_podcast_library,
        on_play=lambda *_a: None,
    )
    try:
        yield window
    finally:
        window.dialog.Destroy()


def _queue_row_of(window: Any, guid: str) -> int:
    queue = window._library.queue
    for row, (index, _label) in enumerate(window._rows):
        if index is not None and queue[index].episode_guid == guid:
            return row
    raise AssertionError(f"{guid} is not in the window")


def test_the_play_queue_window_follows_the_queue_and_keeps_the_row(
    cast_frame, queue_window, monkeypatch
) -> None:
    from quill.core.podcasts import queue as queue_ops
    from quill.ui.podcasts import queue_catch_up

    frame, window = cast_frame, queue_window
    window._select_only(_queue_row_of(window, "d3"))
    before = window._list.GetSelections()[0]
    taken: list[str] = []
    monkeypatch.setattr(window._list, "SetFocus", lambda: taken.append("queue list"))
    frame.said.clear()

    library = frame._podcast_library
    queue_ops.pop_next_playable(library)  # d1 finished playing
    queue_ops.play_next(library, DAILY, "d6")
    queue_ops.play_next(library, DAILY, "d5")
    _background_refresh(frame, monkeypatch, arrivals=3)
    assert queue_catch_up.catch_up(window), "the window saw the queue change"

    row = _queue_row_of(window, "d3")
    assert row != before, "rows went in above"
    assert list(window._list.GetSelections()) == [row]
    assert _caret(window._list) == row, "the caret is on the same episode"
    assert taken == []
    assert _new_episode_lines(frame) == ["3 new episodes in The Daily."]
    assert window._library.queue[window._selected()].episode_guid == "d3"
    frame.said.clear()
    assert not queue_catch_up.catch_up(window), "no change, no redraw"
    assert frame.said == []


def test_a_queue_verb_never_acts_on_a_stale_row(cast_frame, queue_window) -> None:
    """Before FUX-06 this removed d4: the row still pointed at position 3."""
    from quill.core.podcasts import queue as queue_ops

    frame, window = cast_frame, queue_window
    window._select_only(_queue_row_of(window, "d3"))
    queue_ops.pop_next_playable(frame._podcast_library)  # behind the window, no tick yet

    window._on_remove()

    left = [item.episode_guid for item in frame._podcast_library.queue]
    assert left[:2] == ["d2", "d4"], "the episode the listener chose went, and only it"
    assert len(left) == 2 + 28


def test_the_play_queue_window_watches_only_while_it_is_shown(queue_window, monkeypatch) -> None:
    from quill.ui.podcasts import queue_catch_up

    started: list[Any] = []
    running: list[bool] = []
    real_start = queue_catch_up.start_watch

    def start(dialog):
        timer = real_start(dialog)
        started.append(timer)
        return timer

    def modal(_dialog, _title, **_kw):
        running.append(started[0].IsRunning())
        return wx.ID_CANCEL

    monkeypatch.setattr(queue_catch_up, "start_watch", start)
    monkeypatch.setattr("quill.ui.dialog_contract.show_modal_dialog", modal)
    monkeypatch.setattr(queue_window.dialog, "Destroy", lambda: True)
    queue_window.show()
    assert running == [True], "the window watches the queue while it is up"
    assert not started[0].IsRunning(), "and stops before it is destroyed"


# -- Continue Listening, the window ---------------------------------------------------------- #


def test_the_continue_listening_window_is_not_moved_by_a_refresh(cast_frame, monkeypatch) -> None:
    """A snapshot by design: a background refresh never refills it under the reader."""
    from quill.core.media.continue_listening import Unfinished
    from quill.ui.continue_listening_dialog import ContinueListeningDialog

    frame = cast_frame
    rows = [
        Unfinished(
            provider="podcast", key=f"{DAILY}:{guid}", title=f"Daily {n}", position_ms=60_000
        )
        for n, guid in ((4, "d4"), (3, "d3"), (2, "d2"))
    ]
    window = ContinueListeningDialog(frame.frame, rows=rows, announce=frame.said.append)
    try:
        window._list.SetSelection(1)
        frame.said.clear()
        _background_refresh(frame, monkeypatch, arrivals=3)
        assert window._list.GetSelection() == 1
        assert window.selected() is rows[1]
        assert _new_episode_lines(frame) == ["3 new episodes in The Daily."]
    finally:
        window.dialog.Destroy()
