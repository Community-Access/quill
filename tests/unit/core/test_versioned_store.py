from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.versioned_store import load_with_migration

# A toy store: the domain object is just an int "value"; the canonical on-disk
# shape is {"schema_version": 2, "value": N}; legacy is anything below v2.


def _parse(raw: dict[str, object]) -> int:
    value = raw.get("value", 0)
    return value if isinstance(value, int) else 0


def _serialize(value: int) -> dict[str, object]:
    return {"schema_version": 2, "value": value}


def _is_legacy(raw: dict[str, object]) -> bool:
    version = raw.get("schema_version")
    return not isinstance(version, int) or version < 2


def _load(path: Path) -> int:
    return load_with_migration(
        path,
        store_name="toy",
        parse=_parse,
        serialize=_serialize,
        is_legacy=_is_legacy,
        default=lambda: 0,
    )


def test_missing_file_returns_default_without_writing(tmp_path: Path) -> None:
    path = tmp_path / "toy.json"
    assert _load(path) == 0
    assert not path.exists()


def test_canonical_file_is_left_untouched(tmp_path: Path) -> None:
    path = tmp_path / "toy.json"
    path.write_text(json.dumps({"schema_version": 2, "value": 7}), encoding="utf-8")
    mtime = path.stat().st_mtime_ns
    assert _load(path) == 7
    assert path.stat().st_mtime_ns == mtime  # no churn
    assert not (tmp_path / "migration-backups").exists()


def test_legacy_file_is_migrated_and_backed_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    path = tmp_path / "toy.json"
    legacy = {"schema_version": 1, "value": 7, "stale": "x"}
    path.write_text(json.dumps(legacy), encoding="utf-8")

    assert _load(path) == 7

    # Rewritten to the canonical shape (stale key dropped, stamped v2).
    assert json.loads(path.read_text(encoding="utf-8")) == {"schema_version": 2, "value": 7}
    # Original backed up under the store name.
    backups = list((tmp_path / "migration-backups").glob("toy-v1-*.json"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text(encoding="utf-8")) == legacy
