"""Persistent voice-failure blacklist (batch robustness, roadmap §5).

Some installed voices fail synthesis: a broken SAPI token, a deleted neural model,
a cloud provider that rejects a voice id. When round-robin or translated export
cycles many voices, one bad voice should not keep aborting later runs. This module
records voices that fail and lets callers skip them on subsequent runs (it pairs
naturally with the round-robin rotation, which simply drops the blacklisted ids).

Entries are keyed by ``engine`` + ``voice_id`` (case-insensitive). A voice is
considered blacklisted once it has failed at least ``threshold`` times (default 1),
so a single hard failure is enough to skip it next time, while the count is kept so
a caller could require repeated failures if it prefers.

``wx``-free and strict-typed. Persistence is atomic JSON in the app data dir
(:func:`default_path`); a missing or corrupt file is treated as an empty blacklist
— a robustness aid must never itself block an export.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The default number of recorded failures at which a voice is skipped. One hard
# failure is enough — the voice is unusable until the user fixes it (and the count
# lets a stricter caller wait for repeats if it wants).
DEFAULT_THRESHOLD = 1


def voice_key(engine: str, voice_id: str) -> str:
    """Stable, case-insensitive key for an ``engine`` + ``voice_id`` pair."""
    return f"{engine.strip().lower()}|{voice_id.strip().lower()}"


@dataclass(slots=True)
class VoiceFailure:
    """A recorded synthesis failure for one engine/voice (with a running count)."""

    engine: str
    voice_id: str
    count: int = 0
    last_error: str = ""
    last_failed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "voice_id": self.voice_id,
            "count": self.count,
            "last_error": self.last_error,
            "last_failed_at": self.last_failed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VoiceFailure:
        return cls(
            engine=str(data.get("engine", "")),
            voice_id=str(data.get("voice_id", "")),
            count=int(data.get("count", 0) or 0),
            last_error=str(data.get("last_error", "")),
            last_failed_at=float(data.get("last_failed_at", 0.0) or 0.0),
        )


@dataclass(slots=True)
class VoiceBlacklist:
    """An in-memory set of failed voices, loaded from / saved to disk by the caller."""

    entries: dict[str, VoiceFailure] = field(default_factory=dict)

    def is_blacklisted(
        self, engine: str, voice_id: str, *, threshold: int = DEFAULT_THRESHOLD
    ) -> bool:
        entry = self.entries.get(voice_key(engine, voice_id))
        return entry is not None and entry.count >= max(1, threshold)

    def record_failure(self, engine: str, voice_id: str, error: str = "") -> VoiceFailure:
        """Increment (or create) the failure record for this engine/voice."""
        key = voice_key(engine, voice_id)
        entry = self.entries.get(key)
        if entry is None:
            entry = VoiceFailure(engine=engine.strip(), voice_id=voice_id.strip())
            self.entries[key] = entry
        entry.count += 1
        entry.last_error = (error or "").strip()[:500]
        entry.last_failed_at = time.time()
        return entry

    def clear(self, engine: str | None = None, voice_id: str | None = None) -> None:
        """Remove a single entry, all entries for an engine, or everything."""
        if engine is None:
            self.entries.clear()
            return
        if voice_id is not None:
            self.entries.pop(voice_key(engine, voice_id), None)
            return
        prefix = f"{engine.strip().lower()}|"
        for key in [k for k in self.entries if k.startswith(prefix)]:
            del self.entries[key]

    def filter_voices(
        self, engine: str, voice_ids: list[str], *, threshold: int = DEFAULT_THRESHOLD
    ) -> list[str]:
        """Return *voice_ids* with the blacklisted ones removed (order preserved)."""
        return [v for v in voice_ids if not self.is_blacklisted(engine, v, threshold=threshold)]

    def to_dict(self) -> dict[str, Any]:
        return {"voices": [e.to_dict() for e in self.entries.values()]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VoiceBlacklist:
        out = cls()
        for raw in data.get("voices", []) or []:
            if not isinstance(raw, dict):
                continue
            entry = VoiceFailure.from_dict(raw)
            if entry.voice_id:
                out.entries[voice_key(entry.engine, entry.voice_id)] = entry
        return out


_LOCK = threading.Lock()


def default_path() -> Path:
    """The on-disk location of the shared voice blacklist (app data dir)."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / "voice-blacklist.json"


def load_blacklist(path: Path | None = None) -> VoiceBlacklist:
    """Load the blacklist from *path* (or :func:`default_path`); empty if absent/corrupt."""
    target = path or default_path()
    try:
        import json

        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return VoiceBlacklist()
    if not isinstance(data, dict):
        return VoiceBlacklist()
    return VoiceBlacklist.from_dict(data)


def save_blacklist(blacklist: VoiceBlacklist, path: Path | None = None) -> None:
    """Persist *blacklist* atomically (best-effort; never raises to the caller)."""
    target = path or default_path()
    try:
        from quill.core.storage import write_json_atomic

        write_json_atomic(target, blacklist.to_dict())
    except Exception:  # noqa: BLE001 - persistence of a robustness aid is best-effort
        pass


def record_voice_failure(engine: str, voice_id: str, error: str = "") -> None:
    """Load the shared blacklist, record one failure, and persist it (thread-safe)."""
    if not voice_id.strip():
        return
    with _LOCK:
        blacklist = load_blacklist()
        blacklist.record_failure(engine, voice_id, error)
        save_blacklist(blacklist)
