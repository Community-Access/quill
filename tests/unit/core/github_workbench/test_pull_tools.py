"""A pull request's exact patch, its revert, and its conflicts in a worktree (GH-PT)."""

from __future__ import annotations

from collections.abc import Mapping
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import pull_tools as pt
from quill.core.github.rest_transport import RestResponse


class FakeApi:
    def __init__(self, *, files: list[dict[str, Any]] | None = None, pull: Any = None):
        self.files = files or []
        self.pull = pull if pull is not None else {}
        self.calls: list[tuple[str, str, Any]] = []

    def rest(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, object] | None = None,
        query: Mapping[str, str] | None = None,
    ) -> RestResponse:
        self.calls.append((method, path, dict(query or {})))
        if path.endswith("/files"):
            page = int((query or {}).get("page", "1"))
            size = int((query or {}).get("per_page", "100"))
            return RestResponse(200, {}, self.files[(page - 1) * size : page * size])
        return RestResponse(200, {}, self.pull)

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        self.calls.append(("GRAPHQL", query, dict(variables)))
        return {"revertPullRequest": {"revertPullRequest": {"number": 99, "url": "u"}}}


# -- the exact patch -------------------------------------------------------------


def test_patch_is_one_unified_diff_with_every_kind_of_file() -> None:
    api = FakeApi(
        files=[
            {"filename": "a.py", "status": "modified", "patch": "@@ -1 +1 @@\n-x\n+y"},
            {"filename": "new.txt", "status": "added", "patch": "@@ -0,0 +1 @@\n+hi"},
            {"filename": "gone.txt", "status": "removed", "patch": "@@ -1 +0,0 @@\n-bye"},
            {"filename": "logo.png", "status": "modified"},
            {"filename": "b.py", "previous_filename": "old_b.py", "status": "renamed"},
        ]
    )
    patch = pt.patch_text(api, "o/r", 7)
    lines = patch.text.splitlines()
    assert lines[:5] == [
        "diff --git a/a.py b/a.py",
        "--- a/a.py",
        "+++ b/a.py",
        "@@ -1 +1 @@",
        "-x",
    ]
    assert "--- /dev/null" in lines and "+++ /dev/null" in lines
    assert "# logo.png: modified, and GitHub sends no text change for it." in lines
    assert "rename from old_b.py" in lines and "rename to b.py" in lines
    assert patch.files == 5
    assert patch.without_text == ("logo.png",)
    assert "1 of them has no text change" in patch.sentence
    assert patch.text.endswith("\n")


def test_patch_reads_every_page() -> None:
    files = [{"filename": f"f{i}", "status": "modified", "patch": "@@ x"} for i in range(150)]
    api = FakeApi(files=files)
    patch = pt.patch_text(api, "o/r", 1)
    assert patch.files == 150
    pages = [call[2]["page"] for call in api.calls]
    assert pages == ["1", "2"]
    assert patch.sentence == "The patch has 150 files."


def test_patch_of_nothing_and_its_name() -> None:
    assert pt.patch_text(FakeApi(), "o/r", 1).files == 0
    assert pt.patch_file_name("o/quill", 12) == "quill-pr-12.diff"
    assert pt.patch_file_name("o/we ird", 3) == "we-ird-pr-3.diff"


# -- revert ----------------------------------------------------------------------


def test_revert_opens_the_undoing_pull_request() -> None:
    api = FakeApi(pull={"node_id": "PR_1", "merged": True, "title": "Add it"})
    said = pt.revert_pull(api, "o/r", 5)
    assert said == "Opened pull request #99, which reverts #5."
    sent = api.calls[-1][2]
    assert sent["id"] == "PR_1" and sent["title"] == 'Revert "Add it"' and sent["draft"] is False
    assert "body" not in sent


def test_revert_as_draft_with_its_own_title() -> None:
    api = FakeApi(pull={"node_id": "PR_1", "merged": True, "title": "Add it"})
    said = pt.revert_pull(api, "o/r", 5, title="Undo", body="Broke it", draft=True)
    assert said.startswith("Opened draft pull request #99")
    assert api.calls[-1][2]["title"] == "Undo" and api.calls[-1][2]["body"] == "Broke it"


def test_revert_refuses_an_unmerged_or_missing_pull_before_sending() -> None:
    api = FakeApi(pull={"node_id": "PR_1", "merged": False})
    with pytest.raises(pt.PullToolsError, match="not merged"):
        pt.revert_pull(api, "o/r", 5)
    assert all(call[0] != "GRAPHQL" for call in api.calls)
    with pytest.raises(pt.PullToolsError, match="no pull request"):
        pt.revert_pull(FakeApi(pull={}), "o/r", 5)


def test_error_is_coded() -> None:
    assert pt.PullToolsError.code == "QUILL-GITHUB-PULL-TOOLS"


# -- conflicts in a worktree -----------------------------------------------------


class FakeGit:
    def __init__(self, answers: dict[str, tuple[int, str]]):
        self.answers = answers
        self.calls: list[tuple[tuple[str, ...], str]] = []

    def __call__(self, argv: list[str], *, cwd: str, timeout_seconds: float) -> object:
        args = tuple(argv[1:])
        self.calls.append((args, cwd))
        for key, (code, out) in self.answers.items():
            if " ".join(args).startswith(key):
                return SimpleNamespace(returncode=code, stdout=out, stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_remote_for_names_the_matching_remote_only() -> None:
    git = FakeGit({
        "remote -v": (
            0,
            "mine\thttps://github.com/me/r.git (fetch)\n"
            "upstream\thttps://github.com/o/r.git (fetch)\n",
        )
    })
    assert pt.remote_for(git, "/repo", "O/R") == "upstream"
    assert pt.remote_for(git, "/repo", "x/y") == ""
    assert pt.remote_for(FakeGit({"remote": (1, "")}), "/repo", "o/r") == ""


def _prepare(git: FakeGit, tmp_path: Any, **extra: Any) -> pt.ConflictWorktree:
    return pt.prepare_conflict_worktree(
        git,
        str(tmp_path / "repo"),
        remote="origin",
        number=12,
        head="feature",
        base="main",
        path=str(tmp_path / "repo-pr-12-conflicts"),
        **extra,
    )


def test_conflicts_land_in_a_new_worktree_and_are_listed(tmp_path: Any) -> None:
    (tmp_path / "repo").mkdir()
    git = FakeGit({
        "merge": (1, "CONFLICT (content): Merge conflict in a.py"),
        "diff --name-only": (0, "a.py\ndocs/b.md\n"),
    })
    result = _prepare(git, tmp_path, taken_branches=["pr-12-conflicts"])
    assert result.ok and result.files == ("a.py", "docs/b.md")
    commands = [" ".join(args) for args, _cwd in git.calls]
    fetch = next(c for c in commands if c.startswith("fetch"))
    assert "+refs/heads/feature:refs/remotes/origin/feature" in fetch
    assert "+refs/heads/main:refs/remotes/origin/main" in fetch
    add = next(c for c in commands if c.startswith("worktree add"))
    assert "-b pr-12-conflicts-2" in add and add.endswith("origin/feature")
    merge_cwd = next(cwd for args, cwd in git.calls if args[0] == "merge")
    assert merge_cwd == result.path != str(tmp_path / "repo")
    assert "--no-commit" in next(c for c in commands if c.startswith("merge"))
    assert "2 files conflict" in result.message and "git push origin" in result.message
    assert not any(c.startswith(("commit", "push")) for c in commands)


def test_a_clean_merge_says_so(tmp_path: Any) -> None:
    (tmp_path / "repo").mkdir()
    result = _prepare(FakeGit({}), tmp_path)
    assert result.ok and not result.files and "no conflicts" in result.message


def test_a_failed_fetch_or_merge_is_said(tmp_path: Any) -> None:
    (tmp_path / "repo").mkdir()
    fetched = _prepare(FakeGit({"fetch": (128, "fatal: could not read from remote")}), tmp_path)
    assert not fetched.ok and "could not fetch" in fetched.message and "fatal" in fetched.message
    merged = _prepare(FakeGit({"merge": (1, "fatal: refusing")}), tmp_path)
    assert not merged.ok and "could not merge main into feature" in merged.message


def test_branch_names_that_could_be_options_are_refused(tmp_path: Any) -> None:
    with pytest.raises(pt.PullToolsError):
        pt.prepare_conflict_worktree(
            FakeGit({}),
            str(tmp_path),
            remote="origin",
            number=1,
            head="--upload-pack=x",
            base="main",
            path=str(tmp_path / "w"),
        )
