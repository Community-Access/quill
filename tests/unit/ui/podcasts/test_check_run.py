"""qc.md F-10: Refresh All Now finishes out loud, once, and F9 can repeat it."""

from __future__ import annotations

from quill.core import activity
from quill.ui.podcasts import check_run


class _Host:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.retried = 0

    def _announce(self, message: str, **_kw: object) -> None:
        self.said.append(message)

    def _on_check_all_feeds(self) -> None:
        self.retried += 1


def test_a_run_says_milestones_and_one_result(monkeypatch) -> None:
    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda *_a, **_k: False)
    host = _Host()
    ids = [f"s{i}" for i in range(4)]
    check_run.start(host, ids)
    check_run.step(host, "s0", new_episodes=2)
    check_run.step(host, "elsewhere", new_episodes=9)  # not part of this run
    check_run.step(host, "s1")
    check_run.step(host, "s2", failed_title="Broken Feed")
    assert host.said == [
        "Checking feeds, 25 percent",
        "Checking feeds, 50 percent",
        "Checking feeds, 75 percent",
    ]
    check_run.step(host, "s3", new_episodes=1)
    assert (
        host.said[-1]
        == "Checked 4 feeds: 3 new episodes from 2 podcasts. 1 could not be read: Broken Feed."
    )
    latest = activity.LOG.latest_important()
    assert latest is not None and latest.has("retry")
    assert host._check_run is None


def test_nothing_new_is_said_as_such() -> None:
    run = check_run.CheckRun(total=2)
    assert check_run.finish_sentence(run) == "Checked 2 feeds: nothing new."
