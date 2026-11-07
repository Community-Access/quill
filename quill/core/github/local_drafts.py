"""Private, account-scoped local drafts for GitHub workbench actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.github.navigation_state import account_key_for_token
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_FILENAME = "github_local_drafts.json"
_MAX_ACCOUNTS = 32
_MAX_REPOSITORY_DRAFTS = 100
_MAX_BODY_CHARS = 50_000


@dataclass(frozen=True, slots=True)
class GitHubIssueDraftData:
    """A local issue draft. It contains no credential or submission state."""

    title: str = ""
    body: str = ""
    labels: tuple[str, ...] = ()
    assignees: tuple[str, ...] = ()
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class GitHubReviewDraftData:
    """A local pull-request review draft pinned to the head SHA it describes."""

    event: str = "comment"
    body: str = ""
    head_sha: str = ""
    updated_at: str = ""


def _repository(value: object) -> str:
    if not isinstance(value, str):
        return ""
    parts = value.strip().split("/")
    if len(parts) != 2 or not all(parts):
        return ""
    if any(ch.isspace() or ch in "?#@\\" for ch in value):
        return ""
    return value.strip()[:200]


def _bounded_text(value: object, limit: int) -> str:
    return value[:limit] if isinstance(value, str) else ""


def _string_values(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        return ()
    return tuple(
        text[:100] for item in value[:20] if isinstance(item, str) and (text := item.strip())
    )


def _draft(value: object) -> GitHubIssueDraftData | None:
    if not isinstance(value, dict):
        return None
    return GitHubIssueDraftData(
        title=_bounded_text(value.get("title"), 256),
        body=_bounded_text(value.get("body"), _MAX_BODY_CHARS),
        labels=_string_values(value.get("labels")),
        assignees=_string_values(value.get("assignees")),
        updated_at=_bounded_text(value.get("updated_at"), 40),
    )


def _review_draft(value: object) -> GitHubReviewDraftData | None:
    if not isinstance(value, dict):
        return None
    event = value.get("event", "comment")
    if event not in {"approve", "request changes", "comment"}:
        event = "comment"
    return GitHubReviewDraftData(
        event=event,
        body=_bounded_text(value.get("body"), _MAX_BODY_CHARS),
        head_sha=_bounded_text(value.get("head_sha"), 64),
        updated_at=_bounded_text(value.get("updated_at"), 40),
    )


class GitHubIssueDraftStore:
    """Read and update this account's issue and review drafts without its token."""

    def __init__(
        self,
        path: Path,
        account_key: str,
        accounts: dict[str, Any],
    ) -> None:
        self.path = path
        self.account_key = account_key
        self._accounts = accounts
        account = accounts.get(account_key, {})
        drafts = account.get("issue_drafts", {}) if isinstance(account, dict) else {}
        self._drafts = dict(drafts) if isinstance(drafts, dict) else {}
        review_drafts = account.get("review_drafts", {}) if isinstance(account, dict) else {}
        self._review_drafts = dict(review_drafts) if isinstance(review_drafts, dict) else {}

    @classmethod
    def load(cls, token: str | None) -> GitHubIssueDraftStore:
        path = app_data_dir() / _FILENAME
        raw = read_json(path, default={})
        accounts = raw.get("accounts", {}) if isinstance(raw, dict) else {}
        if not isinstance(accounts, dict):
            accounts = {}
        return cls(path, account_key_for_token(token), accounts)

    def get_issue(self, repository: str) -> GitHubIssueDraftData | None:
        normalized = _repository(repository)
        if not normalized:
            return None
        return _draft(self._drafts.get(normalized.casefold()))

    def save_issue(
        self,
        repository: str,
        *,
        title: str,
        body: str,
        labels: tuple[str, ...],
        assignees: tuple[str, ...],
    ) -> bool:
        normalized = _repository(repository)
        if not normalized:
            return False
        entry = asdict(
            GitHubIssueDraftData(
                title=_bounded_text(title, 256),
                body=_bounded_text(body, _MAX_BODY_CHARS),
                labels=_string_values(labels),
                assignees=_string_values(assignees),
                updated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            )
        )
        drafts = dict(self._drafts)
        drafts[normalized.casefold()] = entry
        if len(drafts) > _MAX_REPOSITORY_DRAFTS:
            drafts = dict(list(drafts.items())[-_MAX_REPOSITORY_DRAFTS:])
        return self._write(issue_drafts=drafts)

    def delete_issue(self, repository: str) -> bool:
        normalized = _repository(repository)
        if not normalized:
            return False
        key = normalized.casefold()
        if key not in self._drafts:
            return True
        drafts = dict(self._drafts)
        drafts.pop(key, None)
        return self._write(issue_drafts=drafts)

    def get_review(self, repository: str, number: int) -> GitHubReviewDraftData | None:
        key = self._review_key(repository, number)
        return _review_draft(self._review_drafts.get(key)) if key else None

    def save_review(
        self,
        repository: str,
        number: int,
        *,
        event: str,
        body: str,
        head_sha: str,
    ) -> bool:
        key = self._review_key(repository, number)
        if not key or event not in {"approve", "request changes", "comment"}:
            return False
        entry = asdict(
            GitHubReviewDraftData(
                event=event,
                body=_bounded_text(body, _MAX_BODY_CHARS),
                head_sha=_bounded_text(head_sha, 64),
                updated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            )
        )
        drafts = dict(self._review_drafts)
        drafts[key] = entry
        if len(drafts) > _MAX_REPOSITORY_DRAFTS:
            drafts = dict(list(drafts.items())[-_MAX_REPOSITORY_DRAFTS:])
        return self._write(review_drafts=drafts)

    def delete_review(self, repository: str, number: int) -> bool:
        key = self._review_key(repository, number)
        if not key:
            return False
        if key not in self._review_drafts:
            return True
        drafts = dict(self._review_drafts)
        drafts.pop(key, None)
        return self._write(review_drafts=drafts)

    @staticmethod
    def _review_key(repository: str, number: int) -> str:
        normalized = _repository(repository)
        if not normalized or number <= 0:
            return ""
        return f"{normalized.casefold()}#{number}"

    def _write(
        self,
        *,
        issue_drafts: dict[str, Any] | None = None,
        review_drafts: dict[str, Any] | None = None,
    ) -> bool:
        account = self._accounts.get(self.account_key, {})
        account_data = dict(account) if isinstance(account, dict) else {}
        issue_value = issue_drafts if issue_drafts is not None else self._drafts
        review_value = review_drafts if review_drafts is not None else self._review_drafts
        account_data["issue_drafts"] = issue_value
        account_data["review_drafts"] = review_value
        accounts = dict(self._accounts)
        accounts[self.account_key] = account_data
        if len(accounts) > _MAX_ACCOUNTS:
            accounts = dict(list(accounts.items())[-_MAX_ACCOUNTS:])
        try:
            write_json_atomic(self.path, {"accounts": accounts})
        except OSError:
            return False
        self._accounts = accounts
        self._drafts = issue_value
        self._review_drafts = review_value
        return True


__all__ = [
    "GitHubIssueDraftData",
    "GitHubIssueDraftStore",
    "GitHubReviewDraftData",
]
