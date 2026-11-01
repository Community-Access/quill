"""A QuillVille app's own AI choice, in its own small file (codex.md 10A.6, Phase 3).

Choose Your AI stores one choice per app. QUILL and QUILL Lite keep theirs in
their settings; QUILL Studio has ``studio-ai.json``
(:mod:`quill.core.audio_studio.ai_settings`). Quill Weather, Quill Converter,
Quill Media Player, Quill Inkwell and QuillBeacon keep theirs here, one file an
app -- ``weather-ai.json``, ``converter-ai.json`` and so on -- under the field
names both editors use, so the shared loader
(:func:`~quill.core.ai.connection_choice.load_ai_fields`) cleans them the same
way and the one-time migration runs the same way: an empty ``ai_connection``
becomes what the old precedence would have chosen for *this* app's own sign-in.

Nothing here is a secret. Keys stay in the Windows credential store, and each
app's ChatGPT and GitHub sign-ins are kept under that app's own agent name.
``ai_seeded`` records that the own key's provider and model names were copied
once from QUILL's settings (:func:`seed_from_quill`) -- names, never a key or a
token. ``ai_picture_consent`` is the 10B.4 list
(:mod:`quill.core.ai.picture_consent`).

Persisted with the atomic write; wx-free and strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "AI_SETTINGS_APPS",
    "AppAiSettings",
    "load_app_ai_settings",
    "save_app_ai_settings",
    "seed_from_quill",
    "settings_file",
]

#: The apps that keep their choice in this module's file, by app id.
AI_SETTINGS_APPS: tuple[str, ...] = ("weather", "converter", "player", "inkwell", "beacon")


@dataclass(slots=True)
class AppAiSettings:
    """What the shared hosted-AI code reads as one app's "settings"."""

    ai_privacy_accepted_version: int = 0
    ai_own_key_model: str = ""
    ai_own_key_provider: str = "openai"
    #: "" is "not yet decided", migrated once on first read (10A.6).
    ai_connection: str = ""
    ai_copilot_model: str = ""
    ai_codex_model: str = ""
    #: Connections said Yes to for pictures (10B.4), as ``consent_key`` writes them.
    ai_picture_consent: list[str] = field(default_factory=list)
    #: The own key's names were copied from QUILL's settings, once.
    ai_seeded: bool = False


def settings_file(app: str) -> str:
    """``weather-ai.json``: the file *app* keeps its choice in."""
    if app not in AI_SETTINGS_APPS:
        raise ValueError(f"{app!r} keeps its AI choice elsewhere")
    return f"{app}-ai.json"


def load_app_ai_settings(data_dir: Path, app: str) -> AppAiSettings:
    """The saved choice, each field cleaned by the family's own validators."""
    from quill.core.ai.connection_choice import load_ai_fields
    from quill.core.storage import read_json

    raw = read_json(data_dir / settings_file(app), default={})
    settings = AppAiSettings()
    if not isinstance(raw, dict):
        return settings
    for name, value in load_ai_fields(raw).items():
        if hasattr(settings, name):
            setattr(settings, name, value)
    try:
        settings.ai_privacy_accepted_version = int(raw.get("ai_privacy_accepted_version", 0) or 0)
    except (TypeError, ValueError):
        settings.ai_privacy_accepted_version = 0
    consent = raw.get("ai_picture_consent", [])
    if isinstance(consent, list):
        settings.ai_picture_consent = [str(item) for item in consent if str(item).strip()]
    settings.ai_seeded = bool(raw.get("ai_seeded", False))
    return settings


def save_app_ai_settings(data_dir: Path, app: str, settings: AppAiSettings) -> None:
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        data_dir / settings_file(app),
        {
            "ai_privacy_accepted_version": settings.ai_privacy_accepted_version,
            "ai_own_key_model": settings.ai_own_key_model,
            "ai_own_key_provider": settings.ai_own_key_provider,
            "ai_connection": settings.ai_connection,
            "ai_copilot_model": settings.ai_copilot_model,
            "ai_codex_model": settings.ai_codex_model,
            "ai_picture_consent": list(settings.ai_picture_consent),
            "ai_seeded": settings.ai_seeded,
        },
    )


def seed_from_quill(settings: AppAiSettings, quill_settings: Path) -> bool:
    """Copy the own key's provider and model names from QUILL's settings, once.

    Names only: the key itself stays in the Windows credential store, where every
    family app's Use My Own AI Key reads it. No sign-in or token is copied.
    Returns True when *settings* changed (and so wants saving).
    """
    if settings.ai_seeded:
        return False
    settings.ai_seeded = True
    try:
        from quill.core.ai.own_key import load_settings_fields

        data = json.loads(quill_settings.read_text(encoding="utf-8"))
        fields = load_settings_fields(data if isinstance(data, dict) else {})
    except Exception:  # noqa: BLE001 - no QUILL settings: keep the defaults
        return True
    if not settings.ai_own_key_model:
        settings.ai_own_key_provider = str(fields["ai_own_key_provider"])
        settings.ai_own_key_model = str(fields["ai_own_key_model"])
    return True
