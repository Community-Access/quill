"""Hiding a comment, and showing it again (GitHub PRD 14.2)."""

from __future__ import annotations

from typing import Any

from quill.core.github.comment_moderation import REASONS, hide_comment, show_comment
from quill.core.github.timeline import timeline_entry


class FakeApi:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []

    def graphql(self, query: str, variables: Any) -> Any:
        name = "unminimize" if "unminimizeComment" in query else "minimize"
        self.sent.append((name, dict(variables)))
        return {}

    def rest(self, *_a: Any, **_k: Any) -> Any:
        raise AssertionError


def test_hiding_sends_the_reason_and_says_it_is_not_deleted() -> None:
    api = FakeApi()
    said = hide_comment(api, "IC_1", "OFF_TOPIC")
    assert said.startswith("Hid the comment as off topic.") and "not deleted" in said
    assert api.sent == [("minimize", {"id": "IC_1", "why": "OFF_TOPIC"})]
    assert show_comment(api, "IC_1") == "The comment shows again."
    assert api.sent[-1] == ("unminimize", {"id": "IC_1"})
    assert [code for _label, code in REASONS] == [
        "SPAM", "ABUSE", "OFF_TOPIC", "OUTDATED", "DUPLICATE", "RESOLVED",
    ]  # fmt: skip


def test_a_comment_in_the_timeline_carries_its_id_and_other_events_do_not() -> None:
    comment = timeline_entry({
        "event": "commented",
        "node_id": "IC_9",
        "user": {"login": "ann"},
        "body": "Hi",
    })
    label = timeline_entry({"event": "labeled", "label": {"name": "bug"}, "node_id": "LE_1"})
    assert comment is not None and comment.node_id == "IC_9"
    assert label is not None and label.node_id == ""
