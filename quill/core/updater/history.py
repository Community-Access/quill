"""Update History: a plain record of what the updater did (plan 6.8).

One line of JSON per event in ``update-history.jsonl`` beside ``channels.json``
in the family folder, so one file answers "what happened to my apps" and each
app's Update History window shows its own rows. Appended, never rewritten; the
oldest lines are trimmed once the file passes :data:`MAX_EVENTS`.

Kinds: ``checked`` (manual checks only, to keep it short), ``downloaded``,
``installed``, ``failed``, ``channel_changed``, ``snapshot_saved``,
``held_back`` -- later phases add rollbacks and restores.

Nothing here leaves the computer. wx-free and strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

__all__ = [
    "KIND_LABELS",
    "MAX_EVENTS",
    "UpdateEvent",
    "history_path",
    "read_events",
    "record",
]

MAX_EVENTS = 500

_FILE_NAME = "update-history.jsonl"

#: What each kind reads as in the window's "What happened" column.
KIND_LABELS: dict[str, str] = {
    "checked": "Checked for updates",
    "downloaded": "Downloaded an update",
    "installed": "Installed an update",
    "failed": "Something went wrong",
    "channel_changed": "Changed release channel",
    "snapshot_saved": "Saved a copy of your settings",
    "held_back": "Held an update back",
    "stable_caught_up": "Stable caught up",
}


@dataclass(frozen=True)
class UpdateEvent:
    at: str
    app: str
    kind: str
    from_version: str = ""
    to_version: str = ""
    channel: str = ""
    detail: str = ""

    @property
    def what(self) -> str:
        return KIND_LABELS.get(self.kind, self.kind.replace("_", " ").capitalize())

    def when(self) -> str:
        """A local date and time a person can read: ``3 October 2026, 14:05``."""
        try:
            moment = datetime.fromisoformat(self.at.replace("Z", "+00:00")).astimezone()
        except ValueError:
            return self.at
        return f"{moment.day} {moment:%B %Y, %H:%M}"


def history_path() -> Path:
    from quill.core.updater.channels import family_dir

    return family_dir() / _FILE_NAME


def record(
    app: str,
    kind: str,
    *,
    from_version: str = "",
    to_version: str = "",
    channel: str = "",
    detail: str = "",
    path: Path | None = None,
    now: datetime | None = None,
) -> UpdateEvent:
    """Append one event. Never raises: history is a courtesy, not a gate."""
    event = UpdateEvent(
        at=(now or datetime.now(UTC)).isoformat(timespec="seconds"),
        app=app,
        kind=kind,
        from_version=from_version,
        to_version=to_version,
        channel=channel,
        detail=detail,
    )
    target = path or history_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        _trim(target)
    except OSError:
        pass
    return event


def _trim(target: Path) -> None:
    lines = target.read_text(encoding="utf-8").splitlines()
    if len(lines) <= MAX_EVENTS:
        return
    from quill.core.storage import write_text_atomic

    write_text_atomic(target, "\n".join(lines[-MAX_EVENTS:]) + "\n")


def read_events(app: str | None = None, path: Path | None = None) -> list[UpdateEvent]:
    """Events newest first, optionally for one app. Unreadable lines are skipped."""
    target = path or history_path()
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    events: list[UpdateEvent] = []
    for line in lines:
        try:
            raw = json.loads(line)
        except ValueError:
            continue
        if not isinstance(raw, dict):
            continue
        event = UpdateEvent(
            at=str(raw.get("at") or ""),
            app=str(raw.get("app") or ""),
            kind=str(raw.get("kind") or ""),
            from_version=str(raw.get("from_version") or ""),
            to_version=str(raw.get("to_version") or ""),
            channel=str(raw.get("channel") or ""),
            detail=str(raw.get("detail") or ""),
        )
        if app is None or event.app == app:
            events.append(event)
    events.reverse()
    return events
