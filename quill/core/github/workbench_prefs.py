"""GitHub Workbench preferences: ``github_workbench.json`` (GitHub PRD section 4.1).

GitHub preferences belong to the Workbench, so the editors' main Options stay
about writing (decision 6). Tools > Workbench Options... in the Workbench's
own menu bar edits them, and both editors read and write this one file
through this one module, so QUILL and QUILL Lite cannot drift: QUILL Lite is
never ahead by construction, and the settings vocabulary audit has nothing to
pair because neither editor's ``Settings`` holds these fields.

Preferences are things a person chooses. Where the window *was* (last node,
expanded nodes, history) is resume state and lives beside it, in
:mod:`quill.core.github.navigation_state`.

- **Validated field by field** against ``quill/core/schemas/github_workbench.json``
  (normative; ``tests/unit/core/test_github_workbench_prefs.py`` holds the two
  in step). A hand-edited or corrupt value falls back to that field's default
  and never stops the Workbench opening.
- **Written atomically** through :func:`quill.core.storage.write_json_atomic`.
- **The one-time move out of the main Settings.** The GitHub check's three
  fields (``github_poll_interval_minutes``, ``github_poll_audible_tick``,
  ``github_poll_interrupt_speech``) lived in ``quill/core/settings.py``.
  :func:`adopt_legacy_settings` copies them in once, when this file does not
  exist yet, and ``settings_migration.MOVED_SETTINGS_KEYS`` drops the old keys
  on the editor's next save. The ``MONITOR_GITHUB`` clamp still applies.

Defaults make the Workbench fully usable without ever opening the dialog.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any

from quill.core.monitor_policy import (
    MONITOR_GITHUB,
    MonitorPolicy,
    clamp_interval_minutes,
    resolve_monitor_policy,
)
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "CHOICES",
    "FILENAME",
    "LEGACY_SETTINGS_KEYS",
    "SCHEMA_VERSION",
    "WorkbenchPrefs",
    "adopt_legacy_settings",
    "adopt_legacy_settings_file",
    "github_monitor_policy",
    "load_prefs",
    "prefs_path",
    "save_prefs",
]

FILENAME = "github_workbench.json"
SCHEMA_VERSION = 1

#: The legacy ``Settings`` key -> the field here that took its place.
LEGACY_SETTINGS_KEYS: dict[str, str] = {
    "github_poll_interval_minutes": "poll_interval_minutes",
    "github_poll_audible_tick": "poll_audible_tick",
    "github_poll_interrupt_speech": "poll_interrupt_speech",
}

#: The allowed values of every choice field, in the order the dialog lists them.
CHOICES: dict[str, tuple[str, ...]] = {
    "open_on": ("inbox", "start", "last"),
    "list_mode": ("quick", "full"),
    "default_sort": (
        "number_desc",
        "number_asc",
        "title_asc",
        "title_desc",
        "updated_desc",
        "updated_asc",
        "comments_desc",
    ),
    "default_state": ("open", "closed", "all"),
}


@dataclass(frozen=True, slots=True)
class WorkbenchPrefs:
    """Everything a person can choose about the GitHub Workbench.

    *open_on* is where the window opens: ``"inbox"`` (Start Here until you are
    signed in, then Inbox: decision 2), ``"start"`` or ``"last"`` (the place you
    left). *use_classic_windows* brings back GitHub Items and Explore GitHub for
    one release (decision 4).
    """

    open_on: str = "inbox"
    list_mode: str = "quick"
    default_sort: str = "number_desc"
    default_state: str = "open"
    poll_interval_minutes: int = 15
    poll_audible_tick: bool = False
    poll_interrupt_speech: bool = False
    include_read_notifications: bool = False
    speak_column_names: bool = False
    first_time_help: bool = True
    health_snapshot_opt_in: bool = False
    use_classic_windows: bool = False

    def with_changes(self, **changes: Any) -> WorkbenchPrefs:
        """A copy with *changes* applied and validated."""
        return _coerce({**asdict(self), **changes})


def _coerce(raw: Mapping[str, Any]) -> WorkbenchPrefs:
    """Each field from *raw*, or its default when missing or not valid."""
    defaults = WorkbenchPrefs()
    values: dict[str, Any] = {}
    for spec in fields(WorkbenchPrefs):
        name = spec.name
        default = getattr(defaults, name)
        value = raw.get(name, default)
        if name in CHOICES:
            values[name] = value if isinstance(value, str) and value in CHOICES[name] else default
        elif name == "poll_interval_minutes":
            values[name] = (
                default
                if isinstance(value, bool)
                else clamp_interval_minutes(MONITOR_GITHUB, value)
            )
        elif isinstance(default, bool):
            values[name] = value if isinstance(value, bool) else default
    return replace(defaults, **values)


def prefs_path() -> Path:
    return app_data_dir() / FILENAME


def load_prefs(path: Path | None = None) -> WorkbenchPrefs:
    """The saved preferences, or the defaults when there are none yet."""
    raw = read_json(path or prefs_path(), default={})
    if not isinstance(raw, dict):
        return WorkbenchPrefs()
    return _coerce(raw)


def save_prefs(prefs: WorkbenchPrefs, path: Path | None = None) -> None:
    """Write *prefs* atomically, stamped with the schema version."""
    document: dict[str, Any] = {"schema_version": SCHEMA_VERSION, **asdict(_coerce(asdict(prefs)))}
    write_json_atomic(path or prefs_path(), document)


def adopt_legacy_settings(settings_document: object, path: Path | None = None) -> bool:
    """Copy the GitHub check's three old settings in, once. True when it wrote.

    *settings_document* is the editor's raw ``settings.json`` (a versioned
    document with ``groups``, or a legacy flat mapping). Nothing is written
    when this file already exists (the move happened) or when none of the
    three keys is there (nothing to move).
    """
    target = path or prefs_path()
    if target.exists() or not isinstance(settings_document, dict):
        return False
    groups = settings_document.get("groups")
    flat: dict[str, Any] = {}
    if isinstance(groups, dict):
        for bucket in groups.values():
            if isinstance(bucket, dict):
                flat.update(bucket)
    else:
        flat = dict(settings_document)
    found = {new: flat[old] for old, new in LEGACY_SETTINGS_KEYS.items() if old in flat}
    if not found:
        return False
    try:
        save_prefs(WorkbenchPrefs().with_changes(**found), target)
    except OSError:
        return False
    return True


def adopt_legacy_settings_file(settings_file: Path, path: Path | None = None) -> bool:
    """:func:`adopt_legacy_settings` from the editor's ``settings.json`` itself.

    ``quill.core.settings.load_settings`` calls this before the load that drops
    the old keys, so a value somebody chose survives the move. After the first
    time it costs one existence check: this file exists and nothing is read.
    """
    if (path or prefs_path()).exists() or not settings_file.exists():
        return False
    return adopt_legacy_settings(read_json(settings_file, default={}), path)


def github_monitor_policy(prefs: WorkbenchPrefs | None = None) -> MonitorPolicy:
    """The GitHub check's poll interval, tick and interrupt, from these prefs."""
    return resolve_monitor_policy(prefs or load_prefs(), MONITOR_GITHUB)
