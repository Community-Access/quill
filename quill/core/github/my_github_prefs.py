"""My GitHub's remembered choices: what to show, how to order it, how to group it.

Per account, in ``github_my_github.json`` in QUILL's data folder, schema-stamped
and coerced field by field on read, so a hand-edited or older file reads as the
defaults rather than failing. Preferences only: no token, no GitHub content.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "GROUPS",
    "KINDS",
    "SORTS",
    "MyGitHubPrefs",
    "load_prefs",
    "save",
]

_FILENAME = "github_my_github.json"
_VERSION = 1

#: Queue item kinds, in the order the spoken summary lists them.
KINDS: tuple[tuple[str, str], ...] = (
    ("notification", "Unread notifications"),
    ("assigned", "Assigned issues and pull requests"),
    ("review_request", "Review requests"),
    ("my_pull_request", "My pull requests that need action"),
)
SORTS: tuple[tuple[str, str], ...] = (
    ("newest", "Newest first"),
    ("oldest", "Oldest first"),
    ("repository", "By repository"),
)
GROUPS: tuple[tuple[str, str], ...] = (
    ("none", "No grouping"),
    ("repository", "By repository"),
    ("kind", "By kind"),
)

_KIND_KEYS = frozenset(key for key, _label in KINDS)
_SORT_KEYS = frozenset(key for key, _label in SORTS)
_GROUP_KEYS = frozenset(key for key, _label in GROUPS)


@dataclass(frozen=True, slots=True)
class MyGitHubPrefs:
    """What the person chose for the My GitHub list. Empty ``kinds`` means every kind."""

    kinds: tuple[str, ...] = ()
    repository: str = ""
    unread_only: bool = False
    sort: str = "newest"
    group: str = "none"

    @property
    def is_default(self) -> bool:
        return self == MyGitHubPrefs()


def _clean(raw: Any) -> MyGitHubPrefs:
    if not isinstance(raw, dict):
        return MyGitHubPrefs()
    kinds_raw = raw.get("kinds", [])
    kinds = (
        tuple(dict.fromkeys(k for k in kinds_raw if isinstance(k, str) and k in _KIND_KEYS))
        if isinstance(kinds_raw, list)
        else ()
    )
    repository = raw.get("repository", "")
    sort = raw.get("sort", "newest")
    group = raw.get("group", "none")
    return MyGitHubPrefs(
        # Naming every kind is the same as naming none.
        kinds=() if len(kinds) == len(_KIND_KEYS) else kinds,
        repository=repository.strip() if isinstance(repository, str) else "",
        unread_only=raw.get("unread_only") is True,
        sort=sort if isinstance(sort, str) and sort in _SORT_KEYS else "newest",
        group=group if isinstance(group, str) and group in _GROUP_KEYS else "none",
    )


def _path(path: Path | None) -> Path:
    return path if path is not None else app_data_dir() / _FILENAME


def _account_key(account: str) -> str:
    return account.strip().casefold() or "anonymous"


def load_prefs(account: str, path: Path | None = None) -> MyGitHubPrefs:
    """The account's saved choices, or the defaults when there are none or the file is damaged."""
    raw = read_json(_path(path), default={})
    accounts = raw.get("accounts", {}) if isinstance(raw, dict) else {}
    saved = accounts.get(_account_key(account), {}) if isinstance(accounts, dict) else {}
    return _clean(saved)


def save(account: str, prefs: MyGitHubPrefs, path: Path | None = None) -> None:
    """Remember *prefs* for *account*; other accounts' choices are kept as they were."""
    target = _path(path)
    raw = read_json(target, default={})
    accounts = raw.get("accounts", {}) if isinstance(raw, dict) else {}
    accounts = dict(accounts) if isinstance(accounts, dict) else {}
    clean = _clean({
        "kinds": list(prefs.kinds),
        "repository": prefs.repository,
        "unread_only": prefs.unread_only,
        "sort": prefs.sort,
        "group": prefs.group,
    })
    accounts[_account_key(account)] = {
        "kinds": list(clean.kinds),
        "repository": clean.repository,
        "unread_only": clean.unread_only,
        "sort": clean.sort,
        "group": clean.group,
    }
    write_json_atomic(target, {"version": _VERSION, "accounts": accounts})
