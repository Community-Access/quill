"""One engine for GitHub's list-shaped settings (GitHub PRD section 19, the API long tail).

Much of what is left of GitHub's API is the same shape: a list of things that
belong to a repository, an organization or you, where you add one, perhaps
change one, and delete one. Variables, secrets for Actions, Dependabot,
Codespaces and the Copilot agent, runner groups, organization members, blocked
people, custom properties, issue types, your email addresses and social
accounts. Rather than a module for each, a :class:`ResourceSpec` says where
the list is and how one row reads, and this engine does the rest:

* :func:`fetch` lists it, every row a sentence (row kind ``resource``, key
  ``spec:id``);
* :func:`create` asks for each :class:`Field` in turn and sends it, sealing a
  secret with the owner's public key first (libsodium's sealed box, as GitHub
  requires) so the value never leaves the machine readable;
* :func:`edit` changes the fields a spec lets you change;
* :func:`delete` removes one.

The specs themselves are in :mod:`quill.core.github.resource_specs`; the
Workbench builds a tree node, ``Ctrl+N``, Delete and the coverage rows from
them. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "Field",
    "ResourceError",
    "ResourceSpec",
    "create",
    "delete",
    "edit",
    "fetch",
    "row_spec_and_id",
]

#: Where each scope's paths start, and how the coverage table spells it.
BASES = {
    "repository": ("/repos/{target}", "/repos/{owner}/{repo}"),
    "organization": ("/orgs/{target}", "/orgs/{org}"),
    "user": ("/user", "/user"),
    # One gist's comments, history and forks, reached from the gist's row.
    "gist": ("/gists/{target}", "/gists/{gist_id}"),
    # Someone else's public lists, under People > a person.
    "person": ("/users/{target}", "/users/{username}"),
    # An environment's target is "owner/repo/environments/name"; it has no tree node of
    # its own, and is reached from an environment's row (Secrets..., Variables...).
    "environment": ("/repos/{target}", "/repos/{owner}/{repo}/environments/{environment_name}"),
}


class ResourceError(CodedError):
    """A listed setting could not be read or changed; the message is said."""

    code = "QUILL-GITHUB-RESOURCE"


@dataclass(frozen=True)
class Field:
    """One answer New Here or Change asks for."""

    key: str
    prompt: str
    # text, multiline, secret, choice, bool, number, list (comma separated), names (comma
    # separated, sent as [{"name": ...}]), repository (owner/name, sent as its id)
    kind: str = "text"
    choices: tuple[str, ...] = ()
    optional: bool = False
    is_id: bool = False  # the answer names the new item in its path (a secret's name)


@dataclass(frozen=True)
class ResourceSpec:
    key: str
    label: str
    scope: str  # repository, organization, user
    parent: str
    noun: str
    list_path: str  # "{base}/actions/variables"
    sentence: Callable[[Mapping[str, Any]], str]
    help: str
    page: str  # "https://github.com/{target}/settings/variables/actions"
    items_key: str = ""
    id_field: str = "name"
    id_param: str = "{name}"
    item_path: str = "{list}/{id}"
    create: tuple[Field, ...] = ()
    create_method: str = "POST"
    create_path: str = "{list}"
    seal: bool = False  # create and edit send a sealed value with the public key's id
    edit: tuple[Field, ...] = ()
    edit_method: str = "PATCH"
    delete: bool = True
    delete_body: str = ""  # delete sends {delete_body: [id]} to the list itself
    extra: tuple[str, ...] = field(default=())  # further "METHOD path" rows it covers
    repositories: str = ""  # "/repositories": which repositories may use an item
    title_field: str = ""  # the field a row's sheet is titled by (a ruleset's name)
    # A list that takes more than one read (the access matrices): (api, target, warnings).
    reader: Callable[[GitHubApi, str, list[str]], list[ExploreRow]] | None = None
    # Refuses a delete that would lock you out: (api, target, id) to a sentence, or "".
    guard: Callable[[GitHubApi, str, str], str] | None = None
    typed_delete: bool = False  # Delete asks for the row's name typed (tier 3)
    query: tuple[tuple[str, str], ...] = ()  # sent with every list read ("hide_secret")

    def base(self, target: str) -> str:
        return BASES[self.scope][0].replace("{target}", target)

    def path(self, target: str) -> str:
        return self.list_path.replace("{base}", self.base(target))

    def _fill(self, template: str, target: str, item_id: str = "") -> str:
        filled = template.replace("{list}", self.list_path).replace("{base}", self.base(target))
        return filled.replace("{id}", quote(item_id, safe=""))

    def item(self, target: str, item_id: str) -> str:
        return self._fill(self.item_path, target, item_id)

    def made(self, target: str, item_id: str) -> str:
        return self._fill(self.create_path, target, item_id)

    def endpoints(self) -> dict[str, str]:
        """Every coverage row this spec answers, and where it is reached."""
        base = BASES[self.scope][1]
        listed = self.list_path.replace("{base}", base)

        def spelled(template: str) -> str:
            filled = template.replace("{list}", self.list_path).replace("{base}", base)
            return filled.replace("{id}", self.id_param)

        item = spelled(self.item_path)
        node = f"node:{'' if self.scope == 'user' else self.scope}:{self.key}"
        rows = {f"GET {listed}": node}
        if self.create:
            rows[f"{self.create_method} {spelled(self.create_path)}"] = node
            if self.seal:
                rows[f"GET {listed}/public-key"] = node
        if self.edit:
            rows[f"{self.edit_method} {item}"] = "command:github.workbench.resource_edit"
        if self.delete:
            gone = listed if self.delete_body else item
            rows[f"DELETE {gone}"] = "command:github.workbench.resource_delete"
        if self.repositories:
            chosen = f"{item}{self.repositories}"
            command = "command:github.workbench.resource_repositories"
            rows[f"GET {chosen}"] = command
            rows[f"PUT {chosen}/{{repository_id}}"] = command
            rows[f"DELETE {chosen}/{{repository_id}}"] = command
        for extra in self.extra:
            rows[extra] = node
        return rows


def row_spec_and_id(key: str) -> tuple[str, str]:
    spec, _, item_id = key.partition(":")
    return spec, item_id


def _refused(exc: GitHubRestError, doing: str) -> ResourceError:
    if exc.status in (401, 403):
        return ResourceError(
            f"GitHub refused to {doing}. It needs you to administer this, and sometimes a "
            "permission your sign-in lacks; signing in again asks for it."
        )
    if exc.status == 404:
        return ResourceError(f"GitHub found nothing to {doing}, or will not show it to you.")
    if exc.status == 422:
        return ResourceError(f"GitHub could not {doing}: {exc}")
    return ResourceError(f"Could not {doing}: {exc}")


def fetch(
    api: GitHubApi, spec: ResourceSpec, target: str, warnings: list[str] | None = None
) -> list[ExploreRow]:
    if spec.reader is not None:
        try:
            return spec.reader(api, target, warnings if warnings is not None else [])
        except GitHubRestError as exc:
            raise _refused(exc, f"read the {spec.label}") from exc
    try:
        data = api.rest(
            "GET", spec.path(target), query={"per_page": "100", **dict(spec.query)}
        ).data
    except GitHubRestError as exc:
        raise _refused(exc, f"list the {spec.noun}s") from exc
    items = data.get(spec.items_key) if spec.items_key and isinstance(data, Mapping) else data
    page = spec.page.replace("{target}", target)
    rows = []
    for raw in items or ():
        if isinstance(raw, str):
            raw = {"name": raw}  # lists of plain names, such as .gitignore templates
        if not isinstance(raw, Mapping):
            continue
        label = spec.sentence(raw)
        item_id = str(raw.get(spec.id_field) or "")
        title = str(raw.get(spec.title_field) or "") if spec.title_field else ""
        rows.append(
            ExploreRow(
                label,
                f"{label}\n{page}",
                page,
                target,
                "resource",
                f"{spec.key}:{item_id}",
                title=title,
            )
        )
    if not rows and warnings is not None:
        warnings.append(
            f"No {spec.noun}s yet. Ctrl+N adds one." if spec.create else f"No {spec.noun}s."
        )
    return rows


def _value(answer: str, one: Field) -> object:
    if one.kind == "list":
        return [part.strip() for part in answer.split(",") if part.strip()]
    if one.kind == "names":
        return [{"name": part.strip()} for part in answer.split(",") if part.strip()]
    if one.kind == "bool":
        return answer == "true"
    if one.kind == "number":
        try:
            return int(answer.strip())
        except ValueError:
            raise ResourceError(f"{one.prompt.rstrip(':?')} needs a number.") from None
    return answer


def _repository_id(api: GitHubApi, target: str, answer: str) -> tuple[str, str]:
    """``(id, owner/name)`` for a repository typed as owner/name, or a bare name in *target*."""
    name = answer.strip().removeprefix("https://github.com/").strip("/")
    full = name if "/" in name else f"{target.split('/', 1)[0]}/{name}"
    try:
        data = api.rest("GET", f"/repos/{quote(full, safe='/')}").data
    except GitHubRestError as exc:
        raise _refused(exc, f"find the repository {full}") from exc
    if not isinstance(data, Mapping) or data.get("id") is None:
        raise ResourceError(f"GitHub sent nothing for {full}.")
    return str(data["id"]), str(data.get("full_name") or full)


def _sealed(api: GitHubApi, spec: ResourceSpec, target: str, value: str) -> dict[str, object]:
    from quill.core.github.sheets_deploy import seal_secret

    try:
        key = api.rest("GET", f"{spec.path(target)}/public-key").data
    except GitHubRestError as exc:
        raise _refused(exc, "read the key that seals a secret") from exc
    if not isinstance(key, Mapping) or not key.get("key"):
        raise ResourceError("GitHub sent no key to seal the secret with.")
    return {
        "encrypted_value": seal_secret(str(key["key"]), value),
        "key_id": str(key.get("key_id")),
    }


def _body(
    api: GitHubApi,
    spec: ResourceSpec,
    target: str,
    fields: tuple[Field, ...],
    answers: Mapping[str, str],
) -> dict[str, object]:
    body: dict[str, object] = {}
    for one in fields:
        answer = answers.get(one.key, "")
        if one.is_id or (not answer and one.optional):
            continue
        if one.kind == "secret":
            body.update(_sealed(api, spec, target, answer) if spec.seal else {one.key: answer})
        else:
            body[one.key] = _value(answer, one)
    return body


def create(api: GitHubApi, spec: ResourceSpec, target: str, answers: Mapping[str, str]) -> str:
    """Add one; *answers* holds each field's answer by key. Returns the sentence to say."""
    for one in spec.create:
        if not one.optional and not answers.get(one.key, "").strip():
            raise ResourceError(f"{one.prompt.rstrip(':')} is needed.")
    named = next((answers[one.key].strip() for one in spec.create if one.is_id), "")
    said_name = named
    if any(one.is_id and one.kind == "repository" for one in spec.create):
        named, said_name = _repository_id(api, target, named)
    path = spec.made(target, named)
    body = _body(api, spec, target, spec.create, answers)
    try:
        made = api.rest(spec.create_method, path, body=body).data
    except GitHubRestError as exc:
        raise _refused(exc, f"add the {spec.noun}") from exc
    first = said_name or next(
        (answers.get(one.key, "") for one in spec.create if one.kind != "secret"), ""
    )
    if isinstance(made, Mapping) and made.get("state") == "pending":
        # Adding someone to an organization or team invites them; they are not in it yet.
        return f"Invited {first}. GitHub sends them an invitation to accept."
    return f"Added the {spec.noun} {first}.".replace("  ", " ").replace(" .", ".")


def edit(
    api: GitHubApi, spec: ResourceSpec, target: str, item_id: str, answers: Mapping[str, str]
) -> str:
    body = _body(api, spec, target, spec.edit, answers)
    if not body:
        raise ResourceError("Nothing to change.")
    try:
        api.rest(spec.edit_method, spec.item(target, item_id), body=body)
    except GitHubRestError as exc:
        raise _refused(exc, f"change the {spec.noun}") from exc
    return f"Changed the {spec.noun} {item_id}."


def delete(api: GitHubApi, spec: ResourceSpec, target: str, item_id: str) -> str:
    if spec.guard is not None:
        try:
            problem = spec.guard(api, target, item_id)
        except GitHubRestError as exc:
            raise _refused(
                exc, f"check who else could manage it before removing {item_id}"
            ) from exc
        if problem:
            raise ResourceError(problem)
    try:
        if spec.delete_body:
            api.rest("DELETE", spec.path(target), body={spec.delete_body: [item_id]})
        else:
            api.rest("DELETE", spec.item(target, item_id))
    except GitHubRestError as exc:
        raise _refused(exc, f"delete the {spec.noun}") from exc
    return f"Deleted the {spec.noun} {item_id}."


# -- which repositories may use an item ---------------------------------------------------------


@dataclass(frozen=True)
class Repo:
    id: int
    name: str


def _repos(data: Any) -> list[Repo]:
    items = data.get("repositories", []) if isinstance(data, Mapping) else data
    return [
        Repo(int(one["id"]), str(one.get("full_name") or one.get("name") or one["id"]))
        for one in items or []
        if isinstance(one, Mapping) and one.get("id") is not None
    ]


def allowed_repositories(
    api: GitHubApi, spec: ResourceSpec, target: str, item_id: str
) -> list[Repo]:
    """The repositories that may use one item now, by name."""
    try:
        reply = api.rest(
            "GET", spec.item(target, item_id) + spec.repositories, query={"per_page": "100"}
        )
    except GitHubRestError as exc:
        if exc.status == 409:
            raise ResourceError(
                f"This {spec.noun} is available to all or to private repositories, not to a "
                "chosen few. Change it on its row and choose Selected repositories first."
            ) from exc
        raise _refused(exc, f"read which repositories may use the {spec.noun}") from exc
    return sorted(_repos(reply.data), key=lambda repo: repo.name.lower())


def candidate_repositories(api: GitHubApi, spec: ResourceSpec, target: str) -> list[Repo]:
    """The repositories that could be chosen: the organization's, or your own."""
    path = "/user/repos" if spec.scope == "user" else f"/orgs/{target}/repos"
    found: list[Repo] = []
    for page in range(1, 11):
        try:
            reply = api.rest("GET", path, query={"per_page": "100", "page": str(page)})
        except GitHubRestError as exc:
            raise _refused(exc, "list the repositories to choose from") from exc
        batch = _repos(reply.data)
        found.extend(batch)
        if len(batch) < 100:
            break
    return sorted(found, key=lambda repo: repo.name.lower())


def set_repositories(
    api: GitHubApi,
    spec: ResourceSpec,
    target: str,
    item_id: str,
    had: Sequence[Repo],
    wanted: Sequence[Repo],
) -> str:
    """Add and remove repositories one at a time, so somebody else's change is kept."""
    before = {repo.id for repo in had}
    after = {repo.id for repo in wanted}
    base = spec.item(target, item_id) + spec.repositories
    added = [repo for repo in wanted if repo.id not in before]
    removed = [repo for repo in had if repo.id not in after]
    try:
        for repo in added:
            api.rest("PUT", f"{base}/{repo.id}")
        for repo in removed:
            api.rest("DELETE", f"{base}/{repo.id}")
    except GitHubRestError as exc:
        raise _refused(exc, f"change which repositories may use the {spec.noun}") from exc
    if not added and not removed:
        return "Nothing changed."
    parts = []
    if added:
        parts.append(f"added {_count(len(added), 'repository', 'repositories')}")
    if removed:
        parts.append(f"removed {_count(len(removed), 'repository', 'repositories')}")
    return f"{' and '.join(parts).capitalize()} for {item_id}."


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"
