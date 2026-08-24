"""Sharing and audio export for QUILL Cast (x.md item 9).

Earshot's share sheet has no desktop equivalent, so the parity gap closes as
three ordinary commands: save the audio somewhere of your choosing, copy the
podcast's feed link, and show a downloaded file in the file manager.

The property worth defending across all three is that **QUILL Cast keeps
managing its own copy**. Save Episode Audio As copies; it must never move the
managed file, or resume, retention and the storage cap all quietly lose track
of it.

Save Episode Audio As has since learned to **wait** for a download rather than
telling the listener to run the command again, and moved to
``ui/podcasts/export_audio.py`` (list.md 2.2). The wait itself is pinned in
test_podcast_export_wait.py; what is here is the save, which did not change.

No real wx.App: the clipboard, the message box and the file dialog are all
monkeypatched, and the download queue is a fake.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.core.podcasts.audio_export import suggested_filename
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.ui.podcasts.export_audio import export_episode_audio
from quill.ui.podcasts.share_actions import copy_show_link, reveal_episode_in_file_manager


def _episode(guid: str = "ep1", *, downloaded: str = "") -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title="Episode One",
        audio_url=f"https://example.com/{guid}.mp3",
        published="2026-07-01T00:00:00",
        downloaded_path=downloaded,
    )


def _show(*, feed_url: str = "https://example.com/feed.xml") -> PodcastShow:
    return PodcastShow(id="show-1", title="Test Show", feed_url=feed_url, episodes=[])


class _FakeQueue:
    def __init__(self) -> None:
        self.enqueued: list[str] = []

    def get(self, _item_id: str) -> object | None:
        return None

    def enqueue(self, item_id: str, **_kwargs: object) -> None:
        self.enqueued.append(item_id)


class _FakeClipboard:
    def __init__(self) -> None:
        self.text = ""
        self.opened = 0

    def Open(self) -> bool:  # noqa: N802 - wx naming
        self.opened += 1
        return True

    def SetData(self, data: object) -> None:  # noqa: N802 - wx naming
        self.text = data.GetText()

    def Close(self) -> None:  # noqa: N802 - wx naming
        return None


@pytest.fixture
def clipboard(monkeypatch: pytest.MonkeyPatch) -> _FakeClipboard:
    fake = _FakeClipboard()
    monkeypatch.setattr(wx, "TheClipboard", fake)
    return fake


# -- Copy Podcast Link -------------------------------------------------------


def test_copy_podcast_link_copies_the_feed_address(clipboard: _FakeClipboard) -> None:
    """The feed URL, not the homepage: a feed address is the thing another
    podcast app can actually be given."""
    announced: list[str] = []

    assert copy_show_link(_show(), announce=announced.append) is True
    assert clipboard.text == "https://example.com/feed.xml"
    assert "Test Show" in announced[0]


def test_a_local_podcast_says_it_has_no_link(clipboard: _FakeClipboard) -> None:
    announced: list[str] = []

    assert copy_show_link(_show(feed_url=""), announce=announced.append) is False
    assert clipboard.text == "", "nothing is copied, so the clipboard keeps what it had"
    assert "local podcast" in announced[0]


# -- Show in File Explorer ---------------------------------------------------


def test_show_in_explorer_launches_the_shared_reveal_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audio = tmp_path / "ep1.mp3"
    audio.write_bytes(b"audio")
    launched: list[list[str]] = []
    monkeypatch.setattr("subprocess.Popen", lambda argv, **_k: launched.append(argv))
    announced: list[str] = []

    assert (
        reveal_episode_in_file_manager(_episode(downloaded=str(audio)), announce=announced.append)
        is True
    )
    assert len(launched) == 1
    assert str(audio) in " ".join(launched[0])


def test_a_streamed_episode_has_no_file_to_show(monkeypatch: pytest.MonkeyPatch) -> None:
    launched: list[list[str]] = []
    monkeypatch.setattr("subprocess.Popen", lambda argv, **_k: launched.append(argv))
    announced: list[str] = []

    assert reveal_episode_in_file_manager(_episode(), announce=announced.append) is False
    assert launched == [], "nothing is launched, rather than an unrelated folder opening"
    assert "not downloaded" in announced[0]


def test_a_download_deleted_behind_our_back_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched: list[list[str]] = []
    monkeypatch.setattr("subprocess.Popen", lambda argv, **_k: launched.append(argv))
    announced: list[str] = []
    missing = tmp_path / "gone.mp3"

    assert (
        reveal_episode_in_file_manager(_episode(downloaded=str(missing)), announce=announced.append)
        is False
    )
    assert launched == []
    assert "no longer there" in announced[0]


# -- Save Episode Audio As ---------------------------------------------------


class _FakeFileDialog:
    """Stands in for wx.FileDialog as a context manager."""

    instances: list[_FakeFileDialog] = []

    def __init__(self, _parent: object, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.chosen = ""
        self.result = wx.ID_OK
        _FakeFileDialog.instances.append(self)

    def __enter__(self) -> _FakeFileDialog:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def ShowModal(self) -> int:  # noqa: N802 - wx naming
        return self.result

    def GetPath(self) -> str:  # noqa: N802 - wx naming
        return self.chosen


@pytest.fixture
def file_dialog(monkeypatch: pytest.MonkeyPatch) -> type[_FakeFileDialog]:
    _FakeFileDialog.instances = []
    monkeypatch.setattr(wx, "FileDialog", _FakeFileDialog)
    return _FakeFileDialog


def test_saving_copies_and_leaves_the_managed_file_alone(
    tmp_path: Path, file_dialog: type[_FakeFileDialog], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The invariant: QUILL Cast still manages its own downloaded copy, so
    retention, the storage cap and resume all keep working on it."""
    managed = tmp_path / "managed" / "ep1.mp3"
    managed.parent.mkdir()
    managed.write_bytes(b"the audio")
    destination = tmp_path / "elsewhere" / "My Episode.mp3"
    destination.parent.mkdir()

    def make_dialog(parent: object, **kwargs: object) -> _FakeFileDialog:
        dialog = _FakeFileDialog(parent, **kwargs)
        dialog.chosen = str(destination)
        return dialog

    monkeypatch.setattr(wx, "FileDialog", make_dialog)
    announced: list[str] = []
    episode = _episode(downloaded=str(managed))

    saved = export_episode_audio(
        None, _FakeQueue(), tmp_path, _show(), episode, announce=announced.append
    )

    assert saved is True
    assert destination.read_bytes() == b"the audio"
    assert managed.exists(), "the managed copy must survive -- this is a copy, not a move"
    assert episode.downloaded_path == str(managed), "and the episode still points at it"
    assert "Saved" in announced[0]


def test_cancelling_the_save_dialog_does_nothing(
    tmp_path: Path, file_dialog: type[_FakeFileDialog], monkeypatch: pytest.MonkeyPatch
) -> None:
    managed = tmp_path / "ep1.mp3"
    managed.write_bytes(b"audio")

    def make_dialog(parent: object, **kwargs: object) -> _FakeFileDialog:
        dialog = _FakeFileDialog(parent, **kwargs)
        dialog.result = wx.ID_CANCEL
        return dialog

    monkeypatch.setattr(wx, "FileDialog", make_dialog)
    announced: list[str] = []

    assert (
        export_episode_audio(
            None,
            _FakeQueue(),
            tmp_path,
            _show(),
            _episode(downloaded=str(managed)),
            announce=announced.append,
        )
        is False
    )
    assert announced == []


def test_an_unwritable_destination_is_announced_not_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    managed = tmp_path / "ep1.mp3"
    managed.write_bytes(b"audio")

    def make_dialog(parent: object, **kwargs: object) -> _FakeFileDialog:
        dialog = _FakeFileDialog(parent, **kwargs)
        dialog.chosen = str(tmp_path / "no-such-folder" / "out.mp3")
        return dialog

    monkeypatch.setattr(wx, "FileDialog", make_dialog)
    announced: list[str] = []

    assert (
        export_episode_audio(
            None,
            _FakeQueue(),
            tmp_path,
            _show(),
            _episode(downloaded=str(managed)),
            announce=announced.append,
        )
        is False
    )
    assert "Could not save the audio" in announced[0]


# -- the suggested filename --------------------------------------------------


def test_the_suggested_name_reads_as_show_then_episode(tmp_path: Path) -> None:
    name = suggested_filename(_show(), _episode(), ".mp3")
    assert name == "Test Show - Episode One.mp3"


def test_characters_windows_rejects_are_replaced(tmp_path: Path) -> None:
    """Replaced rather than stripped, so two episodes whose titles differ
    only by punctuation do not collapse onto one suggested name."""
    show = PodcastShow(id="s", title='News: The "Daily"', feed_url="https://e/f", episodes=[])
    episode = _episode()
    episode.title = "Part 1/2 <live>"

    name = suggested_filename(show, episode, ".mp3")

    assert not any(character in name[:-4] for character in '<>:"/\\|?*')
    assert name.endswith(".mp3")
    assert "News" in name and "Part 1" in name


def test_a_very_long_title_is_bounded(tmp_path: Path) -> None:
    """A Save dialog that opens pre-filled with a name the system rejects is
    worse than one that opens with a shorter name."""
    show = PodcastShow(id="s", title="S" * 200, feed_url="https://e/f", episodes=[])
    episode = _episode()
    episode.title = "E" * 200

    name = suggested_filename(show, episode, ".m4a")

    assert len(name) <= 124
    assert name.endswith(".m4a")


def test_an_empty_title_still_yields_a_usable_name() -> None:
    show = PodcastShow(id="s", title="", feed_url="https://e/f", episodes=[])
    episode = _episode()
    episode.title = ""

    assert suggested_filename(show, episode, ".mp3") == "episode.mp3"
