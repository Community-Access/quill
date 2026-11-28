"""Tracked accounts and local favorites: this computer's shortcuts to GitHub accounts.

Two lists, kept per signed-in account in one small file, and **neither sends
anything to GitHub**:

* **Tracked accounts**: people and organizations you chose to keep in
  People > Tracked Accounts, so the next visit is one Enter rather than a search.
* **Favorites**: a second, separate mark. An account can be tracked without
  being a favorite, and a favorite account is always also tracked (it would have
  nowhere to live otherwise). A **favorite repository** is a repository you
  want one keystroke away; it need not be starred.

The words matter and are kept distinct everywhere they appear. A QUILL favorite
is a local shortcut. A GitHub star is a public action (``account_discovery.py``).
A GitHub List is GitHub's own collection (``star_lists.py``). Watching a
repository subscribes to its activity. Marking a favorite here changes none of
those, and no sentence in this module says "star", "follow" or "watch".

Written with :func:`~quill.core.storage.write_json_atomic`, version stamped;
no token and no fetched content, only logins, names and ``owner/name`` text.
An unreadable file reads as empty, never as a crash. wx-free and strict-typed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.github.account_discovery import KIND_ORGANIZATION, KIND_PERSON, AccountHit
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = ["MAX_ENTRIES", "TrackedAccount", "TrackedAccounts"]

_VERSION = 1
#: Plenty for a person's circle; a bound so a runaway loop cannot grow the file.
MAX_ENTRIES = 500


@dataclass(frozen=True)
class TrackedAccount:
    login: str
    kind: str = KIND_PERSON
    name: str = ""
    description: str = ""
    favorite: bool = False

    @property
    def kind_word(self) -> str:
        return "Organization" if self.kind == KIND_ORGANIZATION else "Person"

    @property
    def label(self) -> str:
        who = self.login + (f" ({self.name})" if self.name and self.name != self.login else "")
        kind = f"Favorite {self.kind_word.lower()}" if self.favorite else self.kind_word
        return f"{kind}: {who}"

    @property
    def page(self) -> str:
        return f"https://github.com/{self.login}"


def _key(login: str) -> str:
    return login.strip().lstrip("@").casefold()


def _repo_key(repo: str) -> str:
    return repo.strip().casefold()


@dataclass
class TrackedAccounts:
    path: Path
    accounts: dict[str, TrackedAccount] = field(default_factory=dict)
    favorite_repositories: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, account_key: str, *, data_dir: Path | None = None) -> TrackedAccounts:
        digest = hashlib.sha256(account_key.encode("utf-8")).hexdigest()[:32]
        path = (data_dir or app_data_dir()) / f"github_tracked_accounts_{digest}.json"
        raw = read_json(path, default={})
        store = cls(path)
        if not isinstance(raw, dict):
            return store
        for entry in raw.get("accounts", []) if isinstance(raw.get("accounts"), list) else []:
            if not isinstance(entry, dict):
                continue
            login = str(entry.get("login", "")).strip()
            if not login or _key(login) in store.accounts:
                continue
            kind = KIND_ORGANIZATION if entry.get("kind") == KIND_ORGANIZATION else KIND_PERSON
            store.accounts[_key(login)] = TrackedAccount(
                login,
                kind,
                str(entry.get("name", "")),
                str(entry.get("description", "")),
                bool(entry.get("favorite")),
            )
        repos = raw.get("favorite_repositories")
        for repo in repos if isinstance(repos, list) else []:
            text = str(repo).strip()
            if "/" in text and _repo_key(text) not in {
                _repo_key(r) for r in store.favorite_repositories
            }:
                store.favorite_repositories.append(text)
        return store

    # -- reading -----------------------------------------------------------------

    def listed(self) -> list[TrackedAccount]:
        """Favorites first, then the rest, each group by login."""
        return sorted(self.accounts.values(), key=lambda a: (not a.favorite, a.login.casefold()))

    def get(self, login: str) -> TrackedAccount | None:
        return self.accounts.get(_key(login))

    def is_tracked(self, login: str) -> bool:
        return _key(login) in self.accounts

    def is_favorite(self, login: str) -> bool:
        found = self.get(login)
        return bool(found and found.favorite)

    def is_favorite_repository(self, repo: str) -> bool:
        return _repo_key(repo) in {_repo_key(r) for r in self.favorite_repositories}

    # -- changing (each returns the sentence to say; nothing is sent to GitHub) --

    def track(self, hit: AccountHit) -> str:
        if self.is_tracked(hit.login):
            return f"{hit.login} is already in your Tracked Accounts."
        if len(self.accounts) >= MAX_ENTRIES:
            return f"Tracked Accounts holds {MAX_ENTRIES} accounts; remove one first."
        self.accounts[_key(hit.login)] = TrackedAccount(
            hit.login, hit.kind, hit.name, hit.description, False
        )
        self.save()
        return f"Added {hit.login} to your Tracked Accounts. This is a list on this computer only."

    def untrack(self, login: str) -> str:
        found = self.accounts.pop(_key(login), None)
        if found is None:
            return f"{login} was not in your Tracked Accounts."
        self.save()
        return f"Removed {found.login} from your Tracked Accounts."

    def set_favorite(self, hit: AccountHit, favorite: bool) -> str:
        found = self.get(hit.login)
        if found is None:
            if not favorite:
                return f"{hit.login} is not a favorite."
            if len(self.accounts) >= MAX_ENTRIES:
                return f"Tracked Accounts holds {MAX_ENTRIES} accounts; remove one first."
            found = TrackedAccount(hit.login, hit.kind, hit.name, hit.description)
        self.accounts[_key(hit.login)] = TrackedAccount(
            found.login,
            found.kind,
            found.name or hit.name,
            found.description or hit.description,
            favorite,
        )
        self.save()
        if favorite:
            return (
                f"{hit.login} is now a favorite, and in your Tracked Accounts. "
                "A favorite is a shortcut on this computer; GitHub is not told."
            )
        return f"{hit.login} is no longer a favorite. It stays in your Tracked Accounts."

    def set_favorite_repository(self, repo: str, favorite: bool) -> str:
        name = repo.strip()
        if "/" not in name:
            return f"{repo} is not a repository written as owner/name."
        have = self.is_favorite_repository(name)
        if favorite and not have:
            if len(self.favorite_repositories) >= MAX_ENTRIES:
                return f"Favorites hold {MAX_ENTRIES} repositories; remove one first."
            self.favorite_repositories.append(name)
            self.save()
            return f"{name} is now a favorite on this computer. That does not star it on GitHub."
        if not favorite and have:
            self.favorite_repositories = [
                r for r in self.favorite_repositories if _repo_key(r) != _repo_key(name)
            ]
            self.save()
            return f"{name} is no longer a favorite on this computer."
        return f"{name} is {'already' if favorite else 'not'} a favorite on this computer."

    def save(self) -> None:
        write_json_atomic(
            self.path,
            {
                "version": _VERSION,
                "accounts": [
                    {
                        "login": a.login,
                        "kind": a.kind,
                        "name": a.name,
                        "description": a.description,
                        "favorite": a.favorite,
                    }
                    for a in self.listed()
                ],
                "favorite_repositories": self.favorite_repositories,
            },
        )
