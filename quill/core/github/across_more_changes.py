"""Changing tags, branches, environments, secrets, variables, webhooks, keys and autolinks.

The writes of PRD 22.11 for the kinds :mod:`quill.core.github.across_more_kinds`
reads. Every plan is the same :class:`~quill.core.github.across_changes.Plan`
as for labels, a step per repository, blocked where the account does not
administer it (or, for tags and branches, may not write to it), and run by
:func:`quill.core.github.across_changes.apply` with this module's runner and
conflict check: each target is read again just before the write, and one
somebody changed on GitHub since the survey is skipped with a sentence.

- **Make Them the Same:** environments (wait timer, reviewers, self-review and
  which branches may deploy), variables (the value), webhooks (events, on or
  off, content type; the secret is left as it is, because nobody can read it).
  An environment whose branches are a custom list is not copied: the patterns
  belong to each repository. A team reviewer is not carried into another
  organization, where the team does not exist.
- **Add to Missing:** environments, variables, webhooks and autolinks. A
  deploy key cannot be: GitHub accepts one key in one repository only.
- **Set Secret Everywhere:** one new value, typed once, sealed with each
  repository's own public key. A secret's old value is never read, because
  GitHub never gives it back.
- **Delete Everywhere:** every kind but branches. A tag with a release built
  on it is left alone in that repository, with the reason.
- **Rename Everywhere** (branches): GitHub's rename, which moves protection
  with it, changes the default branch when it is the default, and retargets
  the open pull requests based on it; the preview says each of those.
- **Turn On or Off Everywhere** (webhooks).

Promote to Organization and the release train are
:mod:`quill.core.github.across_more_promote`.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from quill.core.github.across import why_failed
from quill.core.github.across_by_name import ByNameRow, Copy, Survey, describe_props, seg
from quill.core.github.across_changes import (
    LogEntry,
    Outcome,
    Plan,
    Result,
    Step,
    apply,
    blocked_for,
)
from quill.core.github.across_more_kinds import environment_props, hook_props, variable_value

__all__ = [
    "ADMIN_KINDS",
    "MORE_KINDS",
    "apply_more",
    "check_more",
    "exists",
    "hook_create",
    "plan_branch_rename",
    "plan_hooks_on_off",
    "plan_more_add",
    "plan_more_delete",
    "plan_more_same",
    "plan_set_secret",
    "run_more",
    "seal_for",
]

#: The kinds this module changes.
MORE_KINDS = frozenset({
    "tags",
    "branches",
    "environments",
    "secrets",
    "variables",
    "webhooks",
    "deploy_keys",
    "autolinks",
})
#: The kinds that need admin access in each repository.
ADMIN_KINDS = frozenset(MORE_KINDS - {"tags", "branches"})
_SAME = frozenset({"environments", "variables", "webhooks"})
_ADD = frozenset({"environments", "variables", "webhooks", "autolinks", "deploy_keys"})
NO_DEPLOY_KEY_COPY = (
    "GitHub accepts a deploy key in one repository only, so it cannot be added to more; make "
    "a key for each repository, or give a machine user access instead"
)


def _blocked(survey: Survey, repo: str) -> str:
    return blocked_for(survey, repo, admin=survey.kind in ADMIN_KINDS)


def _source(row: ByNameRow, winner: Sequence[tuple[str, str]]) -> Copy:
    return next(c for c in row.copies if c.props == tuple(winner))


def _owner(repo: str) -> str:
    return repo.split("/")[0].lower()


def _body(kind: str, source: Copy) -> tuple[tuple[str, str], ...]:
    """What the write sends, as strings, from the winning copy."""
    if kind == "environments":
        return (*source.props, *source.extra, ("source_repo", source.repository))
    if kind == "webhooks":
        return (*source.props, ("url", source.name))
    return source.props


def _why_not(kind: str, source: Copy, repo: str) -> str:
    """Why the winner cannot be copied to *repo* ("" when it can)."""
    if kind != "environments":
        return ""
    if source.prop("branches") == "custom":
        return (
            "the winner deploys from a custom list of branches, and those patterns belong to "
            "each repository; set them on the environment's own sheet"
        )
    teams = "Team:" in dict(source.extra).get("reviewer_ids", "")
    if teams and _owner(repo) != _owner(source.repository):
        return f"a team reviewer of {_owner(source.repository)} cannot review in another owner's"
    return ""


def plan_more_same(survey: Survey, row: ByNameRow, winner: Sequence[tuple[str, str]]) -> Plan:
    """Every copy of an environment, variable or webhook takes the winner's settings."""
    if survey.kind not in _SAME:
        raise ValueError(f"{survey.kind} have nothing to make the same.")
    source = _source(row, winner)
    steps = []
    for copy in row.copies:
        if copy.props == tuple(winner):
            steps.append(Step(copy.repository, "skip", after="already the same", copy=copy))
            continue
        blocked = _blocked(survey, copy.repository) or _why_not(
            survey.kind, source, copy.repository
        )
        before, after = describe_props(copy.props), describe_props(winner)
        body = _body(survey.kind, source)
        steps.append(Step(copy.repository, "align", before, after, blocked, copy, body))
    return Plan(survey.kind, row.name, "Make the same", tuple(steps))


def plan_more_add(
    survey: Survey, row: ByNameRow, winner: Sequence[tuple[str, str]], targets: Sequence[str] = ()
) -> Plan:
    """Make the row's thing, as the winner, in the repositories that lack it."""
    if survey.kind not in _ADD:
        raise ValueError(f"{survey.kind} are not added this way.")
    source = _source(row, winner)
    steps = []
    for repo in targets or row.missing:
        if survey.has(repo, row.name) is not None:
            steps.append(Step(repo, "skip", after="it already has one"))
            continue
        blocked = _blocked(survey, repo) or _why_not(survey.kind, source, repo)
        if survey.kind == "deploy_keys":
            blocked = NO_DEPLOY_KEY_COPY
        after = f"gains {row.name}, {describe_props(winner)}"
        steps.append(Step(repo, "create", "", after, blocked, None, _body(survey.kind, source)))
    return Plan(survey.kind, row.name, "Add to the missing", tuple(steps))


def plan_more_delete(survey: Survey, row: ByNameRow) -> Plan:
    if survey.kind == "branches":
        raise ValueError("Branches are deleted one at a time, in their repository.")
    steps = tuple(
        Step(c.repository, "delete", row.name, "deleted", _blocked(survey, c.repository), c)
        for c in row.copies
    )
    return Plan(survey.kind, row.name, "Delete", steps)


def plan_branch_rename(survey: Survey, row: ByNameRow, new_name: str) -> Plan:
    """Rename a branch everywhere, saying what follows from GitHub's rename in each."""
    steps = []
    for copy in row.copies:
        repo = copy.repository
        blocked = blocked_for(survey, repo)
        default, guarded = copy.prop("default") == "yes", copy.prop("protected") == "yes"
        if not blocked and (default or guarded) and survey.can_admin.get(repo) is False:
            blocked = "renaming a default or protected branch needs admin access"
        if not blocked and survey.has(repo, new_name) is not None:
            blocked = f"it already has a branch called {new_name}"
        effects = [f"renamed to {new_name}"]
        if default:
            effects.append(f"the default branch becomes {new_name}")
        if guarded:
            effects.append("its protection moves with it")
        prs = dict(copy.extra).get("open_prs", "0")
        if prs != "0":
            effects.append(f"{prs} open pull requests based on it are retargeted")
        body = (("new_name", new_name),)
        steps.append(Step(repo, "rename", copy.name, "; ".join(effects), blocked, copy, body))
    return Plan("branches", row.name, "Rename", tuple(steps))


def plan_hooks_on_off(survey: Survey, row: ByNameRow, on: bool) -> Plan:
    wanted = "on" if on else "off"
    steps = []
    for copy in row.copies:
        if copy.prop("active") == wanted:
            steps.append(Step(copy.repository, "skip", after=f"already {wanted}", copy=copy))
        else:
            blocked = _blocked(survey, copy.repository)
            body = (("active", wanted),)
            steps.append(Step(copy.repository, "switch", "", wanted, blocked, copy, body))
    return Plan("webhooks", row.name, f"Turn {wanted}", tuple(steps))


def plan_set_secret(survey: Survey, name: str, targets: Sequence[str]) -> Plan:
    """One new value for the secret in each target; the value itself is not in the plan."""
    steps = []
    for repo in targets:
        had = survey.has(repo, name) is not None
        after = "a new value, sealed for this repository" + ("" if had else ", new here")
        steps.append(Step(repo, "set_secret", "", after, _blocked(survey, repo)))
    return Plan("secrets", name, "Set the secret", tuple(steps))


# -- checking, just before the write ---------------------------------------------------


def exists(api: Any, path: str) -> Any:
    """GitHub's answer at *path*, or None when it is not found."""
    try:
        return api.rest("GET", path).data
    except Exception as exc:  # noqa: BLE001 - not found is an answer
        if "not found" in why_failed(exc):
            return None
        raise


def _item_path(kind: str, repo: str, copy: Copy) -> str:
    return {
        "environments": f"/repos/{repo}/environments/{seg(copy.ident)}",
        "variables": f"/repos/{repo}/actions/variables/{seg(copy.ident)}",
        "secrets": f"/repos/{repo}/actions/secrets/{seg(copy.ident)}",
        "webhooks": f"/repos/{repo}/hooks/{seg(copy.ident)}",
        "deploy_keys": f"/repos/{repo}/keys/{seg(copy.ident)}",
        "autolinks": f"/repos/{repo}/autolinks/{seg(copy.ident)}",
        "branches": f"/repos/{repo}/branches/{seg(copy.ident)}",
    }[kind]


def _props_now(kind: str, data: Any) -> tuple[tuple[str, str], ...] | None:
    data = data if isinstance(data, Mapping) else {}
    if kind == "environments":
        return environment_props(data)[0]
    if kind == "variables":
        return variable_value(data)
    if kind == "webhooks":
        return hook_props(data)
    return None


def _made_since(api: Any, plan: Plan, step: Step) -> str:
    """For a create: why it must not run because it exists now ("" when it may)."""
    from quill.core.github.tags import tag_exists

    repo, kind = step.repository, plan.kind
    if kind == "tags":
        if tag_exists(api, repo, plan.name):
            return f"{plan.name} was made there since you looked; an existing tag is never moved"
        return ""
    if kind == "webhooks":
        hooks = api.rest("GET", f"/repos/{repo}/hooks").data or []
        found = [h for h in hooks if isinstance(h, Mapping) and _hook_url(h) == plan.name]
    elif kind == "autolinks":
        links = api.rest("GET", f"/repos/{repo}/autolinks").data or []
        found = [a for a in links if isinstance(a, Mapping) and a.get("key_prefix") == plan.name]
    elif kind in ("environments", "variables"):
        fake = Copy(repo, plan.name, (), plan.name)
        if exists(api, _item_path(kind, repo, fake)) is not None:
            return "it was made there since you looked"
        return ""
    else:
        return ""
    return "it was made there since you looked" if found else ""


def _hook_url(hook: Mapping[str, Any]) -> str:
    config = hook.get("config")
    return str(config.get("url") or "") if isinstance(config, Mapping) else ""


def check_more(api: Any, plan: Plan, step: Step) -> str:
    """Why *step* must not run because GitHub changed under it ("" when it may)."""
    if step.action in ("create", "create_tag", "create_release"):
        return _made_since(api, plan, step)
    copy, kind, repo = step.copy, plan.kind, step.repository
    if copy is None or step.action == "set_secret":
        return ""
    if kind == "tags":
        from quill.core.github.tags import release_for_tag, tag_exists

        if not tag_exists(api, repo, copy.ident):
            return "it was deleted on GitHub since you looked"
        release = release_for_tag(api, repo, copy.ident)
        if release:
            return f"the release {release} is built on it; delete the release there first"
        return ""
    data = exists(api, _item_path(kind, repo, copy))
    if data is None:
        return "it was deleted or renamed on GitHub since you looked"
    if kind == "branches":
        new = dict(step.body).get("new_name", "")
        fake = Copy(repo, new, (), new)
        if new and exists(api, _item_path("branches", repo, fake)) is not None:
            return f"a branch called {new} was made there since you looked"
        return ""
    now = _props_now(kind, data)
    if now is not None and now != copy.props:
        return "it was changed on GitHub since you looked"
    return ""


# -- running ----------------------------------------------------------------------------


def _environment_body(body: Mapping[str, str]) -> dict[str, object]:
    reviewers = []
    for one in filter(None, body.get("reviewer_ids", "").split(";")):
        kind, _, number = one.partition(":")
        if number.isdigit():
            reviewers.append({"type": kind, "id": int(number)})
    policy = None
    if body.get("branches") == "protected":
        policy = {"protected_branches": True, "custom_branch_policies": False}
    return {
        "wait_timer": int(body.get("wait_timer", "0").split()[0] or 0),
        "prevent_self_review": body.get("self_review") == "prevented",
        "reviewers": reviewers,
        "deployment_branch_policy": policy,
    }


def _events(body: Mapping[str, str]) -> list[str]:
    return [e for e in body.get("events", "").split(", ") if e and e != "none"]


def hook_create(body: Mapping[str, str], secret: str) -> dict[str, object]:
    config: dict[str, object] = {"url": body["url"], "content_type": body.get("content_type")}
    if secret:
        config["secret"] = secret
    return {
        "name": "web",
        "active": body.get("active") != "off",
        "events": _events(body),
        "config": config,
    }


def seal_for(api: Any, base: str, value: str) -> dict[str, object]:
    from quill.core.github.sheets_deploy import seal_secret

    key = api.rest("GET", f"{base}/public-key").data
    if not isinstance(key, Mapping) or not key.get("key"):
        raise RuntimeError("GitHub sent no key to seal the secret with")
    return {"encrypted_value": seal_secret(str(key["key"]), value), "key_id": key.get("key_id")}


_NOUNS = {
    "environments": "environment",
    "variables": "variable",
    "secrets": "secret",
    "webhooks": "webhook",
    "deploy_keys": "deploy_key",
    "autolinks": "autolink",
    "tags": "tag",
    "branches": "branch",
}


def run_more(api: Any, plan: Plan, step: Step, secret: str = "") -> Outcome:
    """Do one step; the result's words and its Change History entry."""
    repo, kind, body = step.repository, plan.kind, dict(step.body)
    copy = step.copy
    said = _do(api, kind, plan.name, step, repo, body, copy, secret)
    log = LogEntry(_NOUNS[kind], (("repo", repo),), f"{repo} {_NOUNS[kind]} {plan.name}", said)
    return said, log


def _do(
    api: Any,
    kind: str,
    name: str,
    step: Step,
    repo: str,
    body: Mapping[str, str],
    copy: Copy | None,
    secret: str,
) -> str:
    action = step.action
    if action == "set_secret":
        base = f"/repos/{repo}/actions/secrets"
        api.rest("PUT", f"{base}/{seg(name)}", body=seal_for(api, base, secret))
        return "set; the value was sealed for this repository"
    if action == "delete" and copy is not None:
        if kind == "tags":
            from quill.core.github.tags import delete_tag

            delete_tag(api, repo, copy.ident)
        else:
            api.rest("DELETE", _item_path(kind, repo, copy))
        return "deleted"
    if action == "rename" and copy is not None:
        api.rest("POST", f"{_item_path(kind, repo, copy)}/rename", body=dict(body))
        return step.after
    if action == "switch" and copy is not None:
        api.rest("PATCH", _item_path(kind, repo, copy), body={"active": body["active"] == "on"})
        return f"turned {body['active']}"
    if action in ("align", "create"):
        _write(api, kind, name, repo, body, copy, secret)
        return "made the same" if action == "align" else "added"
    raise ValueError(f"{kind} cannot {action}.")


def _write(
    api: Any,
    kind: str,
    name: str,
    repo: str,
    body: Mapping[str, str],
    copy: Copy | None,
    secret: str,
) -> None:
    if kind == "environments":
        api.rest("PUT", f"/repos/{repo}/environments/{seg(name)}", body=_environment_body(body))
    elif kind == "variables" and copy is not None:
        path = _item_path(kind, repo, copy)
        api.rest("PATCH", path, body={"name": name, "value": body["value"]})
    elif kind == "variables":
        api.rest(
            "POST", f"/repos/{repo}/actions/variables", body={"name": name, "value": body["value"]}
        )
    elif kind == "webhooks" and copy is not None:
        path = _item_path(kind, repo, copy)
        api.rest("PATCH", path, body={"events": _events(body), "active": body["active"] == "on"})
        api.rest("PATCH", f"{path}/config", body={"content_type": body["content_type"]})
    elif kind == "webhooks":
        api.rest("POST", f"/repos/{repo}/hooks", body=hook_create(body, secret))
    elif kind == "autolinks":
        link = {
            "key_prefix": name,
            "url_template": body["url_template"],
            "is_alphanumeric": body.get("alphanumeric") != "numbers",
        }
        api.rest("POST", f"/repos/{repo}/autolinks", body=link)
    else:
        raise ValueError(f"{kind} cannot be written this way.")


def apply_more(
    api: Any,
    plan: Plan,
    *,
    secret: str = "",
    on_step: Callable[[Result], None] | None = None,
) -> list[Result]:
    """Run a plan for one of :data:`MORE_KINDS`. *secret* is the value typed once, if any."""

    def runner(api_: Any, plan_: Plan, step: Step) -> Outcome:
        from quill.core.github.across_more_promote import run_train

        if step.action in ("create_tag", "create_release"):
            return run_train(api_, plan_, step)
        return run_more(api_, plan_, step, secret)

    return apply(api, plan, on_step=on_step, runner=runner, check=check_more)
