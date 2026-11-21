"""The rules that block a pull request, each by name (GX09, complete.md 1.3).

GitHub's merge box says "Merging is blocked" and leaves the person to find
which rule. :func:`name_blockers` reads what the review window's Check Merge
Policy reads, through the Workbench's own
:class:`~quill.core.github.workbench_api.GitHubApi`, and says which rule wants
what:

- ``GET /repos/{o}/{r}/rules/branches/{branch}`` -- every active ruleset rule
  on the base branch, each with the ruleset it comes from, named from
  ``GET /repos/{o}/{r}/rulesets``;
- the base branch's classic protection
  (``GET /repos/{o}/{r}/branches/{branch}/protection``), which needs admin
  access to read; without it, the required checks from the branch itself;
- **required checks, by name**: one that failed, has not finished, or has not
  reported on the head commit at all, with the rule that requires it;
- **approving reviews**: how many a rule wants and how many there are;
- **CODEOWNERS**: when a rule wants a code owner's review, the changed files
  are matched to the CODEOWNERS file on the base branch (the last matching
  line wins, as on GitHub), and each line whose owners have not approved is
  named, by line number and pattern, with who could approve;
- **the merge queue**: which rule makes the branch merge only through it.

Nothing here decides whether the pull request can merge: GitHub's answer
(:class:`~quill.core.github.merge_readiness.Readiness`) stands, and these
sentences only name the rules behind it. A part QUILL could not read is
listed as unread, so a missing permission never reads as "no rule".

wx-free and strict-typed.
"""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from quill.core.github.merge_readiness import NamedRules, Readiness
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.template_files import owners_for
from quill.core.github.workbench_api import GitHubApi

__all__ = ["CODEOWNERS_PATHS", "FILE_LIMIT", "name_blockers"]

#: Where GitHub looks for CODEOWNERS, in the order it looks.
CODEOWNERS_PATHS = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")
#: Changed files read to match CODEOWNERS (three pages).
FILE_LIMIT = 300

#: Rules that can block a merge without a check or a review, in words.
_OTHER_RULES = {
    "required_signatures": "signed commits",
    "required_linear_history": "a straight history, with no merge commits",
    "required_deployments": "a successful deployment first",
    "update": "permission to push to it",
}


@dataclass(frozen=True)
class _Rule:
    kind: str
    source: str
    """Who asks, in words: 'the ruleset "Protect main"' or 'the branch protection on main'."""
    parameters: Mapping[str, Any] = field(default_factory=dict)


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" + ("" if count == 1 else "s")


def _either(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} or {names[-1]}"


def _get(api: GitHubApi, path: str, query: Mapping[str, str] | None = None) -> Any:
    return api.rest("GET", path, query=dict(query or {})).data


def _ruleset_names(api: GitHubApi, repo: str) -> dict[int, str]:
    try:
        rows = _get(api, f"/repos/{repo}/rulesets", {"includes_parents": "true", "per_page": "100"})
    except GitHubRestError:
        return {}
    return {
        int(row["id"]): str(row.get("name") or "")
        for row in (rows if isinstance(rows, list) else ())
        if isinstance(row, Mapping) and isinstance(row.get("id"), int)
    }


def _ruleset_rules(api: GitHubApi, repo: str, base: str, unread: list[str]) -> list[_Rule]:
    path = f"/repos/{repo}/rules/branches/{quote(base, safe='')}"
    try:
        rows = _get(api, path, {"per_page": "100"})
    except GitHubRestError:
        unread.append(f"the rulesets on {base}")
        return []
    rows = [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []
    names = _ruleset_names(api, repo) if rows else {}
    found: list[_Rule] = []
    for row in rows:
        ident = row.get("ruleset_id")
        name = names.get(ident, "") if isinstance(ident, int) else ""
        owner = " from the organization" if row.get("ruleset_source_type") == "Organization" else ""
        source = f'the ruleset "{name}"{owner}' if name else f"ruleset {ident}{owner}"
        params = row.get("parameters")
        found.append(
            _Rule(str(row.get("type") or ""), source, params if isinstance(params, Mapping) else {})
        )
    return found


def _status_contexts(checks: Any) -> list[dict[str, str]]:
    contexts = [str(c) for c in (checks or {}).get("contexts") or () if c]
    contexts += [
        str(c.get("context"))
        for c in (checks or {}).get("checks") or ()
        if isinstance(c, Mapping) and c.get("context")
    ]
    return [{"context": c} for c in dict.fromkeys(contexts)]


def _protection_rules(api: GitHubApi, repo: str, base: str, unread: list[str]) -> list[_Rule]:
    source = f"the branch protection on {base}"
    branch = f"/repos/{repo}/branches/{quote(base, safe='')}"
    try:
        data = _get(api, f"{branch}/protection")
    except GitHubRestError as exc:
        if exc.status == 404:
            return []
        try:  # Without admin access the branch itself still lists its required checks.
            summary = _get(api, branch)
        except GitHubRestError:
            unread.append(source)
            return []
        protection = summary.get("protection") if isinstance(summary, Mapping) else None
        if not isinstance(protection, Mapping) or not protection.get("enabled"):
            return []
        unread.append(f"which reviews {source} wants (that needs admin access)")
        contexts = _status_contexts(protection.get("required_status_checks"))
        return [_Rule("required_status_checks", source, {"required_status_checks": contexts})]
    if not isinstance(data, Mapping):
        return []
    found: list[_Rule] = []
    contexts = _status_contexts(data.get("required_status_checks"))
    if contexts:
        found.append(_Rule("required_status_checks", source, {"required_status_checks": contexts}))
    reviews = data.get("required_pull_request_reviews")
    if isinstance(reviews, Mapping):
        params = {
            "required_approving_review_count": reviews.get("required_approving_review_count") or 0,
            "require_code_owner_review": bool(reviews.get("require_code_owner_reviews")),
        }
        found.append(_Rule("pull_request", source, params))
    for key, kind in (
        ("required_signatures", "required_signatures"),
        ("required_linear_history", "required_linear_history"),
    ):
        if (data.get(key) or {}).get("enabled"):
            found.append(_Rule(kind, source))
    return found


def _approvers(api: GitHubApi, repo: str, number: int) -> set[str]:
    """Who has approved: each reviewer's latest review that is not only a comment."""
    rows = _get(api, f"/repos/{repo}/pulls/{number}/reviews", {"per_page": "100"})
    latest: dict[str, str] = {}
    for row in rows if isinstance(rows, list) else ():
        user = row.get("user") if isinstance(row, Mapping) else None
        state = str(row.get("state") or "") if isinstance(row, Mapping) else ""
        if (
            isinstance(user, Mapping)
            and user.get("login")
            and state not in ("COMMENTED", "PENDING")
        ):
            latest[str(user["login"]).casefold()] = state
    return {login for login, state in latest.items() if state == "APPROVED"}


def _codeowners(api: GitHubApi, repo: str, base: str) -> tuple[str, str]:
    """(path, text) of the CODEOWNERS file on *base*, or ("", "") when there is none."""
    for path in CODEOWNERS_PATHS:
        try:
            data = _get(api, f"/repos/{repo}/contents/{path}", {"ref": base})
        except GitHubRestError as exc:
            if exc.status == 404:
                continue
            raise
        if isinstance(data, Mapping) and data.get("type") == "file":
            try:
                text = base64.b64decode(str(data.get("content") or "")).decode("utf-8", "replace")
            except (binascii.Error, ValueError):
                text = ""
            return path, text
    return "", ""


def _changed_files(api: GitHubApi, repo: str, number: int, unread: list[str]) -> list[str]:
    files: list[str] = []
    for page in range(1, FILE_LIMIT // 100 + 1):
        rows = _get(
            api, f"/repos/{repo}/pulls/{number}/files", {"per_page": "100", "page": str(page)}
        )
        rows = rows if isinstance(rows, list) else []
        files += [
            str(r.get("filename")) for r in rows if isinstance(r, Mapping) and r.get("filename")
        ]
        if len(rows) < 100:
            return files
    unread.append(f"every changed file (only the first {FILE_LIMIT} were matched to CODEOWNERS)")
    return files


class _Owners:
    """Whether an owner has approved: a person directly, a team through a member."""

    def __init__(self, api: GitHubApi, approvers: set[str]) -> None:
        self.api, self.approvers = api, approvers
        self._members: dict[tuple[str, str], bool | None] = {}

    def _member(self, team: str, login: str) -> bool | None:
        key = (team, login)
        if key not in self._members:
            org, _slash, slug = team.partition("/")
            try:
                data = _get(self.api, f"/orgs/{org}/teams/{slug}/memberships/{login}")
                self._members[key] = isinstance(data, Mapping) and data.get("state") == "active"
            except GitHubRestError as exc:
                self._members[key] = False if exc.status == 404 else None
        return self._members[key]

    def approved(self, owner: str) -> bool | None:
        """True, False, or None when QUILL cannot tell (an email address, an unreadable team)."""
        if not owner.startswith("@"):
            return None
        name = owner[1:].casefold()
        if "/" not in name:
            return name in self.approvers
        answers = [self._member(name, login) for login in sorted(self.approvers)]
        if any(answers):
            return True
        return None if None in answers else False


def _codeowner_blockers(
    api: GitHubApi, repo: str, ready: Readiness, source: str, approvers: set[str], unread: list[str]
) -> list[str]:
    try:
        path, text = _codeowners(api, repo, ready.base)
    except GitHubRestError:
        unread.append(f"the CODEOWNERS file on {ready.base}")
        return []
    if not path:
        return []
    try:
        files = _changed_files(api, repo, ready.number, unread)
    except GitHubRestError:
        unread.append("the pull request's changed files")
        return []
    lines: dict[int, tuple[Any, list[str]]] = {}
    for name in files:
        rule = owners_for(text, name)
        if rule is not None and rule.owners:
            lines.setdefault(rule.line, (rule, []))[1].append(name)
    owners, found = _Owners(api, approvers), []
    for _line, (rule, matched) in sorted(lines.items()):
        answers = [owners.approved(owner) for owner in rule.owners]
        if any(answers):
            continue
        who = _either(list(rule.owners))
        where = (
            f"{path} line {rule.line}, {rule.pattern}, owns {_plural(len(matched), 'changed file')}"
            f", such as {matched[0]}"
        )
        if None in answers:
            found.append(
                f"{_cap(source)} wants a code owner's review. {_cap(where)}; QUILL could not "
                f"tell whether {who} approved."
            )
        else:
            found.append(
                f"{_cap(source)} wants a code owner's review, and none from {who} has approved: "
                f"{where}."
            )
    return found


def _check_blockers(rules: list[_Rule], ready: Readiness) -> tuple[list[str], set[str]]:
    by_name = {check.name: check for check in ready.checks}
    found: list[str] = []
    named: set[str] = set()
    at = f" on commit {ready.short_head}" if ready.head else ""
    for rule in rules:
        if rule.kind != "required_status_checks":
            continue
        for item in rule.parameters.get("required_status_checks") or ():
            context = str(item.get("context") or "") if isinstance(item, Mapping) else ""
            check = by_name.get(context)
            if not context or context in named or (check is not None and check.state == "passed"):
                continue
            named.add(context)
            if check is None:
                state = f"has not reported{at}"
            elif check.state == "failed":
                state = "failed. Re-run or fix it"
            else:
                state = "has not finished"
            found.append(f"Check {context}, which {rule.source} requires, {state}.")
    return found, named


def _review_blockers(
    api: GitHubApi, repo: str, ready: Readiness, asking: list[_Rule], unread: list[str]
) -> list[str]:
    """Approval counts, then CODEOWNERS; nothing is guessed when the reviews are unreadable."""
    try:
        approvers = _approvers(api, repo, ready.number)
    except GitHubRestError:
        unread.append("the pull request's reviews")
        return []
    found: list[str] = []
    for rule in asking:
        wanted = rule.parameters.get("required_approving_review_count") or 0
        if isinstance(wanted, int) and wanted > len(approvers):
            found.append(
                f"{_cap(rule.source)} wants {_plural(wanted, 'approving review')}; "
                f"it has {len(approvers)}."
            )
    owner_rule = next(
        (rule for rule in asking if rule.parameters.get("require_code_owner_review")), None
    )
    if owner_rule is not None:
        found += _codeowner_blockers(api, repo, ready, owner_rule.source, approvers, unread)
    return found


def name_blockers(api: GitHubApi, repository: str, ready: Readiness) -> NamedRules:
    """Name each rule on the base branch that blocks *ready*; GitHub's answer stays as it is."""
    unread: list[str] = []
    rules = _ruleset_rules(api, repository, ready.base, unread)
    rules += _protection_rules(api, repository, ready.base, unread)
    queue = next((rule.source for rule in rules if rule.kind == "merge_queue"), "")
    if ready.can_merge:
        return NamedRules(queue_rule=queue, unread=tuple(unread))
    blockers, checks = _check_blockers(rules, ready)
    asking = [rule for rule in rules if rule.kind == "pull_request"]
    said = (
        _review_blockers(api, repository, ready, asking, unread)
        if ready.review == "REVIEW_REQUIRED" and asking
        else []
    )
    reviews = bool(said)
    blockers += said
    if not blockers and ready.merge_state == "BLOCKED":
        for rule in rules:
            if rule.kind in _OTHER_RULES:
                blockers.append(
                    f"{_cap(rule.source)} requires {_OTHER_RULES[rule.kind]}; "
                    "that may be what blocks it."
                )
    return NamedRules(
        blockers=tuple(dict.fromkeys(blockers)),
        checks=frozenset(checks),
        reviews=reviews,
        queue_rule=queue,
        unread=tuple(dict.fromkeys(unread)),
    )
