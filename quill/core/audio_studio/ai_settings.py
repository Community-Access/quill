"""QUILL Studio's own AI choice: what the shared hosted-AI code reads as "the settings".

Choose Your AI (codex.md 10A.6, Phase 3) stores one choice per app. Studio's is
kept here, in its own small file beside ``audio-studio-app.json``, under the
field names both editors use -- ``ai_connection``, the own key's provider and
model, the two engine models and the free AI's agreement version -- so the
shared loader (:func:`~quill.core.ai.connection_choice.load_ai_fields`) cleans
them the same way and the one-time migration runs the same way: an empty
``ai_connection`` becomes what the old precedence chose (Studio's own "QUILL
Studio" ChatGPT sign-in, else an own key that is ready, else the free AI).

``ai_picture_consent`` is the 10B.4 list (:mod:`quill.core.ai.picture_consent`):
the connections a person has said Yes to for pictures. Choosing an AI here
changes nothing in the editors or the other apps.

Persisted with the atomic write; wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["SETTINGS_FILE", "StudioAiSettings", "load_ai_settings", "save_ai_settings"]

SETTINGS_FILE = "studio-ai.json"


@dataclass(slots=True)
class StudioAiSettings:
    ai_privacy_accepted_version: int = 0
    ai_own_key_model: str = ""
    ai_own_key_provider: str = "openai"
    #: "" is "not yet decided", migrated once on first read (10A.6).
    ai_connection: str = ""
    ai_copilot_model: str = ""
    ai_codex_model: str = ""
    #: Connections said Yes to for pictures (10B.4), as ``consent_key`` writes them.
    ai_picture_consent: list[str] = field(default_factory=list)


def load_ai_settings(data_dir: Path) -> StudioAiSettings:
    """The saved choice, each field cleaned by the family's own validators."""
    from quill.core.ai.connection_choice import load_ai_fields
    from quill.core.storage import read_json

    raw = read_json(data_dir / SETTINGS_FILE, default={})
    settings = StudioAiSettings()
    if not isinstance(raw, dict):
        return settings
    for name, value in load_ai_fields(raw).items():
        setattr(settings, name, value)
    try:
        settings.ai_privacy_accepted_version = int(raw.get("ai_privacy_accepted_version", 0) or 0)
    except (TypeError, ValueError):
        settings.ai_privacy_accepted_version = 0
    consent = raw.get("ai_picture_consent", [])
    if isinstance(consent, list):
        settings.ai_picture_consent = [str(item) for item in consent if str(item).strip()]
    return settings


def save_ai_settings(data_dir: Path, settings: StudioAiSettings) -> None:
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        data_dir / SETTINGS_FILE,
        {
            "ai_privacy_accepted_version": settings.ai_privacy_accepted_version,
            "ai_own_key_model": settings.ai_own_key_model,
            "ai_own_key_provider": settings.ai_own_key_provider,
            "ai_connection": settings.ai_connection,
            "ai_copilot_model": settings.ai_copilot_model,
            "ai_codex_model": settings.ai_codex_model,
            "ai_picture_consent": list(settings.ai_picture_consent),
        },
    )
