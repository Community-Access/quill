"""11.5 wiring: Retry is registered by kind, so a row outlives its session.

A stored callback could not survive a restart; the log does. So the window
looks its handler up by the row's ``kind`` at the moment Retry is pressed,
and a row nothing claims says so rather than pretending.
"""

from __future__ import annotations

import pytest

from quill.core import problem_log
from quill.ui import problems_dialog


@pytest.fixture(autouse=True)
def _no_handlers() -> object:
    problems_dialog.clear_retries()
    yield
    problems_dialog.clear_retries()


def _problem(kind: str = problem_log.KIND_FEED) -> problem_log.Problem:
    return problem_log.Problem(kind=kind, subject="The Daily", reason="404", target="show-1")


def test_a_row_no_handler_claims_cannot_be_retried() -> None:
    assert problems_dialog.can_retry(_problem()) is False
    assert problems_dialog.can_retry(None) is False


def test_a_registered_handler_claims_its_kind_and_says_the_outcome() -> None:
    seen: list[str] = []

    def _handler(problem: problem_log.Problem) -> str:
        seen.append(problem.target)
        return f"Refreshing {problem.subject}..."

    problems_dialog.register_retry(problem_log.KIND_FEED, _handler)
    assert problems_dialog.can_retry(_problem()) is True
    assert problems_dialog.retry(_problem()) == "Refreshing The Daily..."
    assert seen == ["show-1"]


def test_registering_twice_replaces_rather_than_stacks() -> None:
    problems_dialog.register_retry(problem_log.KIND_FEED, lambda _p: "first")
    problems_dialog.register_retry(problem_log.KIND_FEED, lambda _p: "second")
    assert problems_dialog.retry(_problem()) == "second"


def test_a_handler_that_raises_says_so_rather_than_taking_the_window_down() -> None:
    def _boom(_problem: problem_log.Problem) -> str:
        raise OSError("the feed host is unreachable")

    problems_dialog.register_retry(problem_log.KIND_FEED, _boom)
    assert problems_dialog.retry(_problem()) == (
        "Could not retry The Daily: the feed host is unreachable."
    )


def test_an_unclaimed_kind_refuses_in_words() -> None:
    assert problems_dialog.retry(_problem(problem_log.KIND_STREAM)) == (
        "Nothing here can retry a stream problem."
    )


def test_a_silent_handler_still_produces_a_sentence() -> None:
    problems_dialog.register_retry(problem_log.KIND_FEED, lambda _p: "")
    assert problems_dialog.retry(_problem()) == "Retrying The Daily."


def test_both_apps_register_the_kinds_they_record() -> None:
    """The kinds each app writes must be the kinds it can retry, or a row is
    recorded that its own app cannot act on."""
    from pathlib import Path

    radio = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "radio" / "problem_retries.py"
    ).read_text(encoding="utf-8")
    cast = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "podcasts" / "problem_retries.py"
    ).read_text(encoding="utf-8")
    assert "KIND_STREAM" in radio and "KIND_DOWNLOAD" in radio
    assert "KIND_FEED" in cast and "KIND_DOWNLOAD" in cast
