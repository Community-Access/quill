"""Your codespaces: list, create, start, stop, export, publish and delete (GitHub PRD section 19).

A codespace is a cloud computer GitHub runs for one repository and branch.
Everything here talks to GitHub's REST API for the signed-in person's own
codespaces: rows for the Workbench (kind ``codespace``, keyed by the
codespace's name, which the Codespace Properties sheet opens), the choices
creating one needs (branch, machine, dev container), and each action as one
sentence to say. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "PAYER_UNKNOWN",
    "Choice",
    "CodespaceError",
    "NewChoices",
    "billing_owner",
    "codespace_row",
    "create",
    "delete",
    "export",
    "export_status",
    "fetch",
    "for_pull",
    "machines",
    "new_choices",
    "publish",
    "set_machine",
    "start",
    "stop",
]


class CodespaceError(CodedError):
    code = "QUILL-GITHUB-CODESPACE-REFUSED"


@dataclass(frozen=True)
class Choice:
    """One machine or dev container to choose from: what to send, and what to say."""

    value: str
    label: str


def _one(name: str) -> str:
    return f"/user/codespaces/{quote(name, safe='')}"


def _refused(exc: GitHubRestError, doing: str) -> CodespaceError:
    if exc.status in (401, 403):
        return CodespaceError(
            f"GitHub refused to {doing}. It needs the codespace permission; signing in "
            "again from Manage GitHub Accounts asks for it."
        )
    if exc.status == 404:
        return CodespaceError(f"GitHub found nothing to {doing}.")
    if exc.status == 409:
        return CodespaceError(f"GitHub could not {doing} while the codespace is busy. Try again.")
    if exc.status in (400, 422):
        return CodespaceError(f"GitHub could not {doing}: {exc}")
    return CodespaceError(f"Could not {doing}: {exc}")


PAYER_UNKNOWN = "you, unless the repository's organization pays for Codespaces"


def _payer(data: Any) -> str:
    """Who GitHub bills, from a ``billable_owner`` in *data*, as words to say."""
    owner = data.get("billable_owner") if isinstance(data, Mapping) else None
    if not isinstance(owner, Mapping):
        return PAYER_UNKNOWN
    login = str(owner.get("login") or "")
    if not login:
        return PAYER_UNKNOWN
    if str(owner.get("type") or "").casefold() == "organization":
        return f"the organization {login}"
    return f"you ({login})"


def billing_owner(api: GitHubApi, *, repo: str = "", name: str = "") -> str:
    """Who pays for codespace *name*, or for a new one in *repo*: you, or an organization.

    Never raises: when GitHub will not say, the answer is :data:`PAYER_UNKNOWN`, so
    the question before a paid action can still be asked honestly.
    """
    path = _one(name) if name else f"/repos/{repo}/codespaces/new"
    try:
        return _payer(api.rest("GET", path).data)
    except GitHubRestError:
        return PAYER_UNKNOWN


def codespace_row(raw: Mapping[str, Any]) -> ExploreRow:
    name = str(raw.get("name") or "")
    shown = str(raw.get("display_name") or name)
    repo_data = raw.get("repository")
    repo = str(repo_data.get("full_name") or "") if isinstance(repo_data, Mapping) else ""
    git = raw.get("git_status")
    branch = str(git.get("ref") or "") if isinstance(git, Mapping) else ""
    state = str(raw.get("state") or "Unknown")
    machine_data = raw.get("machine")
    machine = (
        str(machine_data.get("display_name") or "") if isinstance(machine_data, Mapping) else ""
    )
    used = str(raw.get("last_used_at") or "")[:10]
    parts = [state] + ([machine] if machine else []) + ([f"used {used}"] if used else [])
    where = f"{repo} on {branch}" if branch else repo or "a repository"
    label = f"{shown}: {where}, {', '.join(parts)}."
    url = str(raw.get("web_url") or "")
    return ExploreRow(label, label + (f"\n{url}" if url else ""), url, repo, "codespace", name)


def fetch(api: GitHubApi, repo: str = "", warnings: list[str] | None = None) -> list[ExploreRow]:
    """Your codespaces, or only those for *repo*."""
    path = f"/repos/{repo}/codespaces" if repo else "/user/codespaces"
    try:
        data = api.rest("GET", path, query={"per_page": "100"}).data
    except GitHubRestError as exc:
        raise _refused(exc, "list your codespaces") from exc
    items = data.get("codespaces") if isinstance(data, Mapping) else data
    rows = [codespace_row(raw) for raw in items or () if isinstance(raw, Mapping)]
    if not rows and warnings is not None:
        warnings.append(
            "No codespaces yet. Ctrl+N makes one." if repo else "You have no codespaces."
        )
    return rows


def _machines(data: Any) -> list[Choice]:
    items = data.get("machines") if isinstance(data, Mapping) else data
    found = []
    for raw in items or ():
        if not isinstance(raw, Mapping) or not raw.get("name"):
            continue
        cores = raw.get("cpus")
        memory = int(raw.get("memory_in_bytes") or 0) // (1024**3)
        words = str(raw.get("display_name") or raw["name"])
        detail = ", ".join(
            part
            for part in (
                f"{cores} cores" if cores else "",
                f"{memory} GB of memory" if memory else "",
            )
            if part
        )
        found.append(Choice(str(raw["name"]), f"{words}" + (f" ({detail})" if detail else "")))
    return found


@dataclass(frozen=True)
class NewChoices:
    """What creating a codespace in one repository can use, and GitHub's defaults."""

    machines: tuple[Choice, ...]
    containers: tuple[Choice, ...]
    default_container: str
    location: str
    allowed: bool
    payer: str = PAYER_UNKNOWN


def new_choices(api: GitHubApi, repo: str, ref: str) -> NewChoices:
    """The machines, dev containers and defaults for a codespace on *ref*."""
    try:
        made = api.rest("GET", f"/repos/{repo}/codespaces/machines", query={"ref": ref}).data
        containers = api.rest("GET", f"/repos/{repo}/codespaces/devcontainers").data
        defaults = api.rest("GET", f"/repos/{repo}/codespaces/new", query={"ref": ref}).data
    except GitHubRestError as exc:
        raise _refused(exc, f"read what a codespace for {repo} can use") from exc
    listed = containers.get("devcontainers") if isinstance(containers, Mapping) else []
    choices = tuple(
        Choice(str(one.get("path")), str(one.get("display_name") or one.get("name") or one["path"]))
        for one in listed or ()
        if isinstance(one, Mapping) and one.get("path")
    )
    default = defaults.get("defaults") if isinstance(defaults, Mapping) else None
    container = str(default.get("devcontainer_path") or "") if isinstance(default, Mapping) else ""
    location = str(default.get("location") or "") if isinstance(default, Mapping) else ""
    allowed = True
    if container:
        try:
            check = api.rest(
                "GET",
                f"/repos/{repo}/codespaces/permissions_check",
                query={"ref": ref, "devcontainer_path": container},
            ).data
            allowed = bool(check.get("accepted", True)) if isinstance(check, Mapping) else True
        except GitHubRestError:
            allowed = True  # the check is advice; creating says if it is refused
    payer = _payer(defaults)
    return NewChoices(tuple(_machines(made)), choices, container, location, allowed, payer)


def create(api: GitHubApi, repo: str, ref: str, machine: str = "", container: str = "") -> str:
    """Make a codespace for *repo* on *ref*; GitHub starts building it at once."""
    body: dict[str, object] = {"ref": ref}
    if machine:
        body["machine"] = machine
    if container:
        body["devcontainer_path"] = container
    try:
        data = api.rest("POST", f"/repos/{repo}/codespaces", body=body).data
    except GitHubRestError as exc:
        raise _refused(exc, f"make a codespace for {repo}") from exc
    name = (
        str(data.get("display_name") or data.get("name") or "") if isinstance(data, Mapping) else ""
    )
    return f"Making the codespace {name} for {repo} on {ref}. It takes a minute or two to start."


def for_pull(api: GitHubApi, repo: str, number: int) -> str:
    """Make a codespace on a pull request's branch."""
    try:
        data = api.rest("POST", f"/repos/{repo}/pulls/{number}/codespaces", body={}).data
    except GitHubRestError as exc:
        raise _refused(exc, f"make a codespace for pull request #{number}") from exc
    name = (
        str(data.get("display_name") or data.get("name") or "") if isinstance(data, Mapping) else ""
    )
    return f"Making the codespace {name} for pull request #{number}. It takes a minute or two."


def start(api: GitHubApi, name: str) -> str:
    try:
        api.rest("POST", f"{_one(name)}/start")
    except GitHubRestError as exc:
        if exc.status == 402:
            raise CodespaceError(
                "GitHub will not start it: your Codespaces spending limit is used up."
            ) from exc
        raise _refused(exc, f"start {name}") from exc
    return f"Starting {name}."


def stop(api: GitHubApi, name: str) -> str:
    try:
        api.rest("POST", f"{_one(name)}/stop")
    except GitHubRestError as exc:
        raise _refused(exc, f"stop {name}") from exc
    return f"Stopping {name}. Its files are kept."


def delete(api: GitHubApi, name: str) -> str:
    try:
        api.rest("DELETE", _one(name))
    except GitHubRestError as exc:
        raise _refused(exc, f"delete {name}") from exc
    return f"Deleted {name}. Changes not pushed or exported are gone."


def machines(api: GitHubApi, name: str) -> list[Choice]:
    """The machines this codespace may move to."""
    try:
        return _machines(api.rest("GET", f"{_one(name)}/machines").data)
    except GitHubRestError as exc:
        raise _refused(exc, f"list the machines {name} may use") from exc


def set_machine(api: GitHubApi, name: str, machine: Choice) -> str:
    try:
        api.rest("PATCH", _one(name), body={"machine": machine.value})
    except GitHubRestError as exc:
        raise _refused(exc, f"change {name}'s machine") from exc
    return f"{name} will use {machine.label} from its next start."


def export(api: GitHubApi, name: str) -> tuple[str, str]:
    """Push the codespace's unpushed changes to a new branch: (sentence, export id)."""
    try:
        data = api.rest("POST", f"{_one(name)}/exports").data
    except GitHubRestError as exc:
        raise _refused(exc, f"export {name}") from exc
    export_id = str(data.get("id") or "latest") if isinstance(data, Mapping) else "latest"
    return f"Exporting {name}'s changes to a branch of their own.", export_id


def export_status(api: GitHubApi, name: str, export_id: str) -> str:
    try:
        data = api.rest("GET", f"{_one(name)}/exports/{quote(export_id, safe='')}").data
    except GitHubRestError as exc:
        raise _refused(exc, "read the export's progress") from exc
    if not isinstance(data, Mapping):
        return "GitHub sent nothing about the export."
    state = str(data.get("state") or "")
    branch = str(data.get("branch") or "")
    if state == "succeeded":
        return f"Exported to the branch {branch}." if branch else "Exported."
    if state == "failed":
        return "The export failed. Open the codespace on GitHub to see why."
    return "The export is still running."


def publish(api: GitHubApi, name: str, repository: str, private: bool) -> str:
    """Make a new repository from a codespace made from a template."""
    body: dict[str, object] = {"private": private}
    if repository.strip():
        body["name"] = repository.strip()
    try:
        data = api.rest("POST", f"{_one(name)}/publish", body=body).data
    except GitHubRestError as exc:
        raise _refused(exc, f"publish {name} to a new repository") from exc
    made = data.get("repository") if isinstance(data, Mapping) else None
    full = str(made.get("full_name") or "") if isinstance(made, Mapping) else ""
    return f"Published {name} to {full or 'a new repository'}."
