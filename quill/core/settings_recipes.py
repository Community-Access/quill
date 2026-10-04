"""Task recipes and profiles: named bundles of existing settings (qc.md X-02, X-03).

Two shapes over the same plain record of ``Settings`` fields:

* a **recipe** answers a task once -- "Quiet background work" -- by setting a
  handful of existing settings. Before it applies, it says exactly which
  settings change and from what to what; after, one Put Back restores them.
* a **profile** is a mode you turn on and off -- Focus, Review. Turning it on
  remembers what each setting was; turning it off puts every one of them back.
  A profile can be **for this session only**: it is then undone the next time
  QUILL starts, so a mode chosen for one evening never quietly becomes how
  QUILL always is.

A recipe or profile is a *visible composition of existing settings*, never a
hidden mode: every change it makes is a row in Preferences somebody could have
made by hand, and :func:`preview` lists them. Nothing here changes a key, the
focus, or how the screen reader is driven (qc.md X-05's rule applies here too).

wx-free, strict-typed. The caller saves the settings and reports the outcome.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

__all__ = [
    "PROFILES",
    "RECIPES",
    "Bundle",
    "apply",
    "load_state",
    "preview",
    "restore",
    "save_state",
    "session_profiles_to_undo",
    "undo_session_profiles",
]


@dataclass(frozen=True, slots=True)
class Bundle:
    id: str
    title: str
    purpose: str
    changes: tuple[tuple[str, object], ...]
    is_profile: bool = False


_QUIET_BACKGROUND: tuple[tuple[str, object], ...] = (
    ("podcast_check_audible_tick", False),
    ("podcast_check_interrupt_speech", False),
    ("watch_folder_audible_tick", False),
    ("watch_folder_interrupt_speech", False),
    ("weather_monitor_audible_tick", False),
    ("weather_monitor_interrupt_speech", False),
    ("github_poll_audible_tick", False),
    ("github_poll_interrupt_speech", False),
)

RECIPES: tuple[Bundle, ...] = (
    Bundle(
        "quiet_background",
        "Quiet background work",
        "Background checks -- podcasts, a watched folder, the weather, GitHub -- stop "
        "ticking and stop cutting across what is being said. They still run, and "
        "what they find is still kept.",
        _QUIET_BACKGROUND,
    ),
    Bundle(
        "prepare_dictation",
        "Prepare for dictation",
        "Windows dictation says what it is doing, plays its start and stop sounds, "
        "punctuates as you speak and spaces words sensibly.",
        (
            ("windows_dictation_announce", True),
            ("windows_dictation_cue_sounds", True),
            ("windows_dictation_auto_punctuation", True),
            ("dictation_intelligent_spacing", True),
        ),
    ),
    Bundle(
        "easier_to_see",
        "Make the editor easier to see",
        "A dark theme and larger text, for working on the screen as well as by ear.",
        (("theme", "dark"), ("font_size", 16)),
    ),
    Bundle(
        "say_more_while_writing",
        "Tell me more while I write",
        "QUILL says formatting as you move, how deep an indent is, and gives Reveal "
        "Codes its detailed descriptions.",
        (
            ("announce_formatting_on_move", True),
            ("announce_indent_depth", True),
            ("reveal_codes_verbosity", "detailed"),
        ),
    ),
)

PROFILES: tuple[Bundle, ...] = (
    Bundle(
        "focus",
        "Focus",
        "For writing without interruption: no spelling marks as you type, no "
        "formatting called out as you move, no start-up tips, and background work "
        "kept quiet.",
        (
            ("spellcheck_as_you_type", False),
            ("announce_formatting_on_move", False),
            ("announcement_startup_tips_enabled", False),
            *_QUIET_BACKGROUND,
        ),
        is_profile=True,
    ),
    Bundle(
        "review",
        "Review",
        "For reading a draft through: spelling checked as you go, formatting called "
        "out as you move, and Reveal Codes in detail.",
        (
            ("spellcheck_as_you_type", True),
            ("announce_formatting_on_move", True),
            ("reveal_codes_verbosity", "detailed"),
        ),
        is_profile=True,
    ),
)


def known_fields(settings: Any) -> set[str]:
    return {f.name for f in fields(settings)}


def preview(bundle: Bundle, settings: Any, labels: dict[str, str] | None = None) -> list[str]:
    """One sentence per setting that would change; nothing for one already so."""
    names = labels or {}
    lines: list[str] = []
    for name, value in bundle.changes:
        current = getattr(settings, name, None)
        if current == value:
            continue
        label = names.get(name) or name.replace("_", " ").capitalize()
        lines.append(f"{label}: {_words(current)} becomes {_words(value)}.")
    return lines


def _words(value: object) -> str:
    if value is True:
        return "on"
    if value is False:
        return "off"
    return str(value)


def apply(bundle: Bundle, settings: Any) -> dict[str, object]:
    """Make the changes; return what each changed setting was, for Put Back."""
    previous: dict[str, object] = {}
    for name, value in bundle.changes:
        if not hasattr(settings, name):
            continue
        current = getattr(settings, name)
        if current != value:
            previous[name] = current
            setattr(settings, name, value)
    return previous


def restore(settings: Any, previous: dict[str, object]) -> int:
    """Put back what :func:`apply` changed. Returns how many settings moved."""
    moved = 0
    for name, value in previous.items():
        if hasattr(settings, name) and getattr(settings, name) != value:
            setattr(settings, name, value)
            moved += 1
    return moved


# -- which profiles are on (a small file of its own) -----------------------------

_STATE_FILE = "settings_profiles.json"


def load_state(data_dir: Path) -> dict[str, dict[str, Any]]:
    """Profile id -> {"previous": {...}, "session": bool}, for the profiles that are on."""
    try:
        raw = json.loads((data_dir / _STATE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    active = raw.get("active") if isinstance(raw, dict) else None
    if not isinstance(active, dict):
        return {}
    return {
        str(key): {
            "previous": dict(value.get("previous", {})) if isinstance(value, dict) else {},
            "session": bool(value.get("session", False)) if isinstance(value, dict) else False,
        }
        for key, value in active.items()
    }


def save_state(data_dir: Path, state: dict[str, dict[str, Any]]) -> None:
    from quill.core.storage import write_json_atomic

    write_json_atomic(data_dir / _STATE_FILE, {"version": 1, "active": state})


def session_profiles_to_undo(state: dict[str, dict[str, Any]]) -> list[str]:
    """Profiles that were on for one session only -- undone at the next start."""
    return [key for key, value in state.items() if value.get("session")]


def undo_session_profiles(settings: Any, data_dir: Path) -> int:
    """At start-up: turn off the profiles that were on for one session only, and
    save, so the settings file says what QUILL is doing again. Never raises."""
    try:
        state = load_state(data_dir)
        keys = session_profiles_to_undo(state)
        for key in keys:
            restore(settings, state.pop(key).get("previous", {}))
        if keys:
            save_state(data_dir, state)
            from quill.core.settings import save_settings

            save_settings(settings)
        return len(keys)
    except Exception:  # noqa: BLE001 - a start-up courtesy must never stop QUILL
        return 0
