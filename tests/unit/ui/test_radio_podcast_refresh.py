"""Quill Radio checking its subscribed feeds on its own.

The monitor decides four things, and each of them has already been wrong once:

* **What counts as something to say.** ``refresh_subscribed_feeds`` returns a
  row for every show it *checked*, not every show that gained an episode, so
  "did anything happen?" is the sum of the counts. Testing the list instead
  meant the automatic check announced "No new episodes." every fifteen minutes
  to anybody with at least one subscription -- reported by Jeff on 2026-08-24,
  within minutes of it being wired up. The first test below is that bug.
* **Whether a forced check honours the pause.** It must not: Refresh is the
  keystroke that proves a pause is not a trap.
* **Whether a forced check defers to the other app's stamp.** It must not: a
  key somebody pressed is not a timer firing.
* **Whether "the other app just did this" is the same as "nothing new".** It is
  not, which is why the worker returns ``None`` rather than an empty list, and
  why ``None`` is silent.

The monitor is exercised through a fake task manager that runs its work inline,
so no thread, no wx timer and no network are involved.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.ui.radio import podcast_refresh

wx = pytest.importorskip("wx")

said: list[str] = []


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture(autouse=True)
def _clear_said():
    said.clear()
    yield
    said.clear()


@pytest.fixture
def frame():
    window = wx.Frame(None)
    yield window
    window.Destroy()


class _Tasks:
    """Runs the submitted work inline and routes its result like the real one."""

    def __init__(self) -> None:
        self.submitted: list[str] = []

    def submit(self, name, work, *, on_success=None, on_failure=None):  # noqa: ANN001
        self.submitted.append(name)
        try:
            result = work()
        except Exception as error:  # noqa: BLE001 - mirrors the task manager
            if on_failure is not None:
                on_failure(name, error)
            return None
        if on_success is not None:
            on_success(name, result)
        return result


class _History:
    def __init__(self, minutes: int = 0, on_launch: bool = False) -> None:
        self.podcast_refresh_minutes = minutes
        self.podcast_refresh_on_launch = on_launch


def _monitor(frame, history: _History, tasks: _Tasks, *, safe_mode: bool = False):
    return podcast_refresh.PodcastRefreshMonitor(
        frame,
        history_provider=lambda: history,
        announce=said.append,
        task_manager=tasks,
        safe_mode=safe_mode,
        wx=wx,
    )


# -- the announcement bug -------------------------------------------------------


def test_a_quiet_automatic_check_says_nothing_at_all(frame, monkeypatch) -> None:
    """Reported 2026-08-24: it announced the autorefresh every fifteen minutes.

    Two subscriptions, neither with a new episode. The worker returns a row for
    each -- ``[("The Daily", 0), ("Main Menu", 0)]`` -- which is emphatically
    not an empty list, and so the check said "No new episodes." into somebody's
    afternoon four times an hour.
    """
    monkeypatch.setattr(
        podcast_refresh,
        "refresh_subscribed_feeds",
        lambda **_kwargs: [("The Daily", 0), ("Main Menu", 0)],
    )
    tasks = _Tasks()
    monitor = _monitor(frame, _History(minutes=15), tasks)

    monitor.check_now(announce_when_empty=False)

    assert tasks.submitted == ["radio-podcast-refresh"]
    assert said == []


def test_a_check_that_found_something_still_speaks(frame, monkeypatch) -> None:
    monkeypatch.setattr(
        podcast_refresh,
        "refresh_subscribed_feeds",
        lambda **_kwargs: [("The Daily", 2), ("Main Menu", 0)],
    )
    monitor = _monitor(frame, _History(minutes=15), _Tasks())

    monitor.check_now(announce_when_empty=False)

    assert said and "The Daily" in said[0]


def test_a_check_somebody_asked_for_answers_even_when_it_found_nothing(frame, monkeypatch) -> None:
    """Silence is an answer to a timer. It is not an answer to a keystroke."""
    monkeypatch.setattr(
        podcast_refresh, "refresh_subscribed_feeds", lambda **_kwargs: [("The Daily", 0)]
    )
    monitor = _monitor(frame, _History(minutes=15), _Tasks())

    monitor.check_now()

    assert said == ["No new episodes."]


def test_the_other_app_having_just_checked_is_silent_not_nothing_new(frame, monkeypatch) -> None:
    """``None`` and ``[]`` are different facts; only one is worth saying."""
    monkeypatch.setattr(podcast_refresh, "refresh_subscribed_feeds", lambda **_kwargs: None)
    monitor = _monitor(frame, _History(minutes=15), _Tasks())

    monitor.check_now()

    assert said == []


# -- force ----------------------------------------------------------------------


def test_a_forced_check_ignores_the_shared_stamp(frame, monkeypatch) -> None:
    seen: dict[str, Any] = {}

    def _fake(**kwargs: Any):
        seen.update(kwargs)
        return []

    monkeypatch.setattr(podcast_refresh, "refresh_subscribed_feeds", _fake)
    monitor = _monitor(frame, _History(minutes=60), _Tasks())

    monitor.check_now(force=True)

    assert seen["force"] is True
    assert seen["only_if_due_minutes"] is None


def test_an_automatic_check_defers_to_the_shared_stamp(frame, monkeypatch) -> None:
    seen: dict[str, Any] = {}

    def _fake(**kwargs: Any):
        seen.update(kwargs)
        return []

    monkeypatch.setattr(podcast_refresh, "refresh_subscribed_feeds", _fake)
    monitor = _monitor(frame, _History(minutes=60), _Tasks())

    monitor.check_now(announce_when_empty=False)

    assert seen["force"] is False
    assert seen["only_if_due_minutes"] == 60


# -- policy ---------------------------------------------------------------------


def test_safe_mode_says_so_rather_than_failing_quietly(frame) -> None:
    tasks = _Tasks()
    monitor = _monitor(frame, _History(minutes=15), tasks, safe_mode=True)

    assert monitor.check_now() is False
    assert tasks.submitted == []
    assert said == ["Subscribed feeds are not checked in Safe Mode."]


def test_manually_only_starts_no_timer(frame) -> None:
    monitor = _monitor(frame, _History(minutes=0), _Tasks())
    assert monitor.apply() is False
    monitor.stop()


def test_a_cadence_starts_a_timer_and_apply_can_stop_it_again(frame) -> None:
    history = _History(minutes=15)
    monitor = _monitor(frame, history, _Tasks())

    assert monitor.apply() is True
    history.podcast_refresh_minutes = 0
    assert monitor.apply() is False
    monitor.stop()


def test_nothing_runs_at_launch_unless_asked(frame) -> None:
    monitor = _monitor(frame, _History(minutes=15, on_launch=False), _Tasks())
    assert monitor.start_if_asked_at_launch() is False


def test_the_launch_check_is_quiet_when_it_finds_nothing(frame, monkeypatch) -> None:
    """A launch is not the moment to be told that nothing happened."""
    monkeypatch.setattr(
        podcast_refresh, "refresh_subscribed_feeds", lambda **_kwargs: [("The Daily", 0)]
    )
    monitor = _monitor(frame, _History(minutes=15, on_launch=True), _Tasks())

    assert monitor.start_if_asked_at_launch() is True
    assert said == []


def test_a_broken_check_is_written_down_as_well_as_spoken(frame, monkeypatch) -> None:
    """A check that broke at 3 a.m. is what Recent Problems exists to keep."""
    from quill.core import problem_log

    recorded: list[tuple] = []
    monkeypatch.setattr(problem_log, "record_problem", lambda *args: recorded.append(args))

    def _boom(**_kwargs: Any):
        raise RuntimeError("the feed host is down")

    monkeypatch.setattr(podcast_refresh, "refresh_subscribed_feeds", _boom)
    monitor = _monitor(frame, _History(minutes=15), _Tasks())

    monitor.check_now()

    assert recorded and recorded[0][1] == problem_log.KIND_FEED
    assert said and "could not be checked" in said[0]


def test_the_policy_reads_back_as_one_sentence(frame) -> None:
    monitor = _monitor(frame, _History(minutes=60, on_launch=True), _Tasks())
    policy = monitor.describe()
    assert "hour" in policy.lower()
    assert "launch" in policy.lower()
