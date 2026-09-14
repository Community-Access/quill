"""UI-agnostic registry describing user settings as searchable, groupable specs.

This is the model layer behind the tabbed Settings surface (SET-1), the search
and per-setting reset (SET-6), and export/import/reset to defaults (SET-7). It
deliberately reuses the flat :class:`~quill.core.settings.Settings` dataclass and
its :meth:`Settings.from_dict` validation, so every value set or imported through
this registry is normalized and clamped exactly as a loaded settings file would
be. No ``wx`` imports: the dialog binds to this registry, not the other way
round.
"""

from __future__ import annotations

from dataclasses import asdict, fields

from quill.core.settings import Settings
from quill.core.settings_portable import (
    PortabilityReport,
    portable_export,
    portable_import,
)
from quill.core.settings_specs import (
    SCHEMA_VERSION,
    SETTING_GROUPS,
    SETTING_SPECS,
    SettingGroup,
    SettingSpec,
)

__all__ = [
    "SCHEMA_VERSION",
    "SETTING_GROUPS",
    "SETTING_SPECS",
    "SettingGroup",
    "SettingSpec",
    "groups",
    "specs",
    "specs_for_group",
    "find_spec",
    "search_specs",
    "default_value",
    "get_value",
    "set_value",
    "reset_setting",
    "reset_all",
    "LOCAL_SETTINGS",
    "export_portable_settings",
    "export_portable_settings_with_report",
    "export_settings",
    "import_portable_settings_with_report",
    "import_settings",
]


_SPECS_BY_KEY: dict[str, SettingSpec] = {spec.key: spec for spec in SETTING_SPECS}

_SETTINGS_FIELD_NAMES: frozenset[str] = frozenset(field.name for field in fields(Settings))


def groups() -> tuple[SettingGroup, ...]:
    """Return the ordered settings groups."""
    return SETTING_GROUPS


def specs() -> tuple[SettingSpec, ...]:
    """Return every registered setting spec, in declaration order."""
    return SETTING_SPECS


def specs_for_group(group_id: str) -> list[SettingSpec]:
    """Return the specs that belong to ``group_id``, in declaration order."""
    return [spec for spec in SETTING_SPECS if spec.group == group_id]


def find_spec(key: str) -> SettingSpec | None:
    """Return the spec for ``key`` or ``None`` when it is not registered."""
    return _SPECS_BY_KEY.get(key)


def search_specs(query: str) -> list[SettingSpec]:
    """Return specs whose label, key, description, keywords, or group title match.

    The match is case-insensitive and substring-based. An empty query returns
    every spec so the caller can show the full list.
    """
    needle = query.strip().lower()
    if not needle:
        return list(SETTING_SPECS)
    group_titles = {group.id: group.title.lower() for group in SETTING_GROUPS}
    matches: list[SettingSpec] = []
    for spec in SETTING_SPECS:
        haystack = " ".join((
            spec.label.lower(),
            spec.key.lower(),
            spec.description.lower(),
            group_titles.get(spec.group, ""),
            " ".join(keyword.lower() for keyword in spec.keywords),
        ))
        if needle in haystack:
            matches.append(spec)
    return matches


def default_value(key: str) -> object:
    """Return the factory default for ``key`` from a fresh :class:`Settings`."""
    return getattr(Settings(), key)


def get_value(settings: Settings, key: str) -> object:
    """Return the current value of ``key`` on ``settings``."""
    return getattr(settings, key)


def set_value(settings: Settings, key: str, value: object) -> Settings:
    """Return a new, normalized :class:`Settings` with ``key`` set to ``value``.

    Validation and clamping reuse :meth:`Settings.from_dict`, so out-of-range or
    invalid values are corrected exactly as they would be when loading a file.
    Unknown keys raise :class:`KeyError`.
    """
    if key not in _SETTINGS_FIELD_NAMES:
        raise KeyError(key)
    data = asdict(settings)
    data[key] = value
    return Settings.from_dict(data)


def reset_setting(settings: Settings, key: str) -> Settings:
    """Return a new :class:`Settings` with ``key`` reset to its factory default."""
    return set_value(settings, key, default_value(key))


def reset_all() -> Settings:
    """Return a fresh, all-defaults :class:`Settings` (SET-7 reset to defaults)."""
    return Settings()


#: Settings that describe *this machine* rather than how QUILL should behave:
#: folders, file locations, and the "last used" memories that point at them.
#: They are left out of a portable export, because the whole point of one is to
#: land on a different machine -- where a path to somebody else's Downloads
#: folder is not a preference, it is a broken setting (#1501). Left out rather
#: than blanked, so importing an old file cannot wipe a good local value either.
#:
#: API keys are deliberately absent from this list because they are absent from
#: Settings entirely: they live in the OS credential store, so a .qsf has never
#: been able to carry one. The reporter was right to ask; the answer is that it
#: was already safe.
LOCAL_SETTINGS: frozenset[str] = frozenset({
    "abbreviation_expansion_sound_file",
    "batch_speech_temp_folder",
    "convert_file_last_output_dir",
    "git_sync_last_folder",
    "import_export_last_folder",
    "last_update_check",
    "read_aloud_piper_model_dir",
    "sound_pack_path",
    "startup_folder",
    "tesseract_path",
    "vault_root",
    "vault_templates_folder",
    "watch_folder_path",
})


def export_settings(settings: Settings) -> dict[str, object]:
    """Every setting, for a **backup** of this machine.

    Shape::

        {"schema_version": 1, "settings": {<field>: <value>, ...}}

    Complete on purpose, including the machine-local paths. A backup restores
    the computer it came from, so a watch folder or a Tesseract path is part of
    what it is restoring -- ``share_package``'s backup kind is built on this and
    its contract says so in as many words ("a backup preserves per-device
    settings fields"). The *portable* export is a different product with a
    different answer; see :func:`export_portable_settings`.
    """
    return {"schema_version": SCHEMA_VERSION, "settings": asdict(settings)}


def export_portable_settings(settings: Settings) -> dict[str, object]:
    """Every setting **except the machine-local ones**, for another computer.

    The distinction this and :func:`export_settings` draw is the whole of #1501.
    A *backup* restores one machine and wants its paths; a configuration you
    carry to a new laptop wants everything but. Exporting the paths into the
    second case is what left people with an app pointing at folders that were
    never there.
    """
    payload, _report = export_portable_settings_with_report(settings)
    return payload


def export_portable_settings_with_report(
    settings: Settings,
) -> tuple[dict[str, object], PortabilityReport]:
    """:func:`export_portable_settings`, and what it had to leave behind."""
    return portable_export(settings, app="quill", local_fields=LOCAL_SETTINGS)


def import_settings(raw: object) -> Settings:
    """Build a validated :class:`Settings` from an exported document.

    Accepts either the wrapped ``{"schema_version", "settings"}`` shape or a
    bare settings mapping. Unknown keys are ignored and every value is
    normalized through :meth:`Settings.from_dict`, so a malformed or partial
    import never produces an invalid configuration.
    """
    values, _report = portable_import(raw, known=_SETTINGS_FIELD_NAMES)
    return Settings.from_dict(values)


def import_portable_settings_with_report(raw: object) -> tuple[Settings, PortabilityReport]:
    """Read a *portable* export, and say what was different about the file.

    Unlike :func:`import_settings`, which restores a backup verbatim, this one
    ignores any machine-local setting the file still carries -- an older file
    made before the split, or one written by hand -- so restoring somebody
    else's configuration cannot point this computer at their folders.

    The report is the honest half of the reporter's "intelligent wizard" ask
    (#1501): rather than interrogating the user about every setting added since
    their file was written, say how many there are and which, and let them go
    and look. Machine-local settings in an older file are ignored rather than
    applied, so importing a backup made on another computer cannot point this
    one at folders that are not there.
    """
    values, report = portable_import(raw, known=_SETTINGS_FIELD_NAMES, local_fields=LOCAL_SETTINGS)
    return Settings.from_dict(values), report
