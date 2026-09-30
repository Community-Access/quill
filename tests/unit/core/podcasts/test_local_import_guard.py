"""Copy, verify, then create the record (ear.md R9).

The order is the point. Get it the other way round and a failed import leaves a
visible row pointing at nothing, which is worse than no import at all: the listener
now has to work out what it is and how to get rid of it.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts.local_import_guard import (
    HEADROOM_BYTES,
    Check,
    discard,
    enough_room,
    verify_copy,
)


def test_a_check_is_truthy_so_it_reads_as_a_condition() -> None:
    assert Check(True)
    assert not Check(False, "no")


def test_room_is_checked_before_a_byte_is_copied(tmp_path: Path) -> None:
    source = tmp_path / "small.mp3"
    source.write_bytes(b"x" * 1024)
    assert enough_room(source, tmp_path)


def test_a_file_bigger_than_the_disk_is_refused_with_both_numbers(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "huge.mp3"
    source.write_bytes(b"x" * 2048)

    class _Usage:
        free = 1024

    monkeypatch.setattr(
        "quill.core.podcasts.local_import_guard.shutil.disk_usage", lambda _p: _Usage()
    )
    check = enough_room(source, tmp_path)
    assert not check
    assert "not enough room" in check.message
    assert "free" in check.message
    assert "Nothing has been changed" in check.message


def test_headroom_is_demanded_beyond_the_file_itself(tmp_path: Path, monkeypatch) -> None:
    """A copy that exactly fills the disk leaves nothing for the library write."""
    source = tmp_path / "exact.mp3"
    source.write_bytes(b"x" * 1024)

    class _Usage:
        free = 1024 + HEADROOM_BYTES - 1

    monkeypatch.setattr(
        "quill.core.podcasts.local_import_guard.shutil.disk_usage", lambda _p: _Usage()
    )
    assert not enough_room(source, tmp_path)


def test_an_unmeasurable_source_is_allowed_through(tmp_path: Path) -> None:
    """Refusing because a size could not be read would block a good file on a
    network share; the copy will fail honestly if it must."""
    assert enough_room(tmp_path / "absent.mp3", tmp_path)


def test_a_faithful_copy_verifies(tmp_path: Path) -> None:
    source = tmp_path / "a.mp3"
    copied = tmp_path / "b.mp3"
    source.write_bytes(b"identical bytes")
    copied.write_bytes(b"identical bytes")
    assert verify_copy(source, copied)


def test_a_truncated_copy_is_caught_and_the_original_is_promised_safe(tmp_path: Path) -> None:
    """The failure that matters: it plays for a while and then stops, which reads
    as a broken file rather than a broken import."""
    source = tmp_path / "a.mp3"
    copied = tmp_path / "b.mp3"
    source.write_bytes(b"x" * 4096)
    copied.write_bytes(b"x" * 100)

    check = verify_copy(source, copied)
    assert not check
    assert "incomplete" in check.message
    assert "your original file is untouched" in check.message


def test_a_missing_copy_is_caught(tmp_path: Path) -> None:
    source = tmp_path / "a.mp3"
    source.write_bytes(b"x")
    assert not verify_copy(source, tmp_path / "never-written.mp3")


def test_the_hash_is_checked_when_the_caller_has_one(tmp_path: Path) -> None:
    from quill.core.podcasts.local_duplicates import content_hash

    source = tmp_path / "a.mp3"
    copied = tmp_path / "b.mp3"
    source.write_bytes(b"one")
    copied.write_bytes(b"two")  # same length, different bytes

    assert verify_copy(source, copied)  # size alone cannot tell
    check = verify_copy(source, copied, expect_hash=content_hash(source))
    assert not check
    assert "does not match" in check.message


def test_discarding_a_staged_copy_leaves_no_orphan(tmp_path: Path) -> None:
    staged = tmp_path / "staged.mp3"
    staged.write_bytes(b"x")
    discard(staged)
    assert not staged.exists()


def test_discarding_something_that_is_not_there_is_silent(tmp_path: Path) -> None:
    """Called on every failure path, including ones where nothing was written."""
    discard(tmp_path / "never.mp3")


# -- the importer, staging and cleaning up ---------------------------------------


def test_a_failed_copy_leaves_no_orphan_and_no_episode(tmp_path: Path, monkeypatch) -> None:
    """The order the PRD insists on: no record until the bytes are verified."""
    from quill.core.podcasts import local_import

    source = tmp_path / "in" / "lecture.mp3"
    source.parent.mkdir()
    source.write_bytes(b"x" * 2048)
    managed = tmp_path / "managed"
    managed.mkdir()

    def _half_a_copy(src, dst, *args, **kwargs):
        Path(dst).write_bytes(b"x" * 10)  # truncated
        return dst

    monkeypatch.setattr(local_import.shutil, "copy2", _half_a_copy)

    assert local_import._staged_copy(source, managed) is None
    assert list(managed.iterdir()) == [], "a truncated copy was left behind"


def test_a_copy_that_raises_leaves_no_orphan(tmp_path: Path, monkeypatch) -> None:
    from quill.core.podcasts import local_import

    source = tmp_path / "in.mp3"
    source.write_bytes(b"x")
    managed = tmp_path / "managed"
    managed.mkdir()

    def _explode(src, dst, *args, **kwargs):
        Path(dst).write_bytes(b"partial")
        raise OSError("disk went away")

    monkeypatch.setattr(local_import.shutil, "copy2", _explode)

    assert local_import._staged_copy(source, managed) is None
    assert list(managed.iterdir()) == []


def test_a_good_copy_is_returned_and_kept(tmp_path: Path) -> None:
    from quill.core.podcasts import local_import

    source = tmp_path / "in.mp3"
    source.write_bytes(b"real audio bytes")
    managed = tmp_path / "managed"
    managed.mkdir()

    dest = local_import._staged_copy(source, managed)
    assert dest is not None
    assert dest.read_bytes() == b"real audio bytes"


def test_a_file_already_in_the_managed_folder_is_not_copied_over_itself(tmp_path: Path) -> None:
    """Scanning a watched folder that *is* the managed folder used to do this."""
    from quill.core.podcasts import local_import

    managed = tmp_path / "managed"
    managed.mkdir()
    existing = managed / "already.mp3"
    existing.write_bytes(b"kept")

    dest = local_import._staged_copy(existing, managed)
    assert dest == existing
    assert existing.read_bytes() == b"kept"
