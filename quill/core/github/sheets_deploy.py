"""Sheets for environments, deployments, runners, secrets and variables (Appendix C).

An environment's protection (wait timer, self-review, admin bypass, which
branches may deploy) is saved whole, as GitHub wants. A secret's value is
write-only (decision 12): it is never read and never shown; the sheet sends it
sealed with the repository's public key (libsodium's sealed box, as GitHub
requires), the re-read cannot prove it so the sheet says "set", and Change
History records that it was set, never what to.

wx-free and strict-typed.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import dig, ed, lst, obj, page, patch, ro, when
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["DEPLOYMENT", "ENVIRONMENT", "RUNNER", "SECRET", "VARIABLE", "seal_secret"]

_O, _V, _A, _D = (
    WriteTier.ORGANIZING,
    WriteTier.VISIBLE,
    WriteTier.ACCESS,
    WriteTier.DESTRUCTIVE,
)
_K = FieldKind
_ACT = "/repos/{repo}/actions"


def _rows(key: str, render: Any) -> Any:
    def extract(data: Mapping[str, Any]) -> dict[str, Value]:
        return {key: tuple(render(row) for row in lst(data, key) if isinstance(row, Mapping))}

    return extract


# -- environments and deployments -------------------------------------------------


def _environment(data: Mapping[str, Any]) -> dict[str, Value]:
    found: dict[str, Value] = {
        "name": str(data.get("name") or ""),
        "admins_bypass": bool(data.get("can_admins_bypass", True)),
        "wait_timer": 0,
        "prevent_self_review": False,
        "reviewers": (),
        "raw_json": json.dumps(dict(data)),
        "url": str(data.get("html_url") or ""),
    }
    for rule in lst(data, "protection_rules"):
        if not isinstance(rule, Mapping):
            continue
        if rule.get("type") == "wait_timer":
            found["wait_timer"] = int(rule.get("wait_timer") or 0)
        if rule.get("type") == "required_reviewers":
            found["prevent_self_review"] = bool(rule.get("prevent_self_review"))
            found["reviewers"] = tuple(
                f"{dig(r, 'reviewer', 'login') or dig(r, 'reviewer', 'slug') or ''}, "
                f"{str(r.get('type') or '').lower()}"
                for r in lst(rule, "reviewers")
                if isinstance(r, Mapping)
            )
    policy = obj(data, "deployment_branch_policy")
    if not policy:
        found["branches"] = "all branches"
    elif policy.get("protected_branches"):
        found["branches"] = "protected branches"
    else:
        found["branches"] = "selected branches and tags"
    return found


def _compose_environment(
    ident: Ident, edits: Mapping[str, Value]
) -> list[tuple[str, str, dict[str, object]]]:
    raw = json.loads(ident.get("raw_json") or "{}")
    current = _environment(raw)
    merged = {**current, **edits}
    reviewers = []
    for rule in raw.get("protection_rules") or ():
        if isinstance(rule, Mapping) and rule.get("type") == "required_reviewers":
            for r in rule.get("reviewers") or ():
                reviewer = r.get("reviewer") or {}
                reviewers.append({"type": r.get("type"), "id": reviewer.get("id")})
    branches = str(merged.get("branches") or "all branches")
    policy: object = None
    if branches == "protected branches":
        policy = {"protected_branches": True, "custom_branch_policies": False}
    elif branches != "all branches":
        policy = {"protected_branches": False, "custom_branch_policies": True}
    body: dict[str, object] = {
        "wait_timer": int(str(merged.get("wait_timer") or 0)),
        "prevent_self_review": bool(merged.get("prevent_self_review")),
        "reviewers": reviewers or None,
        "deployment_branch_policy": policy,
        "can_admins_bypass": bool(merged.get("admins_bypass")),
    }
    return [("PUT", f"/repos/{ident['repo']}/environments/{ident['name']}", body)]


_ENV_FIELDS = ("wait_timer", "prevent_self_review", "admins_bypass", "branches")

ENVIRONMENT = SheetDef(
    "environment",
    SheetSpec(
        "environment",
        "Environment",
        (
            page("general", "General", ro("name", "Name"), ro("url", "Address", _K.LINK)),
            page(
                "protection",
                "Protection",
                ro(
                    "reviewers",
                    "Required reviewers",
                    _K.TABLE,
                    "Up to six people or teams who must approve a deployment.",
                ),
                ed("prevent_self_review", "Prevent self-review", _K.CHECK),
                ed("wait_timer", "Wait timer in minutes", _K.NUMBER, "0 to 43200."),
                ed("admins_bypass", "Allow administrators to bypass", _K.CHECK),
            ),
            page(
                "branches",
                "Branches and Tags",
                ed(
                    "branches",
                    "Which may deploy",
                    _K.CHOICE,
                    choices=("all branches", "protected branches", "selected branches and tags"),
                ),
            ),
            page("secrets", "Secrets", ro("secrets", "Secrets", _K.TABLE, "Names only.")),
            page("variables", "Variables", ro("variables", "Variables", _K.TABLE)),
            page(
                "deployments",
                "Deployments",
                ro("deployments_note", "Deployments", help="The Deployments node lists them."),
            ),
        ),
    ),
    (
        Read("/repos/{repo}/environments/{name}", _environment),
        Read(
            "/repos/{repo}/environments/{name}/secrets",
            _rows("secrets", lambda r: str(r.get("name", ""))),
            optional=True,
        ),
        Read(
            "/repos/{repo}/environments/{name}/variables",
            _rows("variables", lambda r: f"{r.get('name', '')} = {r.get('value', '')}"),
            optional=True,
        ),
    ),
    {
        key: Write("/repos/{repo}/environments/{name}", "repo:admin", _A, "PUT", "put")
        for key in _ENV_FIELDS
    },
    title=lambda ident: f"Environment {ident['name']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/settings/environments",
    compose=_compose_environment,
    adopt=("raw_json",),
)


def _deployment(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "environment": str(data.get("environment") or ""),
        "ref": str(data.get("ref") or ""),
        "sha": str(data.get("sha") or ""),
        "creator": str(dig(data, "creator", "login") or ""),
        "created": when(data.get("created_at")),
        "description": str(data.get("description") or ""),
    }


DEPLOYMENT = SheetDef(
    "deployment",
    SheetSpec(
        "deployment",
        "Deployment",
        (
            page(
                "general",
                "General",
                ro("environment", "Environment"),
                ro("ref", "Ref"),
                ro("sha", "Commit"),
                ro("creator", "Created by"),
                ro("created", "Created", _K.DATE),
                ro("description", "Description"),
            ),
            page("statuses", "Statuses", ro("statuses", "Statuses", _K.TABLE)),
        ),
    ),
    (
        Read("/repos/{repo}/deployments/{id}", _deployment),
        Read(
            "/repos/{repo}/deployments/{id}/statuses",
            lambda d: {
                "statuses": tuple(
                    f"{s.get('state', '')}, {when(s.get('created_at'))}"
                    for s in lst(d, "items")
                    if isinstance(s, Mapping)
                )
            },
            optional=True,
        ),
    ),
    title=lambda ident: f"Deployment {ident['id']}",
)


def _runner(data: Mapping[str, Any]) -> dict[str, Value]:
    labels = [row for row in lst(data, "labels") if isinstance(row, Mapping)]
    return {
        "name": str(data.get("name") or ""),
        "os": str(data.get("os") or ""),
        "status": str(data.get("status") or ""),
        "busy": bool(data.get("busy")),
        "labels": tuple(str(r.get("name")) for r in labels if r.get("type") == "custom"),
        "builtin_labels": tuple(str(r.get("name")) for r in labels if r.get("type") != "custom"),
    }


RUNNER = SheetDef(
    "runner",
    SheetSpec(
        "runner",
        "Runner",
        (
            page(
                "general",
                "General",
                ro("name", "Name"),
                ro("os", "Operating system"),
                ro("status", "Status"),
                ro("busy", "Busy", _K.CHECK),
            ),
            page(
                "labels",
                "Labels",
                ed("labels", "Custom labels", _K.LIST, "Comma-separated."),
                ro("builtin_labels", "Built-in labels", _K.LIST),
            ),
        ),
    ),
    (Read(_ACT + "/runners/{id}", _runner),),
    {"labels": Write(_ACT + "/runners/{id}/labels", "repo:admin", _A, "PUT", "put", "labels")},
    title=lambda ident: f"Runner {ident.get('name') or ident['id']}",
)


# -- secrets and variables ------------------------------------------------------------


def seal_secret(public_key: str, value: str) -> str:
    """*value* sealed for GitHub with the repository's public key, base64 (decision 12)."""
    from nacl import encoding, public

    key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder)
    sealed = public.SealedBox(key).encrypt(value.encode("utf-8"))
    return base64.b64encode(sealed).decode("ascii")


def _secret(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "name": str(data.get("name") or ""),
        "created": when(data.get("created_at")),
        "updated": str(data.get("updated_at") or ""),
        "secret_value": "",
    }


def _public_key(data: Mapping[str, Any]) -> dict[str, Value]:
    return {"key_id": str(data.get("key_id") or ""), "public_key": str(data.get("key") or "")}


def _seal(value: Value, _choices: Mapping[str, object], ident: Ident) -> dict[str, object]:
    return {
        "encrypted_value": seal_secret(ident.get("public_key", ""), str(value or "")),
        "key_id": ident.get("key_id", ""),
    }


SECRET = SheetDef(
    "secret",
    SheetSpec(
        "secret",
        "Secret",
        (
            page(
                "general",
                "General",
                ro("name", "Name"),
                ro("created", "Created", _K.DATE),
                ed(
                    "secret_value",
                    "New value",
                    help="Write-only: GitHub never shows a secret's value, and neither "
                    "does QUILL. Type a new one to replace it; leave it empty to keep it.",
                ),
            ),
        ),
    ),
    (
        Read(_ACT + "/secrets/{name}", _secret),
        Read(_ACT + "/secrets/public-key", _public_key),
    ),
    {
        "secret_value": Write(
            _ACT + "/secrets/{name}", "repo:admin", _A, "PUT", "put", encode=_seal, undo=False
        )
    },
    title=lambda ident: f"Secret {ident['name']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/settings/secrets/actions",
    adopt=("key_id", "public_key"),
    secret_fields=("secret_value",),
)


def _variable(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "name": str(data.get("name") or ""),
        "value": str(data.get("value") or ""),
        "updated": when(data.get("updated_at")),
    }


VARIABLE = SheetDef(
    "variable",
    SheetSpec(
        "variable",
        "Variable",
        (
            page(
                "general",
                "General",
                ro("name", "Name"),
                ed("value", "Value", _K.MULTILINE),
                ro("updated", "Updated", _K.DATE),
            ),
        ),
    ),
    (Read(_ACT + "/variables/{name}", _variable),),
    {"value": patch(_ACT + "/variables/{name}", "repo:admin", _A)},
    title=lambda ident: f"Variable {ident['name']}",
)
