"""What an imported file says about itself (ear.md R11).

Add Local Podcast named every episode from its filename, so a folder of
``track07.mp3`` became a show of "Track07" episodes while the files carried a
real title, artist and duration all along.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.podcasts.local_tags import Tags, read_tags


def test_a_missing_file_answers_empty_rather_than_raising() -> None:
    """Never raises: the caller falls back to the filename, as it always did."""
    tags = read_tags(Path("nowhere") / "absent.mp3")
    assert tags == Tags()
    assert tags.is_empty


def test_a_file_that_is_not_audio_answers_empty(tmp_path: Path) -> None:
    junk = tmp_path / "notes.txt"
    junk.write_text("this is not audio", encoding="utf-8")
    assert read_tags(junk).is_empty


def test_corrupt_bytes_answer_empty(tmp_path: Path) -> None:
    """Common in exactly the old archives people import."""
    broken = tmp_path / "broken.mp3"
    broken.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\xff" * 64)
    assert read_tags(broken).is_empty


def test_a_list_valued_tag_reads_as_its_first_entry() -> None:
    """Tag values are lists more often than not."""
    from quill.core.podcasts.local_tags import _first

    assert _first(["Real Title", "other"]) == "Real Title"
    assert _first([]) == ""
    assert _first("plain") == "plain"
    assert _first(None) == ""


def test_an_empty_list_reads_as_absent_not_as_brackets() -> None:
    """A tag that is present and says nothing must read as absent."""
    from quill.core.podcasts.local_tags import _first

    assert _first([]) == ""


def test_real_tags_are_read_when_mutagen_can_write_them(tmp_path: Path) -> None:
    """The happy path, skipped where the optional extra is absent."""
    mutagen = pytest.importorskip("mutagen")
    from mutagen.id3 import ID3, TALB, TIT2, TPE1  # noqa: F401

    # A minimal silent MP3 frame is enough for mutagen to attach tags to.
    path = tmp_path / "track07.mp3"
    path.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 1024)
    try:
        audio = mutagen.File(str(path), easy=True)
        if audio is None:
            pytest.skip("mutagen did not recognise the synthetic frame")
        audio["title"] = "The Real Title"
        audio["artist"] = "Somebody"
        audio.save()
    except Exception:  # pragma: no cover - synthetic audio is best effort
        pytest.skip("could not write tags to a synthetic file")

    tags = read_tags(path)
    assert tags.title == "The Real Title"
    assert tags.artist == "Somebody"


def test_both_import_paths_go_through_one_helper() -> None:
    """create_local_show and scan_watched_folder must not drift apart.

    They built the episode independently, so a fix to one silently missed the
    other -- which is how the watched folder would have kept naming episodes from
    filenames after Add Local Podcast learned to read tags.
    """
    import inspect

    from quill.core.podcasts import local_import

    for function in (local_import.create_local_show, local_import.scan_watched_folder):
        source = inspect.getsource(function)
        assert "_episode_for(" in source
        assert "PodcastEpisode(" not in source
