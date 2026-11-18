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

from collections.abc import Callable, Mapping
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
}


class ResourceError(CodedError):
    """A listed setting could not be read or changed; the message is said."""

    code = "QUILL-GITHUB-RESOURCE"


@dataclass(frozen=True)
class Field:
    """One answer New Here or Change asks for."""

    key: str
    prompt: str
    kind: str = "text"  # text, multiline, secret, choice, bool, list (comma separated)
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
    try:
        data = api.rest("GET", spec.path(target), query={"per_page": "100"}).data
    except GitHubRestError as exc:
        raise _refused(exc, f"list the {spec.noun}s") from exc
    items = data.get(spec.items_key) if spec.items_key and isinstance(data, Mapping) else data
    page = spec.page.replace("{target}", target)
    rows = []
    for raw in items or ():
        if not isinstance(raw, Mapping):
            continue
        label = spec.sentence(raw)
        item_id = str(raw.get(spec.id_field) or "")
        rows.append(
            ExploreRow(label, f"{label}\n{page}", page, target, "resource", f"{spec.key}:{item_id}")
        )
    if not rows and warnings is not None:
        warnings.append(
            f"No {spec.noun}s yet. Ctrl+N adds one." if spec.create else f"No {spec.noun}s."
        )
    return rows


def _value(answer: str, one: Field) -> object:
    if one.kind == "list":
        return [part.strip() for part in answer.split(",") if part.strip()]
    if one.kind == "bool":
        return answer == "true"
    return answer


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
    path = spec.made(target, named)
    body = _body(api, spec, target, spec.create, answers)
    try:
        api.rest(spec.create_method, path, body=body)
    except GitHubRestError as exc:
        raise _refused(exc, f"add the {spec.noun}") from exc
    first = named or next(
        (answers.get(one.key, "") for one in spec.create if one.kind != "secret"), ""
    )
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
    try:
        if spec.delete_body:
            api.rest("DELETE", spec.path(target), body={spec.delete_body: [item_id]})
        else:
            api.rest("DELETE", spec.item(target, item_id))
    except GitHubRestError as exc:
        raise _refused(exc, f"delete the {spec.noun}") from exc
    return f"Deleted the {spec.noun} {item_id}."
