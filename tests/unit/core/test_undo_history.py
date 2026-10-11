"""qc.md section 18 item 12: Undo History keeps ten steps; Ctrl+Z is still once."""

from __future__ import annotations

from quill.core.undo_last import HISTORY_LIMIT, UndoableAction, UndoHistory


def _step(name: str, log: list[str], disposed: list[str]) -> UndoableAction:
    return UndoableAction(
        verb="Unfollow",
        subject=name,
        restores="",
        undo=lambda: log.append(name),
        dispose=lambda: disposed.append(name),
    )


def test_ctrl_z_takes_the_newest_and_the_list_keeps_the_rest() -> None:
    log: list[str] = []
    disposed: list[str] = []
    history = UndoHistory()
    for name in ("a", "b", "c"):
        history.remember(_step(name, log, disposed))
    assert [s.subject for s in history.entries()] == ["c", "b", "a"]
    assert history.take().subject == "c"
    assert history.peek().subject == "b"
    assert disposed == []


def test_an_older_step_can_be_undone_alone() -> None:
    history = UndoHistory()
    for name in ("a", "b", "c"):
        history.remember(_step(name, [], []))
    assert history.take_at(2).subject == "a"
    assert [s.subject for s in history.entries()] == ["c", "b"]


def test_the_eleventh_step_disposes_of_the_oldest() -> None:
    disposed: list[str] = []
    history = UndoHistory()
    for index in range(HISTORY_LIMIT + 1):
        history.remember(_step(str(index), [], disposed))
    assert len(history.entries()) == HISTORY_LIMIT
    assert disposed == ["0"]


def test_a_failed_older_preparation_keeps_its_place_behind_newer_work() -> None:
    history = UndoHistory()
    for name in ("a", "b", "c"):
        history.remember(_step(name, [], []))
    older = history.entries()[2:]
    action = history.take_at(1)
    assert action is not None
    history.remember(_step("d", [], []))
    history.restore_failed(action, older=older)
    assert [entry.subject for entry in history.entries()] == ["d", "c", "b", "a"]


def test_returning_a_retry_to_a_full_history_retains_it_without_growing() -> None:
    history = UndoHistory()
    action = _step("retry", [], [])
    for index in range(HISTORY_LIMIT):
        history.remember(_step(str(index), [], []))
    history.restore_failed(action, older=[])
    assert len(history.entries()) == HISTORY_LIMIT
    assert history.entries()[-1] is action
