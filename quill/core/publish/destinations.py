"""Saved SFTP publishing destinations (no secrets on disk).

A destination names a server and folder a finished book (and its feed and
sidecars) is uploaded to. The record on disk carries **no password**: secrets
live in the Windows Credential Manager under a per-destination target name,
via the platform credential store. Persistence is the standard atomic-JSON
app-data pattern. wx-free, strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

_FILE_NAME = "publish_destinations.json"


@dataclass(slots=True)
class SftpDestination:
    """One server+folder to publish to; the password lives in the credential store."""

    name: str
    host: str
    username: str
    remote_dir: str
    port: int = 22
    #: Public URL that mirrors ``remote_dir`` (used to build enclosure links).
    url_base: str = ""

    @property
    def credential_target(self) -> str:
        """The Windows Credential Manager target name for this destination."""
        return f"quill:publish:sftp:{self.name}"


@dataclass(slots=True)
class DestinationStore:
    """All saved destinations."""

    destinations: list[SftpDestination] = field(default_factory=list)

    def find(self, name: str) -> SftpDestination | None:
        for destination in self.destinations:
            if destination.name == name:
                return destination
        return None


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_destinations(data_dir: Path) -> DestinationStore:
    """Read the saved destinations (an absent or broken file reads as empty)."""
    path = _store_path(data_dir)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DestinationStore()
    entries = raw.get("destinations") if isinstance(raw, dict) else None
    store = DestinationStore()
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        host = str(entry.get("host", "")).strip()
        if not name or not host:
            continue
        try:
            port = int(entry.get("port", 22))
        except (TypeError, ValueError):
            port = 22
        store.destinations.append(
            SftpDestination(
                name=name,
                host=host,
                username=str(entry.get("username", "")),
                remote_dir=str(entry.get("remote_dir", "")) or "/",
                port=port,
                url_base=str(entry.get("url_base", "")),
            )
        )
    return store


def save_destinations(data_dir: Path, store: DestinationStore) -> None:
    """Persist the destinations atomically (never any secret material)."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        _store_path(data_dir),
        {"destinations": [asdict(d) for d in store.destinations]},
    )
