"""Rulesets and the access matrices, as lists in the Workbench's tree (GitHub PRD 18.3).

* **A repository > Settings > Rulesets** and **an organization > Rulesets**:
  each ruleset as a sentence; Alt+Enter opens its sheet (every rule, the
  target, the repositories an organization ruleset covers, who may bypass,
  and the Summary), and Delete removes it after its id is typed.
* **An organization > Rule Insights**: the pushes its rulesets judged.
* **An organization > Access Review: People** and **Access Review: Teams**:
  the matrices of :mod:`quill.core.github.access_matrix`, one row a pair,
  each saying the role and where it comes from.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.access_matrix import people_rows, team_rows
from quill.core.github.resource_engine import ResourceSpec

__all__ = ["ADMIN_SPECS"]

_ENFORCED = {"active": "Active", "evaluate": "Evaluate only", "disabled": "Disabled"}
_TARGETS = {"branch": "branches", "tag": "tags", "push": "every push"}
_RESULTS = {"pass": "Passed", "fail": "Blocked", "bypass": "Bypassed"}


def _ruleset(raw: Mapping[str, Any]) -> str:
    enforced = _ENFORCED.get(str(raw.get("enforcement")), str(raw.get("enforcement") or ""))
    target = _TARGETS.get(str(raw.get("target") or "branch"), str(raw.get("target")))
    source = str(raw.get("source_type") or "")
    inherited = (
        f", from the organization {raw.get('source')}"
        if source == "Organization" and "/" not in str(raw.get("source") or "")
        else ""
    )
    return f"{raw.get('name')}: {enforced}, on {target}{inherited}."


def _judged(raw: Mapping[str, Any]) -> str:
    result = _RESULTS.get(str(raw.get("result")), "Judged")
    ref = str(raw.get("ref") or "").removeprefix("refs/heads/").removeprefix("refs/tags/")
    when = str(raw.get("pushed_at") or "")[:10]
    return (
        f"{result}: {raw.get('actor_name') or 'someone'} pushed to "
        f"{raw.get('repository_name') or 'a repository'} {ref}"
        + (f", {when}" if when else "")
        + "."
    )


ADMIN_SPECS: tuple[ResourceSpec, ...] = (
    ResourceSpec(
        key="repo_rulesets",
        label="Rulesets",
        scope="repository",
        parent="settings",
        noun="ruleset",
        list_path="{base}/rulesets",
        id_field="id",
        id_param="{ruleset_id}",
        title_field="name",
        sentence=_ruleset,
        help="Rulesets: every ruleset on this repository, its own and the organization's. "
        "Alt+Enter opens one's sheet: its target, every rule and setting, who may bypass it, "
        "and a Summary in plain words. Ctrl+N makes one; Delete removes one after its name "
        "is typed.",
        page="https://github.com/{target}/rules",
        typed_delete=True,
    ),
    ResourceSpec(
        key="org_rulesets",
        label="Rulesets",
        scope="organization",
        parent="organization",
        noun="organization ruleset",
        list_path="{base}/rulesets",
        id_field="id",
        id_param="{ruleset_id}",
        title_field="name",
        sentence=_ruleset,
        help="Rulesets: the organization's rulesets, which apply across its repositories. "
        "Alt+Enter opens one's sheet, with the repositories it covers by name or property; "
        "Delete removes it from every repository after its name is typed.",
        page="https://github.com/organizations/{target}/settings/rules",
        typed_delete=True,
    ),
    ResourceSpec(
        key="org_rule_insights",
        label="Rule Insights",
        scope="organization",
        parent="organization",
        noun="judged push",
        list_path="{base}/rulesets/rule-suites",
        id_field="id",
        sentence=_judged,
        help="Rule Insights: recent pushes the organization's rulesets passed, blocked or "
        "let through, in every repository.",
        page="https://github.com/organizations/{target}/settings/rules/insights",
        delete=False,
    ),
    ResourceSpec(
        key="access_people",
        label="Access Review: People",
        scope="organization",
        parent="organization",
        noun="person's access",
        list_path="{base}/members",
        id_field="login",
        sentence=lambda raw: str(raw.get("login") or ""),
        help="Access Review: People: every person and repository pair, a row each, with the "
        "effective role and where it comes from: being an owner, the base permission, a team "
        "or direct access, and the others after 'also'. Filter it by a name, a role or a "
        "team; File, Export List saves it.",
        page="https://github.com/orgs/{target}/people",
        delete=False,
        reader=people_rows,
    ),
    ResourceSpec(
        key="access_teams",
        label="Access Review: Teams",
        scope="organization",
        parent="organization",
        noun="team's access",
        list_path="{base}/teams",
        id_field="slug",
        sentence=lambda raw: str(raw.get("name") or ""),
        help="Access Review: Teams: every team and repository pair, a row each, with the "
        "team's role there and how many people it reaches. File, Export List saves it.",
        page="https://github.com/orgs/{target}/teams",
        delete=False,
        reader=team_rows,
    ),
)
