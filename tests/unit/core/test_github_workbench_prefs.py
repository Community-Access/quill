"""GitHub Workbench preferences: the file, its schema and the move out of Settings."""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from pathlib import Path

import pytest

from quill.core.github import workbench_prefs as prefs_module
from quill.core.github.workbench_prefs import (
    CHOICES,
    LEGACY_SETTINGS_KEYS,
    WorkbenchPrefs,
    adopt_legacy_settings,
    github_monitor_policy,
    load_prefs,
    save_prefs,
)
from quill.core.settings import Settings
from quill.core.settings_migration import MOVED_SETTINGS_KEYS, from_versioned

_SCHEMA = Path(prefs_module.__file__).parents[1] / "schemas" / "github_workbench.json"


def test_the_schema_names_every_field_and_every_choice() -> None:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))["properties"]
    names = {spec.name for spec in fields(WorkbenchPrefs)}
    assert set(schema) == names | {"schema_version"}
    for name, choices in CHOICES.items():
        assert tuple(schema[name]["enum"]) == choices


def test_defaults_round_trip_and_bad_values_fall_back(tmp_path: Path) -> None:
    path = tmp_path / "github_workbench.json"
    assert load_prefs(path) == WorkbenchPrefs()
    save_prefs(WorkbenchPrefs(open_on="last", poll_interval_minutes=30), path)
    assert load_prefs(path) == WorkbenchPrefs(open_on="last", poll_interval_minutes=30)
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1
    path.write_text(
        json.dumps({"open_on": "nowhere", "poll_interval_minutes": 0, "poll_audible_tick": "yes"}),
        encoding="utf-8",
    )
    loaded = load_prefs(path)
    assert loaded.open_on == "inbox"
    assert loaded.poll_interval_minutes == 5  # the MONITOR_GITHUB clamp, never zero
    assert loaded.poll_audible_tick is False
    path.write_text("not json", encoding="utf-8")
    assert load_prefs(path) == WorkbenchPrefs()


def test_the_three_settings_move_once(tmp_path: Path) -> None:
    path = tmp_path / "github_workbench.json"
    document = {
        "schema_version": 2,
        "groups": {
            "accessibility": {
                "github_poll_interval_minutes": 45,
                "github_poll_audible_tick": True,
            }
        },
    }
    assert adopt_legacy_settings(document, path)
    moved = load_prefs(path)
    assert moved.poll_interval_minutes == 45
    assert moved.poll_audible_tick is True
    assert moved.poll_interrupt_speech is False
    # Once only: a second document never overwrites what the person has now.
    assert not adopt_legacy_settings({"github_poll_interval_minutes": 90}, path)
    assert load_prefs(path).poll_interval_minutes == 45
    assert not adopt_legacy_settings({"theme": "dark"}, tmp_path / "other.json")


def test_settings_no_longer_hold_them_and_drop_the_old_keys() -> None:
    names = {spec.name for spec in fields(Settings)}
    assert not names & set(LEGACY_SETTINGS_KEYS)
    assert set(LEGACY_SETTINGS_KEYS) == MOVED_SETTINGS_KEYS
    loaded = from_versioned({
        "schema_version": 2,
        "groups": {"accessibility": {"github_poll_interval_minutes": 45}},
    })
    assert "github_poll_interval_minutes" not in asdict(loaded)


def test_the_monitor_policy_reads_the_workbench_prefs() -> None:
    policy = github_monitor_policy(WorkbenchPrefs(poll_interval_minutes=20, poll_audible_tick=True))
    assert policy.poll_interval_seconds == 1200
    assert policy.audible_tick is True
    assert policy.interrupt_speech is False


def test_the_settings_file_hands_them_over_before_the_load(tmp_path: Path) -> None:
    from quill.core.github.workbench_prefs import adopt_legacy_settings_file

    settings_file = tmp_path / "settings.json"
    target = tmp_path / "github_workbench.json"
    assert not adopt_legacy_settings_file(settings_file, target)  # no settings yet
    settings_file.write_text(json.dumps({"github_poll_interrupt_speech": True}), encoding="utf-8")
    assert adopt_legacy_settings_file(settings_file, target)
    assert load_prefs(target).poll_interrupt_speech is True
    assert not adopt_legacy_settings_file(settings_file, target)  # once only


def test_with_changes_validates() -> None:
    assert WorkbenchPrefs().with_changes(list_mode="full").list_mode == "full"
    assert WorkbenchPrefs().with_changes(list_mode="wide").list_mode == "quick"
    with pytest.raises(AttributeError):
        WorkbenchPrefs().open_on = "x"  # type: ignore[misc]
