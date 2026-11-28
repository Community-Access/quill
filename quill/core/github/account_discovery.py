"""Finding people and organizations on GitHub, and the few things you can do to one.

The Workbench's **Find a Person or Organization** window
(``quill/ui/github_find_account_dialog.py``)
asks this module for four things, each through the Workbench's own
:class:`~quill.core.github.workbench_api.GitHubApi` (one client, one token, the
rate-limit and error plumbing every other Workbench read already uses; this
module opens no connection of its own):

* **Search** (``GET /search/users``): by login or name, people and organizations
  together. A search reply carries only the login, the type and the address, so
  the first few hits are each read once more (``GET /users/{login}``) for their
  display name, description and public repository count. A hit that cannot be
  read keeps what the search gave; one failure never loses the list.
* **An account's repositories** (``GET /users/{login}/repos`` or
  ``/orgs/{login}/repos``), newest push first.
* **Follow and unfollow a person** (``PUT`` and ``DELETE /user/following/{login}``).
  GitHub documents following only for people, so an organization is refused here
  with a pointer to its page: following an organization is public-preview on
  GitHub's side and QUILL does not build on a preview.
* **Star and unstar a repository** (``PUT`` and ``DELETE /user/starred/{owner}/{repo}``).

After every change the state is read back from GitHub (``GET`` on the same
path answers 204 for yes and 404 for no) and the sentence says what GitHub
reports, not what was asked for.

Three meanings that must not blur, in code and in every sentence here:

* a **QUILL favorite** is a local shortcut (``tracked_accounts.py``); nothing is sent;
* a **GitHub star** is a public action, visible on the person's profile;
* a **GitHub List** is GitHub's own collection of starred repositories
  (``star_lists.py`` already adds a repository to one); a **watch** is a
  subscription to a repository's activity, which this module never touches.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.rest_transport import GitHubRestError, rest_failure_message
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "ENRICH_LIMIT",
    "KIND_ORGANIZATION",
    "KIND_PERSON",
    "AccountError",
    "AccountHit",
    "RepositoryHit",
    "disambiguate",
    "is_following",
    "is_starred",
    "list_repositories",
    "search_accounts",
    "set_following",
    "set_starred",
]

KIND_PERSON = "person"
KIND_ORGANIZATION = "organization"

#: How many hits are read a second time for their name and counts. The rest keep
#: the login and the type the search gave, so a long list costs a bounded number
#: of requests.
ENRICH_LIMIT = 12
_PAGE = 20
_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class AccountError(CodedError):
    """People and organization discovery could not do something; the message is said."""

    code = "QUILL-GITHUB-ACCOUNT-DISCOVERY"


@dataclass(frozen=True)
class AccountHit:
    """One person or organization, as the search and the profile read give it."""

    login: str
    kind: str
    name: str = ""
    description: str = ""
    public_repos: int | None = None
    followers: int | None = None
    url: str = ""

    @property
    def kind_word(self) -> str:
        return "Organization" if self.kind == KIND_ORGANIZATION else "Person"

    @property
    def page(self) -> str:
        return self.url or f"https://github.com/{self.login}"

    @property
    def repo_words(self) -> str:
        if self.public_repos is None:
            return ""
        count = self.public_repos
        return f"{count:,} public repositor{'y' if count == 1 else 'ies'}"

    def label(self, *, extra: str = "") -> str:
        """One row, whole: "Person: octocat (The Octocat), 8 public repositories. A bio."."""
        who = self.login + (f" ({self.name})" if self.name and self.name != self.login else "")
        parts = [f"{self.kind_word}: {who}"]
        if self.repo_words:
            parts[0] += f", {self.repo_words}"
        if extra:
            parts[0] += f", {extra}"
        text = parts[0]
        if self.description:
            text += f". {self.description.strip()}"
        return text

    def detail(self) -> str:
        lines = [f"{self.kind_word}: {self.login}"]
        if self.name:
            lines.append(f"Name: {self.name}")
        if self.description:
            lines.append(f"About: {self.description.strip()}")
        if self.public_repos is not None:
            lines.append(f"Public repositories: {self.public_repos:,}")
        if self.followers is not None:
            lines.append(f"Followers: {self.followers:,}")
        lines.append(self.page)
        return "\n".join(lines)


@dataclass(frozen=True)
class RepositoryHit:
    full_name: str
    description: str = ""
    stars: int = 0
    language: str = ""
    fork: bool = False
    archived: bool = False
    url: str = ""

    @property
    def page(self) -> str:
        return self.url or f"https://github.com/{self.full_name}"

    @property
    def label(self) -> str:
        bits = [self.full_name]
        if self.language:
            bits.append(self.language)
        bits.append(f"{self.stars:,} star{'' if self.stars == 1 else 's'}")
        if self.fork:
            bits.append("a fork")
        if self.archived:
            bits.append("archived")
        text = ", ".join(bits)
        return text + (f". {self.description.strip()}" if self.description else "")


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _count(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _kind(value: object) -> str:
    return KIND_ORGANIZATION if _text(value).casefold() == "organization" else KIND_PERSON


def _check_login(login: str) -> str:
    name = login.strip().lstrip("@")
    if not _LOGIN.match(name):
        raise AccountError(f"{login!r} is not a GitHub username or organization name.")
    return name


def _check_repo(repo: str) -> str:
    name = repo.strip()
    if not _REPO.match(name) or ".." in name:
        raise AccountError(f"{repo!r} is not a repository written as owner/name.")
    return name


def _failure(action: str, exc: GitHubRestError) -> AccountError:
    return AccountError(rest_failure_message(action, exc))


def _hit_from(data: Mapping[str, Any]) -> AccountHit | None:
    login = _text(data.get("login"))
    if not login:
        return None
    return AccountHit(
        login=login,
        kind=_kind(data.get("type")),
        name=_text(data.get("name")),
        description=_text(data.get("bio")) or _text(data.get("description")),
        public_repos=_count(data.get("public_repos")),
        followers=_count(data.get("followers")),
        url=_text(data.get("html_url")),
    )


def search_accounts(api: GitHubApi, text: str, *, limit: int = _PAGE) -> list[AccountHit]:
    """People and organizations matching *text*, best match first.

    Fewer than two characters is not a search (it would be every account whose
    login holds one letter), so it answers an empty list without a request.
    """
    wanted = " ".join(text.split())
    if len(wanted) < 2:
        return []
    try:
        reply = api.rest(
            "GET",
            "/search/users",
            query={"q": wanted, "per_page": str(max(1, min(limit, 50)))},
        )
    except GitHubRestError as exc:
        raise _failure("search GitHub for people and organizations", exc) from exc
    items = reply.data.get("items") if isinstance(reply.data, Mapping) else None
    found: list[AccountHit] = []
    for index, item in enumerate(items if isinstance(items, list) else []):
        if not isinstance(item, Mapping):
            continue
        hit = _hit_from(item)
        if hit is None:
            continue
        if index < ENRICH_LIMIT:
            hit = _enriched(api, hit)
        found.append(hit)
    return found


def _enriched(api: GitHubApi, hit: AccountHit) -> AccountHit:
    """*hit* with the name, bio and counts GitHub's profile gives; itself if that fails."""
    try:
        reply = api.rest("GET", f"/users/{quote(hit.login, safe='')}")
    except GitHubRestError:
        return hit
    if not isinstance(reply.data, Mapping):
        return hit
    fuller = _hit_from(reply.data)
    if fuller is None:
        return hit
    return AccountHit(
        login=hit.login,
        kind=fuller.kind or hit.kind,
        name=fuller.name,
        description=fuller.description,
        public_repos=fuller.public_repos,
        followers=fuller.followers,
        url=fuller.url or hit.url,
    )


def disambiguate(hits: list[AccountHit]) -> list[str]:
    """One label per hit, with the follower count added where two share a display name.

    "Jeff Bishop" is the name of more than one account; the login already tells
    them apart, but a listener reading a row hears the name first, so the rows
    that share a name or a look-alike login also say how many people follow them.
    """
    names: dict[str, int] = {}
    for hit in hits:
        for key in {hit.name.casefold(), hit.login.casefold()} - {""}:
            names[key] = names.get(key, 0) + 1
    labels = []
    for hit in hits:
        clash = (hit.name and names.get(hit.name.casefold(), 0) > 1) or any(
            other is not hit
            and other.login.casefold() != hit.login.casefold()
            and (
                other.name.casefold() == hit.login.casefold()
                or other.login.casefold().replace("-", "") == hit.login.casefold().replace("-", "")
            )
            for other in hits
        )
        extra = ""
        if clash and hit.followers is not None:
            extra = f"{hit.followers:,} follower{'' if hit.followers == 1 else 's'}"
        labels.append(hit.label(extra=extra))
    return labels


def list_repositories(
    api: GitHubApi, login: str, kind: str, *, limit: int = 50
) -> list[RepositoryHit]:
    """An account's public repositories, most recently pushed to first."""
    name = _check_login(login)
    base = "orgs" if kind == KIND_ORGANIZATION else "users"
    try:
        reply = api.rest(
            "GET",
            f"/{base}/{quote(name, safe='')}/repos",
            query={"per_page": str(max(1, min(limit, 100))), "sort": "pushed", "type": "owner"}
            if base == "users"
            else {"per_page": str(max(1, min(limit, 100))), "sort": "pushed", "type": "public"},
        )
    except GitHubRestError as exc:
        raise _failure(f"read the repositories of {name}", exc) from exc
    found = []
    for item in reply.data if isinstance(reply.data, list) else []:
        if not isinstance(item, Mapping) or not _text(item.get("full_name")):
            continue
        found.append(
            RepositoryHit(
                full_name=_text(item.get("full_name")),
                description=_text(item.get("description")),
                stars=_count(item.get("stargazers_count")) or 0,
                language=_text(item.get("language")),
                fork=bool(item.get("fork")),
                archived=bool(item.get("archived")),
                url=_text(item.get("html_url")),
            )
        )
    return found


def _state(api: GitHubApi, path: str, action: str) -> bool:
    """True when GitHub answers 204 for *path*, False for 404."""
    try:
        return api.rest("GET", path).status == 204
    except GitHubRestError as exc:
        if exc.status == 404:
            return False
        raise _failure(action, exc) from exc


def is_following(api: GitHubApi, login: str) -> bool:
    name = _check_login(login)
    return _state(
        api, f"/user/following/{quote(name, safe='')}", f"check whether you follow {name}"
    )


def is_starred(api: GitHubApi, repo: str) -> bool:
    name = _check_repo(repo)
    return _state(
        api, f"/user/starred/{quote(name, safe='/')}", f"check whether you starred {name}"
    )


def set_following(api: GitHubApi, hit: AccountHit, follow: bool) -> str:
    """Follow or unfollow a person, read the state back, and say what GitHub reports.

    An organization is refused before any request: GitHub documents following
    an organization only as a public preview, so the person is sent to the
    organization's page instead.
    """
    if hit.kind == KIND_ORGANIZATION:
        raise AccountError(
            f"QUILL does not follow organizations: GitHub documents that only as a public "
            f"preview. Use Open on GitHub for {hit.login} and press Follow there."
        )
    name = _check_login(hit.login)
    path = f"/user/following/{quote(name, safe='')}"
    verb = "follow" if follow else "unfollow"
    try:
        api.rest("PUT" if follow else "DELETE", path)
    except GitHubRestError as exc:
        raise _failure(f"{verb} {name}", exc) from exc
    now = _state(api, path, f"confirm that you {verb}ed {name}")
    if now == follow:
        return f"You now follow {name}." if follow else f"You no longer follow {name}."
    return (
        f"GitHub accepted the request, but reports that you still follow {name}."
        if now
        else f"GitHub accepted the request, but reports that you do not follow {name}."
    )


def set_starred(api: GitHubApi, repo: str, star: bool) -> str:
    """Star or unstar a repository, read the state back, and say what GitHub reports.

    A star is public: it appears on the person's GitHub profile. The sentence
    says so when it adds one, so a local favorite is never mistaken for it.
    """
    name = _check_repo(repo)
    path = f"/user/starred/{quote(name, safe='/')}"
    verb = "star" if star else "unstar"
    try:
        api.rest("PUT" if star else "DELETE", path)
    except GitHubRestError as exc:
        raise _failure(f"{verb} {name}", exc) from exc
    now = _state(api, path, f"confirm that you {verb}red {name}")
    if now == star:
        return (
            f"You starred {name} on GitHub. Your stars are public."
            if star
            else f"You removed your star from {name} on GitHub."
        )
    return (
        f"GitHub accepted the request, but reports that {name} is still starred."
        if now
        else f"GitHub accepted the request, but reports that {name} is not starred."
    )
