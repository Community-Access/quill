"""Repository > Insights > Commit Activity: statistics as tables (GitHub PRD 14.2)."""

from __future__ import annotations

from typing import Any

from quill.core.github.conditional_requests import ConditionalResult
from quill.core.github.repo_activity import fetch_activity
from quill.core.github.rest_transport import GitHubRestError

WEEK = 1762646400  # 2025-11-09, a Sunday

STATS: dict[str, Any] = {
    "participation": {"all": [0] * 48 + [5, 10, 7, 8], "owner": [0] * 48 + [1, 2, 3, 4]},
    "commit_activity": [
        {"week": WEEK - 604800, "total": 0, "days": [0] * 7},
        {"week": WEEK, "total": 14, "days": [0, 3, 5, 2, 2, 2, 0]},
    ],
    "code_frequency": [[WEEK, 1204, -310]],
    "punch_card": [[2, 14, 23], [1, 9, 4], [0, 0, 0]],
    "contributors": [
        {"author": {"login": "sam"}, "total": 3, "weeks": [{"a": 10, "d": 2}]},
        {"author": {"login": "jeff"}, "total": 120, "weeks": [{"a": 3000, "d": 900}]},
    ],
}


def _reader(status: dict[str, int] | None = None, fail: str = "") -> Any:
    def read(path: str, _query: Any) -> ConditionalResult:
        name = path.rsplit("/", 1)[1]
        if name == fail:
            raise GitHubRestError("no", status=500)
        code = (status or {}).get(name, 200)
        return ConditionalResult(None if code in (202, 204) else STATS[name], False, code)

    return read


def test_every_statistic_reads_as_whole_sentences() -> None:
    warnings: list[str] = []
    rows = fetch_activity(None, "o/r", limit=10, warnings=warnings, get=_reader())
    labels = [row.label for row in rows]
    assert labels[0] == "o/r: commit activity in 8 rows, newest first."
    assert "Last 4 weeks: 30 commits, 10 by the owner." in labels
    assert labels[2] == "Commit activity, week of 2025-11-09: 14 commits. Busiest Tuesday, 5."
    assert labels[3] == "Commit activity, week of 2025-11-02: 0 commits."
    assert "Code frequency, week of 2025-11-09: 1,204 lines added, 310 removed." in labels
    assert "Busiest hour 1: Tuesdays at 14:00 UTC, 23 commits." in labels
    assert "Busiest hour 2: Mondays at 09:00 UTC, 4 commits." in labels
    assert labels[-2:] == [
        "Contributor jeff: 120 commits, 3,000 lines added, 900 removed.",
        "Contributor sam: 3 commits, 10 lines added, 2 removed.",
    ]
    assert all(row.kind == "insight" for row in rows) and warnings == []


def test_still_counting_is_said_and_a_failure_is_a_warning() -> None:
    warnings: list[str] = []
    rows = fetch_activity(
        None, "o/r", limit=10, warnings=warnings, get=_reader({"punch_card": 202}, "contributors")
    )
    assert rows[0].label.startswith("o/r: GitHub is still counting its statistics")
    assert not any(row.label.startswith("Busiest hour") for row in rows)
    assert len(warnings) == 1 and "contributors" in warnings[0]


def test_no_statistics_at_all_says_why() -> None:
    empty = dict.fromkeys(STATS, 204)
    rows = fetch_activity(None, "o/r", limit=10, warnings=[], get=_reader(empty))
    assert rows[0].label.startswith("o/r: no commit statistics.")
