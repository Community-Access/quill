"""Find in library on the task manager: stale answers dropped, one announcement (F-09).

``test_cast_library_find.py`` covers the box with no task manager, where the
search runs inline. These tests give the host a task manager that holds each
job until the test runs it, so they can do what a fast typist does: start a
search, type more before it answers, and let the old answer arrive late.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.stability.task_manager import CancellationToken, CancelledError
from quill.ui.podcasts.library_find import CastLibraryFindMixin, hit_label


class _Tasks:
    """Holds submitted jobs; ``run(i)`` does what the worker and CallAfter would."""

    def __init__(self) -> None:
        self.jobs: list[dict[str, Any]] = []
        self.cancelled: list[str] = []

    def submit(self, name: str, func: Any, **kwargs: Any) -> Any:
        token = CancellationToken()
        operation = f"op{len(self.jobs)}"
        self.jobs.append({"name": name, "func": func, "token": token, "op": operation, **kwargs})
        return SimpleNamespace(operation_id=operation)

    def cancel(self, operation: str) -> bool:
        self.cancelled.append(operation)
        for job in self.jobs:
            if job["op"] == operation:
                job["token"].cancel()
        return True

    def run(self, index: int) -> None:
        job = self.jobs[index]
        try:
            result = job["func"](cancellation_token=job["token"])
        except BaseException as exc:  # noqa: BLE001 - delivered as the manager would
            if job.get("on_failure"):
                job["on_failure"](job["op"], exc)
            return
        if job.get("on_success"):
            job["on_success"](job["op"], result)


class _Tree:
    def __init__(self) -> None:
        self.rows: list[tuple[str, Any]] = []
        self.selected: Any = None

    def DeleteAllItems(self) -> None:  # noqa: N802 - wx API shape
        self.rows = []

    def AddRoot(self, _label: str) -> int:  # noqa: N802
        return 0

    def AppendItem(self, _parent: int, label: str) -> int:  # noqa: N802
        self.rows.append((label, None))
        return len(self.rows)

    def SetItemData(self, item: int, data: Any) -> None:  # noqa: N802
        self.rows[item - 1] = (self.rows[item - 1][0], data)

    def SelectItem(self, item: int) -> None:  # noqa: N802
        self.selected = item

    def SetFocus(self) -> None:  # noqa: N802
        pass


class _Host(CastLibraryFindMixin):
    def __init__(self, library: PodcastLibrary) -> None:
        self._podcast_library = library
        self._task_manager = _Tasks()
        self._shows_tree = _Tree()
        self._find_box = SimpleNamespace(value="", GetValue=lambda: self._find_box.value)
        self._find_box.ChangeValue = lambda v: setattr(self._find_box, "value", v)
        self._find_status = SimpleNamespace(text="")
        self._find_status.SetLabel = lambda t: setattr(self._find_status, "text", t)
        self.spoken: list[str] = []
        self.reloaded: list[Any] = []

    def _announce(self, message: str) -> None:
        self.spoken.append(message)

    def _selected_tree_data(self) -> Any:
        return None

    def _reload_library_tree(self, *, keep_key: Any = None) -> None:
        self.reloaded.append(keep_key)


@pytest.fixture(autouse=True)
def _isolated(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("quill.core.podcasts.episode_notes.load_episode_notes", lambda: [])


@pytest.fixture
def host() -> _Host:
    show = PodcastShow(id="d", title="The Daily", feed_url="https://example.invalid/d")
    show.episodes = [
        PodcastEpisode(guid="d1", title="Bristol bus boycott", audio_url="", published="2026-01"),
        PodcastEpisode(guid="d2", title="Bridges", audio_url="", published="2026-02"),
    ]
    return _Host(PodcastLibrary(shows=[show]))


def test_the_search_runs_on_the_task_manager_and_speaks_once(host: _Host) -> None:
    host._find_box.value = "bristol"
    host._run_library_find()
    assert host._shows_tree.rows == []  # nothing drawn on the UI thread yet
    assert [job["name"] for job in host._task_manager.jobs] == ["cast-library-find"]
    host._task_manager.run(0)
    assert [label for label, _ in host._shows_tree.rows] == [
        "Bristol bus boycott -- an episode of The Daily"
    ]
    assert host.spoken == ["1 match for bristol"]


def test_an_answer_overtaken_by_more_typing_is_dropped_and_its_job_cancelled(host: _Host) -> None:
    host._find_box.value = "br"
    host._run_library_find()
    host._find_box.value = "bris"
    host._run_library_find()
    assert host._task_manager.cancelled == ["op0"]
    host._task_manager.run(1)  # the newer one answers first
    host._task_manager.run(0)  # the older one arrives late -- cancelled, so it stops
    assert host.spoken == ["1 match for bris"]
    assert [label for label, _ in host._shows_tree.rows] == [
        "Bristol bus boycott -- an episode of The Daily"
    ]


def test_a_late_answer_after_escape_does_not_put_the_matches_back(host: _Host) -> None:
    host._find_box.value = "bri"
    host._run_library_find()
    host._find_box.value = ""
    host._end_library_find(announce=False)
    outcome_job = host._task_manager.jobs[0]
    outcome_job["token"] = CancellationToken()  # as if it had already finished its work
    host._task_manager.run(0)
    assert host._shows_tree.rows == []
    assert host.spoken == []
    assert host.reloaded == [None]


def test_a_quiet_refresh_while_finding_does_not_speak(host: _Host) -> None:
    host._find_box.value = "b"
    assert host._refresh_library_find() == ""
    host._task_manager.run(0)
    assert host.spoken == []
    assert host._find_status.text == "2 matches for b"


def test_a_failed_search_says_so_once_and_a_superseded_one_says_nothing(host: _Host) -> None:
    host._find_box.value = "b"
    host._run_library_find()
    host._task_manager.jobs[0]["on_failure"]("op0", RuntimeError("disk"))
    assert host.spoken == ["Find could not search your library. Try again."]
    host._task_manager.jobs[0]["on_failure"]("op0", CancelledError("superseded"))
    assert len(host.spoken) == 1


def test_a_transcript_match_is_labelled_as_one(host: _Host, tmp_path) -> None:
    folder = tmp_path / "podcast-transcripts"
    folder.mkdir()
    (folder / "t.txt").write_bytes(b"d\nd2\nWe walked across the Clifton suspension bridge.")
    host._find_box.value = "clifton"
    host._run_library_find()
    host._task_manager.run(0)
    assert host._shows_tree.rows == [
        (
            '"...We walked across the Clifton suspension bridge...." -- in the transcript of '
            "Bridges, The Daily",
            ("episode", "d\x00d2"),
        )
    ]
    assert host.spoken == ["1 match for clifton"]


def test_focusing_the_box_warms_the_indexes_once(host: _Host) -> None:
    host._find_box.SetFocus = lambda: None
    host._find_box.SelectAll = lambda: None
    host.focus_library_find()
    host.focus_library_find()
    assert [job["name"] for job in host._task_manager.jobs] == ["cast-library-index"]
    host._task_manager.run(0)
    assert host._library_search_index.stats()["episodes"] == 2


def test_a_feed_refresh_marks_its_podcast_stale_in_the_index(host: _Host) -> None:
    host._library_search_indexes()
    host._library_search_index.sync(host._podcast_library.shows)
    host._podcast_library.shows[0].episodes[1].title = "Bridges and tunnels"
    host.podcast_search_index_changed("d")
    assert host._library_search_index.sync(host._podcast_library.shows) == 1


def test_every_kind_of_row_says_what_it_is() -> None:
    from quill.core.podcasts.search_index import SearchHit

    hit = SearchHit("show_notes", "d", "The Daily", "d1", "Monday", "", "")
    assert hit_label(hit) == "Monday -- an episode of The Daily, mentioned in its show notes"
    note = SearchHit("note", "d", "The Daily", "d1", "Monday", "", "remember this")
    assert hit_label(note) == "Note on Monday: remember this"
    show = SearchHit("show", "d", "The Daily")
    assert hit_label(show, 3) == "The Daily -- a podcast (3 unheard)"
