"""Numbered bookmarks in QUILL: nine slots you address by digit.

The engine is :mod:`quill.core.numbered_bookmarks`, whose own docstring says it
lives in shared core *"where QUILL's editor can adopt it, and QuillLite is
simply its first caller"*. Until 2026-09-16 QuillLite was its **only** caller:
nothing under ``quill/ui`` imported it, QUILL's own ``set_quick_bookmark`` /
``go_to_quick_bookmark`` had no command, no key and no caller, and
``navigate.set_bookmark`` was registered with ``binding=None`` and absent from
the keyboard reference. So the small product had nine persistent bookmarks and
the big one did not -- which is the shape ``CLAUDE.md`` forbids, and the reason
it forbids it: nobody opens QUILL and notices the absence of a thing they have
only ever seen in QuillLite, so it is never reported. This module is the door.

**Numbered is not named.** QUILL keeps its named bookmark vault
(:class:`quill.core.bookmarks.BookmarkVault`, ``navigate.set_bookmark``) and its
mark ring; those are the writing environment's answer to "come back to the
place I called Chapter Three". A numbered bookmark is the notepad's answer to
"come back to where I just was", and a digit is a name you do not have to think
of at the moment you are trying not to lose your place.

Three things this deliberately shares with QuillLite rather than reinventing:

**The same store.** Positions persist through
:class:`~quill.core.bookmarks.DocumentMemory`, keyed by path, in the same
``numbered_for`` / ``set_numbered`` records QuillLite writes -- so a file's
bookmarks are the same file's bookmarks in either editor. That seam already
existed; only QUILL's half of it was missing.

**Written on every change**, not on close. QuillLite writes on close and after
save, and loses a clear-all to a crash (bad.md L10); QUILL already writes named
bookmarks on every Set and this follows that, which is the better half of the
pair.

**Every jump feeds Back.** ``Alt+Left`` undoes a bookmark jump, because the
jump goes through ``_record_location_before_jump`` and the location ring like
every other jump in QUILL (bad.md L8). QuillLite routes bookmarks through its
own ``_go_to`` seam for the same reason.
"""

from __future__ import annotations

from typing import Any

from quill.core.bookmarks import DocumentMemory
from quill.core.numbered_bookmarks import MAX_BOOKMARKS, Bookmark, BookmarkSet, label_for

__all__ = ["NumberedBookmarksMixin"]


class NumberedBookmarksMixin:
    """Nine numbered bookmark slots for the active document.

    Expects from :class:`~quill.ui.main_frame.MainFrame`: ``editor``,
    ``document``, ``_active_tab``, ``_doc_memory``, ``_move_point``,
    ``_record_location_before_jump``, ``_announce_result`` and ``_set_status``.
    """

    # ------------------------------------------------------------------ #
    # Registration, menu and bindings -- all three here on purpose
    # ------------------------------------------------------------------ #

    def register_numbered_bookmark_commands(self) -> None:
        """Put the fourteen commands in the registry, from one call site.

        Kept here rather than in ``main_frame_commands.py`` because a verb
        registered in one module, built into a menu in a second and bound in a
        third is exactly how the labels and the handlers drift apart (bad.md
        7.1). One module owns all three for this feature.
        """
        self.commands.register(
            "navigate.set_numbered_bookmark",
            "Set Bookmark",
            self.set_numbered_bookmark,
            self._binding_for("navigate.set_numbered_bookmark"),
        )
        for slot in range(1, MAX_BOOKMARKS + 1):
            self.commands.register(
                f"navigate.set_numbered_bookmark_{slot}",
                f"Set Bookmark {slot}",
                getattr(self, f"set_numbered_bookmark_{slot}"),
                self._binding_for(f"navigate.set_numbered_bookmark_{slot}"),
            )
        for command_id, title, handler in (
            ("navigate.next_bookmark", "Next Bookmark", self.next_bookmark),
            ("navigate.previous_bookmark", "Previous Bookmark", self.previous_bookmark),
            (
                "navigate.clear_numbered_bookmarks",
                "Clear All Bookmarks",
                self.clear_numbered_bookmarks,
            ),
        ):
            self.commands.register(command_id, title, handler, self._binding_for(command_id))

    def build_numbered_bookmarks_menu(self, menu: Any) -> None:
        """Append the numbered-bookmark rows to *menu* and bind every one.

        Labels come from ``_menu_label`` so each row shows whatever is actually
        bound and follows a rebinding, which is the house rule.
        """
        wx = self._wx
        rows: list[tuple[object, str, str, object]] = [
            (
                wx.NewIdRef(),
                "&Set Bookmark",
                "navigate.set_numbered_bookmark",
                self.set_numbered_bookmark,
            ),
            (wx.NewIdRef(), "&Next Bookmark", "navigate.next_bookmark", self.next_bookmark),
            (
                wx.NewIdRef(),
                "&Previous Bookmark",
                "navigate.previous_bookmark",
                self.previous_bookmark,
            ),
            (
                wx.NewIdRef(),
                "&Clear All Bookmarks",
                "navigate.clear_numbered_bookmarks",
                self.clear_numbered_bookmarks,
            ),
        ]
        for item_id, label, command_id, handler in rows:
            menu.Append(item_id, self._menu_label(label, command_id))
            self.frame.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        menu.AppendSeparator()
        for slot in range(1, MAX_BOOKMARKS + 1):
            item_id = wx.NewIdRef()
            menu.Append(
                item_id,
                self._menu_label(f"Set Bookmark &{slot}", f"navigate.set_numbered_bookmark_{slot}"),
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e, n=slot: self._set_numbered_bookmark(n), id=item_id
            )

    # ------------------------------------------------------------------ #
    # The active document's set
    # ------------------------------------------------------------------ #

    @property
    def numbered_bookmarks(self) -> BookmarkSet:
        """The active tab's bookmark set, created on first use.

        Held on the tab rather than the frame because QUILL has tabs and a
        bookmark belongs to a document, not to a window. A frame-level cache
        would follow the user from tab to tab, which is the one thing a
        bookmark must never do.
        """
        tab = self._active_tab()
        if tab is None:
            # A stub frame with no tabs (tests, early startup). A set that is
            # never persisted is still better than raising at a keystroke.
            existing = getattr(self, "_orphan_numbered_bookmarks", None)
            if existing is None:
                existing = BookmarkSet()
                self._orphan_numbered_bookmarks = existing
            return existing
        marks = getattr(tab, "numbered_bookmarks", None)
        if not isinstance(marks, BookmarkSet):
            marks = BookmarkSet.from_records(self._stored_numbered_records())
            tab.numbered_bookmarks = marks
        return marks

    def _stored_numbered_records(self) -> list:
        key = DocumentMemory.key_for(getattr(getattr(self, "document", None), "path", None))
        if not key:
            return []
        try:
            return list(self._doc_memory.numbered_for(key))
        except Exception:  # noqa: BLE001 - persistence is best-effort
            return []

    def _save_numbered_bookmarks(self) -> None:
        """Persist the active document's numbered bookmarks. Untitled: in memory only."""
        key = DocumentMemory.key_for(getattr(getattr(self, "document", None), "path", None))
        if not key:
            return
        try:
            self._doc_memory.set_numbered(key, self.numbered_bookmarks.to_records())
        except Exception:  # noqa: BLE001 - persistence is best-effort
            pass

    # ------------------------------------------------------------------ #
    # Setting
    # ------------------------------------------------------------------ #

    def _set_numbered_bookmark(self, number: int) -> None:
        position = self.editor.GetInsertionPoint()
        label = label_for(self.editor.GetValue(), position)
        mark = self.numbered_bookmarks.set(number, position, label)
        self._save_numbered_bookmarks()
        self._announce_result(f"Bookmark {mark.number} set: {mark.label}")

    def set_numbered_bookmark(self) -> None:
        """Drop a bookmark in the next free slot, or reuse slot 1 when full."""
        self._set_numbered_bookmark(self.numbered_bookmarks.next_free_number())

    def set_numbered_bookmark_1(self) -> None:
        self._set_numbered_bookmark(1)

    def set_numbered_bookmark_2(self) -> None:
        self._set_numbered_bookmark(2)

    def set_numbered_bookmark_3(self) -> None:
        self._set_numbered_bookmark(3)

    def set_numbered_bookmark_4(self) -> None:
        self._set_numbered_bookmark(4)

    def set_numbered_bookmark_5(self) -> None:
        self._set_numbered_bookmark(5)

    def set_numbered_bookmark_6(self) -> None:
        self._set_numbered_bookmark(6)

    def set_numbered_bookmark_7(self) -> None:
        self._set_numbered_bookmark(7)

    def set_numbered_bookmark_8(self) -> None:
        self._set_numbered_bookmark(8)

    def set_numbered_bookmark_9(self) -> None:
        self._set_numbered_bookmark(9)

    # ------------------------------------------------------------------ #
    # Walking
    # ------------------------------------------------------------------ #

    def _go_to_numbered_bookmark(self, mark: Bookmark) -> None:
        self._record_location_before_jump()
        self._move_point(mark.position)
        self.editor.SetFocus()
        self._announce_result(f"Bookmark {mark.number}: {mark.label}")

    def next_bookmark(self) -> None:
        mark = self.numbered_bookmarks.next_after(self.editor.GetInsertionPoint())
        if mark is None:
            self._announce_result("No bookmarks in this document")
            return
        self._go_to_numbered_bookmark(mark)

    def previous_bookmark(self) -> None:
        mark = self.numbered_bookmarks.previous_before(self.editor.GetInsertionPoint())
        if mark is None:
            self._announce_result("No bookmarks in this document")
            return
        self._go_to_numbered_bookmark(mark)

    def go_to_numbered_bookmark(self, number: int) -> None:
        """Jump to one slot by number. No chord: the list's rows begin with the digit."""
        mark = self.numbered_bookmarks.get(number)
        if mark is None:
            self._announce_result(f"Bookmark {number} is not set")
            return
        self._go_to_numbered_bookmark(mark)

    def clear_numbered_bookmarks(self) -> None:
        count = self.numbered_bookmarks.clear_all()
        self._save_numbered_bookmarks()
        self._announce_result(
            f"Cleared {count} bookmark{'s' if count != 1 else ''}"
            if count
            else "No bookmarks to clear"
        )

    # ------------------------------------------------------------------ #
    # Keeping positions true
    # ------------------------------------------------------------------ #

    def shift_numbered_bookmarks(self, at: int, delta: int) -> None:
        """Move bookmarks after *at* by *delta* characters, and persist.

        Called from the edit path so an insertion above a bookmark does not
        leave it pointing at the wrong line. The shared ``BookmarkSet.shift``
        does the arithmetic; re-anchoring by snippet (bad.md 5.2, P2.2) is the
        better model and is a later change -- this is the floor, not the ceiling.
        """
        if not delta or not len(self.numbered_bookmarks):
            return
        self.numbered_bookmarks.shift(at, delta)
        self._save_numbered_bookmarks()

    def clamp_numbered_bookmarks(self) -> None:
        """Pull any bookmark past the end of the text back inside it."""
        marks = self.numbered_bookmarks
        if not len(marks):
            return
        try:
            marks.clamped_to(self.editor.GetLastPosition())
        except Exception:  # noqa: BLE001 - a dead control during teardown
            return

    def numbered_bookmark_rows(self) -> list[tuple[int, str, int]]:
        """``(number, label, position)`` for every set slot, for a list dialog.

        The rows begin with the digit deliberately: "3, Enter" then goes to
        bookmark 3, which is why there is no Go-To-Bookmark-N chord family to
        learn (bad.md 3.5). ``MAX_BOOKMARKS`` is nine for the same reason.
        """
        return [(m.number, m.label, m.position) for m in self.numbered_bookmarks.all()]

    def _numbered_bookmarks_empty_message(self) -> str:
        return (
            "No bookmarks in this document. Control Shift B sets one, "
            f"or Control Shift 1 to {MAX_BOOKMARKS} sets a numbered one."
        )

    def _adopt_numbered_bookmarks(self, tab: Any, records: object) -> None:
        """Load a freshly opened tab's stored bookmarks onto it."""
        try:
            tab.numbered_bookmarks = BookmarkSet.from_records(records)
        except Exception:  # noqa: BLE001 - a malformed store must not block an open
            tab.numbered_bookmarks = BookmarkSet()
