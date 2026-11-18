"""Setting a commit status by hand."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.commit_status import CommitStatusError, set_commit_status
from quill.core.github.rest_transport import RestResponse


class FakeApi:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        return RestResponse(201, {}, {})

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_a_status_is_posted_with_its_name_words_and_link() -> None:
    api = FakeApi()
    said = set_commit_status(
        api, "o/r", "abc1234def", "failure", "lab tests", "2 failed", "https://lab/run/4"
    )
    assert said == "Set lab tests to failed on commit abc1234."
    assert api.sent == [
        (
            "POST",
            "/repos/o/r/statuses/abc1234def",
            {
                "state": "failure",
                "context": "lab tests",
                "description": "2 failed",
                "target_url": "https://lab/run/4",
            },
        )
    ]


def test_bad_states_and_links_are_refused_before_sending() -> None:
    api = FakeApi()
    with pytest.raises(CommitStatusError, match="not a state"):
        set_commit_status(api, "o/r", "a", "great", "x")
    with pytest.raises(CommitStatusError, match="https://"):
        set_commit_status(api, "o/r", "a", "success", "x", target_url="http://plain")
    assert api.sent == [] and CommitStatusError.code == "QUILL-GITHUB-COMMIT-STATUS"
    assert set_commit_status(api, "o/r", "abcdefg", "pending", " ").startswith("Set manual to")
