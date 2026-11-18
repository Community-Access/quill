"""One commit at a time, and changes that are only whitespace (GH-D)."""

from __future__ import annotations

from typing import Any

from quill.core.github.commit_review import commit_diff, pull_commits, whitespace_only
from quill.core.github.diff_lines import parse_diff_lines
from quill.core.github.rest_transport import RestResponse


class FakeApi:
    def __init__(self, commits: list[dict[str, Any]] | None = None) -> None:
        self.commits = commits or []
        self.sent: list[tuple[str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((path, dict(query or {})))
        if path.endswith("/commits") and "/pulls/" in path:
            page = int((query or {}).get("page", "1"))
            return RestResponse(200, {}, self.commits[(page - 1) * 100 : page * 100])
        return RestResponse(
            200,
            {},
            {
                "parents": [{"sha": "p" * 40}],
                "commit": {"message": "Fix the parser\n\nLonger words."},
                "files": [
                    {
                        "filename": "a.py",
                        "status": "modified",
                        "additions": 1,
                        "deletions": 1,
                        "patch": "@@ -1 +1 @@\n-x\n+y",
                    }
                ],
            },
        )

    def graphql(self, query: str, variables: Any) -> Any:
        raise AssertionError


def _commit(i: int, login: str = "ann") -> dict[str, Any]:
    return {
        "sha": f"{i:07d}" + "a" * 33,
        "commit": {"message": f"Step {i}\n\nbody", "author": {"name": "Ann B"}},
        "author": {"login": login} if login else None,
    }


def test_commits_are_listed_oldest_first_across_pages() -> None:
    api = FakeApi([_commit(i) for i in range(1, 131)] + [_commit(131, login="")])
    commits = pull_commits(api, "o/r", 4)
    assert len(commits) == 131 and [q["page"] for _p, q in api.sent] == ["1", "2"]
    assert commits[0].label == "0000001 Step 1, by ann"
    assert commits[-1].author == "Ann B"


def test_a_commit_diff_reads_like_the_whole_one() -> None:
    diff = commit_diff(FakeApi(), "o/r", 4, "Add it", "c" * 40)
    assert diff.number == 4 and diff.head_sha == "c" * 40 and diff.base_sha == "p" * 40
    assert diff.title == "Add it, commit ccccccc: Fix the parser"
    assert diff.head_ref == "commit ccccccc" and diff.base_ref == "commit ppppppp"
    assert [f.filename for f in diff.files] == ["a.py"] and diff.files[0].patch.startswith("@@")


def test_whitespace_only_changes_are_paired_and_blank_lines_go() -> None:
    lines = parse_diff_lines(
        "@@ -1,4 +1,5 @@\n-  a = 1\n-x\n+    a = 1\n+y\n+\n keep\n-\tb\n+b  \n"
    )
    hidden = whitespace_only(lines)
    kept = [
        lines[i].text for i in range(len(lines)) if lines[i].kind != "context" and i not in hidden
    ]
    assert kept == ["", "x", "y"]  # the hunk heading, and the one real change
    assert len(hidden) == 5
