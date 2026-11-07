"""Pending line comments: kept on this device until they go out with a review.

A comment written on a line of a pull request's diff can be posted at once,
or added to the review the person is putting together. Added ones wait here,
per account and per pull request, pinned to the head revision they were
written against, and are sent in the same request as the review itself when
the person submits it from Compose Review. Nothing here holds a credential;
the account key is a one-way hash, as for the other workbench drafts.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.github.diff_lines import LineCommentAnchor
from quill.core.github.navigation_state import account_key_for_token
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_FILENAME = "github_line_comment_drafts.json"
_MAX_ACCOUNTS = 32
_MAX_PULLS = 100
_MAX_COMMENTS = 200
_MAX_BODY_CHARS = 50_000


@dataclass(frozen=True, slots=True)
class PendingLineComment:
    """One comment waiting for the review it belongs to."""

    id: str
    path: str
    line: int
    side: str
    body: str
    head_sha: str
    start_line: int = 0
    start_side: str = ""
    created_at: str = ""

    @property
    def anchor(self) -> LineCommentAnchor:
        return LineCommentAnchor(self.path, self.line, self.side, self.start_line, self.start_side)

    @property
    def label(self) -> str:
        """The outline row: where, then the first line of what it says."""
        first = next((part.strip() for part in self.body.splitlines() if part.strip()), "")
        if first.startswith("```suggestion"):
            first = "suggested change"
        return f"{self.anchor.describe()}: {first[:80]}"

    def review_payload(self) -> dict[str, object]:
        return {**self.anchor.payload(), "body": self.body}


def _int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def _comment(value: object) -> PendingLineComment | None:
    if not isinstance(value, dict):
        return None
    path = value.get("path")
    body = value.get("body")
    identifier = value.get("id")
    line = _int(value.get("line"))
    side = value.get("side")
    if (
        not isinstance(path, str)
        or not path
        or not isinstance(body, str)
        or not body.strip()
        or not isinstance(identifier, str)
        or not identifier
        or not line
        or side not in ("LEFT", "RIGHT")
    ):
        return None
    start_side = value.get("start_side")
    return PendingLineComment(
        id=identifier[:40],
        path=path[:1000],
        line=line,
        side=str(side),
        body=body[:_MAX_BODY_CHARS],
        head_sha=str(value.get("head_sha") or "")[:64],
        start_line=_int(value.get("start_line")),
        start_side=start_side if start_side in ("LEFT", "RIGHT") else "",
        created_at=str(value.get("created_at") or "")[:40],
    )


def _pull_key(repository: str, number: int) -> str:
    parts = repository.strip().split("/")
    if len(parts) != 2 or not all(parts) or number <= 0:
        return ""
    if any(ch.isspace() or ch in "?#@\\" for ch in repository.strip()):
        return ""
    return f"{repository.strip().casefold()[:200]}#{number}"


class LineCommentDraftStore:
    """This account's pending line comments, read and changed atomically."""

    def __init__(self, path: Path, account_key: str, accounts: dict[str, Any]) -> None:
        self.path = path
        self.account_key = account_key
        self._accounts = accounts

    @classmethod
    def load(cls, token: str | None, path: Path | None = None) -> LineCommentDraftStore:
        target = path if path is not None else app_data_dir() / _FILENAME
        raw = read_json(target, default={})
        accounts = raw.get("accounts", {}) if isinstance(raw, dict) else {}
        if not isinstance(accounts, dict):
            accounts = {}
        return cls(target, account_key_for_token(token), accounts)

    def _pulls(self) -> dict[str, Any]:
        account = self._accounts.get(self.account_key)
        pulls = account.get("pulls") if isinstance(account, dict) else None
        return dict(pulls) if isinstance(pulls, dict) else {}

    def pending(self, repository: str, number: int) -> tuple[PendingLineComment, ...]:
        key = _pull_key(repository, number)
        rows = self._pulls().get(key, []) if key else []
        if not isinstance(rows, list):
            return ()
        return tuple(comment for row in rows if (comment := _comment(row)) is not None)

    def add(
        self,
        repository: str,
        number: int,
        anchor: LineCommentAnchor,
        body: str,
        head_sha: str,
    ) -> PendingLineComment | None:
        """Keep a new pending comment; None when it cannot be saved."""
        key = _pull_key(repository, number)
        if not key or not body.strip() or anchor.line <= 0:
            return None
        comment = PendingLineComment(
            id=uuid.uuid4().hex[:16],
            path=anchor.path,
            line=anchor.line,
            side=anchor.side,
            body=body[:_MAX_BODY_CHARS],
            head_sha=head_sha[:64],
            start_line=anchor.start_line if anchor.is_range else 0,
            start_side=(anchor.start_side or anchor.side) if anchor.is_range else "",
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        existing = list(self.pending(repository, number))
        if len(existing) >= _MAX_COMMENTS:
            return None
        return comment if self._write(key, [*existing, comment]) else None

    def update(self, repository: str, number: int, comment_id: str, body: str) -> bool:
        key = _pull_key(repository, number)
        if not key or not body.strip():
            return False
        existing = list(self.pending(repository, number))
        if not any(comment.id == comment_id for comment in existing):
            return False
        changed = [
            replace(comment, body=body[:_MAX_BODY_CHARS]) if comment.id == comment_id else comment
            for comment in existing
        ]
        return self._write(key, changed)

    def remove(self, repository: str, number: int, comment_id: str) -> bool:
        key = _pull_key(repository, number)
        if not key:
            return False
        existing = list(self.pending(repository, number))
        kept = [comment for comment in existing if comment.id != comment_id]
        return len(kept) == len(existing) or self._write(key, kept)

    def clear(self, repository: str, number: int) -> bool:
        key = _pull_key(repository, number)
        return bool(key) and (not self.pending(repository, number) or self._write(key, []))

    def _write(self, key: str, comments: list[PendingLineComment]) -> bool:
        pulls = self._pulls()
        if comments:
            pulls.pop(key, None)
            pulls[key] = [asdict(comment) for comment in comments]
        else:
            pulls.pop(key, None)
        if len(pulls) > _MAX_PULLS:
            pulls = dict(list(pulls.items())[-_MAX_PULLS:])
        accounts = dict(self._accounts)
        accounts[self.account_key] = {"pulls": pulls}
        if len(accounts) > _MAX_ACCOUNTS:
            accounts = dict(list(accounts.items())[-_MAX_ACCOUNTS:])
        try:
            write_json_atomic(self.path, {"accounts": accounts})
        except OSError:
            return False
        self._accounts = accounts
        return True


__all__ = ["LineCommentDraftStore", "PendingLineComment"]
