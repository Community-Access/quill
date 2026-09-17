"""Structure in QuillLite: the heading you arrived at, and the list you are in.

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

**Lists are the second half, and the case for them is even plainer.** A
screen reader in a browser says "list with 5 items", "level 2" and "out of
list", because the browser hands it an ``<ul>`` with a count. An editor hands it
characters. So a listener writing a nested bullet list hears "dash space item"
over and over with nothing to separate the second level from the third but the
number of spaces they can count by ear. The reading is
:mod:`quill.core.list_structure`; the deciding is the same shared announcer, on
the same latch, under a toggle of its own (Ctrl+Alt+F5).

The two toggles are separate on purpose. They answer different questions and
people want different answers: editing a report the heading level is the whole
point, and reorganising an outline the list level is. Folding both into one
switch would mean giving up the half you wanted to keep.

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
from quill.core.heading_levels import heading_level_at, heading_text_at
from quill.core.list_structure import supports_lists
from quill.core.markdown_sections import parse_heading_blocks
from quill.core.structure_announce import (
    StructureAnnouncer,
    heading_first_from,
    point_from_text,
)
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
        self._structure_revision = None

    def _structure_point(self):
        """Where the caret is, structurally, or ``None`` if that is unknowable."""
        try:
            text = self.doc_text.text
            caret = int(self.control.GetInsertionPoint())
        except (AttributeError, RuntimeError):
            return None
        surface = self.markup_surface()
        if self.editor.mode == RICH:
            # The ladder, read from the control's own Text Object Model, so the
            # announcement and the status bar's Heading cell cannot disagree.
            try:
                level = int(self.editor.heading_level_at_caret() or 0)
            except Exception:  # noqa: BLE001 - a TOM failure must not break typing
                level = 0
        elif surface is not None:
            level = heading_level_at(text, caret, markup_kind=surface)
        else:
            # A ``#`` in a shell script, a Python file or an ini is a comment.
            # Announcing "Heading 1" on most lines of a build script is the
            # over-announcement that makes an app tiring to use.
            level = 0
        settings = self.app.settings
        if not bool(getattr(settings, "announce_headings", True)):
            level = 0
        # ``None`` when list cues are off, which is deliberate rather than lazy:
        # it skips the scan as well as the sentence, and it makes switching the
        # cue back on announce the list you are already standing in on the very
        # next keypress instead of staying silent until you leave and return.
        list_markup = (
            surface
            if surface is not None
            and supports_lists(surface)
            and bool(getattr(settings, "announce_lists", True))
            else None
        )
        return point_from_text(
            text,
            caret,
            heading_level=level,
            # The words as well as the level, so the cue can lead with the level
            # and carry the line with it. In rich mode the buffer line *is* the
            # heading's text; in markup it is the line with its marker taken off.
            heading_text=(
                heading_text_at(text, caret, markup_kind=surface or "plain") if level else ""
            ),
            # Tables are QUILL's. Announcing the edge of a grid the small editor
            # cannot then navigate would advertise something that is not there.
            include_tables=False,
            list_markup=list_markup,
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
        if not self._structure_cues_on():
            # Both switched off. The latch is still fed, so switching either back
            # on mid-document announces the next thing you arrive at rather than
            # staying quiet until you happen to leave one and return.
            announcer.sync(point)
            self._structure_revision = self.doc_text.revision
            return
        # The revision, not the length. This ran on every caret move and read
        # the whole buffer to measure it -- twice, counting the sync below --
        # which is the second half of what an arrow key cost in a large file
        # (bad.md V3). The mirror's revision answers the same question ("has the
        # text changed since I last looked?") for nothing, and answers it
        # correctly for an edit that happens to leave the length unchanged,
        # which the old test could not see at all.
        try:
            revision = self.doc_text.revision
        except (AttributeError, RuntimeError):
            return
        edited = self._structure_revision is not None and revision != self._structure_revision
        self._structure_revision = revision
        if edited:
            # The text changed under the caret. Re-latch silently: a line index
            # that moved because a line was deleted is not an arrival.
            announcer.sync(point)
            return
        message = announcer.update(point, heading_first=heading_first_from(self.app.settings))
        if message:
            # Queued unless the phrase already contains the line's own text.
            # Queuing is right for "Heading 2" on its own -- the reader is
            # speaking the line and cutting across it would take away the text
            # the user moved there to hear. It is wrong for "Heading 2,
            # Installing", which *is* that text: there, interrupting is what
            # makes the cue survive a Ctrl+Home, where the reader cancels
            # everything pending and our queued phrase is simply never heard.
            self._announce(message, interrupt=announcer.replaces_reader)

    def _structure_cues_on(self) -> bool:
        """Whether either caret cue is switched on.

        Either, not both: the point built above already zeroes the half that is
        off, so one being on is enough reason to run the latch. Checking for
        both would silence lists whenever headings were off, which is exactly
        the coupling the two separate toggles exist to avoid.
        """
        settings = self.app.settings
        return bool(getattr(settings, "announce_headings", True)) or bool(
            getattr(settings, "announce_lists", True)
        )

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
                self._structure_revision = self.doc_text.revision
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
        surface = self.markup_surface()
        if surface is None:
            return []
        blocks = parse_heading_blocks(self.doc_text.text, surface)
        return [(block.start, block.level, block.title) for block in blocks]

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

    def cmd_toggle_list_announcements(self) -> None:
        """Ctrl+Alt+F5: stop (or resume) saying what list the caret is in.

        Its own switch rather than a share of the heading one, because the two
        answer different questions. Reorganising an outline, the level is the
        work; proof-reading the same file, it is a phrase between you and every
        item. Ctrl+Alt+F4 was the obvious neighbour to Ctrl+Alt+F3 and was passed
        over deliberately: a finger that misses the Control key on a chord you
        press this often finds Alt+F4, and the cost of that is the document.

        The message names the consequence rather than the state, as its sibling
        does -- "Lists will not be announced" beats "off", which leaves you
        working out what was off and what it did.
        """
        settings = self.app.settings
        settings.announce_lists = not getattr(settings, "announce_lists", True)
        self.app.save_settings()
        if settings.announce_lists:
            self.sync_structure_announcer()
            self._announce("Lists announced as you enter them")
        else:
            self._announce("Lists will not be announced")

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
