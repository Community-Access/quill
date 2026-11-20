"""Compare configuration with a source, and propose it as one pull request (PRD 22.11)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.config_compare import compare_files, propose_update, pull_request_body
from quill.core.github.template_save import TemplateSaveConflict


class NotFound(Exception):
    status = 404


class _Entry:
    def __init__(self, repo: FakeRepo, path: str, kind: str, ref: str) -> None:
        self.path, self.type, self.name = path, kind, path.rsplit("/", 1)[-1]
        text = repo.branches[ref].get(path, "")
        self.size = len(text)
        self.sha = repo.sha(ref, path)
        self.html_url = ""
        self.decoded_content = text.encode()


class _Commit:
    def __init__(self, sha: str) -> None:
        self.sha = sha


class _Branch:
    def __init__(self, name: str, protected: bool) -> None:
        self.name, self.protected, self.commit = name, protected, _Commit(f"head-{name}")


class FakeRepo:
    """A PyGithub-shaped repository whose files live per branch; every write is kept."""

    default_branch = "main"
    permissions = None

    def __init__(self, files: dict[str, str], *, protected: bool = False) -> None:
        self.branches: dict[str, dict[str, str]] = {"main": dict(files)}
        self.protected = protected
        self.writes: list[tuple[str, str, str]] = []
        self.pulls: list[dict[str, str]] = []
        self.refs: list[str] = []

    def sha(self, ref: str, path: str) -> str:
        text = self.branches[ref].get(path)
        return f"sha-{abs(hash(text)) % 10_000}" if text is not None else ""

    def get_contents(self, path: str, ref: str | None = None) -> Any:
        files = self.branches[ref or "main"]
        if path in files:
            return _Entry(self, path, "file", ref or "main")
        prefix = f"{path}/" if path else ""
        names = {p[len(prefix) :].split("/", 1)[0] for p in files if p.startswith(prefix)}
        if not names:
            raise NotFound(path)
        return [
            _Entry(self, prefix + n, "file" if prefix + n in files else "dir", ref or "main")
            for n in sorted(names)
        ]

    def get_branch(self, name: str) -> _Branch:
        if name not in self.branches:
            raise NotFound(name)
        return _Branch(name, self.protected and name == "main")

    def create_git_ref(self, ref: str, sha: str) -> None:
        name = ref.removeprefix("refs/heads/")
        self.refs.append(name)
        self.branches[name] = dict(self.branches["main"])

    def _put(self, path: str, text: str, branch: str) -> dict[str, Any]:
        self.branches[branch][path] = text
        self.writes.append((branch, path, text))
        return {"commit": _Commit(f"c{len(self.writes)}")}

    def create_file(self, path: str, _m: str, text: str, branch: str) -> Any:
        return self._put(path, text, branch)

    def update_file(self, path: str, _m: str, text: str, _sha: str, branch: str) -> Any:
        return self._put(path, text, branch)

    def create_pull(self, title: str, body: str, head: str, base: str) -> Any:
        self.pulls.append({"title": title, "body": body, "head": head, "base": base})
        return type("P", (), {"number": 41, "html_url": "https://github.com/o/r/pull/41"})()


CI = (
    "name: CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
    "    steps:\n      - run: make\n"
)
SOURCE = {
    ".github/workflows/ci.yml": CI,
    ".github/ISSUE_TEMPLATE/bug.yml": "name: Bug\n",
    ".github/dependabot.yml": "version: 2\nupdates: []\n",
    "CONTRIBUTING.md": "# Contributing\n\nOpen an issue first.\n",
    ".github/CODEOWNERS": "* @org/owners\n",
    "README.md": "not configuration\n",
}


def _target() -> FakeRepo:
    return FakeRepo({
        ".github/workflows/ci.yml": CI.replace("make", "make test"),
        ".github/workflows/local.yml": "name: Local\n",
        ".github/CONTRIBUTING.md": "# Contributing\n\nOpen an issue first.\n",
    })


def test_each_file_is_missing_the_same_different_or_only_here() -> None:
    diffs = compare_files(FakeRepo(SOURCE), "o/source", _target(), "o/r")
    said = [d.sentence() for d in diffs]
    assert said == [
        "workflow .github/workflows/ci.yml: different, 1 line added and 1 removed.",
        "CODEOWNERS .github/CODEOWNERS: missing here; it would be added (1 line).",
        "issue template .github/ISSUE_TEMPLATE/bug.yml: missing here; it would be added (1 line).",
        "Dependabot configuration .github/dependabot.yml: missing here; it would be added "
        "(2 lines).",
        "workflow .github/workflows/local.yml: only here; the source has none, and it is kept.",
        "community file .github/CONTRIBUTING.md: the same as the source.",
    ]
    different = diffs[0]
    assert different.diff_lines()[0] == "--- .github/workflows/ci.yml (here)"
    assert different.diff_lines()[-2:] == ["-      - run: make test", "+      - run: make"]


def test_the_organization_s_starter_workflows_fill_in_the_default_branch() -> None:
    org = FakeRepo({
        "workflow-templates/lint.yml": "on:\n  push:\n    branches: [$default-branch]\n"
    })
    diffs = compare_files(org, "o/.github", FakeRepo({}), "o/r")
    assert [(d.path, d.state) for d in diffs] == [(".github/workflows/lint.yml", "missing")]
    assert "branches: [main]" in diffs[0].source_text


def test_the_update_is_one_pull_request_and_never_a_push_to_the_default_branch() -> None:
    target = _target()
    diffs = compare_files(FakeRepo(SOURCE), "o/source", target, "o/r")
    chosen = [d for d in diffs if d.can_update]
    made = propose_update(target, "o/r", "o/source", chosen)
    assert made.pull_request_number == 41
    assert all(branch != "main" for branch, _p, _t in target.writes)
    assert {p for _b, p, _t in target.writes} == {d.path for d in chosen}
    assert target.branches["main"][".github/workflows/ci.yml"].endswith("make test\n")
    pull = target.pulls[0]
    assert pull["base"] == "main" and pull["head"] == target.refs[0]
    assert pull["title"] == "Update 4 configuration files from o/source"
    assert (
        "- workflow .github/workflows/ci.yml: different, 1 line added and 1 removed."
        in (pull["body"])
    )
    assert "```diff" in pull["body"] and "+      - run: make" in pull["body"]


def test_a_file_changed_since_the_comparison_stops_everything() -> None:
    target = _target()
    diffs = compare_files(FakeRepo(SOURCE), "o/source", target, "o/r")
    target.branches["main"][".github/workflows/ci.yml"] = "changed meanwhile\n"
    with pytest.raises(TemplateSaveConflict, match="compare again"):
        propose_update(target, "o/r", "o/source", [diffs[0]])
    assert target.writes == [] and target.refs == []


def test_the_body_cuts_a_long_diff_and_points_at_the_files_tab() -> None:
    long_source = FakeRepo({".github/workflows/x.yml": "".join(f"a{i}\n" for i in range(80))})
    diffs = compare_files(long_source, "o/s", FakeRepo({".github/workflows/x.yml": "b\n"}), "o/r")
    body = pull_request_body("o/s", diffs)
    assert "more lines in the Files tab." in body
    assert body.startswith("Brings these files in line with o/s")
