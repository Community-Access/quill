"""QUILL Transcribe's own preferences, and the move from Quill Inkwell.

Small on purpose. The dictation settings themselves -- model, language,
microphone, punctuation, read-back -- are the family's shared ones, stored here
under the shared names (``windows_dictation_*``) and cleaned by the same loader
the editors and Inkwell use (:mod:`quill.core.windows_dictation.anywhere`).
What is Transcribe's own is how the app behaves: whether setup has been done,
the start and stop key, and the tray.

**Its own AI choice** (codex.md Phase 3, decision 2): ``ai_connection`` and the
fields beside it, under the names both editors use and cleaned by the same
loader (:func:`~quill.core.ai.connection_choice.load_ai_fields`), so Choose Your
AI works here as everywhere. QUILL Transcribe signs in to ChatGPT as itself,
"QUILL Transcribe"; it no longer reads QUILL's sign-in. ``ai_seeded`` records
that the own key's provider and model were copied once from QUILL's settings
(names, never a key or a token), and ``ai_sign_in_noticed`` that the one
sentence about the new sign-in has been said.

**A key from the start.** ``dictation_hotkey`` is Alt+Shift+\\ until the
listener chooses another (owner, 2026-10-12: a dictation app with no key to
start it was one more step before the first word). Emptying it is still a
choice that is kept: then nothing is registered with Windows.

**From Quill Inkwell, once.** Somebody who used Inkwell's Dictate Anywhere
already chose an engine, a microphone and a key there. The first time
Transcribe runs it copies those into its own file -- Inkwell's file is read,
never changed -- and remembers that it did (:func:`take_from_inkwell`), so
running it again changes nothing.

Persisted with the atomic write; wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "OPTIONAL_KEY_FIELDS",
    "SCHEMA_VERSION",
    "TRANSCRIBE_DICTATION_DEFAULTS",
    "TranscribeSettings",
    "load_settings",
    "save_settings",
    "settings_path",
    "take_from_inkwell",
]

_SETTINGS_FILE = "transcribe.json"

#: Bumped when a field changes meaning, never merely when one is added.
SCHEMA_VERSION = 1
#: The start and stop key a new install has. Checked against every family
#: app's keys by family_chords.default_system_wide_keys.
DEFAULT_DICTATION_HOTKEY = "Alt+Shift+\\"
#: The system-wide keys added for D-6, each empty by default.
OPTIONAL_KEY_FIELDS = ("status_hotkey", "resume_hotkey", "discard_hotkey")
#: Where QUILL Transcribe's shared dictation settings start from a different
#: default than the editors', each with its reason. A value the person saved
#: always wins (the dictation window writes every field back).
TRANSCRIBE_DICTATION_DEFAULTS: dict[str, Any] = {
    # The working tick (D-17): QUILL Transcribe is where large models are used
    # and where nothing on screen shows the wait, so it ticks by default; the
    # editors' status bar already says "hearing you".
    "windows_dictation_working_tick": True,
    # Strict mode (D-1): a bare "scratch that" is typed as words, and only
    # "QUILL scratch that" is a command. A command typed by mistake is cheap to
    # undo in an editor and expensive in somebody's email.
    "windows_dictation_command_prefix_required": True,
}


@dataclass(slots=True)
class TranscribeSettings:
    #: Set when the setup window has been finished or skipped, so it is offered
    #: once and then only from the Help menu.
    setup_done: bool = False
    #: The key that starts and stops dictation from any program. Empty only
    #: when the listener emptied it.
    dictation_hotkey: str = DEFAULT_DICTATION_HOTKEY
    #: The Command Key (D-1): the next thing said is a command; pressed twice,
    #: command mode. Empty until the listener chooses one (dict.md section 5:
    #: every global key but the start and stop key starts empty).
    command_hotkey: str = ""
    #: Dictation Status, Resume and Discard Held Words from any program (D-6):
    #: empty until the listener chooses them, like the Command Key.
    status_hotkey: str = ""
    resume_hotkey: str = ""
    discard_hotkey: str = ""
    #: Open hidden in the tray rather than with the window showing.
    start_in_tray: bool = False
    #: The close button hides to the tray rather than exiting.
    close_to_tray: bool = True
    #: Inkwell's Dictate Anywhere settings have been looked at (copied or not).
    inkwell_checked: bool = False
    #: The shared dictation settings, under their shared names.
    dictation: dict[str, Any] = field(default_factory=dict)
    #: Choose Your AI (codex.md 10A.6): "" is "not yet decided", migrated once.
    ai_connection: str = ""
    ai_own_key_provider: str = "openai"
    ai_own_key_model: str = ""
    ai_copilot_model: str = ""
    ai_codex_model: str = ""
    ai_privacy_accepted_version: int = 0
    #: The own key's provider and model were copied from QUILL's settings, once.
    ai_seeded: bool = False
    #: The one sentence about QUILL Transcribe's own sign-in has been said.
    ai_sign_in_noticed: bool = False
    #: Set when the file came from a newer build: read, never written back.
    read_only: bool = False


def settings_path(data_dir: Path) -> Path:
    return data_dir / _SETTINGS_FILE


def load_settings(data_dir: Path) -> TranscribeSettings:
    """The saved settings, each field defaulted on its own."""
    from quill.core.storage import read_json

    raw = read_json(settings_path(data_dir), default={})
    settings = TranscribeSettings()
    if not isinstance(raw, dict):
        return settings
    settings.setup_done = bool(raw.get("setup_done", False))
    settings.dictation_hotkey = str(
        raw.get("dictation_hotkey", DEFAULT_DICTATION_HOTKEY) or ""
    ).strip()
    settings.command_hotkey = str(raw.get("command_hotkey", "") or "").strip()
    for name in OPTIONAL_KEY_FIELDS:
        setattr(settings, name, str(raw.get(name, "") or "").strip())
    settings.start_in_tray = bool(raw.get("start_in_tray", False))
    settings.close_to_tray = bool(raw.get("close_to_tray", True))
    settings.inkwell_checked = bool(raw.get("inkwell_checked", False))
    dictation = raw.get("dictation", {})
    if isinstance(dictation, dict):
        settings.dictation = {
            str(name): value
            for name, value in dictation.items()
            if str(name).startswith("windows_dictation_")
        }
    _load_ai(settings, raw)
    try:
        version = int(raw.get("schema_version", SCHEMA_VERSION) or SCHEMA_VERSION)
    except (TypeError, ValueError):
        version = SCHEMA_VERSION
    settings.read_only = version > SCHEMA_VERSION
    return settings


def save_settings(data_dir: Path, settings: TranscribeSettings) -> None:
    """Persist, stamped with the schema version. A file from a newer build is
    never written over: that would drop every field this build does not know."""
    from quill.core.storage import write_json_atomic

    if settings.read_only:
        return
    write_json_atomic(
        settings_path(data_dir),
        {
            "schema_version": SCHEMA_VERSION,
            "setup_done": settings.setup_done,
            "dictation_hotkey": settings.dictation_hotkey,
            "command_hotkey": settings.command_hotkey,
            **{name: getattr(settings, name) for name in OPTIONAL_KEY_FIELDS},
            "start_in_tray": settings.start_in_tray,
            "close_to_tray": settings.close_to_tray,
            "inkwell_checked": settings.inkwell_checked,
            "dictation": dict(settings.dictation),
            **{name: getattr(settings, name) for name in _AI_FIELDS},
        },
    )


#: Choose Your AI's fields, saved as they are.
_AI_FIELDS = (
    "ai_connection",
    "ai_own_key_provider",
    "ai_own_key_model",
    "ai_copilot_model",
    "ai_codex_model",
    "ai_privacy_accepted_version",
    "ai_seeded",
    "ai_sign_in_noticed",
)


def _load_ai(settings: TranscribeSettings, raw: dict[str, Any]) -> None:
    from quill.core.ai.connection_choice import load_ai_fields

    for name, value in load_ai_fields(raw).items():
        setattr(settings, name, value)
    try:
        settings.ai_privacy_accepted_version = int(raw.get("ai_privacy_accepted_version", 0) or 0)
    except (TypeError, ValueError):
        settings.ai_privacy_accepted_version = 0
    settings.ai_seeded = bool(raw.get("ai_seeded", False))
    settings.ai_sign_in_noticed = bool(raw.get("ai_sign_in_noticed", False))


def take_from_inkwell(settings: TranscribeSettings, data_dir: Path) -> str:
    """Copy Inkwell's Dictate Anywhere settings the first time; the sentence to say.

    Non-destructive and idempotent: Inkwell's file is only read, and once
    ``inkwell_checked`` is set this does nothing. Transcribe's own choices
    always win -- a setting already here is never replaced -- and the key is
    copied only when Transcribe has none, so the person's one choice of key
    carries over rather than being registered as a new default.
    """
    if settings.inkwell_checked:
        return ""
    settings.inkwell_checked = True
    from quill.core.expansion.settings import load_settings as load_inkwell
    from quill.core.expansion.settings import settings_path as inkwell_path

    if not inkwell_path(data_dir).is_file():
        return ""
    try:
        inkwell = load_inkwell(data_dir)
    except Exception:  # noqa: BLE001 - an unreadable Inkwell file is nothing to bring over
        return ""
    brought: list[str] = []
    if inkwell.dictation and not settings.dictation:
        settings.dictation = dict(inkwell.dictation)
        brought.append("dictation settings")
    key = inkwell.dictate_anywhere_hotkey.strip()
    if key and settings.dictation_hotkey in ("", DEFAULT_DICTATION_HOTKEY):
        settings.dictation_hotkey = key
        brought.append(f"start and stop key, {key}")
    if not brought:
        return ""
    return "Brought over your Dictate Anywhere " + " and ".join(brought) + " from Quill Inkwell."
