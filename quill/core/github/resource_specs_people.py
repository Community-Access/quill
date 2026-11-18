"""Someone's public lists, and GitHub's own templates, for the resource engine.

Under **People >** a person: their SSH keys, GPG keys, SSH signing keys,
social accounts, public gists, starred and watched repositories, Projects,
and the public activity of people they follow. All read only: these are
another account's.

Under **Repositories**, three of GitHub's own lists a new repository chooses
from: licences, .gitignore templates and codes of conduct.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.resource_engine import ResourceSpec
from quill.core.github.sheet_fields import dig

__all__ = ["PEOPLE_SPECS"]

_PROFILE = "https://github.com/{target}"


def _key_end(raw: Mapping[str, Any]) -> str:
    key = str(raw.get("key") or "")
    return f"ending {key[-8:]}" if key else "with no key text"


def _gpg(raw: Mapping[str, Any]) -> str:
    emails = [str(e.get("email")) for e in raw.get("emails") or () if isinstance(e, Mapping)]
    said = f"GPG key {raw.get('key_id')}" + (f" for {', '.join(emails)}" if emails else "")
    expires = str(raw.get("expires_at") or "")[:10]
    return said + (f", expires {expires}" if expires else "") + "."


def _repo_line(raw: Mapping[str, Any]) -> str:
    about = f": {raw['description']}" if raw.get("description") else ""
    return f"{raw.get('full_name')}{about}."


def _read_only(
    key: str, label: str, list_path: str, noun: str, sentence: Any, help_: str, page: str, **kw: Any
) -> ResourceSpec:
    return ResourceSpec(
        key=key,
        label=label,
        scope="person",
        parent="person",
        noun=noun,
        list_path=list_path,
        sentence=sentence,
        help=help_,
        page=page,
        delete=False,
        **kw,
    )


PEOPLE_SPECS: tuple[ResourceSpec, ...] = (
    _read_only(
        "person_keys",
        "SSH Keys",
        "{base}/keys",
        "SSH key",
        lambda raw: f"SSH key {raw.get('id')}, {_key_end(raw)}.",
        "SSH Keys: the public keys this person signs in to Git with; useful to check one "
        "before giving them access to a server.",
        _PROFILE + ".keys",
        id_field="id",
    ),
    _read_only(
        "person_gpg_keys",
        "GPG Keys",
        "{base}/gpg_keys",
        "GPG key",
        lambda raw: _gpg(raw),
        "GPG Keys: the keys GitHub checks this person's signed commits against.",
        _PROFILE + ".gpg",
        id_field="key_id",
    ),
    _read_only(
        "person_signing_keys",
        "SSH Signing Keys",
        "{base}/ssh_signing_keys",
        "SSH signing key",
        lambda raw: f"{raw.get('title') or 'A signing key'}, {_key_end(raw)}.",
        "SSH Signing Keys: SSH keys this person signs commits with.",
        _PROFILE,
        id_field="id",
    ),
    _read_only(
        "person_social",
        "Social Accounts",
        "{base}/social_accounts",
        "social account",
        lambda raw: f"{raw.get('provider')}: {raw.get('url')}.",
        "Social Accounts: the links on this person's profile.",
        _PROFILE,
        id_field="url",
    ),
    _read_only(
        "person_gists",
        "Gists",
        "{base}/gists",
        "gist",
        lambda raw: (
            f"{raw.get('description') or ', '.join(raw.get('files') or {}) or 'A gist'}"
            f"{'' if raw.get('public', True) else ', secret'}."
        ),
        "Gists: this person's public gists, newest first.",
        "https://gist.github.com/{target}",
        id_field="id",
    ),
    _read_only(
        "person_starred",
        "Starred",
        "{base}/starred",
        "starred repository",
        _repo_line,
        "Starred: the repositories this person starred, newest first.",
        _PROFILE + "?tab=stars",
        id_field="full_name",
    ),
    _read_only(
        "person_watching",
        "Watching",
        "{base}/subscriptions",
        "watched repository",
        _repo_line,
        "Watching: the repositories this person watches.",
        _PROFILE,
        id_field="full_name",
    ),
    _read_only(
        "person_projects",
        "Projects",
        "{base}/projectsV2",
        "Project",
        lambda raw: (
            f"{raw.get('title')} (#{raw.get('number')}){', closed' if raw.get('closed') else ''}."
        ),
        "Projects: this person's public Projects.",
        _PROFILE + "?tab=projects",
        id_field="number",
    ),
    _read_only(
        "person_feed",
        "People They Follow: Activity",
        "{base}/received_events/public",
        "event",
        lambda raw: (
            f"{dig(raw, 'actor', 'login') or 'Someone'}: "
            f"{str(raw.get('type') or '').removesuffix('Event')} in "
            f"{dig(raw, 'repo', 'name') or 'a repository'}, "
            f"{str(raw.get('created_at') or '')[:10]}."
        ),
        "People They Follow: Activity: public activity of the accounts this person follows.",
        _PROFILE,
        id_field="id",
    ),
    # -- GitHub's own lists ------------------------------------------------------------------
    ResourceSpec(
        key="licenses",
        label="Licences",
        scope="user",
        parent="repositories",
        noun="licence",
        list_path="/licenses",
        id_field="key",
        sentence=lambda raw: f"{raw.get('name')} ({raw.get('spdx_id') or raw.get('key')}).",
        help="Licences: the open source licences GitHub offers a new repository.",
        page="https://choosealicense.com",
        delete=False,
    ),
    ResourceSpec(
        key="gitignore_templates",
        label=".gitignore Templates",
        scope="user",
        parent="repositories",
        noun=".gitignore template",
        list_path="/gitignore/templates",
        id_field="name",
        sentence=lambda raw: f"{raw.get('name')}.",
        help=".gitignore Templates: lists of files to leave out, offered to a new repository.",
        page="https://github.com/github/gitignore",
        delete=False,
    ),
    ResourceSpec(
        key="codes_of_conduct",
        label="Codes of Conduct",
        scope="user",
        parent="repositories",
        noun="code of conduct",
        list_path="/codes_of_conduct",
        id_field="key",
        sentence=lambda raw: f"{raw.get('name')}.",
        help="Codes of Conduct: the codes of conduct GitHub offers a repository.",
        page="https://docs.github.com/communities",
        delete=False,
    ),
)
