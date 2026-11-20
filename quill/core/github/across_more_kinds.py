"""Reading tags, branches, environments, secrets, variables, webhooks, keys and autolinks by name.

The rest of PRD 22.11's by-name table. :func:`read_copies` reads one kind from
one repository as :class:`~quill.core.github.across_by_name.Copy` rows, which
:func:`quill.core.github.across_by_name.survey` gathers by name like labels:

- **Tags** by name, each with the commit it points at ("v3.2.0: in 4 of 4
  repositories, 4 different commits"). GitHub lists the newest 100 here.
- **Branches** by name, with whether each is the default and protected, and
  how many open pull requests are based on it (what a rename retargets).
- **Environments** by name: wait timer, required reviewers, whether a person
  may approve their own deployment, and which branches may deploy.
- **Secrets** by name only: GitHub never shows a secret's value, to anyone.
- **Variables** by name, with their values.
- **Webhooks** by address: events, on or off, and content type. The secret
  is never readable, so it is never compared.
- **Deploy keys** by title, with the key's fingerprint and its access.
- **Autolinks** by prefix: the address and whether references are numbers.

Changing them is :mod:`quill.core.github.across_more_changes`. Most of these
need admin access to read; a repository that refuses is listed as could not
be read, never as missing.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.across_by_name import Copy

__all__ = ["environment_props", "hook_props", "read_copies", "variable_value"]


def _get(api: Any, path: str, query: Mapping[str, str] | None = None) -> Any:
    return api.rest("GET", path, query=dict(query or {"per_page": "100"})).data


def _entries(data: Any, key: str = "") -> list[Mapping[str, Any]]:
    if key and isinstance(data, Mapping):
        data = data.get(key)
    return [e for e in data or [] if isinstance(e, Mapping)] if isinstance(data, list) else []


def _tags(api: Any, repo: str) -> list[Copy]:
    found = []
    for entry in _entries(_get(api, f"/repos/{repo}/tags")):
        commit = entry.get("commit")
        sha = str(commit.get("sha") or "") if isinstance(commit, Mapping) else ""
        name = str(entry.get("name") or "")
        if name:
            found.append(Copy(repo, name, (("commit", sha[:7]),), name, (("sha", sha),)))
    return found


def _branches(api: Any, repo: str, default_branch: str) -> list[Copy]:
    based: dict[str, int] = {}
    for pull in _entries(_get(api, f"/repos/{repo}/pulls", {"state": "open", "per_page": "100"})):
        base = pull.get("base")
        ref = str(base.get("ref") or "") if isinstance(base, Mapping) else ""
        based[ref] = based.get(ref, 0) + 1
    found = []
    for entry in _entries(_get(api, f"/repos/{repo}/branches")):
        name = str(entry.get("name") or "")
        if not name:
            continue
        props = (
            ("default", "yes" if name == default_branch else "no"),
            ("protected", "yes" if entry.get("protected") else "no"),
        )
        found.append(Copy(repo, name, props, name, (("open_prs", str(based.get(name, 0))),)))
    return found


def environment_props(
    entry: Mapping[str, Any],
) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    """(compared properties, hidden extras) for one environment from GitHub's answer."""
    wait, self_review, people, ids = 0, False, [], []
    for rule in _entries(entry.get("protection_rules") or []):
        if rule.get("type") == "wait_timer":
            wait = int(rule.get("wait_timer") or 0)
        if rule.get("type") == "required_reviewers":
            self_review = bool(rule.get("prevent_self_review"))
            for one in _entries(rule.get("reviewers") or []):
                who = one.get("reviewer")
                who = who if isinstance(who, Mapping) else {}
                kind = str(one.get("type") or "User")
                people.append(f"{kind} {who.get('login') or who.get('slug') or who.get('id')}")
                ids.append(f"{kind}:{who.get('id')}")
    policy = entry.get("deployment_branch_policy")
    if not isinstance(policy, Mapping):
        branches = "all"
    elif policy.get("custom_branch_policies"):
        branches = "custom"
    else:
        branches = "protected"
    props = (
        ("wait_timer", f"{wait} minutes"),
        ("reviewers", ", ".join(sorted(people)) or "none"),
        ("self_review", "prevented" if self_review else "allowed"),
        ("branches", branches),
    )
    return props, (("reviewer_ids", ";".join(ids)),)


def _environments(api: Any, repo: str) -> list[Copy]:
    found = []
    for entry in _entries(_get(api, f"/repos/{repo}/environments"), "environments"):
        name = str(entry.get("name") or "")
        if name:
            props, extra = environment_props(entry)
            found.append(Copy(repo, name, props, name, extra))
    return found


def _secrets(api: Any, repo: str) -> list[Copy]:
    found = []
    for entry in _entries(_get(api, f"/repos/{repo}/actions/secrets"), "secrets"):
        name = str(entry.get("name") or "")
        if name:
            changed = (("updated", str(entry.get("updated_at") or "")[:10]),)
            found.append(Copy(repo, name, (), name, changed))
    return found


def variable_value(entry: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    return (("value", str(entry.get("value") or "")),)


def _variables(api: Any, repo: str) -> list[Copy]:
    found = []
    for entry in _entries(_get(api, f"/repos/{repo}/actions/variables"), "variables"):
        name = str(entry.get("name") or "")
        if name:
            found.append(Copy(repo, name, variable_value(entry), name))
    return found


def hook_props(entry: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """A webhook's comparable summary; its secret is never readable, so never compared."""
    config = entry.get("config")
    config = config if isinstance(config, Mapping) else {}
    events = sorted(str(e) for e in entry.get("events") or [])
    return (
        ("events", ", ".join(events) or "none"),
        ("active", "on" if entry.get("active") else "off"),
        ("content_type", str(config.get("content_type") or "form")),
    )


def _webhooks(api: Any, repo: str) -> list[Copy]:
    found = []
    for entry in _entries(_get(api, f"/repos/{repo}/hooks")):
        config = entry.get("config")
        url = str(config.get("url") or "") if isinstance(config, Mapping) else ""
        if url:
            found.append(Copy(repo, url, hook_props(entry), str(entry.get("id") or "")))
    return found


def _deploy_keys(api: Any, repo: str) -> list[Copy]:
    from quill.core.github.account_keys import fingerprint

    found = []
    for entry in _entries(_get(api, f"/repos/{repo}/keys")):
        title = str(entry.get("title") or "")
        if title:
            key = str(entry.get("key") or "")
            props = (
                ("key", fingerprint(key) or key[-16:]),
                ("access", "read only" if entry.get("read_only") else "read and write"),
            )
            found.append(Copy(repo, title, props, str(entry.get("id") or "")))
    return found


def _autolinks(api: Any, repo: str) -> list[Copy]:
    found = []
    for entry in _entries(_get(api, f"/repos/{repo}/autolinks")):
        prefix = str(entry.get("key_prefix") or "")
        if prefix:
            props = (
                ("url_template", str(entry.get("url_template") or "")),
                (
                    "alphanumeric",
                    "letters and numbers" if entry.get("is_alphanumeric") else "numbers",
                ),
            )
            found.append(Copy(repo, prefix, props, str(entry.get("id") or "")))
    return found


def read_copies(api: Any, kind: str, repo: str, default_branch: str) -> list[Copy]:
    """*kind*'s copies in *repo*. Raises on a refusal, which the survey says per repository."""
    if kind == "tags":
        return _tags(api, repo)
    if kind == "branches":
        return _branches(api, repo, default_branch)
    readers = {
        "environments": _environments,
        "secrets": _secrets,
        "variables": _variables,
        "webhooks": _webhooks,
        "deploy_keys": _deploy_keys,
        "autolinks": _autolinks,
    }
    if kind not in readers:
        raise ValueError(f"Unknown kind {kind!r}.")
    return readers[kind](api, repo)
