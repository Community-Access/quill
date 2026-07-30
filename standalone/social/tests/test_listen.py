"""Listen-to-queue transport: auto-advance, boundaries, pause/next/prev/stop."""

from __future__ import annotations

from quill_social.model import SocialItem
from quill_social.services.listen import QueueItem, QueueReader, queue_from_items


class FakePlayer:
    """Records speak calls and lets the test drive completion deterministically."""

    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.paused = 0
        self.resumed = 0
        self.stopped = 0
        self._on_finished = None

    def speak(self, text, on_finished):
        self.spoken.append(text)
        self._on_finished = on_finished

    def finish(self):
        cb = self._on_finished
        self._on_finished = None
        if cb:
            cb()

    def pause(self):
        self.paused += 1

    def resume(self):
        self.resumed += 1

    def stop(self):
        self.stopped += 1


def _reader(**kw):
    player = FakePlayer()
    said: list[str] = []
    reader = QueueReader(player=player, announce=said.append, **kw)
    return reader, player, said


def test_queue_from_items_builds_titles_and_feeds():
    items = [
        SocialItem(item_id="a", account_id="acc1", text="Big News\n\nBody text here."),
    ]
    q = queue_from_items(items, feed_names={"acc1": "The Verge"})
    assert q[0].item_id == "a"
    assert q[0].title == "Big News"
    assert q[0].feed == "The Verge"


def test_play_speaks_boundary_then_body():
    reader, player, _ = _reader()
    reader.load([QueueItem("a", "Body one.", title="First", feed="Feed A")])
    reader.play()
    assert reader.state == QueueReader.PLAYING
    assert player.spoken[0].startswith("First, from Feed A.")
    assert "Body one." in player.spoken[0]


def test_auto_advance_through_queue_then_end():
    reader, player, said = _reader()
    reader.load(
        [QueueItem("a", "One.", title="A"), QueueItem("b", "Two.", title="B")]
    )
    reader.play()
    assert reader.index == 0
    player.finish()  # first article ends
    assert reader.index == 1
    assert reader.state == QueueReader.PLAYING
    player.finish()  # second ends -> end of queue
    assert reader.state == QueueReader.STOPPED
    assert "End of the listen queue." in said


def test_pause_resume_stop():
    reader, player, said = _reader()
    reader.load([QueueItem("a", "One.")])
    reader.play()
    reader.pause()
    assert reader.state == QueueReader.PAUSED
    assert player.paused == 1
    assert "Paused" in said
    reader.resume()
    assert reader.state == QueueReader.PLAYING
    assert player.resumed == 1
    reader.stop()
    assert reader.state == QueueReader.STOPPED
    assert player.stopped >= 1


def test_stop_prevents_auto_advance():
    reader, player, _ = _reader()
    reader.load([QueueItem("a", "One."), QueueItem("b", "Two.")])
    reader.play()
    reader.stop()
    player.finish()  # a late completion callback must not resurrect playback
    assert reader.state == QueueReader.STOPPED
    assert reader.index == 0


def test_next_and_prev_article():
    reader, player, said = _reader()
    reader.load(
        [QueueItem("a", "One.", title="A"), QueueItem("b", "Two.", title="B")]
    )
    reader.play()
    reader.next_article()
    assert reader.index == 1
    assert player.spoken[-1].startswith("B")
    reader.prev_article()
    assert reader.index == 0
    reader.next_article()
    reader.next_article()  # already at last -> announce end, stay put
    assert reader.index == 1
    assert "End of the listen queue." in said


def test_empty_queue_is_safe():
    reader, _player, said = _reader()
    reader.play()
    assert reader.state == QueueReader.STOPPED
    assert "The listen queue is empty." in said


def test_boundaries_can_be_disabled():
    reader, player, _ = _reader(speak_boundaries=False)
    reader.load([QueueItem("a", "Just the body.", title="T", feed="F")])
    reader.play()
    assert player.spoken[0] == "Just the body."
