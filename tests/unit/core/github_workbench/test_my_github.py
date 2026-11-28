"""My GitHub: queue assembly, filter, sort, group, the spoken sentences, and the saved choices."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.github.explore_models import ExploreRow
from quill.core.github.my_github import (
    assemble,
    changes_sentence,
    empty_sentence,
    group_counts_sentence,
    present,
    refine,
    summary_sentence,
)
from quill.core.github.my_github_prefs import MyGitHubPrefs, load_prefs, save


def _note(note_id, repo, title, when, *, unread=True, number=0):
    state = "Unread" if unread else "Read"
    url = f"https://api.github.com/repos/{repo}/issues/{number}" if number else ""
    return ExploreRow(
        f"{state}, mention: {repo} - {title}",
        f"Issue: {title}\nRepository: {repo}\nWhy you got it: you were mentioned\n"
        f"{state}. Updated: {when}\n{url}",
        url,
        repo,
        "notification",
        note_id,
        when,
        title,
    )


def _search(repo, number, title, source, when, *, pr=False):
    kind = "pr" if pr else "issue"
    url = f"https://github.com/{repo}/{'pull' if pr else 'issues'}/{number}"
    return ExploreRow(
        f"{repo} #{number}: {title} ({kind})",
        f"{source}\n{repo} #{number}\nState: open\nUpdated: {when}\n{url}",
        url,
        repo,
        kind,
        str(number),
        when,
        title,
    )


def _build(notes=(), found=(), *, note_fails=False, found_fails=False, note=""):
    def read_notes():
        if note_fails:
            raise RuntimeError("GitHub is not answering")
        return list(notes)

    def read_found():
        if found_fails:
            raise RuntimeError("search rate limit")
        return list(found)

    return assemble(notifications=read_notes, attention=read_found, attention_note=lambda: note)


NOTES = [
    _note("1", "octo/app", "Crash on save", "2026-11-20T10:00:00Z", number=5),
    _note("2", "octo/web", "Docs typo", "2026-11-22T10:00:00Z", number=9),
    _note("3", "octo/app", "Old thread", "2026-11-01T10:00:00Z", unread=False, number=2),
]
FOUND = [
    _search("octo/web", 40, "Add search", "Assigned", "2026-11-21T10:00:00Z"),
    _search("octo/api", 7, "Retry logic", "Review requested", "2026-11-23T10:00:00Z", pr=True),
    _search("octo/api", 8, "Fix build", "Failed checks", "2026-11-19T10:00:00Z", pr=True),
]


def test_queue_holds_every_source_with_kind_repository_title_reason_and_time() -> None:
    queue = _build(NOTES, FOUND)
    assert not queue.failures
    by_title = {item.title: item for item in queue.items}
    assert by_title["Crash on save"].kind == "notification"
    assert by_title["Crash on save"].reason == "you were mentioned"
    assert by_title["Add search"].kind == "assigned"
    assert by_title["Add search"].reason == "Assigned to you"
    assert by_title["Retry logic"].kind == "review_request"
    assert by_title["Fix build"].kind == "my_pull_request"
    assert by_title["Fix build"].reason == "Its checks failed"
    assert by_title["Retry logic"].repository == "octo/api"
    assert by_title["Retry logic"].updated_at == "2026-11-23T10:00:00Z"


def test_a_review_request_wins_over_assigned_and_keeps_the_other_reason() -> None:
    row = _search("octo/api", 7, "Retry", "Also: Assigned, Review requested", "2026-11-23", pr=True)
    (item,) = _build(found=[row]).items
    assert item.kind == "review_request"
    assert item.reason == "Assigned to you"  # first source named; the rest in `also`
    assert "your review was requested" in item.also


def test_mentioned_only_rows_are_not_in_the_queue() -> None:
    row = _search("octo/api", 7, "Retry", "Mentioned", "2026-11-23")
    assert _build(found=[row]).items == ()


def test_a_failing_source_is_named_and_the_other_still_shows() -> None:
    queue = _build(NOTES, FOUND, note_fails=True)
    assert [f.source for f in queue.failures] == ["Notifications"]
    assert queue.failures[0].sentence == "Notifications could not load: GitHub is not answering."
    assert {item.kind for item in queue.items} == {"assigned", "review_request", "my_pull_request"}
    queue = _build(NOTES, FOUND, found_fails=True)
    assert [f.source for f in queue.failures] == ["Assigned issues and review requests"]
    assert {item.kind for item in queue.items} == {"notification"}


def test_both_sources_failing_gives_no_items_and_two_failures() -> None:
    queue = _build(NOTES, FOUND, note_fails=True, found_fails=True)
    assert queue.items == ()
    assert len(queue.failures) == 2


def test_the_attention_reads_own_warning_is_carried_as_a_note() -> None:
    queue = _build(found=FOUND, note="Attention queue: showing the first 50 items")
    assert queue.notes == ("Attention queue: showing the first 50 items",)


def test_a_thread_in_both_sources_is_one_row_with_both_reasons() -> None:
    notes = [_note("9", "octo/web", "Add search", "2026-11-24T10:00:00Z", number=40)]
    found = [_search("octo/web", 40, "Add search", "Assigned", "2026-11-21T10:00:00Z")]
    queue = _build(notes, found)
    assert len(queue.items) == 1
    item = queue.items[0]
    assert item.kind == "notification"  # keeps Mark Read and Done working
    assert "Assigned to you" in item.also
    assert item.updated_at == "2026-11-24T10:00:00Z"


def test_default_order_is_newest_first() -> None:
    items = refine(_build(NOTES, FOUND).items, MyGitHubPrefs())
    assert [i.updated_at for i in items] == sorted((i.updated_at for i in items), reverse=True)


def test_oldest_and_by_repository_sorting() -> None:
    queue = _build(NOTES, FOUND)
    oldest = refine(queue.items, MyGitHubPrefs(sort="oldest"))
    assert [i.updated_at for i in oldest] == sorted(i.updated_at for i in oldest)
    by_repo = refine(queue.items, MyGitHubPrefs(sort="repository"))
    repos = [i.repository for i in by_repo]
    assert repos == sorted(repos)
    within_api = [i.updated_at for i in by_repo if i.repository == "octo/api"]
    assert within_api == sorted(within_api, reverse=True)  # newest first inside a repository


def test_filter_by_kind_repository_and_unread() -> None:
    queue = _build(NOTES, FOUND)
    only_reviews = refine(queue.items, MyGitHubPrefs(kinds=("review_request",)))
    assert [i.title for i in only_reviews] == ["Retry logic"]
    one_repo = refine(queue.items, MyGitHubPrefs(repository="OCTO/api"))
    assert {i.repository for i in one_repo} == {"octo/api"}
    unread = refine(queue.items, MyGitHubPrefs(unread_only=True))
    assert "Old thread" not in {i.title for i in unread}
    # GitHub gives assignments and review requests no read state: never hidden as read.
    assert {"Add search", "Retry logic", "Fix build"} <= {i.title for i in unread}


def test_group_by_repository_and_by_kind_keep_a_group_together() -> None:
    queue = _build(NOTES, FOUND)
    grouped = refine(queue.items, MyGitHubPrefs(group="repository"))
    repos = [i.repository for i in grouped]
    assert repos == sorted(repos)
    by_kind = refine(queue.items, MyGitHubPrefs(group="kind"))
    assert [i.kind for i in by_kind] == [
        "notification",
        "notification",
        "notification",
        "assigned",
        "review_request",
        "my_pull_request",
    ]
    assert group_counts_sentence(grouped, "repository") == (
        "Grouped by repository: octo/api 2, octo/app 2, octo/web 2."
    )
    assert group_counts_sentence(grouped, "none") == ""


def test_counts_are_spoken_by_kind() -> None:
    sentence = summary_sentence(_build([NOTES[0], NOTES[1]], [FOUND[0], FOUND[1]]).items)
    assert sentence == (
        "4 need your attention: 2 unread notifications, 1 assigned issue, 1 review request."
    )


def test_one_item_uses_the_singular_verb() -> None:
    assert summary_sentence(_build(found=[FOUND[1]]).items) == (
        "1 needs your attention: 1 review request."
    )


def test_an_empty_queue_says_so_in_one_sentence() -> None:
    assert summary_sentence(()) == "Nothing needs your attention."
    assert empty_sentence() == "Nothing needs your attention."


def test_an_empty_view_caused_by_the_filter_says_what_was_hidden() -> None:
    assert empty_sentence(hidden=1) == "Nothing shows with your filters; 1 item is hidden."
    assert empty_sentence(hidden=6) == "Nothing shows with your filters; 6 items are hidden."


def test_refresh_says_what_changed_once() -> None:
    first = _build(NOTES[:2], FOUND[:1]).items
    assert changes_sentence(None, first) == ""  # the first load only reports the count
    previous = frozenset(i.key for i in first)
    later = _build(NOTES[:1], FOUND).items
    assert changes_sentence(previous, later) == "2 new, 1 cleared since the last refresh."
    assert changes_sentence(previous, first) == "No changes since the last refresh."


def test_the_list_row_keeps_the_original_for_the_workbenchs_own_actions() -> None:
    (item,) = _build([NOTES[0]]).items
    row = present(item)
    assert (row.kind, row.key, row.url, row.repo) == (
        "notification",
        "1",
        NOTES[0].url,
        "octo/app",
    )
    assert row.label.startswith("Notification, unread: octo/app - Crash on save")
    assert "Why it is here: you were mentioned" in row.detail
    assert "Read state: Unread" in row.detail


def test_an_assigned_row_never_claims_a_read_state() -> None:
    (item,) = _build(found=[FOUND[0]]).items
    row = present(item)
    assert "unread" not in row.label.lower()
    assert "Read state" not in row.detail


def test_choices_persist_per_account(tmp_path: Path) -> None:
    path = tmp_path / "mine.json"
    chosen = MyGitHubPrefs(
        kinds=("assigned", "review_request"),
        repository="octo/app",
        unread_only=True,
        sort="repository",
        group="kind",
    )
    save("Alice", chosen, path)
    save("bob", MyGitHubPrefs(sort="oldest"), path)
    assert load_prefs("alice", path) == chosen
    assert load_prefs("BOB", path).sort == "oldest"
    assert load_prefs("carol", path) == MyGitHubPrefs()


@pytest.mark.parametrize(
    "junk", ["not json", "[]", '{"accounts": {"a": {"sort": 4, "kinds": "x"}}}']
)
def test_a_damaged_file_reads_as_the_defaults(tmp_path: Path, junk: str) -> None:
    path = tmp_path / "mine.json"
    path.write_text(junk, encoding="utf-8")
    assert load_prefs("a", path) == MyGitHubPrefs()


def test_naming_every_kind_is_the_same_as_naming_none(tmp_path: Path) -> None:
    path = tmp_path / "mine.json"
    every = ("notification", "assigned", "review_request", "my_pull_request")
    save("a", MyGitHubPrefs(kinds=every), path)
    assert load_prefs("a", path).kinds == ()
