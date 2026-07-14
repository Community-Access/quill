from __future__ import annotations

from dataclasses import asdict

from quill.core.settings import Settings
from quill.core.settings_migration import (
    SETTINGS_SCHEMA_VERSION,
    UNGROUPED_KEY,
    from_versioned,
    is_legacy_settings_document,
    migrate,
    to_versioned,
)


def test_pristine_settings_serialize_to_an_empty_delta() -> None:
    # The delta format: a Settings() with no customizations writes no field
    # entries, only the version stamp. This is what lets a later default change
    # reach the user (the field is absent, so it resolves to the new default).
    doc = to_versioned(Settings())
    assert doc["schema_version"] == SETTINGS_SCHEMA_VERSION
    assert doc["groups"] == {}


def test_only_overrides_are_serialized_grouped_by_registry_group() -> None:
    doc = to_versioned(Settings(theme="dark"))
    # The overridden field lands under its registry group...
    assert doc["groups"].get("general", {}) == {"theme": "dark"}
    # ...and nothing equal to a default is written.
    all_written = {key for bucket in doc["groups"].values() for key in bucket}
    assert all_written == {"theme"}


def test_round_trip_is_lossless() -> None:
    original = Settings(
        theme="dark",
        read_aloud_rate=275,
        autosave_interval_seconds=120,
        announce_wrap=False,
        status_bar_hidden=["encoding", "selection"],
    )
    # Dropping default-valued fields is still lossless: from_dict refills each
    # missing field with that same default.
    restored = from_versioned(to_versioned(original))
    assert restored == original


def test_non_overridden_field_tracks_the_current_default() -> None:
    # The crux of forward-compat: a field absent from the saved delta resolves
    # to whatever Settings() says today, so a changed/added default reaches
    # existing users with no per-field migration.
    saved = to_versioned(Settings(theme="dark"))
    restored = from_versioned(saved)
    assert restored.theme == "dark"
    assert restored.read_aloud_rate == Settings().read_aloud_rate


def test_legacy_v1_full_snapshot_is_read_and_reduced_to_a_delta() -> None:
    # A schema_version 1 file stored every field (a full snapshot). It must
    # still load, and re-serializing it yields a delta containing only the
    # genuine overrides -- default-valued fields drop out.
    full = asdict(Settings(theme="dark"))
    v1_doc = {"schema_version": 1, "groups": {"_ungrouped": full}}
    settings = from_versioned(v1_doc)
    assert settings.theme == "dark"
    reduced = to_versioned(settings)
    assert {k for bucket in reduced["groups"].values() for k in bucket} == {"theme"}


def test_legacy_flat_document_migrates() -> None:
    legacy = {"theme": "dark", "read_aloud_rate": 300, "soft_wrap": False}
    settings = from_versioned(legacy)
    assert settings.theme == "dark"
    assert settings.read_aloud_rate == 300
    assert settings.soft_wrap is False


def test_is_legacy_settings_document_detects_pre_current_shapes() -> None:
    assert is_legacy_settings_document({"schema_version": 1, "groups": {}}) is True
    assert is_legacy_settings_document({"theme": "dark"}) is True  # unstamped flat
    assert is_legacy_settings_document(to_versioned(Settings(theme="dark"))) is False
    assert is_legacy_settings_document(None) is False
    assert is_legacy_settings_document(42) is False


def test_corrupt_value_recovers_without_losing_siblings() -> None:
    # Override two fields so both groups exist in the delta, then corrupt one.
    doc = to_versioned(Settings(theme="dark", read_aloud_rate=275))
    doc["groups"]["read_aloud"]["read_aloud_rate"] = "not-a-number"
    settings = from_versioned(doc)
    assert settings.theme == "dark"  # preserved
    assert settings.read_aloud_rate == Settings().read_aloud_rate  # defaulted


def test_migrate_handles_junk() -> None:
    assert migrate(None) == {}
    assert migrate(42) == {}
    assert migrate({"groups": "broken"}) == {}


def test_unspecced_override_goes_to_ungrouped() -> None:
    # status_bar_order has no registry spec; when overridden it must still be
    # serialized, in the ungrouped bucket.
    custom_order = list(reversed(Settings().status_bar_order))
    doc = to_versioned(Settings(status_bar_order=custom_order))
    assert doc["groups"].get(UNGROUPED_KEY, {}).get("status_bar_order") == custom_order


def test_dictation_engine_legacy_values_migrate_to_offline() -> None:
    # The legacy local-recognizer values never actually ran; preserve the user's
    # local/offline intent by mapping them to "offline" (Speech wave S0, #617).
    assert Settings.from_dict({"dictation_engine": "vosk"}).dictation_engine == "offline"
    assert Settings.from_dict({"dictation_engine": "whisper"}).dictation_engine == "offline"


def test_dictation_engine_unknown_defaults_to_windows() -> None:
    assert Settings.from_dict({"dictation_engine": "bogus"}).dictation_engine == "windows"
    # Windows dictation is the only functional engine today, so it is the default.
    assert Settings.from_dict({}).dictation_engine == "windows"


def test_dictation_engine_valid_values_pass_through() -> None:
    for value in ("offline", "windows", "cloud"):
        assert Settings.from_dict({"dictation_engine": value}).dictation_engine == value
