"""Access templates: named sets of access, applied to a person in one batch (GH-R-068).

A template is what a role in a project means, written once:

    Contributor
      write on Community-Access/quill
      write on Community-Access/quill-docs
      member of Community-Access/docs

Applying it to a person is one previewed batch of the same requests an Access
page's Add... sends (:func:`quill.core.github.access.plan_add`): an
organization membership first, then team memberships, then repository roles,
because a team membership invites someone who is not yet in the
organization. The Workbench's write gate and tier confirmation hold it, and
it reports a result per change, exactly as Bulk Access Changes does.

Each line is one grant, in the words the preview uses:

- ``<role> on <owner/repository>``: read, triage, write, maintain or admin;
- ``member of <org/team>`` or ``maintainer of <org/team>``;
- ``member of <org>`` or ``owner of <org>``.

Templates are per GitHub account, one file per account (the account key
hashed, as :mod:`quill.core.github.repository_sets` does), written
atomically. They hold names and grants only.

wx-free and strict-typed.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.github.access import AccessChange, plan_add
from quill.core.github.permissions import REPO_ROLES
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "MAX_GRANTS",
    "MAX_TEMPLATE_NAME",
    "AccessTemplates",
    "Grant",
    "parse_grants",
    "template_plan",
]

MAX_TEMPLATE_NAME = 80
#: A template is a role in a project, not an organization's whole access list.
MAX_GRANTS = 100
_VERSION = 1
_REPO = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
_ORG = re.compile(r"^[A-Za-z0-9-]+$")
_TEAM = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
#: Where a grant goes in the batch: organization, then teams, then repositories.
_ORDER = {"organization": 0, "team": 1, "repository": 2}


@dataclass(frozen=True)
class Grant:
    """One line of a template: a role in one place."""

    scope: str  # repository, team or organization
    target: str  # owner/name, org/team or org
    role: str

    def text(self) -> str:
        if self.scope == "repository":
            return f"{self.role} on {self.target}"
        return f"{self.role} of {self.target}"

    def ident(self) -> dict[str, str]:
        if self.scope == "repository":
            return {"repo": self.target}
        if self.scope == "team":
            org, team = self.target.split("/", 1)
            return {"org": org, "team": team}
        return {"org": self.target}


def _grant(line: str) -> Grant | None:
    words = line.strip().split()
    if len(words) != 3:
        return None
    role, joint, target = words[0].casefold(), words[1].casefold(), words[2].strip("/")
    if joint == "on" and role in REPO_ROLES and _REPO.match(target):
        return Grant("repository", target, role)
    if joint != "of":
        return None
    if role in ("member", "maintainer") and _TEAM.match(target):
        return Grant("team", target, role)
    if role in ("member", "owner") and _ORG.match(target):
        return Grant("organization", target, role)
    return None


def parse_grants(text: str) -> tuple[list[Grant], list[str]]:
    """The grants in *text* (a line or a semicolon each), and the lines that are not one.

    A grant written twice is kept once; two roles in one place keep the last,
    since a person has one role in a place.
    """
    found: dict[tuple[str, str], Grant] = {}
    rejected: list[str] = []
    for line in text.replace(";", "\n").splitlines():
        if not line.strip():
            continue
        grant = _grant(line)
        if grant is None:
            rejected.append(line.strip())
            continue
        found[(grant.scope, grant.target.casefold())] = grant
    return list(found.values())[:MAX_GRANTS], rejected


def template_plan(grants: Sequence[Grant], who: str) -> list[AccessChange]:
    """The batch that gives *who* everything in the template, in the order GitHub needs."""
    ordered = sorted(grants, key=lambda g: (_ORDER[g.scope], g.target.casefold()))
    return [plan_add(g.scope, g.ident(), who, "person", g.role) for g in ordered]


@dataclass
class AccessTemplates:
    """The account's templates; :meth:`save` writes them back."""

    path: Path
    templates: dict[str, list[Grant]] = field(default_factory=dict)

    @classmethod
    def load(cls, account_key: str, *, data_dir: Path | None = None) -> AccessTemplates:
        digest = hashlib.sha256(account_key.encode("utf-8")).hexdigest()[:32]
        path = (data_dir or app_data_dir()) / f"github_access_templates_{digest}.json"
        raw = read_json(path, default={})
        templates: dict[str, list[Grant]] = {}
        stored = raw.get("templates") if isinstance(raw, dict) else None
        if isinstance(stored, dict):
            for name, lines in stored.items():
                if isinstance(name, str) and name.strip() and isinstance(lines, list):
                    templates[name] = parse_grants("\n".join(str(x) for x in lines))[0]
        return cls(path, templates)

    def names(self) -> list[str]:
        return sorted(self.templates, key=str.casefold)

    def grants(self, name: str) -> list[Grant]:
        return list(self.templates.get(name, []))

    def text(self, name: str) -> str:
        """The template as it is edited: one grant a line."""
        return "\n".join(grant.text() for grant in self.templates.get(name, []))

    def describe(self, name: str) -> str:
        """One line for the template's row: its name and what it gives."""
        grants = self.templates.get(name, [])
        if not grants:
            return f"{name}: nothing yet"
        said = "; ".join(grant.text() for grant in grants[:3])
        more = f"; and {len(grants) - 3} more" if len(grants) > 3 else ""
        return f"{name}: {said}{more}"

    def set_template(self, name: str, text: str) -> tuple[str, list[str]]:
        """Make or replace a template. Returns (problem, lines that were not grants)."""
        key = " ".join(name.split())[:MAX_TEMPLATE_NAME]
        if not key:
            return "A template needs a name.", []
        grants, rejected = parse_grants(text)
        if not grants:
            return "A template needs at least one line such as write on owner/name.", rejected
        existing = {n.casefold(): n for n in self.templates}
        self.templates[existing.get(key.casefold(), key)] = grants
        return "", rejected

    def rename(self, old: str, new: str) -> str:
        """Rename a template; "" on success, else the sentence that says why not."""
        target = " ".join(new.split())[:MAX_TEMPLATE_NAME]
        if old not in self.templates:
            return f"There is no template called {old}."
        if not target:
            return "A template needs a name."
        if target != old and target.casefold() in {n.casefold() for n in self.templates}:
            return f"There is already a template called {target}."
        self.templates = {target if k == old else k: v for k, v in self.templates.items()}
        return ""

    def delete(self, name: str) -> bool:
        return self.templates.pop(name, None) is not None

    def save(self) -> None:
        data = {
            "version": _VERSION,
            "templates": {
                name: [grant.text() for grant in grants] for name, grants in self.templates.items()
            },
        }
        write_json_atomic(self.path, data, base=self.path.parent)
