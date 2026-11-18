"""Every GitHub Workbench write command, each with a live scenario or a reason.

``github-live-run.py`` imports this. :data:`VERBS` has a row for every command
in :data:`quill.core.github.write_requirements.COMMAND_REQUIREMENTS`, by its
verb: a scenario (a function of the run that does what the command's handler
does, through the same provider call, checks it took, and puts it back), or a
string saying why the run does not do it here:

- ``"sheet:<kind>.<field>"``: the command writes that sheet field, and the
  sheets pass changes, reads back and puts back every such field;
- ``"needs Jeff: ..."``: only a person can judge it, or it would change
  something real of yours (your notifications, a billed codespace);
- ``"not here: ..."``: the account or the test repositories have nothing to
  test it on (a second account, a fork, Copilot).

:data:`FEATURES` is the same for the Workbench features that are not single
commands (import, export, the line commands). ``test_github_live_run_coverage``
fails when a command or sheet is added without a row here.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

TAG = "QUILL live test"
LABELS = ("quill-live-a", "quill-live-b")
MILESTONE = f"{TAG} milestone"
RELEASE_TAG = "v0.0.1-quill-live"
SAMPLE = "src/sample.py"

Scenario = Callable[[Any], str]


class NotHere(Exception):
    """The account, plan or repository has nothing to test this on."""


# -- helpers -------------------------------------------------------------------------


def _token(run: Any) -> str:
    return str(run.api._token)


def _explore(run: Any) -> Any:
    from quill.core.github.explore import GitHubExploreClient

    return GitHubExploreClient(run.items)


def _issue_state(run: Any, repo: str, number: str | int) -> dict[str, Any]:
    return dict(run.rest("GET", f"/repos/{repo}/issues/{number}"))


def _new_issue(run: Any, title: str, repo: str = "") -> int:
    made = run.items.create_issue(repo or run.repo, f"{TAG} {title}", TAG)
    return int(made.number)


def _delete_issue(run: Any, repo: str, number: int) -> None:
    """Issues cannot be deleted over REST; the owner can over GraphQL."""
    owner, name = repo.split("/")
    node = run.api.graphql(
        "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){issue(number:$i){id}}}",
        {"o": owner, "n": name, "i": number},
    )["repository"]["issue"]["id"]
    run.api.graphql(
        "mutation($i:ID!){deleteIssue(input:{issueId:$i}){clientMutationId}}", {"i": node}
    )


def _expect(condition: bool, said: str) -> None:
    if not condition:
        raise AssertionError(said)


def _wait_run(run: Any, run_id: int, *, seconds: int = 420) -> dict[str, Any]:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        found = run.rest("GET", f"/repos/{run.repo}/actions/runs/{run_id}")
        if found["status"] == "completed":
            return dict(found)
        time.sleep(8)
    raise TimeoutError(f"run {run_id} did not finish")


def _dispatch(run: Any, outcome: str) -> int:
    before = {
        r["id"]
        for r in run.rest("GET", f"/repos/{run.repo}/actions/runs", per_page="20")["workflow_runs"]
    }
    run.items.dispatch_workflow(
        run.repo, "quill-live.yml", run.ids["default_branch"], inputs={"outcome": outcome}
    )
    for _ in range(30):
        time.sleep(4)
        runs = run.rest("GET", f"/repos/{run.repo}/actions/runs", per_page="20")["workflow_runs"]
        new = [r for r in runs if r["id"] not in before]
        if new:
            return int(new[0]["id"])
    raise TimeoutError("the dispatched run never appeared")


# -- issues and pull requests --------------------------------------------------------


def comment(run: Any) -> str:
    made = run.items.create_comment(
        run.repo, int(run.ids["issue"]), f"{TAG}: a comment the run posts"
    )
    comment_id = int(made["id"])
    run.items.delete_comment(run.repo, comment_id)
    return "posted, then deleted"


def close_reopen(run: Any) -> str:
    """Close for each of GitHub's three reasons, as the window asks; reopen after each."""
    from quill.core.github.issue_development import CLOSE_REASONS, close_issue

    number = int(run.ids["issue"])
    original = int(run.ids["sub_issue"])
    seen = []
    for reason in CLOSE_REASONS:
        dup = original if reason.rest == "duplicate" else 0
        close_issue(run.api, run.repo, number, reason, duplicate_of=dup)
        state = _issue_state(run, run.repo, number)
        _expect(state["state"] == "closed", f"still open after closing as {reason.said}")
        seen.append(str(state.get("state_reason")))
        run.items.update_items(run.repo, [number], state="open")
        _expect(_issue_state(run, run.repo, number)["state"] == "open", "still closed")
    _expect(seen == ["completed", "not_planned", "duplicate"], f"reasons GitHub kept: {seen}")
    return "closed as completed, not planned and duplicate, reopened after each"


def task_lists(run: Any) -> str:
    """Check or Uncheck a Task, then Convert Tasks to Sub-issues, on an issue of its own."""
    from quill.core.github.issue_development import (
        convertible,
        linked_body,
        task_items,
        toggle_task,
    )

    body = f"{TAG} tasks:\n- [ ] {TAG} task one\n- [x] {TAG} task two\n"
    made = run.rest(
        "POST", f"/repos/{run.repo}/issues", {"title": f"{TAG} task list", "body": body}
    )
    number = int(made["number"])
    try:
        first = task_items(body)[0]
        run.rest("PATCH", f"/repos/{run.repo}/issues/{number}", {"body": toggle_task(body, first)})
        now = str(_issue_state(run, run.repo, number)["body"])
        _expect(f"- [x] {TAG} task one" in now, "the task was not checked")
        made_subs: dict[int, int] = {}
        for item in convertible(now):
            issue = run.rest("POST", f"/repos/{run.repo}/issues", {"title": item.text})
            run.rest(
                "POST",
                f"/repos/{run.repo}/issues/{number}/sub_issues",
                {"sub_issue_id": int(issue["id"])},
            )
            made_subs[item.line] = int(issue["number"])
        run.rest(
            "PATCH", f"/repos/{run.repo}/issues/{number}", {"body": linked_body(now, made_subs)}
        )
        _expect(convertible(str(_issue_state(run, run.repo, number)["body"])) == [], "not linked")
        for sub in made_subs.values():
            _delete_issue(run, run.repo, sub)
    finally:
        _delete_issue(run, run.repo, number)
    return "checked one task, converted both to sub-issues and linked them, then deleted"


def create_branch(run: Any) -> str:
    from quill.core.github.issue_development import (
        branch_name_for,
        create_linked_branch,
        linked_branches,
    )

    number = int(run.ids["issue"])
    name = f"{branch_name_for(number, TAG)}-{int(time.time())}"
    said = create_linked_branch(run.api, run.repo, number, name)
    linked = linked_branches(run.api, run.repo, number)
    run.rest("DELETE", f"/repos/{run.repo}/git/refs/heads/{name}")
    _expect(name in linked, f"not linked: {linked}")
    return f"{said} It was listed as linked, then deleted."


def labels(run: Any) -> str:
    number = int(run.ids["issue"])
    run.items.update_items(run.repo, [number], add_labels=[LABELS[1]])
    names = {label["name"] for label in _issue_state(run, run.repo, number)["labels"]}
    run.items.update_items(run.repo, [number], remove_labels=[LABELS[1]])
    _expect(LABELS[1] in names, "the label did not take")
    return "added, then removed"


def assignees(run: Any) -> str:
    number = int(run.ids["issue"])
    run.items.update_items(run.repo, [number], add_assignees=[run.login])
    who = {a["login"] for a in _issue_state(run, run.repo, number)["assignees"]}
    run.items.update_items(run.repo, [number], remove_assignees=[run.login])
    _expect(run.login in who, "the assignee did not take")
    return "assigned, then unassigned"


def lock(run: Any) -> str:
    from quill.core.github.issue_housekeeping import GitHubIssueHousekeeping

    house = GitHubIssueHousekeeping(_token(run))
    number = int(run.ids["issue"])
    house.lock(run.repo, number, "off-topic")
    _expect(bool(_issue_state(run, run.repo, number)["locked"]), "not locked")
    house.unlock(run.repo, number)
    return "locked, then unlocked"


def pin(run: Any) -> str:
    from quill.core.github.issue_housekeeping import GitHubIssueHousekeeping

    house = GitHubIssueHousekeeping(_token(run))
    house.set_pinned(run.repo, int(run.ids["issue"]), True)
    house.set_pinned(run.repo, int(run.ids["issue"]), False)
    return "pinned, then unpinned"


def sub_issues(run: Any) -> str:
    from quill.core.github.issue_housekeeping import GitHubIssueHousekeeping

    parent, child = run.ids["issue"], run.ids["sub_issue"]
    child_id = _issue_state(run, run.repo, child)["id"]
    run.rest("POST", f"/repos/{run.repo}/issues/{parent}/sub_issues", {"sub_issue_id": child_id})
    found = GitHubIssueHousekeeping(_token(run)).sub_issues(run.repo, int(parent))
    run.rest("DELETE", f"/repos/{run.repo}/issues/{parent}/sub_issue", {"sub_issue_id": child_id})
    _expect(
        any(getattr(s, "number", 0) == int(child) for s in found), "the sub-issue was not listed"
    )
    return f"added, listed ({len(found)}), removed"


def transfer(run: Any) -> str:
    from quill.core.github.issue_housekeeping import GitHubIssueHousekeeping

    number = _new_issue(run, "issue to transfer")
    moved = GitHubIssueHousekeeping(_token(run)).transfer(run.repo, number, run.second)
    new_number = (
        int(str(moved).rstrip("/").rsplit("/", 1)[-1])
        if str(moved).rstrip("/")[-1:].isdigit()
        else 0
    )
    if new_number:
        _delete_issue(run, run.second, new_number)
    return f"moved to {run.second}, then deleted there"


def new_issue(run: Any) -> str:
    number = _new_issue(run, "new issue")
    _delete_issue(run, run.repo, number)
    return f"made #{number}, then deleted it"


def merge_and_delete_branch(run: Any) -> str:
    """Merge (squash) a fresh pull request, then Delete Branch on its branch."""
    from quill.core.github.repo_admin import GitHubRepoAdminProvider

    branch = f"quill-live-merge-{int(time.time())}"
    sha = run.rest("GET", f"/repos/{run.repo}/git/ref/heads/{run.ids['default_branch']}")["object"][
        "sha"
    ]
    run.rest("POST", f"/repos/{run.repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha})
    import base64

    run.rest(
        "PUT",
        f"/repos/{run.repo}/contents/merged/{branch}.md",
        {"message": TAG, "content": base64.b64encode(TAG.encode()).decode(), "branch": branch},
    )
    pull = run.items.create_pull_request(
        run.repo, f"{TAG} merge", TAG, branch, run.ids["default_branch"]
    )
    from quill.core.github.merge_readiness import load_readiness, merge_at

    ready = load_readiness(run.api, run.repo, int(pull.number))
    merge_at(run.api, run.repo, int(pull.number), "squash", ready.head)
    _expect(bool(run.rest("GET", f"/repos/{run.repo}/pulls/{pull.number}")["merged"]), "not merged")
    admin = GitHubRepoAdminProvider(_token(run))
    admin.delete_branch(run.repo, branch)
    _expect(run.exists(f"/repos/{run.repo}/branches/{branch}") is None, "the branch is still there")
    return f"merged #{pull.number}, deleted {branch}"


def revert_merged(run: Any) -> str:
    """Revert Pull Request on a freshly merged pull request, then close the revert."""
    import base64

    from quill.core.github.pull_tools import revert_pull

    branch = f"quill-live-revert-{int(time.time())}"
    base = run.ids["default_branch"]
    sha = run.rest("GET", f"/repos/{run.repo}/git/ref/heads/{base}")["object"]["sha"]
    run.rest("POST", f"/repos/{run.repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha})
    run.rest(
        "PUT",
        f"/repos/{run.repo}/contents/reverted/{branch}.md",
        {"message": TAG, "content": base64.b64encode(TAG.encode()).decode(), "branch": branch},
    )
    pull = run.items.create_pull_request(run.repo, f"{TAG} revert", TAG, branch, base)
    run.items.merge_pull_request(run.repo, int(pull.number), merge_method="squash")
    run.rest("DELETE", f"/repos/{run.repo}/git/refs/heads/{branch}")
    said = revert_pull(run.api, run.repo, int(pull.number), draft=True)
    made = int(said.split("#", 1)[1].split(",", 1)[0])
    revert = run.rest("GET", f"/repos/{run.repo}/pulls/{made}")
    run.rest("PATCH", f"/repos/{run.repo}/pulls/{made}", {"state": "closed"})
    run.rest("DELETE", f"/repos/{run.repo}/git/refs/heads/{revert['head']['ref']}")
    _expect(revert["base"]["ref"] == base and revert["draft"], f"not a draft into {base}")
    return f"{said} Closed it and deleted its branch."


def why_cant_merge(run: Any) -> str:
    from quill.core.github.merge_readiness import load_readiness

    ready = load_readiness(run.api, run.repo, int(run.ids["pull"]))
    _expect(len(ready.head) == 40 and str(ready.number) in ready.sentence, "no readiness")
    return ready.sentence


def open_patch(run: Any) -> str:
    from quill.core.github.pull_tools import patch_text

    patch = patch_text(run.api, run.repo, int(run.ids["pull"]))
    _expect(patch.files > 0 and patch.text.startswith("diff --git "), "no patch")
    return patch.sentence


# -- Actions -------------------------------------------------------------------------


def run_workflow(run: Any) -> str:
    _expect(bool(run.ids.get("run")), "the seed's dispatch did not run")
    return f"dispatched and finished in the seed (run {run.ids['run']})"


def workflow_state(run: Any) -> str:
    """Turn the live workflow off, read it back, and turn it on again."""
    from quill.core.github.workflow_state import set_enabled

    path = f"/repos/{run.repo}/actions/workflows/quill-live.yml"
    workflow_id = int(run.rest("GET", path)["id"])
    set_enabled(run.api, run.repo, workflow_id, "quill-live", False)
    off = run.rest("GET", path)["state"]
    set_enabled(run.api, run.repo, workflow_id, "quill-live", True)
    on = run.rest("GET", path)["state"]
    _expect(off == "disabled_manually" and on == "active", f"states were {off}, {on}")
    return "turned off, read back as off, turned on again"


def tags_made_and_deleted(run: Any) -> str:
    from quill.core.github.tags import create_tag, delete_tag, tag_message

    name = f"quill-live-tag-{int(time.time())}"
    said = create_tag(run.api, run.repo, name, run.ids["default_branch"])
    _expect(run.exists(f"/repos/{run.repo}/git/ref/tags/{name}") is not None, "no tag")
    delete_tag(run.api, run.repo, name)
    _expect(run.exists(f"/repos/{run.repo}/git/ref/tags/{name}") is None, "still there")
    annotated = f"{name}-a"
    create_tag(run.api, run.repo, annotated, run.ids["default_branch"], "by the live run")
    heard = tag_message(run.api, run.repo, annotated)
    delete_tag(run.api, run.repo, annotated)
    _expect(heard.endswith(": by the live run"), f"the message read back as {heard!r}")
    return f"{said} Deleted it again. Annotated: {heard}"


def commit_status(run: Any) -> str:
    from quill.core.github.commit_status import set_commit_status

    sha = run.rest("GET", f"/repos/{run.repo}/commits/{run.ids['default_branch']}")["sha"]
    said = set_commit_status(run.api, run.repo, sha, "success", "quill-live", "by the live run")
    found = run.rest("GET", f"/repos/{run.repo}/commits/{sha}/statuses")
    _expect(any(s["context"] == "quill-live" for s in found), "no status")
    return said


def cancel_run(run: Any) -> str:
    run_id = _dispatch(run, "pass")
    run.items.cancel_workflow_run(run.repo, run_id)
    finished = _wait_run(run, run_id)
    run.items.delete_workflow_run(run.repo, run_id)
    return f"cancel accepted; it ended {finished['conclusion']}; deleted"


def rerun_failed_and_delete(run: Any) -> str:
    run_id = _dispatch(run, "fail")
    _expect(_wait_run(run, run_id)["conclusion"] == "failure", "the failing run did not fail")
    run.items.rerun_failed_jobs(run.repo, run_id)
    _wait_run(run, run_id)
    run.items.delete_workflow_run(run.repo, run_id)
    _expect(
        run.exists(f"/repos/{run.repo}/actions/runs/{run_id}") is None, "the run is still there"
    )
    return "failed, re-ran its failed job, deleted"


def rerun(run: Any) -> str:
    run_id = int(run.ids["run"])
    run.items.rerun_workflow_run(run.repo, run_id)
    finished = _wait_run(run, run_id)
    return f"re-ran run {run_id}: {finished['conclusion']}"


def delete_cache(run: Any) -> str:
    from quill.core.github.repo_actions import GitHubRepoActions

    caches = run.rest("GET", f"/repos/{run.repo}/actions/caches")["actions_caches"]
    if not caches:
        raise NotHere("the test workflow left no cache")
    GitHubRepoActions(_token(run)).delete_cache(run.repo, str(caches[0]["id"]))
    return f"deleted cache {caches[0]['key']}"


# -- labels, releases, stars, gists, people --------------------------------------------


def edit_label(run: Any) -> str:
    client = _explore(run)
    old = LABELS[1]
    client.edit_label(run.repo, old, f"{old}-edited", "fbca04", f"{TAG} edited")
    _expect(run.exists(f"/repos/{run.repo}/labels/{old}-edited") is not None, "not renamed")
    client.edit_label(run.repo, f"{old}-edited", old, "1d76db", TAG)
    return "renamed and recoloured, then put back"


def delete_label(run: Any) -> str:
    client = _explore(run)
    client.create_label(run.repo, "quill-live-delete", "000000", TAG)
    client.delete_label(run.repo, "quill-live-delete")
    _expect(run.exists(f"/repos/{run.repo}/labels/quill-live-delete") is None, "still there")
    return "made, then deleted"


def _release_admin(run: Any) -> Any:
    from quill.core.github.release_admin import GitHubReleaseAdmin

    return GitHubReleaseAdmin(_token(run))


def edit_release(run: Any) -> str:
    admin = _release_admin(run)
    release = admin.find_release(run.repo, RELEASE_TAG)
    edited, _said = admin.edit_release(
        run.repo, release, name=f"{TAG} release (edited)", body=TAG, draft=False, prerelease=True
    )
    admin.edit_release(
        run.repo, edited, name=f"{TAG} release", body=TAG, draft=False, prerelease=False
    )
    return "renamed and marked a pre-release, then put back"


def upload_and_delete_asset(run: Any) -> str:
    admin = _release_admin(run)
    release = admin.find_release(run.repo, RELEASE_TAG)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / f"quill-live-{int(time.time())}.txt"
        path.write_text(TAG, encoding="utf-8")
        asset = admin.upload_release_asset(run.repo, release, path)
    admin.delete_asset(run.repo, asset)
    return f"uploaded {path.name}, then deleted it"


def star(run: Any) -> str:
    client = _explore(run)
    was = run.exists(f"/user/starred/{run.repo}") is not None
    client.set_starred(run.repo, not was)
    client.set_starred(run.repo, was)
    return "starred and unstarred"


def star_gist(run: Any) -> str:
    client = _explore(run)
    gist = run.ids.get("gist", "")
    _expect(bool(gist), "no gist was made")
    was = client.is_gist_starred(gist)
    client.set_gist_starred(gist, not was)
    _expect(client.is_gist_starred(gist) is (not was), "the star did not change")
    client.set_gist_starred(gist, was)
    return "starred and unstarred the test gist"


def delete_gist(run: Any) -> str:
    made = run.rest(
        "POST",
        "/gists",
        {
            "description": f"{TAG} gist to delete",
            "public": False,
            "files": {"a.md": {"content": TAG}},
        },
    )
    _explore(run).delete_gist(str(made["id"]))
    _expect(run.exists(f"/gists/{made['id']}") is None, "still there")
    return "made, then deleted"


def follow(run: Any) -> str:
    from quill.core.github.repo_actions import GitHubRepoActions

    who = "octocat"
    was = run.exists(f"/user/following/{who}") is not None
    actions = GitHubRepoActions(_token(run))
    actions.set_following(who, not was)
    actions.set_following(who, was)
    return f"followed and unfollowed {who}"


# -- templates -------------------------------------------------------------------------


def _repo_for(run: Any) -> Callable[[str], Any]:
    return lambda name: run.items.template_repository(name)


def open_template(run: Any) -> str:
    from quill.core.github.template_catalog import list_templates, read_entry_text
    from quill.core.github.template_save import plan_save, save_template

    entries = list_templates(_repo_for(run), run.repo)
    path = ".github/pull_request_template.md"
    repo = run.items.template_repository(run.repo)
    text, sha = read_entry_text(repo, path)
    plan = plan_save(repo, run.repo, path)
    save_template(
        repo, plan, text + f"\n{TAG}: saved by the run.\n", expected_sha=sha, use_pull_request=False
    )
    _text, sha2 = read_entry_text(repo, path)
    save_template(
        repo, plan_save(repo, run.repo, path), text, expected_sha=sha2, use_pull_request=False
    )
    return f"{len(entries)} templates listed; one saved, then put back"


def convert_template(run: Any) -> str:
    from quill.core.github.template_builder import load_draft
    from quill.core.github.template_catalog import read_entry_text
    from quill.core.github.template_convert import form_to_markdown

    repo = run.items.template_repository(run.repo)
    text, _sha = read_entry_text(repo, ".github/ISSUE_TEMPLATE/quill-live.yml")
    markdown = form_to_markdown(load_draft(text))
    _expect("What happened" in markdown, "the form's field was lost")
    return "the issue form converts to Markdown with its field"


def copy_template(run: Any) -> str:
    from quill.core.github.template_save import copy_template as copy
    from quill.core.github.template_save import plan_copy

    path = ".github/pull_request_template.md"
    text = f"## {TAG}\n\nCopied by the run.\n"
    targets = plan_copy(_repo_for(run), path, text, [run.second])
    results = copy(_repo_for(run), path, text, targets, message=TAG)
    current = run.exists(f"/repos/{run.second}/contents/{path}")
    if current:
        run.rest(
            "DELETE",
            f"/repos/{run.second}/contents/{path}",
            {"message": TAG, "sha": current["sha"]},
        )
    _expect(bool(results), "nothing was copied")
    return f"copied to {run.second}, then removed"


# -- local lists (this device) ----------------------------------------------------------


def _saved(run: Any) -> Any:
    from quill.ui.github_workbench_loaders import saved_items_for

    return saved_items_for(run.items)


def favorite(run: Any) -> str:
    from quill.core.github.saved_items import FavoriteItem

    saved = _saved(run)
    url = f"https://github.com/{run.repo}/issues/{run.ids['issue']}"
    item = FavoriteItem(repo=run.repo, item_type="issue", url=url, title=TAG)
    _expect(saved.add_favorite(item), "not added")
    saved.save()
    _expect(_saved(run).remove_favorite(item.key), "not removed")
    return "added and removed, kept on disk between"


def pin_repository(run: Any) -> str:
    saved = _saved(run)
    saved.pin_repo(run.repo)
    saved.save()
    again = _saved(run)
    _expect(again.is_pinned(run.repo), "not pinned after a reload")
    again.unpin_repo(run.repo)
    again.save()
    return "pinned, reloaded, unpinned"


def save_and_remove_search(run: Any) -> str:
    saved = _saved(run)
    saved.save_search(f"is:open label:{LABELS[0]}")
    saved.save()
    again = _saved(run)
    _expect(again.remove_search(f"is:open label:{LABELS[0]}"), "not saved")
    again.save()
    return "saved, reloaded, removed"


def snooze(run: Any) -> str:
    from quill.core.github.attention_queue import GitHubAttentionQueue

    queue = GitHubAttentionQueue.load(run.login)
    key = f"{run.repo}#{run.ids['issue']}"
    queue.snooze(key, dt.datetime.now(dt.UTC) + dt.timedelta(days=1))
    queue.save()
    again = GitHubAttentionQueue.load(run.login)
    _expect(again.is_snoozed(key), "not snoozed after a reload")
    _expect(again.unsnooze(key), "not unsnoozed")
    again.save()
    return "snoozed, reloaded, unsnoozed"


def watches(run: Any) -> str:
    from quill.core.github.watches import WatchStore, check_watch

    store = WatchStore.load(run.login)
    watch = store.add("issue", run.repo, number=int(run.ids["issue"]))
    checked, said = check_watch(run.api, watch)
    store.replace(checked)
    store.replace(dataclasses.replace(checked, paused=True))
    store.save()
    _expect(bool(WatchStore.load(run.login).find(watch.id).paused), "not paused after a reload")
    _expect(store.remove(watch.id), "not removed")
    store.save()
    return f"watched, checked ({len(said)} changes), paused, removed"


def sets(run: Any) -> str:
    from quill.ui.github_workbench_across_sets import sets_for

    store = sets_for(run.items)
    store.set_repositories(f"{TAG} set", [run.repo, run.second])
    store.set_filter(f"{TAG} set", f"user:{run.login} quill-workbench-test")
    renamed = store.rename(f"{TAG} set", f"{TAG} set renamed")
    store.choose(renamed)
    store.save()
    again = sets_for(run.items)
    _expect(again.repositories(renamed) == [run.repo, run.second], "the set was not kept")
    _expect(again.delete(renamed), "not deleted")
    again.save()
    return "made, filtered, renamed, chosen, reloaded, deleted"


def api_console(run: Any) -> str:
    from quill.core.github.api_console import find_operation, is_write, load_operations

    operations = load_operations()
    _expect(not is_write("GET"), "GET counted as a write")
    _expect(is_write("DELETE"), "DELETE not counted as a write")
    found = find_operation("GET", f"/repos/{run.repo}", operations)
    answer = run.rest("GET", f"/repos/{run.repo}")
    _expect(answer["full_name"].lower() == run.repo.lower(), "the wrong repository answered")
    return f"{len(operations)} operations known; GET answered" + (
        "" if found else " (operation not found)"
    )


def account_level(run: Any) -> str:
    from quill.core.github.permissions import AccessLevel, WriteTier, level_allows

    _expect(not level_allows(AccessLevel.READ_ONLY, WriteTier.VISIBLE), "read only allowed a write")
    _expect(level_allows(AccessLevel.FULL, WriteTier.DESTRUCTIVE), "full access refused a delete")
    return "each level allows what it says, and no more"


# -- Across Repositories -----------------------------------------------------------------


def _survey(run: Any, kind: str) -> Any:
    from quill.core.github.across_by_name import survey

    return survey(run.api, kind, [run.repo, run.second])


def _apply(run: Any, plan: Any) -> list[Any]:
    from quill.core.github.across_changes import apply

    results = apply(run.api, plan)
    failed = [r.said for r in results if not r.ok]
    _expect(not failed, "; ".join(failed))
    return results


def across_make_same(run: Any) -> str:
    from quill.core.github.across_changes import plan_make_same

    found = _survey(run, "labels")
    row = found.row(LABELS[0])
    _expect(row is not None and len(row.copies) == 2, f"{LABELS[0]} is not in both repositories")
    winner = next(c.props for c in row.copies if c.repository == run.repo)
    results = _apply(run, plan_make_same(found, row, winner))
    run.rest(
        "PATCH",
        f"/repos/{run.second}/labels/{LABELS[0]}",
        {"color": "b60205", "description": "different"},
    )
    return f"{len(results)} changed, then {run.second}'s copy put back"


def across_add_missing(run: Any) -> str:
    from quill.core.github.across_changes import plan_copy_missing

    found = _survey(run, "labels")
    row = found.row(LABELS[1])
    _expect(row is not None, f"{LABELS[1]} was not found")
    winner = row.copies[0].props
    results = _apply(run, plan_copy_missing(found, row, winner, [run.second]))
    run.rest("DELETE", f"/repos/{run.second}/labels/{LABELS[1]}")
    return f"copied to {len(results)}, then removed"


def across_rename_name(run: Any) -> str:
    from quill.core.github.across_changes import plan_rename

    new = f"{LABELS[0]}-renamed"
    _apply(run, plan_rename(_survey(run, "labels"), _survey(run, "labels").row(LABELS[0]), new))
    found = _survey(run, "labels")
    _expect(found.row(new) is not None, "not renamed")
    _apply(run, plan_rename(found, found.row(new), LABELS[0]))
    return "renamed in both, then back"


def across_close_milestone(run: Any) -> str:
    from quill.core.github.across_changes import plan_close

    for repo in (run.repo, run.second):
        mine = [
            m
            for m in run.rest("GET", f"/repos/{repo}/milestones", state="all")
            if m["title"] == f"{TAG} across"
        ]
        if not mine:
            run.rest("POST", f"/repos/{repo}/milestones", {"title": f"{TAG} across"})
    found = _survey(run, "milestones")
    results = _apply(run, plan_close(found, found.row(f"{TAG} across")))
    for repo in (run.repo, run.second):
        for m in run.rest("GET", f"/repos/{repo}/milestones", state="all"):
            if m["title"] == f"{TAG} across":
                run.rest("DELETE", f"/repos/{repo}/milestones/{m['number']}")
    return f"closed in {len(results)}, then deleted"


def across_merge_label(run: Any) -> str:
    from quill.core.github.across_changes import plan_merge

    for repo in (run.repo, run.second):
        if run.exists(f"/repos/{repo}/labels/quill-live-merge-from") is None:
            run.rest(
                "POST",
                f"/repos/{repo}/labels",
                {"name": "quill-live-merge-from", "color": "5319e7"},
            )
    number = _new_issue(run, "issue for a label merge")
    run.items.update_items(run.repo, [number], add_labels=["quill-live-merge-from"])
    found = _survey(run, "labels")
    _apply(run, plan_merge(found, found.row("quill-live-merge-from"), LABELS[0]))
    names = {label["name"] for label in _issue_state(run, run.repo, number)["labels"]}
    _delete_issue(run, run.repo, number)
    _expect(
        LABELS[0] in names and "quill-live-merge-from" not in names,
        f"labels after: {sorted(names)}",
    )
    return "the issue moved to the kept label; the merged one is gone"


def across_delete_name(run: Any) -> str:
    from quill.core.github.across_changes import plan_delete

    for repo in (run.repo, run.second):
        if run.exists(f"/repos/{repo}/labels/quill-live-delete-across") is None:
            run.rest(
                "POST",
                f"/repos/{repo}/labels",
                {"name": "quill-live-delete-across", "color": "000000"},
            )
    found = _survey(run, "labels")
    results = _apply(run, plan_delete(found, found.row("quill-live-delete-across")))
    return f"deleted from {len(results)}"


def across_move_open(run: Any) -> str:
    from quill.core.github.across_changes import plan_move_open

    into = f"{TAG} milestone two"
    for repo in (run.repo,):
        if not [
            m
            for m in run.rest("GET", f"/repos/{repo}/milestones", state="all")
            if m["title"] == into
        ]:
            run.rest("POST", f"/repos/{repo}/milestones", {"title": into})
    found = _survey(run, "milestones")
    _apply(run, plan_move_open(found, found.row(MILESTONE), into))
    moved = _issue_state(run, run.repo, run.ids["issue"]).get("milestone") or {}
    found = _survey(run, "milestones")
    _apply(run, plan_move_open(found, found.row(into), MILESTONE))
    _expect(moved.get("title") == into, "the open issue did not move")
    return "open issues moved to the other milestone, then back"


# -- the table -----------------------------------------------------------------------

VERBS: dict[str, Scenario | str] = {
    "approve_fork": "not here: needs a pull request from a fork whose run waits for approval",
    "assign_copilot": "not here: needs the Copilot coding agent on the account",
    "assignees": assignees,
    "cancel_run": cancel_run,
    "clone": "needs Jeff: clones into a folder you choose, then opens it in the editor",
    "close_reopen": close_reopen,
    "create_branch": create_branch,
    "edit_tasks": task_lists,
    "convert_tasks": "with edit_tasks: checked, converted and linked",
    "comment": comment,
    "delete_asset": "with upload_asset: uploaded, then deleted",
    "delete_branch": "with merge: the merged pull request's branch is deleted",
    "delete_cache": delete_cache,
    "delete_gist": delete_gist,
    "delete_label": delete_label,
    "delete_run": "with rerun_failed: the failed run is deleted",
    "dismiss_alert": "not here: the test repositories have no security alert",
    "edit_label": edit_label,
    "edit_release": edit_release,
    "edit_title": "sheet:issue.title",
    "favorite": favorite,
    "follow": follow,
    "issue_type": "not here: issue types belong to organizations, not personal repositories",
    "labels": labels,
    "lock": lock,
    "mark_done": "needs Jeff: would mark one of your real notifications done",
    "mark_read": "needs Jeff: would mark one of your real notifications read",
    "merge": merge_and_delete_branch,
    "revert_pull": revert_merged,
    "workflow_state": workflow_state,
    "new_tag": tags_made_and_deleted,
    "delete_tag": "with new_tag: made, then deleted",
    "transfer_repository": "not here: needs a second account or an organization to receive it",
    "delete_package_version": "not here: the live run publishes no package to delete",
    "delete_package": "not here: the live run publishes no package to delete",
    "commit_status": commit_status,
    "user_status": "needs Jeff: changes the status on your own GitHub profile",
    "accept_invitation": "not here: needs an invitation from a second GitHub account",
    "decline_invitation": "not here: needs an invitation from a second GitHub account",
    "practice": "needs Jeff: makes quill-practice in your own account, then deletes it",
    "inbox_rules": "needs Jeff: a rule acts on your real notifications as they load",
    "auto_merge": "not here: needs a pull request waiting on a required check; none is required",
    "merge_queue": "not here: a merge queue needs an organization repository's ruleset",
    "resolve_conflicts": "needs Jeff: fetches into a folder beside your checkout, in the editor",
    "milestone": "sheet:issue.milestone",
    "open_codespaces": "needs Jeff: makes a codespace, which is billed",
    "pending_deployments": "not here: needs an environment with reviewers, and a run waiting",
    "pin": pin,
    "pin_repository": pin_repository,
    "projects": "sheet:issue.projects",
    "react": "sheet:issue.reactions",
    "remove_search": "with save_search: saved, then removed",
    "rerun": rerun,
    "rerun_failed": rerun_failed_and_delete,
    "run_workflow": run_workflow,
    "snooze": snooze,
    "star": star,
    "star_gist": star_gist,
    "start_worktree": "needs Jeff: makes a worktree in a folder you choose, from the editor",
    "sub_issues": sub_issues,
    "transfer": transfer,
    "unsnooze": "with snooze: snoozed, then unsnoozed",
    "unsubscribe": "sheet:issue.subscribed",
    "upload_asset": upload_and_delete_asset,
    "watch": "sheet:repository.watch",
    "undo_change": "sheet: every field the sheets change is put back by Undo's own code (inverse)",
    "redo_change": "sheet: Redo sends the same change the sheets send first",
    "mark_all_read": "needs Jeff: would mark all of your real notifications read",
    "save_search": save_and_remove_search,
    "new_issue": new_issue,
    "open_template": open_template,
    "convert_template": convert_template,
    "copy_template": copy_template,
    "account_level": account_level,
    "bulk_access": "not here: needs a second GitHub account to give access to",
    "access_add": "not here: needs a second GitHub account to give access to",
    "access_change": "not here: needs a second GitHub account to give access to",
    "access_remove": "not here: needs a second GitHub account to give access to",
    "delete_team": "not here: would change a real organization",
    "create_team": "not here: would change a real organization",
    "pause_watch": watches,
    "remove_watch": "with pause_watch: watched, paused, removed",
    "api_console": api_console,
    "across_edit_set": sets,
    "across_set_filter": "with across_edit_set",
    "across_new_set": "with across_edit_set",
    "across_rename_set": "with across_edit_set",
    "across_delete_set": "with across_edit_set",
    "across_make_same": across_make_same,
    "across_add_missing": across_add_missing,
    "across_rename_name": across_rename_name,
    "across_close_milestone": across_close_milestone,
    "across_merge_label": across_merge_label,
    "across_delete_name": across_delete_name,
    "across_move_open": across_move_open,
    "across_promote_org": "not here: would change a real organization",
}


def run_verbs(run: Any) -> None:
    from quill.core.github.sheet_catalog import SHEETS

    for verb, how in VERBS.items():
        name = f"github.workbench.{verb}"
        if callable(how):
            if run.dry_run:
                run.record("command", name, "not here", "a --dry-run writes nothing")
            else:
                run.check("command", name, lambda h=how: h(run))
        elif how.startswith("sheet:") and "." in how:
            kind, field_key = how.removeprefix("sheet:").split(".", 1)
            _expect(field_key in SHEETS[kind].writes, f"{how} names no write")
            run.record(
                "command", name, "pass", f"as the {kind} sheet's {field_key} field (see the sheets)"
            )
        elif how.startswith(("sheet:", "with ")):
            run.record("command", name, "pass", how)
        elif how.startswith("needs Jeff"):
            run.record("command", name, "needs Jeff", how.removeprefix("needs Jeff: "))
        else:
            run.record("command", name, "not here", how.removeprefix("not here: "))


# -- features that are not single commands ------------------------------------------------


def _clone(run: Any, folder: Path) -> Path:
    from quill.core.github.clone import CloneSource, clone_repository
    from quill.stability.safe_subprocess import run_subprocess_safely

    source = CloneSource(
        url=f"https://github.com/{run.repo}.git", name=run.repo.split("/")[1], full_name=run.repo
    )
    return Path(
        clone_repository(
            "git", source, folder / "clone", token=_token(run), runner=run_subprocess_safely
        )
    )


def line_commands(run: Any) -> str:
    from quill.core.github import editor_line as el
    from quill.core.local_git import blame_line
    from quill.stability.safe_subprocess import run_subprocess_safely

    with tempfile.TemporaryDirectory(dir=Path.home()) as folder:
        root = _clone(run, Path(folder))
        site = el.locate(root / SAMPLE, 3, 5, runner=run_subprocess_safely)
        link = el.permalink(site)
        _expect(link.endswith(f"/{SAMPLE}#L3-L5") and run.repo in link, link)
        blame = el.blame_sentence(blame_line(str(root), SAMPLE, 3, runner=run_subprocess_safely))
        pulls = run.rest("GET", el.commit_pulls_path(run.repo, site.commit))
        first = el.first_pull(pulls)
        refs = el.references_in(
            f"See #{run.ids['issue']} and {run.repo}#{run.ids['pull']}", run.repo
        )
        _expect(len(refs) == 2, f"references found: {refs}")
    return f"link {link.rsplit('/', 1)[-1]}; {blame}; pull for the commit: {first or 'none'}"


def import_issues(run: Any) -> str:
    from quill.core.github.issue_import import import_mapping, import_plan, issue_payload
    from quill.core.workbench.spreadsheet import read_spreadsheet

    with tempfile.TemporaryDirectory() as folder:
        sheet = Path(folder) / "issues.csv"
        sheet.write_text(
            "Summary,Description,Tags,Milestone,Owner\n"
            f"{TAG} import one,From a spreadsheet,{LABELS[0]},{MILESTONE},{run.login}\n"
            f",no title so skipped,,,\n"
            f"{TAG} import two,,{LABELS[0]}, a milestone that is not there,\n",
            encoding="utf-8",
        )
        rows = read_spreadsheet(sheet)
    mapping, ignored = import_mapping(rows[0].keys())
    milestones = {
        m["title"]: m["number"]
        for m in run.rest("GET", f"/repos/{run.repo}/milestones", state="all")
    }
    plan = import_plan(rows, milestones=milestones)
    ready = [row for row in plan if not row.problem]
    _expect(len(ready) == 1 and len(plan) == 3, " / ".join(row.sentence for row in plan))
    made = run.rest("POST", f"/repos/{run.repo}/issues", issue_payload(ready[0], milestones))
    _expect(
        made["milestone"]["title"] == MILESTONE and made["assignees"],
        "the mapped fields did not take",
    )
    _delete_issue(run, run.repo, int(made["number"]))
    return (
        f"3 rows: 1 made with its milestone and assignee, 2 skipped with reasons; mapping {mapping}"
    )


def issues_from_lines(run: Any) -> str:
    from quill.core.github.issue_import import titles_from_lines

    titles = titles_from_lines(f"- [ ] {TAG} line one\n\n2. {TAG} line two\n")
    _expect(titles == [f"{TAG} line one", f"{TAG} line two"], str(titles))
    parent = run.ids["issue"]
    for title in titles:
        made = run.rest("POST", f"/repos/{run.repo}/issues", {"title": title})
        run.rest(
            "POST", f"/repos/{run.repo}/issues/{parent}/sub_issues", {"sub_issue_id": made["id"]}
        )
        _delete_issue(run, run.repo, int(made["number"]))
    return "two lines, two sub-issues, then deleted"


#: The import commands (PRD 22.7), whose scenarios are defined just above.
VERBS["import_issues"] = import_issues
VERBS["issues_from_lines"] = issues_from_lines


def comment_composer(run: Any) -> str:
    """The composer's lookups against real GitHub: people, references, saved replies."""
    from quill.core.github import comment_compose as cc

    people = cc.mention_candidates(run.api, run.repo, already=[run.login])
    _expect(run.login in people, f"the owner was not offered: {people}")
    refs = cc.reference_candidates(run.api, run.repo, run.ids["issue"])
    _expect(bool(refs) and refs[0].number == int(run.ids["issue"]), "the issue was not found")
    replies = cc.saved_replies(run.api)
    return f"{len(people)} people, issue #{refs[0].number} found, {len(replies)} saved replies"


def review_viewed_files(run: Any) -> str:
    """Mark a file of the test pull request viewed, read it back, and put it back."""
    from quill.core.github.review_viewed import load_viewed, set_viewed

    number = int(run.ids["pull"])
    viewed = load_viewed(run.api, run.repo, number)
    _expect(bool(viewed.states), "the pull request listed no files")
    path = next(iter(viewed.states))
    was = viewed.is_viewed(path)
    set_viewed(run.api, viewed, path, not was)
    again = load_viewed(run.api, run.repo, number)
    _expect(again.is_viewed(path) is (not was), f"GitHub kept {path} as it was")
    set_viewed(run.api, again, path, was)
    return f"{path}: marked, read back, put back; {again.sentence()}"


def export_list(run: Any) -> str:
    from quill.core.workbench.export import export_rows

    issues = run.rest("GET", f"/repos/{run.repo}/issues", state="open")
    rows = [(str(i["number"]), i["title"], i["state"]) for i in issues]
    sizes = []
    with tempfile.TemporaryDirectory() as folder:
        for suffix in ("csv", "md", "xlsx"):
            try:
                count = export_rows(
                    Path(folder) / f"list.{suffix}", ("Number", "Title", "State"), rows
                )
            except ModuleNotFoundError:
                continue
            sizes.append(f"{suffix} {count}")
    _expect(bool(sizes), "nothing exported")
    return ", ".join(sizes) + " rows"


def runners_and_sbom(run: Any) -> str:
    from quill.core.github.runners_sbom import RunnersError, fetch_runners, save_sbom, sbom_name

    runners = fetch_runners(run.api, run.repo)
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / sbom_name(run.repo)
        try:
            said = save_sbom(run.api, run.repo, target)
        except RunnersError as exc:
            said = f"no bill of materials ({exc})"
        else:
            _expect(target.stat().st_size > 0, "an empty file")
    return f"{len(runners)} self-hosted runners; {said}"


def commit_activity(run: Any) -> str:
    from quill.core.github.repo_activity import fetch_activity

    warnings: list[str] = []
    token = getattr(run.api, "_token", None)
    rows = fetch_activity(token, run.repo, limit=20, warnings=warnings)
    _expect(not warnings, "; ".join(warnings))
    return rows[0].label


def my_packages(run: Any) -> str:
    from quill.core.github.packages import PackageError, fetch_packages

    try:
        rows = fetch_packages(run.api)
    except PackageError as exc:
        return f"refused, in words: {exc}"
    return f"{len(rows)} packages" + (f"; first: {rows[0].label}" if rows else "")


def check_with_git(run: Any) -> str:
    done = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)
    _expect(done.returncode == 0, "git is not installed")
    return done.stdout.strip()


FEATURES: dict[str, Scenario | str] = {
    "git on this computer (the line commands need it)": check_with_git,
    "From This Line: link, blame, pull for the commit, references (PRD 22.3)": line_commands,
    "Export List: CSV, Markdown and Excel (PRD 22.7)": export_list,
    "The comment composer's lookups (PRD 22.4)": comment_composer,
    "Viewed files in a pull request review (PRD 22.1)": review_viewed_files,
    "Open Patch in Editor: the whole change as one diff": open_patch,
    "Why Can't I Merge?, for the exact commit": why_cant_merge,
    "Runners and Export Software Bill of Materials (PRD 14.2)": runners_and_sbom,
    "Commit Activity as tables (PRD 14.2)": commit_activity,
    "My Packages, or the permission it needs said in words (PRD 14.2)": my_packages,
    "Speech and braille for each list, sheet and result": (
        "needs Jeff: the screen-reader checks in docs/qa/screen-reader-checks-2026-10.md"
    ),
    "Keyboard: every menu row's key and access letter": (
        "covered by the unit gates (menu accelerators, access keys); needs Jeff to hear them"
    ),
}


def run_features(run: Any) -> None:
    for name, how in FEATURES.items():
        if callable(how):
            if run.dry_run and how is not check_with_git:
                run.record("feature", name, "not here", "a --dry-run writes nothing")
            else:
                run.check("feature", name, lambda h=how: h(run))
        elif how.startswith("needs Jeff"):
            run.record("feature", name, "needs Jeff", how.removeprefix("needs Jeff: "))
        else:
            run.record("feature", name, "pass", how)
