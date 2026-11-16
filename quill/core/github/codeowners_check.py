"""Check that every CODEOWNERS owner exists and may write (PRD 21.8).

GitHub only says an owner is wrong after the file is on the default branch: an
unknown account, a team that is not in the organization, or somebody without
write access is silently skipped when reviews are requested, so a rule meant to
protect a folder protects nothing. The CODEOWNERS sheet checks before saving,
the way the issue form checks do (PRD 21.5).

What is checked, per owner, once each however many rules name it:

* ``@user`` -- the account exists, and its permission on this repository is
  write, maintain or admin.
* ``@org/team`` -- the team exists in that organization, and it has push on
  this repository.
* an email address -- cannot be checked from here (GitHub matches it to an
  account with that verified address), so it is listed as unchecked rather
  than passed or failed.

:func:`check_owners` is pure: the lookups are passed in, so the rules are
tested without a network. :func:`github_lookups` makes the real ones from a
PyGithub repository and a way to reach organizations. A lookup that fails for
a reason other than "not found" says so -- an unreachable answer is never a
pass.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.github.template_files import parse_codeowners

__all__ = ["OwnerResult", "check_owners", "github_lookups", "summary"]

#: Repository permissions that let an owner approve a pull request.
_WRITES = frozenset({"admin", "maintain", "write", "push"})


@dataclass(frozen=True, slots=True)
class OwnerResult:
    owner: str
    line: int
    #: "ok", "problem" or "unchecked"
    state: str
    sentence: str


def _owners(text: str) -> list[tuple[str, int]]:
    seen: dict[str, int] = {}
    for rule in parse_codeowners(text):
        for owner in rule.owners:
            seen.setdefault(owner, rule.line)
    return list(seen.items())


def check_owners(
    text: str,
    *,
    user_permission: Callable[[str], str | None],
    team_can_push: Callable[[str, str], bool | None],
) -> list[OwnerResult]:
    """Every owner in *text*, judged once.

    *user_permission(login)* returns the permission name, or ``None`` when
    there is no such account. *team_can_push(org, slug)* returns whether the
    team may push, or ``None`` when there is no such team. Either may raise;
    the owner is then reported as not checked, with the reason.
    """
    results: list[OwnerResult] = []
    for owner, line in _owners(text):
        where = f"line {line}"
        if not owner.startswith("@"):
            if "@" in owner:
                results.append(
                    OwnerResult(
                        owner,
                        line,
                        "unchecked",
                        f"{owner} ({where}) is an email address. GitHub uses it only if it "
                        "is the verified address of an account with write access.",
                    )
                )
            else:
                results.append(
                    OwnerResult(
                        owner,
                        line,
                        "problem",
                        f"{owner} ({where}) is not an owner: start a person or team with @.",
                    )
                )
            continue
        name = owner[1:]
        try:
            if "/" in name:
                org, slug = name.split("/", 1)
                can_push = team_can_push(org, slug)
                if can_push is None:
                    state, said = "problem", f"{owner} ({where}): there is no such team in {org}."
                elif not can_push:
                    state, said = (
                        "problem",
                        f"{owner} ({where}) cannot write to this repository, so GitHub will "
                        "not ask it to review. Give the team write access, or remove it.",
                    )
                else:
                    state, said = "ok", f"{owner} ({where}) exists and can write."
            else:
                permission = user_permission(name)
                if permission is None:
                    state, said = "problem", f"{owner} ({where}): there is no such account."
                elif permission.lower() not in _WRITES:
                    state, said = (
                        "problem",
                        f"{owner} ({where}) has {permission} access, not write, so GitHub "
                        "will not ask them to review.",
                    )
                else:
                    state, said = "ok", f"{owner} ({where}) exists and can write."
        except Exception as error:  # noqa: BLE001 - an unanswered check is reported, never passed
            state, said = "unchecked", f"{owner} ({where}) could not be checked: {error}"
        results.append(OwnerResult(owner, line, state, said))
    return results


def summary(results: list[OwnerResult]) -> str:
    """One sentence for the announcement: how many owners, and how many need fixing."""
    if not results:
        return "There are no owners to check."
    problems = sum(1 for result in results if result.state == "problem")
    unchecked = sum(1 for result in results if result.state == "unchecked")
    total = len(results)
    parts = [f"{total} owner{'' if total == 1 else 's'} checked"]
    parts.append(
        "all can write" if not problems else f"{problems} need{'s' if problems == 1 else ''} fixing"
    )
    if unchecked:
        parts.append(f"{unchecked} could not be checked")
    return ", ".join(parts) + "."


def _not_found(error: BaseException) -> bool:
    return getattr(error, "status", None) == 404


def github_lookups(
    repo: Any, organization: Callable[[str], Any]
) -> tuple[Callable[[str], str | None], Callable[[str, str], bool | None]]:
    """The two lookups, from a PyGithub repository and ``organization(name)``."""

    def user_permission(login: str) -> str | None:
        try:
            return str(repo.get_collaborator_permission(login))
        except Exception as error:
            if _not_found(error):
                return None
            raise

    def team_can_push(org: str, slug: str) -> bool | None:
        try:
            team = organization(org).get_team_by_slug(slug)
        except Exception as error:
            if _not_found(error):
                return None
            raise
        permissions = team.get_repo_permission(repo)
        if permissions is None:
            return False
        return bool(
            getattr(permissions, "push", False)
            or getattr(permissions, "maintain", False)
            or getattr(permissions, "admin", False)
        )

    return user_permission, team_can_push
