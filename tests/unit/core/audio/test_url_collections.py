"""Playlists and channels for Convert from URL, without the network.

Convert from URL took one video per link. These pin the new half: reading
what a link is before downloading anything, the options that make a playlist
land numbered and tagged as one album, the channel limits, "only what is new",
the pause on long runs, a stop, and failures listed rather than fatal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.audio import url_collections as uc
from quill.core.audio.url_import import UrlImportError

PLAYLIST = "https://www.youtube.com/playlist?list=PL123"


def _fake(responses: dict[str, Any]):
    calls: list[tuple[str, dict[str, Any], bool]] = []

    def extract(url: str, options: dict[str, Any], download: bool) -> dict[str, Any]:
        calls.append((url, options, download))
        answer = responses.get(url)
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            raise RuntimeError("no such page")
        return answer(options) if callable(answer) else answer

    return extract, calls


def test_one_video_is_a_video() -> None:
    extract, calls = _fake({"https://youtu.be/abc": {"title": "A talk", "id": "abc"}})
    info = uc.read_link("https://youtu.be/abc", extract=extract)
    assert (info.kind, info.title) == ("video", "A talk")
    assert calls[0][2] is False  # reading never downloads


def test_a_playlist_says_how_many_videos() -> None:
    extract, _ = _fake({
        PLAYLIST: {
            "_type": "playlist",
            "title": "Lectures",
            "id": "PL123",
            "extractor_key": "YoutubeTab",
            "playlist_count": 42,
            "entries": [{}],
        }
    })
    info = uc.read_link(PLAYLIST, extract=extract)
    assert (info.kind, info.title, info.count) == ("playlist", "Lectures", 42)


def test_a_video_inside_a_playlist_names_the_video() -> None:
    url = "https://www.youtube.com/watch?v=abc&list=PL123"

    def answer(options: dict[str, Any]) -> dict[str, Any]:
        if options.get("noplaylist"):
            return {"title": "Lecture 3"}
        return {"_type": "playlist", "title": "Lectures", "id": "PL123", "playlist_count": 9}

    extract, _ = _fake({url: answer})
    info = uc.read_link(url, extract=extract)
    assert info.kind == "playlist" and info.video_title == "Lecture 3"


def test_a_channel_lists_only_the_sections_it_has() -> None:
    base = "https://www.youtube.com/channel/UCabc"
    extract, _ = _fake({
        "https://www.youtube.com/@someone": {
            "_type": "playlist",
            "title": "Someone - Videos",
            "id": "UCabc",
            "extractor_key": "YoutubeTab",
            "channel": "Someone",
            "channel_url": base,
        },
        base + "/videos": {"_type": "playlist", "entries": [{"id": "1"}]},
        base + "/shorts": RuntimeError("This channel does not have a shorts tab"),
        base + "/streams": {"_type": "playlist", "entries": []},
    })
    info = uc.read_link("https://www.youtube.com/@someone", extract=extract)
    assert info.kind == "channel" and info.title == "Someone"
    assert info.sections == (("Videos", base + "/videos"),)


def test_an_unreadable_link_says_why() -> None:
    extract, _ = _fake({"https://example.com/x": RuntimeError("ERROR: Unsupported URL")})
    with pytest.raises(UrlImportError, match="Could not read that link: Unsupported URL"):
        uc.read_link("https://example.com/x", extract=extract)


def test_safe_mode_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(UrlImportError, match="Safe Mode"):
        uc.read_link(PLAYLIST, extract=_fake({})[0])


# -- the download options ----------------------------------------------------


def test_a_playlist_is_numbered_in_order_and_tagged_as_one_album(tmp_path: Path) -> None:
    choice = uc.CollectionChoice(url=PLAYLIST, title="Lectures", newest=5, only_new=False)
    options = uc.collection_options(choice, tmp_path, ffmpeg="ffmpeg.exe")
    assert options["outtmpl"].endswith("%(playlist_index|0)03d - %(title)s.%(ext)s")
    assert options["playlistend"] == 5 and options["ignoreerrors"] is True
    parser = options["postprocessors"][0]
    assert parser["key"] == "MetadataParser"
    assert parser["actions"][0][1:] == ("%(quill_collection_name|Lectures)s", "%(album)s")
    assert options["postprocessors"][1]["key"] == "FFmpegMetadata"
    assert options["ffmpeg_location"] == "ffmpeg.exe"
    assert "sleep_interval" not in options  # five videos need no pause
    assert "download_archive" not in options


def test_a_channel_is_named_by_date_limited_and_paused(tmp_path: Path) -> None:
    choice = uc.CollectionChoice(
        url="https://www.youtube.com/@x/videos",
        title="X - Videos",
        is_channel=True,
        newest=100,
        within_days=31,
    )
    options = uc.collection_options(choice, tmp_path, archive_dir=tmp_path / "seen")
    assert "%(upload_date>%Y-%m-%d|)s" in options["outtmpl"]
    assert options["playlistend"] == 100
    assert callable(options["match_filter"])
    assert options["sleep_interval"] >= 2
    assert options["download_archive"] == str(uc.archive_path(tmp_path / "seen", choice.url))


def test_each_link_keeps_its_own_record_of_what_was_fetched(tmp_path: Path) -> None:
    one = uc.archive_path(tmp_path, "https://www.youtube.com/@a")
    assert one == uc.archive_path(tmp_path, " https://www.youtube.com/@a ")
    assert one != uc.archive_path(tmp_path, "https://www.youtube.com/@b")


@pytest.mark.parametrize(
    ("title", "folder"),
    [("A/B: C?", "A B C"), ("Untitled List", "YouTube list"), ("", "YouTube list")],
)
def test_folder_titles_are_safe(title: str, folder: str) -> None:
    assert uc.folder_title(title) == folder


# -- the download itself ------------------------------------------------------


def test_new_files_are_reported_and_failures_listed(tmp_path: Path) -> None:
    choice = uc.CollectionChoice(url=PLAYLIST, title="Lectures", only_new=False)
    seen: list[tuple[int, int, float, str]] = []

    def extract(url: str, options: dict[str, Any], download: bool) -> dict[str, Any]:
        assert download is True
        folder = Path(options["outtmpl"]).parent
        hook = options["progress_hooks"][0]
        for n in (1, 2):
            info = {"title": f"Talk {n}", "n_entries": 3}
            hook({
                "status": "downloading",
                "info_dict": info,
                "downloaded_bytes": 5,
                "total_bytes": 10,
            })
            (folder / f"00{n} - Talk {n}.webm").write_bytes(b"x")
            hook({"status": "finished", "info_dict": info})
        options["logger"].error("ERROR: [youtube] zzz: Video unavailable. This video is private")
        return {}

    old = tmp_path / "Lectures" / "000 - from before.webm"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"x")
    result = uc.download_collection(
        choice, tmp_path, extract=extract, progress=lambda *a: seen.append(a)
    )
    assert [p.name for p in result.files] == ["001 - Talk 1.webm", "002 - Talk 2.webm"]
    assert result.failed == ["[youtube] zzz: Video unavailable. This video is private"]
    assert (0, 3, 0.5, "Talk 1") in seen and (2, 3, 0.0, "Talk 2") in seen
    assert not result.stopped


def test_a_stop_ends_the_run_and_keeps_what_finished(tmp_path: Path) -> None:
    choice = uc.CollectionChoice(url=PLAYLIST, title="Lectures", only_new=False)
    stop = {"now": False}

    def extract(url: str, options: dict[str, Any], download: bool) -> dict[str, Any]:
        folder = Path(options["outtmpl"]).parent
        (folder / "001 - Talk 1.webm").write_bytes(b"x")
        stop["now"] = True
        options["progress_hooks"][0]({"status": "downloading", "info_dict": {}})
        raise AssertionError("the hook should have stopped the run")

    result = uc.download_collection(
        choice, tmp_path, extract=extract, cancelled=lambda: stop["now"]
    )
    assert result.stopped
    assert [p.name for p in result.files] == ["001 - Talk 1.webm"]


def test_a_whole_list_failure_is_said_in_words(tmp_path: Path) -> None:
    choice = uc.CollectionChoice(url=PLAYLIST, title="Lectures")

    def extract(url: str, options: dict[str, Any], download: bool) -> dict[str, Any]:
        raise RuntimeError("ERROR: [youtube:tab] PL123: The playlist does not exist.")

    with pytest.raises(UrlImportError, match="The playlist does not exist"):
        uc.download_collection(choice, tmp_path, extract=extract)


def test_a_handle_link_that_lists_tabs_is_still_a_channel() -> None:
    base = "https://www.youtube.com/channel/UCted"
    extract, _ = _fake({
        "https://www.youtube.com/@TED": {
            "_type": "playlist",
            "title": "TED",
            "id": "@TED",
            "extractor_key": "YoutubeTab",
            "channel": "TED",
            "channel_url": base,
            "playlist_count": 3,  # three tabs, not three videos
        },
        base + "/videos": {"entries": [{"id": "1"}]},
        base + "/shorts": {"entries": [{"id": "2"}]},
        base + "/streams": {"entries": [{"id": "3"}]},
    })
    info = uc.read_link("https://www.youtube.com/@TED", extract=extract)
    assert info.kind == "channel" and [label for label, _u in info.sections] == [
        "Videos",
        "Shorts",
        "Live streams",
    ]
