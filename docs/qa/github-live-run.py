#!/usr/bin/env python
"""Live regression run for the GitHub Workbench, against two test repositories.

Runs ``docs/qa/github-regression-testing.md`` against a real repository,
through the same code the Workbench runs: the window's own provider for every
list (:meth:`GitHubWorkbenchProvider.load`), the sheet engine for every
properties sheet (load, change each editable field, read it back, put it
back), and the providers each write command's handler calls. It never drives
the window: anything that needs a screen reader, an ear or eyes is recorded as
"needs Jeff", never guessed.

What it covers is not a hand-kept list. Every list node in ``GITHUB_TREE``,
every sheet in ``SHEETS`` and every command in ``COMMAND_REQUIREMENTS`` has a
row in the results, and ``tests/unit/docs/test_github_live_run_coverage.py``
fails the build when one is added without a scenario or a reason here
(``github_live_verbs.VERBS``). That is the classification as review, as the
other gates do it.

Run it from the repository root, on the computer you are signed in to GitHub
on in QUILL::

    python docs/qa/github-live-run.py --create      # make the two repositories, then the full run
    python docs/qa/github-live-run.py               # the full run (the repositories exist)
    python docs/qa/github-live-run.py --dry-run     # reads only: lists and sheets, writes nothing
    python docs/qa/github-live-run.py --keep        # leave what the run made, to look at it

The token comes, in this order, from ``QUILL_LIVE_GITHUB_TOKEN``, QUILL's
active GitHub account, QUILL's older single token, then ``gh auth token``. It
is never printed, logged or written. Everything the run makes is called
"QUILL live test" and is deleted afterwards (unless ``--keep``); every field
it changes is put back. The run keeps its own local lists (sets, favorites,
snoozes, watches) in a scratch folder, never in your QUILL data. The results
replace the "Live run" section of the plan, whose HTML and EPUB are rendered
again when pandoc is on the PATH.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "qa" / "github-regression-testing.md"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

TAG = "QUILL live test"
REPOSITORY = "quill-workbench-test"
LABELS = ("quill-live-a", "quill-live-b")
MILESTONE = f"{TAG} milestone"
BRANCH = "quill-live-branch"
PROTECTED = "quill-live-protected"
RELEASE_TAG = "v0.0.1-quill-live"
ENVIRONMENT = "quill-live"
VARIABLE = "QUILL_LIVE_VAR"
SECRET = "QUILL_LIVE_SECRET"
WORKFLOW = ".github/workflows/quill-live.yml"
SAMPLE = "src/sample.py"

STATUSES = ("pass", "fail", "not here", "needs Jeff")
"""``not here``: the account, plan or repository has nothing to test it on, said
why; ``needs Jeff``: only a person can judge it (speech, braille, a dialog)."""

FILES: dict[str, str] = {
    "README.md": f"# {TAG}\n\nA repository QUILL's GitHub regression run makes and checks.\n",
    SAMPLE: "".join(f"# line {n}: {TAG}\n" for n in range(1, 13)),
    WORKFLOW: """name: QUILL live test
on:
  workflow_dispatch:
    inputs:
      outcome:
        description: pass or fail
        default: pass
jobs:
  work:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/cache@v4
        with:
          path: cache-dir
          key: quill-live-${{ github.run_id }}
      - run: mkdir -p cache-dir && echo live > cache-dir/a.txt
      - uses: actions/upload-artifact@v4
        with:
          name: quill-live-artifact
          path: src/sample.py
          retention-days: 1
      - run: test "${{ inputs.outcome }}" = pass
""",
    ".github/ISSUE_TEMPLATE/quill-live.yml": f"""name: {TAG} form
description: An issue form the regression run reads.
body:
  - type: textarea
    id: what
    attributes:
      label: What happened
    validations:
      required: true
""",
    ".github/pull_request_template.md": f"## {TAG}\n\nWhat this changes.\n",
}


@dataclass
class Outcome:
    area: str
    item: str
    status: str
    said: str = ""


@dataclass
class Run:
    """Everything one run knows: the token's account, the repositories, what it made."""

    api: Any
    items: Any
    login: str
    repo: str
    second: str
    org: str
    dry_run: bool
    keep: bool
    results: list[Outcome] = field(default_factory=list)
    ids: dict[str, str] = field(default_factory=dict)
    cleanup: list[tuple[str, Callable[[], object]]] = field(default_factory=list)
    scopes: frozenset[str] = frozenset()

    # -- recording ------------------------------------------------------------

    def record(self, area: str, item: str, status: str, said: str = "") -> None:
        assert status in STATUSES, status
        self.results.append(Outcome(area, item, status, _masked(said, self)))
        mark = {"pass": "ok  ", "fail": "FAIL", "not here": "n/a ", "needs Jeff": "Jeff"}[status]
        print(f"[{mark}] {area}: {item}" + (f" -- {_masked(said, self)}" if said else ""))

    def check(self, area: str, item: str, work: Callable[[], object]) -> object:
        """Run *work*; a value or None passes, an exception fails with its message."""
        try:
            said = work()
        except NotHere as why:
            self.record(area, item, "not here", str(why))
            return None
        except Exception as exc:  # noqa: BLE001 - every failure is a result, never a stop
            self.record(area, item, "fail", f"{type(exc).__name__}: {exc}")
            if os.environ.get("QUILL_LIVE_TRACE"):
                traceback.print_exc()
            return None
        self.record(area, item, "pass", said if isinstance(said, str) else "")
        return said

    # -- REST helpers ---------------------------------------------------------

    def rest(
        self, method: str, path: str, body: Mapping[str, object] | None = None, **query: str
    ) -> Any:
        return self.api.rest(method, path, body=body, query=query or None).data

    def exists(self, path: str) -> Any:
        from quill.core.github.rest_transport import GitHubRestError

        try:
            return self.rest("GET", path)
        except GitHubRestError as exc:
            if "404" in str(exc) or getattr(exc, "status", 0) == 404:
                return None
            raise

    def later(self, what: str, undo: Callable[[], object]) -> None:
        """Delete *what* at the end of the run (newest first), unless --keep."""
        self.cleanup.append((what, undo))


from github_live_verbs import NotHere  # noqa: E402 - after the path is set


def _masked(text: str, run: Run | None = None) -> str:
    token = getattr(getattr(run, "api", None), "_token", None)
    return text.replace(token, "(token)") if token and text else text


# -- the token ---------------------------------------------------------------------


def find_token() -> tuple[str, str]:
    """The token and where it came from; never printed."""
    found = os.environ.get("QUILL_LIVE_GITHUB_TOKEN", "").strip()
    if found:
        return found, "QUILL_LIVE_GITHUB_TOKEN"
    try:
        from quill.core.github.accounts import active_github_account_id, load_github_account_token

        account = active_github_account_id()
        found = (load_github_account_token(account) if account else None) or ""
        if found:
            return found, "QUILL's active GitHub account"
        from quill.core.github.token_store import load_github_token

        found = load_github_token() or ""
        if found:
            return found, "QUILL's stored GitHub token"
    except Exception:  # noqa: BLE001 - fall through to gh
        pass
    gh = shutil.which("gh")
    if gh:
        done = subprocess.run([gh, "auth", "token"], capture_output=True, text=True, check=False)
        if done.returncode == 0 and done.stdout.strip():
            return done.stdout.strip(), "gh auth token"
    raise SystemExit(
        "No GitHub token: sign in to GitHub in QUILL (Ctrl+Shift+K), run gh auth login, "
        "or set QUILL_LIVE_GITHUB_TOKEN."
    )


def isolate_local_lists() -> Path:
    """Point QUILL's data folder at a scratch folder under home for the rest of the run."""
    from quill.core import paths

    scratch = Path(tempfile.mkdtemp(prefix="quill-github-live-", dir=Path.home()))
    os.environ["QUILL_DATA_DIR"] = str(scratch)
    paths._DEV_BUILD = True
    return scratch


# -- the repositories -----------------------------------------------------------------


def ensure_repository(run: Run, full: str, *, create: bool, private: bool) -> None:
    if run.exists(f"/repos/{full}") is not None:
        return
    if not create:
        raise SystemExit(f"{full} does not exist. Run again with --create to make it.")
    run.rest(
        "POST",
        "/user/repos",
        {
            "name": full.split("/", 1)[1],
            "description": f"{TAG}: QUILL's GitHub Workbench regression run makes and checks this.",
            "private": private,
            "auto_init": True,
            "has_discussions": True,
            "has_projects": True,
            "has_wiki": False,
        },
    )
    print(f"Made {full}.")
    time.sleep(3)


def put_file(run: Run, repo: str, path: str, text: str, *, branch: str = "") -> None:
    current = run.exists(f"/repos/{repo}/contents/{path}" + (f"?ref={branch}" if branch else ""))
    body: dict[str, object] = {
        "message": f"{TAG}: {path}",
        "content": base64.b64encode(text.encode()).decode(),
    }
    if branch:
        body["branch"] = branch
    if isinstance(current, Mapping):
        if base64.b64decode(str(current.get("content", ""))).decode(errors="replace") == text:
            return
        body["sha"] = current["sha"]
    run.rest("PUT", f"/repos/{repo}/contents/{path}", body)


def seed(run: Run) -> None:
    """One of everything the sheets and commands need, each called "QUILL live test"."""
    repo = run.repo
    head = run.rest("GET", f"/repos/{repo}")
    run.ids["default_branch"] = str(head["default_branch"])
    for path, text in FILES.items():
        run.check("seed", f"file {path}", lambda p=path, t=text: put_file(run, repo, p, t))
    for colour, name in zip(("0e8a16", "1d76db"), LABELS, strict=True):
        if run.exists(f"/repos/{repo}/labels/{name}") is None:
            run.rest(
                "POST", f"/repos/{repo}/labels", {"name": name, "color": colour, "description": TAG}
            )
    milestone = next(
        (
            m
            for m in run.rest("GET", f"/repos/{repo}/milestones", state="all")
            if m["title"] == MILESTONE
        ),
        None,
    ) or run.rest("POST", f"/repos/{repo}/milestones", {"title": MILESTONE, "description": TAG})
    run.ids["milestone"] = str(milestone["number"])
    sha = run.rest("GET", f"/repos/{repo}/git/ref/heads/{run.ids['default_branch']}")["object"][
        "sha"
    ]
    run.ids["sha"] = sha
    for branch in (BRANCH, PROTECTED):
        if run.exists(f"/repos/{repo}/branches/{branch}") is None:
            run.rest("POST", f"/repos/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha})
    put_file(run, repo, "src/branch-change.md", f"{TAG}: a change on {BRANCH}.\n", branch=BRANCH)
    issues = {
        i["title"]: i for i in run.rest("GET", f"/repos/{repo}/issues", state="all", per_page="100")
    }
    for key, title in (("issue", f"{TAG} issue"), ("sub_issue", f"{TAG} sub-issue")):
        found = issues.get(title) or run.rest(
            "POST",
            f"/repos/{repo}/issues",
            {
                "title": title,
                "body": TAG,
                "labels": [LABELS[0]],
                "milestone": int(run.ids["milestone"]),
            },
        )
        run.ids[key] = str(found["number"])
        if found.get("state") == "closed":
            run.rest("PATCH", f"/repos/{repo}/issues/{found['number']}", {"state": "open"})
    comments = run.rest("GET", f"/repos/{repo}/issues/{run.ids['issue']}/comments")
    comment = (
        comments[0]
        if comments
        else run.rest(
            "POST", f"/repos/{repo}/issues/{run.ids['issue']}/comments", {"body": f"{TAG} comment"}
        )
    )
    run.ids["comment"] = str(comment["id"])
    pulls = run.rest("GET", f"/repos/{repo}/pulls", state="open", head=f"{run.login}:{BRANCH}")
    pull = (
        pulls[0]
        if pulls
        else run.rest(
            "POST",
            f"/repos/{repo}/pulls",
            {
                "title": f"{TAG} pull request",
                "head": BRANCH,
                "base": run.ids["default_branch"],
                "body": TAG,
            },
        )
    )
    run.ids["pull"] = str(pull["number"])
    release = run.exists(f"/repos/{repo}/releases/tags/{RELEASE_TAG}") or run.rest(
        "POST",
        f"/repos/{repo}/releases",
        {
            "tag_name": RELEASE_TAG,
            "target_commitish": run.ids["default_branch"],
            "name": f"{TAG} release",
            "body": TAG,
        },
    )
    run.ids["release"] = str(release["id"])
    run.check(
        "seed",
        "environment",
        lambda: run.rest("PUT", f"/repos/{repo}/environments/{ENVIRONMENT}", {}),
    )
    if run.exists(f"/repos/{repo}/actions/variables/{VARIABLE}") is None:
        run.check(
            "seed",
            "Actions variable",
            lambda: run.rest(
                "POST", f"/repos/{repo}/actions/variables", {"name": VARIABLE, "value": "one"}
            ),
        )
    hooks = [
        h
        for h in run.rest("GET", f"/repos/{repo}/hooks")
        if "quill-live" in str(h["config"].get("url"))
    ]
    hook = (
        hooks[0]
        if hooks
        else run.check(
            "seed",
            "webhook",
            lambda: run.rest(
                "POST",
                f"/repos/{repo}/hooks",
                {
                    "name": "web",
                    "active": False,
                    "events": ["issues"],
                    "config": {
                        "url": "https://example.com/quill-live-test",
                        "content_type": "json",
                    },
                },
            ),
        )
    )
    if isinstance(hook, Mapping):
        run.ids["hook"] = str(hook["id"])
    _seed_ruleset(run)
    _seed_protection(run)
    _seed_deploy_key(run)
    _seed_discussion(run)
    _seed_gist(run)
    _seed_project(run)
    deployment = run.check(
        "seed",
        "deployment",
        lambda: run.rest(
            "POST",
            f"/repos/{repo}/deployments",
            {
                "ref": run.ids["default_branch"],
                "environment": ENVIRONMENT,
                "auto_merge": False,
                "required_contexts": [],
            },
        ),
    )
    if isinstance(deployment, Mapping):
        run.ids["deployment"] = str(deployment["id"])
    for name in LABELS[:1]:
        if run.exists(f"/repos/{run.second}/labels/{name}") is None:
            run.rest(
                "POST",
                f"/repos/{run.second}/labels",
                {"name": name, "color": "b60205", "description": "different"},
            )


def _seed_ruleset(run: Run) -> None:
    def make() -> None:
        found = [
            r for r in run.rest("GET", f"/repos/{run.repo}/rulesets") if r["name"].startswith(TAG)
        ]
        ruleset = (
            found[0]
            if found
            else run.rest(
                "POST",
                f"/repos/{run.repo}/rulesets",
                {
                    "name": f"{TAG} ruleset",
                    "target": "branch",
                    "enforcement": "disabled",
                    "conditions": {
                        "ref_name": {"include": ["refs/heads/quill-live-*"], "exclude": []}
                    },
                    "rules": [{"type": "deletion"}],
                },
            )
        )
        run.ids["ruleset"] = str(ruleset["id"])

    run.check("seed", "ruleset", _plan_limited(make, "rulesets"))


def _seed_protection(run: Run) -> None:
    run.check(
        "seed",
        "branch protection",
        _plan_limited(
            lambda: run.rest(
                "PUT",
                f"/repos/{run.repo}/branches/{PROTECTED}/protection",
                {
                    "required_status_checks": None,
                    "enforce_admins": False,
                    "required_pull_request_reviews": None,
                    "restrictions": None,
                },
            ),
            "branch protection",
        ),
    )


def _seed_deploy_key(run: Run) -> None:
    def make() -> None:
        found = [
            k for k in run.rest("GET", f"/repos/{run.repo}/keys") if k["title"].startswith(TAG)
        ]
        if found:
            run.ids["deploy_key"] = str(found[0]["id"])
            return
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        public = (
            Ed25519PrivateKey
            .generate()
            .public_key()
            .public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
            .decode()
        )
        key = run.rest(
            "POST",
            f"/repos/{run.repo}/keys",
            {"title": f"{TAG} key", "key": public, "read_only": True},
        )
        run.ids["deploy_key"] = str(key["id"])

    run.check("seed", "deploy key", make)


def _seed_discussion(run: Run) -> None:
    def make() -> None:
        owner, name = run.repo.split("/")
        data = run.api.graphql(
            "query($o:String!,$n:String!){repository(owner:$o,name:$n){id "
            "discussionCategories(first:10){nodes{id name}} "
            "discussions(first:20){nodes{number title}}}}",
            {"o": owner, "n": name},
        )
        repo = data["repository"]
        mine = [d for d in repo["discussions"]["nodes"] if d["title"].startswith(TAG)]
        if mine:
            run.ids["discussion"] = str(mine[0]["number"])
            return
        categories = repo["discussionCategories"]["nodes"]
        if not categories:
            raise NotHere("the repository has no discussion categories")
        made = run.api.graphql(
            "mutation($r:ID!,$c:ID!,$t:String!,$b:String!){createDiscussion(input:"
            "{repositoryId:$r,categoryId:$c,title:$t,body:$b}){discussion{number}}}",
            {"r": repo["id"], "c": categories[0]["id"], "t": f"{TAG} discussion", "b": TAG},
        )
        run.ids["discussion"] = str(made["createDiscussion"]["discussion"]["number"])

    run.check("seed", "discussion", make)


def _seed_gist(run: Run) -> None:
    def make() -> None:
        mine = [
            g
            for g in run.rest("GET", "/gists", per_page="100")
            if str(g.get("description", "")).startswith(TAG)
        ]
        gist = (
            mine[0]
            if mine
            else run.rest(
                "POST",
                "/gists",
                {
                    "description": f"{TAG} gist",
                    "public": False,
                    "files": {"quill-live.md": {"content": TAG}},
                },
            )
        )
        run.ids["gist"] = str(gist["id"])
        if not run.keep and not mine:
            run.later("the test gist", lambda: run.rest("DELETE", f"/gists/{gist['id']}"))

    run.check("seed", "gist", make)


def _seed_project(run: Run) -> None:
    def make() -> None:
        if "project" not in run.scopes and run.scopes:
            raise NotHere("the token has no project scope (gh auth refresh -s project)")
        viewer = run.api.graphql(
            "query{viewer{id projectsV2(first:50){nodes{id number title}}}}", {}
        )["viewer"]
        mine = [p for p in viewer["projectsV2"]["nodes"] if p["title"].startswith(TAG)]
        project = (
            mine[0]
            if mine
            else run.api.graphql(
                "mutation($o:ID!,$t:String!){createProjectV2(input:"
                "{ownerId:$o,title:$t}){projectV2{id number}}}",
                {"o": viewer["id"], "t": f"{TAG} project"},
            )["createProjectV2"]["projectV2"]
        )
        run.ids["project"] = str(project["number"])
        run.ids["project_id"] = str(project["id"])
        if not run.keep and not mine:
            run.later(
                "the test project",
                lambda: run.api.graphql(
                    "mutation($p:ID!){deleteProjectV2(input:{projectId:$p}){projectV2{id}}}",
                    {"p": project["id"]},
                ),
            )

    run.check("seed", "project", make)


def _plan_limited(work: Callable[[], object], what: str) -> Callable[[], object]:
    def wrapped() -> object:
        try:
            return work()
        except Exception as exc:
            if "403" in str(exc) and ("upgrade" in str(exc).lower() or "plan" in str(exc).lower()):
                raise NotHere(f"GitHub's plan for this repository has no {what}") from exc
            raise

    return wrapped


def run_the_workflow(run: Run) -> None:
    """Dispatch the test workflow and wait: the run, job, artifact and cache lists need one."""
    from quill.core.github.items_provider import GitHubItemsProvider

    assert isinstance(run.items, GitHubItemsProvider)
    before = {
        r["id"]
        for r in run.rest("GET", f"/repos/{run.repo}/actions/runs", per_page="20")["workflow_runs"]
    }
    run.items.dispatch_workflow(
        run.repo, "quill-live.yml", run.ids["default_branch"], inputs={"outcome": "pass"}
    )
    deadline = time.monotonic() + 420
    while time.monotonic() < deadline:
        time.sleep(10)
        runs = run.rest("GET", f"/repos/{run.repo}/actions/runs", per_page="20")["workflow_runs"]
        new = [r for r in runs if r["id"] not in before]
        if new and new[0]["status"] == "completed":
            run.ids["run"] = str(new[0]["id"])
            jobs = run.rest("GET", f"/repos/{run.repo}/actions/runs/{new[0]['id']}/jobs")["jobs"]
            run.ids["job"] = str(jobs[0]["id"]) if jobs else ""
            arts = run.rest("GET", f"/repos/{run.repo}/actions/runs/{new[0]['id']}/artifacts")[
                "artifacts"
            ]
            run.ids["artifact"] = str(arts[0]["id"]) if arts else ""
            workflow = run.rest("GET", f"/repos/{run.repo}/actions/workflows/quill-live.yml")
            run.ids["workflow"] = str(workflow["id"])
            return
    raise TimeoutError("the test workflow did not finish within seven minutes")


# -- lists: every node in the tree ---------------------------------------------------


def run_lists(run: Run) -> None:
    from quill.core.github.workbench_tree import GITHUB_TREE
    from quill.core.workbench.filters import Query
    from quill.core.workbench.tree import Scope
    from quill.ui.github_workbench_window import GitHubWorkbenchProvider
    from quill.ui.workbench_frame import NodeRef

    said: list[str] = []
    provider = GitHubWorkbenchProvider(run.items, run.repo, announce=said.append)
    provider._people.append(run.login)
    provider._organizations.append(run.org)
    instance = {"repository": run.repo, "person": run.login, "organization": run.org, "": ""}
    groups = {"": GITHUB_TREE._nodes, **GITHUB_TREE._templates}
    for template, nodes in groups.items():
        for node in nodes.values():
            if not node.loader:
                continue
            where = instance[template] or (run.repo if node.scope is Scope.REPOSITORY else "")
            ref = NodeRef(template, node.key, where)
            name = f"{template or 'top'} > {node.label} ({node.loader})"

            def load(node: Any = node, ref: Any = ref) -> str:
                blocked = provider.unavailable(ref, node)
                if blocked:
                    raise NotHere(blocked)
                rows = provider.load(ref, node, Query())
                return f"{len(rows)} rows"

            run.check("list", name, load)


# -- sheets: load every one, change every editable field, put it back -----------------


#: Fields a run never changes, with why; everything else on a sheet is changed and put back.
LEAVE_ALONE: dict[str, dict[str, str]] = {
    "person": {
        key: "your own profile: the run changes nothing on it but who you follow"
        for key in ("blocked", "name", "bio", "company", "location", "blog", "twitter", "hireable")
    },
    "pull_request": {"base": "changing the base retargets the pull request's whole diff"},
    "release": {"tag": "a release's tag is its address in the run", "target": "a tag's commit"},
    "repository": {
        "pages_cname": "Pages is not turned on for the test repository",
        "pages_https": "Pages is not turned on for the test repository",
        "actions_enabled": "turning Actions off would stop the run's own workflow",
        "visibility": "changing visibility can lose plan features half way through the run",
    },
    "issue": {"issue_type": "issue types belong to organizations; the test repository is personal"},
}

#: Fields that each save alone, after the rest: they move or freeze the object.
SOLO = {"name", "archived", "default_branch", "state", "locked", "draft"}


def sheet_idents(run: Run) -> dict[str, dict[str, str] | str]:
    """The object each sheet is tried on, or why there is none."""
    repo, ids = run.repo, run.ids

    first = _first_of(run)
    return {
        "repository": {"repo": repo},
        "issue": {"repo": repo, "number": ids["issue"]},
        "pull_request": {"repo": repo, "number": ids["pull"]},
        "label": {"repo": repo, "name": LABELS[1]},
        "milestone": {"repo": repo, "number": ids["milestone"]},
        "comment": {"repo": repo, "id": ids["comment"]},
        "branch": {"repo": repo, "branch": BRANCH},
        "branch_protection": {"repo": repo, "branch": PROTECTED},
        "commit": {"repo": repo, "sha": ids["sha"]},
        "tag": {"repo": repo, "tag": RELEASE_TAG},
        "release": {"repo": repo, "tag": RELEASE_TAG},
        "release_asset": {"repo": repo, "tag": RELEASE_TAG},
        "file": {"repo": repo, "path": SAMPLE},
        "environment": {"repo": repo, "name": ENVIRONMENT},
        "variable": {"repo": repo, "name": VARIABLE},
        "secret": {"repo": repo, "name": SECRET},
        "collaborator": {"repo": repo, "login": run.login},
        "invitation": "nobody is invited to the test repository; inviting needs a second account",
        "webhook": _with(ids, "hook", {"repo": repo}, "id", "the webhook could not be made"),
        "ruleset": _with(ids, "ruleset", {"repo": repo}, "id", "no ruleset: see the seed result"),
        "deploy_key": _with(
            ids, "deploy_key", {"repo": repo}, "id", "no deploy key: see the seed result"
        ),
        "deployment": _with(
            ids, "deployment", {"repo": repo}, "id", "no deployment: see the seed result"
        ),
        "workflow": _with(ids, "workflow", {"repo": repo}, "id", "the test workflow did not run"),
        "run": _with(ids, "run", {"repo": repo}, "id", "the test workflow did not run"),
        "job": _with(ids, "job", {"repo": repo}, "id", "the test workflow did not run"),
        "artifact": _with(
            ids, "artifact", {"repo": repo}, "id", "the test workflow kept no artifact"
        ),
        "cache": {"repo": repo},
        "gist": _with(ids, "gist", {}, "id", "no gist: see the seed result"),
        "discussion": _with(
            ids, "discussion", {"repo": repo}, "number", "no discussion: see the seed result"
        ),
        "project": _with(
            ids,
            "project",
            {"owner": run.login, "me": "1"},
            "number",
            "no project: see the seed result",
        ),
        "person": {"login": run.login, "me": "1"},
        "organization": {"org": run.org, "me": ""},
        "team": first.get("team") or "the organization has no team this account can see",
        "issue_type": {"org": run.org},
        "notification": first.get("notification") or "the account has no notification to read",
        "runner": first.get("runner") or "the test repository has no self-hosted runner",
        "codespace": first.get("codespace") or "the account has no codespace",
        "package": first.get("package") or "the account has no package",
        "security_alert": first.get("security_alert")
        or "the test repository has no security alert",
    }


def _with(
    ids: Mapping[str, str], key: str, base: dict[str, str], as_key: str, why: str
) -> dict[str, str] | str:
    return {**base, as_key: ids[key]} if ids.get(key) else why


def _first_of(run: Run) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}

    def first(path: str, **query: str) -> Any:
        try:
            data = run.rest("GET", path, **query)
        except Exception:  # noqa: BLE001 - nothing there is "not here"
            return None
        if isinstance(data, Mapping):
            data = next((v for v in data.values() if isinstance(v, list)), [])
        return data[0] if data else None

    if team := first(f"/orgs/{run.org}/teams"):
        found["team"] = {"org": run.org, "team": team["slug"], "me": ""}
    if note := first("/notifications", all="true"):
        found["notification"] = {"id": str(note["id"])}
    if runner := first(f"/repos/{run.repo}/actions/runners"):
        found["runner"] = {"repo": run.repo, "id": str(runner["id"])}
    if space := first("/user/codespaces"):
        found["codespace"] = {"name": space["name"]}
    for kind in ("container", "npm", "maven", "rubygems", "nuget"):
        if package := first("/user/packages", package_type=kind):
            found["package"] = {
                "name": package["name"],
                "package_type": kind,
                "owner_path": f"users/{run.login}",
            }
            break
    if alert := first(f"/repos/{run.repo}/dependabot/alerts"):
        found["security_alert"] = {
            "repo": run.repo,
            "number": str(alert["number"]),
            "alert_path": "dependabot/alerts",
        }
    return found


def run_sheets(run: Run) -> None:
    from quill.core.github.sheet_catalog import SHEETS

    idents = sheet_idents(run)
    for kind in sorted(SHEETS):
        ident = idents.get(kind, "no object for this sheet in the run")
        if isinstance(ident, str):
            run.record("sheet", f"{kind}: load", "not here", ident)
            continue
        loaded = run.check(
            "sheet", f"{kind}: load", lambda k=kind, i=ident: _load_said(run, SHEETS[k], i)
        )
        if loaded is None or run.dry_run:
            continue
        _round_trip(run, SHEETS[kind], ident)


def _load_said(run: Run, sheet: Any, ident: Mapping[str, str]) -> str:
    from quill.core.github.sheet_engine import load

    loaded = load(run.api, sheet, ident)
    filled = sum(1 for v in loaded.values.values() if v not in (None, "", ()))
    return f"{filled} fields filled" + (
        f"; optional reads missing: {', '.join(loaded.missing)}" if loaded.missing else ""
    )


def _choices(run: Run, sheet: Any, ident: Mapping[str, str]) -> dict[str, dict[str, object]]:
    from quill.core.github.sheet_engine import load_options

    found = {key: dict(values) for key, values in sheet.fixed.items()}
    found.update(load_options(run.api, sheet, ident))
    for spec in sheet.sheet.fields():
        if spec.choices and spec.key not in found:
            found[spec.key] = {choice: choice for choice in spec.choices}
    return found


def changed_value(spec: Any, before: object, choices: Mapping[str, object]) -> object:
    """A different value for *spec*, or ``NotImplemented`` when there is none to try."""
    from quill.core.workbench.properties import FieldKind

    kind = spec.kind
    if kind is FieldKind.CHECK:
        return not bool(before)
    if kind is FieldKind.NUMBER:
        if isinstance(before, bool) or not str(before or "").lstrip("-").isdigit():
            return 2  # neither 0 nor 1, so never equal to a stray boolean either
        return int(str(before)) + 1
    if kind is FieldKind.DATE:
        return "2031-01-15" if str(before or "")[:10] != "2031-01-15" else "2032-02-16"
    if kind is FieldKind.CHOICE:
        options = [c for c in choices if c != before and c]
        return options[0] if options else NotImplemented
    if kind in (FieldKind.CHECKLIST, FieldKind.LIST):
        have = tuple(before) if isinstance(before, tuple) else ()
        extra = [c for c in choices if c not in have]
        if kind is FieldKind.LIST and not extra:
            extra = [f"quill-live-{spec.key.replace('_', '-')}"]
        return (*have, extra[0]) if extra else NotImplemented
    if kind in (FieldKind.TEXT, FieldKind.MULTILINE, FieldKind.LINK):
        text = str(before or "")
        if spec.key == "colour":
            return "fbca04" if text.lower() != "fbca04" else "0e8a16"
        if spec.key in ("homepage", "address", "blog"):
            return "https://example.com/quill-live-other"
        if spec.key == "default_branch":
            return BRANCH
        if spec.key in ("name", "tag"):
            return f"{text}-renamed"[:90]
        if spec.key == "secret_value":
            return "quill-live-secret-value"
        if spec.key == "value":
            return "two" if text != "two" else "three"
        return f"{text} (changed by the {TAG})".strip()
    return NotImplemented


def _round_trip(run: Run, sheet: Any, ident: Mapping[str, str]) -> None:
    """Change every editable field, read it back, put it back: one save, then the solo ones."""
    from quill.core.github.sheet_engine import inverse, load, save
    from quill.core.workbench.properties import FieldChange

    leave = LEAVE_ALONE.get(sheet.kind, {})
    loaded = load(run.api, sheet, ident).values
    choices = _choices(run, sheet, ident)
    batch: list[Any] = []
    solo: list[Any] = []
    for spec in sheet.sheet.fields():
        if spec.readonly or spec.key not in sheet.writes:
            continue
        name = f"{sheet.kind}: {spec.label}"
        if spec.key in leave:
            run.record("sheet field", name, "not here", leave[spec.key])
            continue
        before = loaded.get(spec.key)
        after = changed_value(spec, before, choices.get(spec.key, {}))
        if after is NotImplemented:
            run.record("sheet field", name, "not here", "nothing to change it to on this account")
            continue
        change = FieldChange(spec.key, spec.label, before, after)  # type: ignore[arg-type]
        (solo if spec.key in SOLO else batch).append(change)
    current = dict(ident)
    for group in ([batch] if batch else []) + [[c] for c in solo]:
        fresh = load(run.api, sheet, current).values
        group = [FieldChange(c.key, c.label, fresh.get(c.key), c.after) for c in group]
        try:
            outcome = save(run.api, sheet, current, group, loaded=fresh, choices=choices)
        except Exception as exc:  # noqa: BLE001
            for change in group:
                run.record("sheet field", f"{sheet.kind}: {change.label}", "fail", f"save: {exc}")
            continue
        for change, why in outcome.failed:
            run.record("sheet field", f"{sheet.kind}: {change.label}", "fail", _short(why))
        for change in outcome.not_taken:
            run.record(
                "sheet field",
                f"{sheet.kind}: {change.label}",
                "fail",
                "sent, but GitHub kept the old value",
            )
        for found in outcome.conflicts:
            run.record(
                "sheet field",
                f"{sheet.kind}: {getattr(found, 'label', found)}",
                "fail",
                "conflict on a fresh load",
            )
        moved = sheet.ident_after(current, outcome.done)
        back, cannot = inverse(sheet, outcome.done)
        restored_ok: set[str] = set()
        if back:
            try:
                undo = save(
                    run.api,
                    sheet,
                    moved,
                    back,
                    loaded=outcome.after,
                    choices=choices,
                    check_conflicts=False,
                )
                restored_ok = {c.key for c in undo.done}
                moved = sheet.ident_after(moved, undo.done)
            except Exception as exc:  # noqa: BLE001
                print(f"  could not put {sheet.kind} back: {exc}")
        current = moved
        for change in outcome.done:
            if change.key in restored_ok:
                run.record(
                    "sheet field",
                    f"{sheet.kind}: {change.label}",
                    "pass",
                    "changed, read back, put back",
                )
            elif change.label in cannot:
                run.record(
                    "sheet field",
                    f"{sheet.kind}: {change.label}",
                    "pass",
                    "changed and read back; GitHub cannot undo it",
                )
            else:
                run.record(
                    "sheet field",
                    f"{sheet.kind}: {change.label}",
                    "fail",
                    "changed, but not put back",
                )


def _short(text: str, limit: int = 240) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


# -- the report ----------------------------------------------------------------------


def report(run: Run, started: dt.datetime, token_from: str) -> str:
    counts = {status: sum(1 for r in run.results if r.status == status) for status in STATUSES}
    lines = [
        "## Live run",
        "",
        f"Run on {started:%Y-%m-%d at %H:%M} UTC against `{run.repo}` and `{run.second}`, "
        f"signed in as {run.login} ({token_from}), organization reads against `{run.org}`"
        + (", reads only (`--dry-run`)" if run.dry_run else "")
        + ".",
        "",
        f"**{counts['pass']} passed, {counts['fail']} failed, {counts['not here']} not here, "
        f"{counts['needs Jeff']} need Jeff.**",
        "",
    ]
    for area in dict.fromkeys(r.area for r in run.results):
        rows = [r for r in run.results if r.area == area]
        failed = sum(1 for r in rows if r.status == "fail")
        lines += [
            f"### {area.capitalize()} ({len(rows)}, {failed} failed)",
            "",
            "| Item | Result | Detail |",
            "|---|---|---|",
        ]
        lines += [f"| {_cell(r.item)} | {r.status} | {_cell(r.said)} |" for r in rows]
        lines.append("")
    return "\n".join(lines)


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def write_report(section: str) -> None:
    text = DOC.read_text(encoding="utf-8") if DOC.exists() else ""
    head, marker, _rest = text.partition("## Live run")
    DOC.write_text((head if marker else text.rstrip() + "\n\n") + section + "\n", encoding="utf-8")
    print(f"Wrote the Live run section of {DOC.relative_to(ROOT)}.")
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        print("pandoc is not on the PATH; render the .html and .epub before committing.")
        return
    template = ROOT / "docs" / "pandoc" / "quill-accessible.html5"
    for suffix, fmt in ((".html", "html5"), (".epub", "epub3")):
        args = [pandoc, str(DOC), "-f", "gfm", "-t", fmt, "-s", "--metadata", "lang=en"]
        if fmt == "html5" and template.exists():
            args += ["--template", str(template)]
        subprocess.run([*args, "-o", str(DOC.with_suffix(suffix))], check=False, cwd=ROOT)
    print("Rendered the HTML and EPUB.")


# -- the run ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--repository", default="", help="owner/name (default: <you>/quill-workbench-test)"
    )
    parser.add_argument(
        "--org", default="Community-Access", help="an organization to read (never changed)"
    )
    parser.add_argument(
        "--create", action="store_true", help="make the test repositories if they are missing"
    )
    parser.add_argument(
        "--private", action="store_true", help="make them private (fewer features on free plans)"
    )
    parser.add_argument("--dry-run", action="store_true", help="reads only")
    parser.add_argument("--keep", action="store_true", help="leave what the run made")
    parser.add_argument(
        "--only", default="", help="comma-separated areas: seed,lists,sheets,verbs,features"
    )
    args = parser.parse_args(argv)

    token, token_from = find_token()
    scratch = isolate_local_lists()
    from quill.core.github.items_provider import GitHubItemsProvider
    from quill.core.github.workbench_api import TokenApi

    api = TokenApi(token)
    me = api.rest("GET", "/user")
    login = str(me.data["login"])
    scopes = frozenset(s.strip() for s in me.header("x-oauth-scopes").split(",") if s.strip())
    repo = args.repository or f"{login}/{REPOSITORY}"
    run = Run(
        api=api,
        items=GitHubItemsProvider(token),
        login=login,
        repo=repo,
        second=f"{repo}-2",
        org=args.org,
        dry_run=args.dry_run,
        keep=args.keep,
        scopes=scopes,
    )
    only = {a.strip() for a in args.only.split(",") if a.strip()}
    started = dt.datetime.now(dt.UTC)
    print(
        f"Signed in as {login} ({token_from}); "
        f"scopes: {', '.join(sorted(scopes)) or 'fine-grained token'}."
    )
    try:
        if not args.dry_run:
            for full in (run.repo, run.second):
                ensure_repository(run, full, create=args.create, private=args.private)
        if not only or "seed" in only:
            if args.dry_run:
                _adopt_existing(run)
            else:
                seed(run)
                run.check("seed", "test workflow run", lambda: run_the_workflow(run))
        else:
            _adopt_existing(run)
        if not only or "lists" in only:
            run_lists(run)
        if not only or "sheets" in only:
            run_sheets(run)
        import github_live_verbs as verbs

        if not only or "verbs" in only:
            verbs.run_verbs(run)
        if not only or "features" in only:
            verbs.run_features(run)
    finally:
        for what, undo in reversed(run.cleanup):
            if run.keep:
                break
            try:
                undo()
            except Exception as exc:  # noqa: BLE001
                print(f"Could not remove {what}: {exc}")
        shutil.rmtree(scratch, ignore_errors=True)
    section = report(run, started, token_from)
    write_report(section)
    failed = sum(1 for r in run.results if r.status == "fail")
    print(f"\n{len(run.results)} results, {failed} failed. Written to {DOC.relative_to(ROOT)}.")
    return 1 if failed else 0


def _adopt_existing(run: Run) -> None:
    """For a read-only run: find what an earlier full run made, without making anything."""
    repo = run.repo
    head = run.exists(f"/repos/{repo}")
    if head is None:
        raise SystemExit(f"{repo} does not exist yet: run once without --dry-run, with --create.")
    run.ids["default_branch"] = str(head["default_branch"])
    run.ids["sha"] = run.rest("GET", f"/repos/{repo}/commits/{head['default_branch']}")["sha"]
    issues = run.rest("GET", f"/repos/{repo}/issues", state="all", per_page="100")
    for key, title in (("issue", f"{TAG} issue"), ("sub_issue", f"{TAG} sub-issue")):
        hit = next((i for i in issues if i["title"] == title), None)
        run.ids[key] = str(hit["number"]) if hit else ""
    pull = next((i for i in issues if i["title"] == f"{TAG} pull request"), None)
    run.ids["pull"] = str(pull["number"]) if pull else ""
    milestone = next(
        (
            m
            for m in run.rest("GET", f"/repos/{repo}/milestones", state="all")
            if m["title"] == MILESTONE
        ),
        None,
    )
    run.ids["milestone"] = str(milestone["number"]) if milestone else ""
    comments = (
        run.rest("GET", f"/repos/{repo}/issues/{run.ids['issue']}/comments")
        if run.ids["issue"]
        else []
    )
    run.ids["comment"] = str(comments[0]["id"]) if comments else ""


if __name__ == "__main__":
    raise SystemExit(main())
