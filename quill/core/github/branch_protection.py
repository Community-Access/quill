"""Classic branch protection, read and written whole (GitHub PRD 18.3.1, GH-R-064).

GitHub replaces a branch's protection whole on a PUT, so a save that sent
only the settings on the sheet would quietly drop everything else: who may
push, who may dismiss reviews, who may skip the pull request. :func:`values`
reads every setting GitHub returns; :func:`body` writes back exactly what was
there, with the sheet's edits applied, and :func:`requests` adds the one
setting GitHub keeps on its own endpoint (signed commits).

wx-free and strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

__all__ = ["FLAGS", "body", "requests", "values", "who_words"]

#: The on-or-off settings: the sheet's key, GitHub's key, and the words.
FLAGS: tuple[tuple[str, str, str], ...] = (
    ("enforce_admins", "enforce_admins", "Include administrators"),
    ("linear_history", "required_linear_history", "Require linear history"),
    ("allow_force_pushes", "allow_force_pushes", "Allow force pushes"),
    ("allow_deletions", "allow_deletions", "Allow deletion"),
    ("resolve_threads", "required_conversation_resolution", "Require conversations resolved"),
    ("block_creations", "block_creations", "Block creating matching branches"),
    ("lock_branch", "lock_branch", "Lock the branch (read-only)"),
    ("allow_fork_syncing", "allow_fork_syncing", "Let forks sync a locked branch"),
)
#: Pull request settings: the sheet's key and GitHub's key.
_REVIEWS = (
    ("dismiss_stale", "dismiss_stale_reviews"),
    ("code_owners", "require_code_owner_reviews"),
    ("last_push", "require_last_push_approval"),
)


def _on(data: Mapping[str, Any], key: str) -> bool:
    found = data.get(key)
    return bool(found.get("enabled")) if isinstance(found, Mapping) else bool(found)


def _names(group: object) -> dict[str, list[str]]:
    """GitHub's {users: [{login}], teams: [{slug}], apps: [{slug}]} as names, for a PUT."""
    found: dict[str, list[str]] = {"users": [], "teams": [], "apps": []}
    if isinstance(group, Mapping):
        for kind, key in (("users", "login"), ("teams", "slug"), ("apps", "slug")):
            items = group.get(kind) or ()
            found[kind] = [str(item.get(key) or "") for item in items if isinstance(item, Mapping)]
    return found


def who_words(group: object, nobody: str) -> str:
    """ "people kelly; teams docs; apps dependabot", or *nobody*."""
    names = _names(group)
    parts = [f"{kind} {', '.join(found)}" for kind, found in names.items() if found]
    return "; ".join(parts) if parts else nobody


def values(data: Mapping[str, Any]) -> dict[str, object]:
    """Every setting of a branch's protection, as the sheet shows it."""
    reviews = data.get("required_pull_request_reviews")
    checks = data.get("required_status_checks")
    pr: Mapping[str, Any] = reviews if isinstance(reviews, Mapping) else {}
    found: dict[str, object] = {
        "approvals": int(pr.get("required_approving_review_count") or 0),
        "require_pr": isinstance(reviews, Mapping),
        "status_checks": tuple(str(c) for c in (checks or {}).get("contexts") or ())
        if isinstance(checks, Mapping)
        else (),
        "strict": bool(checks.get("strict")) if isinstance(checks, Mapping) else False,
        "signatures": _on(data, "required_signatures"),
        "push_restrictions": who_words(data.get("restrictions"), "Anyone with write access."),
        "dismissers": who_words(pr.get("dismissal_restrictions"), "Anyone who may approve."),
        "pr_bypass": who_words(pr.get("bypass_pull_request_allowances"), "Nobody."),
        "raw_json": json.dumps(dict(data)),
    }
    for key, api in _REVIEWS:
        found[key] = bool(pr.get(api))
    for key, api, _words in FLAGS:
        found[key] = _on(data, api)
    return found


def body(protection: Mapping[str, Any], edits: Mapping[str, object]) -> dict[str, object]:
    """The whole PUT body: what GitHub sent, every list of names kept, the edits applied."""
    reviews = protection.get("required_pull_request_reviews")
    checks = protection.get("required_status_checks")
    restrictions = protection.get("restrictions")
    pr: dict[str, Any] | None = None
    if isinstance(reviews, Mapping):
        pr = {
            "required_approving_review_count": reviews.get("required_approving_review_count", 1),
            "dismissal_restrictions": _names(reviews.get("dismissal_restrictions")),
            "bypass_pull_request_allowances": _names(reviews.get("bypass_pull_request_allowances")),
        }
        for _key, api in _REVIEWS:
            pr[api] = bool(reviews.get(api))
    found: dict[str, Any] = {
        "required_status_checks": (
            {"strict": bool(checks.get("strict")), "contexts": list(checks.get("contexts") or ())}
            if isinstance(checks, Mapping)
            else None
        ),
        "required_pull_request_reviews": pr,
        "restrictions": _names(restrictions) if isinstance(restrictions, Mapping) else None,
    }
    for key, api, _words in FLAGS:
        found[api] = bool(edits[key]) if key in edits else _on(protection, api)
    if "approvals" in edits:
        count = int(str(edits["approvals"] or 0))
        found["required_pull_request_reviews"] = (
            {**(pr or {}), "required_approving_review_count": count} if count else None
        )
    if found["required_pull_request_reviews"] is not None:
        for key, api in _REVIEWS:
            if key in edits:
                found["required_pull_request_reviews"][api] = bool(edits[key])
    elif any(key in edits for key, _api in _REVIEWS):
        found["required_pull_request_reviews"] = {
            "required_approving_review_count": 1,
            **{api: bool(edits.get(key, False)) for key, api in _REVIEWS},
        }
    if "status_checks" in edits and isinstance(edits["status_checks"], tuple):
        contexts = list(edits["status_checks"])
        strict = bool(edits.get("strict", (checks or {}).get("strict", False)))
        found["required_status_checks"] = (
            {"strict": strict, "contexts": contexts} if contexts else None
        )
    elif "strict" in edits and found["required_status_checks"] is not None:
        found["required_status_checks"]["strict"] = bool(edits["strict"])
    return found


def requests(
    repo: str, branch: str, protection: Mapping[str, Any], edits: Mapping[str, object]
) -> list[tuple[str, str, dict[str, object]]]:
    """The PUT of the whole protection, and signed commits on their own endpoint."""
    path = f"/repos/{repo}/branches/{branch}/protection"
    whole = {key: value for key, value in edits.items() if key != "signatures"}
    found: list[tuple[str, str, dict[str, object]]] = []
    if whole or "signatures" not in edits:
        found.append(("PUT", path, body(protection, whole)))
    if "signatures" in edits:
        method = "POST" if edits["signatures"] else "DELETE"
        found.append((method, f"{path}/required_signatures", {}))
    return found
