"""GitHub Workbench Phase 13 (PRD 22.2, 22.3, 22.5): Watches, Read as Document, API Console.

The wx-free halves, against a recorded fake of the Workbench's one API door:
no test reaches GitHub.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from quill.core.github.api_console import (
    ConsoleCommand,
    SavedCommands,
    answer_tree,
    complete_path,
    confirmation_word,
    explain,
    find_operation,
    is_write,
    load_operations,
    parse_body,
)
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.thread_document import (
    fetch_thread,
    suggested_name,
    thread_html,
    thread_markdown,
)
from quill.core.github.watches import (
    MIN_MINUTES,
    WatchStore,
    check_round,
    due,
    freshness,
    parse_target,
)


class FakeApi:
    """Recorded answers by path; records every call, and fails a path on request."""

    def __init__(self, answers: dict[str, Any], graph: dict[str, Any] | None = None) -> None:
        self.answers = answers
        self.graph = graph or {}
        self.calls: list[tuple[str, str, dict[str, str] | None]] = []
        self.failing: set[str] = set()

    def rest(self, method: str, path: str, *, body=None, query=None) -> RestResponse:
        self.calls.append((method, path, dict(query) if query else None))
        if path in self.failing:
            raise GitHubRestError("GitHub said no.", status=404)
        data = self.answers.get(path, [])
        if isinstance(data, list) and query and query.get("page", "1") != "1":
            data = []
        return RestResponse(200, {}, data)

    def graphql(self, query: str, variables: Any) -> dict[str, Any]:
        self.calls.append(("GRAPHQL", query.split("{", 1)[0].strip(), dict(variables)))
        return self.graph


# -- Watches -----------------------------------------------------------------------


def test_parse_target_takes_names_numbers_links_and_a_branch() -> None:
    assert parse_target("run", "owner/repo main") == ("owner/repo", "main", 0)
    assert parse_target("release", "https://github.com/owner/repo") == ("owner/repo", "", 0)
    assert parse_target("review", "owner/repo#42") == ("owner/repo", "", 42)
    assert parse_target("comment", "https://github.com/o/r/issues/7") == ("o/r", "", 7)
    with pytest.raises(ValueError, match="number"):
        parse_target("review", "owner/repo")
    with pytest.raises(ValueError, match="owner/name"):
        parse_target("release", "just-a-name")


def test_freshness_says_when_it_was_checked_in_words() -> None:
    assert freshness(0, 1000) == "not checked yet"
    assert freshness(1000, 1030) == "checked just now"
    assert freshness(1000, 1000 + 180) == "checked 3 minutes ago"
    assert freshness(1000, 1000 + 3600) == "checked 1 hour ago"
    assert freshness(1000, 1000 + 2 * 86400) == "checked 2 days ago"


def test_watches_are_kept_per_account_and_atomically(quill_data_dir: Path) -> None:
    mine = WatchStore.load("alice")
    mine.add("release", "o/r")
    mine.save()
    theirs = WatchStore.load("bob")
    theirs.add("run", "o/r", "main")
    theirs.save()
    raw = json.loads((quill_data_dir / "github_watches.json").read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    assert set(raw["accounts"]) == {"alice", "bob"}
    assert [w.kind for w in WatchStore.load("alice").watches] == ["release"]
    assert WatchStore.load("bob").watches[0].branch == "main"


def test_a_first_check_learns_then_only_new_things_are_said(quill_data_dir: Path) -> None:
    store = WatchStore.load("alice")
    store.add("release", "o/r")
    run = store.add("run", "o/r", "main")
    api = FakeApi({
        "/repos/o/r/releases": [{"id": 1, "tag_name": "v1"}],
        "/repos/o/r/actions/runs": {
            "workflow_runs": [
                {"id": 10, "name": "CI", "head_branch": "main", "conclusion": "success"}
            ]
        },
    })
    clock = [1000.0]
    assert check_round(api, store, now=lambda: clock[0]) == []  # learns, says nothing
    assert all(w.last_result == "started watching" for w in store.watches)
    api.answers["/repos/o/r/releases"] = [{"id": 2, "name": "Two"}, {"id": 1, "tag_name": "v1"}]
    api.answers["/repos/o/r/actions/runs"]["workflow_runs"].insert(
        0, {"id": 11, "name": "CI", "head_branch": "main", "conclusion": "failure"}
    )
    clock[0] = 2000.0
    said = check_round(api, store, now=lambda: clock[0])
    assert said == [
        "New release in o/r: Two.",
        "CI finished on main: failure, in o/r.",
    ]
    assert store.last_round == 2000.0
    assert (
        "GET",
        "/repos/o/r/actions/runs",
        {"status": "completed", "per_page": "20", "branch": "main"},
    ) in api.calls
    # Nothing ever touches the notifications inbox.
    assert not any("notifications" in path for _m, path, _q in api.calls)
    assert store.find(run.id).last_checked == 2000.0


def test_a_paused_watch_is_not_checked_and_a_failure_says_why(quill_data_dir: Path) -> None:
    store = WatchStore.load("alice")
    paused = store.add("release", "o/quiet")
    from dataclasses import replace

    store.replace(replace(paused, paused=True))
    broken = store.add("comment", "o/r", number=5)
    api = FakeApi({})
    api.failing.add("/repos/o/r/issues/5/comments")
    assert check_round(api, store, now=lambda: 50.0) == []
    assert all("quiet" not in path for _m, path, _q in api.calls)
    assert store.find(broken.id).last_result == "Could not check: GitHub said no."


def test_due_follows_the_interval_and_never_sooner_than_the_floor(quill_data_dir: Path) -> None:
    store = WatchStore.load("alice")
    assert not due(store, 15, now=lambda: 10_000.0)  # nothing to watch
    store.add("release", "o/r")
    store.last_round = 10_000.0
    assert not due(store, 1, now=lambda: 10_000.0 + (MIN_MINUTES * 60) - 1)
    assert due(store, 1, now=lambda: 10_000.0 + MIN_MINUTES * 60)
    assert not due(store, 30, now=lambda: 10_000.0 + 29 * 60)


# -- Read as Document --------------------------------------------------------------


def _pull_api() -> FakeApi:
    return FakeApi({
        "/repos/o/r/issues/3": {
            "title": "Speed up start",
            "state": "closed",
            "html_url": "https://github.com/o/r/pull/3",
            "user": {"login": "ann"},
            "created_at": "2026-11-01T10:00:00Z",
            "body": "Makes it faster.\n\n```python\nprint('hi')\n```\nSee [docs](https://x.test).",
            "pull_request": {"merged_at": "2026-11-03T00:00:00Z"},
        },
        "/repos/o/r/issues/3/comments": [
            {"user": {"login": "bob"}, "created_at": "2026-11-02T09:00:00Z", "body": "Nice."}
        ],
        "/repos/o/r/pulls/3/reviews": [
            {
                "id": 77,
                "user": {"login": "cy"},
                "state": "CHANGES_REQUESTED",
                "submitted_at": "2026-11-01T12:00:00Z",
                "body": "One thing.",
            },
            {"id": 78, "user": {"login": "cy"}, "state": "PENDING", "body": "draft"},
        ],
        "/repos/o/r/pulls/3/comments": [
            {
                "pull_request_review_id": 77,
                "user": {"login": "cy"},
                "path": "app.py",
                "line": 12,
                "created_at": "2026-11-01T12:00:00Z",
                "body": "Rename this.",
            }
        ],
    })


def test_a_pull_request_reads_as_one_document_in_time_order() -> None:
    doc = fetch_thread(_pull_api(), "o/r", 3, "pull_request")
    assert doc.kind == "pull request" and doc.state == "merged"
    text = thread_markdown(doc)
    lines = [line for line in text.splitlines() if line.startswith("#")]
    assert lines == [
        "# Pull request o/r#3: Speed up start",
        "## Opening post by ann, 2026-11-01",
        "## Review by cy, 2026-11-01",
        "### Line comment by cy, 2026-11-01",
        "## Comment by bob, 2026-11-02",
    ]
    assert "```python\nprint('hi')\n```" in text  # code kept as GitHub wrote it
    assert "[docs](https://x.test)" in text  # links kept
    assert "Changes requested." in text and "On app.py, line 12." in text
    assert "draft" not in text  # a pending review is nobody's to read yet
    assert "<h1" in thread_html(doc) and "<pre" in thread_html(doc)
    assert suggested_name(doc) == "o-r-pr-3.md"


def test_a_discussion_reads_with_its_answer_and_replies() -> None:
    graph = {
        "repository": {
            "discussion": {
                "number": 9,
                "title": "How?",
                "body": "Question **here**.",
                "url": "https://github.com/o/r/discussions/9",
                "createdAt": "2026-10-01T00:00:00Z",
                "closed": False,
                "author": {"login": "dee"},
                "category": {"name": "Q&A"},
                "comments": {
                    "totalCount": 1,
                    "nodes": [
                        {
                            "body": "Like this.",
                            "createdAt": "2026-10-02T00:00:00Z",
                            "isAnswer": True,
                            "author": {"login": "eve"},
                            "replies": {
                                "nodes": [
                                    {
                                        "body": "Thanks!",
                                        "createdAt": "2026-10-03T00:00:00Z",
                                        "author": {"login": "dee"},
                                    }
                                ]
                            },
                        }
                    ],
                },
            }
        }
    }
    api = FakeApi({}, graph)
    text = thread_markdown(fetch_thread(api, "o/r", 9, "discussion"))
    assert "## Answer by eve, 2026-10-02" in text
    assert "### Reply by dee, 2026-10-03" in text
    assert "Question **here**." in text and "Category: Q&A." in text
    assert api.calls[0][2] == {"owner": "o", "repo": "r", "number": 9}


# -- API Console -------------------------------------------------------------------


def test_completion_keeps_typed_values_and_finds_the_operation() -> None:
    operations = load_operations()
    if not operations:
        pytest.skip("The vendored API snapshot is not present.")
    matches = complete_path("/repos/o/r/iss", operations, "GET")
    assert "/repos/o/r/issues" in matches
    found = find_operation("GET", "/repos/o/r/issues/5", operations)
    assert found is not None and found.name == "Get an issue"
    deleting = find_operation("DELETE", "/repos/o/r", operations)
    assert deleting is not None
    words = explain("DELETE", "/repos/o/r", deleting)
    assert "destructive" in words and "Full access" in words and "type DELETE" in words


def test_risk_words_cover_unknown_writes_and_graphql() -> None:
    assert "risk is unknown" in explain("POST", "/nowhere", None)
    assert explain("GET", "/nowhere", None).endswith("A GET only reads.")
    assert is_write("GRAPHQL", "mutation { addStar(input:{}) { clientMutationId } }")
    assert not is_write("GRAPHQL", "query { viewer { login } }")
    assert confirmation_word("GRAPHQL") == "MUTATION"
    assert confirmation_word("patch") == "PATCH"


def test_bodies_read_as_json_or_name_value_lines() -> None:
    assert parse_body('{"title": "x"}') == {"title": "x"}
    assert parse_body("title=Hello\nlocked=true\ncount=3") == {
        "title": "Hello",
        "locked": True,
        "count": 3,
    }
    with pytest.raises(ValueError):
        parse_body("no equals sign")


def test_the_answer_tree_has_values_in_labels_and_json_paths() -> None:
    tree = answer_tree({"items": [{"title": "A", "draft": False}], "total count": 1})
    assert tree.label == "Answer: object, 2 fields"
    items = tree.children[0]
    assert items.label == "items: list, 1 items"
    title = items.children[0].children[0]
    assert (title.label, title.path, title.value_text()) == ("title: A", "$.items[0].title", "A")
    assert items.children[0].children[1].label == "draft: false"
    assert tree.children[1].path == "$['total count']"


def test_saved_commands_are_per_account(quill_data_dir: Path) -> None:
    saved = SavedCommands.load("alice")
    saved.put(ConsoleCommand("me", "GET", "/user"))
    saved.put(ConsoleCommand("me", "GET", "/user/repos"))  # same name replaces
    saved.save()
    assert SavedCommands.load("alice").commands == [ConsoleCommand("me", "GET", "/user/repos")]
    assert SavedCommands.load("bob").commands == []
