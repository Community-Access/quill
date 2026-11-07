"""Repository files: folders, file text, README, history and blame runs."""

from __future__ import annotations

import base64
import datetime as dt
from typing import Any

import pytest

from quill.core.github import github_graphql, repo_files
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.repo_files import (
    BlameRun,
    GitHubRepoFilesMixin,
    blob_url,
    clean_repo_path,
    group_blame_runs,
    parse_blame,
    parse_folder,
)
from quill.core.github.rest_transport import GitHubRestError, RestResponse

TODAY = dt.date(2026, 11, 7)


class _Provider(GitHubRepoFilesMixin):
    def __init__(self, token: str | None = "tok") -> None:
        self._token = token


class _Api:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any, Any]] = []
        self.replies: dict[tuple[str, str], Any] = {}

    def __call__(self, token, method, path, *, body=None, query=None, **_kw):
        self.calls.append((method, path, query, body))
        reply = self.replies.get((method, path), RestResponse(200, {}, None))
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> _Api:
    fake = _Api()
    monkeypatch.setattr(repo_files, "request_json", fake)
    monkeypatch.setattr(github_graphql, "request_json", fake)
    return fake


def _content(text: str) -> dict[str, object]:
    return {
        "type": "file",
        "encoding": "base64",
        "path": "docs/README.md",
        "content": base64.b64encode(text.encode()).decode(),
    }


def test_folder_lists_folders_first_and_says_sizes(api: _Api) -> None:
    api.replies[("GET", "/repos/o/r/contents/docs")] = RestResponse(
        200,
        {},
        [
            {"name": "b.txt", "path": "docs/b.txt", "type": "file", "size": 2048},
            {"name": "z", "path": "docs/z", "type": "dir"},
            {"name": "a.md", "path": "docs/a.md", "type": "file", "size": 1},
        ],
    )
    entries = _Provider().fetch_repo_folder("o/r", "main", "/docs/")
    assert [entry.label for entry in entries] == [
        "z, folder",
        "a.md, 1 byte",
        "b.txt, 2 kilobytes",
    ]
    assert api.calls[0][2] == {"ref": "main"}


def test_root_folder_has_no_trailing_path_and_a_file_is_refused(api: _Api) -> None:
    api.replies[("GET", "/repos/o/r/contents")] = RestResponse(200, {}, _content("x"))
    with pytest.raises(GitHubItemsError, match="is a file"):
        _Provider().fetch_repo_folder("o/r", "v1.0")


def test_paths_that_leave_the_repository_are_refused() -> None:
    for bad in ("../etc", "a/../../b", "a\\b", "a//b"):
        with pytest.raises(GitHubItemsError):
            clean_repo_path(bad)
    assert clean_repo_path("/docs/guide/") == "docs/guide"


def test_file_text_decodes_and_refuses_binary_or_large(api: _Api) -> None:
    path = "/repos/o/r/contents/docs/README.md"
    api.replies[("GET", path)] = RestResponse(200, {}, _content("﻿Hello\n"))
    assert _Provider().fetch_repo_file_text("o/r", "docs/README.md", "main") == "Hello\n"
    api.replies[("GET", path)] = RestResponse(
        200, {}, {"type": "file", "encoding": "base64", "content": base64.b64encode(b"\x00\x01")}
    )
    with pytest.raises(GitHubItemsError):
        _Provider().fetch_repo_file_text("o/r", "docs/README.md", "main")
    api.replies[("GET", path)] = RestResponse(200, {}, {"type": "file", "encoding": "none"})
    with pytest.raises(GitHubItemsError, match="1 MB"):
        _Provider().fetch_repo_file_text("o/r", "docs/README.md", "main")


def test_readme_of_a_folder_and_a_missing_one(api: _Api) -> None:
    api.replies[("GET", "/repos/o/r/readme/docs")] = RestResponse(200, {}, _content("# Docs"))
    assert _Provider().fetch_readme("o/r", "main", "docs") == ("docs/README.md", "# Docs")
    api.replies[("GET", "/repos/o/r/readme")] = GitHubRestError("Not Found", status=404)
    with pytest.raises(GitHubItemsError, match="This repository has no README"):
        _Provider().fetch_readme("o/r", "main")


def test_file_history_reads_newest_first_with_spoken_dates(api: _Api) -> None:
    api.replies[("GET", "/repos/o/r/commits")] = RestResponse(
        200,
        {},
        [
            {
                "sha": "abcdef1234",
                "html_url": "https://github.com/o/r/commit/abcdef1234",
                "commit": {
                    "message": "Fix the diff\n\nLonger text",
                    "author": {"name": "Jeff", "date": "2026-11-03T10:00:00Z"},
                },
            }
        ],
    )
    commits = _Provider().fetch_file_history("o/r", "a.py", "main")
    assert commits[0].label(TODAY) == "Fix the diff: Jeff, 3 November, abcdef1"
    assert api.calls[0][2] == {"sha": "main", "per_page": "50", "path": "a.py"}


def _range(start: int, end: int, sha: str) -> dict[str, object]:
    return {
        "startingLine": start,
        "endingLine": end,
        "commit": {
            "oid": sha * 10,
            "messageHeadline": f"Commit {sha}",
            "url": f"https://github.com/o/r/commit/{sha}",
            "author": {"name": f"Author {sha}", "date": "2025-12-12T08:00:00Z"},
        },
    }


def test_blame_groups_neighbouring_ranges_of_one_commit_into_runs(api: _Api) -> None:
    api.replies[("POST", "/graphql")] = RestResponse(
        200,
        {},
        {
            "data": {
                "repository": {
                    "object": {
                        "blame": {
                            "ranges": [
                                _range(10, 12, "a"),
                                _range(1, 9, "b"),
                                _range(13, 14, "a"),
                                _range(15, 15, "c"),
                            ]
                        }
                    }
                }
            }
        },
    )
    runs = _Provider().fetch_blame("o/r", "main", "src/app.py")
    assert [run.label(TODAY) for run in runs] == [
        "Lines 1 to 9: Author b, 12 December 2025, bbbbbbb, Commit b",
        "Lines 10 to 14: Author a, 12 December 2025, aaaaaaa, Commit a",
        "Line 15: Author c, 12 December 2025, ccccccc, Commit c",
    ]
    _method, _path, _query, body = api.calls[0]
    assert "blame(path:$path)" in body["query"]
    assert body["variables"] == {"owner": "o", "repo": "r", "ref": "main", "path": "src/app.py"}


def test_blame_needs_sign_in_and_a_real_commit(api: _Api) -> None:
    with pytest.raises(GitHubItemsError, match="signed-in"):
        _Provider(token=None).fetch_blame("o/r", "main", "a.py")
    with pytest.raises(GitHubItemsError, match="not in this repository"):
        parse_blame({"repository": {"object": None}})


def test_group_keeps_separate_runs_of_the_same_commit_apart() -> None:
    a1 = BlameRun(1, 2, "a", "t", "x", "")
    b = BlameRun(3, 3, "b", "t", "y", "")
    a2 = BlameRun(4, 5, "a", "t", "x", "")
    assert group_blame_runs([a1, b, a2]) == [a1, b, a2]


def test_blob_url_quotes_the_path() -> None:
    assert blob_url("o/r", "feature/x", "docs/my file.md") == (
        "https://github.com/o/r/blob/feature/x/docs/my%20file.md"
    )


def test_parse_folder_ignores_malformed_rows() -> None:
    assert parse_folder([{"name": "x"}, "junk", None]) == []
