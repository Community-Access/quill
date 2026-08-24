"""11.10: one file carrying the setup, out of one machine and into another.

OPML moves subscriptions and nothing else. What somebody actually built is
their favorites, the folders they filed them into, the places they saved,
their Go To order, their keys -- and none of that has ever travelled.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from quill.core import setup_transfer


def _seed(data_dir: Path, **files: object) -> None:
    for name, payload in files.items():
        (data_dir / name).write_text(json.dumps(payload), encoding="utf-8")


def test_an_export_carries_what_is_there_and_counts_what_is_not(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed(
        data,
        **{"radio_favorites.json": {"favorites": []}, "podcasts_library.json": {"shows": []}},
    )
    target = tmp_path / f"mine{setup_transfer.EXTENSION}"
    tally = setup_transfer.export_setup(
        data, target, app="Quill Radio", stamped="2026-08-24T10:00:00Z"
    )
    assert tally.done == 2
    assert tally.skipped == len(setup_transfer.ITEMS) - 2
    assert tally.failed == 0
    assert target.is_file()


def test_the_export_says_what_it_carried_and_what_it_skipped(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed(data, **{"quiet-hours.json": {"enabled": True}})
    target = tmp_path / f"mine{setup_transfer.EXTENSION}"
    tally = setup_transfer.export_setup(data, target, app="Cast", stamped="x")
    sentence = tally.sentence("Exported", target.name, noun="item")
    assert "1 done" in sentence
    assert "this machine has never made one" in sentence


def test_the_manifest_names_the_app_the_time_and_the_files(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed(data, **{"keymap.json": {"edit.undo": "Ctrl+Z"}})
    target = tmp_path / f"mine{setup_transfer.EXTENSION}"
    setup_transfer.export_setup(data, target, app="Quill Radio", stamped="2026-08-24T10:00:00Z")
    manifest = setup_transfer.read_manifest(target)
    assert manifest["app"] == "Quill Radio"
    assert manifest["created"] == "2026-08-24T10:00:00Z"
    assert manifest["files"] == ["keymap.json"]
    assert "Passwords are not included" in manifest["note"]


def test_a_round_trip_lands_the_same_bytes_on_the_other_machine(tmp_path: Path) -> None:
    here, there = tmp_path / "here", tmp_path / "there"
    here.mkdir()
    there.mkdir()
    _seed(here, **{"radio_favorites.json": {"favorites": [{"name": "WQXR"}]}})
    target = tmp_path / f"mine{setup_transfer.EXTENSION}"
    setup_transfer.export_setup(here, target, app="Quill Radio", stamped="x")
    tally = setup_transfer.import_setup(target, there)
    assert tally.done == 1
    restored = json.loads((there / "radio_favorites.json").read_text(encoding="utf-8"))
    assert restored == {"favorites": [{"name": "WQXR"}]}


def test_importing_overwrites_rather_than_merging(tmp_path: Path) -> None:
    """ "Move my setup" means the other machine ends up with this setup."""
    here, there = tmp_path / "here", tmp_path / "there"
    here.mkdir()
    there.mkdir()
    _seed(here, **{"radio_favorites.json": {"favorites": ["new"]}})
    _seed(there, **{"radio_favorites.json": {"favorites": ["old"]}})
    target = tmp_path / f"mine{setup_transfer.EXTENSION}"
    setup_transfer.export_setup(here, target, app="Quill Radio", stamped="x")
    setup_transfer.import_setup(target, there)
    assert json.loads((there / "radio_favorites.json").read_text(encoding="utf-8")) == {
        "favorites": ["new"]
    }


def test_a_file_the_inventory_does_not_name_is_never_written(tmp_path: Path) -> None:
    """A setup file is not a way to drop an arbitrary file into a data folder."""
    target = tmp_path / f"evil{setup_transfer.EXTENSION}"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("radio_favorites.json", json.dumps({"favorites": []}))
        archive.writestr("remote-site-secrets.json", json.dumps({"token": "hunter2"}))
        archive.writestr(setup_transfer.MANIFEST_NAME, json.dumps({"files": []}))
    there = tmp_path / "there"
    there.mkdir()
    setup_transfer.import_setup(target, there)
    assert (there / "radio_favorites.json").is_file()
    assert not (there / "remote-site-secrets.json").exists()


def test_a_corrupt_entry_is_counted_as_failed_rather_than_written(tmp_path: Path) -> None:
    target = tmp_path / f"broken{setup_transfer.EXTENSION}"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("radio_favorites.json", "{not json")
        archive.writestr(setup_transfer.MANIFEST_NAME, json.dumps({"files": []}))
    there = tmp_path / "there"
    there.mkdir()
    tally = setup_transfer.import_setup(target, there)
    assert tally.failed == 1
    assert not (there / "radio_favorites.json").exists()


def test_a_file_that_is_not_a_setup_file_says_so(tmp_path: Path) -> None:
    stray = tmp_path / "notes.txt"
    stray.write_text("hello", encoding="utf-8")
    assert setup_transfer.read_manifest(stray) == {}
    tally = setup_transfer.import_setup(stray, tmp_path)
    assert tally.failed == 1
    assert "not a Quill setup file" in tally.sentence("Restored", "notes.txt")


def test_a_checklist_limits_what_is_restored(tmp_path: Path) -> None:
    here, there = tmp_path / "here", tmp_path / "there"
    here.mkdir()
    there.mkdir()
    _seed(here, **{"radio_favorites.json": {"a": 1}, "keymap.json": {"b": 2}})
    target = tmp_path / f"mine{setup_transfer.EXTENSION}"
    setup_transfer.export_setup(here, target, app="Quill Radio", stamped="x")
    setup_transfer.import_setup(target, there, only={"keymap.json"})
    assert (there / "keymap.json").is_file()
    assert not (there / "radio_favorites.json").exists()


def test_no_secret_store_is_in_the_inventory() -> None:
    """The rule, enforced rather than asserted in a docstring."""
    carried = {item.filename for item in setup_transfer.ITEMS}
    forbidden = {
        "remote-site-secrets.json",
        "unlock_codes.json",
        "personal.json",
        "components.state.json",
    }
    assert carried & forbidden == set()


def test_every_item_says_what_it_is_and_which_app_owns_it() -> None:
    for item in setup_transfer.ITEMS:
        assert item.filename.endswith(".json")
        assert item.label and item.label[0].islower(), item.filename
        assert item.app in ("radio", "cast", "both"), item.filename


def test_the_contents_sentence_reads_as_a_list(tmp_path: Path) -> None:
    text = setup_transfer.describe_contents(["radio_favorites.json", "quiet-hours.json"])
    assert text.startswith("It carries your favorite stations")
    assert "your quiet hours" in text
    assert setup_transfer.describe_contents([]) == "This setup file is empty."


def test_an_unknown_entry_is_counted_rather_than_hidden() -> None:
    text = setup_transfer.describe_contents(["quiet-hours.json", "something-new.json"])
    assert "1 item(s) this version does not recognise" in text
