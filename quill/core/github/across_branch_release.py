"""Delete Where Merged and Draft Releases Together, across repositories (PRD 22.11; GH-R-151).

Two by-name writes whose preview needs GitHub's answers, so each plan is made
off the UI thread and is still the same
:class:`~quill.core.github.across_changes.Plan`: a step per repository, with
what will change or why it will not, run by
:func:`~quill.core.github.across_changes.apply`, which checks each target again
just before writing it.

- **Delete Where Merged** (a Branches by Name row): the branch is deleted in
  each repository where everything on it is already in the default branch, or
  a merged pull request took exactly its last commit (a squash merge). A copy
  that is the default branch, protected, has open pull requests based on it or
  from it, or has commits nowhere else is kept, with the reason. One that gains
  a commit after the preview is kept too. The result names the last commit, so
  the branch can be made again by hand; GitHub has no undo for a deleted
  branch, and neither does Delete Branch in one repository.
- **Draft Releases Together** (a Tags by Name row): one draft release of the tag
  in each repository you choose, from notes written once, in which
  ``{repository}`` and ``{tag}`` become each repository's own; GitHub's
  generated notes can follow them. A draft is seen only by people who may push,
  until somebody publishes it. A repository that already has a release or a
  draft for the tag is left alone.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from quill.core.github.across import why_failed
from quill.core.github.across_by_name import ByNameRow, Copy, Survey, seg
from quill.core.github.across_changes import (
    LogEntry,
    Outcome,
    Plan,
    Result,
    Step,
    apply,
    blocked_for,
)
from quill.core.github.across_more_changes import exists

__all__ = [
    "TEMPLATE_HELP",
    "apply_draft_releases",
    "apply_merged_delete",
    "fill_template",
    "plan_draft_releases",
    "plan_merged_delete",
]

TEMPLATE_HELP = "{repository} becomes each repository's name, and {tag} the tag."


def _get(api: Any, path: str, query: Mapping[str, str] | None = None) -> Any:
    return api.rest("GET", path, query=dict(query or {})).data


def _entries(data: Any) -> list[Mapping[str, Any]]:
    return [e for e in data if isinstance(e, Mapping)] if isinstance(data, list) else []


# -- Delete Where Merged ----------------------------------------------------------------


def _pulls(api: Any, repo: str, branch: str, state: str) -> list[Mapping[str, Any]]:
    head = f"{repo.split('/')[0]}:{branch}"
    query = {"state": state, "head": head, "per_page": "100"}
    return _entries(_get(api, f"/repos/{repo}/pulls", query))


def _tip(api: Any, repo: str, branch: str) -> str:
    data = exists(api, f"/repos/{repo}/branches/{seg(branch)}")
    commit = data.get("commit") if isinstance(data, Mapping) else None
    return str(commit.get("sha") or "") if isinstance(commit, Mapping) else ""


def _merged(api: Any, repo: str, branch: str) -> tuple[str, str, str]:
    """(why it is merged, or "", why it is kept, or "", its last commit)."""
    data = _get(api, f"/repos/{repo}")
    default = str(data.get("default_branch") or "") if isinstance(data, Mapping) else ""
    sha = _tip(api, repo, branch)
    if not default or not sha:
        return "", "GitHub did not say its default branch or the branch's last commit", sha
    opened = _pulls(api, repo, branch, "open")
    if opened:
        return "", f"pull request #{opened[0].get('number')} is open from it", sha
    compared = _get(api, f"/repos/{repo}/compare/{seg(default)}...{seg(branch)}")
    if not isinstance(compared, Mapping) or not isinstance(compared.get("ahead_by"), int):
        return "", f"GitHub did not say how it compares with {default}", sha
    ahead = int(compared["ahead_by"])
    if ahead == 0:
        return f"everything on it is in {default}", "", sha
    for pull in _pulls(api, repo, branch, "closed"):
        head = pull.get("head")
        took = isinstance(head, Mapping) and head.get("sha") == sha
        if pull.get("merged_at") and took:
            return f"pull request #{pull.get('number')} merged its last commit", "", sha
    words = f"{ahead} commits on it are" if ahead != 1 else "1 commit on it is"
    return "", f"{words} not in {default} and no merged pull request took them", sha


def _kept(survey: Survey, copy: Copy) -> str:
    """Why *copy* is kept whatever GitHub says about merging ("" when it may go)."""
    blocked = blocked_for(survey, copy.repository)
    if blocked:
        return blocked
    if copy.prop("default") == "yes":
        return "it is the default branch"
    if copy.prop("protected") == "yes":
        return "it is protected (its branch sheet removes the protection first)"
    based = dict(copy.extra).get("open_prs", "0")
    if based != "0":
        return f"{based} open pull request{'' if based == '1' else 's'} based on it"
    return ""


def plan_merged_delete(api: Any, survey: Survey, row: ByNameRow) -> Plan:
    """The branch deleted where it is merged; reads each repository. Off the UI thread."""
    if survey.kind != "branches":
        raise ValueError("Only branches are deleted where merged.")
    steps = []
    for copy in row.copies:
        repo = copy.repository
        blocked, after, sha = _kept(survey, copy), "", ""
        if not blocked:
            try:
                reason, blocked, sha = _merged(api, repo, copy.name)
            except Exception as exc:  # noqa: BLE001 - one repository never sinks the rest
                reason, blocked = "", f"it could not be checked ({why_failed(exc)})"
            after = f"{copy.name}, because {reason}" if reason else copy.name
        body = (("sha", sha),)
        steps.append(Step(repo, "delete", "", after or copy.name, blocked, copy, body))
    return Plan("branches", row.name, "Delete the merged copies of", tuple(steps))


def _check_merged(api: Any, _plan: Plan, step: Step) -> str:
    copy = step.copy
    if copy is None:
        return ""
    sha = _tip(api, step.repository, copy.name)
    if not sha:
        return "it was deleted on GitHub since you looked"
    if sha != dict(step.body).get("sha"):
        return "it gained commits since you looked, so it is kept"
    return ""


def _run_merged(api: Any, plan: Plan, step: Step) -> Outcome:
    repo, copy = step.repository, step.copy
    if copy is None:
        raise ValueError("A merged branch needs its copy.")
    api.rest("DELETE", f"/repos/{repo}/git/refs/heads/{seg(copy.name)}")
    sha = dict(step.body).get("sha", "")
    said = f"deleted; its last commit was {sha[:7]}, if it is ever wanted back"
    ident = (("repo", repo), ("name", copy.name))
    return said, LogEntry("branch", ident, f"{repo} branch {plan.name}", said)


def apply_merged_delete(
    api: Any, plan: Plan, *, on_step: Callable[[Result], None] | None = None
) -> list[Result]:
    return apply(api, plan, on_step=on_step, runner=_run_merged, check=_check_merged)


# -- Draft Releases Together ------------------------------------------------------------


def fill_template(template: str, repo: str, tag: str) -> str:
    """The shared notes for one repository: ``{repository}`` and ``{tag}`` filled in."""
    return template.replace("{repository}", repo).replace("{tag}", tag)


def _release_for(api: Any, repo: str, tag: str) -> str:
    """The release or draft that has *tag* in *repo*, in words ("" when there is none)."""
    for entry in _entries(_get(api, f"/repos/{repo}/releases", {"per_page": "100"})):
        if entry.get("tag_name") == tag:
            name = str(entry.get("name") or tag)
            return f"draft release {name}" if entry.get("draft") else f"release {name}"
    return ""


def plan_draft_releases(
    api: Any,
    survey: Survey,
    tag: str,
    targets: Sequence[str],
    template: str,
    *,
    generated: bool = False,
) -> Plan:
    """One draft release of *tag* per target, from *template*. Off the UI thread."""
    if survey.kind != "tags":
        raise ValueError("Draft releases are made from a tag's row.")
    steps = []
    for repo in targets:
        blocked = blocked_for(survey, repo)
        if not blocked:
            try:
                had = _release_for(api, repo, tag)
            except Exception as exc:  # noqa: BLE001 - one repository never sinks the rest
                had, blocked = "", f"its releases could not be read ({why_failed(exc)})"
            if had:
                blocked = f"it already has the {had} (its own sheet changes the notes)"
        has_tag = survey.has(repo, tag) is not None
        after = f"a draft release {tag} with the shared notes"
        if generated:
            after += ", then GitHub's generated notes"
        if not has_tag:
            after += "; the tag is made on its default branch when it is published"
        body = (
            ("notes", fill_template(template, repo, tag)),
            ("generated", "yes" if generated else "no"),
            ("has_tag", "yes" if has_tag else "no"),
        )
        steps.append(Step(repo, "draft", "", after, blocked, None, body))
    return Plan("tags", tag, "Draft a release for", tuple(steps))


def _check_draft(api: Any, plan: Plan, step: Step) -> str:
    had = _release_for(api, step.repository, plan.name)
    return f"the {had} was made there since you looked" if had else ""


def _run_draft(api: Any, plan: Plan, step: Step) -> Outcome:
    repo, body = step.repository, dict(step.body)
    release: dict[str, object] = {
        "tag_name": plan.name,
        "name": plan.name,
        "body": body.get("notes", ""),
        "draft": True,
        "generate_release_notes": body.get("generated") == "yes",
    }
    if body.get("has_tag") != "yes":
        data = _get(api, f"/repos/{repo}")
        branch = str(data.get("default_branch") or "") if isinstance(data, Mapping) else ""
        if not branch:
            raise RuntimeError("GitHub did not say its default branch")
        release["target_commitish"] = branch
    made = api.rest("POST", f"/repos/{repo}/releases", body=release).data
    if isinstance(made, Mapping) and made.get("draft") is False:
        said = f"published {plan.name}, not drafted: GitHub published it, so check it now"
    else:
        said = f"drafted {plan.name}; only people who may push see it until it is published"
    ident = (("repo", repo), ("tag", plan.name))
    return said, LogEntry("release", ident, f"{repo} release {plan.name}", said)


def apply_draft_releases(
    api: Any, plan: Plan, *, on_step: Callable[[Result], None] | None = None
) -> list[Result]:
    return apply(api, plan, on_step=on_step, runner=_run_draft, check=_check_draft)
