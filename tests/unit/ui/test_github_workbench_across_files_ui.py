"""GH-R-150 in the window: workflows, templates, Dependabot, CODEOWNERS, people, repository
settings and packages by name, grouped category first; Compare Configuration on a file row;
files proposed as pull requests and settings made the same, each previewed first.

A real frame over a recorded fake of the Workbench's GitHubApi; nothing leaves the machine.
"""

from __future__ import annotations

import base64
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.navigation_state import account_key_for_token  # noqa: E402
from quill.core.github.repository_sets import RepositorySets  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

TOKEN = "test-token-not-real"


class _Items:
    is_authenticated = True
    token = TOKEN

    def close(self) -> None:
        pass


class FakeApi:
    def __init__(self, answers: dict[tuple[str, str], Any]) -> None:
        self.answers = answers
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        if method != "GET":
            self.sent.append((method, path, body))
            return SimpleNamespace(status=200, data={}, headers={})
        query = query or {}
        if "affiliation" in query:
            path = f"{path}?{query['affiliation']}"
        answer = self.answers.get((method, path))
        if answer is None:
            raise RuntimeError(f"404 Not Found: {path}")
        return SimpleNamespace(status=200, data=answer, headers={})


class NotFound(Exception):
    status = 404


class FakeRepo:
    """Just enough of a PyGithub repository for one pull request."""

    default_branch = "main"

    def __init__(self, files: dict[str, tuple[str, str]]) -> None:
        self.files = files  # path: (sha, text)
        self.pulls: list[str] = []
        self.written: list[str] = []

    def get_contents(self, path: str, ref: str | None = None) -> Any:
        if path not in self.files:
            raise NotFound(path)
        sha, text = self.files[path]
        return SimpleNamespace(sha=sha, decoded_content=text.encode())

    def get_branch(self, name: str) -> Any:
        if name != "main":
            raise NotFound(name)
        return SimpleNamespace(commit=SimpleNamespace(sha="head"))

    def create_git_ref(self, ref: str, _sha: str) -> None:
        pass

    def update_file(self, path: str, _m: str, text: str, _s: str, branch: str) -> Any:
        self.written.append(branch)
        self.files[path] = ("new", text)
        return {"commit": SimpleNamespace(sha="c1")}

    def create_pull(self, title: str, body: str, head: str, base: str) -> Any:
        self.pulls.append(base)
        return SimpleNamespace(number=12, html_url="")


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, quill_data_dir):
    said: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), "", announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)


def _choose(*repos: str) -> None:
    sets = RepositorySets.load(account_key_for_token(TOKEN))
    sets.set_repositories("My Repositories", list(repos))
    sets.save()


def _repo(**settings: Any) -> dict[str, Any]:
    return {"default_branch": "main", "permissions": {"push": True, "admin": True}, **settings}


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def _workflow_api() -> FakeApi:
    def listing(sha: str) -> list[dict[str, str]]:
        path = ".github/workflows/ci.yml"
        return [{"name": "ci.yml", "path": path, "type": "file", "sha": sha}]

    return FakeApi({
        ("GET", "/repos/o/one"): _repo(),
        ("GET", "/repos/o/two"): _repo(),
        ("GET", "/repos/o/one/contents/.github/workflows"): listing("aaaaaaa1"),
        ("GET", "/repos/o/two/contents/.github/workflows"): listing("bbbbbbb2"),
        ("GET", "/repos/o/one/contents/.github/workflows/ci.yml"): {
            "content": _b64("run: a\n"),
            "encoding": "base64",
            "sha": "aaaaaaa1",
        },
        ("GET", "/repos/o/two/contents/.github/workflows/ci.yml"): {
            "content": _b64("run: b\n"),
            "encoding": "base64",
            "sha": "bbbbbbb2",
        },
    })


def test_the_seven_places_are_grouped_category_first() -> None:
    from quill.core.github.workbench_tree import GITHUB_TREE

    parents = {n.key: n.parent for n in GITHUB_TREE._nodes.values()}
    assert parents["across_by_workflows"] == "across_actions"
    assert parents["across_by_packages"] == "across_code"
    for kind in ("templates", "dependabot", "codeowners"):
        assert parents[f"across_by_{kind}"] == "across_files"
    assert parents["across_by_settings"] == parents["across_by_people"] == "across_settings"
    assert parents["across_files"] == "across"


def test_a_workflow_row_compares_through_compare_configuration(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one", "o/two")
    api = _workflow_api()
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_by_workflows"))
    (row,) = bench.rows
    assert row.label == "ci.yml: in 2 of 2 repositories, 2 versions of the file"
    assert provider._fits_across_compare_config(row)
    assert provider._fits_across_make_same(row) and not provider._fits_across_delete_name(row)
    monkeypatch.setattr(provider, "_choose", lambda _t, _p, _labels: 0)
    shown: list[tuple[str, str, list[Any]]] = []
    monkeypatch.setattr(provider, "_compared", lambda *args: shown.append(args))
    provider._do_across_compare_config(None, row)
    ((target, source, (diff,)),) = shown
    assert (target, source) == ("o/two", "o/one")
    assert diff.state == "different" and diff.path == ".github/workflows/ci.yml"
    assert not api.sent


def test_make_them_the_same_on_a_workflow_opens_one_pull_request_each(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one", "o/two")
    api = _workflow_api()
    monkeypatch.setattr(provider, "github_api", lambda: api)
    target = FakeRepo({".github/workflows/ci.yml": ("bbbbbbb2", "run: b\n")})
    monkeypatch.setattr(provider, "_authoring_repo", lambda name: target)
    _go(bench, NodeRef("", "across_by_workflows"))
    (row,) = bench.rows
    monkeypatch.setattr(provider, "_choose", lambda _t, _p, _labels: 0)
    previews: list[str] = []
    monkeypatch.setattr(
        provider, "_across_preview", lambda title, plan, yes, **_k: previews.append(yes) or True
    )
    provider._do_across_make_same(None, row)
    assert previews == ["Open Pull Requests"]
    assert target.pulls == ["main"] and target.written and "main" not in target.written
    details = bench.details.GetValue()
    assert details.startswith(
        "Opened 1 pull request to review; 1 repository already had this version. "
        "Nothing changes until each is merged."
    )
    assert "o/two: opened pull request #12" in details
    assert not api.sent  # nothing went through the REST writes, only the pull request


def test_a_setting_is_made_the_same_from_its_row(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one", "o/two")
    api = FakeApi({
        ("GET", "/repos/o/one"): _repo(allow_auto_merge=True),
        ("GET", "/repos/o/two"): _repo(allow_auto_merge=False),
    })
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_by_settings"))
    (row,) = bench.rows
    assert row.label == "Allow auto-merge: off in 1, on in 1"
    monkeypatch.setattr(
        provider,
        "_choose",
        lambda _t, _p, labels: labels.index(next(label for label in labels if "value on" in label)),
    )
    monkeypatch.setattr(provider, "_across_preview", lambda *_a, **_k: True)
    provider._do_across_make_same(None, row)
    assert api.sent == [("PATCH", "/repos/o/two", {"allow_auto_merge": True})]
    assert bench.details.GetValue().startswith("1 of 2 repositories changed. 1 needed no change.")


def test_people_and_packages_are_read_only_and_say_why(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one")
    api = FakeApi({
        ("GET", "/repos/o/one"): _repo(),
        ("GET", "/repos/o/one/collaborators?all"): [{"login": "kim", "role_name": "write"}],
        ("GET", "/repos/o/one/collaborators?direct"): [{"login": "kim"}],
    })
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_by_people"))
    (row,) = bench.rows
    assert row.label == "kim: access in 1 of 1 repositories, Write in 1"
    for verb in ("make_same", "add_missing", "delete_name", "compare_config"):
        assert not getattr(provider, f"_fits_across_{verb}")(row), verb
