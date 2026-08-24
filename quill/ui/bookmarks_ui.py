"""The frame's side of bookmarks: two commands and the jump handlers (4.4).

Two verbs, and the split between them is the point:

* **Bookmark This Moment** is one keystroke, mid-listen, with no dialog. A
  bookmark you have to stop and fill in a form for is one you do not make.
  The note is optional (4.2) and the Bookmarks window is where it gets added,
  later, if there is anything to say.
* **Bookmarks...** is the list -- jump, share, note, delete, export.

Both live in one mixin because both apps need both, and because *what is
playing* is the one thing they answer differently: Quill Radio may be on a
station, a recording or a YouTube row; QUILL Cast is on a podcast episode.
Each app supplies that one answer through :meth:`_bookmark_target`, and
everything else here is shared.

**Jump handlers are registered by anchor kind**, so the list window can offer
Go There for a station in Radio and dim it in Cast, on the same row, in the
same shared file -- without either app knowing about the other.
"""

from __future__ import annotations

from typing import Any

from quill.core import bookmark_anchors, bookmark_ops
from quill.core.media.bookmarks import BookmarkStore


class BookmarksMixin:
    """Bookmark This Moment, the Bookmarks window, and the store behind them."""

    _shared_bookmarks: BookmarkStore | None = None

    def _bookmark_store(self) -> BookmarkStore:
        """One store per frame, in the shared data folder.

        Built on demand rather than at launch: an app whose listener never
        makes a bookmark should not pay for the object, and the file is not
        read until something asks.
        """
        if self._shared_bookmarks is None:
            self._shared_bookmarks = BookmarkStore()
        return self._shared_bookmarks

    # -- what the app is playing ---------------------------------------------

    def _bookmark_target(self) -> tuple[str, int, str]:
        """``(anchor, position_ms, title)`` for whatever is playing now.

        The one thing each app answers for itself. The default is "nothing",
        which is the right answer for a frame that plays nothing at all and
        makes the verb say so rather than crash.
        """
        return ("", 0, "")

    # -- the verbs ------------------------------------------------------------

    def bookmark_this_moment(self) -> bool:
        """Drop a bookmark where playback is. True when one was made."""
        anchor, position_ms, title = self._bookmark_target()
        mark, said = bookmark_ops.add(self._bookmark_store(), anchor, position_ms, title=title)
        self._announce(said)  # type: ignore[attr-defined]
        return mark is not None

    def open_bookmarks(self) -> None:
        """Open the shared Bookmarks window."""
        from quill.ui.bookmarks_dialog import show_bookmarks

        show_bookmarks(self, store=self._bookmark_store())

    # -- registration ---------------------------------------------------------

    def _register_bookmark_commands(self) -> None:
        commands: Any = self.commands  # type: ignore[attr-defined]
        commands.try_register(
            "app.bookmark_moment",
            "Bookmark This Moment",
            self.bookmark_this_moment,
            feature_id="core.app",
        )
        commands.try_register(
            "app.bookmarks",
            "Bookmarks...",
            self.open_bookmarks,
            feature_id="core.app",
        )

    def _register_bookmark_jumps(self, kinds: dict[str, Any]) -> None:
        """Teach the list window which kinds this app can actually open.

        A dict rather than a decorator so an app declares the whole set in one
        readable place, and so a kind it cannot play is visibly absent rather
        than quietly unregistered somewhere else.
        """
        from quill.ui.bookmarks_dialog import register_jump

        for kind, handler in kinds.items():
            if kind in bookmark_anchors.KINDS:
                register_jump(kind, handler)


__all__ = ["BookmarksMixin"]
