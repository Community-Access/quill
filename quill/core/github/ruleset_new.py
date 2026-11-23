"""New Ruleset in one repository (GitHub PRD 18.3.1; GH-R-151's single-repository home).

Ctrl+N in a repository's Settings > Rulesets makes a ruleset from a few plain
questions: its name, whether it guards branches or tags, which ones, the rules
that need no further setting (and the number of approvals, for a pull
request), and whether it is on. Every other rule and setting is on the
ruleset's own sheet afterwards (Alt+Enter), which edits the whole ruleset.

Evaluate mode is not offered: GitHub gives it to Enterprise organizations only.
Add to Missing on a Rules and Branch Protection row copies a whole ruleset to
other repositories (:mod:`quill.core.github.across_admin_changes`).

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.rulesets import summary
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "BRANCH_ONLY",
    "ENFORCEMENT_CHOICES",
    "NEW_RULES",
    "REF_CHOICES",
    "RulesetRefused",
    "create_ruleset",
    "ruleset_request",
]


class RulesetRefused(CodedError):
    code = "QUILL-GITHUB-RULESET-REFUSED"


#: The rules New Ruleset offers as check boxes: each needs no further answer,
#: except a pull request's number of approvals, which is asked for next.
NEW_RULES: tuple[tuple[str, str], ...] = (
    ("pull_request", "Require a pull request before merging"),
    ("non_fast_forward", "Block force pushes"),
    ("deletion", "Restrict deletions"),
    ("required_linear_history", "Require linear history"),
    ("required_signatures", "Require signed commits"),
    ("creation", "Restrict creations"),
    ("update", "Restrict updates"),
)
#: Which branches or tags, as GitHub's ref_name condition.
REF_CHOICES: tuple[tuple[str, str], ...] = (
    ("~DEFAULT_BRANCH", "The default branch"),
    ("~ALL", "Every one"),
    ("pattern", "Names matching a pattern..."),
)
#: Rules that make no sense on a tag (a tag is never merged), left out of its check list.
BRANCH_ONLY = frozenset({"pull_request"})
ENFORCEMENT_CHOICES: tuple[tuple[str, str], ...] = (
    ("active", "On: it applies as soon as it is made"),
    ("disabled", "Off: made now, turned on later on its sheet"),
)
_MAX_APPROVALS = 10


def _ref(target: str, include: str) -> str:
    if include.startswith("~"):
        return include
    prefix = "refs/tags/" if target == "tag" else "refs/heads/"
    return include if include.startswith("refs/") else prefix + include


def ruleset_request(
    name: str,
    target: str,
    include: str,
    rules: Sequence[str],
    *,
    approvals: int = 1,
    enforcement: str = "active",
) -> dict[str, object]:
    """The body GitHub's POST takes; raises :class:`RulesetRefused` before anything is sent."""
    name = name.strip()
    if not name:
        raise RulesetRefused("A ruleset needs a name.")
    if target not in ("branch", "tag"):
        raise RulesetRefused("A ruleset here guards branches or tags.")
    include = include.strip()
    if not include:
        raise RulesetRefused("Name the branches or tags it guards, such as release/*.")
    if target == "tag" and include == "~DEFAULT_BRANCH":
        raise RulesetRefused("A tag ruleset guards tags; choose every tag or a pattern.")
    if target == "tag" and BRANCH_ONLY & set(rules):
        raise RulesetRefused("A tag is never merged, so a tag ruleset has no pull request rule.")
    known = dict(NEW_RULES)
    if not rules:
        raise RulesetRefused("Check at least one rule.")
    unknown = [rule for rule in rules if rule not in known]
    if unknown:
        raise RulesetRefused(f"New Ruleset does not offer {', '.join(unknown)}.")
    if enforcement not in dict(ENFORCEMENT_CHOICES):
        raise RulesetRefused("A new ruleset is on or off.")
    if not 0 <= approvals <= _MAX_APPROVALS:
        raise RulesetRefused(f"Approvals are from 0 to {_MAX_APPROVALS}, not {approvals}.")
    made: list[dict[str, object]] = []
    for rule in rules:
        if rule == "pull_request":
            made.append({
                "type": rule,
                "parameters": {
                    "required_approving_review_count": approvals,
                    "dismiss_stale_reviews_on_push": False,
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_review_thread_resolution": False,
                },
            })
        else:
            made.append({"type": rule})
    return {
        "name": name,
        "target": target,
        "enforcement": enforcement,
        "conditions": {"ref_name": {"include": [_ref(target, include)], "exclude": []}},
        "rules": made,
    }


def create_ruleset(api: GitHubApi, repo: str, body: Mapping[str, Any]) -> str:
    """Make the ruleset in *repo*; the sentence says what GitHub made, from its answer."""
    name = str(body.get("name") or "")
    try:
        existing = api.rest("GET", f"/repos/{repo}/rulesets", query={"per_page": "100"}).data
    except GitHubRestError as exc:
        raise RulesetRefused(f"the rulesets of {repo} could not be read first ({exc})") from exc
    for entry in existing if isinstance(existing, list) else ():
        if isinstance(entry, Mapping) and str(entry.get("name") or "").casefold() == (
            name.casefold()
        ):
            raise RulesetRefused(f"{repo} already has a ruleset called {entry.get('name')}.")
    try:
        made = api.rest("POST", f"/repos/{repo}/rulesets", body=dict(body)).data
    except GitHubRestError as exc:
        if exc.status in (401, 403):
            raise RulesetRefused(
                "GitHub refused it; a ruleset needs admin access, and on a private repository "
                "a GitHub Pro or Team plan."
            ) from exc
        raise RulesetRefused(str(exc)) from exc
    # An answer without the ruleset's rules says nothing about them; read the request.
    answer = made if isinstance(made, Mapping) and "rules" in made else body
    said = summary(answer)
    if said == summary(body):  # the question before it already read it out (GATE-13)
        return f"Made the ruleset {name} in {repo}, as described."
    return f"Made the ruleset {name} in {repo}, but GitHub has it as: {said}"
