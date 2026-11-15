"""Topics, rulesets and branch protection across repositories, and Promote to Organization.

The administrator's half of PRD 22.11's by-name table. Each plan is the same
:class:`~quill.core.github.across_changes.Plan` with a step per repository,
blocked where the account does not administer the repository, and run by
:func:`quill.core.github.across_changes.apply` with this module's runner and
conflict check, so the preview, the re-read before writing and the result
per repository are the same as for labels.

- **Topics:** add one to the repositories that lack it, or remove it
  everywhere. GitHub replaces a repository's whole topic list, so each step
  reads the list again immediately before writing it and changes only the one
  topic: a topic somebody added since the survey is kept. Change History can
  undo it through the Repository sheet's Topics field.
- **Rulesets:** make every copy the same as the winning one (its full
  definition is read from the repository that has it), or add it where it
  is missing.
- **Branch protection:** make each default branch's protection the same as
  the winner's: required approvals, stale-review dismissal, code-owner
  review, required checks and whether admins are included. Who may push
  (restrictions) is never copied: people and teams differ by repository.
  Making protection "the same" as an unprotected branch is refused; removing
  protection is a decision for the repository's own settings.
- **Promote to Organization:** one organization ruleset with the winner's
  rules, covering the set's repositories in that organization, then each
  repository's own copy deleted -- only after the organization ruleset was
  created, so protection never lapses. Labels have no organization-level
  equivalent in GitHub's API (default labels for new repositories are set on
  github.com only), so they are not promoted.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.github.across import why_failed
from quill.core.github.across_by_name import (
    PROTECTION_PREFIX,
    ByNameRow,
    Survey,
    protection_props,
    ruleset_props,
    seg,
)
from quill.core.github.across_changes import (
    LogEntry,
    Outcome,
    Plan,
    Result,
    Step,
    apply,
    blocked_for,
)

__all__ = [
    "apply_admin",
    "apply_promote",
    "plan_promote",
    "plan_rules_add_missing",
    "plan_rules_same",
    "plan_topic_add",
    "plan_topic_remove",
]


def _admin(survey: Survey, repo: str) -> str:
    return blocked_for(survey, repo, admin=True)


# -- topics -------------------------------------------------------------------------


def plan_topic_add(survey: Survey, row: ByNameRow, targets: Sequence[str] = ()) -> Plan:
    steps = []
    for repo in targets or row.missing:
        if survey.has(repo, row.name) is not None:
            steps.append(Step(repo, "skip", after="it already has it"))
        else:
            steps.append(Step(repo, "add_topic", "", f"gains {row.name}", _admin(survey, repo)))
    return Plan("topics", row.name, "Add the topic", tuple(steps))


def plan_topic_remove(survey: Survey, row: ByNameRow) -> Plan:
    steps = tuple(
        Step(c.repository, "remove_topic", row.name, "removed", _admin(survey, c.repository), c)
        for c in row.copies
    )
    return Plan("topics", row.name, "Remove the topic", steps)


def _topics(api: Any, repo: str) -> list[str]:
    answer = api.rest("GET", f"/repos/{repo}/topics")
    names = answer.data.get("names") if isinstance(answer.data, Mapping) else None
    return [str(n) for n in names or []]


def _run_topic(api: Any, plan: Plan, step: Step) -> Outcome:
    repo, topic = step.repository, plan.name
    before = _topics(api, repo)  # read again now: GitHub replaces the whole list
    if step.action == "add_topic":
        after = before if topic in before else [*before, topic]
        said = "added" if topic not in before else "no change, it was added on GitHub meanwhile"
    else:
        after = [t for t in before if t != topic]
        said = "removed" if topic in before else "no change, it was removed on GitHub meanwhile"
    if after != before:
        api.rest("PUT", f"/repos/{repo}/topics", body={"names": after})
    proven = _topics(api, repo) == after
    change = (("topics", "Topics", tuple(before), tuple(after)),)
    log = LogEntry(
        "repository",
        (("repo", repo),),
        f"{repo} topics",
        f"topic {topic} {said}",
        change,
        after != before,
        proven,
    )
    return said, log


# -- rulesets and branch protection ---------------------------------------------------


def _is_protection(row: ByNameRow) -> bool:
    return row.name.startswith(PROTECTION_PREFIX)


def _source(row: ByNameRow, winner: Sequence[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    copy = next(c for c in row.copies if c.props == tuple(winner))
    return (("source_repo", copy.repository), ("source_id", copy.ident))


def plan_rules_same(survey: Survey, row: ByNameRow, winner: Sequence[tuple[str, str]]) -> Plan:
    """Every copy of a ruleset, or every default branch's protection, takes the winner's."""
    source = _source(row, winner)
    unprotect = _is_protection(row) and dict(winner).get("protected") != "yes"
    steps = []
    for copy in row.copies:
        if copy.props == tuple(winner):
            steps.append(Step(copy.repository, "skip", after="already the same", copy=copy))
            continue
        blocked = _admin(survey, copy.repository)
        if unprotect:
            blocked = (
                "making protection match an unprotected branch would remove it; remove it in "
                "the repository's own settings if that is meant"
            )
        elif not copy.ident:
            blocked = "its protection could not be read, so it is left alone"
        before = ", ".join(f"{k} {v}" for k, v in copy.props)
        after = ", ".join(f"{k} {v}" for k, v in winner)
        steps.append(Step(copy.repository, "align_rules", before, after, blocked, copy, source))
    return Plan("rules", row.name, "Make the same", tuple(steps))


def plan_rules_add_missing(
    survey: Survey, row: ByNameRow, winner: Sequence[tuple[str, str]], targets: Sequence[str] = ()
) -> Plan:
    if _is_protection(row):
        steps = tuple(
            Step(r, "skip", blocked="branch protection is per branch; Make the Same covers it")
            for r in targets or row.missing
        )
        return Plan("rules", row.name, "Add to the missing", steps)
    source = _source(row, winner)
    steps = tuple(
        Step(
            r,
            "create_ruleset",
            "",
            f"gains the ruleset {row.name}",
            _admin(survey, r),
            None,
            source,
        )
        for r in targets or row.missing
    )
    return Plan("rules", row.name, "Add to the missing", steps)


_RULESET_KEYS = ("name", "target", "enforcement", "conditions", "rules", "bypass_actors")


def _ruleset_body(api: Any, body: Mapping[str, str]) -> dict[str, object]:
    answer = api.rest("GET", f"/repos/{body['source_repo']}/rulesets/{seg(body['source_id'])}")
    data = answer.data if isinstance(answer.data, Mapping) else {}
    return {k: data[k] for k in _RULESET_KEYS if data.get(k) is not None}


def _protection_body(api: Any, body: Mapping[str, str]) -> dict[str, object]:
    """PUT's shape from GET's: what protection requires, never who may push."""
    path = f"/repos/{body['source_repo']}/branches/{seg(body['source_id'])}/protection"
    data = api.rest("GET", path).data
    data = data if isinstance(data, Mapping) else {}
    checks = data.get("required_status_checks")
    reviews = data.get("required_pull_request_reviews")
    admins = data.get("enforce_admins")
    return {
        "required_status_checks": (
            {"strict": bool(checks.get("strict")), "contexts": list(checks.get("contexts") or [])}
            if isinstance(checks, Mapping)
            else None
        ),
        "enforce_admins": bool(isinstance(admins, Mapping) and admins.get("enabled")),
        "required_pull_request_reviews": (
            {
                "required_approving_review_count": int(
                    reviews.get("required_approving_review_count") or 0
                ),
                "dismiss_stale_reviews": bool(reviews.get("dismiss_stale_reviews")),
                "require_code_owner_reviews": bool(reviews.get("require_code_owner_reviews")),
            }
            if isinstance(reviews, Mapping)
            else None
        ),
        "restrictions": None,
    }


def _check(api: Any, plan: Plan, step: Step) -> str:
    """The copy must still be what the survey read, or the step is skipped."""
    copy = step.copy
    if plan.kind == "topics" or copy is None:
        return ""
    try:
        if plan.name.startswith(PROTECTION_PREFIX):
            data = api.rest(
                "GET", f"/repos/{step.repository}/branches/{seg(copy.ident)}/protection"
            ).data
            now = protection_props(data if isinstance(data, Mapping) else {})
        else:
            data = api.rest("GET", f"/repos/{step.repository}/rulesets/{seg(copy.ident)}").data
            now = ruleset_props(data if isinstance(data, Mapping) else {})
            if dict(copy.props).get("rules") == "not listed":
                now = tuple((k, v) for k, v in now if k != "rules") + (("rules", "not listed"),)
    except Exception as exc:  # noqa: BLE001
        reason = why_failed(exc)
        if "not found" in reason and copy.prop("protected") == "no":
            return ""
        return "it was deleted on GitHub since you looked" if "not found" in reason else ""
    return "" if now == copy.props else "it was changed on GitHub since you looked"


def _run_admin(api: Any, plan: Plan, step: Step) -> Outcome:
    if plan.kind == "topics":
        return _run_topic(api, plan, step)
    repo, body = step.repository, dict(step.body)
    target = f"{repo} {plan.name}"
    if step.action == "align_rules" and step.copy is not None:
        if plan.name.startswith(PROTECTION_PREFIX):
            path = f"/repos/{repo}/branches/{seg(step.copy.ident)}/protection"
            api.rest("PUT", path, body=_protection_body(api, body))
        else:
            path = f"/repos/{repo}/rulesets/{seg(step.copy.ident)}"
            api.rest("PUT", path, body=_ruleset_body(api, body))
        said = f"made the same as {body['source_repo']}"
        changes = (("summary", plan.name, step.before, step.after),)
        return said, LogEntry("ruleset", (("repo", repo),), target, said, changes)
    if step.action == "create_ruleset":
        api.rest("POST", f"/repos/{repo}/rulesets", body=_ruleset_body(api, body))
        return "added", LogEntry("ruleset", (("repo", repo),), target, "added")
    raise ValueError(f"rules cannot {step.action}.")


def apply_admin(api: Any, plan: Plan) -> list[Result]:
    """Run a topics or rules plan. Runs off the UI thread."""
    return apply(api, plan, runner=_run_admin, check=_check)


# -- Promote to Organization -------------------------------------------------------------


def plan_promote(
    survey: Survey, row: ByNameRow, winner: Sequence[tuple[str, str]], organization: str
) -> Plan:
    """One organization ruleset, then each in-organization copy deleted (rulesets only)."""
    if _is_protection(row):
        refused = Step(
            f"organization {organization}",
            "skip",
            blocked="classic branch protection has no organization form; make the branches' "
            "protection a repository ruleset first",
        )
        return Plan("rules", row.name, "Promote to Organization", (refused,))
    source = _source(row, winner)
    inside = [c for c in row.copies if c.repository.split("/")[0].lower() == organization.lower()]
    names = ",".join(c.repository.split("/")[1] for c in inside)
    first = Step(
        f"organization {organization}",
        "create_org_ruleset",
        "",
        f"an organization ruleset {row.name} for {len(inside)} repositories",
        "" if inside else f"no repository in the set belongs to {organization}",
        None,
        (*source, ("organization", organization), ("names", names)),
    )
    steps = [first]
    for copy in row.copies:
        if copy not in inside:
            steps.append(
                Step(copy.repository, "skip", after=f"not in {organization}, keeps its own")
            )
        else:
            steps.append(
                Step(
                    copy.repository,
                    "delete_ruleset",
                    row.name,
                    "replaced by the organization's",
                    _admin(survey, copy.repository),
                    copy,
                )
            )
    return Plan("rules", row.name, "Promote to Organization", tuple(steps))


def _run_promote(api: Any, plan: Plan, step: Step) -> Outcome:
    body = dict(step.body)
    if step.action == "create_org_ruleset":
        definition = _ruleset_body(api, body)
        conditions = definition.get("conditions")
        ref = conditions.get("ref_name") if isinstance(conditions, Mapping) else None
        definition["conditions"] = {
            "ref_name": ref or {"include": ["~DEFAULT_BRANCH"], "exclude": []},
            "repository_name": {"include": body["names"].split(","), "exclude": []},
        }
        organization = body["organization"]
        api.rest("POST", f"/orgs/{organization}/rulesets", body=definition)
        said = f"created the organization ruleset {plan.name}"
        return said, LogEntry(
            "ruleset", (("org", organization),), f"{organization} {plan.name}", said
        )
    if step.action == "delete_ruleset" and step.copy is not None:
        api.rest("DELETE", f"/repos/{step.repository}/rulesets/{seg(step.copy.ident)}")
        said = "its own copy deleted; the organization ruleset covers it"
        return said, LogEntry(
            "ruleset", (("repo", step.repository),), f"{step.repository} {plan.name}", said
        )
    raise ValueError(f"cannot {step.action}.")


def apply_promote(api: Any, plan: Plan) -> list[Result]:
    """Create the organization ruleset first; delete copies only if that worked."""
    first, rest = plan.steps[0], plan.steps[1:]
    head = apply(
        api,
        Plan(plan.kind, plan.name, plan.operation, (first,)),
        runner=_run_promote,
        check=lambda *_a: "",
    )
    if not head[0].ok:
        kept = [
            Result(
                s.repository,
                s.action == "skip",
                "no change, " + (s.after or "kept")
                if s.action == "skip"
                else "kept: the organization ruleset was not created",
            )
            for s in rest
        ]
        return head + kept
    tail = Plan(plan.kind, plan.name, plan.operation, rest)
    return head + apply(api, tail, runner=_run_promote, check=_check)
