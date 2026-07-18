"""Multi-vintage shared-store safety for the settings store.

Several apps of possibly different vintages (QUILL, Quill Radio, QUILL Cast,
Audio Studio) read AND rewrite the same ``%APPDATA%\\Quill\\settings.json``.
Adding a setting *field* does not bump ``schema_version``, so the load path
must not let an older build drop a field a newer sibling wrote, and must never
downgrade a genuinely newer-schema file.
"""

from __future__ import annotations

import json

from quill.core.settings import Settings
from quill.core.settings_migration import (
    RETIRED_SETTINGS_KEYS,
    SETTINGS_SCHEMA_VERSION,
    from_versioned,
    is_future_settings_document,
    is_legacy_settings_document,
    reconcile_unknown_overrides,
    to_versioned,
)
from quill.core.versioned_store import load_with_migration


def _load(path):
    return load_with_migration(
        path,
        store_name="settings",
        parse=from_versioned,
        serialize=to_versioned,
        is_legacy=is_legacy_settings_document,
        default=Settings,
        reconcile_unknown=reconcile_unknown_overrides,
        is_future=is_future_settings_document,
    )


def _write(path, doc) -> None:
    path.write_text(json.dumps(doc), encoding="utf-8")


def _flat(doc) -> dict:
    return {k: v for b in doc.get("groups", {}).values() for k, v in b.items()}


# --- pure reconcile / is_future logic ---------------------------------------


def test_reconcile_preserves_unknown_override():
    desired = {"schema_version": SETTINGS_SCHEMA_VERSION, "groups": {"general": {}}}
    raw = {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "groups": {"general": {"future_setting_from_newer_app": 42}},
    }
    out = reconcile_unknown_overrides(raw, desired)
    assert out["groups"]["general"]["future_setting_from_newer_app"] == 42


def test_reconcile_no_unknown_returns_desired_unchanged():
    desired = {"schema_version": SETTINGS_SCHEMA_VERSION, "groups": {"general": {}}}
    raw = {"schema_version": SETTINGS_SCHEMA_VERSION, "groups": {"general": {}}}
    assert reconcile_unknown_overrides(raw, desired) is desired


def test_reconcile_does_not_preserve_retired_keys():
    if not RETIRED_SETTINGS_KEYS:
        return  # nothing retired in this build; property holds vacuously
    retired = sorted(RETIRED_SETTINGS_KEYS)[0]
    desired = {"schema_version": SETTINGS_SCHEMA_VERSION, "groups": {}}
    raw = {"schema_version": SETTINGS_SCHEMA_VERSION, "groups": {"general": {retired: 1}}}
    out = reconcile_unknown_overrides(raw, desired)
    assert retired not in _flat(out)


def test_is_future_detects_newer_schema():
    assert is_future_settings_document({"schema_version": SETTINGS_SCHEMA_VERSION + 1})
    assert not is_future_settings_document({"schema_version": SETTINGS_SCHEMA_VERSION})
    assert not is_future_settings_document({"schema_version": 1})
    assert not is_future_settings_document("junk")


# --- end-to-end through the loader ------------------------------------------


def test_unknown_only_file_preserved_verbatim_no_churn(tmp_path):
    path = tmp_path / "settings.json"
    raw = {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "groups": {"_ungrouped": {"future_only_field": "keep-me"}},
    }
    _write(path, raw)
    before = path.read_text(encoding="utf-8")
    _load(path)
    after = path.read_text(encoding="utf-8")
    assert before == after
    assert _flat(json.loads(after)).get("future_only_field") == "keep-me"


def test_unknown_survives_a_rewrite(tmp_path):
    # Force a rewrite (a retired key that migration strips) and confirm the
    # unknown newer-app field is still carried forward.
    if not RETIRED_SETTINGS_KEYS:
        return
    retired = sorted(RETIRED_SETTINGS_KEYS)[0]
    path = tmp_path / "settings.json"
    raw = {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "groups": {"general": {retired: "stale", "future_only_field": "keep-me"}},
    }
    _write(path, raw)
    _load(path)
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    flat = _flat(on_disk)
    assert retired not in flat  # migration dropped the retired key
    assert flat.get("future_only_field") == "keep-me"  # unknown preserved


def test_future_schema_file_not_rewritten(tmp_path):
    path = tmp_path / "settings.json"
    raw = {
        "schema_version": SETTINGS_SCHEMA_VERSION + 5,
        "groups": {"general": {"something_a_future_build_added": 1}},
    }
    _write(path, raw)
    before = path.read_text(encoding="utf-8")
    _load(path)
    after = path.read_text(encoding="utf-8")
    assert before == after  # an older build must never downgrade a newer file


def test_legacy_flat_file_still_migrates(tmp_path):
    # A stamp-less flat legacy document is unaffected by the new preservation
    # path (it has no "groups"); it migrates to the canonical v2 shape as before.
    path = tmp_path / "settings.json"
    _write(path, {"some_legacy_flat_key": "v"})
    _load(path)
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk.get("schema_version") == SETTINGS_SCHEMA_VERSION
    assert "groups" in on_disk
