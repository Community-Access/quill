"""Tests for the one-prompt-store-truth migration (AI Library, Phase 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

import quill.core.assistant_prompts as assistant_prompts
from quill.core.prompt_library import PromptLibrary
from quill.core.prompt_migration import (
    MIGRATED_ID_PREFIX,
    consolidate_prompts,
    consolidate_prompts_quietly,
)


def _seed_legacy(prompts: list[assistant_prompts.CustomPrompt]) -> None:
    assistant_prompts.save_custom_prompts(prompts)


def _canonical_library(tmp_path: Path) -> PromptLibrary:
    from quill.core.paths import app_data_dir

    return PromptLibrary(app_data_dir() / "prompts.json")


def test_migration_copies_legacy_prompts_into_canonical_library(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    _seed_legacy([
        assistant_prompts.CustomPrompt(
            prompt_id="p-1", title="Refine Draft", template="Rewrite {selection}", shortcut="ctrl+r"
        ),
        assistant_prompts.CustomPrompt(
            prompt_id="p-2", title="Tighten", template="Shorten {selection}"
        ),
    ])

    migrated = consolidate_prompts()

    assert set(migrated) == {f"{MIGRATED_ID_PREFIX}p-1", f"{MIGRATED_ID_PREFIX}p-2"}
    lib = _canonical_library(tmp_path)
    p1 = lib.find_by_id(f"{MIGRATED_ID_PREFIX}p-1")
    assert p1 is not None
    assert p1.name == "Refine Draft"
    assert p1.text == "Rewrite {selection}"
    assert p1.shortcut == "ctrl+r"
    assert p1.source == "migrated"
    assert not p1.is_builtin


def test_migration_is_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    _seed_legacy([
        assistant_prompts.CustomPrompt(prompt_id="p-1", title="One", template="Do {selection}"),
    ])

    first = consolidate_prompts()
    second = consolidate_prompts()

    assert first == [f"{MIGRATED_ID_PREFIX}p-1"]
    assert second == []  # nothing new on the second run
    lib = _canonical_library(tmp_path)
    migrated = [p for p in lib.all() if p.source == "migrated"]
    assert len(migrated) == 1  # not duplicated


def test_migration_is_non_destructive_to_legacy_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    _seed_legacy([
        assistant_prompts.CustomPrompt(prompt_id="p-1", title="Keep", template="Edit {selection}"),
    ])

    consolidate_prompts()

    # The legacy store is untouched, so the migration reverts by dropping the copies.
    remaining = assistant_prompts.load_custom_prompts()
    assert [p.prompt_id for p in remaining] == ["p-1"]


def test_migration_preserves_existing_user_edits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    _seed_legacy([
        assistant_prompts.CustomPrompt(prompt_id="p-1", title="Legacy", template="v1 {selection}"),
    ])
    # First migration, then the user edits the migrated prompt in the library.
    consolidate_prompts()
    lib = _canonical_library(tmp_path)
    lib.update(f"{MIGRATED_ID_PREFIX}p-1", text="user edited {selection}")

    # A later migration must not clobber the user's edit.
    consolidate_prompts()
    lib2 = _canonical_library(tmp_path)
    edited = lib2.find_by_id(f"{MIGRATED_ID_PREFIX}p-1")
    assert edited is not None
    assert edited.text == "user edited {selection}"


def test_migration_handles_empty_legacy_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    assert consolidate_prompts() == []
    consolidate_prompts_quietly()  # never raises


def test_upsert_external_refuses_to_overwrite_builtin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    lib = PromptLibrary(tmp_path / "prompts.json")
    builtin = next(p for p in lib.all() if p.is_builtin)
    with pytest.raises(ValueError):
        lib.upsert_external(id=builtin.id, name="x", text="y {selection}")
