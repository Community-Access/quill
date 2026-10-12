from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import wx

from quill.core.podcasts import feed_auth
from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui import undo_last_ui
from quill.ui.podcasts.show_actions import remove_all_episodes_prompt, unsubscribe_show_prompt


@pytest.fixture
def undo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    owner = SimpleNamespace()
    history = undo_last_ui.activate(tmp_path, owner=owner)
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    monkeypatch.setattr(feed_auth, "load_feed_password", lambda _show_id: "")
    monkeypatch.setattr(feed_auth, "delete_feed_password", lambda _show_id: None)
    try:
        yield history
    finally:
        undo_last_ui.deactivate(owner)


def test_unfollow_undo_rejects_a_normalized_equivalent_subscription(undo) -> None:
    original = PodcastShow("original", "Original", feed_url="https://example.test/feed/")
    library = PodcastLibrary(shows=[original])
    assert unsubscribe_show_prompt(None, library, original, announce=lambda _message: None)
    replacement = PodcastShow("replacement", "Replacement", feed_url="https://EXAMPLE.test/feed")
    library.shows.append(replacement)

    with pytest.raises(ValueError, match="already followed"):
        undo.take().undo()

    assert library.shows == [replacement]


def test_unfollow_undo_preserves_current_queue_additions(undo) -> None:
    original = PodcastShow("original", "Original", feed_url="https://example.test/feed")
    removed = QueueItem(original.id, "old")
    library = PodcastLibrary(shows=[original], queue=[removed])
    assert unsubscribe_show_prompt(None, library, original, announce=lambda _message: None)
    arrived = QueueItem("other", "new")
    library.queue.append(arrived)

    undo.take().undo()

    assert library.shows == [original]
    assert library.queue == [removed, arrived]


def test_remove_all_undo_preserves_new_arrivals_and_current_matching_objects(undo) -> None:
    removed = PodcastEpisode("old", "Old", audio_url="https://example.test/old.mp3")
    show = PodcastShow("show", "Show", episodes=[removed])
    queue = SimpleNamespace(cancel_show=lambda _show_id: 0)
    assert remove_all_episodes_prompt(None, queue, show, announce=lambda _message: None)
    matching = PodcastEpisode("old", "Updated", audio_url="https://example.test/old.mp3")
    matching.position_ms = 42000
    arrived = PodcastEpisode("new", "New", audio_url="https://example.test/new.mp3")
    show.episodes.extend([matching, arrived])

    undo.take().undo()

    assert show.episodes == [matching, arrived]
    assert show.episodes[0] is matching
    assert matching.position_ms == 42000
