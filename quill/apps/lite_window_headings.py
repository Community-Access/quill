"""Headings in QuillLite: finding them, and saying so when you arrive.

QuillLite's headings are real in every way that matters to a document and
invisible in the one way that matters to a listener. In rich text they are the
point-size ladder (:mod:`quill.ui.richedit_rtf_surface`); in plain markup they
are Markdown hashes. Neither is a paragraph style, and a Windows edit control
has no way to tell JAWS or NVDA that a paragraph is a heading -- so the reader
says nothing, and a listener arrowing down a document hears a line of text with
no clue that it is a title.

That is squarely GATE-13's "only what the reader cannot know", so QuillLite says
it: "Heading 2", once, on arrival. The rules and the latch live in the shared
:mod:`quill.core.structure_announce`, because QUILL announces the same thing the
same way and two copies would drift apart within a release.

Two suppressions do most of the work here, and both were learned the hard way
from over-announcing:

* **An edit is not an arrival.** Deleting the line above a heading changes which
  line the heading is on, and a naive latch reads that as "you have arrived at a
  heading" and says so in the middle of typing. So a move that follows a change
  in the text only re-latches; it never speaks.
* **Tables are QUILL's, not QuillLite's.** ``include_tables=False`` is passed on
  every call. Cell navigation is a full-QUILL feature and announcing the edge of
  a grid the small editor cannot then navigate would advertise something that is
  not there.
"""

from __future__ import annotations

from typing import Any

from quill.apps.lite_dialogs import choose_heading
from quill.core.heading_levels import heading_level_at
from quill.core.lite.filetypes import has_markdown_headings
from quill.core.markdown_sections import parse_heading_blocks
from quill.core.structure_announce import StructureAnnouncer, StructurePoint
from quill.ui.richedit_editing import RICH


class DocumentHeadingsMixin:
    """Heading navigation and caret-move heading cues for :class:`DocumentFrame`."""

    control: Any
    editor: Any
    _announce: Any
    _go_to: Any

    _structure_announcer: StructureAnnouncer | None = None
    _structure_text_length: int | None = None

    def reset_structure_announcer(self) -> None:
        """Forget where the caret was: a new document, or a format switch.

        Called on open and on a mode change so the first position in the new
        document is not announced -- opening a file whose first line is its own
        title should not greet every user with "Heading 1" over the reader's
        own reading of the line.
        """
        self._structure_announcer = StructureAnnouncer()
        self._structure_text_length = None

    def _structure_point(self) -> StructurePoint | None:
        """Where the caret is, structurally, or ``None`` if that is unknowable."""
        try:
            text = self.control.GetValue()
            caret = int(self.control.GetInsertionPoint())
        except (AttributeError, RuntimeError):
            return None
        if self.editor.mode == RICH:
            # The ladder, read from the control's own Text Object Model, so the
            # announcement and the status bar's Heading cell cannot disagree.
            try:
                level = int(self.editor.heading_level_at_caret() or 0)
            except Exception:  # noqa: BLE001 - a TOM failure must not break typing
                level = 0
        elif self._markdown_headings_apply():
            level = heading_level_at(text, caret)
        else:
            # A ``#`` in a shell script, a Python file or an ini is a comment.
            # Announcing "Heading 1" on most lines of a build script is the
            # over-announcement that makes an app tiring to use.
            level = 0
        return StructurePoint(
            paragraph_key=text.count("\n", 0, max(0, min(caret, len(text)))),
            heading_level=level,
        )

    def announce_structure_at_caret(self) -> None:
        """Speak the heading the caret has just entered, if it has entered one.

        Fed on every caret move, including the quiet ones: the latch needs every
        position to know which of them is a crossing.
        """
        if self._structure_announcer is None:
            self.reset_structure_announcer()
        announcer = self._structure_announcer
        assert announcer is not None
        point = self._structure_point()
        if point is None:
            return
        if not self.app.settings.announce_headings:
            # Switched off. The latch is still fed, so switching it back on
            # mid-document announces the next heading you arrive at rather than
            # staying quiet until you happen to leave one and return.
            announcer.sync(point)
            self._structure_text_length = len(self.control.GetValue())
            return
        try:
            length = len(self.control.GetValue())
        except (AttributeError, RuntimeError):
            return
        edited = self._structure_text_length is not None and length != self._structure_text_length
        self._structure_text_length = length
        if edited:
            # The text changed under the caret. Re-latch silently: a line index
            # that moved because a line was deleted is not an arrival.
            announcer.sync(point)
            return
        message = announcer.update(point)
        if message:
            # Queued, never interrupting. The reader is speaking the line the
            # caret just landed on; cutting across it to say "Heading 2" would
            # take away the text the user moved there to hear. Leasey reaches
            # the same conclusion with its speak-then-spell ordering.
            self._announce(message, interrupt=False)

    def sync_structure_announcer(self) -> None:
        """Latch the caret's surroundings without speaking.

        For the commands that have already said it themselves -- applying
        Heading 2 announces "Heading 2", and the caret hook that fires a moment
        later must not repeat it.
        """
        if self._structure_announcer is None:
            self.reset_structure_announcer()
        announcer = self._structure_announcer
        assert announcer is not None
        point = self._structure_point()
        if point is not None:
            announcer.sync(point)
            try:
                self._structure_text_length = len(self.control.GetValue())
            except (AttributeError, RuntimeError):
                pass

    def _plain_headings(self) -> list[tuple[int, int, str]]:
        """Markdown headings in a plain-text document, as ``(start, level, title)``.

        The same shape :meth:`RichEditDocument.all_headings` returns for the
        rich ladder, so heading navigation and the headings list take one code
        path in both modes. Parsed by
        :func:`~quill.core.markdown_sections.parse_heading_blocks`, which knows
        to skip a ``#`` inside a fenced code block -- a plain regex does not,
        and a shell comment in a code sample is not a heading.
        """
        if not self._markdown_headings_apply():
            return []
        blocks = parse_heading_blocks(self.control.GetValue(), "markdown")
        return [(block.start, block.level, block.title) for block in blocks]

    def _markdown_headings_apply(self) -> bool:
        """Whether a leading ``#`` is a heading in *this* plain document.

        See :func:`~quill.core.lite.filetypes.has_markdown_headings`: it is in a
        ``.md`` or a ``.txt`` or an untitled buffer, and it is a comment in the
        ``.py`` / ``.sh`` / ``.ini`` files a Notepad replacement opens all day.
        """
        path = getattr(self, "path", None)
        return has_markdown_headings(path.name if path is not None else None)

    def _navigate_heading(self, *, reverse: bool) -> None:
        # Plain text has headings too -- they are Markdown hashes rather than
        # the point-size ladder. Refusing here told a listener the document had
        # no structure when the very next command (Alt+Shift+Right) would
        # happily change a heading's level.
        if self.editor.mode != RICH:
            self._navigate_plain_heading(reverse=reverse)
            return
        found = self.editor.next_heading(self.control.GetInsertionPoint(), reverse=reverse)
        if found is None:
            self._announce("No previous heading" if reverse else "No next heading")
            return
        start, level = found
        self._go_to(start)
        # The level *and* the text: the level alone says what shape the document
        # is, not where in it the caret has landed.
        self._announce(f"Heading {level}: {self.editor.paragraph_text_at(start)}")

    def cmd_next_heading(self) -> None:
        self._navigate_heading(reverse=False)

    def cmd_previous_heading(self) -> None:
        self._navigate_heading(reverse=True)

    def _navigate_plain_heading(self, *, reverse: bool) -> None:
        """Next / previous Markdown heading, announced exactly as the rich one."""
        caret = self.control.GetInsertionPoint()
        headings = self._plain_headings()
        candidates = (
            [h for h in reversed(headings) if h[0] < caret]
            if reverse
            else [h for h in headings if h[0] > caret]
        )
        if not candidates:
            self._announce("No previous heading" if reverse else "No next heading")
            return
        start, level, title = candidates[0]
        self._go_to(start)
        # The level *and* the text, for the same reason the rich path gives both.
        self._announce(f"Heading {level}: {title}")
        self.sync_structure_announcer()

    def cmd_list_headings(self) -> None:
        if self.editor.mode != RICH:
            headings = self._plain_headings()
            if not headings:
                self._announce("No headings in this document")
                return
            target = choose_heading(self, headings)
            if target is None:
                self.control.SetFocus()
                return
            self._go_to(target)
            self.sync_structure_announcer()
            return
        headings = self.editor.all_headings()
        if not headings:
            self._announce("No headings in this document")
            return
        target = choose_heading(self, headings)
        if target is None:
            self.control.SetFocus()
            return
        self._go_to(target)

    def cmd_toggle_heading_announcements(self) -> None:
        """Ctrl+Alt+F3: stop (or resume) saying "Heading 2" on arrival.

        A toggle rather than a buried preference because it is a decision per
        document and per task. Editing a report, the level is the whole point;
        reading a file *as text*, it is one sentence between you and the line.

        The message names the consequence rather than the state -- "Headings
        will not be announced" beats "off", which leaves you working out what
        was off and what it did.
        """
        settings = self.app.settings
        settings.announce_headings = not settings.announce_headings
        self.app.save_settings()
        if settings.announce_headings:
            self.sync_structure_announcer()
            self._announce("Headings announced on arrival")
        else:
            self._announce("Headings will not be announced")
