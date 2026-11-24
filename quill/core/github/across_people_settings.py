"""People, repository settings and packages by name across repositories (PRD 22.11).

Three by-name places that reuse what one repository already reads:

- **People**: the access matrix from a person's side (PRD 18.3.2). Each row
  is a person, each variant a role and where it comes from ("Write,
  directly"; "Admin, from the organization or a team"), read from each
  repository's collaborators the way
  :mod:`quill.core.github.access_matrix` reads a role. A repository where the
  person has no access is said as "no access in"; one whose collaborators
  GitHub will not show you (it needs push access) could not be read, so it is
  never counted. Read only: Bulk Access Changes changes access in many
  repositories, previewed, and each repository's Access page in one.
- **Repository settings**: the switches of the Repository sheet's Features and
  Merging pages, under the sheet's own names ("Allow auto-merge: on in 20,
  off in 8"). **Make Them the Same** sets the winner's value in each
  repository, as that sheet's field does in one: admin access in each, the
  value read again first, and Change History can put each one back.
- **Packages**: each package by name with its type and visibility. GitHub
  lists packages by owner, each naming the repository it came from, so each
  owner is read once. Read only: GitHub's REST API cannot change a
  package's visibility or access.

wx-free and strict-typed.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from quill.core.github.across_by_name import ByNameRow, Copy, Survey
from quill.core.github.across_changes import LogEntry, Outcome, Plan, Result, Step, blocked_for

__all__ = [
    "PLACE_KINDS",
    "SETTING_KEYS",
    "apply_settings",
    "place_sentence",
    "plan_settings_same",
    "read_place_copies",
]

#: The by-name kinds this module reads.
PLACE_KINDS = frozenset({"people", "settings", "packages"})

#: The Repository sheet's switches that are the same kind of thing in every repository.
SETTING_KEYS = (
    "has_issues",
    "has_projects",
    "has_wiki",
    "has_discussions",
    "web_commit_signoff_required",
    "allow_merge_commit",
    "allow_squash_merge",
    "allow_rebase_merge",
    "allow_auto_merge",
    "allow_update_branch",
    "delete_branch_on_merge",
)
_DIRECT = "directly"
_INHERITED = "from the organization or a team"


def _labels() -> dict[str, str]:
    from quill.core.github.sheets_repo import REPOSITORY

    return {spec.key: spec.label for spec in REPOSITORY.sheet.fields()}


def _people(api: Any, repo: str) -> list[Copy]:
    from quill.core.github.access_matrix import role_of

    def page(affiliation: str) -> list[Mapping[str, Any]]:
        found: list[Mapping[str, Any]] = []
        number = 1
        while True:
            query = {"affiliation": affiliation, "per_page": "100", "page": str(number)}
            data = api.rest("GET", f"/repos/{repo}/collaborators", query=query).data
            if not isinstance(data, list) or not all(isinstance(row, Mapping) for row in data):
                raise ValueError(f"GitHub returned an unreadable collaborator list for {repo}.")
            found.extend(data)
            if len(data) < 100:
                return found
            number += 1

    direct = {str(row.get("login") or "").casefold() for row in page("direct")}
    found = []
    for row in page("all"):
        login = str(row.get("login") or "")
        if login:
            role, _rank = role_of(row)
            source = _DIRECT if login.casefold() in direct else _INHERITED
            props = (("role", role[:1].upper() + role[1:]), ("source", source))
            found.append(Copy(repo, login, props, login))
    return found


def _settings(api: Any, repo: str) -> list[Copy]:
    data = api.rest("GET", f"/repos/{repo}").data
    data = data if isinstance(data, Mapping) else {}
    labels = _labels()
    return [
        Copy(repo, labels.get(key, key), (("value", "on" if data.get(key) else "off"),), key)
        for key in SETTING_KEYS
        if key in data  # GitHub leaves some out for people who do not administer it
    ]


def _packages(api: Any, repo: str, memo: MutableMapping[str, Any]) -> list[Copy]:
    from quill.core.github.packages import owner_packages

    owner = repo.partition("/")[0].casefold()
    with memo.setdefault("packages lock", threading.Lock()):  # repositories read in parallel
        if owner not in memo:  # one owner's packages serve every repository it owns
            memo[owner] = owner_packages(api, repo.partition("/")[0], repo, all_pages=True)[0]
    found = []
    for raw in memo[owner]:
        source = raw.get("repository")
        name = str(source.get("full_name") or "") if isinstance(source, Mapping) else ""
        if name.casefold() != repo.casefold() or not raw.get("name"):
            continue
        kind = str(raw.get("package_type") or "")
        props = (("type", kind), ("visibility", str(raw.get("visibility") or "")))
        count = raw.get("version_count")
        plural = "" if count == 1 else "s"
        extra = (("has", f"{count} version{plural}"),) if isinstance(count, int) else ()
        found.append(Copy(repo, str(raw["name"]), props, f"{kind}/{raw['name']}", extra))
    return found


def read_place_copies(
    api: Any, kind: str, repo: str, memo: MutableMapping[str, Any] | None = None
) -> list[Copy]:
    """*kind*'s copies in *repo*. Raises on a refusal, which the survey says per repository."""
    if kind == "people":
        return _people(api, repo)
    if kind == "settings":
        return _settings(api, repo)
    if kind == "packages":
        return _packages(api, repo, memo if memo is not None else {})
    raise ValueError(f"Unknown kind {kind!r}.")


def _counted(row: ByNameRow, prop: str) -> str:
    """ "on in 20, off in 8": each value with how many repositories have it, commonest first."""
    counts: dict[str, int] = {}
    for copy in row.copies:
        counts[copy.prop(prop)] = counts.get(copy.prop(prop), 0) + 1
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return ", ".join(f"{value} in {count}" for value, count in ordered)


def place_sentence(row: ByNameRow) -> str:
    """A settings or people row in the PRD's words; "" for the other kinds."""
    if row.kind == "settings":
        parts = [f"{row.name}: {_counted(row, 'value')}"]
        if row.missing:
            parts.append(f"not shown to you in {len(row.missing)}")
    elif row.kind == "people":
        total = len(row.copies) + len(row.missing)
        said = f"{row.name}: access in {len(row.copies)} of {total} repositories"
        parts = [said, _counted(row, "role")]
        if row.missing:
            parts.append(f"no access in {len(row.missing)}")
    else:
        return ""
    if row.unread:
        parts.append(f"{len(row.unread)} could not be read")
    return ", ".join(parts)


# -- Make Them the Same, for settings ----------------------------------------------------


def plan_settings_same(survey: Survey, row: ByNameRow, winner: Sequence[tuple[str, str]]) -> Plan:
    """Every repository takes the winning value of one setting; admin access in each."""
    value = dict(winner).get("value", "")
    steps = []
    for copy in row.copies:
        if copy.prop("value") == value:
            steps.append(Step(copy.repository, "skip", after=f"already {value}", copy=copy))
            continue
        blocked = blocked_for(survey, copy.repository, admin=True)
        steps.append(
            Step(copy.repository, "update", copy.prop("value"), value, blocked, copy, tuple(winner))
        )
    return Plan(survey.kind, row.name, "Make the same", tuple(steps))


def _now(api: Any, repo: str, key: str) -> str:
    data = api.rest("GET", f"/repos/{repo}").data
    return "on" if isinstance(data, Mapping) and data.get(key) else "off"


def _changed(api: Any, plan: Plan, step: Step) -> str:
    copy = step.copy
    if copy is not None and _now(api, step.repository, copy.ident) != copy.prop("value"):
        return "it was changed on GitHub since you looked"
    return ""


def _run(api: Any, plan: Plan, step: Step) -> Outcome:
    copy = step.copy
    if copy is None or step.action != "update":
        raise ValueError(f"settings cannot {step.action}.")
    on = dict(step.body).get("value") == "on"
    api.rest("PATCH", f"/repos/{step.repository}", body={copy.ident: on})
    proven = _now(api, step.repository, copy.ident) == ("on" if on else "off")
    said = f"turned {'on' if on else 'off'}"
    change = ((copy.ident, plan.name, not on, on),)
    target = f"{step.repository} setting {plan.name}"
    ident = (("repo", step.repository),)
    return said, LogEntry("repository", ident, target, said, change, True, proven)


def apply_settings(api: Any, plan: Plan) -> list[Result]:
    """Run a settings plan, one result per repository. Runs off the UI thread."""
    from quill.core.github.across_changes import apply

    return apply(api, plan, runner=_run, check=_changed)
