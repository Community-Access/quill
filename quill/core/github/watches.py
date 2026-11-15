"""Watches in the GitHub Workbench (PRD 22.5): tell me when something happens.

A watch is a saved rule, kept per account on this device:

- ``run``: a workflow run finishes on a repository, or on one branch of it;
- ``review``: a review arrives on a pull request;
- ``release``: a repository publishes a new release;
- ``comment``: an issue or pull request gets a new comment.

The Workbench checks them on the GitHub notification check's own cadence
(``poll_interval_minutes`` in Workbench Options, through
:func:`quill.core.github.workbench_prefs.github_monitor_policy`, never sooner
than :data:`MIN_MINUTES`), only after the GitHub network consent and only
while signed in. A check reads the repository's runs, the pull request's
reviews, the releases or the comments through
:class:`quill.core.github.workbench_api.GitHubApi`; it never reads or touches
the notifications inbox, so nothing is ever marked read by a watch.

The first check of a watch only learns what is already there, so adding a
watch never announces a repository's history. Every watch keeps when it was
last checked, and :func:`freshness` says it in words ("checked 3 minutes
ago"), so a quiet list never looks fresher than it is.

Stored in ``github_watches.json`` (schema-stamped, written atomically), one
list per account key. wx-free and strict-typed.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from quill.core.github.workbench_api import GitHubApi
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "FILENAME",
    "KINDS",
    "MIN_MINUTES",
    "SCHEMA_VERSION",
    "Watch",
    "WatchStore",
    "check_round",
    "check_watch",
    "due",
    "freshness",
    "parse_target",
]

FILENAME = "github_watches.json"
SCHEMA_VERSION = 1
MIN_MINUTES = 5
_SEEN_CAP = 200

#: Each kind, as the sentence the Add Watch choice shows.
KINDS: Mapping[str, str] = {
    "run": "A workflow run finishes on a repository or branch",
    "review": "A review arrives on a pull request",
    "release": "A repository publishes a new release",
    "comment": "An issue or pull request gets a new comment",
}

_REVIEW_WORDS = {
    "APPROVED": "approved",
    "CHANGES_REQUESTED": "requested changes on",
    "COMMENTED": "reviewed",
    "DISMISSED": "had a review dismissed on",
}


@dataclass(frozen=True)
class Watch:
    """One saved rule, and what its last check saw."""

    id: str
    kind: str
    repository: str
    branch: str = ""
    number: int = 0
    paused: bool = False
    primed: bool = False
    seen: tuple[str, ...] = ()
    last_checked: float = 0.0
    last_result: str = ""

    def describe(self) -> str:
        """The rule in words: "Runs finishing on owner/name, branch main"."""
        if self.kind == "run":
            where = f"{self.repository}, branch {self.branch}" if self.branch else self.repository
            return f"Runs finishing on {where}"
        if self.kind == "review":
            return f"Reviews on pull request {self.repository}#{self.number}"
        if self.kind == "release":
            return f"New releases in {self.repository}"
        return f"Comments on {self.repository}#{self.number}"

    def label(self, now: float | None = None) -> str:
        state = "Paused. " if self.paused else ""
        last = f" Last: {self.last_result}" if self.last_result else ""
        return f"{self.describe()}. {state}{freshness(self.last_checked, now)}.{last}".rstrip()

    def detail(self, now: float | None = None) -> str:
        lines = [
            self.describe() + ".",
            KINDS.get(self.kind, self.kind) + ".",
            "Paused: it is not checked until you resume it." if self.paused else "Active.",
            freshness(self.last_checked, now).capitalize() + ".",
        ]
        if self.last_result:
            lines.append(f"Last result: {self.last_result}")
        lines.append("Enter edits it, Delete removes it. Watches never mark notifications read.")
        return "\n".join(lines)

    def url(self) -> str:
        base = f"https://github.com/{self.repository}"
        return {
            "run": f"{base}/actions",
            "release": f"{base}/releases",
            "review": f"{base}/pull/{self.number}",
            "comment": f"{base}/issues/{self.number}",
        }.get(self.kind, base)


def freshness(last_checked: float, now: float | None = None) -> str:
    """When a watch was last checked, in words; "not checked yet" before the first."""
    if last_checked <= 0:
        return "not checked yet"
    seconds = max(0, int((time.time() if now is None else now) - last_checked))
    if seconds < 60:
        return "checked just now"
    for size, unit in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if seconds >= size:
            count = seconds // size
            return f"checked {count} {unit}{'' if count == 1 else 's'} ago"
    return "checked just now"  # pragma: no cover - the loop always returns


def parse_target(kind: str, text: str) -> tuple[str, str, int]:
    """(repository, branch, number) from what a person typed for *kind*.

    ``owner/name`` or ``owner/name branch`` for a run; ``owner/name`` for a
    release; ``owner/name#42`` (or a GitHub link) for a review or a comment.
    Raises :class:`ValueError` with the sentence to say when it does not fit.
    """
    raw = text.strip()
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if raw.lower().startswith(prefix):
            raw = raw[len(prefix) :]
    branch = ""
    if kind == "run" and " " in raw:
        raw, _, branch = raw.partition(" ")
        branch = branch.strip()
    number = 0
    for marker in ("#", "/pull/", "/issues/"):
        if marker in raw:
            raw, _, tail = raw.partition(marker)
            digits = tail.strip().split("/")[0].split("#")[0]
            number = int(digits) if digits.isdigit() else -1
            break
    parts = [p for p in raw.strip().strip("/").split("/") if p]
    if len(parts) != 2 or any(c in raw for c in " \\") or ".." in raw:
        raise ValueError("Type the repository as owner/name.")
    repository = "/".join(parts)
    if kind in ("review", "comment") and number <= 0:
        raise ValueError("Type the number too, as owner/name#42.")
    if kind not in ("review", "comment"):
        number = 0
    return repository, branch, number


def _from_raw(raw: Mapping[str, Any]) -> Watch | None:
    kind = str(raw.get("kind", ""))
    repository = str(raw.get("repository", ""))
    if kind not in KINDS or "/" not in repository:
        return None
    seen = raw.get("seen")
    number = raw.get("number", 0)
    return Watch(
        id=str(raw.get("id") or uuid.uuid4().hex),
        kind=kind,
        repository=repository,
        branch=str(raw.get("branch", "") or ""),
        number=number if isinstance(number, int) and not isinstance(number, bool) else 0,
        paused=bool(raw.get("paused", False)),
        primed=bool(raw.get("primed", False)),
        seen=tuple(str(s) for s in seen) if isinstance(seen, list) else (),
        last_checked=float(raw.get("last_checked", 0.0) or 0.0),
        last_result=str(raw.get("last_result", "") or ""),
    )


@dataclass
class WatchStore:
    """One account's watches, and when the last round ran."""

    account: str
    path: Path | None = None
    watches: list[Watch] = field(default_factory=list)
    last_round: float = 0.0

    def _file(self) -> Path:
        return self.path or (app_data_dir() / FILENAME)

    @classmethod
    def load(cls, account: str, path: Path | None = None) -> WatchStore:
        store = cls(account, path)
        raw = read_json(store._file(), default={})
        accounts = raw.get("accounts") if isinstance(raw, dict) else None
        mine = accounts.get(account) if isinstance(accounts, dict) else None
        if isinstance(mine, dict):
            rows = mine.get("watches")
            for item in rows if isinstance(rows, list) else ():
                watch = _from_raw(item) if isinstance(item, dict) else None
                if watch is not None:
                    store.watches.append(watch)
            store.last_round = float(mine.get("last_round", 0.0) or 0.0)
        return store

    def save(self) -> None:
        """Write this account's list atomically, keeping every other account's."""
        target = self._file()
        raw = read_json(target, default={})
        accounts = raw.get("accounts") if isinstance(raw, dict) else None
        others = dict(accounts) if isinstance(accounts, dict) else {}
        others[self.account] = {
            "watches": [{**asdict(w), "seen": list(w.seen)} for w in self.watches],
            "last_round": self.last_round,
        }
        write_json_atomic(target, {"schema_version": SCHEMA_VERSION, "accounts": others})

    def find(self, watch_id: str) -> Watch | None:
        return next((w for w in self.watches if w.id == watch_id), None)

    def add(self, kind: str, repository: str, branch: str = "", number: int = 0) -> Watch:
        if kind not in KINDS:
            raise ValueError(f"Unknown watch kind: {kind}.")
        watch = Watch(uuid.uuid4().hex, kind, repository, branch, number)
        self.watches.append(watch)
        return watch

    def replace(self, watch: Watch) -> None:
        self.watches = [watch if w.id == watch.id else w for w in self.watches]

    def remove(self, watch_id: str) -> bool:
        before = len(self.watches)
        self.watches = [w for w in self.watches if w.id != watch_id]
        return len(self.watches) != before


def due(store: WatchStore, minutes: int, *, now: Callable[[], float] = time.time) -> bool:
    """Whether a round is due: never sooner than :data:`MIN_MINUTES` after the last."""
    if not any(not w.paused for w in store.watches):
        return False
    return now() - store.last_round >= max(MIN_MINUTES, int(minutes)) * 60


def _rest_list(api: GitHubApi, path: str, query: Mapping[str, str]) -> list[dict[str, Any]]:
    data = api.rest("GET", path, query=query).data
    if isinstance(data, dict):
        for key in ("workflow_runs", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def _login(row: Mapping[str, Any]) -> str:
    user = row.get("user")
    return str(user.get("login", "")) if isinstance(user, dict) else ""


def _found(api: GitHubApi, watch: Watch) -> list[tuple[str, str]]:
    """(marker, sentence) for everything the watch can see now, oldest first."""
    repo = watch.repository
    if watch.kind == "run":
        query = {"status": "completed", "per_page": "20"}
        if watch.branch:
            query["branch"] = watch.branch
        rows = _rest_list(api, f"/repos/{repo}/actions/runs", query)
        return [
            (
                str(r.get("id", "")),
                f"{r.get('name') or 'A workflow'} finished on {r.get('head_branch') or repo}: "
                f"{str(r.get('conclusion') or 'done').replace('_', ' ')}, in {repo}.",
            )
            for r in reversed(rows)
        ]
    if watch.kind == "release":
        rows = _rest_list(api, f"/repos/{repo}/releases", {"per_page": "10"})
        return [
            (
                str(r.get("id", "")),
                f"New release in {repo}: {r.get('name') or r.get('tag_name') or 'untitled'}.",
            )
            for r in reversed(rows)
            if not r.get("draft")
        ]
    if watch.kind == "review":
        rows = _rest_list(api, f"/repos/{repo}/pulls/{watch.number}/reviews", {"per_page": "100"})
        return [
            (
                str(r.get("id", "")),
                f"{_login(r) or 'Someone'} "
                f"{_REVIEW_WORDS.get(str(r.get('state', '')), 'reviewed')} "
                f"pull request #{watch.number} in {repo}.",
            )
            for r in rows
            if str(r.get("state", "")) != "PENDING"
        ]
    rows = _rest_list(api, f"/repos/{repo}/issues/{watch.number}/comments", {"per_page": "100"})
    return [
        (str(r.get("id", "")), f"{_login(r) or 'Someone'} commented on #{watch.number} in {repo}.")
        for r in rows
    ]


def check_watch(
    api: GitHubApi, watch: Watch, *, now: Callable[[], float] = time.time
) -> tuple[Watch, list[str]]:
    """Check one watch; the updated watch and the sentences worth saying.

    The first check learns and says nothing. A failure keeps what was seen and
    records the reason as the last result, so the list says why it is stale.
    """
    try:
        found = _found(api, watch)
    except Exception as exc:  # noqa: BLE001 - one watch failing never stops the round
        reason = str(exc.args[0]) if exc.args else str(exc)
        return replace(watch, last_checked=now(), last_result=f"Could not check: {reason}"), []
    known = set(watch.seen)
    new = [(marker, said) for marker, said in found if marker and marker not in known]
    seen = (*watch.seen, *(marker for marker, _ in new))[-_SEEN_CAP:]
    said = [sentence for _, sentence in new] if watch.primed else []
    if len(said) > 3:
        said = [*said[:2], f"And {len(said) - 2} more for {watch.describe().lower()}."]
    if said:
        result = said[-1]
    elif watch.primed:
        result = "nothing new"
    else:
        result = "started watching"
    updated = replace(watch, primed=True, seen=tuple(seen), last_checked=now(), last_result=result)
    return updated, said


def check_round(
    api: GitHubApi,
    store: WatchStore,
    *,
    only: Iterable[str] | None = None,
    now: Callable[[], float] = time.time,
) -> list[str]:
    """Check every active watch (or those in *only*); the sentences, in order."""
    wanted = set(only) if only is not None else None
    said: list[str] = []
    for watch in list(store.watches):
        if watch.paused or (wanted is not None and watch.id not in wanted):
            continue
        updated, sentences = check_watch(api, watch, now=now)
        store.replace(updated)
        said.extend(sentences)
    if wanted is None:
        store.last_round = now()
    return said
