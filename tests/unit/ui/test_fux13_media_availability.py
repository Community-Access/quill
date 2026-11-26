"""FUX-13 in Cast, Radio and Media Player: rows say where their audio is."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core.media.librivox import LibriVoxBook, LibriVoxSection
from quill.core.media.playlist_availability import librivox_row, play_payload
from quill.core.podcasts import episode_availability as ea
from quill.core.radio.browse_helpers import row_label
from quill.core.radio.browse_nodes import BrowseNode
from quill.core.radio.models import RadioStation

# -- Cast ---------------------------------------------------------------------


def test_downloaded_file_on_disk_reads_downloaded(tmp_path: Path) -> None:
    audio = tmp_path / "episode.mp3"
    audio.write_bytes(b"x")
    assert ea.status_words(downloaded_path=str(audio), played=True) == "Downloaded, played"
    assert ea.downloaded_words(str(audio)) == "Downloaded"


def test_downloaded_file_deleted_says_missing_and_streams(tmp_path: Path) -> None:
    gone = str(tmp_path / "deleted.mp3")
    words = ea.status_words(downloaded_path=gone, played=False)
    assert words == "File missing, will stream. Download to get it back"
    assert ea.downloaded_words(gone) == "File missing, streams"


def test_failed_download_says_failed_and_why() -> None:
    words = ea.status_words(
        downloaded_path="",
        played=False,
        item_status="failed",
        item_error="The disk is full (2 GB free). Free some space, then Download again.",
    )
    assert words == "Download failed, will stream: The disk is full (2 GB free)."


def test_in_flight_and_never_downloaded_keep_their_words() -> None:
    assert ea.status_words(downloaded_path="", played=False, item_status="paused") == "Paused"
    assert ea.status_words(downloaded_path="", played=False) == "Streaming"
    assert ea.status_words(downloaded_path="", played=False, item_status="cancelled") == (
        "Streaming"
    )


def test_manager_row_uses_the_availability_words(tmp_path: Path) -> None:
    from quill.ui.podcasts.manager_row_view import ManagerRowViewMixin

    failed = SimpleNamespace(
        status="failed", error_message="The download connection dropped: no route"
    )
    host = SimpleNamespace(
        _download_queue={"id": failed},
        _download_item_id=lambda _episode: "id",
    )
    episode = SimpleNamespace(downloaded_path="", played=False)
    words = ManagerRowViewMixin._episode_status_text(host, episode)  # type: ignore[arg-type]
    assert words.startswith("Download failed, will stream")

    episode = SimpleNamespace(downloaded_path=str(tmp_path / "gone.mp3"), played=False)
    words = ManagerRowViewMixin._episode_status_text(host, episode)  # type: ignore[arg-type]
    assert words.startswith("File missing, will stream")


# -- Radio ----------------------------------------------------------------------


def test_browse_row_says_a_failed_check() -> None:
    station = RadioStation(name="Example FM", stream_url="https://example.invalid/s")
    station.last_check_ok = False
    node = BrowseNode(node_id="s1", label="Example FM", station=station)
    assert row_label(node) == "Example FM  (may not be playable)"


def test_browse_row_stays_quiet_when_healthy_or_needing_lookup() -> None:
    healthy = RadioStation(name="Good FM", stream_url="https://example.invalid/g")
    healthy.last_check_ok = True
    assert row_label(BrowseNode(node_id="g", label="Good FM", station=healthy)) == "Good FM"
    lookup = RadioStation(name="Tune", stream_url="https://example.invalid/t", source="TuneIn")
    assert row_label(BrowseNode(node_id="t", label="Tune", station=lookup)) == "Tune"


# -- Media Player ---------------------------------------------------------------


class _Player:
    def __init__(self, answer: object = True) -> None:
        self.loaded: list[str] = []
        self._answer = answer

    def load(self, path: str, _chapters: list[object], **_kwargs: object) -> object:
        self.loaded.append(path)
        return self._answer


def test_missing_track_is_not_called_playing(tmp_path: Path) -> None:
    player = _Player()
    gone = tmp_path / "track02.mp3"
    ok, status = play_payload(player, ("track", (gone, 0)), "Chapter 2", autoplay=True)
    assert not ok
    assert status.startswith("Chapter 2: audio file missing.")
    assert player.loaded == []


def test_present_track_plays_and_refused_load_says_so(tmp_path: Path) -> None:
    track = tmp_path / "track01.mp3"
    track.write_bytes(b"x")
    played = play_payload(_Player(), ("track", (track, 500)), "One", autoplay=True)
    assert played == (True, "Playing One")
    refused = play_payload(_Player(False), ("load", str(track)), "One", autoplay=False)
    assert refused == (False, "Could not play One.")


def test_stream_address_is_not_checked_on_disk() -> None:
    player = _Player()
    url = "https://example.invalid/section1.mp3"
    assert play_payload(player, ("load", url), "Section 1", autoplay=True)[1] == (
        "Playing Section 1"
    )
    assert player.loaded == [url]


def test_librivox_row_without_audio_says_so() -> None:
    silent = LibriVoxBook(book_id="1", title="A Book", authors="An Author")
    assert librivox_row(silent) == "A Book - An Author, no audio to play"
    voiced = LibriVoxBook(
        book_id="2",
        title="B Book",
        sections=(LibriVoxSection(index=1, title="1", url="https://example.invalid/1.mp3"),),
    )
    assert librivox_row(voiced) == "B Book"


def test_long_reason_without_a_full_stop_is_cut_on_a_word() -> None:
    reason = ea.first_sentence("The download connection dropped: " + "word " * 30)
    assert len(reason) <= ea.REASON_LIMIT + 3
    assert reason.endswith("...")


def test_auto_advance_onto_a_missing_file_does_not_say_next(tmp_path: Path) -> None:
    from quill.apps.player import QuillMediaPlayerFrame as MediaPlayerFrame

    said: list[str] = []
    status: list[str] = []
    host = SimpleNamespace(
        _playlist=[
            ("One", ("track", (tmp_path / "1.mp3", 0))),
            ("Two", ("track", (tmp_path / "2.mp3", 0))),
        ],
        _playlist_index=0,
        _player=_Player(),
        _announce=said.append,
        _set_status=status.append,
        _save_resume=lambda: None,
    )
    host._play_payload = lambda payload, title, autoplay: MediaPlayerFrame._play_payload(
        host, payload, title, autoplay=autoplay
    )
    MediaPlayerFrame._on_finished(host)  # type: ignore[arg-type]
    assert said == [
        "Two: audio file missing. If you moved the book, open it again from its new folder."
    ]
    assert status == said


def test_cast_state_cells_follow_the_column_ids(tmp_path: Path) -> None:
    from quill.ui.podcasts.manager_row_view import ManagerRowViewMixin

    written: dict[int, str] = {}
    host = SimpleNamespace(
        _episode_columns=[
            SimpleNamespace(id="title"),
            SimpleNamespace(id="remaining"),
            SimpleNamespace(id="status"),
        ],
        _episodes=SimpleNamespace(
            SetItem=lambda _row, column, text: written.__setitem__(column, text)
        ),
        _download_queue={},
        _download_item_id=lambda _episode: "id",
    )
    host._episode_status_text = lambda episode: ManagerRowViewMixin._episode_status_text(
        host, episode
    )
    episode = SimpleNamespace(downloaded_path=str(tmp_path / "gone.mp3"), played=False)
    ManagerRowViewMixin._set_episode_state_cells(host, 0, episode)  # type: ignore[arg-type]
    assert written == {2: "File missing, will stream. Download to get it back"}
