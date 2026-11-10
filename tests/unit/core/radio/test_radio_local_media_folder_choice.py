"""Add a Folder by path: cleaning what was typed, saying what is wrong, and the
saved Include Subfolders choice (Chris Nova, 2026-11-09)."""

from __future__ import annotations

from pathlib import Path

from quill.core.radio.local_media import LocalMediaLibrary, Playlist, parse, serialize
from quill.core.radio.local_media_files import (
    clean_folder_text,
    describe_found,
    folder_problem,
    new_files_in,
)


def _music(tmp_path: Path) -> Path:
    root = tmp_path / "other files" / "downloads"
    (root / "Disc 2").mkdir(parents=True)
    (root / "12_days_of_Assistive_Tech_20261109_1203.mp3").write_bytes(b"x")
    (root / "talk.mp4").write_bytes(b"x")
    (root / "notes.txt").write_text("not media", encoding="utf-8")
    (root / "Disc 2" / "track 1.mp3").write_bytes(b"x")
    return root


def test_spaces_inside_the_path_are_kept_and_explorer_quotes_are_taken_off(tmp_path) -> None:
    root = _music(tmp_path)
    assert clean_folder_text(f'  "{root}"\r\n') == str(root)
    assert clean_folder_text(f"'{root}'") == str(root)
    assert " " in clean_folder_text(str(root))
    assert clean_folder_text("   ") == ""


def test_variables_and_the_home_folder_are_understood(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QUILL_TEST_MUSIC", str(tmp_path))
    assert clean_folder_text("%QUILL_TEST_MUSIC%\\x") == str(tmp_path) + "\\x"
    assert not clean_folder_text("~").startswith("~")


def test_each_problem_is_one_plain_sentence(tmp_path) -> None:
    root = _music(tmp_path)
    assert folder_problem(str(root)) == ""
    assert folder_problem(f'"{root}"') == ""
    assert "Type or paste" in folder_problem("")
    missing = folder_problem(str(tmp_path / "no such folder"))
    assert missing.startswith("There is no folder at") and "Browse" in missing
    a_file = folder_problem(str(root / "talk.mp4"))
    assert "is a file, not a folder" in a_file


def test_what_a_folder_held_is_counted_by_kind() -> None:
    assert describe_found(["a.mp3", "b.flac", "c.mp4"]) == "2 audio files and 1 video"
    assert describe_found(["a.mp3"]) == "1 audio file"
    assert describe_found(["a.mkv", "b.MP4"]) == "2 videos"
    assert describe_found([]) == "no media files"


def test_include_subfolders_is_kept_with_the_playlist() -> None:
    library = LocalMediaLibrary()
    deep = library.add_playlist("Deep")
    shallow = library.add_playlist("Shallow")
    shallow.subfolders = False
    data = serialize(library)
    rows = {row["name"]: row for row in data["playlists"]}  # type: ignore[union-attr]
    assert "subfolders" not in rows["Deep"]  # the default is not written
    assert rows["Shallow"]["subfolders"] is False
    again = parse(data)
    assert again.find(deep.id).subfolders is True
    assert again.find(shallow.id).subfolders is False


def test_looking_at_the_folder_again_respects_the_choice(tmp_path) -> None:
    root = _music(tmp_path)
    playlist = Playlist(id="p", name="downloads", folder=str(root))
    names = {p.name for p in new_files_in(playlist)}
    assert names == {"12_days_of_Assistive_Tech_20261109_1203.mp3", "talk.mp4", "track 1.mp3"}
    playlist.subfolders = False
    names = {p.name for p in new_files_in(playlist)}
    assert names == {"12_days_of_Assistive_Tech_20261109_1203.mp3", "talk.mp4"}
    assert {p.name for p in new_files_in(playlist, recursive=True)} >= {"track 1.mp3"}
