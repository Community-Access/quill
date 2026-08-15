"""Carrying your place between machines, end to end.

Everything underneath this existed and nothing connected it. These are the
seams the connection had to get right: a phrase that carries the key, a vault
that refuses to be overwritten, two stores that stay two, and a merge that
never silently loses a place.
"""

from __future__ import annotations

import json

import pytest

from quill.core.media.positions import PositionStore
from quill.core.radio.resume import ResumeStore, merge_resume_points
from quill.core.sync import places, places_config, vault_file
from quill.core.sync import recovery_phrase as rp
from quill.core.sync.places_config import PlacesConfig, default_device_name

# -- the recovery phrase -------------------------------------------------


def test_a_phrase_is_eight_words_from_the_list() -> None:
    phrase = rp.generate()
    assert rp.word_count(phrase) == rp.PHRASE_WORDS
    assert rp.is_from_word_list(phrase)
    assert rp.is_valid(phrase)


def test_the_word_list_is_fixed_and_exactly_a_power_of_two() -> None:
    # The list *is* the format: adding or reordering a word silently
    # invalidates every phrase already written down.
    assert len(rp.WORDS) == 256
    assert len(set(rp.WORDS)) == 256
    assert all(word.isalpha() and word.islower() for word in rp.WORDS)


def test_typing_it_off_paper_is_forgiving() -> None:
    # Somebody copying eight words will punctuate them however they like.
    assert rp.normalise("  Apple, BANJO-cedar  ") == "apple banjo cedar"


def test_a_wrong_word_is_named_rather_than_just_refused() -> None:
    # With eight words read off paper, "one of these is wrong" means checking
    # all eight again.
    problem = rp.describe_problem(" ".join([*rp.WORDS[:7], "zzzz"]))
    assert "zzzz" in problem


def test_a_short_phrase_says_how_short() -> None:
    assert "2 words" in rp.describe_problem("apple banjo")


def test_the_phrase_reads_back_numbered_for_writing_down() -> None:
    assert rp.spoken("apple banjo") == "1, apple. 2, banjo."


# -- the vault -----------------------------------------------------------


def test_the_second_machine_derives_the_same_key_from_the_same_phrase(tmp_path) -> None:
    phrase = rp.generate()
    first = vault_file.load_or_create(tmp_path, phrase)
    second = vault_file.load_or_create(tmp_path, phrase)
    assert first.created is True
    assert second.created is False
    assert first.key.key == second.key.key


def test_a_wrong_phrase_is_caught_before_anything_is_read(tmp_path) -> None:
    vault_file.load_or_create(tmp_path, rp.generate())
    with pytest.raises(vault_file.VaultError) as caught:
        vault_file.open_existing(tmp_path, rp.generate())
    assert "does not match" in str(caught.value)
    assert "nothing was changed" in str(caught.value)


def test_a_vault_is_never_overwritten(tmp_path) -> None:
    # Overwriting would orphan every commit already there -- unreadable
    # forever, while the machine that did it appears to have synced correctly.
    vault_file.load_or_create(tmp_path, rp.generate())
    with pytest.raises(vault_file.VaultError):
        vault_file.create(tmp_path, rp.generate())


def test_a_vault_from_a_newer_build_is_refused_not_guessed_at(tmp_path) -> None:
    phrase = rp.generate()
    vault_file.load_or_create(tmp_path, phrase)
    path = vault_file.vault_path(tmp_path)
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["version"] = vault_file.VAULT_VERSION + 1
    path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(vault_file.VaultError) as caught:
        vault_file.open_existing(tmp_path, phrase)
    assert "newer version" in str(caught.value)


# -- syncing a place -----------------------------------------------------


def _book(tmp_path, name: str = "book.mp3"):
    path = tmp_path / name
    path.write_bytes(b"x" * 4096)
    return path


def test_a_place_saved_on_one_machine_arrives_on_the_other(tmp_path) -> None:
    remote = tmp_path / "remote"
    remote.mkdir()
    laptop, desktop = tmp_path / "laptop", tmp_path / "desktop"
    laptop.mkdir()
    desktop.mkdir()
    book = _book(tmp_path)
    phrase = rp.generate()

    PositionStore(laptop).remember(book, 600_000, duration_ms=3_600_000)
    key = vault_file.load_or_create(remote, phrase).key
    sent = places.sync_places(data_dir=laptop, remote_dir=remote, vault=key, device="laptop")
    assert sent.pushed >= 1

    key2 = vault_file.load_or_create(remote, phrase).key
    got = places.sync_places(data_dir=desktop, remote_dir=remote, vault=key2, device="desktop")
    assert got.pulled >= 1
    assert PositionStore(desktop).position_for(book) == 600_000


def test_syncing_twice_in_a_row_manufactures_no_history(tmp_path) -> None:
    # A machine left running would otherwise grow a commit log made entirely of
    # duplicates, on somebody's cloud folder.
    remote = tmp_path / "remote"
    remote.mkdir()
    local = tmp_path / "local"
    local.mkdir()
    PositionStore(local).remember(_book(tmp_path), 600_000, duration_ms=3_600_000)
    key = vault_file.load_or_create(remote, rp.generate()).key
    first = places.sync_places(data_dir=local, remote_dir=remote, vault=key, device="one")
    second = places.sync_places(data_dir=local, remote_dir=remote, vault=key, device="one")
    assert first.changed is True
    assert second.changed is False
    assert second.summary() == "Everything was already up to date."


def test_a_missing_folder_is_a_sentence_not_a_crash(tmp_path) -> None:
    key = vault_file.load_or_create(tmp_path, rp.generate()).key
    report = places.sync_places(
        data_dir=tmp_path, remote_dir=tmp_path / "gone", vault=key, device="one"
    )
    assert report.problems
    # Never "everything was already up to date", which is the most misleading
    # thing this feature could say about a folder that has gone missing.
    assert "sync folder is not there" in report.summary()


def test_the_two_stores_stay_two(tmp_path) -> None:
    # The media store keys on a file's contents and the radio store on a
    # normalised stream identity, and no single key can mean both.
    assert places.PLACES_STORES == ("positions", "recordings")
    key = vault_file.load_or_create(tmp_path, rp.generate()).key
    one = places.engine_for("positions", data_dir=tmp_path, vault=key, device="d")
    two = places.engine_for("recordings", data_dir=tmp_path, vault=key, device="d")
    assert one.log_path != two.log_path
    assert one.entity_type != two.entity_type


def test_a_recording_position_syncs_too(tmp_path) -> None:
    remote = tmp_path / "remote"
    remote.mkdir()
    laptop, desktop = tmp_path / "laptop", tmp_path / "desktop"
    laptop.mkdir()
    desktop.mkdir()
    phrase = rp.generate()
    ResumeStore(laptop).remember(
        "https://a.example/chapter4.mp3", 600_000, duration_ms=7_200_000, label="The Moonstone"
    )
    key = vault_file.load_or_create(remote, phrase).key
    places.sync_places(data_dir=laptop, remote_dir=remote, vault=key, device="laptop")
    places.sync_places(data_dir=desktop, remote_dir=remote, vault=key, device="desktop")
    point = ResumeStore(desktop).position_for("https://a.example/chapter4.mp3")
    assert point is not None
    assert point.position_ms == 600_000
    assert point.label == "The Moonstone"


# -- merging -------------------------------------------------------------


def test_the_most_recent_save_wins_and_a_real_disagreement_is_reported() -> None:
    older = {"position_ms": 100_000, "saved_at": 10.0, "label": "Book", "url": "u"}
    newer = {"position_ms": 900_000, "saved_at": 20.0, "label": "", "url": "u"}
    merged, conflicts = merge_resume_points(older, newer)
    assert merged["position_ms"] == 900_000
    # A label only one machine knew is kept, or the row could never be listed.
    assert merged["label"] == "Book"
    assert conflicts and "different places" in conflicts[0].message


def test_a_few_seconds_apart_is_not_a_disagreement() -> None:
    first = {"position_ms": 600_000, "saved_at": 10.0, "url": "u"}
    second = {"position_ms": 601_000, "saved_at": 20.0, "url": "u"}
    _merged, conflicts = merge_resume_points(first, second)
    assert conflicts == []


# -- the settings --------------------------------------------------------


def test_sync_is_off_until_it_is_asked_for() -> None:
    config = PlacesConfig()
    assert config.enabled is False
    assert config.is_ready is False
    assert "not being carried" in config.describe()


def test_the_settings_line_says_what_is_still_missing() -> None:
    assert "Choose a folder" in PlacesConfig(enabled=True).describe()
    assert "recovery phrase" in PlacesConfig(enabled=True, remote_dir="X").describe()
    ready = PlacesConfig(enabled=True, remote_dir="X", has_phrase=True, device="Laptop")
    assert ready.is_ready is True
    assert "Laptop" in ready.describe()


def test_the_settings_survive_a_restart(tmp_path) -> None:
    config = PlacesConfig(enabled=True, remote_dir=str(tmp_path), device="Laptop", has_phrase=True)
    places_config.save(tmp_path, config)
    assert places_config.load(tmp_path).device == "Laptop"


def test_a_damaged_settings_file_reads_as_not_set_up(tmp_path) -> None:
    places_config.config_path(tmp_path).write_text("{not json", encoding="utf-8")
    assert places_config.load(tmp_path).enabled is False


def test_the_phrase_is_never_in_the_settings_file(tmp_path) -> None:
    # It is the key. It lives in the platform credential store, and the file
    # records only that one was saved.
    places_config.save(tmp_path, PlacesConfig(enabled=True, has_phrase=True))
    written = places_config.config_path(tmp_path).read_text(encoding="utf-8")
    assert "phrase" not in written.replace("has_phrase", "")


def test_this_machine_has_a_name_without_being_asked() -> None:
    assert default_device_name().strip()
