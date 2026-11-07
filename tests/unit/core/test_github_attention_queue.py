"""Local state for the cross-repository attention queue."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from quill.core.github.attention_queue import GitHubAttentionQueue


def _queue(tmp_path: Path, account: str = "alice") -> GitHubAttentionQueue:
    return GitHubAttentionQueue.load(account, tmp_path / "attention.json")


def test_queue_preferences_and_saved_filters_are_account_scoped(tmp_path: Path) -> None:
    path = tmp_path / "attention.json"
    queue = GitHubAttentionQueue.load("Alice", path)
    queue.set_repositories(["Org/One", "org/one", "Org/Two"])
    queue.set_categories(["assigned", "failed_checks"])
    assert queue.save_filter("Build failures")
    queue.save()

    other_account = GitHubAttentionQueue.load("Bob", path)
    assert other_account.repositories == []
    assert len(other_account.categories) == 4

    restored = GitHubAttentionQueue.load("ALICE", path)
    assert restored.repositories == ["Org/One", "Org/Two"]
    assert restored.categories == ["assigned", "failed_checks"]
    assert restored.apply_filter("build failures")
    assert restored.repositories == ["Org/One", "Org/Two"]
    assert restored.remove_filter("BUILD FAILURES")
    assert not GitHubAttentionQueue.load("Alice", path).filters


def test_repository_scope_rejects_invalid_names_and_too_many_repositories(
    tmp_path: Path,
) -> None:
    queue = _queue(tmp_path)
    queue.set_repositories(["owner/repo", "OWNER/REPO"])
    assert queue.repositories == ["owner/repo"]

    try:
        queue.set_repositories([f"owner/repo{i}" for i in range(11)])
    except ValueError as exc:
        assert "no more than 10" in str(exc)
    else:
        raise AssertionError("an oversized queue scope should be rejected")

    try:
        queue.set_repositories(["not a repository"])
    except ValueError as exc:
        assert "owner/repo" in str(exc)
    else:
        raise AssertionError("invalid repository names should be rejected")


def test_snoozes_expire_and_can_be_cleared_locally(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    now = datetime(2026, 11, 6, tzinfo=UTC)
    queue.snooze("https://github.com/o/r/issues/7", now + timedelta(days=1))
    assert queue.is_snoozed("https://github.com/o/r/issues/7", now=now)
    assert not queue.is_snoozed("https://github.com/o/r/issues/7", now=now + timedelta(days=1))
    assert not queue.snoozed

    queue.snooze("https://github.com/o/r/issues/8", now + timedelta(days=1))
    assert queue.unsnooze("https://github.com/o/r/issues/8")
    assert not queue.unsnooze("https://github.com/o/r/issues/8")


def test_last_visit_only_marks_items_updated_after_the_previous_visit(
    tmp_path: Path,
) -> None:
    queue = _queue(tmp_path)
    queue.mark_visited(datetime(2026, 11, 5, tzinfo=UTC))
    assert queue.changed_since_last_visit("2026-11-06T00:00:00+00:00")
    assert not queue.changed_since_last_visit("2026-11-04T00:00:00+00:00")
    assert not queue.changed_since_last_visit("unknown")


def test_corrupt_queue_file_degrades_to_default_preferences(tmp_path: Path) -> None:
    target = tmp_path / "attention.json"
    target.write_text("not json", encoding="utf-8")
    queue = GitHubAttentionQueue.load("alice", target)
    assert not queue.repositories
    assert len(queue.categories) == 4
    assert not queue.filters
