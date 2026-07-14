"""Tests for local (imported-file) podcasts: file discovery and show
creation (real filesystem via tmp_path, no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.podcasts.local_import import (
    create_local_show,
    find_audio_files,
    local_podcasts_root,
    scan_watched_folder,
)
from quill.core.podcasts.models import PodcastShow


def test_local_podcasts_root_is_outside_home_quill_local(monkeypatch: pytest.MonkeyPatch) -> None:
    root = local_podcasts_root()
    assert ".quill-local" in root.parts
    assert "podcasts" == root.name


def test_find_audio_files_from_a_folder_is_sorted_and_filtered(tmp_path: Path) -> None:
    (tmp_path / "b.mp3").write_bytes(b"x")
    (tmp_path / "a.mp3").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")
    result = find_audio_files([tmp_path])
    assert [p.name for p in result] == ["a.mp3", "b.mp3"]


def test_find_audio_files_from_explicit_files_preserves_only_audio(tmp_path: Path) -> None:
    audio = tmp_path / "episode.wav"
    audio.write_bytes(b"x")
    other = tmp_path / "cover.jpg"
    other.write_bytes(b"x")
    result = find_audio_files([audio, other])
    assert result == [audio]


def test_find_audio_files_does_not_recurse_into_subfolders(tmp_path: Path) -> None:
    (tmp_path / "top.mp3").write_bytes(b"x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.mp3").write_bytes(b"x")
    result = find_audio_files([tmp_path])
    assert [p.name for p in result] == ["top.mp3"]


def test_create_local_show_copies_files_and_builds_one_episode_each(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest_root = tmp_path / "local-store"
    monkeypatch.setattr("quill.core.podcasts.local_import.local_podcasts_root", lambda: dest_root)
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    ep1 = source_dir / "01 - Intro.mp3"
    ep1.write_bytes(b"audio one")
    ep2 = source_dir / "02 - Deep Dive.mp3"
    ep2.write_bytes(b"audio two")

    show = create_local_show("My Recordings", [ep1, ep2])

    assert show.is_local is True
    assert show.feed_url == ""
    assert len(show.episodes) == 2
    assert show.episodes[0].title == "Intro"
    assert show.episodes[1].title == "Deep Dive"
    for episode in show.episodes:
        assert Path(episode.downloaded_path).is_file()
        assert Path(episode.downloaded_path).parent == dest_root / "my-recordings"


def test_create_local_show_title_falls_back_to_stem_when_purely_numeric(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "quill.core.podcasts.local_import.local_podcasts_root", lambda: tmp_path / "store"
    )
    numeric_file = tmp_path / "01.mp3"
    numeric_file.write_bytes(b"x")
    show = create_local_show("Show", [numeric_file])
    assert show.episodes[0].title == "01"


class TestScanWatchedFolder:
    def test_no_watched_folder_is_a_noop(self) -> None:
        show = PodcastShow(id="s1", title="Show", is_local=True)
        assert scan_watched_folder(show) == 0

    def test_missing_folder_is_a_noop(self, tmp_path: Path) -> None:
        show = PodcastShow(
            id="s1", title="Show", is_local=True, watched_folder=str(tmp_path / "gone")
        )
        assert scan_watched_folder(show) == 0

    def test_adds_only_genuinely_new_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "quill.core.podcasts.local_import.local_podcasts_root", lambda: tmp_path / "store"
        )
        watch_dir = tmp_path / "watched"
        watch_dir.mkdir()
        existing = watch_dir / "already-added.mp3"
        existing.write_bytes(b"x")
        new_file = watch_dir / "brand-new.mp3"
        new_file.write_bytes(b"x")

        show = create_local_show("Show", [existing])
        show.watched_folder = str(watch_dir)

        added_count = scan_watched_folder(show)
        assert added_count == 1
        assert len(show.episodes) == 2
        assert {Path(e.downloaded_path).name for e in show.episodes} == {
            "already-added.mp3",
            "brand-new.mp3",
        }

    def test_rescanning_with_nothing_new_adds_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "quill.core.podcasts.local_import.local_podcasts_root", lambda: tmp_path / "store"
        )
        watch_dir = tmp_path / "watched"
        watch_dir.mkdir()
        only_file = watch_dir / "episode.mp3"
        only_file.write_bytes(b"x")
        show = create_local_show("Show", [only_file])
        show.watched_folder = str(watch_dir)
        assert scan_watched_folder(show) == 0
        assert len(show.episodes) == 1
