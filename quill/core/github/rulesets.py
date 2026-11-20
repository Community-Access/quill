"""Rulesets and branch protection, every rule, read as sentences (GitHub PRD 18.3.1, GH-R-064).

These hold the most combinations GitHub offers, so the sheet is laid out for
them: Target, Bypass, Rules, and a **Summary** page that writes the whole set
in plain words, the page people read first:

    On the default branch: changes need a pull request with 2 approvals
    including a code owner; checks build and test must pass; force pushes are
    blocked; maintainers may bypass.

:data:`RULES` is every rule type GitHub's rulesets API has, with its words.
:func:`summary` reads a ruleset (or classic branch protection, through
:func:`classic_as_rules`); :func:`ruleset_body` applies the sheet's edits to
the ruleset GitHub sent and returns the whole body to PUT back, because
GitHub replaces a ruleset whole.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

__all__ = [
    "BYPASS_ROLES",
    "MERGE_METHODS",
    "RULES",
    "bypass_roles",
    "bypass_words",
    "classic_as_rules",
    "classic_body",
    "repository_words",
    "rule_details",
    "rule_words",
    "ruleset_body",
    "ruleset_values",
    "summary",
    "target_words",
]

#: Every rule type, in GitHub's order, with the words a check box and the summary use.
RULES: tuple[tuple[str, str], ...] = (
    ("creation", "restrict creation"),
    ("update", "restrict updates"),
    ("deletion", "restrict deletion"),
    ("required_linear_history", "require linear history"),
    ("required_deployments", "require deployments to succeed"),
    ("required_signatures", "require signed commits"),
    ("pull_request", "require a pull request"),
    ("required_status_checks", "require status checks"),
    ("non_fast_forward", "block force pushes"),
    ("code_scanning", "require code scanning results"),
    ("merge_queue", "require a merge queue"),
    ("commit_message_pattern", "commit message pattern"),
    ("commit_author_email_pattern", "author email pattern"),
    ("committer_email_pattern", "committer email pattern"),
    ("branch_name_pattern", "branch name pattern"),
    ("tag_name_pattern", "tag name pattern"),
    ("file_path_restriction", "restrict file paths"),
    ("file_extension_restriction", "restrict file extensions"),
    ("max_file_size", "restrict file size"),
    ("max_file_path_length", "restrict file path length"),
    ("workflows", "require workflows to pass"),
    ("copilot_code_review", "request a Copilot code review"),
)
_WORDS = dict(RULES)
_TYPES = {words: key for key, words in RULES}
MERGE_METHODS: tuple[str, ...] = ("merge", "squash", "rebase")
_ROLE_IDS = {1: "read", 2: "maintainers", 3: "triage", 4: "writers", 5: "admins"}
#: The bypass actors a check list can name, with GitHub's actor type and id for each.
BYPASS_ROLES: tuple[tuple[str, str, int | None], ...] = (
    ("organization admins", "OrganizationAdmin", 1),
    ("admins", "RepositoryRole", 5),
    ("maintainers", "RepositoryRole", 2),
    ("writers", "RepositoryRole", 4),
    ("deploy keys", "DeployKey", None),
)


def target_words(conditions: Mapping[str, Any] | None, target: str = "branch") -> str:
    """ "the default branch", "all branches", "main and release/*, except release/old"."""
    ref = (conditions or {}).get("ref_name") or {}
    include = [str(item) for item in ref.get("include") or ()]
    exclude = [str(item) for item in ref.get("exclude") or ()]
    plural = "tags" if target == "tag" else "branches"

    def name(item: str) -> str:
        if item == "~DEFAULT_BRANCH":
            return "the default branch"
        if item == "~ALL":
            return f"all {plural}"
        return item.removeprefix("refs/heads/").removeprefix("refs/tags/")

    said = " and ".join(name(item) for item in include) or f"no {plural} yet"
    if exclude:
        said += ", except " + " and ".join(name(item) for item in exclude)
    return said


def bypass_words(actors: Sequence[Mapping[str, Any]]) -> list[str]:
    """Each bypass actor in words: "maintainers, always"."""
    found: list[str] = []
    for actor in actors:
        kind = str(actor.get("actor_type") or "")
        number = actor.get("actor_id")
        if kind == "RepositoryRole":
            who = _ROLE_IDS.get(int(number or 0), f"role {number}")
        elif kind == "OrganizationAdmin":
            who = "organization admins"
        elif kind == "Team":
            who = f"team {number}"
        elif kind == "Integration":
            who = f"app {number}"
        elif kind == "DeployKey":
            who = "deploy keys"
        else:
            who = kind or "someone"
        mode = "for pull requests only" if actor.get("bypass_mode") == "pull_request" else "always"
        found.append(f"{who}, {mode}")
    return found


def _params(rule: Mapping[str, Any]) -> Mapping[str, Any]:
    found = rule.get("parameters")
    return found if isinstance(found, Mapping) else {}


def rule_words(rule: Mapping[str, Any]) -> str:
    """One rule as a clause of the summary."""
    kind = str(rule.get("type") or "")
    params = _params(rule)
    if kind == "pull_request":
        count = int(params.get("required_approving_review_count") or 0)
        said = "changes need a pull request"
        if count:
            said += f" with {count} approval{'s' if count != 1 else ''}"
        extras = []
        if params.get("require_code_owner_review"):
            extras.append("including a code owner")
        if params.get("dismiss_stale_reviews_on_push"):
            extras.append("new pushes dismiss approvals")
        if params.get("require_last_push_approval"):
            extras.append("the last push must be approved by someone else")
        if params.get("required_review_thread_resolution"):
            extras.append("every conversation resolved")
        methods = params.get("allowed_merge_methods")
        if methods:
            extras.append("merging by " + " or ".join(str(m) for m in methods))
        return said + (" " + ", ".join(extras) if extras else "")
    if kind == "required_status_checks":
        checks = [str(c.get("context")) for c in params.get("required_status_checks") or ()]
        strict = (
            " and the branch must be up to date"
            if params.get("strict_required_status_checks_policy")
            else ""
        )
        named = " and ".join(checks) or "the chosen checks"
        return f"checks {named} must pass{strict}"
    if kind == "non_fast_forward":
        return "force pushes are blocked"
    if kind == "deletion":
        return "the branch cannot be deleted"
    if kind == "required_deployments":
        names = params.get("required_deployment_environments") or []
        return (
            "deployments to "
            + (" and ".join(str(n) for n in names) or "environments")
            + (" must succeed")
        )
    if kind == "merge_queue":
        return f"merges go through a merge queue ({params.get('merge_method', 'merge')})"
    if kind.endswith("_pattern"):
        operator = str(params.get("operator") or "matches")
        return f"{_WORDS.get(kind, kind)} {operator.replace('_', ' ')} {params.get('pattern', '')}"
    if kind == "code_scanning":
        tools = [str(t.get("tool")) for t in params.get("code_scanning_tools") or ()]
        return (
            "code scanning results from "
            + (" and ".join(tools) or "the chosen tools")
            + (" must pass")
        )
    if kind == "max_file_size":
        return f"files may be at most {params.get('max_file_size', '?')} MB"
    if kind == "max_file_path_length":
        return f"file paths may be at most {params.get('max_file_path_length', '?')} characters"
    if kind == "file_path_restriction":
        paths = " and ".join(str(p) for p in params.get("restricted_file_paths") or ())
        return f"pushes may not change {paths or 'the chosen paths'}"
    if kind == "file_extension_restriction":
        kinds = " and ".join(str(p) for p in params.get("restricted_file_extensions") or ())
        return f"pushes may not add {kinds or 'the chosen'} files"
    if kind == "workflows":
        flows = params.get("workflows") or ()
        flow_paths = [str(w.get("path")) for w in flows if isinstance(w, Mapping)]
        return "workflows " + (" and ".join(flow_paths) or "chosen") + " must pass"
    if kind == "update" and params.get("update_allows_fetch_and_merge"):
        return "updates are restricted, except fetch and merge"
    return _WORDS.get(kind, kind.replace("_", " "))


def _said(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, Mapping):
        named = value.get("context") or value.get("tool") or value.get("path") or value.get("name")
        return str(named) if named else ", ".join(f"{k} {_said(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return " and ".join(_said(v) for v in value) or "none"
    return str(value)


def rule_details(ruleset: Mapping[str, Any]) -> tuple[str, ...]:
    """Every rule GitHub sent, each with every setting it carries, one line a rule.

    Rule types QUILL has no words for yet are read the same way, by GitHub's
    own names, so nothing a ruleset holds is hidden from the sheet.
    """
    lines = []
    for rule in ruleset.get("rules") or ():
        if not isinstance(rule, Mapping):
            continue
        kind = str(rule.get("type") or "")
        params = _params(rule)
        settings = "; ".join(f"{k.replace('_', ' ')}: {_said(v)}" for k, v in params.items())
        name = _WORDS.get(kind, kind.replace("_", " "))
        lines.append(f"{name[:1].upper()}{name[1:]}" + (f": {settings}" if settings else ""))
    return tuple(lines)


def bypass_roles(actors: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """The :data:`BYPASS_ROLES` names among *actors* (teams and apps are listed apart)."""
    held = {_role_of(actor) for actor in actors}
    return tuple(name for name, _kind, _number in BYPASS_ROLES if name in held)


def _role_of(actor: Mapping[str, Any]) -> str:
    """The :data:`BYPASS_ROLES` name *actor* is, or "" for a team or an app."""
    for name, kind, number in BYPASS_ROLES:
        if actor.get("actor_type") == kind and (number is None or actor.get("actor_id") == number):
            return name
    return ""


def _bypass_body(actors: Sequence[Mapping[str, Any]], chosen: tuple[str, ...]) -> list[Any]:
    """*actors* with the named roles set to *chosen*; teams and apps are kept as they were."""
    kept: list[Any] = [dict(a) for a in actors if not _role_of(a)]
    before = {_role_of(a): a for a in actors if _role_of(a)}
    for name, kind, number in BYPASS_ROLES:
        if name in chosen:
            mode = str((before.get(name) or {}).get("bypass_mode") or "always")
            kept.append({"actor_type": kind, "actor_id": number, "bypass_mode": mode})
    return kept


def repository_words(conditions: Mapping[str, Any] | None) -> str:
    """Which repositories an organization ruleset covers, or "" for a repository's own."""
    found = conditions or {}
    names = found.get("repository_name")
    if isinstance(names, Mapping):
        include = [str(i) for i in names.get("include") or ()]
        exclude = [str(i) for i in names.get("exclude") or ()]
        said = " and ".join("every repository" if i == "~ALL" else i for i in include)
        said = said or "no repositories yet"
        if exclude:
            said += ", except " + " and ".join(exclude)
        if names.get("protected"):
            said += "; nobody may rename those repositories out of it"
        return said
    props = found.get("repository_property")
    if isinstance(props, Mapping):
        parts = []
        for key, how in (("include", "with"), ("exclude", "without")):
            for prop in props.get(key) or ():
                if isinstance(prop, Mapping):
                    values = " or ".join(str(v) for v in prop.get("property_values") or ())
                    parts.append(f"{how} {prop.get('name')} {values}".rstrip())
        return "repositories " + (" and ".join(parts) or "chosen by property")
    ids = found.get("repository_id")
    if isinstance(ids, Mapping):
        count = len(ids.get("repository_ids") or ())
        return f"{count} chosen repositor{'y' if count == 1 else 'ies'}"
    return ""


def summary(ruleset: Mapping[str, Any]) -> str:
    """The whole ruleset in plain words: the Summary page."""
    conditions = ruleset.get("conditions")
    target = str(ruleset.get("target") or "branch")
    where = "every push" if target == "push" else target_words(conditions, target)
    repos = repository_words(conditions if isinstance(conditions, Mapping) else None)
    if repos:
        where += f" in {repos}"
    rules = [rule_words(r) for r in ruleset.get("rules") or () if isinstance(r, Mapping)]
    said = f"On {where}: " + ("; ".join(rules) if rules else "no rules yet")
    bypass = bypass_words(ruleset.get("bypass_actors") or ())
    if bypass:
        said += "; " + " and ".join(bypass) + " may bypass"
    enforcement = str(ruleset.get("enforcement") or "active")
    if enforcement == "evaluate":
        said += ". Evaluate mode: it reports what it would block, and blocks nothing"
    elif enforcement == "disabled":
        said += ". It is turned off"
    return said + "."


def ruleset_values(ruleset: Mapping[str, Any]) -> dict[str, object]:
    """The Ruleset sheet's values from GitHub's JSON."""
    rules = {str(r.get("type")): r for r in ruleset.get("rules") or () if isinstance(r, Mapping)}
    pr = _params(rules.get("pull_request", {}))
    checks = _params(rules.get("required_status_checks", {}))
    conditions = ruleset.get("conditions") or {}
    ref = conditions.get("ref_name") or {}
    names = conditions.get("repository_name") or {}
    actors = ruleset.get("bypass_actors") or ()
    return {
        "name": str(ruleset.get("name") or ""),
        "enforcement": str(ruleset.get("enforcement") or "active"),
        "target": str(ruleset.get("target") or "branch"),
        "include": tuple(str(i) for i in ref.get("include") or ()),
        "exclude": tuple(str(i) for i in ref.get("exclude") or ()),
        "repo_include": tuple(str(i) for i in names.get("include") or ()),
        "repo_exclude": tuple(str(i) for i in names.get("exclude") or ()),
        "repo_protected": bool(names.get("protected")),
        "repositories": repository_words(conditions) or "This repository only.",
        "bypass": tuple(bypass_words(actors)),
        "bypass_roles": bypass_roles(actors),
        "rule_details": "\n".join(rule_details(ruleset)) or "No rules yet.",
        "rules": tuple(_WORDS.get(kind, kind) for kind in rules),
        "approvals": int(pr.get("required_approving_review_count") or 0),
        "dismiss_stale": bool(pr.get("dismiss_stale_reviews_on_push")),
        "code_owners": bool(pr.get("require_code_owner_review")),
        "last_push": bool(pr.get("require_last_push_approval")),
        "resolve_threads": bool(pr.get("required_review_thread_resolution")),
        "merge_methods": tuple(str(m) for m in pr.get("allowed_merge_methods") or MERGE_METHODS),
        "status_checks": tuple(
            str(c.get("context")) for c in checks.get("required_status_checks") or ()
        ),
        "strict": bool(checks.get("strict_required_status_checks_policy")),
        "summary": summary(ruleset),
        "raw_json": json.dumps(dict(ruleset)),
    }


def ruleset_body(raw: Mapping[str, Any], edits: Mapping[str, object]) -> dict[str, object]:
    """GitHub's ruleset with the sheet's *edits* applied: the whole body to PUT back."""
    body: dict[str, Any] = {
        key: raw[key]
        for key in ("name", "target", "enforcement", "bypass_actors", "conditions", "rules")
        if key in raw
    }
    rules = {str(r.get("type")): dict(r) for r in body.get("rules") or () if isinstance(r, Mapping)}
    if "name" in edits:
        body["name"] = edits["name"]
    if "enforcement" in edits:
        body["enforcement"] = edits["enforcement"]
    if "include" in edits or "exclude" in edits:
        ref = dict((body.get("conditions") or {}).get("ref_name") or {})
        for key in ("include", "exclude"):
            value = edits.get(key)
            if key in edits:
                ref[key] = [str(item) for item in value] if isinstance(value, tuple) else []
        body["conditions"] = {**(body.get("conditions") or {}), "ref_name": ref}
    if any(key in edits for key in ("repo_include", "repo_exclude", "repo_protected")):
        # GitHub takes one way of choosing repositories: changing the names
        # chooses them by name, in place of a property or a list of ids.
        conditions = dict(body.get("conditions") or {})
        names = dict(conditions.get("repository_name") or {})
        for key in ("include", "exclude"):
            value = edits.get(f"repo_{key}")
            if f"repo_{key}" in edits:
                names[key] = [str(item) for item in value] if isinstance(value, tuple) else []
            names.setdefault(key, [])
        if "repo_protected" in edits:
            names["protected"] = bool(edits["repo_protected"])
        conditions.pop("repository_property", None)
        conditions.pop("repository_id", None)
        conditions["repository_name"] = names
        body["conditions"] = conditions
    if "bypass_roles" in edits and isinstance(edits["bypass_roles"], tuple):
        body["bypass_actors"] = _bypass_body(body.get("bypass_actors") or (), edits["bypass_roles"])
    if "rules" in edits and isinstance(edits["rules"], tuple):
        wanted = {_TYPES.get(str(words), str(words)) for words in edits["rules"]}
        rules = {kind: rule for kind, rule in rules.items() if kind in wanted}
        for kind in wanted - set(rules):
            rules[kind] = _default_rule(kind)
    pr_keys = {
        "approvals": "required_approving_review_count",
        "dismiss_stale": "dismiss_stale_reviews_on_push",
        "code_owners": "require_code_owner_review",
        "last_push": "require_last_push_approval",
        "resolve_threads": "required_review_thread_resolution",
        "merge_methods": "allowed_merge_methods",
    }
    if any(key in edits for key in pr_keys):
        rule = rules.setdefault("pull_request", _default_rule("pull_request"))
        params = dict(rule.get("parameters") or {})
        for key, api in pr_keys.items():
            if key in edits:
                value = edits[key]
                params[api] = (
                    list(value)
                    if isinstance(value, tuple)
                    else (int(str(value)) if key == "approvals" else value)
                )
        rule["parameters"] = params
    if "status_checks" in edits or "strict" in edits:
        rule = rules.setdefault("required_status_checks", _default_rule("required_status_checks"))
        params = dict(rule.get("parameters") or {})
        if "status_checks" in edits and isinstance(edits["status_checks"], tuple):
            params["required_status_checks"] = [{"context": c} for c in edits["status_checks"]]
        if "strict" in edits:
            params["strict_required_status_checks_policy"] = bool(edits["strict"])
        rule["parameters"] = params
    body["rules"] = list(rules.values())
    return body


def _default_rule(kind: str) -> dict[str, Any]:
    if kind == "pull_request":
        return {
            "type": kind,
            "parameters": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews_on_push": False,
                "require_code_owner_review": False,
                "require_last_push_approval": False,
                "required_review_thread_resolution": False,
            },
        }
    if kind == "required_status_checks":
        return {
            "type": kind,
            "parameters": {
                "strict_required_status_checks_policy": False,
                "required_status_checks": [],
            },
        }
    return {"type": kind}


def classic_as_rules(protection: Mapping[str, Any], branch: str) -> dict[str, Any]:
    """Classic branch protection, as a ruleset, so one summary reads both."""
    rules: list[dict[str, Any]] = []
    reviews = protection.get("required_pull_request_reviews")
    if isinstance(reviews, Mapping):
        rules.append({
            "type": "pull_request",
            "parameters": {
                "required_approving_review_count": reviews.get(
                    "required_approving_review_count", 0
                ),
                "dismiss_stale_reviews_on_push": reviews.get("dismiss_stale_reviews", False),
                "require_code_owner_review": reviews.get("require_code_owner_reviews", False),
                "require_last_push_approval": reviews.get("require_last_push_approval", False),
            },
        })
    checks = protection.get("required_status_checks")
    if isinstance(checks, Mapping):
        rules.append({
            "type": "required_status_checks",
            "parameters": {
                "strict_required_status_checks_policy": checks.get("strict", False),
                "required_status_checks": [{"context": c} for c in checks.get("contexts") or ()],
            },
        })
    if not _enabled(protection, "allow_force_pushes"):
        rules.append({"type": "non_fast_forward"})
    if not _enabled(protection, "allow_deletions"):
        rules.append({"type": "deletion"})
    if _enabled(protection, "required_linear_history"):
        rules.append({"type": "required_linear_history"})
    if _enabled(protection, "required_signatures"):
        rules.append({"type": "required_signatures"})
    admins = _enabled(protection, "enforce_admins")
    return {
        "target": "branch",
        "conditions": {"ref_name": {"include": [branch], "exclude": []}},
        "rules": rules,
        "bypass_actors": []
        if admins
        else [{"actor_type": "RepositoryRole", "actor_id": 5, "bypass_mode": "always"}],
        "enforcement": "active",
    }


def _enabled(protection: Mapping[str, Any], key: str) -> bool:
    found = protection.get(key)
    if isinstance(found, Mapping):
        return bool(found.get("enabled"))
    return bool(found)


def classic_body(protection: Mapping[str, Any], edits: Mapping[str, object]) -> dict[str, object]:
    """Classic protection's whole PUT body (:func:`quill.core.github.branch_protection.body`)."""
    from quill.core.github.branch_protection import body

    return body(protection, edits)
