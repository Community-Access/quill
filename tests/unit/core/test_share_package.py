from __future__ import annotations

import pytest

from quill.core.settings import Settings
from quill.core.settings_registry import export_settings
from quill.core.share_package import (
    BACKUP_EXTENSION,
    KIND_BACKUP,
    KIND_PROFILE,
    PROFILE_EXTENSION,
    SECTION_FEATURES,
    SECTION_SECRETS,
    SECTION_SETTINGS,
    PackageError,
    PrivacyError,
    build_package,
    extension_for_kind,
    package_summary,
    private_fields_present,
    read_package,
    read_package_file,
    scrub_settings_for_profile,
    write_package_file,
)


def _settings_payload() -> dict[str, object]:
    settings = Settings(
        theme="dark",
        watch_folder_path=r"D:\watch",
        skipped_update_version="9.9.9",
    )
    return export_settings(settings)


def test_extension_for_kind() -> None:
    assert extension_for_kind(KIND_PROFILE) == PROFILE_EXTENSION
    assert extension_for_kind(KIND_BACKUP) == BACKUP_EXTENSION


def test_backup_keeps_everything_including_private_sections() -> None:
    doc = build_package(
        kind=KIND_BACKUP,
        name="My backup",
        source_version="0.1.5",
        sections={
            SECTION_SETTINGS: _settings_payload(),
            SECTION_SECRETS: {"openai": "sk-secret"},
        },
    )
    assert doc["manifest"]["kind"] == KIND_BACKUP
    assert SECTION_SECRETS in doc["sections"]
    # A backup preserves per-device settings fields.
    assert "watch_folder_path" in doc["sections"][SECTION_SETTINGS]["settings"]


def test_profile_refuses_private_section() -> None:
    with pytest.raises(PrivacyError):
        build_package(
            kind=KIND_PROFILE,
            name="Share me",
            source_version="0.1.5",
            sections={SECTION_SECRETS: {"openai": "sk-secret"}},
        )


def test_profile_scrubs_private_settings_fields() -> None:
    doc = build_package(
        kind=KIND_PROFILE,
        name="Share me",
        source_version="0.1.5",
        sections={SECTION_SETTINGS: _settings_payload()},
    )
    inner = doc["sections"][SECTION_SETTINGS]["settings"]
    assert "theme" in inner  # shareable preference survives
    assert "watch_folder_path" not in inner
    assert "skipped_update_version" not in inner
    # The privacy guard finds nothing leaking.
    assert private_fields_present(doc) == []


def test_unknown_section_rejected() -> None:
    with pytest.raises(PackageError):
        build_package(
            kind=KIND_BACKUP,
            name="x",
            source_version="0.1.5",
            sections={"not_a_section": {}},
        )


def test_round_trip_through_read_package() -> None:
    doc = build_package(
        kind=KIND_BACKUP,
        name="Round trip",
        source_version="0.1.5",
        sections={SECTION_FEATURES: {"schema_version": 1, "active_profile_id": "essential"}},
    )
    package = read_package(doc)
    assert package.kind == KIND_BACKUP
    assert package.name == "Round trip"
    assert package.source_version == "0.1.5"
    assert SECTION_FEATURES in package.sections


def test_reader_strips_private_section_from_handedited_profile() -> None:
    # Simulate a hand-edited profile that smuggles a private section in.
    hostile = {
        "manifest": {
            "schema_version": 1,
            "kind": KIND_PROFILE,
            "name": "Hostile",
            "source_version": "0.1.5",
            "created": "2026-06-02T00:00:00+00:00",
            "contents": [SECTION_SECRETS],
        },
        "sections": {
            SECTION_SECRETS: {"openai": "sk-secret"},
            SECTION_SETTINGS: {"settings": {"theme": "dark", "watch_folder_path": "D:/w"}},
        },
    }
    package = read_package(hostile)
    assert SECTION_SECRETS not in package.sections
    assert "watch_folder_path" not in package.sections[SECTION_SETTINGS]["settings"]
    assert package.warnings  # warned about the stripped section


def test_scrub_handles_bare_mapping() -> None:
    scrubbed = scrub_settings_for_profile({"theme": "dark", "watch_folder_path": "D:/w"})
    assert scrubbed == {"theme": "dark"}


def test_package_summary_mentions_privacy_for_profile() -> None:
    doc = build_package(
        kind=KIND_PROFILE,
        name="Share me",
        source_version="0.1.5",
        sections={SECTION_SETTINGS: _settings_payload()},
    )
    summary = package_summary(read_package(doc))
    assert "Share me" in summary
    assert "never included" in summary.lower()


def test_read_package_rejects_bad_schema() -> None:
    with pytest.raises(PackageError):
        read_package({"manifest": {"schema_version": 99, "kind": KIND_BACKUP}, "sections": {}})


def test_file_round_trip(tmp_path) -> None:
    doc = build_package(
        kind=KIND_PROFILE,
        name="File",
        source_version="0.1.5",
        sections={SECTION_SETTINGS: _settings_payload()},
    )
    path = tmp_path / ("share" + extension_for_kind(KIND_PROFILE))
    write_package_file(doc, path)
    package = read_package_file(path)
    assert package.name == "File"
    assert package.is_profile


def test_private_settings_fields_are_all_real_settings_fields() -> None:
    """Every per-device name scrubbed from a shared profile must be a real
    Settings field. A name here with no matching field means some code path
    reads settings.<name> and crashes with AttributeError -- the shape of the
    "'Settings' object has no attribute 'read_aloud_piper_executable'" bug hit
    when previewing a Piper voice.
    """
    from dataclasses import fields

    from quill.core.share_package import PRIVATE_SETTINGS_FIELDS

    field_names = {f.name for f in fields(Settings)}
    missing = sorted(name for name in PRIVATE_SETTINGS_FIELDS if name not in field_names)
    assert not missing, f"PRIVATE_SETTINGS_FIELDS names with no Settings field: {missing}"
