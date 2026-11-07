"""Account-scoped local preferences for the GitHub attention queue."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_FILENAME = "github_attention_queue.json"
_REPOSITORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
QUEUE_CATEGORIES = (
    ("assigned", "Assigned to me"),
    ("review_requested", "Review requested"),
    ("mentioned", "Mentioned"),
    ("failed_checks", "Failed checks"),
)
_CATEGORY_KEYS = frozenset(key for key, _label in QUEUE_CATEGORIES)


@dataclass(frozen=True, slots=True)
class AttentionFilter:
    """A named, local-only queue scope."""

    name: str
    repositories: tuple[str, ...]
    categories: tuple[str, ...]


@dataclass(slots=True)
class GitHubAttentionQueue:
    """Selected repositories, saved filters, snoozes, and last-visit time."""

    account: str
    path: Path
    repositories: list[str]
    categories: list[str]
    snoozed: dict[str, str]
    filters: list[AttentionFilter]
    last_visit_at: str = ""

    @classmethod
    def load(cls, account: str, path: Path | None = None) -> GitHubAttentionQueue:
        target = path if path is not None else app_data_dir() / _FILENAME
        account_key = account.strip().casefold() or "anonymous"
        raw = read_json(target, default={})
        accounts = raw.get("accounts", {}) if isinstance(raw, dict) else {}
        saved = accounts.get(account_key, {}) if isinstance(accounts, dict) else {}
        if not isinstance(saved, dict):
            saved = {}
        repositories = _repositories(saved.get("repositories", []))
        categories = _categories(saved.get("categories", []))
        snoozed_raw = saved.get("snoozed", {})
        snoozed = (
            {
                key: value
                for key, value in snoozed_raw.items()
                if isinstance(key, str) and isinstance(value, str)
            }
            if isinstance(snoozed_raw, dict)
            else {}
        )
        filters_raw = saved.get("filters", [])
        filters: list[AttentionFilter] = []
        if isinstance(filters_raw, list):
            for item in filters_raw[:50]:
                if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                    continue
                name = item["name"].strip()
                if not name:
                    continue
                filters.append(
                    AttentionFilter(
                        name,
                        tuple(_repositories(item.get("repositories", []))),
                        tuple(_categories(item.get("categories", []))),
                    )
                )
        last_visit = saved.get("last_visit_at", "")
        return cls(
            account_key,
            target,
            repositories,
            categories or list(_CATEGORY_KEYS),
            snoozed,
            filters,
            last_visit if isinstance(last_visit, str) else "",
        )

    def save(self) -> None:
        raw = read_json(self.path, default={})
        data = raw if isinstance(raw, dict) else {}
        accounts = data.get("accounts", {})
        accounts = dict(accounts) if isinstance(accounts, dict) else {}
        accounts[self.account] = {
            "repositories": _repositories(self.repositories),
            "categories": _categories(self.categories),
            "snoozed": dict(self.snoozed),
            "filters": [asdict(item) for item in self.filters[:50]],
            "last_visit_at": self.last_visit_at,
        }
        write_json_atomic(self.path, {"accounts": accounts})

    def set_repositories(self, repositories: list[str]) -> None:
        invalid = [
            value.strip()
            for value in repositories
            if value.strip() and not _REPOSITORY.fullmatch(value.strip())
        ]
        if invalid:
            raise ValueError(f"Invalid repository name: {invalid[0]}. Use owner/repo.")
        cleaned = _repositories(repositories, limit=100)
        if len(cleaned) > 10:
            raise ValueError("Choose no more than 10 repositories for one attention queue.")
        self.repositories = cleaned

    def set_categories(self, categories: list[str]) -> None:
        self.categories = _categories(categories)

    def save_filter(self, name: str) -> bool:
        label = name.strip()
        if not label:
            return False
        self.filters = [item for item in self.filters if item.name.casefold() != label.casefold()]
        self.filters.insert(
            0, AttentionFilter(label, tuple(self.repositories), tuple(self.categories))
        )
        self.filters = self.filters[:50]
        self.save()
        return True

    def apply_filter(self, name: str) -> bool:
        item = next((f for f in self.filters if f.name.casefold() == name.casefold()), None)
        if item is None:
            return False
        self.repositories = list(item.repositories)
        self.categories = list(item.categories)
        self.save()
        return True

    def remove_filter(self, name: str) -> bool:
        before = len(self.filters)
        self.filters = [item for item in self.filters if item.name.casefold() != name.casefold()]
        if len(self.filters) == before:
            return False
        self.save()
        return True

    def snooze(self, key: str, until: datetime) -> None:
        if key.strip():
            if until.tzinfo is None:
                until = until.replace(tzinfo=UTC)
            self.snoozed[key] = until.astimezone(UTC).isoformat(timespec="seconds")
            self.save()

    def unsnooze(self, key: str) -> bool:
        if key not in self.snoozed:
            return False
        del self.snoozed[key]
        self.save()
        return True

    def is_snoozed(self, key: str, *, now: datetime | None = None) -> bool:
        value = self.snoozed.get(key)
        if value is None:
            return False
        try:
            until = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if until.tzinfo is None:
                until = until.replace(tzinfo=UTC)
        except ValueError:
            self.snoozed.pop(key, None)
            return False
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        if until <= current.astimezone(UTC):
            self.snoozed.pop(key, None)
            return False
        return True

    def mark_visited(self, when: datetime | None = None) -> None:
        value = when or datetime.now(UTC)
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        self.last_visit_at = value.astimezone(UTC).isoformat(timespec="seconds")
        self.save()

    def changed_since_last_visit(self, updated_at: str) -> bool:
        if not self.last_visit_at or not updated_at:
            return False
        try:
            last = datetime.fromisoformat(self.last_visit_at.replace("Z", "+00:00"))
            updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=UTC)
        return updated > last


def _repositories(values: Any, *, limit: int = 10) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        name = value.strip()
        folded = name.casefold()
        if _REPOSITORY.fullmatch(name) and folded not in seen:
            seen.add(folded)
            result.append(name)
    return result[:limit]


def _categories(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return list(
        dict.fromkeys(
            value for value in values if isinstance(value, str) and value in _CATEGORY_KEYS
        )
    )


__all__ = ["AttentionFilter", "GitHubAttentionQueue", "QUEUE_CATEGORIES"]
