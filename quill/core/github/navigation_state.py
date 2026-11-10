"""Per-account local resume state for the shared GitHub Items workbench."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_FILENAME = "github_items_context.json"
_MAX_ACCOUNTS = 32
_MAX_HISTORY = 100


@dataclass(frozen=True, slots=True)
class GitHubItemsContext:
    """The last local view, filter, and selected row; no credential is stored."""

    repository: str = ""
    view: str = "issues"
    show: str = "both"
    state: str = "open"
    sort: str = "number_desc"
    search_query: str = ""
    quick_filter_query: str = ""
    selected_key: str = ""
    drill_branch: str = ""


def account_key_for_token(token: str | None) -> str:
    """Return a stable local account key without retaining the credential."""
    if not token:
        return "anonymous"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"token-{digest[:32]}"


def _valid_repository(value: object) -> str:
    if not isinstance(value, str):
        return ""
    owner_repo = value.strip()
    parts = owner_repo.split("/")
    if len(parts) != 2 or not all(parts) or any(ch.isspace() for ch in owner_repo):
        return ""
    if any(ch in owner_repo for ch in "?#@\\"):
        return ""
    return owner_repo[:200]


def _context(value: object) -> GitHubItemsContext:
    if not isinstance(value, dict):
        return GitHubItemsContext()
    allowed_views = {"issues", "branches", "commits", "tags", "releases", "workflows", "runs"}
    raw_view = value.get("view")
    view = raw_view if isinstance(raw_view, str) and raw_view in allowed_views else "issues"
    raw_show = value.get("show")
    show = (
        raw_show if isinstance(raw_show, str) and raw_show in {"both", "issues", "prs"} else "both"
    )
    raw_state = value.get("state")
    state = (
        raw_state
        if isinstance(raw_state, str) and raw_state in {"open", "closed", "all"}
        else "open"
    )
    return GitHubItemsContext(
        repository=_valid_repository(value.get("repository")),
        view=view,
        show=show,
        state=state,
        sort=str(value.get("sort", "number_desc"))[:32],
        search_query=str(value.get("search_query", ""))[:512],
        quick_filter_query=str(value.get("quick_filter_query", ""))[:512],
        selected_key=str(value.get("selected_key", ""))[:256],
        drill_branch=str(value.get("drill_branch", ""))[:256],
    )


class GitHubNavigationState:
    """Store one account's most recent Items view on this computer."""

    def __init__(
        self,
        path: Path,
        account_key: str,
        accounts: dict[str, Any],
        context: GitHubItemsContext,
        history: list[GitHubItemsContext],
        history_index: int,
    ):
        self.path = path
        self.account_key = account_key
        self._accounts = accounts
        self.context = context
        self.history = history[-_MAX_HISTORY:]
        self.history_index = (
            min(max(history_index, 0), len(self.history) - 1) if self.history else -1
        )

    @classmethod
    def load(cls, token: str | None) -> GitHubNavigationState:
        path = app_data_dir() / _FILENAME
        raw = read_json(path, default={})
        accounts = raw.get("accounts", {}) if isinstance(raw, dict) else {}
        if not isinstance(accounts, dict):
            accounts = {}
        key = account_key_for_token(token)
        account = accounts.get(key, {})
        context = _context(account)
        history_values = account.get("history", []) if isinstance(account, dict) else []
        history = (
            [_context(value) for value in history_values if isinstance(value, dict)][-_MAX_HISTORY:]
            if isinstance(history_values, list)
            else []
        )
        history_index = (
            account.get("history_index", len(history) - 1) if isinstance(account, dict) else -1
        )
        if isinstance(history_index, bool) or not isinstance(history_index, int):
            history_index = len(history) - 1
        return cls(path, key, accounts, context, history, history_index)

    @property
    def can_go_back(self) -> bool:
        return self.history_index > 0

    @property
    def can_go_forward(self) -> bool:
        return 0 <= self.history_index < len(self.history) - 1

    def record(self, context: GitHubItemsContext) -> None:
        """Append one local location; a new choice after Back drops the old forward path."""
        value = _context(asdict(context))
        if (
            0 <= self.history_index < len(self.history)
            and self.history[self.history_index] == value
        ):
            self.context = value
            return
        history = self.history[: self.history_index + 1] if self.history_index >= 0 else []
        history.append(value)
        if len(history) > _MAX_HISTORY:
            history = history[-_MAX_HISTORY:]
        self.history = history
        self.history_index = len(history) - 1
        self.context = value

    def back(self) -> GitHubItemsContext | None:
        if not self.can_go_back:
            return None
        self.history_index -= 1
        self.context = self.history[self.history_index]
        return self.context

    def forward(self) -> GitHubItemsContext | None:
        if not self.can_go_forward:
            return None
        self.history_index += 1
        self.context = self.history[self.history_index]
        return self.context

    def save(self, context: GitHubItemsContext) -> bool:
        value = _context(asdict(context))
        if not self.history or self.history[self.history_index] != value:
            self.record(value)
            value = self.context
        accounts = dict(self._accounts)
        account_data = asdict(value)
        account_data["history"] = [asdict(location) for location in self.history]
        account_data["history_index"] = self.history_index
        previous = self._accounts.get(self.account_key)
        if isinstance(previous, dict) and isinstance(previous.get(_WORKBENCH), dict):
            account_data[_WORKBENCH] = previous[_WORKBENCH]  # the Workbench's place survives
        accounts[self.account_key] = account_data
        if len(accounts) > _MAX_ACCOUNTS:
            accounts = dict(list(accounts.items())[-_MAX_ACCOUNTS:])
        try:
            write_json_atomic(self.path, {"accounts": accounts})
        except OSError:
            return False
        self._accounts = accounts
        self.context = value
        return True


#: The Workbench window's place, inside each account's entry (GitHub PRD 3.1, 9).
_WORKBENCH = "workbench"
_MAX_EXPANDED = 200
_MAX_INSTANCES = 20

#: A node, as the Workbench names it: (template, key, instance).
Place = tuple[str, str, str]


@dataclass(frozen=True, slots=True)
class WorkbenchPlace:
    """Where the Workbench window was for one account: never a credential.

    *last* is the node that was selected, *expanded* the nodes that were open,
    and *repositories* and *people* the instances the tree showed, most
    recent first, so a big account never means re-expanding everything.
    """

    last: Place | None = None
    expanded: tuple[Place, ...] = ()
    repositories: tuple[str, ...] = ()
    people: tuple[str, ...] = ()


def _place(value: object) -> Place | None:
    if not isinstance(value, list | tuple) or len(value) != 3:
        return None
    if not all(isinstance(part, str) and len(part) <= 256 for part in value):
        return None
    return (str(value[0]), str(value[1]), str(value[2]))


def _names(value: object, *, repository: bool) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    found: list[str] = []
    for entry in value:
        name = _valid_repository(entry) if repository else str(entry).strip()[:100]
        if name and isinstance(entry, str) and name not in found:
            found.append(name)
    return tuple(found[:_MAX_INSTANCES])


def load_workbench_place(account_key: str, path: Path | None = None) -> WorkbenchPlace:
    """The Workbench's place for *account_key*, or an empty one."""
    raw = read_json(path or app_data_dir() / _FILENAME, default={})
    accounts = raw.get("accounts", {}) if isinstance(raw, dict) else {}
    account = accounts.get(account_key, {}) if isinstance(accounts, dict) else {}
    data = account.get(_WORKBENCH, {}) if isinstance(account, dict) else {}
    if not isinstance(data, dict):
        return WorkbenchPlace()
    expanded_raw = data.get("expanded", [])
    expanded = (
        tuple(p for p in (_place(v) for v in expanded_raw) if p is not None)[:_MAX_EXPANDED]
        if isinstance(expanded_raw, list)
        else ()
    )
    return WorkbenchPlace(
        last=_place(data.get("last")),
        expanded=expanded,
        repositories=_names(data.get("repositories"), repository=True),
        people=_names(data.get("people"), repository=False),
    )


def save_workbench_place(account_key: str, place: WorkbenchPlace, path: Path | None = None) -> bool:
    """Keep *place* for *account_key*, beside GitHub Items' resume state."""
    target = path or app_data_dir() / _FILENAME
    raw = read_json(target, default={})
    accounts = raw.get("accounts", {}) if isinstance(raw, dict) else {}
    if not isinstance(accounts, dict):
        accounts = {}
    account = (
        dict(accounts.get(account_key, {})) if isinstance(accounts.get(account_key), dict) else {}
    )
    account[_WORKBENCH] = {
        "last": list(place.last) if place.last else None,
        "expanded": [list(p) for p in place.expanded[:_MAX_EXPANDED]],
        "repositories": list(place.repositories[:_MAX_INSTANCES]),
        "people": list(place.people[:_MAX_INSTANCES]),
    }
    accounts = {k: v for k, v in accounts.items() if k != account_key}
    accounts[account_key] = account
    if len(accounts) > _MAX_ACCOUNTS:
        accounts = dict(list(accounts.items())[-_MAX_ACCOUNTS:])
    try:
        write_json_atomic(target, {"accounts": accounts})
    except OSError:
        return False
    return True


__all__ = [
    "GitHubItemsContext",
    "GitHubNavigationState",
    "WorkbenchPlace",
    "account_key_for_token",
    "load_workbench_place",
    "save_workbench_place",
]
