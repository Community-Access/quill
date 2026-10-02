"""QUILL Lite's Activity (Shift+F9) and Repeat Last Result (F9), qc.md F-10 and F-01."""

from __future__ import annotations

import errno

import pytest

from quill.core import activity
from quill.ui import activity_window
from quill.ui.persistence_reporting import PersistenceReporter


@pytest.fixture(autouse=True)
def _fresh_log():
    activity.LOG.clear()
    yield
    activity.LOG.clear()


def test_f9_says_there_is_nothing_yet(lite_window) -> None:
    win = lite_window("hello", cursor=0)
    (lambda w: w.cmd_repeat_last_result())(win)
    assert win.announcements[-1].startswith("Nothing to repeat yet")


def test_f9_repeats_the_newest_important_result_and_what_activity_offers(lite_window) -> None:
    win = lite_window("hello", cursor=0)
    result = activity.ActionResult(
        "save",
        "QUILL Lite settings",
        activity.FAILED,
        "QUILL Lite settings could not be saved.",
        "The disk is full.",
        (activity.RETRY,),
        importance=activity.REVIEW,
    )
    activity_window.report_result(win, result, {"retry": lambda: "Saved."})
    assert win.announcements == []  # a review-only result is not spoken on arrival
    (lambda w: w.cmd_repeat_last_result())(win)
    assert win.announcements[-1] == (
        "QUILL Lite settings could not be saved. The disk is full. Activity offers Retry."
    )


def test_shift_f9_opens_the_shared_window(lite_window, monkeypatch) -> None:
    win = lite_window("hello", cursor=0)
    opened: list[object] = []
    monkeypatch.setattr("quill.apps.lite_window_activity.show_activity", opened.append)
    (lambda w: w.cmd_activity())(win)
    assert opened == [win]


def test_a_failed_settings_write_is_recorded_once_with_retry_and_open_folder(tmp_path) -> None:
    from quill.core.persistence_outcome import WriteOutcome

    class Host:
        said: list[str] = []

        def _announce(self, message: str) -> None:
            self.said.append(message)

    host = Host()
    reporter = PersistenceReporter(host, speak=True, call_after=lambda fn, arg: fn(arg))
    attempts: list[int] = []

    def retry() -> None:
        attempts.append(1)

    failure = WriteOutcome(
        "QUILL settings", tmp_path / "s.json", ok=False, reason="disk_full", retry=retry
    )
    reporter(failure)
    reporter(failure)  # the same file again within the minute: not said twice
    assert len(host.said) == 1
    assert host.said[0] == (
        "QUILL settings could not be saved. Your changes stay in use for this session. "
        "The disk is full."
    )
    latest = activity.LOG.recent()[0]
    assert [a.id for a in latest.next_actions] == ["retry", "open_folder"]
    assert activity_window.run_action(latest, "retry") == "Saved QUILL settings."
    assert attempts == [1]
    # A later success is said, so the failure is not believed in forever.
    reporter(WriteOutcome("QUILL settings", tmp_path / "s.json", ok=True))
    assert host.said[-1] == "QUILL settings saved now, after the earlier failure."
    # And a success with no earlier failure says nothing at all.
    reporter(WriteOutcome("QUILL settings", tmp_path / "s.json", ok=True))
    assert len(host.said) == 2


def test_an_action_that_raises_says_so_rather_than_crashing() -> None:
    result = activity.ActionResult(
        "x", "y", activity.FAILED, "Broke.", next_actions=(activity.RETRY,)
    )
    activity.LOG.record(result)

    def boom() -> str:
        raise OSError(errno.EACCES, "denied")

    activity_window.register_actions(result, {"retry": boom})
    assert activity_window.run_action(result, "retry").startswith("Retry did not work")
    assert (
        activity_window.run_action(result, "undo")
        == "undo is not available for this result any more."
    )
