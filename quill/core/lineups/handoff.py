"""Quill Cast asking Quill Radio to play Lineup rows it cannot play itself.

Cast plays podcast episodes; a Lineup can also hold stations, YouTube, Local
Media and recordings, which only Radio plays. Cast writes a small request file
naming the Lineup and the rows, then queues it for Radio through the family's
open-request queue (``quill.core.ipc``) with the action :data:`ACTION`; Radio
reads the rows from the shared ``lineups.json`` and plays them. No URL or other
content travels in the request: only which Lineup and which rows, so Radio plays
exactly what its own copy of the Lineup says.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

ACTION = "lineup_play"
FOLDER = "lineup-requests"
#: A request older than this is stale (Radio was not running for a long time).
MAX_AGE_SECONDS = 15 * 60


@dataclass(frozen=True, slots=True)
class PlayRequest:
    lineup_id: str
    tokens: tuple[str, ...]
    at: float


def write_request(
    data_dir: Path, lineup_id: str, tokens: list[str], *, now: float | None = None
) -> Path:
    """Write the request file and return its path (to hand to the open-request queue)."""
    from quill.core.storage import write_json_atomic

    folder = Path(data_dir) / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"play-{uuid.uuid4().hex[:12]}.json"
    write_json_atomic(path, {"lineup_id": lineup_id, "tokens": tokens, "at": now or time.time()})
    return path


def read_request(path: Path, *, now: float | None = None) -> PlayRequest | None:
    """The request in *path*, consumed (the file is removed); ``None`` if stale or broken."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    finally:
        try:
            Path(path).unlink()
        except OSError:
            pass
    if not isinstance(raw, dict):
        return None
    at = float(raw.get("at", 0) or 0)
    if (now or time.time()) - at > MAX_AGE_SECONDS:
        return None
    tokens = raw.get("tokens")
    if not isinstance(tokens, list):
        return None
    return PlayRequest(str(raw.get("lineup_id", "")), tuple(str(t) for t in tokens), at)


__all__ = ["ACTION", "FOLDER", "MAX_AGE_SECONDS", "PlayRequest", "read_request", "write_request"]
