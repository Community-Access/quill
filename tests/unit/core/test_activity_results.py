"""The family's result model (qc.md F-10): results, the log, progress, focus memory."""

from __future__ import annotations

import errno
from pathlib import Path

import pytest

from quill.core import activity, persistence_outcome
from quill.core.activity import (
    FAILED,
    OPEN_FOLDER,
    RETRY,
    REVIEW,
    ActionResult,
    ActivityLog,
    Progress,
    ProgressAnnouncer,
    restore_index,
    summary_sentence,
)


def _failed(summary: str = "Settings could not be saved.") -> ActionResult:
    return ActionResult(
        "save", "settings", FAILED, summary, "The disk is full.", (RETRY, OPEN_FOLDER)
    )


def test_a_result_renders_speech_row_and_details_from_one_record() -> None:
    result = _failed()
    assert result.spoken() == "Settings could not be saved. The disk is full."
    assert result.row().startswith("Failed: Settings could not be saved -- The disk is full. ")
    details = result.details_text()
    assert "Outcome: Failed" in details and "You can: Retry, Open Folder." in details
    assert result.is_problem and result.has("retry") and not result.has("undo")


def test_the_reason_is_not_said_twice() -> None:
    result = ActionResult("save", "x", FAILED, "Failed: the disk is full.", "The disk is full.")
    assert result.spoken() == "Failed: the disk is full."


def test_the_log_is_newest_first_bounded_and_repeats_only_what_matters() -> None:
    log = ActivityLog(limit=3)
    quiet = ActionResult(
        "refresh", "feeds", activity.COMPLETED, "Feeds checked.", importance=REVIEW
    )
    spoken = ActionResult("save", "doc", activity.COMPLETED, "Saved.")
    log.record(spoken)
    log.record(quiet)
    assert log.latest_important() is spoken  # a review-only success is not repeated
    problem = log.record(ActionResult("x", "y", FAILED, "Broke.", importance=REVIEW))
    assert log.latest_important() is problem  # but a problem always is
    for n in range(3):
        log.record(ActionResult("n", "n", activity.COMPLETED, f"{n}"))
    assert len(log.recent()) == 3 and log.recent()[0].summary == "2"
    assert log.find(problem.operation_id) is None  # evicted


def test_listeners_hear_every_result_and_a_bad_one_does_not_stop_the_rest() -> None:
    log = ActivityLog()
    heard: list[str] = []

    def bad(_result: ActionResult) -> None:
        raise RuntimeError("boom")

    log.subscribe(bad)
    stop = log.subscribe(lambda result: heard.append(result.summary))
    log.record(ActionResult("a", "b", activity.COMPLETED, "One."))
    stop()
    log.record(ActionResult("a", "b", activity.COMPLETED, "Two."))
    assert heard == ["One."]


def test_summary_sentences() -> None:
    assert summary_sentence([]) == "Nothing has happened yet in this session."
    assert summary_sentence([_failed(), _failed()]) == "2 results, 2 problems."


def test_progress_speaks_milestones_and_phase_changes_only() -> None:
    owner = object()
    announcer = ProgressAnnouncer(step=25, owner_token=owner)

    def at(n: int, phase: str = activity.DOWNLOADING) -> str | None:
        return announcer.next_sentence(
            Progress("op", phase, "Downloading", n, 100, owner_token=owner)
        )

    said = [at(n) for n in (0, 5, 10, 26, 30, 49, 51, 76, 99)]
    assert [s for s in said if s] == [
        "Downloading, 0 percent",
        "Downloading, 26 percent",
        "Downloading, 51 percent",
        "Downloading, 76 percent",
    ]
    assert at(80, activity.WRITING) == "Downloading, 80 percent"  # a new phase is said
    assert at(100, activity.WRITING) == "Downloading, 100 percent"
    assert at(100, activity.WRITING) is None  # finished: never again


def test_a_stale_owner_cannot_announce() -> None:
    announcer = ProgressAnnouncer(owner_token=object())
    stale = Progress("op", activity.READING, "Reading", 50, 100, owner_token=object())
    assert announcer.next_sentence(stale) is None


@pytest.mark.parametrize(
    ("keys", "wanted", "previous", "expected"),
    [
        (["a", "b", "c"], "c", 0, 2),  # by identity, wherever it moved
        (["a", "c"], "b", 1, 1),  # gone: the row that moved into its place
        (["a"], "b", 4, 0),  # gone and the list shrank: the last row
        ([], "a", 0, -1),
        (["a", "b"], None, -1, 0),
    ],
)
def test_focus_returns_by_identity(keys, wanted, previous, expected) -> None:
    assert restore_index(keys, wanted, previous) == expected


# -- truthful writes -------------------------------------------------------------------


def test_a_guarded_write_reports_success_and_failure_and_still_raises(tmp_path: Path) -> None:
    heard: list[persistence_outcome.WriteOutcome] = []
    stop = persistence_outcome.subscribe(heard.append)
    try:
        persistence_outcome.guarded_write("notes", tmp_path / "a.json", lambda: None)

        def full() -> None:
            raise OSError(errno.ENOSPC, "No space left on device")

        with pytest.raises(OSError):
            persistence_outcome.guarded_write("notes", tmp_path / "a.json", full)
    finally:
        stop()
    assert [o.ok for o in heard] == [True, False]
    failure = heard[1]
    assert failure.reason == persistence_outcome.DISK_FULL
    assert failure.reason_sentence == "The disk is full."
    assert failure.retry is not None
    with pytest.raises(OSError):
        failure.retry()  # retries through the same guard


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (PermissionError(errno.EACCES, "denied"), persistence_outcome.DENIED),
        (FileNotFoundError(errno.ENOENT, "gone"), persistence_outcome.MISSING_FOLDER),
        (OSError(errno.EROFS, "ro"), persistence_outcome.READ_ONLY),
        (OSError(errno.EIO, "io"), persistence_outcome.OTHER),
    ],
)
def test_reasons_are_stable_codes(error: OSError, reason: str) -> None:
    assert persistence_outcome.reason_for(error) == reason


def test_the_real_settings_writers_report_through_the_guard(tmp_path, monkeypatch) -> None:
    """Each shared writer -- QUILL's settings, both apps' histories, the library --
    reports a failed write, so no call site can fail silently again."""
    from quill.core import storage
    from quill.core.podcasts import history as cast_history
    from quill.core.podcasts import subscriptions
    from quill.core.radio import history as radio_history

    def refuse(*_args, **_kwargs):
        raise PermissionError(errno.EACCES, "denied")

    heard: list[str] = []
    stop = persistence_outcome.subscribe(lambda o: heard.append(o.what))
    monkeypatch.setattr(storage, "write_json_atomic", refuse)
    try:
        for save in (
            lambda: radio_history.save_history(tmp_path, radio_history.RadioHistory()),
            lambda: cast_history.save_history(tmp_path, cast_history.PodcastHistory()),
            lambda: subscriptions.save_library(tmp_path, subscriptions.PodcastLibrary()),
        ):
            with pytest.raises(OSError):
                save()
    finally:
        stop()
    assert heard == ["Quill Radio's settings", "QUILL Cast's settings", "your podcast library"]
