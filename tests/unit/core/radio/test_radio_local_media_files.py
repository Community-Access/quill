"""Local Media's files: finding media in folders, and M3U/PLS in and out."""

from __future__ import annotations

from pathlib import Path

from quill.core.radio.browse_local_media import (
    ITEM,
    PLAYLIST,
    PLAYLIST_OF,
    ROOT,
    browse_local_media,
    browse_local_playlist,
    menu_actions,
    station_for,
)
from quill.core.radio.local_media import LocalMediaLibrary
from quill.core.radio.local_media_files import (
    export_m3u,
    find_media_files,
    name_for_files,
    new_files_in,
    parse_playlist_text,
    read_playlist_file,
)


def _album(root: Path) -> Path:
    album = root / "Abbey Road"
    (album / "Disc 2").mkdir(parents=True)
    for name in ("10 End.mp3", "2 Something.mp3", "1 Come Together.mp3", "cover.jpg"):
        (album / name).write_bytes(b"x")
    (album / "Disc 2" / "1 Bonus.flac").write_bytes(b"x")
    return album


def test_a_folder_is_read_the_way_a_person_reads_it(tmp_path: Path) -> None:
    album = _album(tmp_path)
    found = [path.name for path in find_media_files([album])]
    assert found == ["1 Come Together.mp3", "2 Something.mp3", "10 End.mp3", "1 Bonus.flac"]
    assert [p.name for p in find_media_files([album], recursive=False)][-1] == "10 End.mp3"
    assert name_for_files([album / "1 Come Together.mp3", album / "10 End.mp3"]) == "Abbey Road"


def test_a_followed_folder_offers_only_what_is_new(tmp_path: Path) -> None:
    album = _album(tmp_path)
    playlist = LocalMediaLibrary().add_playlist("Abbey Road")
    playlist.folder = str(album)
    for path in find_media_files([album]):
        playlist.items.append(playlist.make_item(path))
    (album / "11 Her Majesty.mp3").write_bytes(b"x")
    assert [p.name for p in new_files_in(playlist)] == ["11 Her Majesty.mp3"]


def test_m3u_round_trips_relative_paths_and_skips_streams(tmp_path: Path) -> None:
    album = _album(tmp_path)
    playlist = LocalMediaLibrary().add_playlist("Abbey Road")
    for path in find_media_files([album]):
        playlist.items.append(playlist.make_item(path, title=path.stem, duration_seconds=125))
    playlist.items[0].artist = "The Beatles"
    text = export_m3u(playlist, playlist_dir=album)
    assert "#EXTINF:125,The Beatles - 1 Come Together" in text
    assert "1 Come Together.mp3" in text.splitlines()
    assert str(album) not in text, "tracks under the playlist's folder are written relatively"
    saved = album / "list.m3u8"
    saved.write_text(text + "http://example.invalid/stream\n", encoding="utf-8")
    entries, skipped = read_playlist_file(saved)
    assert [Path(e.path).name for e in entries] == [p.file_name for p in playlist.items]
    assert Path(entries[0].path).parent == album
    assert entries[0].duration_seconds == 125
    assert skipped == 1


def test_pls_and_file_urls_are_read(tmp_path: Path) -> None:
    pls = "[playlist]\nFile1=a.mp3\nTitle1=First\nLength1=61\nFile2=http://x/y\nNumberOfEntries=2\n"
    entries, skipped = parse_playlist_text(pls, base_dir=tmp_path, filename="x.pls")
    assert (Path(entries[0].path).name, entries[0].title, entries[0].duration_seconds) == (
        "a.mp3",
        "First",
        61,
    )
    assert skipped == 1
    m3u = "#EXTM3U\nfile:///C:/Music/Track%201.mp3\n"
    entries, _ = parse_playlist_text(m3u, base_dir=tmp_path)
    assert entries[0].path.replace("/", "\\").endswith("Music\\Track 1.mp3")


def test_the_branch_lists_playlists_then_ways_in(tmp_path: Path) -> None:
    empty = browse_local_media([], safe_mode=True, library=LocalMediaLibrary())
    assert [node.label for node in empty] == [
        "Add Media Files...",
        "Add a Folder...",
        "New Playlist...",
        "Import a Playlist...",
        "Open the Local Media Window",
    ]
    library = LocalMediaLibrary()
    playlist = library.add_playlist("Road Trip")
    song = tmp_path / "song.mp3"
    song.write_bytes(b"x")
    playlist.items.append(
        playlist.make_item(song, title="Song", artist="Band", duration_seconds=90)
    )
    nodes = browse_local_media([], safe_mode=False, library=library)
    assert nodes[0].label == "Road Trip" and nodes[0].is_folder
    assert "1 item" in nodes[0].note
    leaves = browse_local_playlist([playlist.id], safe_mode=False, library=library)
    assert leaves[0].station is not None and leaves[0].station.is_recording
    assert leaves[0].note == "Band, 1 minute 30 seconds"
    assert PLAYLIST_OF[str(song).casefold()] == playlist.id
    assert station_for(playlist.items[0]).station_uuid == "", "never a Radio Browser click"


def _keys(actions: list) -> list[str]:
    letters = []
    for action in actions:
        label = action.label
        letters.append(label[label.index("&") + 1].lower())
    return letters


def test_every_row_menu_has_unique_access_keys(tmp_path: Path) -> None:
    library = LocalMediaLibrary()
    playlist = library.add_playlist("Road Trip")
    playlist.folder = str(tmp_path)
    present = tmp_path / "here.mp3"
    present.write_bytes(b"x")
    playlist.items.append(playlist.make_item(present))
    playlist.items.append(playlist.make_item(tmp_path / "gone.mp3"))
    playlist.last_item_id = 1
    shapes = [
        menu_actions(ROOT),
        menu_actions(ROOT, expanded=True),
        menu_actions(PLAYLIST, playlist=playlist),
        menu_actions(ITEM, playlist=playlist, item=playlist.items[0], playing=True),
        menu_actions(ITEM, playlist=playlist, item=playlist.items[1]),
    ]
    for actions in shapes:
        letters = _keys(actions)
        assert len(letters) == len(set(letters)), [a.label for a in actions]
    labels = [a.label for a in shapes[4]]
    assert "&Locate..." in labels, "a missing file offers Locate"
