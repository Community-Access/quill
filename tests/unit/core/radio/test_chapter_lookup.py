"""Radio finds chapters; it never works them out.

The point of these cases is the boundary. Radio is the lite app: it may read a
file's own chapter frames and it may read the list Cast left in the shared
cache, and if neither exists the honest answer is nothing at all.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.radio import chapter_lookup
from quill.core.radio.chapter_lookup import SOURCE_CACHE, SOURCE_FILE, chapters_for_media


class _Chapter:
    def __init__(self, start_ms: int, title: str) -> None:
        self.start_ms = start_ms
        self.title = title


def test_nothing_anywhere_is_answered_with_nothing(tmp_path: Path) -> None:
    audio = tmp_path / "capture.mp3"
    audio.write_bytes(b"not really audio")
    assert chapters_for_media(audio) == ([], "")
    assert chapters_for_media(None) == ([], "")


def test_the_files_own_marks_win(tmp_path: Path, monkeypatch: Any) -> None:
    audio = tmp_path / "capture.mp3"
    audio.write_bytes(b"x")
    monkeypatch.setattr(
        "quill.core.podcasts.chapter_sources.read_file_chapters",
        lambda _path: [_Chapter(0, "One"), _Chapter(60_000, "Two")],
    )
    found, where = chapters_for_media(audio)
    assert [c.title for c in found] == ["One", "Two"]
    assert where == SOURCE_FILE


def test_a_single_mark_is_not_a_chapter_list(tmp_path: Path, monkeypatch: Any) -> None:
    audio = tmp_path / "capture.mp3"
    audio.write_bytes(b"x")
    monkeypatch.setattr(
        "quill.core.podcasts.chapter_sources.read_file_chapters",
        lambda _path: [_Chapter(0, "Only")],
    )
    assert chapters_for_media(audio) == ([], "")


def test_casts_cache_is_read_when_the_file_has_no_marks(tmp_path: Path, monkeypatch: Any) -> None:
    """The listener who analysed an episode in Cast finds it done in Radio."""
    audio = tmp_path / "episode.mp3"
    audio.write_bytes(b"x")
    monkeypatch.setattr("quill.core.podcasts.chapter_sources.read_file_chapters", lambda _path: [])
    monkeypatch.setattr(
        "quill.core.podcasts.chapter_inference.load_cached_inference",
        lambda _show, _guid, audio_path=None: (
            [_Chapter(0, "Opening"), _Chapter(900_000, "The interview")],
            "transcript",
        ),
    )
    found, where = chapters_for_media(audio, show_id="show-1", episode_guid="guid-1")
    assert [c.title for c in found] == ["Opening", "The interview"]
    assert where == SOURCE_CACHE


def test_the_cache_is_not_consulted_without_an_identity(tmp_path: Path, monkeypatch: Any) -> None:
    """A recording has no publisher, so there is nothing to look up."""
    audio = tmp_path / "capture.mp3"
    audio.write_bytes(b"x")
    monkeypatch.setattr("quill.core.podcasts.chapter_sources.read_file_chapters", lambda _path: [])

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the cache must not be read for an unidentified file")

    monkeypatch.setattr("quill.core.podcasts.chapter_inference.load_cached_inference", _boom)
    assert chapters_for_media(audio) == ([], "")


def test_an_unreadable_tag_is_no_chapters_not_an_error(tmp_path: Path, monkeypatch: Any) -> None:
    audio = tmp_path / "capture.mp3"
    audio.write_bytes(b"x")

    def _raise(_path: Path) -> list[object]:
        raise OSError("truncated file")

    monkeypatch.setattr("quill.core.podcasts.chapter_sources.read_file_chapters", _raise)
    assert chapters_for_media(audio) == ([], "")


def test_identify_episode_translates_radios_two_urls(tmp_path: Path, monkeypatch: Any) -> None:
    """Radio knows a feed and an audio URL; Cast's cache wants an id and a GUID."""

    class _Episode:
        audio_url = "https://cdn.example.com/ep7.mp3"
        guid = "guid-7"

    class _Show:
        id = "show-42"
        episodes = [_Episode()]

    class _Library:
        @staticmethod
        def find_show_by_feed_url(url: str) -> object | None:
            return _Show() if url == "https://example.com/feed.xml" else None

    monkeypatch.setattr("quill.core.podcasts.subscriptions.load_library", lambda _dir: _Library())
    assert chapter_lookup.identify_episode(
        tmp_path, "https://example.com/feed.xml", "https://cdn.example.com/ep7.mp3"
    ) == ("show-42", "guid-7")
    # A feed nobody follows, and an episode the library has not seen.
    assert chapter_lookup.identify_episode(tmp_path, "https://other/feed", "x") == ("", "")
    assert chapter_lookup.identify_episode(
        tmp_path, "https://example.com/feed.xml", "https://cdn.example.com/ep9.mp3"
    ) == ("", "")


def test_identify_episode_survives_a_library_that_will_not_load(
    tmp_path: Path, monkeypatch: Any
) -> None:
    def _raise(_dir: Path) -> object:
        raise OSError("library is locked")

    monkeypatch.setattr("quill.core.podcasts.subscriptions.load_library", _raise)
    assert chapter_lookup.identify_episode(tmp_path, "https://f", "https://a") == ("", "")
