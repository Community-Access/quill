"""Tests for Work Personas (#896): the persistent named-bundle store."""

from __future__ import annotations

from pathlib import Path

from quill.core.work_persona import WorkPersona, WorkPersonaStore


def test_create_adds_and_persists(tmp_path: Path) -> None:
    store = WorkPersonaStore(tmp_path)
    persona = WorkPersona(name="School", technical_profile="essential")
    assert store.create(persona) is True
    assert len(store) == 1

    reloaded = WorkPersonaStore(tmp_path)
    assert len(reloaded) == 1
    assert reloaded.get("School").technical_profile == "essential"


def test_create_rejects_duplicate_name(tmp_path: Path) -> None:
    store = WorkPersonaStore(tmp_path)
    store.create(WorkPersona(name="Work"))
    assert store.create(WorkPersona(name="Work")) is False
    assert len(store) == 1


def test_update_replaces_stored_persona(tmp_path: Path) -> None:
    store = WorkPersonaStore(tmp_path)
    store.create(WorkPersona(name="Hobby", technical_profile="essential"))
    store.update(WorkPersona(name="Hobby", technical_profile="full_quill"))
    assert store.get("Hobby").technical_profile == "full_quill"
    assert len(store) == 1


def test_remove_deletes_a_persona(tmp_path: Path) -> None:
    store = WorkPersonaStore(tmp_path)
    store.create(WorkPersona(name="School"))
    store.remove("School")
    assert len(store) == 0
    assert store.get("School") is None


def test_remove_missing_persona_is_a_no_op(tmp_path: Path) -> None:
    store = WorkPersonaStore(tmp_path)
    store.remove("Nonexistent")
    assert len(store) == 0


def test_all_returns_personas_sorted_by_name(tmp_path: Path) -> None:
    store = WorkPersonaStore(tmp_path)
    store.create(WorkPersona(name="Zebra"))
    store.create(WorkPersona(name="apple"))
    store.create(WorkPersona(name="Mango"))
    names = [p.name for p in store.all()]
    assert names == ["apple", "Mango", "Zebra"]


def test_favorite_files_and_keymap_round_trip(tmp_path: Path) -> None:
    store = WorkPersonaStore(tmp_path)
    persona = WorkPersona(
        name="Novel",
        technical_profile="author_or_student",
        working_folder=str(tmp_path / "novel"),
        favorite_files=("chapter1.md", "outline.md"),
        keymap_profile="profile_sr_friendly",
    )
    store.create(persona)
    reloaded = WorkPersonaStore(tmp_path)
    got = reloaded.get("Novel")
    assert got.favorite_files == ("chapter1.md", "outline.md")
    assert got.keymap_profile == "profile_sr_friendly"
    assert got.working_folder == str(tmp_path / "novel")


def test_corrupt_file_starts_fresh(tmp_path: Path) -> None:
    (tmp_path / "work_personas.json").write_text("not json", encoding="utf-8")
    store = WorkPersonaStore(tmp_path)
    assert len(store) == 0


def test_display_label_includes_working_folder_when_set() -> None:
    with_folder = WorkPersona(name="Work", working_folder="C:/Work")
    assert with_folder.display_label() == "Work — C:/Work"
    without_folder = WorkPersona(name="Hobby")
    assert without_folder.display_label() == "Hobby"
