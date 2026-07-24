"""Tests for show_actions.py's bulk episode actions: Download All Episodes
(purely additive, no confirmation) and Remove All Episodes (two-step
confirm: remove the entries, then optionally delete downloaded files too).
No real wx.App or network -- wx.MessageBox is monkeypatched, the download
queue is a fake."""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.ui.podcasts.show_actions import download_all_episodes, remove_all_episodes_prompt


def _episode(guid: str, *, downloaded: bool = False) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=f"Episode {guid}",
        audio_url=f"https://example.com/{guid}.mp3",
        published="2026-07-01T00:00:00",
        downloaded_path=f"C:/downloads/{guid}.mp3" if downloaded else "",
    )


def _show(episodes: list[PodcastEpisode]) -> PodcastShow:
    return PodcastShow(
        id="show-1", title="Test Show", feed_url="https://example.com/feed.xml", episodes=episodes
    )


class _FakeQueue:
    def __init__(self, in_flight: set[str] | None = None) -> None:
        self._in_flight = in_flight or set()
        self.enqueued: list[tuple[str, str, str, str, Path]] = []
        self.cancelled: list[str] = []

    def get(self, item_id: str) -> object | None:
        return object() if item_id in self._in_flight else None

    def enqueue(
        self,
        item_id: str,
        *,
        show_id: str,
        episode_guid: str,
        url: str,
        destination: Path,
        auth_header: str = "",
    ) -> None:
        self.enqueued.append((item_id, show_id, episode_guid, url, destination))

    def cancel_item(self, item_id: str) -> bool:
        self.cancelled.append(item_id)
        return True


def test_download_all_episodes_skips_downloaded_and_already_queued(tmp_path: Path) -> None:
    show = _show([
        _episode("fresh"),
        _episode("done", downloaded=True),
        _episode("queued"),
    ])
    queue = _FakeQueue(in_flight={"queued"})
    announced = []
    count = download_all_episodes(queue, tmp_path, show, announce=announced.append)
    assert count == 1
    assert [e[0] for e in queue.enqueued] == ["fresh"]
    assert "Queued 1 episode(s)" in announced[-1]


def test_download_all_episodes_announces_when_nothing_to_do(tmp_path: Path) -> None:
    show = _show([_episode("done", downloaded=True)])
    queue = _FakeQueue()
    announced = []
    count = download_all_episodes(queue, tmp_path, show, announce=announced.append)
    assert count == 0
    assert "Nothing to download" in announced[-1]


def test_remove_all_episodes_prompt_no_episodes_skips_the_dialog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail(*_a: object, **_k: object) -> int:
        raise AssertionError("MessageBox should not be shown for an empty episode list")

    monkeypatch.setattr(wx, "MessageBox", _fail)
    show = _show([])
    announced = []
    result = remove_all_episodes_prompt(None, _FakeQueue(), show, announce=announced.append)
    assert result is False
    assert "no episodes" in announced[-1]


def test_remove_all_episodes_prompt_declined_leaves_episodes_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.NO)
    show = _show([_episode("e1")])
    result = remove_all_episodes_prompt(None, _FakeQueue(), show, announce=lambda _m: None)
    assert result is False
    assert len(show.episodes) == 1


def test_remove_all_episodes_prompt_confirmed_without_deleting_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    downloaded_file = tmp_path / "e1.mp3"
    downloaded_file.write_bytes(b"audio")
    show = _show([_episode("e1", downloaded=True)])
    show.episodes[0].downloaded_path = str(downloaded_file)

    answers = iter([wx.YES, wx.NO])  # remove: yes; delete files: no
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: next(answers))

    queue = _FakeQueue()
    announced = []
    result = remove_all_episodes_prompt(None, queue, show, announce=announced.append)
    assert result is True
    assert show.episodes == []
    assert downloaded_file.exists()  # not deleted
    assert queue.cancelled == ["e1"]
    assert "deleted" not in announced[-1]


def test_remove_all_episodes_prompt_confirmed_and_deletes_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    downloaded_file = tmp_path / "e1.mp3"
    downloaded_file.write_bytes(b"audio")
    show = _show([_episode("e1", downloaded=True)])
    show.episodes[0].downloaded_path = str(downloaded_file)

    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)

    queue = _FakeQueue()
    announced = []
    result = remove_all_episodes_prompt(None, queue, show, announce=announced.append)
    assert result is True
    assert show.episodes == []
    assert not downloaded_file.exists()
    assert "deleted" in announced[-1]


def test_remove_all_episodes_prompt_no_downloaded_files_skips_second_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def _record(*_a: object, **k: object) -> int:
        calls.append(k)
        return wx.YES

    monkeypatch.setattr(wx, "MessageBox", _record)
    show = _show([_episode("e1")])  # never downloaded
    result = remove_all_episodes_prompt(None, _FakeQueue(), show, announce=lambda _m: None)
    assert result is True
    assert len(calls) == 1  # only the "remove?" prompt, no "delete files?" follow-up
