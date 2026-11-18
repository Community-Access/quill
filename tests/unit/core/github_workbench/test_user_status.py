"""Your GitHub status (GitHub PRD 14.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from quill.core.github.user_status import UserStatus, clear_status, read_status, set_status


class FakeApi:
    def __init__(self, status: Any = None) -> None:
        self.status = status
        self.sent: list[dict[str, Any]] = []

    def graphql(self, query: str, variables: Any) -> Any:
        if query.lstrip().startswith("query"):
            return {"viewer": {"status": self.status}}
        self.sent.append(dict(variables))
        return {"changeUserStatus": {"status": {"message": variables.get("message")}}}

    def rest(self, *_a: Any, **_k: Any) -> Any:
        raise AssertionError


def test_the_status_is_read_in_words() -> None:
    status = read_status(
        FakeApi({
            "message": "On holiday :palm_tree:",
            "emoji": ":palm_tree:",
            "indicatesLimitedAvailability": True,
            "expiresAt": "2026-11-23T09:00:00Z",
        })
    )
    assert status.sentence == (
        "Your status: On holiday palm tree with palm tree and marked busy. "
        "It clears at 2026-11-23 09:00 UTC."
    )
    assert read_status(FakeApi(None)).sentence == "You have no status set."


def test_setting_sends_the_message_emoji_busy_and_when_it_clears() -> None:
    api = FakeApi()
    now = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
    said = set_status(
        api, "In a workshop", emoji="house", busy=True, clear_after=timedelta(hours=4), now=now
    )
    assert api.sent == [
        {
            "message": "In a workshop",
            "emoji": ":house:",
            "busy": True,
            "expires": "2026-11-18T14:00:00Z",
        }
    ]
    assert said.startswith("Your status is now: In a workshop with house and marked busy.")


def test_clearing() -> None:
    api = FakeApi()
    assert clear_status(api) == "Your status is cleared."
    assert api.sent == [{"message": None, "emoji": None, "busy": False, "expires": None}]
    assert UserStatus(busy=True).sentence == "Your status: no message and marked busy."
