"""Change History: every write the Workbench made, kept on this device (GitHub PRD 16.5, 18.5).

Account > Change History lists every write: when, which account, what object,
what changed before and after, the tier, and whether the re-read confirmed
it. Undo GitHub Change (Ctrl+Z in the list) reverses the newest one GitHub
allows, and the history's own Undo reverses any row it allows (GH-R-044,
GH-R-067).

- **Local and atomic:** one JSON file in the app data folder, written with
  :func:`quill.core.storage.write_json_atomic`.
- **Kept 90 days** by default, older entries pruned on load and on save, and
  clearable in one step.
- **Never a secret:** secret fields are write-only and never logged at all;
  every text that is logged passes the known-secret and token redaction first,
  so a token pasted into a title by mistake does not end up on disk twice.

wx-free and strict-typed.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic
from quill.core.workbench.properties import FieldChange

__all__ = [
    "FILENAME",
    "RETENTION_DAYS",
    "ChangeLog",
    "LoggedChange",
    "LoggedField",
]

FILENAME = "github_change_history.json"
RETENTION_DAYS = 90
_MAX_ENTRIES = 5000


def _clean(text: str) -> str:
    from quill.stability.redaction import redact_known_secrets, redact_source_tokens

    return redact_source_tokens(redact_known_secrets(text))


def _json_value(value: object) -> object:
    if isinstance(value, tuple):
        return [_clean(str(item)) for item in value]
    if isinstance(value, str):
        return _clean(value)
    if isinstance(value, (bool, int)) or value is None:
        return value
    return _clean(str(value))


def _from_json(value: object) -> object:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return value


@dataclass(frozen=True)
class LoggedField:
    key: str
    label: str
    before: object
    after: object


@dataclass(frozen=True)
class LoggedChange:
    """One write, as Change History shows it and Undo reads it."""

    when: float
    account: str
    kind: str
    ident: Mapping[str, str]
    target: str
    summary: str
    fields: tuple[LoggedField, ...] = ()
    tier: int = 0
    confirmed: bool = True
    can_undo: bool = True
    undone: bool = False

    def row_text(self) -> str:
        """The list row: "9 Nov 14:05, owner/name#42, added bug, confirmed"."""
        stamp = time.strftime("%d %b %Y %H:%M", time.localtime(self.when))
        state = "confirmed" if self.confirmed else "not confirmed by GitHub"
        undone = ", undone" if self.undone else ""
        undo = "" if self.can_undo else ", cannot be undone"
        return f"{stamp}, {self.target}, {self.summary}, {state}{undone}{undo}"

    def detail_text(self) -> str:
        lines = [self.row_text(), f"Account: {self.account or 'unknown'}", f"Tier: {self.tier}"]
        for item in self.fields:
            lines.append(f"{item.label}: before {_say(item.before)}; after {_say(item.after)}")
        return "\n".join(lines)

    def as_changes(self) -> list[FieldChange]:
        return [
            FieldChange(item.key, item.label, item.before, item.after)  # type: ignore[arg-type]
            for item in self.fields
        ]


def _say(value: object) -> str:
    if isinstance(value, tuple):
        return ", ".join(value) if value else "none"
    if value is None or value == "":
        return "none"
    return str(value)


def _entry(raw: Mapping[str, Any]) -> LoggedChange | None:
    try:
        ident = {str(k): str(v) for k, v in dict(raw.get("ident") or {}).items()}
        fields = tuple(
            LoggedField(
                str(item.get("key", "")),
                str(item.get("label", "")),
                _from_json(item.get("before")),
                _from_json(item.get("after")),
            )
            for item in raw.get("fields") or ()
            if isinstance(item, Mapping)
        )
        return LoggedChange(
            float(raw.get("when", 0.0)),
            str(raw.get("account", "")),
            str(raw.get("kind", "")),
            ident,
            str(raw.get("target", "")),
            str(raw.get("summary", "")),
            fields,
            int(raw.get("tier", 0)),
            bool(raw.get("confirmed", True)),
            bool(raw.get("can_undo", True)),
            bool(raw.get("undone", False)),
        )
    except (TypeError, ValueError):
        return None


def _raw(entry: LoggedChange) -> dict[str, object]:
    return {
        "when": entry.when,
        "account": entry.account,
        "kind": entry.kind,
        "ident": {k: _clean(v) for k, v in entry.ident.items()},
        "target": _clean(entry.target),
        "summary": _clean(entry.summary),
        "fields": [
            {
                "key": item.key,
                "label": item.label,
                "before": _json_value(item.before),
                "after": _json_value(item.after),
            }
            for item in entry.fields
        ],
        "tier": entry.tier,
        "confirmed": entry.confirmed,
        "can_undo": entry.can_undo,
        "undone": entry.undone,
    }


@dataclass
class ChangeLog:
    """The history file, newest last."""

    path: Path | None = None
    entries: list[LoggedChange] = field(default_factory=list)
    retention_days: int = RETENTION_DAYS

    def _file(self) -> Path:
        return self.path or (app_data_dir() / FILENAME)

    @classmethod
    def load(
        cls, path: Path | None = None, *, retention_days: int = RETENTION_DAYS, now: float = 0.0
    ) -> ChangeLog:
        log = cls(path, retention_days=retention_days)
        raw = read_json(log._file(), default={})
        rows = raw.get("entries", []) if isinstance(raw, dict) else []
        for item in rows if isinstance(rows, list) else ():
            entry = _entry(item) if isinstance(item, Mapping) else None
            if entry is not None:
                log.entries.append(entry)
        log.prune(now or time.time())
        return log

    def prune(self, now: float) -> int:
        """Drop entries older than the retention; return how many went."""
        oldest = now - self.retention_days * 86400
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.when >= oldest][-_MAX_ENTRIES:]
        return before - len(self.entries)

    def save(self) -> None:
        self.prune(time.time())
        write_json_atomic(
            self._file(), {"schema_version": 1, "entries": [_raw(e) for e in self.entries]}
        )

    def record(
        self,
        *,
        account: str,
        kind: str,
        ident: Mapping[str, str],
        target: str,
        summary: str,
        changes: Sequence[FieldChange],
        tier: int,
        confirmed: bool,
        can_undo: bool,
        when: float = 0.0,
    ) -> LoggedChange:
        entry = LoggedChange(
            when or time.time(),
            account,
            kind,
            dict(ident),
            target,
            summary,
            tuple(LoggedField(c.key, c.label, c.before, c.after) for c in changes),
            tier,
            confirmed,
            can_undo,
        )
        self.entries.append(entry)
        self.save()
        return entry

    def newest_undoable(self, account: str = "") -> int:
        """The index of the newest entry Undo can reverse, or -1."""
        for index in range(len(self.entries) - 1, -1, -1):
            entry = self.entries[index]
            if entry.can_undo and not entry.undone and (not account or entry.account == account):
                return index
        return -1

    def mark_undone(self, index: int) -> None:
        self.entries[index] = replace(self.entries[index], undone=True)
        self.save()

    def clear(self) -> None:
        self.entries.clear()
        self.save()

    def as_csv(self) -> str:
        """The whole history as CSV, for Save as CSV."""
        import csv
        import io

        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["when", "account", "object", "summary", "tier", "confirmed", "undone"])
        for entry in self.entries:
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M", time.localtime(entry.when)),
                entry.account,
                entry.target,
                entry.summary,
                entry.tier,
                "yes" if entry.confirmed else "no",
                "yes" if entry.undone else "no",
            ])
        return out.getvalue()
