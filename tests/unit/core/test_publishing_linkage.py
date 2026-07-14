from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core import paths
from quill.core.publishing_linkage import (
    PublishingLinkageEntry,
    apply_publishing_linkage_to_source_metadata,
    get_publishing_linkage,
    load_publishing_linkage_registry,
    publishing_linkage_from_source_metadata,
    publishing_linkage_path,
    remove_publishing_linkage,
    save_publishing_linkage_registry,
    upsert_publishing_linkage,
)


@pytest.fixture
def quill_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated QUILL_DATA_DIR that holds even when ``--basetemp`` points

    outside ``$HOME``. ``paths._is_constrained_to_home`` (H-1-core) rejects
    a dev override that isn't under ``Path.home()``, so this fixture patches
    ``Path.home`` itself rather than relying on the default pytest temp
    directory's location, matching the pattern in test_publishing.py's
    ``publishing_data_env`` fixture.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    data_dir = fake_home / "quill-data"
    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setenv("QUILL_DATA_DIR", str(data_dir))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE_ROOT", raising=False)
    return data_dir


def _entry(**overrides: object) -> PublishingLinkageEntry:
    defaults: dict[str, object] = {
        "provider_id": "wordpress",
        "site_url": "https://example.com",
        "remote_id": "22",
        "remote_url": "https://example.com/about",
        "remote_title": "About page",
        "content_kind": "page",
        "authoring_surface": "markdown",
        "open_representation": "readable_markdown",
        "status": "publish",
        "updated_at": "2026-06-18T12:00:00",
    }
    defaults.update(overrides)
    return PublishingLinkageEntry(**defaults)  # type: ignore[arg-type]


def test_load_publishing_linkage_registry_defaults_to_empty(quill_data_dir: Path) -> None:
    assert load_publishing_linkage_registry() == {}


def test_upsert_and_get_publishing_linkage_round_trip(quill_data_dir: Path, tmp_path: Path) -> None:
    target = tmp_path / "my-post.md"
    target.write_text("hello", encoding="utf-8")
    entry = _entry()

    upsert_publishing_linkage(target, entry)

    assert get_publishing_linkage(target) == entry


def test_get_publishing_linkage_canonicalizes_relative_paths(
    quill_data_dir: Path, tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "my-post.md"
    target.write_text("hello", encoding="utf-8")
    entry = _entry()
    upsert_publishing_linkage(target, entry)

    monkeypatch.chdir(tmp_path)
    relative = Path("my-post.md")

    assert get_publishing_linkage(relative) == entry


def test_get_publishing_linkage_returns_none_for_unknown_path(
    quill_data_dir: Path, tmp_path: Path
) -> None:
    assert get_publishing_linkage(tmp_path / "missing.md") is None


def test_upsert_publishing_linkage_overwrites_existing_entry(
    quill_data_dir: Path, tmp_path: Path
) -> None:
    target = tmp_path / "my-post.md"
    upsert_publishing_linkage(target, _entry(status="draft"))
    upsert_publishing_linkage(target, _entry(status="publish"))

    entry = get_publishing_linkage(target)
    assert entry is not None
    assert entry.status == "publish"


def test_remove_publishing_linkage_deletes_entry(quill_data_dir: Path, tmp_path: Path) -> None:
    target = tmp_path / "my-post.md"
    upsert_publishing_linkage(target, _entry())

    remove_publishing_linkage(target)

    assert get_publishing_linkage(target) is None


def test_remove_publishing_linkage_is_a_no_op_for_unknown_path(
    quill_data_dir: Path, tmp_path: Path
) -> None:
    remove_publishing_linkage(tmp_path / "missing.md")
    assert load_publishing_linkage_registry() == {}


def test_load_publishing_linkage_registry_tolerates_corrupt_json(
    quill_data_dir: Path,
) -> None:
    path = publishing_linkage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    assert load_publishing_linkage_registry() == {}


def test_load_publishing_linkage_registry_tolerates_non_dict_entries_value(
    quill_data_dir: Path,
) -> None:
    path = publishing_linkage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"entries": "nope"}), encoding="utf-8")

    assert load_publishing_linkage_registry() == {}


def test_load_publishing_linkage_registry_skips_malformed_entry_values(
    quill_data_dir: Path,
) -> None:
    path = publishing_linkage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"entries": {"/a/path": "not-a-dict", "/b/path": {"provider_id": "x"}}}),
        encoding="utf-8",
    )

    registry = load_publishing_linkage_registry()

    assert "/a/path" not in registry
    assert registry["/b/path"].provider_id == "x"


def test_save_publishing_linkage_registry_writes_expected_shape(
    quill_data_dir: Path, tmp_path: Path
) -> None:
    target = tmp_path / "my-post.md"
    save_publishing_linkage_registry({str(target.resolve()): _entry()})

    raw = json.loads(publishing_linkage_path().read_text(encoding="utf-8"))
    assert raw["entries"][str(target.resolve())]["provider_id"] == "wordpress"


def test_publishing_linkage_from_source_metadata_returns_none_when_not_remote() -> None:
    assert publishing_linkage_from_source_metadata({"source_kind": "text"}) is None
    assert publishing_linkage_from_source_metadata({}) is None


def test_publishing_linkage_from_source_metadata_returns_none_without_provider_id() -> None:
    metadata: dict[str, object] = {
        "source_kind": "publishing_remote",
        "publishing_provider_id": "  ",
    }
    assert publishing_linkage_from_source_metadata(metadata) is None


def test_publishing_linkage_from_source_metadata_extracts_all_fields() -> None:
    metadata: dict[str, object] = {
        "source_kind": "publishing_remote",
        "source_label": "from publishing",
        "publishing_provider_id": "wordpress",
        "publishing_site_url": "https://example.com",
        "publishing_remote_id": "22",
        "publishing_remote_url": "https://example.com/about",
        "publishing_remote_title": "About page",
        "publishing_content_kind": "page",
        "publishing_authoring_surface": "markdown",
        "publishing_open_representation": "readable_markdown",
        "publishing_status": "publish",
        "publishing_updated_at": "2026-06-18T12:00:00",
    }

    entry = publishing_linkage_from_source_metadata(metadata)

    assert entry == _entry()


def test_apply_publishing_linkage_to_source_metadata_sets_expected_keys() -> None:
    metadata: dict[str, object] = {"csv_open_mode": "grid", "engine": "pandoc"}
    entry = _entry()

    apply_publishing_linkage_to_source_metadata(metadata, entry)

    assert metadata["source_kind"] == "publishing_remote"
    assert metadata["source_label"] == "from publishing"
    assert metadata["publishing_provider_id"] == "wordpress"
    assert metadata["publishing_remote_url"] == "https://example.com/about"
    assert metadata["publishing_updated_at"] == "2026-06-18T12:00:00"
    # Unrelated, pre-existing keys are left untouched.
    assert metadata["csv_open_mode"] == "grid"
    assert metadata["engine"] == "pandoc"


def test_apply_then_extract_round_trips_through_source_metadata() -> None:
    metadata: dict[str, object] = {}
    entry = _entry()

    apply_publishing_linkage_to_source_metadata(metadata, entry)
    extracted = publishing_linkage_from_source_metadata(metadata)

    assert extracted == entry
