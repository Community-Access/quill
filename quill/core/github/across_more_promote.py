"""Promote secrets, variables and webhooks to the organization, and the release train.

**Promote to Organization** (PRD 22.11, "prefer what GitHub already shares"):

- a **secret** becomes one organization secret with the set's repositories
  in that organization selected. Its value cannot be read from any copy, so it
  is typed once and sealed with the organization's public key;
- a **variable** becomes one organization variable with the winner's value,
  for the same selected repositories;
- a **webhook** becomes one organization webhook with the winner's address,
  events and content type. GitHub sends an organization webhook for *every*
  repository in the organization, not only the set's, and the preview says so.

The organization's one is made first; each repository's own copy is deleted
only after that worked, because a repository's own secret or variable wins
over the organization's of the same name, and two webhooks would deliver
twice. Environments, deploy keys and autolinks have no organization form in
GitHub, so they are not promoted (the scope matrix says so).

**Release train** (PRD 22.11, Tags): the same tag -- or the tag and a draft or
published release -- made in every repository you choose, on its default
branch, previewed repository by repository. A repository that already has the
tag is skipped and its tag is never moved; one where the tag appeared since
the survey is skipped at the moment of writing. A draft release has no tag
until it is published, and the preview says that too.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.github.across_by_name import ByNameRow, Survey, seg
from quill.core.github.across_changes import (
    LogEntry,
    Outcome,
    Plan,
    Result,
    Step,
    apply,
    blocked_for,
)
from quill.core.github.across_more_changes import (
    ADMIN_KINDS,
    check_more,
    exists,
    hook_create,
    run_more,
    seal_for,
)

__all__ = [
    "PROMOTABLE",
    "TRAIN_CHOICES",
    "apply_more_promote",
    "plan_more_promote",
    "plan_release_train",
    "run_train",
]

PROMOTABLE = frozenset({"secrets", "variables", "webhooks"})

#: What a release train makes, in the words the chooser shows.
TRAIN_CHOICES: tuple[tuple[str, str], ...] = (
    ("tag", "The tag only"),
    ("draft", "The tag's draft release (GitHub makes the tag when it is published)"),
    ("published", "The tag and a published release"),
)


def plan_more_promote(
    survey: Survey, row: ByNameRow, winner: Sequence[tuple[str, str]], organization: str
) -> Plan:
    """One organization secret, variable or webhook, then each in-organization copy deleted."""
    kind = survey.kind
    if kind not in PROMOTABLE:
        raise ValueError(f"{kind} have no organization form.")
    inside = [c for c in row.copies if c.repository.split("/")[0].lower() == organization.lower()]
    names = ",".join(c.repository for c in inside)
    source = next((c for c in row.copies if c.props == tuple(winner)), None)
    props = source.props if source is not None else ()
    noun = {"secrets": "secret", "variables": "variable", "webhooks": "webhook"}[kind]
    after = f"an organization {noun} {row.name} for {len(inside)} repositories"
    if kind == "webhooks":
        after = (
            f"an organization webhook to {row.name}; GitHub sends it for every repository in "
            f"{organization}, not only the set's"
        )
    first = Step(
        f"organization {organization}",
        f"create_org_{noun}",
        "",
        after,
        "" if inside else f"no repository in the set belongs to {organization}",
        None,
        (*props, ("organization", organization), ("names", names)),
    )
    steps = [first]
    for copy in row.copies:
        if copy not in inside:
            steps.append(
                Step(copy.repository, "skip", after=f"not in {organization}, keeps its own")
            )
            continue
        blocked = blocked_for(survey, copy.repository, admin=kind in ADMIN_KINDS)
        steps.append(
            Step(
                copy.repository, "delete", row.name, "replaced by the organization's", blocked, copy
            )
        )
    return Plan(kind, row.name, "Promote to Organization", tuple(steps))


def _repository_ids(api: Any, names: str) -> list[int]:
    ids = []
    for repo in filter(None, names.split(",")):
        data = api.rest("GET", f"/repos/{repo}").data
        if isinstance(data, Mapping) and isinstance(data.get("id"), int):
            ids.append(int(data["id"]))
    return ids


def _org_path(plan: Plan, organization: str) -> str:
    where = {"secrets": "actions/secrets", "variables": "actions/variables", "webhooks": "hooks"}
    return f"/orgs/{organization}/{where[plan.kind]}"


def _org_conflict(api: Any, plan: Plan, step: Step) -> str:
    organization = dict(step.body)["organization"]
    base = _org_path(plan, organization)
    if plan.kind == "webhooks":
        hooks = api.rest("GET", base).data or []
        urls = {
            str(h.get("config", {}).get("url") or "")
            for h in hooks
            if isinstance(h, Mapping) and isinstance(h.get("config"), Mapping)
        }
        taken = plan.name in urls
    else:
        taken = exists(api, f"{base}/{seg(plan.name)}") is not None
    if taken:
        return f"{organization} already has one; promoting would replace it, so nothing is changed"
    return ""


def _run_org(api: Any, plan: Plan, step: Step, secret: str) -> Outcome:
    body = dict(step.body)
    organization = body["organization"]
    base = _org_path(plan, organization)
    if plan.kind == "webhooks":
        api.rest("POST", base, body=hook_create({**body, "url": plan.name}, secret))
    else:
        chosen = {
            "visibility": "selected",
            "selected_repository_ids": _repository_ids(api, body["names"]),
        }
        if plan.kind == "secrets":
            api.rest(
                "PUT", f"{base}/{seg(plan.name)}", body={**seal_for(api, base, secret), **chosen}
            )
        else:
            api.rest("POST", base, body={"name": plan.name, "value": body["value"], **chosen})
    said = f"created the organization's {plan.name}"
    return said, LogEntry(plan.kind, (("org", organization),), f"{organization} {plan.name}", said)


def apply_more_promote(api: Any, plan: Plan, *, secret: str = "") -> list[Result]:
    """Make the organization's one first; delete copies only if that worked."""
    first, rest = plan.steps[0], plan.steps[1:]
    head = apply(
        api,
        Plan(plan.kind, plan.name, plan.operation, (first,)),
        runner=lambda a, p, s: _run_org(a, p, s, secret),
        check=_org_conflict,
    )
    if not head[0].ok:
        kept = [
            Result(
                s.repository,
                s.action == "skip",
                "no change, " + (s.after or "kept")
                if s.action == "skip"
                else "kept: the organization's was not created",
            )
            for s in rest
        ]
        return head + kept
    tail = Plan(plan.kind, plan.name, plan.operation, rest)
    return head + apply(api, tail, runner=run_more, check=check_more)


# -- the release train -------------------------------------------------------------------


def plan_release_train(
    survey: Survey, name: str, targets: Sequence[str], make: str, notes: str = ""
) -> Plan:
    """The tag *name* (and a release, by *make*) in each target that lacks it."""
    words = dict(TRAIN_CHOICES)
    if make not in words:
        raise ValueError(f"Unknown release train {make!r}.")
    steps = []
    for repo in targets:
        copy = survey.has(repo, name)
        if copy is not None:
            at = copy.prop("commit")
            steps.append(
                Step(repo, "skip", after=f"it has {name} at {at}; an existing tag is never moved")
            )
            continue
        action = "create_tag" if make == "tag" else "create_release"
        after = {
            "tag": f"gains the tag {name} on its default branch",
            "draft": f"a draft release {name}; the tag is made when it is published",
            "published": f"gains the tag {name} and a published release on its default branch",
        }[make]
        body = (("make", make), ("notes", notes))
        steps.append(Step(repo, action, "", after, blocked_for(survey, repo), None, body))
    return Plan("tags", name, "Release train", tuple(steps))


def run_train(api: Any, plan: Plan, step: Step) -> Outcome:
    from quill.core.github.tags import create_tag

    repo, body = step.repository, dict(step.body)
    data = api.rest("GET", f"/repos/{repo}").data
    branch = str(data.get("default_branch") or "") if isinstance(data, Mapping) else ""
    if not branch:
        raise RuntimeError("GitHub did not say its default branch")
    if step.action == "create_tag":
        said = create_tag(api, repo, plan.name, branch).rstrip(".")
    else:
        draft = body.get("make") == "draft"
        release = {
            "tag_name": plan.name,
            "name": plan.name,
            "body": body.get("notes", ""),
            "draft": draft,
            "target_commitish": branch,
        }
        api.rest("POST", f"/repos/{repo}/releases", body=release)
        said = f"{'drafted' if draft else 'published'} {plan.name} on {branch}"
    return said, LogEntry("tag", (("repo", repo),), f"{repo} {plan.name}", said)
