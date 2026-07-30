"""Listen to my Queue -- continuous article read-aloud (plan xxx.md 3.21).

The flagship accessibility+delight differentiator: turn a feed/folder of unread
items into a hands-free, auto-advancing "podcast of my reading", with a spoken
handoff between articles. No surveyed RSS reader ships in-app article TTS.

This module is the **pure, wx-free queue controller**. It owns the playlist and
the transport state machine and speaks through an injected :class:`Player` -- so
it is fully unit-testable with a fake player, and the real neural voice
(``quill.core.read_aloud.ReadAloudController`` on merge, or a SAPI player
standalone) plugs in behind the same tiny interface. Crucially the content voice
is a *separate audio path* from the screen-reader announcement channel, so it
never double-speaks NVDA/JAWS (the transport confirmations go through the
``announce`` callback; the article body goes through the ``Player``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


class Player(Protocol):
    """The content-voice surface the queue drives (kept minimal for testing)."""

    def speak(self, text: str, on_finished: Callable[[], None]) -> None:
        """Begin narrating ``text``; call ``on_finished`` when it completes."""

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def stop(self) -> None: ...


@dataclass
class QueueItem:
    """One article queued for listening."""

    item_id: str
    text: str
    title: str = ""
    feed: str = ""


def _first_line(text: str, limit: int = 80) -> str:
    line = (text or "").strip().splitlines()[0] if text.strip() else ""
    return line[:limit].strip()


def queue_from_items(items, feed_names: dict[str, str] | None = None) -> list[QueueItem]:
    """Build a listen queue from SocialItem-like rows (unread order preserved).

    ``feed_names`` optionally maps ``account_id`` to a spoken feed label so the
    handoff can say "from The Verge".
    """
    names = feed_names or {}
    out: list[QueueItem] = []
    for it in items:
        text = getattr(it, "text", "") or ""
        out.append(
            QueueItem(
                item_id=getattr(it, "item_id", ""),
                text=text,
                title=_first_line(text),
                feed=names.get(getattr(it, "account_id", ""), ""),
            )
        )
    return out


class QueueReader:
    """Article-level transport over a listen queue: play/pause/next/prev/stop.

    Auto-advances to the next article when one finishes, speaking a short handoff
    ("Next: <title>, from <feed>") through the content voice so it feels like a
    station. Transport-state confirmations ("Paused", "End of the listen queue")
    go through the ``announce`` callback -- the screen-reader channel -- so the
    two voices never collide.
    """

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"

    def __init__(
        self,
        *,
        player: Player,
        announce: Callable[[str], None] | None = None,
        speak_boundaries: bool = True,
    ) -> None:
        self._player = player
        self._announce = announce or (lambda _t: None)
        self._speak_boundaries = speak_boundaries
        self._items: list[QueueItem] = []
        self._index = -1
        self._state = self.STOPPED

    # -- inspection -----------------------------------------------------------

    @property
    def state(self) -> str:
        return self._state

    @property
    def index(self) -> int:
        return self._index

    @property
    def count(self) -> int:
        return len(self._items)

    @property
    def current(self) -> QueueItem | None:
        if 0 <= self._index < len(self._items):
            return self._items[self._index]
        return None

    # -- playlist -------------------------------------------------------------

    def load(self, items: list[QueueItem]) -> None:
        """Replace the queue and reset transport (does not auto-start)."""
        self._player.stop()
        self._items = list(items)
        self._index = -1
        self._state = self.STOPPED

    def _content_for(self, item: QueueItem) -> str:
        if not self._speak_boundaries:
            return item.text
        if item.feed:
            head = f"{item.title}, from {item.feed}."
        elif item.title:
            head = f"{item.title}."
        else:
            return item.text
        return f"{head}\n\n{item.text}" if item.text else head

    def _start_current(self) -> None:
        item = self.current
        if item is None:
            self._state = self.STOPPED
            self._announce("End of the listen queue.")
            return
        self._state = self.PLAYING
        self._player.speak(self._content_for(item), self._on_item_finished)

    def _on_item_finished(self) -> None:
        # Fired by the player when an item finishes on its own; advance. If the
        # user stopped, we're already STOPPED and must not resurrect playback.
        if self._state != self.PLAYING:
            return
        if self._index + 1 < len(self._items):
            self._index += 1
            self._start_current()
        else:
            self._state = self.STOPPED
            self._announce("End of the listen queue.")

    # -- transport ------------------------------------------------------------

    def play(self) -> None:
        if not self._items:
            self._announce("The listen queue is empty.")
            return
        if self._state == self.PAUSED:
            self.resume()
            return
        if self._state == self.PLAYING:
            return
        if self._index < 0:
            self._index = 0
        self._start_current()

    def pause(self) -> None:
        if self._state == self.PLAYING:
            self._player.pause()
            self._state = self.PAUSED
            self._announce("Paused")

    def resume(self) -> None:
        if self._state == self.PAUSED:
            self._player.resume()
            self._state = self.PLAYING
            self._announce("Playing")

    def toggle(self) -> None:
        if self._state == self.PLAYING:
            self.pause()
        else:
            self.play()

    def stop(self) -> None:
        self._player.stop()
        self._state = self.STOPPED
        self._announce("Stopped")

    def next_article(self) -> None:
        if not self._items:
            return
        if self._index + 1 >= len(self._items):
            self._announce("End of the listen queue.")
            return
        self._player.stop()
        self._index += 1
        self._start_current()

    def prev_article(self) -> None:
        if not self._items:
            return
        self._player.stop()
        self._index = max(0, self._index - 1)
        self._start_current()
