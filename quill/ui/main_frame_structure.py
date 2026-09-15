"""Caret-move structure announcements: the heading, the table, and the list.

A screen reader reads what the accessibility tree exposes, and a Windows edit
control exposes no paragraph style. ``RICHEDIT50W`` will tell JAWS the font name,
the point size and the weight; it has no way to say "this paragraph is a
heading". Word announces "heading level 2" only because Word implements its own
UIA provider with ``StyleId_Heading2`` behind it -- hosting a stock control buys
the control's provider and no seam to extend it.

That is true of every route a heading takes into QUILL. Rich mode's headings are
the point-size ladder in :mod:`quill.ui.richedit_rtf_surface`; markup mode's are
Markdown hashes or ``<h2>`` tags; a Word document's real ``Heading 2`` style is
read faithfully by :mod:`quill.io.docx_reader` and then rendered through that
same ladder. All three are invisible to the reader by the time the caret is in
them, so the editor says it: **"Heading 2"**, once, on arrival.

The table half was already here as ``_maybe_announce_table_transition`` and moved
in with it, because the two cues answer the same question ("what have I just
walked into?") and were drifting apart -- one had a latch and no tests, the other
had neither. Now both come from :mod:`quill.core.structure_announce`, which
QuillLite shares for the heading half, and entering a table says how big it is
instead of only that it happened.

**The list is the third, and it is the one a screen reader gives you
everywhere else.** In a browser an ``<ul>`` reaches the accessibility tree as a
list with a count, and NVDA says "list with 5 items" going in, "level 2" a rung
down and "out of list" coming out. In an editor the list is characters, so the
reader has nothing to go on -- which means a listener writing a nested outline
hears "dash space item" over and over with only the number of spaces, counted by
ear, to tell one level from the next. QUILL reads the structure with
:mod:`quill.core.list_structure` (Markdown ``-``/``1.``/``Term``/``: def``, and
HTML ``ul``/``ol``/``dl`` alike) and says the same three things a browser would.

It has a switch of its own, Ctrl+Alt+F5, deliberately separate from the heading
one. The two answer different questions and people want different answers:
reorganising an outline the list level is the work, and proof-reading the same
file it is a phrase between you and every item. Folding them into one switch
would mean giving up the half you wanted to keep.

What is *not* here is as deliberate. The heading's text is never repeated (the
reader is reading the line as the caret lands on it), body paragraphs are silent,
moving within a heading is silent, and an edit that shifts the line numbering
re-latches without speaking. GATE-13 is the standard: only what the reader cannot
know, and no more than once.
"""

from __future__ import annotations

from typing import Any

from quill.core.heading_levels import heading_level_at, heading_text_at
from quill.core.list_structure import supports_lists
from quill.core.settings import save_settings
from quill.core.structure_announce import (
    StructureAnnouncer,
    StructurePoint,
    heading_first_from,
    point_from_text,
)


class StructureAnnounceMixin:
    """Heading and table-boundary cues for ``MainFrame``.

    Host requirements: ``editor``, ``_announce``, ``_document_text_for_display``,
    ``_current_editor_mode``, ``_effective_markup_kind``.
    """

    editor: Any
    settings: Any
    _announce: Any
    _document_text_for_display: Any
    _current_editor_mode: Any
    _effective_markup_kind: Any

    _structure_announcer: StructureAnnouncer | None = None
    _structure_text_length: int | None = None

    def reset_structure_announcer(self) -> None:
        """Forget the caret's surroundings: a new document, tab or format.

        The first position after a reset is never announced, which is what stops
        opening a file on its own title from greeting every user with "Heading 1"
        across the reader's own reading of the line.
        """
        self._structure_announcer = StructureAnnouncer()
        self._structure_text_length = None

    def _structure_heading_level(self, text: str, caret: int) -> int:
        """The caret's heading level, asked of whichever mode owns the answer."""
        try:
            mode = str(self._current_editor_mode())
        except Exception:  # noqa: BLE001 - a surface with no mode is markup
            mode = "markup"
        if mode == "rich":
            # The point-size ladder, read from the control's own Text Object
            # Model, so the cue and the Describe Formatting command cannot
            # disagree about what the caret is sitting in.
            wrapper = getattr(getattr(self, "editor", None), "quill_richedit", None)
            if wrapper is None:
                return 0
            try:
                return int(wrapper.heading_level_at_caret() or 0)
            except Exception:  # noqa: BLE001 - a TOM failure must not break typing
                return 0
        try:
            kind = str(self._effective_markup_kind())
        except Exception:  # noqa: BLE001 - default to the commonest markup
            kind = "markdown"
        return heading_level_at(text, caret, markup_kind=kind)

    def _structure_point(self) -> StructurePoint | None:
        """Where the caret is, structurally, or ``None`` when unknowable."""
        editor = getattr(self, "editor", None)
        if editor is None:
            return None
        try:
            # Display-only read: document.text is the same string GetValue would
            # marshal, at zero cost (#1346 follow-up).
            text = self._document_text_for_display()
            caret = int(editor.GetInsertionPoint())
        except Exception:  # noqa: BLE001 - a non-text surface has no structure
            return None
        settings = getattr(self, "settings", None)
        headings_on = bool(getattr(settings, "announce_headings", True))
        lists_on = bool(getattr(settings, "announce_lists", True))
        # Each half is zeroed at source when its switch is off. That skips the
        # scan as well as the sentence, and -- for lists -- it is what makes
        # switching the cue back on announce the list you are already standing in
        # on the very next keypress, instead of staying silent until you happen
        # to leave it and come back.
        return point_from_text(
            text,
            caret,
            heading_level=self._structure_heading_level(text, caret) if headings_on else 0,
            # The words as well as the level, so the cue can lead with the level
            # and carry the line with it -- which is what makes it survive a
            # Ctrl+Home, where the reader cancels everything pending.
            heading_text=self._structure_heading_text(text, caret) if headings_on else "",
            # The table cue rides with the heading switch, and the settings
            # field says so ("and the shape of a table when it arrives in one").
            # They are one idea -- what shape of thing have I walked into -- and
            # giving a table a third switch would be a third thing to find.
            include_tables=headings_on,
            list_markup=self._structure_list_markup() if lists_on else None,
        )

    def _structure_heading_text(self, text: str, caret: int) -> str:
        """The caret line's heading text, in whichever markup owns the answer.

        Rich mode passes ``"plain"``, which strips nothing: a rich heading has no
        marker in the buffer, so the line already *is* its text.
        """
        try:
            kind = (
                "plain"
                if str(self._current_editor_mode()) == "rich"
                else str(self._effective_markup_kind())
            )
        except Exception:  # noqa: BLE001 - default to the commonest markup
            kind = "markdown"
        try:
            return heading_text_at(text, caret, markup_kind=kind)
        except Exception:  # noqa: BLE001 - the level alone is still a usable cue
            return ""

    def _structure_list_markup(self) -> str | None:
        """The markup lists should be read in, or ``None`` when there are none.

        A rich document has no markup lists: its bullets are the control's own,
        set through the Text Object Model, and a ``-`` typed into one is a
        hyphen. A plain document has none either -- a letter is full of hyphens,
        and a cue that fired on them would be superstition rather than help.
        """
        try:
            if str(self._current_editor_mode()) == "rich":
                return None
            kind = str(self._effective_markup_kind())
        except Exception:  # noqa: BLE001 - a surface with no markup has no lists
            return None
        return kind if supports_lists(kind) else None

    def announce_structure_at_caret(self) -> None:
        """Speak whatever the caret has just walked into, if anything.

        Fed on every caret move, quiet ones included: the latch needs every
        position to tell a crossing from a stroll.
        """
        if self._structure_announcer is None:
            self.reset_structure_announcer()
        announcer = self._structure_announcer
        assert announcer is not None
        point = self._structure_point()
        if point is None:
            return
        if not self._structure_cues_on():
            # Both switched off (Ctrl+Alt+F3, Ctrl+Alt+F5). The latch is still
            # fed, so switching either back on inside a heading or a list does
            # not stay quiet until you leave and return -- which would read as
            # the toggle not having worked.
            announcer.sync(point)
            self._structure_text_length = len(self._document_text_for_display())
            return
        try:
            length = len(self._document_text_for_display())
        except Exception:  # noqa: BLE001 - no text, nothing to say
            return
        edited = self._structure_text_length is not None and length != self._structure_text_length
        self._structure_text_length = length
        if edited:
            # The text changed under the caret. A line index that moved because
            # a line above it was deleted is not an arrival, and announcing it
            # would interrupt typing with "Heading 2".
            announcer.sync(point)
            return
        message = announcer.update(point, heading_first=heading_first_from(self.settings))
        if message:
            # ``force=False`` (the default) queues behind the reader rather than
            # interrupting it, which is right for "Heading 2" on its own: the
            # reader is speaking the line the caret just landed on, and cutting
            # across that would cost the listener the text they moved to hear.
            # It is wrong for "Heading 2, Installing", which *is* that text --
            # and queuing it is what made the cue vanish on Ctrl+Home, where the
            # reader cancels everything pending and starts again.
            self._announce(message, force=announcer.replaces_reader)

    def _structure_cues_on(self) -> bool:
        """Whether either caret cue is switched on.

        Either, not both. The point built above already zeroes the half that is
        off, so one being on is enough reason to run the latch -- and checking
        for both would silence lists whenever headings were off, which is exactly
        the coupling two separate toggles exist to avoid.
        """
        settings = getattr(self, "settings", None)
        return bool(getattr(settings, "announce_headings", True)) or bool(
            getattr(settings, "announce_lists", True)
        )

    def sync_structure_announcer(self) -> None:
        """Latch the caret's surroundings without speaking.

        For the commands that have already said it: applying Heading 2 announces
        itself, and the caret hook that fires a moment later must not repeat it.
        """
        if self._structure_announcer is None:
            self.reset_structure_announcer()
        announcer = self._structure_announcer
        assert announcer is not None
        point = self._structure_point()
        if point is not None:
            announcer.sync(point)
            try:
                self._structure_text_length = len(self._document_text_for_display())
            except Exception:  # noqa: BLE001 - the latch is still correct
                pass

    def bind_structure_cue_items(self) -> None:
        """Wire the View menu's two cue rows to their toggles.

        Here rather than in ``main_frame_menu_bindings``, which owns four
        hundred of these and was at its GATE-11 ceiling. Two switches for one
        idea are a pair, and a loop over the pair is one place a new cue gets
        added rather than two -- the shape that let a row be built, labelled and
        never bound.
        """
        import wx

        for item_id, toggle in (
            (self._id_announce_headings, self.toggle_heading_announcements),
            (self._id_announce_lists, self.toggle_list_announcements),
        ):
            self.frame.Bind(wx.EVT_MENU, lambda _e, run=toggle: run(), id=item_id)

    def toggle_list_announcements(self) -> None:
        """Ctrl+Alt+F5: stop (or resume) saying what list the caret is in.

        Its own switch rather than a share of the heading one, for the reason the
        module docstring gives. Ctrl+Alt+F4 was the obvious neighbour to
        Ctrl+Alt+F3 and was passed over deliberately: a finger that misses the
        Control key on a chord pressed this often finds Alt+F4, and what that
        costs is the document.

        The message names the consequence rather than the state, as its sibling
        does -- "Lists will not be announced" beats "off", which leaves you
        working out what was off and what it did.
        """
        on = not bool(getattr(self.settings, "announce_lists", True))
        self.settings.announce_lists = on
        save_settings(self.settings)
        # The View menu shows this as a check item; a tick that disagrees with
        # the behaviour is worse than no tick at all.
        item = getattr(self, "_announce_lists_item", None)
        if item is not None:
            try:
                item.Check(on)
            except RuntimeError:  # the menu can be gone during teardown
                pass
        if on:
            self.sync_structure_announcer()
            self._announce("Lists announced as you enter them")
        else:
            self._announce("Lists will not be announced")

    def toggle_heading_announcements(self) -> None:
        """Ctrl+Alt+F3: stop (or resume) the caret-move structure cues.

        A toggle rather than a buried preference because it is a decision per
        document and per task: in a report the level is the whole point, and in
        a file being read *as text* it is one sentence between you and the line.
        The message names the consequence rather than the state.
        """
        on = not bool(getattr(self.settings, "announce_headings", True))
        self.settings.announce_headings = on
        save_settings(self.settings)
        # The View menu shows this as a check item; a tick that disagrees with
        # the behaviour is worse than no tick at all.
        item = getattr(self, "_announce_headings_item", None)
        if item is not None:
            try:
                item.Check(on)
            except RuntimeError:  # the menu can be gone during teardown
                pass
        if on:
            self.sync_structure_announcer()
            self._announce("Headings announced on arrival")
        else:
            self._announce("Headings will not be announced")
