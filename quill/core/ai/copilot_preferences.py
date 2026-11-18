"""Per-app, non-secret preferences for the Copilot SDK integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "AUTO_TIERS",
    "CopilotPreferences",
    "load_copilot_preferences",
    "save_copilot_preferences",
]

AUTO_TIERS = ("efficiency", "balance", "intelligence")
_PREFERENCES_FILE = "copilot-preferences.json"


@dataclass(frozen=True, slots=True)
class CopilotPreferences:
    """Explicit, local choices that control optional Copilot SDK features."""

    auto_tier: str = "balance"
    keep_sessions: bool = False
    long_context: bool = False
    share_enabled_skills: bool = False
    resume_session_id: str = ""


def _preferences_path(data_dir: Path | None) -> Path:
    root = data_dir if data_dir is not None else app_data_dir()
    return root / "ai" / _PREFERENCES_FILE


def load_copilot_preferences(data_dir: Path | None = None) -> CopilotPreferences:
    """Read one app's preferences; malformed or missing optional values use safe defaults."""
    raw = read_json(_preferences_path(data_dir), default={})
    if not isinstance(raw, dict):
        return CopilotPreferences()
    auto_tier = raw.get("auto_tier")
    if not isinstance(auto_tier, str) or auto_tier not in AUTO_TIERS:
        auto_tier = "balance"
    return CopilotPreferences(
        auto_tier=auto_tier,
        keep_sessions=raw.get("keep_sessions") is True,
        long_context=raw.get("long_context") is True,
        share_enabled_skills=raw.get("share_enabled_skills") is True,
        resume_session_id=(
            raw.get("resume_session_id", "").strip()
            if isinstance(raw.get("resume_session_id", ""), str)
            else ""
        ),
    )


def save_copilot_preferences(preferences: CopilotPreferences, data_dir: Path | None = None) -> None:
    """Atomically save validated, non-secret Copilot preferences for one app."""
    if preferences.auto_tier not in AUTO_TIERS:
        raise ValueError(f"Unknown Copilot Auto tier: {preferences.auto_tier!r}")
    if not isinstance(preferences.resume_session_id, str):
        raise ValueError("A Copilot resume session ID must be text.")
    write_json_atomic(
        _preferences_path(data_dir),
        {
            "schema_version": 1,
            "auto_tier": preferences.auto_tier,
            "keep_sessions": preferences.keep_sessions,
            "long_context": preferences.long_context,
            "share_enabled_skills": preferences.share_enabled_skills,
            "resume_session_id": preferences.resume_session_id.strip(),
        },
    )
