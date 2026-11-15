"""By name, across repositories: labels, milestones, topics and rules (PRD 22.11).

GitHub keeps a label or a milestone inside one repository, but people think
of them by name across many. :func:`survey` reads one kind from every
repository in a Repository Set and gathers the copies by name; each
:class:`ByNameRow` then says where the copies differ (:meth:`ByNameRow.variants`)
and which repositories that answered lack it (``missing``). A repository that
could not be read is listed apart (``unread``), never counted as missing.

Changing them -- the plan with its preview, and the run with a result per
repository -- is :mod:`quill.core.github.across_changes`.

Labels and milestones change through :mod:`quill.core.github.across_changes`;
topics, rulesets and branch protection through
:mod:`quill.core.github.across_admin_changes`. Every request goes through the Workbench's one
:class:`~quill.core.github.workbench_api.GitHubApi`; tests pass a fake.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from quill.core.github.across import why_failed

__all__ = [
    "KINDS",
    "PROTECTION_PREFIX",
    "WRITABLE_KINDS",
    "ByNameRow",
    "Copy",
    "Survey",
    "describe_props",
    "find_uses_query",
    "protection_props",
    "ruleset_props",
    "survey",
]

#: (kind, the words for one of it, the properties whose differences are variants).
KINDS: dict[str, tuple[str, tuple[str, ...]]] = {
    "labels": ("label", ("color", "description")),
    "milestones": ("milestone", ("due_on", "description", "state")),
    "topics": ("topic", ()),
    "rules": ("rule set", ("enforcement", "target", "rules")),
}
WRITABLE_KINDS = frozenset({"labels", "milestones", "topics", "rules"})
_WORKERS = 6


def seg(text: str) -> str:
    """One path segment: a label called "area/ui" must not become two."""
    return quote(text, safe="")


@dataclass(frozen=True, slots=True)
class Copy:
    """One repository's copy of a named thing."""

    repository: str
    name: str
    props: tuple[tuple[str, str], ...] = ()
    #: What the API addresses it by: a label's name, a milestone's number.
    ident: str = ""
    #: Counts and the like that are not variants (a milestone's open and closed items).
    extra: tuple[tuple[str, str], ...] = ()

    def prop(self, name: str) -> str:
        return dict(self.props).get(name, "")


@dataclass(frozen=True, slots=True)
class ByNameRow:
    kind: str
    name: str
    copies: tuple[Copy, ...] = ()
    missing: tuple[str, ...] = ()
    unread: tuple[tuple[str, str], ...] = ()

    def variants(self) -> list[tuple[tuple[tuple[str, str], ...], list[str]]]:
        """Each distinct set of properties and the repositories that have it, commonest first."""
        found: dict[tuple[tuple[str, str], ...], list[str]] = {}
        for copy in self.copies:
            found.setdefault(copy.props, []).append(copy.repository)
        return sorted(found.items(), key=lambda pair: (-len(pair[1]), pair[0]))

    def differs(self) -> list[str]:
        """The properties whose values are not the same everywhere."""
        names = list(dict.fromkeys(k for c in self.copies for k, _v in c.props))
        return [n for n in names if len({c.prop(n) for c in self.copies}) > 1]

    def sentence(self) -> str:
        total = len(self.copies) + len(self.missing)
        parts = [f"{self.name}: in {len(self.copies)} of {total} repositories"]
        for prop in self.differs():
            count = len({c.prop(prop) for c in self.copies})
            parts.append(f"{count} {_PROP_WORDS.get(prop, prop)}")
        if not self.differs() and len(self.copies) > 1 and self.copies[0].props:
            parts.append("the same everywhere")
        if self.kind == "milestones":
            opened = sum(int(dict(c.extra).get("open", "0")) for c in self.copies)
            closed = sum(int(dict(c.extra).get("closed", "0")) for c in self.copies)
            parts.append(f"{closed} of {opened + closed} items closed")
        if self.missing:
            parts.append(f"missing from {len(self.missing)}")
        if self.unread:
            parts.append(f"{len(self.unread)} could not be read")
        return ", ".join(parts)

    def detail(self) -> str:
        noun = KINDS[self.kind][0]
        lines = [self.sentence() + ".", ""]
        if KINDS[self.kind][1]:
            lines.append("Variants:")
            for number, (props, repos) in enumerate(self.variants(), start=1):
                lines.append(f"Variant {number}, {describe_props(props)}: {', '.join(repos)}")
        else:
            lines.append(f"Has the {noun}: {', '.join(c.repository for c in self.copies)}")
        lines.append("")
        lines.append(
            "Missing From: " + (", ".join(self.missing) if self.missing else "none of them")
        )
        for repo, reason in self.unread:
            lines.append(f"Could not be read, so not counted: {repo}, {reason}")
        return "\n".join(lines)


_PROP_WORDS = {
    "color": "colours",
    "description": "descriptions",
    "due_on": "due dates",
    "state": "states",
    "enforcement": "enforcement settings",
    "target": "targets",
    "rules": "rule lists",
    "protected": "protection states",
    "approvals": "approval counts",
    "checks": "required check lists",
    "admins": "admin settings",
}


def describe_props(props: Sequence[tuple[str, str]]) -> str:
    said = []
    for name, value in props:
        label = {"color": "colour", "due_on": "due"}.get(name, name)
        said.append(f"{label} {value}" if value else f"no {label}")
    return ", ".join(said) or "no properties"


@dataclass(frozen=True, slots=True)
class Survey:
    kind: str
    rows: tuple[ByNameRow, ...]
    #: Repository -> True (may change it), False (may not) or None (not known).
    can_write: Mapping[str, bool | None] = field(default_factory=dict)
    #: Repositories that could not be read, and why.
    unread: tuple[tuple[str, str], ...] = ()
    scope: tuple[str, ...] = ()
    read_at: str = ""
    #: Repository -> True when the account administers it (topics, rules), as can_write.
    can_admin: Mapping[str, bool | None] = field(default_factory=dict)

    def row(self, name: str) -> ByNameRow | None:
        key = name.casefold()
        return next((r for r in self.rows if r.name.casefold() == key), None)

    def has(self, repository: str, name: str) -> Copy | None:
        row = self.row(name)
        if row is None:
            return None
        return next((c for c in row.copies if c.repository == repository), None)

    def summary(self) -> str:
        noun = KINDS[self.kind][0]
        read = len(self.scope) - len(self.unread)
        said = f"{len(self.rows)} {noun} names from {read} of {len(self.scope)} repositories"
        if self.unread:
            said += f"; {len(self.unread)} could not be read: " + "; ".join(
                f"{repo}, {reason}" for repo, reason in self.unread
            )
        return said + (f". Read at {self.read_at}." if self.read_at else ".")


# -- reading ---------------------------------------------------------------------


def _list(api: Any, path: str, query: Mapping[str, str] | None = None) -> list[Any]:
    answer = api.rest("GET", path, query=dict(query or {"per_page": "100"}))
    data = answer.data
    return data if isinstance(data, list) else []


def _label_copies(api: Any, repo: str) -> list[Copy]:
    found = []
    for entry in _list(api, f"/repos/{repo}/labels"):
        if isinstance(entry, Mapping) and entry.get("name"):
            name = str(entry["name"])
            props = (
                ("color", str(entry.get("color") or "").lower()),
                ("description", str(entry.get("description") or "")),
            )
            found.append(Copy(repo, name, props, name))
    return found


def _milestone_copies(api: Any, repo: str) -> list[Copy]:
    found = []
    query = {"state": "all", "per_page": "100"}
    for entry in _list(api, f"/repos/{repo}/milestones", query):
        if isinstance(entry, Mapping) and entry.get("title"):
            props = (
                ("due_on", str(entry.get("due_on") or "")[:10]),
                ("description", str(entry.get("description") or "")),
                ("state", str(entry.get("state") or "")),
            )
            extra = (
                ("open", str(entry.get("open_issues") or 0)),
                ("closed", str(entry.get("closed_issues") or 0)),
            )
            found.append(Copy(repo, str(entry["title"]), props, str(entry.get("number")), extra))
    return found


def _topic_copies(api: Any, repo: str) -> list[Copy]:
    answer = api.rest("GET", f"/repos/{repo}/topics")
    names = answer.data.get("names") if isinstance(answer.data, Mapping) else None
    return [Copy(repo, str(n), (), str(n)) for n in names or [] if n]


def _rule_copies(api: Any, repo: str, default_branch: str) -> list[Copy]:
    found = []
    for entry in _list(api, f"/repos/{repo}/rulesets"):
        if isinstance(entry, Mapping) and entry.get("name"):
            props = ruleset_props(entry)
            found.append(Copy(repo, str(entry["name"]), props, str(entry.get("id"))))
    if default_branch:
        name = f"Branch protection on {default_branch}"
        try:
            answer = api.rest("GET", f"/repos/{repo}/branches/{seg(default_branch)}/protection")
        except Exception as exc:  # noqa: BLE001 - unprotected is a 404, which is an answer
            reason = why_failed(exc)
            if "not found" in reason:
                found.append(Copy(repo, name, (("protected", "no"),), default_branch))
            else:
                found.append(Copy(repo, name, (("protected", f"unknown, {reason}"),), ""))
            return found
        data = answer.data if isinstance(answer.data, Mapping) else {}
        found.append(Copy(repo, name, protection_props(data), default_branch))
    return found


PROTECTION_PREFIX = "Branch protection on "


def ruleset_props(entry: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """A ruleset's comparable summary: enforcement, target and its rule types."""
    rules = entry.get("rules")
    kinds = sorted(
        str(r.get("type")) for r in rules or [] if isinstance(r, Mapping) and r.get("type")
    )
    return (
        ("enforcement", str(entry.get("enforcement") or "")),
        ("target", str(entry.get("target") or "")),
        ("rules", ", ".join(kinds) if rules is not None else "not listed"),
    )


def protection_props(data: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """A protected branch's comparable summary, from ``GET .../protection``."""
    reviews = data.get("required_pull_request_reviews")
    count = 0
    if isinstance(reviews, Mapping):
        count = int(reviews.get("required_approving_review_count") or 0)
    checks = data.get("required_status_checks")
    contexts = checks.get("contexts", []) if isinstance(checks, Mapping) else []
    admins = data.get("enforce_admins")
    included = isinstance(admins, Mapping) and bool(admins.get("enabled"))
    return (
        ("protected", "yes"),
        ("approvals", str(count)),
        ("checks", ", ".join(sorted(str(c) for c in contexts)) or "none"),
        ("admins", "included" if included else "exempt"),
    )


def _access(api: Any, repo: str) -> tuple[bool | None, bool | None, str]:
    """(may write, administers, default branch) from ``GET /repos/{repo}``."""
    answer = api.rest("GET", f"/repos/{repo}")
    data = answer.data if isinstance(answer.data, Mapping) else {}
    perms = data.get("permissions")
    can: bool | None = None
    admin: bool | None = None
    if isinstance(perms, Mapping):
        can = bool(perms.get("push") or perms.get("maintain") or perms.get("admin"))
        admin = bool(perms.get("admin"))
    return can, admin, str(data.get("default_branch") or "")


def survey(
    api: Any,
    kind: str,
    repositories: Sequence[str],
    *,
    read_at: str = "",
) -> Survey:
    """Read *kind* from every repository; each answers for itself. Runs off the UI thread."""
    if kind not in KINDS:
        raise ValueError(f"Unknown kind {kind!r}.")
    chosen = list(dict.fromkeys(r for r in (s.strip() for s in repositories) if r))

    admins: dict[str, bool | None] = {}

    def one(repo: str) -> tuple[str, list[Copy], bool | None, str]:
        try:
            can, admins[repo], default_branch = _access(api, repo)
            if kind == "labels":
                copies = _label_copies(api, repo)
            elif kind == "milestones":
                copies = _milestone_copies(api, repo)
            elif kind == "topics":
                copies = _topic_copies(api, repo)
            else:
                copies = _rule_copies(api, repo, default_branch)
        except Exception as exc:  # noqa: BLE001 - one repository never sinks the rest
            return repo, [], None, why_failed(exc)
        return repo, copies, can, ""

    with ThreadPoolExecutor(max_workers=min(_WORKERS, max(1, len(chosen)))) as pool:
        answers = list(pool.map(one, chosen))
    unread = tuple((repo, error) for repo, _c, _w, error in answers if error)
    read = [repo for repo, _c, _w, error in answers if not error]
    by_name: dict[str, list[Copy]] = {}
    for _repo, copies, _can, _error in answers:
        for copy in copies:
            by_name.setdefault(copy.name.casefold(), []).append(copy)
    rows = []
    for _key, copies in sorted(by_name.items()):
        have = {c.repository for c in copies}
        rows.append(
            ByNameRow(
                kind,
                copies[0].name,
                tuple(copies),
                tuple(r for r in read if r not in have),
                unread,
            )
        )
    can_write = {repo: can for repo, _c, can, error in answers if not error}
    return Survey(kind, tuple(rows), can_write, unread, tuple(chosen), read_at, dict(admins))


def find_uses_query(kind: str, name: str, repositories: Sequence[str]) -> str:
    """The issue search that finds every item with a label or in a milestone, in the set."""
    qualifier = {"labels": "label", "milestones": "milestone"}.get(kind, "")
    if not qualifier:
        return ""
    repos = " ".join(f"repo:{r}" for r in repositories)
    return f'{qualifier}:"{name}" {repos}'.strip()
