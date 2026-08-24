"""Cast has no backup, only an export -- until now (list.md 5.6).

Radio has had Back Up / Restore since #1193: a real archive, restored in place
with the running app reloaded afterwards. Cast had Export My Data, a one-shot
readable JSON, and the shared setup transfer. Neither is a restore.

Cast's library is the more painful of the two apps' to lose. A station list can
be rebuilt from a directory in an afternoon; subscriptions, folders, playlists,
positions, notes and statistics are years of accumulated choices that exist
nowhere else.

The tests that matter here are the ones about a *hostile or damaged* archive,
because restore is the one verb in the app that writes over everything at once.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from quill.core.podcasts import backup


def _data_dir(tmp_path: Path, *, files: tuple[str, ...] = ()) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    for name in files or backup.CAST_DATA_FILES:
        (data / name).write_text(json.dumps({"name": name}), encoding="utf-8")
    return data


def test_a_backup_round_trips_the_whole_library(tmp_path: Path) -> None:
    data = _data_dir(tmp_path)
    dest = tmp_path / backup.suggested_filename()

    backup.create_backup(data, dest, shows=12)
    restored = tmp_path / "restored"
    result = backup.restore_backup(dest, restored)

    assert set(result.data_files) == set(backup.CAST_DATA_FILES)
    for name in backup.CAST_DATA_FILES:
        assert json.loads((restored / name).read_text(encoding="utf-8"))["name"] == name


def test_the_json_is_copied_verbatim_rather_than_re_serialised(tmp_path: Path) -> None:
    """So a backup made by one version restores cleanly into another, and a
    field this build has never heard of survives the round trip."""
    data = _data_dir(tmp_path, files=("podcasts_library.json",))
    (data / "podcasts_library.json").write_text(
        '{"shows": [], "a_field_from_the_future": 7}', encoding="utf-8"
    )
    dest = tmp_path / "b.qcbackup"

    backup.create_backup(data, dest)
    restored = tmp_path / "restored"
    backup.restore_backup(dest, restored)

    assert "a_field_from_the_future" in (restored / "podcasts_library.json").read_text(
        encoding="utf-8"
    )


def test_a_library_that_has_not_been_used_yet_still_backs_up(tmp_path: Path) -> None:
    """An empty library is a perfectly good thing to back up before starting,
    and a missing file is not an error."""
    data = _data_dir(tmp_path, files=("podcasts_library.json",))
    dest = tmp_path / "b.qcbackup"

    backup.create_backup(data, dest)

    assert backup.read_manifest(dest).data_files == ["podcasts_library.json"]


# -- downloaded episodes --------------------------------------------------------


def test_episodes_are_left_out_unless_asked_for(tmp_path: Path) -> None:
    """Tens of gigabytes that can be downloaded again, beside 40 KB that
    cannot. The small thing has to be quick and reliable."""
    data = _data_dir(tmp_path, files=("podcasts_library.json",))
    downloads = tmp_path / "podcasts"
    (downloads / "A Show").mkdir(parents=True)
    (downloads / "A Show" / "episode.mp3").write_bytes(b"audio")
    dest = tmp_path / "b.qcbackup"

    backup.create_backup(data, dest, downloads_dir=downloads)

    assert backup.read_manifest(dest).episodes == 0


def test_episodes_keep_their_folders_when_included(tmp_path: Path) -> None:
    """The per-show folder is how the library finds a downloaded file again;
    flattening them would restore audio the app cannot see."""
    data = _data_dir(tmp_path, files=("podcasts_library.json",))
    downloads = tmp_path / "podcasts"
    (downloads / "A Show").mkdir(parents=True)
    (downloads / "A Show" / "episode.mp3").write_bytes(b"audio")
    dest = tmp_path / "b.qcbackup"

    backup.create_backup(data, dest, downloads_dir=downloads, include_episodes=True)
    restored_downloads = tmp_path / "restored-podcasts"
    result = backup.restore_backup(dest, tmp_path / "restored", downloads_dir=restored_downloads)

    assert result.episodes == ("A Show/episode.mp3",)
    assert (restored_downloads / "A Show" / "episode.mp3").read_bytes() == b"audio"


# -- a damaged or hostile archive -----------------------------------------------


def test_a_file_that_is_not_a_backup_says_so(tmp_path: Path) -> None:
    junk = tmp_path / "holiday.zip"
    with zipfile.ZipFile(junk, "w") as zf:
        zf.writestr("hello.txt", "hi")

    with pytest.raises(backup.CastBackupError, match="not a QUILL Cast backup"):
        backup.read_manifest(junk)


def test_a_radio_backup_is_refused_rather_than_half_restored(tmp_path: Path) -> None:
    """The two apps' archives look alike from the outside. Restoring one into
    the other would write a station list over a podcast library."""
    fake = tmp_path / "radio.qcbackup"
    with zipfile.ZipFile(fake, "w") as zf:
        zf.writestr("quill-cast-backup.json", json.dumps({"schema": 1, "app": "quill-radio"}))

    with pytest.raises(backup.CastBackupError):
        backup.read_manifest(fake)


def test_a_newer_backup_is_refused_with_a_reason(tmp_path: Path) -> None:
    future = tmp_path / "future.qcbackup"
    with zipfile.ZipFile(future, "w") as zf:
        zf.writestr("quill-cast-backup.json", json.dumps({"schema": 99, "app": "quill-cast"}))

    with pytest.raises(backup.CastBackupError, match="newer version"):
        backup.read_manifest(future)


def test_a_corrupt_zip_costs_the_restore_and_nothing_else(tmp_path: Path) -> None:
    broken = tmp_path / "broken.qcbackup"
    broken.write_bytes(b"not a zip at all")

    with pytest.raises(backup.CastBackupError):
        backup.restore_backup(broken, tmp_path / "restored")


def test_an_archive_cannot_write_outside_the_data_folder(tmp_path: Path) -> None:
    """Zip-slip. A backup is not a place to be clever about hostile input, so
    an entry naming .. is refused outright rather than sanitised."""
    hostile = tmp_path / "hostile.qcbackup"
    with zipfile.ZipFile(hostile, "w") as zf:
        zf.writestr("quill-cast-backup.json", json.dumps({"schema": 1, "app": "quill-cast"}))
        zf.writestr("data/../../escaped.json", "{}")
        zf.writestr("episodes/../../escaped.mp3", "x")

    restored = tmp_path / "restored"
    downloads = tmp_path / "restored-downloads"
    result = backup.restore_backup(hostile, restored, downloads_dir=downloads)

    assert result.data_files == ()
    assert result.episodes == ()
    assert not (tmp_path / "escaped.json").exists()
    assert not (tmp_path / "escaped.mp3").exists()


def test_an_unknown_state_file_is_not_restored(tmp_path: Path) -> None:
    """Only the known filenames are accepted, so an archive cannot drop
    anything it likes into the data folder under a plausible name."""
    sneaky = tmp_path / "sneaky.qcbackup"
    with zipfile.ZipFile(sneaky, "w") as zf:
        zf.writestr("quill-cast-backup.json", json.dumps({"schema": 1, "app": "quill-cast"}))
        zf.writestr("data/settings.json", "{}")
        zf.writestr("data/podcasts_library.json", "{}")

    restored = tmp_path / "restored"
    result = backup.restore_backup(sneaky, restored)

    assert result.data_files == ("podcasts_library.json",)
    assert not (restored / "settings.json").exists()


def test_a_failed_write_leaves_no_half_backup(tmp_path: Path) -> None:
    """A half-written zip is worse than none, because somebody would restore
    from it."""
    data = _data_dir(tmp_path, files=("podcasts_library.json",))
    dest = tmp_path / "nope" / "b.qcbackup"
    dest.parent.mkdir()
    dest.parent.chmod(0o500)  # best-effort; Windows ignores this
    try:
        try:
            backup.create_backup(data, dest)
        except backup.CastBackupError:
            assert not dest.exists()
    finally:
        dest.parent.chmod(0o700)


# -- what it says ---------------------------------------------------------------


def test_the_confirm_names_the_date_and_the_size(tmp_path: Path) -> None:
    """The two facts somebody needs to spot the wrong file *before* it
    replaces the right one."""
    data = _data_dir(tmp_path, files=("podcasts_library.json",))
    dest = tmp_path / "b.qcbackup"
    backup.create_backup(data, dest, shows=12)

    said = backup.read_manifest(dest).describe()

    assert "12 podcasts" in said
    assert said.count("-") >= 2  # the date


def test_one_podcast_reads_as_one_podcast() -> None:
    """Read aloud, "1 podcasts" makes somebody stop trusting the sentence
    that is about to overwrite their library."""
    said = backup.BackupManifest(shows=1, created="2026-08-24T00:00:00").describe()

    assert "1 podcast." in said
    assert "1 podcasts" not in said


def test_the_restore_summary_counts_rather_than_lists() -> None:
    """Ten filenames read aloud is not an answer to "did it work"."""
    said = backup.RestoreResult(("a.json", "b.json"), ("show/ep.mp3",)).summary()

    assert said == "Restored 2 data files and 1 downloaded episode."


def test_an_empty_restore_says_so_rather_than_claiming_success() -> None:
    assert "Nothing was restored" in backup.RestoreResult().summary()


def test_the_suggested_name_is_dated() -> None:
    """The first thing anybody does with a second backup is try to tell it
    from the first."""
    name = backup.suggested_filename(stamp="2026-08-24T10:00:00")

    assert name == "quill-cast-backup-2026-08-24.qcbackup"


def test_the_two_apps_use_different_extensions() -> None:
    """So a file dialog cannot offer one app's archive to the other."""
    from quill.core.radio import backup as radio_backup

    assert backup.BACKUP_SUFFIX != radio_backup.BACKUP_SUFFIX
