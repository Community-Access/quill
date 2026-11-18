"""Inbox rules for notifications: a condition and an action (GitHub PRD 22.12)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.github.explore_notifications import ExploreNotificationsMixin
from quill.core.github.inbox_rules import (
    InboxRule,
    apply_rules,
    load_rules,
    preview,
    save_rules,
)
from quill.core.github.notification_triage import NotificationInbox
from quill.core.github.notifications import GitHubNotification


def _note(i: str, repo: str, reason: str, kind: str, title: str, unread: bool = True) -> Any:
    return GitHubNotification(i, repo, reason, title, kind, unread)


NOTES = [
    _note("1", "octo/app", "subscribed", "PullRequest", "Bump lodash from 4 to 5"),
    _note("2", "octo/site", "mention", "Issue", "Broken link"),
    _note("3", "me/notes", "review_requested", "PullRequest", "Add a chapter"),
    _note("4", "octo/app", "subscribed", "Issue", "Crash", unread=False),
]


def test_a_rule_reads_as_a_sentence() -> None:
    rule = InboxRule("mark_done", repository="octo/*", subject="PullRequest", title_contains="Bump")
    assert rule.sentence == (
        "When a notification is from octo/*, about a pull request, with 'Bump' in its title: "
        "mark it done."
    )
    assert InboxRule("to_top", reason="mention").sentence == (
        "When a notification is because you were mentioned: move it to the top."
    )


def test_conditions_all_hold_and_globs_match_any_part() -> None:
    rule = InboxRule("mark_done", repository="OCTO/*", subject="PullRequest")
    assert [rule.matches(n) for n in NOTES] == [True, False, False, False]
    assert not InboxRule("mark_done").has_condition


def test_the_first_rule_that_fits_decides_and_nothing_is_sent() -> None:
    rules = [
        InboxRule("to_top", reason="mention"),
        InboxRule("mark_done", title_contains="bump"),
        InboxRule("mark_read", repository="octo/app"),
        InboxRule("mark_done"),  # no condition: ignored
    ]
    run = apply_rules(rules, NOTES)
    assert [n.id for n in run.kept] == ["2", "3", "4"]
    assert run.done == ["1"] and run.read == [] and run.to_top == 1
    assert run.sentence == "Inbox rules: 1 marked done, 1 moved to the top."
    assert apply_rules([], NOTES).sentence == ""


def test_mark_read_only_touches_unread() -> None:
    run = apply_rules([InboxRule("mark_read", repository="octo/app")], NOTES)
    assert run.read == ["1"]


def test_preview_says_what_it_would_do_to_today() -> None:
    said = preview(InboxRule("mark_done", repository="octo/*"), NOTES, show=2)
    assert said.startswith(
        "It matches 3 of the 4 notifications loaded today, and would mark them done:"
    )
    assert said.endswith("; and 1 more.")
    assert "matches none" in preview(InboxRule("mark_done", reason="assign"), NOTES)
    assert "no notifications loaded" in preview(InboxRule("mark_done", reason="x"), [])


def test_rules_are_kept_and_bad_entries_dropped(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    rules = [InboxRule("mark_done", repository="octo/*"), InboxRule("to_top", reason="mention")]
    save_rules(rules, path)
    assert load_rules(path) == rules
    path.write_text('{"rules": [{"action": "explode", "reason": "x"}, {"action": "mark_read"}]}')
    assert load_rules(path) == []
    assert load_rules(tmp_path / "missing.json") == []


class _Provider:
    is_authenticated = True

    def __init__(self, refuse: str = "") -> None:
        self.refuse = refuse
        self.sent: list[tuple[str, str]] = []

    def fetch_notification_inbox(self, **_kw: Any) -> NotificationInbox:
        return NotificationInbox(tuple(NOTES))

    def mark_notification_done(self, note_id: str) -> None:
        if note_id == self.refuse:
            raise RuntimeError("no")
        self.sent.append(("done", note_id))

    def mark_notification_read(self, note_id: str) -> None:
        self.sent.append(("read", note_id))


class _Client(ExploreNotificationsMixin):
    def __init__(self, provider: _Provider) -> None:
        self._provider = provider
        self._notification_init()


def test_rules_run_when_notifications_load(monkeypatch: Any) -> None:
    rules = [
        InboxRule("mark_done", title_contains="bump"),
        InboxRule("mark_read", reason="mention"),
    ]
    monkeypatch.setattr("quill.core.github.inbox_rules.load_rules", lambda: rules)
    provider = _Provider()
    client = _Client(provider)
    rows = client._fetch_notification_rows(include_read=True, limit=50)
    assert provider.sent == [("done", "1"), ("read", "2")]
    assert [row.key for row in rows] == ["2", "3", "4"]
    assert rows[0].label.startswith("Read,")
    assert client.inbox_rules_note == "Inbox rules: 1 marked done, 1 marked read."
    assert {n.id for n in client.loaded_notifications()} == {"2", "3", "4"}


def test_a_refused_write_keeps_the_notification_and_says_so(monkeypatch: Any) -> None:
    rules = [InboxRule("mark_done", repository="octo/app")]
    monkeypatch.setattr("quill.core.github.inbox_rules.load_rules", lambda: rules)
    client = _Client(_Provider(refuse="1"))
    rows = client._fetch_notification_rows(include_read=True, limit=50)
    assert {row.key for row in rows} == {"1", "2", "3"}
    assert client.inbox_rules_note == (
        "Inbox rules: 1 marked done. 1 could not be changed on GitHub."
    )
