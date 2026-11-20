"""What GitHub itself says about who may do what: the evidence behind Roles and Access.

My Access Here, Why Can't They?, Compare Accounts, the Access Review and the
Bulk Access Changes preview answer from what GitHub returns, never from a
guessed table:

* a person's role on a repository: ``GET /repos/{o}/{r}/collaborators/{u}/permission``
  (``role_name``, which names a custom role too, and the ``permission`` it is
  built on);
* your own: the repository's ``permissions`` and GraphQL ``viewerPermission``;
* the organization: your membership (``GET /user/memberships/orgs/{org}``) or
  theirs (``GET /orgs/{org}/memberships/{u}``) and its base permission;
* teams: ``GET /repos/{o}/{r}/teams`` with each team's permission, and whether
  the person is on it;
* rules: ``GET /repos/{o}/{r}/rules/branches/{branch}`` (every ruleset that
  applies, the organization's too) and classic branch protection;
* the token: ``X-OAuth-Scopes`` for a classic or OAuth token. A fine-grained
  token's permissions are not listed by GitHub at all; when it refuses
  something, ``X-Accepted-GitHub-Permissions`` names what was needed, and
  :func:`refusal_needs` says it.

When GitHub will not say (a 403 for lack of access, a 404), the answer says
that plainly, as unknown, rather than filling the gap. The one fixed table left,
:data:`quill.core.github.access.ROLE_ABILITIES`, is GitHub's documented default
for its built-in roles, and every answer that uses it says so
(:data:`DOCUMENTED`).

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.github.access import ROLE_ABILITIES
from quill.core.github.permissions import REPO_ROLES, repo_role
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "BLOCKING",
    "DOCUMENTED",
    "Fact",
    "Read",
    "Rule",
    "blocking",
    "branch_rules",
    "documented_need",
    "fetch",
    "person_role",
    "refusal_needs",
    "role_from_answer",
    "team_role",
    "token_facts",
    "token_kind",
]

#: Said wherever an answer rests on GitHub's documented defaults, not on a reply.
DOCUMENTED = (
    "By GitHub's documented defaults for its built-in roles (docs.github.com, "
    "Repository roles for an organization). GitHub's API does not list what a role may do."
)


@dataclass(frozen=True)
class Fact:
    """One thing GitHub said, and the request that said it ("" for no request)."""

    text: str
    source: str = ""

    def line(self) -> str:
        return f"{self.text} (GitHub: {self.source})" if self.source else self.text


@dataclass(frozen=True)
class Read:
    """One GET: what came back, or the status that stopped it."""

    path: str
    data: Any = None
    status: int | None = 200
    headers: Mapping[str, str] = field(default_factory=dict)
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    def why_not(self, what: str) -> str:
        """Why *what* cannot be known, from the refusal, in one sentence."""
        if self.status == 403:
            needs = refusal_needs(self.headers)
            return f"GitHub would not tell this account {what} (403)." + (
                f" {needs}" if needs else ""
            )
        if self.status == 404:
            return (
                f"GitHub answered 'not found' for {what}: it is not there, or this account "
                "cannot see it."
            )
        return f"QUILL could not read {what}: {self.message or 'GitHub did not answer'}."


def fetch(api: GitHubApi, path: str, query: Mapping[str, str] | None = None) -> Read:
    """GET *path*; a refusal becomes a :class:`Read` with its status, never an exception."""
    try:
        answer = api.rest("GET", path, query=query)
    except GitHubRestError as exc:
        return Read(path, None, exc.status, dict(exc.headers or {}), str(exc))
    except Exception as exc:  # noqa: BLE001 - a network failure is "could not read"
        return Read(path, None, None, {}, str(exc))
    return Read(path, answer.data, answer.status, dict(answer.headers or {}))


def refusal_needs(headers: Mapping[str, str]) -> str:
    """What a 403 says it needed: a fine-grained permission or a classic scope ("" if none)."""
    lowered = {str(k).casefold(): str(v) for k, v in headers.items()}
    fine = lowered.get("x-accepted-github-permissions", "").strip()
    scopes = lowered.get("x-accepted-oauth-scopes", "").strip()
    parts = []
    if fine:
        parts.append(f"GitHub says it needs the token permission {fine.replace(';', ',')}.")
    if scopes:
        parts.append(f"GitHub accepts the scope {scopes} for it.")
    return " ".join(parts)


# -- the token --------------------------------------------------------------------


def token_kind(token: str | None) -> str:
    """``classic``, ``oauth``, ``fine-grained``, ``app`` or ``unknown``, by GitHub's prefixes."""
    value = (token or "").strip()
    if value.startswith("github_pat_"):
        return "fine-grained"
    if value.startswith("ghp_"):
        return "classic"
    if value.startswith("gho_"):
        return "oauth"
    if value.startswith(("ghu_", "ghs_")):
        return "app"
    return "unknown"


def token_facts(token: str | None, scopes_header: str | None) -> list[Fact]:
    """What can be known about the token's own permissions, and what cannot."""
    kind = token_kind(token)
    if scopes_header is not None and kind not in ("fine-grained", "app"):
        scopes = ", ".join(s.strip() for s in scopes_header.split(",") if s.strip())
        return [
            Fact(
                f"This sign-in's scopes are {scopes or 'none at all'}.",
                "the X-OAuth-Scopes header",
            )
        ]
    if kind in ("fine-grained", "app"):
        noun = "fine-grained token" if kind == "fine-grained" else "GitHub App token"
        return [
            Fact(
                f"This is a {noun}. GitHub does not list its permissions, so they cannot "
                "be known here; when GitHub refuses something, it names the permission it "
                "needed, and QUILL says it."
            )
        ]
    return [Fact("GitHub sent no scope list for this sign-in, so its scopes cannot be known here.")]


# -- roles -------------------------------------------------------------------------


def role_from_answer(data: object) -> tuple[str, str]:
    """``(role_name, permission)`` from a collaborator-permission answer.

    ``role_name`` is GitHub's own name for the role (``maintain``, or a custom
    role's name); ``permission`` is the older word it is built on (``admin``,
    ``write``, ``read`` or ``none``).
    """
    if not isinstance(data, Mapping):
        return "", ""
    permission = str(data.get("permission") or "")
    role_name = str(data.get("role_name") or "")
    if not role_name:
        user = data.get("user")
        role_name = repo_role(user.get("permissions") if isinstance(user, Mapping) else None)
    return role_name or repo_role(permission), permission


def person_role(api: GitHubApi, repo: str, login: str) -> tuple[str, str, list[Fact]]:
    """*login*'s role on *repo* as GitHub says it: ``(role_name, permission, facts)``.

    ``role_name`` is "" when GitHub would not say; the facts say why.
    """
    path = f"/repos/{repo}/collaborators/{login}/permission"
    read = fetch(api, path)
    if not read.ok:
        return "", "", [Fact(read.why_not(f"{login}'s role on {repo}"))]
    role_name, permission = role_from_answer(read.data)
    if not role_name or permission == "none":
        return "", permission, [Fact(f"GitHub says {login} has no access to {repo}.", path)]
    facts = [Fact(f"GitHub says {login}'s role on {repo} is {role_name}.", path)]
    if role_name not in REPO_ROLES:
        facts.append(
            Fact(
                f"{role_name} is a custom role, built on {permission or 'a base role'}. GitHub's "
                "API names it but does not list each permission it adds; the organization's "
                "Settings, Repository roles page does."
            )
        )
    return role_name, permission, facts


def team_role(permission: object) -> str:
    """A team's permission word (``pull``, ``push``) as a role (``read``, ``write``)."""
    return repo_role(str(permission or ""))


def documented_need(ability: str) -> str:
    """The built-in role GitHub documents for *ability*; "" when the table has no such ability."""
    for name, abilities in ROLE_ABILITIES:
        if ability in abilities:
            return name
    return ""


# -- rules --------------------------------------------------------------------------

_RULE_WORDS: dict[str, str] = {
    "pull_request": "changes need a pull request",
    "required_status_checks": "status checks must pass",
    "non_fast_forward": "no force pushes",
    "deletion": "the branch cannot be deleted",
    "creation": "matching branches cannot be created",
    "update": "the branch cannot be pushed to",
    "required_linear_history": "history must be linear",
    "required_signatures": "commits must be signed",
    "merge_queue": "merges go through the merge queue",
    "required_deployments": "deployments must succeed first",
    "code_scanning": "code scanning results must pass",
    "workflows": "required workflows must pass",
}

#: Which rules can stop an ability even when the role allows it.
BLOCKING: dict[str, frozenset[str]] = {
    "push to branches": frozenset({
        "update",
        "pull_request",
        "required_status_checks",
        "required_signatures",
        "required_linear_history",
        "non_fast_forward",
    }),
    "merge pull requests": frozenset({
        "pull_request",
        "required_status_checks",
        "merge_queue",
        "required_deployments",
        "code_scanning",
        "workflows",
    }),
    "delete branches": frozenset({"deletion"}),
    "push to protected branches where rules allow": frozenset({"update", "pull_request"}),
}


@dataclass(frozen=True)
class Rule:
    """One rule GitHub says applies to a branch, and the ruleset it came from."""

    kind: str
    source: str = ""
    detail: str = ""

    def words(self) -> str:
        said = _RULE_WORDS.get(self.kind, self.kind.replace("_", " "))
        where = f", from {self.source}" if self.source else ""
        return f"{said}{(' (' + self.detail + ')') if self.detail else ''}{where}"


def _rule(row: Mapping[str, Any]) -> Rule:
    kind = str(row.get("type") or "")
    params = row.get("parameters")
    detail = ""
    if isinstance(params, Mapping):
        approvals = params.get("required_approving_review_count")
        if isinstance(approvals, int) and approvals:
            detail = f"{approvals} approving review{'s' if approvals != 1 else ''}"
        checks = params.get("required_status_checks")
        if isinstance(checks, list) and checks:
            names = [str(c.get("context", "")) for c in checks if isinstance(c, Mapping)]
            detail = ", ".join(n for n in names if n)
    source_type = str(row.get("ruleset_source_type") or "")
    source = str(row.get("ruleset_source") or "")
    origin = f"the {source_type.lower()} {source}'s ruleset" if source else ""
    return Rule(kind, origin, detail)


def branch_rules(api: GitHubApi, repo: str, branch: str) -> tuple[list[Rule], list[Fact]]:
    """Every rule GitHub says applies to *branch*: rulesets, then classic protection."""
    facts: list[Fact] = []
    path = f"/repos/{repo}/rules/branches/{branch}"
    read = fetch(api, path)
    rules: list[Rule] = []
    if read.ok and isinstance(read.data, list):
        rules = [_rule(row) for row in read.data if isinstance(row, Mapping)]
        facts.append(
            Fact(
                f"GitHub lists {len(rules)} ruleset rule{'s' if len(rules) != 1 else ''} on "
                f"{branch}" + (": " + "; ".join(r.words() for r in rules) if rules else "."),
                path,
            )
        )
    else:
        facts.append(Fact(read.why_not(f"the rules on {branch}")))
    protection = f"/repos/{repo}/branches/{branch}/protection"
    classic = fetch(api, protection)
    if classic.ok and isinstance(classic.data, Mapping):
        found = _classic_rules(classic.data)
        rules.extend(found)
        facts.append(
            Fact(
                f"{branch} has classic branch protection: "
                + ("; ".join(r.words() for r in found) or "nothing that limits pushes")
                + ".",
                protection,
            )
        )
    elif classic.status == 404:
        facts.append(Fact(f"{branch} has no classic branch protection.", protection))
    else:
        facts.append(
            Fact(classic.why_not(f"{branch}'s classic protection (only admins may read it)"))
        )
    return rules, facts


def _classic_rules(data: Mapping[str, Any]) -> list[Rule]:
    found: list[Rule] = []
    source = "classic branch protection"
    reviews = data.get("required_pull_request_reviews")
    if isinstance(reviews, Mapping):
        count = reviews.get("required_approving_review_count")
        detail = f"{count} approving review{'s' if count != 1 else ''}" if count else ""
        found.append(Rule("pull_request", source, detail))
    checks = data.get("required_status_checks")
    if isinstance(checks, Mapping):
        found.append(Rule("required_status_checks", source))
    restrictions = data.get("restrictions")
    if isinstance(restrictions, Mapping):
        people = [
            str(u.get("login", ""))
            for u in restrictions.get("users") or []
            if isinstance(u, Mapping)
        ]
        teams = [
            str(t.get("slug", ""))
            for t in restrictions.get("teams") or []
            if isinstance(t, Mapping)
        ]
        allowed = ", ".join([*people, *teams]) or "nobody named"
        found.append(Rule("update", source, f"only {allowed} may push"))
    for key, kind in (
        ("required_linear_history", "required_linear_history"),
        ("required_signatures", "required_signatures"),
    ):
        value = data.get(key)
        if isinstance(value, Mapping) and value.get("enabled"):
            found.append(Rule(kind, source))
    deletions = data.get("allow_deletions")
    if isinstance(deletions, Mapping) and not deletions.get("enabled"):
        found.append(Rule("deletion", source))
    return found


def blocking(rules: Sequence[Rule], ability: str) -> list[Rule]:
    """The rules among *rules* that can stop *ability*."""
    kinds = BLOCKING.get(ability, frozenset())
    return [rule for rule in rules if rule.kind in kinds]
