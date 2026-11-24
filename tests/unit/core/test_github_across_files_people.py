"""PRD 22.11: workflows, templates, Dependabot, CODEOWNERS, people, repository settings and
packages by name across repositories (GH-R-150); files proposed as pull requests, never pushed.
Against a recorded fake of the Workbench's GitHubApi and PyGithub-shaped repositories: nothing
reaches GitHub.
"""

from __future__ import annotations

import base64
import hashlib
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.across_by_name import survey
from quill.core.github.across_files import apply_files, file_diff, plan_files, source_copy
from quill.core.github.across_people_settings import (
    apply_settings,
    plan_settings_same,
    read_place_copies,
)


class NotFound(Exception):
    status = 404


def _sha(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()  # noqa: S324 - a fake blob id


class FakeRepo:
    """A PyGithub-shaped repository: files per branch, every write and pull request kept."""

    default_branch = "main"

    def __init__(self, files: dict[str, str]) -> None:
        self.branches: dict[str, dict[str, str]] = {"main": dict(files)}
        self.writes: list[tuple[str, str]] = []
        self.pulls: list[dict[str, str]] = []

    def get_contents(self, path: str, ref: str | None = None) -> Any:
        text = self.branches[ref or "main"].get(path)
        if text is None:
            raise NotFound(path)
        return SimpleNamespace(path=path, sha=_sha(text), decoded_content=text.encode())

    def get_branch(self, name: str) -> Any:
        if name not in self.branches:
            raise NotFound(name)
        return SimpleNamespace(commit=SimpleNamespace(sha=f"head-{name}"))

    def create_git_ref(self, ref: str, _sha: str) -> None:
        self.branches[ref.removeprefix("refs/heads/")] = dict(self.branches["main"])

    def _put(self, path: str, text: str, branch: str) -> dict[str, Any]:
        self.branches[branch][path] = text
        self.writes.append((branch, path))
        return {"commit": SimpleNamespace(sha="c1")}

    def create_file(self, path: str, _m: str, text: str, branch: str) -> Any:
        return self._put(path, text, branch)

    def update_file(self, path: str, _m: str, text: str, _s: str, branch: str) -> Any:
        return self._put(path, text, branch)

    def create_pull(self, title: str, body: str, head: str, base: str) -> Any:
        self.pulls.append({"title": title, "body": body, "head": head, "base": base})
        return SimpleNamespace(number=7, html_url="https://github.com/o/r/pull/7")


class FakeApi:
    """GitHub's REST answers for repositories held as :class:`FakeRepo`, plus fixed answers."""

    def __init__(self, repos: dict[str, FakeRepo], answers: dict[tuple[str, str], Any]) -> None:
        self.repos, self.answers = repos, answers
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        if method != "GET":
            self.sent.append((method, path, body))
            return SimpleNamespace(status=200, data={}, headers={})
        query = query or {}
        if "package_type" in query:  # one answer per package type; the others have none
            return SimpleNamespace(
                data=self.answers.get((method, f"{path}?{query['package_type']}"), [])
            )
        key = (method, path + (f"?{query['affiliation']}" if "affiliation" in query else ""))
        if key in self.answers:
            return SimpleNamespace(status=200, data=self.answers[key], headers={})
        head, _sep, where = path.partition("/contents")
        repo = self.repos.get(head.removeprefix("/repos/"))
        if repo is None or not _sep:
            raise RuntimeError(f"404 Not Found: {path}")
        files, where = repo.branches["main"], where.lstrip("/")
        if where in files:
            text = files[where]
            content = base64.b64encode(text.encode()).decode()
            return SimpleNamespace(
                data={"content": content, "encoding": "base64", "sha": _sha(text)}, headers={}
            )
        prefix = f"{where}/" if where else ""
        names = {p[len(prefix) :].split("/", 1)[0] for p in files if p.startswith(prefix)}
        if not names:
            raise RuntimeError(f"404 Not Found: {path}")
        listing = []
        for one in sorted(names):
            full = prefix + one
            kind = "file" if full in files else "dir"
            listing.append({
                "name": one,
                "path": full,
                "type": kind,
                "sha": _sha(files.get(full, "")),
            })
        return SimpleNamespace(data=listing, headers={})


def _repo(admin: bool = True, push: bool = True) -> dict[str, Any]:
    return {"default_branch": "main", "permissions": {"push": push, "admin": admin}}


CI = (
    "name: CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
    "    steps:\n      - run: make\n"
)


def _files_api() -> FakeApi:
    repos = {
        "o/one": FakeRepo({
            ".github/workflows/ci.yml": CI,
            ".github/ISSUE_TEMPLATE/bug.yml": "name: Bug\n",
            ".github/CONTRIBUTING.md": "# Contributing\n",
            ".github/dependabot.yml": (
                "version: 2\nupdates:\n  - package-ecosystem: npm\n    directory: /\n"
            ),
            ".github/CODEOWNERS": "* @o/owners\ndocs/ @kim\n",
            "CODEOWNERS": "* @ignored\n",
        }),
        "o/two": FakeRepo({
            ".github/workflows/ci.yml": CI.replace("make", "make test"),
            "CONTRIBUTING.md": "# Contributing\n",
            "docs/CODEOWNERS": "* @o/owners\n",
        }),
        "o/three": FakeRepo({"README.md": "hello\n"}),
    }
    answers = {("GET", f"/repos/{name}"): _repo() for name in repos}
    return FakeApi(repos, answers)


SET = ["o/one", "o/two", "o/three"]


def test_workflows_by_name_say_how_many_versions_of_the_file() -> None:
    found = survey(_files_api(), "workflows", SET)
    row = found.row("ci.yml")
    assert row is not None
    assert (
        row.sentence() == "ci.yml: in 2 of 3 repositories, 2 versions of the file, missing from 1"
    )
    assert "Version 1: o/one" in row.detail() and "Missing From: o/three" in row.detail()


def test_templates_are_found_by_file_name_wherever_each_repository_keeps_them() -> None:
    found = survey(_files_api(), "templates", SET)
    assert [r.name for r in found.rows] == ["bug.yml, issue template", "CONTRIBUTING.md"]
    contributing = found.row("CONTRIBUTING.md")
    assert contributing is not None
    assert contributing.sentence().startswith("CONTRIBUTING.md: in 2 of 3 repositories, the same")
    assert "o/one: in the .github folder" in contributing.detail()
    assert "o/two: in the root folder" in contributing.detail()


def test_dependabot_and_codeowners_say_their_entries_rules_and_owners() -> None:
    api = _files_api()
    bot = survey(api, "dependabot", SET).row("dependabot.yml")
    assert bot is not None and "o/one: updates npm in the root folder" in bot.detail()
    owners = survey(api, "codeowners", SET).row("CODEOWNERS")
    assert owners is not None
    detail = owners.detail()
    # GitHub uses .github/CODEOWNERS before the root's, so the root's is not read.
    assert "o/one: in the .github folder, has 2 rules, owned by @kim, @o/owners" in detail
    assert "o/two: in the docs folder, has 1 rule, owned by @o/owners" in detail


def test_a_file_is_made_the_same_by_one_pull_request_each_never_pushed() -> None:
    api = _files_api()
    found = survey(api, "workflows", SET)
    row = found.row("ci.yml")
    assert row is not None
    winner = next(c.props for c in row.copies if c.repository == "o/one")
    plan = plan_files(found, row, winner)
    assert plan.preview().splitlines()[0] == (
        "Propose the workflow file ci.yml: 1 of 2 repositories will get a pull request; "
        "nothing changes until it is merged."
    )
    step = plan.runnable[0]
    assert step.preview() == "o/two: pull request, replaces version 2 with version 1 from o/one"
    results = apply_files(api, plan, source_copy(row, winner), api.repos.__getitem__)
    one, two = results
    assert one.said == "no change, already this version"
    assert two.ok and two.said == "opened pull request #7"
    target = api.repos["o/two"]
    assert target.branches["main"][".github/workflows/ci.yml"] != CI  # main is never written
    (pull,) = target.pulls
    assert pull["base"] == "main" and pull["head"] != "main"
    assert all(branch != "main" for branch, _path in target.writes)
    assert not api.sent


def test_add_to_missing_proposes_the_file_where_it_is_not() -> None:
    api = _files_api()
    found = survey(api, "workflows", SET)
    row = found.row("ci.yml")
    assert row is not None
    winner = row.copies[0].props
    plan = plan_files(found, row, winner, ["o/three"], missing=True)
    assert plan.steps[0].preview().startswith("o/three: pull request, adds version 1 from ")
    (three,) = apply_files(api, plan, source_copy(row, winner), api.repos.__getitem__)
    assert three.ok and api.repos["o/three"].pulls


def test_a_file_changed_since_the_survey_is_not_proposed() -> None:
    api = _files_api()
    found = survey(api, "workflows", SET)
    row = found.row("ci.yml")
    assert row is not None
    winner = next(c.props for c in row.copies if c.repository == "o/one")
    api.repos["o/two"].branches["main"][".github/workflows/ci.yml"] = "changed meanwhile\n"
    _one, two = apply_files(
        api, plan_files(found, row, winner), row.copies[0], api.repos.__getitem__
    )
    assert not two.ok and "changed in o/two since it was compared" in two.said
    assert not api.repos["o/two"].pulls


def test_a_source_changed_since_the_survey_is_not_proposed() -> None:
    api = _files_api()
    found = survey(api, "workflows", SET)
    row = found.row("ci.yml")
    assert row is not None
    source = next(c for c in row.copies if c.repository == "o/one")
    api.repos["o/one"].branches["main"][".github/workflows/ci.yml"] = "changed source\n"
    _one, two = apply_files(
        api, plan_files(found, row, source.props), source, api.repos.__getitem__
    )
    assert not two.ok and "changed in o/one since it was compared" in two.said
    assert not api.repos["o/two"].pulls


@pytest.mark.parametrize(
    "answer",
    [
        {"sha": _sha(CI), "encoding": "none", "content": ""},
        {"sha": _sha(CI), "encoding": "base64"},
        {"sha": _sha(CI), "encoding": "base64", "content": "not base64!"},
    ],
)
def test_unreadable_source_is_not_proposed(answer: dict[str, str]) -> None:
    api = _files_api()
    found = survey(api, "workflows", SET)
    row = found.row("ci.yml")
    assert row is not None
    source = next(c for c in row.copies if c.repository == "o/one")
    api.answers[("GET", "/repos/o/one/contents/.github/workflows/ci.yml")] = answer
    _one, two = apply_files(
        api, plan_files(found, row, source.props), source, api.repos.__getitem__
    )
    assert not two.ok
    assert not api.repos["o/two"].pulls


def test_versions_with_the_same_short_sha_are_distinct() -> None:
    from quill.core.github.across_by_name import ByNameRow
    from quill.core.github.across_files import _copy

    one = _copy("o/one", "ci.yml", {"path": "ci.yml", "sha": "1234567a"})
    two = _copy("o/two", "ci.yml", {"path": "ci.yml", "sha": "1234567b"})
    assert len(ByNameRow("workflows", "ci.yml", (one, two)).variants()) == 2


def test_a_repository_you_may_not_write_to_is_blocked_in_the_preview() -> None:
    api = _files_api()
    api.answers[("GET", "/repos/o/two")] = _repo(admin=False, push=False)
    found = survey(api, "workflows", SET)
    row = found.row("ci.yml")
    assert row is not None
    plan = plan_files(found, row, next(c.props for c in row.copies if c.repository == "o/one"))
    assert (
        plan.steps[1].blocked == "you may not change a workflow file there (it needs write access)"
    )


def test_compare_configuration_gets_the_difference_of_two_copies() -> None:
    api = _files_api()
    found = survey(api, "workflows", SET)
    row = found.row("ci.yml")
    assert row is not None
    one = next(c for c in row.copies if c.repository == "o/one")
    diff = file_diff(api, "workflows", one, "o/two", found.has("o/two", "ci.yml"))
    assert diff.state == "different" and diff.counts() == (1, 1)
    assert diff.sentence().startswith("workflow .github/workflows/ci.yml: different")
    missing = file_diff(api, "workflows", one, "o/three", None)
    assert missing.state == "missing" and missing.can_update


# -- people, settings and packages ------------------------------------------------------------


def _people_api() -> FakeApi:
    write = {"permissions": {"push": True}, "role_name": "write"}
    admin = {"permissions": {"admin": True}, "role_name": "admin"}
    return FakeApi(
        {},
        {
            ("GET", "/repos/o/one"): _repo(),
            ("GET", "/repos/o/two"): _repo(),
            ("GET", "/repos/o/three"): _repo(),
            ("GET", "/repos/o/one/collaborators?all"): [
                {"login": "kim", **write},
                {"login": "ana", **admin},
            ],
            ("GET", "/repos/o/one/collaborators?direct"): [{"login": "kim"}],
            ("GET", "/repos/o/two/collaborators?all"): [{"login": "kim", **admin}],
            ("GET", "/repos/o/two/collaborators?direct"): [],
        },
    )


def test_people_include_collaborators_after_the_first_page() -> None:
    class PagedPeople(FakeApi):
        def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
            if path.endswith("/collaborators"):
                page = int(query["page"])
                if query["affiliation"] == "direct":
                    rows = [{"login": "person100"}] if page == 1 else []
                else:
                    indexes = range(100) if page == 1 else range(100, 101)
                    rows = [{"login": f"person{i}", "role_name": "write"} for i in indexes]
                return SimpleNamespace(data=rows)
            return super().rest(method, path, body=body, query=query)

    people = read_place_copies(PagedPeople({}, {}), "people", "o/repo")
    assert len(people) == 101
    assert people[-1].name == "person100"
    assert people[-1].prop("source") == "directly"


def test_packages_include_entries_after_the_first_page() -> None:
    class PagedPackages(FakeApi):
        def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
            if path == "/users/o":
                return SimpleNamespace(data={"type": "Organization"})
            if path == "/orgs/o/packages":
                if query["package_type"] != "container":
                    return SimpleNamespace(data=[])
                indexes = range(100) if query["page"] == "1" else range(100, 101)
                return SimpleNamespace(
                    data=[
                        {
                            "name": f"package{i}",
                            "package_type": "container",
                            "repository": {"full_name": "o/repo"},
                        }
                        for i in indexes
                    ]
                )
            return super().rest(method, path, body=body, query=query)

    packages = read_place_copies(PagedPackages({}, {}), "packages", "o/repo")
    assert len(packages) == 101
    assert packages[-1].name == "package100"


def test_people_by_name_is_the_access_matrix_from_a_person_s_side() -> None:
    found = survey(_people_api(), "people", SET)
    kim = found.row("kim")
    assert kim is not None
    assert (
        kim.sentence()
        == "kim: access in 2 of 2 repositories, Admin in 1, Write in 1, 1 could not be read"
    )
    assert "role Write, source directly: o/one" in kim.detail()
    assert "role Admin, source from the organization or a team: o/two" in kim.detail()
    ana = found.row("ana")
    assert ana is not None and "no access in 1" in ana.sentence()
    assert found.unread == (("o/three", "not found, or no access"),)


def _settings_api() -> FakeApi:
    on = {"allow_auto_merge": True, "has_wiki": True, "delete_branch_on_merge": False}
    off = {"allow_auto_merge": False, "has_wiki": True, "delete_branch_on_merge": False}
    return FakeApi(
        {},
        {
            ("GET", "/repos/o/one"): {**_repo(), **on},
            ("GET", "/repos/o/two"): {**_repo(), **off},
            ("GET", "/repos/o/three"): {**_repo(admin=False), **off},
        },
    )


def test_repository_settings_by_name_say_on_in_how_many_and_off_in_how_many() -> None:
    found = survey(_settings_api(), "settings", SET)
    row = found.row("Allow auto-merge")
    assert row is not None and row.sentence() == "Allow auto-merge: off in 2, on in 1"
    wiki = found.row("Wiki")
    assert wiki is not None and wiki.sentence() == "Wiki: on in 3"
    issues = found.row("Issues")
    assert issues is None  # GitHub left it out of every answer, so there is no row to guess


def test_a_setting_is_made_the_same_with_admin_access_and_can_be_put_back() -> None:
    api = _settings_api()
    found = survey(api, "settings", SET)
    row = found.row("Allow auto-merge")
    assert row is not None
    plan = plan_settings_same(found, row, (("value", "on"),))
    assert [s.preview() for s in plan.steps] == [
        "o/one: no change, already on",
        "o/two: update, off becomes on",
        "o/three: will not change, you may not change a setting there (it needs admin access)",
    ]
    one, two, three = apply_settings(api, plan)
    assert one.ok and two.ok and not three.ok
    assert api.sent == [("PATCH", "/repos/o/two", {"allow_auto_merge": True})]
    assert two.log is not None and two.log.can_undo and two.log.kind == "repository"
    assert two.log.changes == (("allow_auto_merge", "Allow auto-merge", False, True),)


def test_packages_by_name_are_read_once_per_owner() -> None:
    package = {
        "name": "engine",
        "package_type": "container",
        "visibility": "private",
        "version_count": 3,
        "repository": {"full_name": "o/one"},
    }
    calls: list[str] = []

    class Counting(FakeApi):
        def rest(self, method: str, path: str, **kwargs: Any) -> Any:
            calls.append(path)
            return super().rest(method, path, **kwargs)

    api = Counting(
        {},
        {
            ("GET", "/repos/o/one"): _repo(),
            ("GET", "/repos/o/two"): _repo(),
            ("GET", "/users/o"): {"type": "Organization"},
            ("GET", "/orgs/o/packages?container"): [package],
        },
    )
    found = survey(api, "packages", ["o/one", "o/two"])
    row = found.row("engine")
    assert row is not None
    assert row.sentence() == "engine: in 1 of 2 repositories, missing from 1"
    assert "type container, visibility private: o/one" in row.detail()
    assert "o/one: has 3 versions" in row.detail()
    assert calls.count("/users/o") == 1
