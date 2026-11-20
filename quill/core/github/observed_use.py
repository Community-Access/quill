"""What the Workbench saw an account use on this computer, for least-privilege advice.

Account > Roles and Access > Least Privilege Advice suggests the smallest
token and Workbench level that would cover what QUILL actually did. It can
only be as good as what was seen, so this module keeps that record:

* **Requests** sent through QUILL's REST transport, reduced to a method and
  an *area* (``GET repos/issues``, ``PUT repos/contents:workflows``): never a
  repository, a person, a number or a query, so the record names no object.
* **Refusals** (403) with GitHub's own ``X-Accepted-GitHub-Permissions``
  header, which is how a fine-grained token says what it lacked, and
  ``X-Accepted-OAuth-Scopes`` for a classic one.
* **Commands** that passed the write gate (:mod:`quill.core.github.write_gate`),
  with their tier: what the Workbench level has to allow.

Kept per account (the same one-way account key the navigation state uses,
never the token), in one JSON file in the app data folder, written atomically
and only when something *new* is seen, so a session of reading costs a write
or two, not one a request. It never changes a token or asks GitHub anything.

wx-free and strict-typed.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "ACCEPTED_PERMISSIONS",
    "ACCEPTED_SCOPES",
    "FILENAME",
    "OBSERVED_USE",
    "AccountUse",
    "ObservedUseTracker",
    "area_of",
    "observe_gated",
]

FILENAME = "github_observed_use.json"
ACCEPTED_PERMISSIONS = "X-Accepted-GitHub-Permissions"
ACCEPTED_SCOPES = "X-Accepted-OAuth-Scopes"

#: Path roots whose second segment is an owner (and, for repos, a third a name).
_OWNED = {"repos": 3, "orgs": 2, "users": 2, "enterprises": 2}


def area_of(path: str) -> str:
    """The part of GitHub a path is about, with no object named in it.

    ``/repos/o/r/issues/5/comments`` is ``repos/issues``; ``/repos/o/r`` is
    ``repos``; a workflow file is ``repos/contents:workflows``; ``/user/keys``
    is ``user/keys``; ``/gists/abc`` is ``gists``.
    """
    parts = [p for p in path.split("?", 1)[0].split("/") if p]
    if not parts:
        return ""
    root = parts[0]
    if root in _OWNED:
        rest = parts[_OWNED[root] :]
    elif root in ("gists", "teams", "projects"):
        rest = parts[2:]  # past the object's id
    else:
        rest = parts[1:]
    sub = rest[0] if rest else ""
    if sub.isdigit():
        sub = ""
    if root == "repos" and sub == "contents" and parts[4:6] == [".github", "workflows"]:
        sub = "contents:workflows"
    return f"{root}/{sub}" if sub else root


@dataclass
class AccountUse:
    """One account's record: since when, the requests, the refusals and the commands."""

    since: float = 0.0
    requests: set[str] = field(default_factory=set)  # "GET repos/issues"
    refused: dict[str, str] = field(default_factory=dict)  # "PATCH repos/issues" -> "issues=write"
    commands: dict[str, int] = field(default_factory=dict)  # command id -> tier

    @property
    def empty(self) -> bool:
        return not (self.requests or self.refused or self.commands)

    def as_json(self) -> dict[str, object]:
        return {
            "since": self.since,
            "requests": sorted(self.requests),
            "refused": dict(sorted(self.refused.items())),
            "commands": dict(sorted(self.commands.items())),
        }

    @classmethod
    def from_json(cls, raw: object) -> AccountUse:
        if not isinstance(raw, Mapping):
            return cls()
        refused = raw.get("refused")
        commands = raw.get("commands")
        requests = raw.get("requests")
        try:
            since = float(raw.get("since") or 0.0)
        except (TypeError, ValueError):
            since = 0.0
        return cls(
            since,
            {str(r) for r in requests} if isinstance(requests, list) else set(),
            {str(k): str(v) for k, v in refused.items()} if isinstance(refused, Mapping) else {},
            {
                str(k): int(v)
                for k, v in (commands.items() if isinstance(commands, Mapping) else ())
                if isinstance(v, int)
            },
        )


class ObservedUseTracker:
    """The process-wide recorder the transport and the write gate report to (any thread)."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._loaded: dict[str, dict[str, AccountUse]] = {}

    def _file(self) -> Path:
        return self._path or (app_data_dir() / FILENAME)

    def _accounts(self, where: Path) -> dict[str, AccountUse]:
        key = str(where)
        if key not in self._loaded:
            raw = read_json(where, default={})
            accounts = raw.get("accounts", {}) if isinstance(raw, dict) else {}
            self._loaded[key] = {
                str(name): AccountUse.from_json(value)
                for name, value in (accounts.items() if isinstance(accounts, dict) else ())
            }
        return self._loaded[key]

    def _change(self, token: str | None, change: Callable[[AccountUse], bool]) -> None:
        """Apply *change* (a callable on the account's record) and save if it said it changed."""
        if not token:
            return
        from quill.core.github.navigation_state import account_key_for_token

        account = account_key_for_token(token)
        where = self._file()
        with self._lock:
            accounts = self._accounts(where)
            use = accounts.setdefault(account, AccountUse())
            if not change(use):
                return
            use.since = use.since or time.time()
            snapshot = {name: one.as_json() for name, one in sorted(accounts.items())}
        try:
            write_json_atomic(where, {"schema_version": 1, "accounts": snapshot})
        except OSError:
            pass  # a record that cannot be written must never break a request

    def observe_reply(
        self, token: str | None, method: str, path: str, status: int, headers: object
    ) -> None:
        """One reply: a request seen, or a refusal with what GitHub said it wanted."""
        from quill.core.github.token_health import header_value

        area = area_of(path)
        if not area:
            return
        what = f"{method.upper()} {area}"
        if status == 403:
            wanted = (
                header_value(headers, ACCEPTED_PERMISSIONS)
                or header_value(headers, ACCEPTED_SCOPES)
                or ""
            ).strip()

            def refused(use: AccountUse) -> bool:
                if use.refused.get(what) == wanted:
                    return False
                use.refused[what] = wanted
                return True

            self._change(token, refused)
            return
        if 200 <= status < 300 or status == 304:

            def seen(use: AccountUse) -> bool:
                if what in use.requests:
                    return False
                use.requests.add(what)
                return True

            self._change(token, seen)

    def observe_command(self, token: str | None, command_id: str, tier: int) -> None:
        """A command that changes GitHub passed the write gate at *tier*."""

        def ran(use: AccountUse) -> bool:
            if use.commands.get(command_id) == tier:
                return False
            use.commands[command_id] = tier
            return True

        self._change(token, ran)

    def use_for(self, token: str | None) -> AccountUse:
        """A copy of what was seen for the account behind *token*."""
        if not token:
            return AccountUse()
        from quill.core.github.navigation_state import account_key_for_token

        with self._lock:
            found = self._accounts(self._file()).get(account_key_for_token(token))
            return AccountUse.from_json(found.as_json()) if found is not None else AccountUse()


OBSERVED_USE = ObservedUseTracker()
"""The one recorder every Workbench request and gated command reports to."""


def observe_gated(token: str | None, command_id: str) -> None:
    """Record *command_id* if it is a write the gate checks (its tier); a read records nothing."""
    from quill.core.github.write_gate import gated_tier

    tier = gated_tier(command_id)
    if tier is not None:
        OBSERVED_USE.observe_command(token, command_id, int(tier))
