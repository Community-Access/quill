from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core import quillin_settings as qs


def test_round_trip_uses_versioned_envelope(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    qs.save_settings("demo", {"foo": 1, "bar": "x"})
    # On disk it is wrapped with a schema_version, but the API returns the inner dict.
    raw = json.loads(qs._settings_path("demo").read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    assert raw["settings"] == {"foo": 1, "bar": "x"}
    assert qs.load_settings("demo") == {"foo": 1, "bar": "x"}


def test_load_reads_legacy_bare_dict(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    path = qs._settings_path("demo")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Pre-versioning files were the bare settings dict (no envelope).
    path.write_text(json.dumps({"foo": 1, "bar": "x"}), encoding="utf-8")
    assert qs.load_settings("demo") == {"foo": 1, "bar": "x"}


def test_set_setting_round_trips(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    qs.set_setting("demo", "enabled", True)
    assert qs.get_setting("demo", "enabled") is True
