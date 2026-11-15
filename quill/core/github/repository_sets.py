"""Repository Sets: named lists of repositories, per GitHub account (PRD 22.11).

Across Repositories (:mod:`quill.core.github.across`) reads one kind of thing
from the set in use, and every by-name sheet works over it. A set is made by
hand (a list of ``owner/name``) or by a filter (``org:Community-Access
topic:quillville``), which GitHub's repository search resolves each time the
set is used, so a new repository with that topic joins without anybody
editing the set. One file per account (the account key hashed, as
:mod:`quill.core.github.saved_items` does), written atomically; it holds
names and filters only -- never a token, never fetched content.

Version 1 files (``{"sets": {name: [repos]}}``) still load; the first save
writes version 2, which adds ``filters`` and ``current``.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "DEFAULT_SET",
    "EVERY",
    "MAX_REPOSITORIES",
    "MAX_SET_NAME",
    "RepositorySets",
    "normalize_repository",
    "normalize_set_name",
]

#: The set a first Choose Repositories fills.
DEFAULT_SET = "My Repositories"
#: Generous, but bounded: each repository costs one request per category.
MAX_REPOSITORIES = 200
MAX_SET_NAME = 80
#: The filter that means "every repository this account may read" (PRD 22.11's
#: widest scope): GitHub's own list of your repositories, bounded by
#: :data:`MAX_REPOSITORIES`, with the truncation said aloud.
EVERY = "@every"
_VERSION = 2
_NAME = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")


def normalize_repository(text: str) -> str:
    """``owner/name`` from a name or a github.com address; "" when it is neither."""
    value = text.strip().removesuffix("/").removesuffix(".git")
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix) :]
            break
    value = "/".join(value.split("/")[:2])
    return value if _NAME.match(value) else ""


def normalize_set_name(text: str) -> str:
    """A set's name, trimmed and bounded; "" when nothing printable is left."""
    return " ".join(text.split())[:MAX_SET_NAME]


def _clean(repositories: list[str]) -> tuple[list[str], list[str]]:
    clean: list[str] = []
    rejected: list[str] = []
    for text in repositories:
        if not text.strip():
            continue
        repo = normalize_repository(text)
        (clean if repo else rejected).append(repo or text.strip())
    unique: dict[str, str] = {}
    for repo in clean:
        unique.setdefault(repo.lower(), repo)  # adding a listed one checks it once
    return list(unique.values())[:MAX_REPOSITORIES], rejected


@dataclass
class RepositorySets:
    """The account's sets; :meth:`save` writes them back."""

    path: Path
    sets: dict[str, list[str]] = field(default_factory=dict)
    #: A filter-driven set's search (GitHub repository search syntax).
    filters: dict[str, str] = field(default_factory=dict)
    #: The set Across Repositories reads ("" means :data:`DEFAULT_SET`).
    current: str = ""

    @classmethod
    def load(cls, account_key: str, *, data_dir: Path | None = None) -> RepositorySets:
        digest = hashlib.sha256(account_key.encode("utf-8")).hexdigest()[:32]
        path = (data_dir or app_data_dir()) / f"github_repository_sets_{digest}.json"
        raw = read_json(path, default={})
        sets: dict[str, list[str]] = {}
        filters: dict[str, str] = {}
        current = ""
        if isinstance(raw, dict):
            stored = raw.get("sets")
            if isinstance(stored, dict):
                for name, repos in stored.items():
                    if isinstance(name, str) and isinstance(repos, list) and name.strip():
                        sets[name] = _clean([str(r) for r in repos])[0]
            stored_filters = raw.get("filters")
            if isinstance(stored_filters, dict):
                for name, text in stored_filters.items():
                    if isinstance(name, str) and isinstance(text, str) and text.strip():
                        filters[name] = text.strip()
                        sets.setdefault(name, [])
            chosen = raw.get("current")
            if isinstance(chosen, str) and chosen in sets:
                current = chosen
        return cls(path, sets, filters, current)

    # -- reading -----------------------------------------------------------------

    def names(self) -> list[str]:
        return sorted(self.sets, key=str.casefold)

    @property
    def current_name(self) -> str:
        """The set in use: the chosen one, else the default, else the first."""
        if self.current in self.sets:
            return self.current
        if DEFAULT_SET in self.sets or not self.sets:
            return DEFAULT_SET
        return self.names()[0]

    def repositories(self, name: str = "") -> list[str]:
        """*name*'s hand-made list (or a filter set's last resolution); default the current."""
        return list(self.sets.get(name or self.current_name, []))

    def filter_for(self, name: str = "") -> str:
        return self.filters.get(name or self.current_name, "")

    def describe(self, name: str = "") -> str:
        """One line for a set's row: what it is and how it is made."""
        name = name or self.current_name
        count = len(self.sets.get(name, []))
        mark = ", in use" if name == self.current_name else ""
        search = self.filters.get(name, "")
        if search == EVERY:
            return (
                f"{name}: every repository you can reach, up to {MAX_REPOSITORIES}, "
                f"{count} last time{mark}"
            )
        if search:
            return f"{name}: made by the filter {search}, {count} repositories last time{mark}"
        return f"{name}: {count} repositories, chosen by hand{mark}"

    # -- changing ----------------------------------------------------------------

    def set_repositories(self, name: str, repositories: list[str]) -> list[str]:
        """Replace *name*'s list, making it hand-made; returns what was not a repository."""
        clean, rejected = _clean(repositories)
        key = normalize_set_name(name) or DEFAULT_SET
        self.sets[key] = clean
        self.filters.pop(key, None)
        return rejected

    def set_filter(self, name: str, search: str) -> None:
        """Make *name* a filter-driven set; its list is filled by :meth:`resolved`."""
        key = normalize_set_name(name) or DEFAULT_SET
        self.filters[key] = search.strip()
        self.sets.setdefault(key, [])

    def resolved(self, name: str, repositories: list[str]) -> None:
        """Keep what a filter set's search found last, so its row can say how many."""
        self.sets[name] = _clean(repositories)[0]

    def choose(self, name: str) -> bool:
        if name not in self.sets:
            return False
        self.current = name
        return True

    def rename(self, old: str, new: str) -> str:
        """Rename a set; "" on success, else the sentence that says why not."""
        target = normalize_set_name(new)
        if old not in self.sets:
            return f"There is no set called {old}."
        if not target:
            return "A set needs a name."
        if target != old and target.casefold() in {n.casefold() for n in self.sets}:
            return f"There is already a set called {target}."
        self.sets = {target if k == old else k: v for k, v in self.sets.items()}
        if old in self.filters:
            self.filters[target] = self.filters.pop(old)
        if self.current == old:
            self.current = target
        return ""

    def delete(self, name: str) -> bool:
        self.filters.pop(name, None)
        if self.current == name:
            self.current = ""
        return self.sets.pop(name, None) is not None

    def save(self) -> None:
        write_json_atomic(
            self.path,
            {
                "version": _VERSION,
                "sets": self.sets,
                "filters": self.filters,
                "current": self.current,
            },
        )
