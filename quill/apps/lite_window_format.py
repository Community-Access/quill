"""The Format menu: WordPad's, key for key.

Split from :mod:`quill.apps.lite_window_commands` because it is the one menu
with a rule of its own, and the rule runs through every handler here:
**formatting exists only in rich text, and saying so is part of the feature.**

``_require_rich`` is therefore not a guard clause, it is the product: a
formatting key pressed where it cannot work says what would make it work. A
command that quietly does nothing is indistinguishable, to a listener, from a
key that is not bound at all -- and they would have no way to find out which.

That rule got *narrower* when plain documents gained a language
(:mod:`quill.apps.lite_window_markup`). Bold in a Markdown or HTML document is
no longer unavailable: it writes ``**bold**`` or ``<strong>``, which is what
somebody editing one of those files meant by pressing Ctrl+B. So the three run
attributes and the heading ladder try markup first and fall back to the
refusal, and the refusal itself now names the real obstacle -- a ``.py`` has no
markup and never will, and telling its author to switch to rich text would be
advice that does not apply to the file they are in.

The keys are WordPad's, deliberately and without improvement: Ctrl+B, I and U;
Ctrl+L, E, R and J for the four alignments; Ctrl+Shift+L for bullets; Ctrl+1,
Ctrl+5 and Ctrl+2 for single, one-and-a-half and double spacing; and
Ctrl+Shift+> and Ctrl+Shift+< to grow and shrink the selection. Somebody moving
from WordPad should not have to learn anything.

Two additions WordPad does not have, both from QUILL: the **heading ladder**
(Ctrl+Alt+1 to 4, Ctrl+Alt+0 for body text), and **Describe Formatting**
(Ctrl+Shift+D), which answers "what am I standing in?" -- the question a
formatted document raises and a screen reader cannot answer on its own.
"""

from __future__ import annotations

import wx

from quill.core.heading_levels import LevelResult, adjust_heading_level
from quill.core.list_style import LIST_STYLES, cycle_list_style
from quill.core.lite.filetypes import language_label
from quill.core.lite.keymap import spoken_key_for
from quill.core.markdown_sections import MoveResult, move_section
from quill.ui.atomic_edit import replace_as_one_undo
from quill.ui.richedit_editing import (
    LINE_SPACING_DOUBLE,
    LINE_SPACING_ONE_AND_A_HALF,
    LINE_SPACING_SINGLE,
    PLAIN,
    RICH,
)
from quill.ui.richedit_rtf_surface import HEADING_POINT_SIZES, RichEditRtfError

__all__ = ["DocumentFormatCommandsMixin"]

#: The deepest rich-text heading, read off the ladder rather than written twice:
#: the menu, the demote ceiling and the sizes must not be able to disagree about
#: how many levels there are.
MAX_HEADING_LEVEL = max(HEADING_POINT_SIZES)


class DocumentFormatCommandsMixin:
    """The ``cmd_*`` handlers for the Format menu.

    Mixed into :class:`~quill.apps.lite_window.DocumentFrame`, which supplies
    ``control``, ``editor``, ``_announce`` and ``_set_modified``.
    """

    def _require_rich(self) -> bool:
        """True when formatting can run; otherwise say why, and how to fix it."""
        if self.editor.mode != RICH:
            self._announce(self._no_formatting_here())
            return False
        if not self.editor.rtf_available():
            self._announce("Rich text formatting is unavailable on this system")
            return False
        return True

    def _no_formatting_here(self) -> str:
        """Why this document cannot be formatted, and what would change that.

        Two different sentences for two genuinely different situations, because
        one piece of advice that is wrong half the time is worse than none. In a
        ``.txt`` or a ``.py`` the honest answer is rich text. In a ``.md`` opened
        with the language set to Plain -- which somebody can do deliberately --
        the nearer answer is to set the language back, and being sent to rich
        text instead would convert the document they are editing.
        """
        language = self.document_language()
        # The ring key is a RING -- plain, Markdown, HTML, rich, round again
        # (cmd_switch_document_kind) -- so "press it for rich text" was wrong
        # from every stop but HTML. From a plain document one press lands on
        # Markdown. Advice that is wrong half the time is worse than none, which
        # is the rule this method was written for; it was just breaking it
        # itself (bad.md R10).
        #
        # Read out of the keymap rather than typed into the sentence: the chord
        # moved on 2026-09-16 and is rebindable besides, and a refusal that names
        # a key which does something else is the same defect as no refusal at
        # all (bad.md C7).
        keymap = getattr(self.app, "keymap", None)
        ring = spoken_key_for(keymap, "cmd_switch_document_kind")
        language_key = spoken_key_for(keymap, "cmd_set_language")
        if language == "plain":
            return (
                f"This document has no formatting. {ring} cycles the kind of "
                f"document -- Markdown, then HTML, then rich text -- or {language_key} "
                "sets the language without converting anything."
            )
        return (
            f"Formatting is not available in this {language_label(language)} document. "
            f"{ring} cycles on to the next kind; rich text is the one that "
            "has formatting."
        )

    def _toggle_attr(self, attr: str, label: str) -> None:
        # Markup first: in a Markdown or HTML document Ctrl+B has a real answer
        # that is not "go and be in a different kind of document".
        if self.apply_markup_run(attr):
            return
        if not self._require_rich():
            return
        try:
            state = self.editor.toggle_font_attr(attr)
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(f"{label} on" if state else f"{label} off")

    def cmd_normal_text(self) -> None:
        """Word's Ctrl+Shift+N: take everything off this text and leave it plain.

        Asked for directly, while testing rich text: "we also need a normal text
        command ... something like Word's Ctrl+Shift+N to set text to normal
        mode in an RTF document."

        Every other formatting command is a toggle or a set, which means each
        one needs you to already know what is applied. Bold off needs bold to be
        on; a twenty-point run needs the size ladder walked back down; a colour,
        a highlight or a list had no "none" at all. Somebody who cannot glance
        at the page to see what is still on it was left with no way to be sure,
        and "no way to be sure what this text looks like" is the whole problem
        this editor exists to solve. One key that means "whatever is on this,
        take it off" is the answer, and it is Word's key for it.

        Spoken, because nothing else will say it. Formatting coming *off* is
        invisible and silent: the text does not move, the caret does not move,
        no control gains or loses focus, and a screen reader reports none of it.
        The one thing GATE-13 asks is that the app says what only the app
        knows, and this is exactly that.

        In a Markdown or HTML document the same key removes the heading marks,
        because that is what "normal" means to a line that is written in
        markup -- the emphasis around a word is text the user typed, and a
        command that silently deleted their asterisks would be doing something
        they did not ask for.
        """
        if self.apply_markup_heading(0):
            self._announce("Normal text")
            self.sync_structure_announcer()
            return
        if not self._require_rich():
            return
        try:
            self.editor.clear_formatting()
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce("Normal text")
        # Said already; latch it so the caret hook does not repeat it a moment
        # later now that the paragraph is no longer a heading.
        self.sync_structure_announcer()

    def cmd_bold(self) -> None:
        self._toggle_attr("Bold", "Bold")

    def cmd_italic(self) -> None:
        self._toggle_attr("Italic", "Italic")

    def cmd_underline(self) -> None:
        self._toggle_attr("Underline", "Underline")

    def _heading(self, level: int) -> None:
        # Markdown hashes or an ``<h2>`` in a markup document; the point-size
        # ladder in a rich one. One key, one idea, two mechanisms.
        if self.apply_markup_heading(level):
            return
        if not self._require_rich():
            return
        try:
            self.editor.set_heading(level)
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(f"Heading {level}" if level else "Body text")
        # Already said. Latch it so the caret hook that fires next does not say
        # it again a moment later.
        self.sync_structure_announcer()

    def _shift_heading(self, delta: int) -> None:
        """Promote or demote the heading the cursor is in, in either mode.

        Two documents, two mechanisms, one command, because "make this heading
        one level shallower" is one idea to the person doing it:

        * **Rich text** is QuillLite's own heading ladder -- bold plus a point
          size -- so the level is read back off the caret and re-applied one
          step along. Level 1 promoted stays 1 rather than becoming body text:
          losing a heading entirely is not what Alt+Shift+Left means, and it
          would silently take the paragraph out of the headings list.
        * **Plain text** is Markdown, so it is the hashes, through the shared
          :func:`~quill.core.heading_levels.adjust_heading_level` that QUILL's
          own Alt+Shift+Left / Right run.

        Every refusal is spoken separately. Nothing here moves the caret or
        makes a sound of its own, so "not on a heading", "already at level one"
        and "nothing happened because the key is not bound" are the same event
        to a listener unless they are told apart.
        """
        if self.editor.mode == RICH:
            level = self.editor.heading_level_at_caret()
            if not level:
                self._announce("Put the cursor in a heading to change its level")
                return
            # Six, not four: the rich ladder gained levels 5 and 6 sizes of
            # their own on 2026-09-09, so Alt+Shift+Right now walks all the way
            # down instead of stopping two rungs short of the menu.
            new_level = min(MAX_HEADING_LEVEL, max(1, level + delta))
            if new_level == level:
                self._announce(
                    "Already Heading 1" if delta < 0 else "Already at the smallest heading"
                )
                return
            self._heading(new_level)
            return
        text = self.control.GetValue()
        # The document's own markup, so Alt+Shift+Right walks an ``<h2>`` down
        # to an ``<h3>`` in an HTML file rather than looking for hashes that a
        # well-formed HTML document will never contain.
        #
        # And **no fallback to Markdown**. A plain text document has no markup
        # at all, so asking for hashes in one found none and answered "put the
        # cursor on a heading line" -- which tells somebody their plain document
        # has heading lines somewhere. It does not. Reported as the editor being
        # "misleading about markdown ... in plain text we are not writing
        # markdown, just plain text".
        surface = self.markup_surface()
        if not surface:
            self._announce(self._no_formatting_here())
            return
        change = adjust_heading_level(
            text, self.control.GetInsertionPoint(), delta, markup_kind=surface
        )
        if change.result is LevelResult.NO_MARKUP:
            self._announce(self._no_formatting_here())
            return
        if change.result is LevelResult.NOT_A_HEADING:
            self._announce("Put the cursor on a heading line to change its level")
            return
        if change.result is LevelResult.AT_TOP:
            self._announce("Already Heading 1")
            return
        if change.result is LevelResult.AT_BOTTOM:
            self._announce("Already Heading 6")
            return
        caret = self.control.GetInsertionPoint()
        replace_as_one_undo(self.control, change.start, change.end, change.replacement)
        # Hold the caret's place in the line rather than in the document: the
        # line just grew or shrank by one hash in front of it.
        moved = len(change.replacement) - (change.end - change.start)
        self.control.SetInsertionPoint(max(change.start, min(caret + moved, len(text) + moved)))
        self._set_modified(True)
        self._touch_status()
        self._announce(f"Heading {change.new_level}")
        self.sync_structure_announcer()

    def cmd_promote_heading(self) -> None:
        """Alt+Shift+Left: one level shallower, towards Heading 1."""
        self._shift_heading(-1)

    def cmd_demote_heading(self) -> None:
        """Alt+Shift+Right: one level deeper."""
        self._shift_heading(1)

    def _move_section(self, direction: str) -> None:
        """Move the whole section the cursor is in, heading and body together.

        QUILL's own :func:`~quill.core.markdown_sections.move_section`, over
        Markdown, and therefore plain text only: rich-text headings are a font
        size rather than markup, and moving formatted runs through the Text
        Object Model is a different piece of work that QUILL has not done
        either. Saying so is better than a key that quietly does nothing in
        half the documents somebody opens.

        This is the operation cut-and-paste is worst at. Reorganising by hand
        means selecting from a heading to the start of the next one -- a
        boundary you cannot see and have to find by ear -- and the usual result
        of getting it wrong is losing your place in the document you were
        halfway through reorganising.
        """
        if self.editor.mode == RICH:
            self._announce(
                "Moving sections works in plain text documents, where headings are Markdown"
            )
            return
        text = self.control.GetValue()
        caret = self.control.GetInsertionPoint()
        # The document's own markup, not an assumed "markdown". An HTML document
        # has headings too, and move_section was looking for hashes it would
        # never find in one -- so Alt+Shift+Up in a .html said "not in a
        # section" about a section (bad.md R13).
        # No Markdown fallback here either: "No section to move" in a plain
        # text document is a sentence about sections that document cannot have.
        surface = self.markup_surface()
        if not surface:
            self._announce(self._no_formatting_here())
            return
        new_text, new_caret, result, announce = move_section(
            text, caret, direction, markup_kind=surface
        )
        if result is not MoveResult.OK:
            self._announce(announce)
            return
        replace_as_one_undo(self.control, 0, self.control.GetLastPosition(), new_text)
        self.control.SetInsertionPoint(min(new_caret, self.control.GetLastPosition()))
        self.control.ShowPosition(self.control.GetInsertionPoint())
        self._set_modified(True)
        self._touch_status()
        self._announce(announce)

    def cmd_move_section_up(self) -> None:
        self._move_section("up")

    def cmd_move_section_down(self) -> None:
        self._move_section("down")

    def cmd_heading_0(self) -> None:
        self._heading(0)

    def cmd_heading_1(self) -> None:
        self._heading(1)

    def cmd_heading_2(self) -> None:
        self._heading(2)

    def cmd_heading_3(self) -> None:
        self._heading(3)

    def cmd_heading_4(self) -> None:
        self._heading(4)

    def cmd_heading_5(self) -> None:
        self._heading(5)

    def cmd_heading_6(self) -> None:
        self._heading(6)

    def _align(self, how: str, label: str) -> None:
        if not self._require_rich():
            return
        try:
            self.editor.set_alignment(how)
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(label)

    def cmd_align_left(self) -> None:
        self._align("left", "Aligned left")

    def cmd_align_center(self) -> None:
        self._align("center", "Centred")

    def cmd_align_right(self) -> None:
        self._align("right", "Aligned right")

    def cmd_align_justify(self) -> None:
        self._align("justify", "Justified")

    #: What each stop of the ring is called when it announces itself.
    _LIST_STYLE_WORDS = {
        "none": "Not a list",
        "bullet": "Bulleted list",
        "numbered": "Numbered list",
    }

    def cmd_cycle_list_style(self) -> None:
        """Ctrl+Shift+L: bulleted list, numbered list, no list, round again.

        WordPad's key and WordPad's behaviour. It was a *toggle* -- bullets on,
        bullets off -- which meant QuillLite could not make a numbered list at
        all, in any kind of document, while its own PRD said an ordered list is
        structure a reader announces and should come first (bad.md P1.5, 4.2).

        Two implementations, because a list is two different things:

        * In **rich text** it is ``ITextPara.ListType`` -- a paragraph property
          the control draws and renumbers itself. Nothing is written into the
          text, which is what makes it a list rather than a line that starts
          with a bullet character.
        * In **Markdown** it is the ``- `` and ``1. `` markers, over the
          selected lines or the caret's line and *never* the whole document:
          QUILL's list-off rewrote the entire buffer, which removed every other
          list in the file and cleared the undo stack with them (bad.md R2).

        HTML says so rather than guessing: ``<ul>`` needs a wrapper as well as
        per-item tags, and half of one is a document that will not render.
        """
        if self.editor.mode == RICH:
            try:
                style = LIST_STYLES[
                    (LIST_STYLES.index(self.editor.list_style_at_caret()) + 1) % len(LIST_STYLES)
                ]
                self.editor.set_list_style(style)
            except RichEditRtfError as exc:
                self._announce(str(exc))
                return
            self._set_modified(True)
            self._announce(self._LIST_STYLE_WORDS[style])
            return
        if self.markup_surface() != "markdown":
            self._announce(self._no_formatting_here())
            return
        text = self.control.GetValue()
        start, end = self.control.GetSelection()
        updated, style, span_start, span_end = cycle_list_style(text, start, end)
        replace_as_one_undo(self.control, 0, self.control.GetLastPosition(), updated)
        self.control.SetSelection(span_start, span_end)
        self._set_modified(True)
        self._touch_status()
        self._announce(self._LIST_STYLE_WORDS[style])

    def _line_spacing(self, rule: int, label: str) -> None:
        if not self._require_rich():
            return
        try:
            self.editor.set_line_spacing(rule)
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(label)

    def cmd_spacing_single(self) -> None:
        self._line_spacing(LINE_SPACING_SINGLE, "Single spacing")

    def cmd_spacing_one_half(self) -> None:
        self._line_spacing(LINE_SPACING_ONE_AND_A_HALF, "One and a half spacing")

    def cmd_spacing_double(self) -> None:
        self._line_spacing(LINE_SPACING_DOUBLE, "Double spacing")

    def _step_font(self, *, larger: bool) -> None:
        """WordPad's Ctrl+Shift+> and Ctrl+Shift+<: resize the selection itself.

        Not the same thing as the View menu's text size, and the difference is
        worth knowing: this changes the *document*, so it is an edit and it is
        saved; the View menu changes the *view*, so it is neither.
        """
        if not self._require_rich():
            return
        try:
            size = self.editor.step_font_size(larger=larger)
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(f"{size:g} point")

    def cmd_grow_font(self) -> None:
        self._step_font(larger=True)

    def cmd_shrink_font(self) -> None:
        self._step_font(larger=False)

    def cmd_selection_font(self) -> None:
        """Set the face and size of the selection only (rich mode)."""
        if not self._require_rich():
            return
        with wx.FontDialog(self, wx.FontData()) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            font = dialog.GetFontData().GetChosenFont()
        try:
            self.editor.set_font_name(font.GetFaceName())
            self.editor.set_font_size(font.GetPointSize())
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(f"{font.GetFaceName()}, {font.GetPointSize()} point")

    def cmd_describe(self) -> None:
        """Say what the formatting at the cursor is -- QUILL's Describe Formatting.

        Three answers, because there are three kinds of document with formatting
        in them:

        * **Rich text** asks the control's own Text Object Model -- "Arial, 14
          point, bold, centred".
        * **Markdown** parses the markup, through the same shared pair QUILL
          uses (:func:`~quill.io.rtf_model.format_at_markdown_offset` and
          :func:`~quill.core.format_speech.describe_inline_format`). It used to
          answer "Plain text" with the caret inside ``**bold**`` or on a ``##``
          heading, which is not a description of the formatting, it is a denial
          that there is any (bad.md R13).
        * **Everything else** -- HTML, and a plain document with no markup
          language -- says so rather than guessing. QUILL answers the same way.
        """
        if self.editor.mode == RICH:
            try:
                self._announce(self.editor.caret_format_description())
            except RichEditRtfError as exc:
                self._announce(str(exc))
            return
        if self.markup_surface() != "markdown":
            self._announce("Plain text")
            return
        from quill.core.format_speech import describe_inline_format
        from quill.io.rtf_model import format_at_markdown_offset

        fmt = format_at_markdown_offset(self.doc_text.text, self.control.GetInsertionPoint())
        phrase = describe_inline_format(
            bold=fmt.bold,
            italic=fmt.italic,
            href=fmt.href,
            heading_level=fmt.heading_level,
            bullet=fmt.bullet,
            underline=fmt.underline,
            strike=fmt.strike,
            superscript=fmt.superscript,
            subscript=fmt.subscript,
            font_family=fmt.font_family,
            font_size_pt=fmt.font_size_pt,
            color=fmt.color,
            highlight=fmt.highlight,
            align=fmt.align,
            named_style=fmt.named_style,
            line_spacing=fmt.line_spacing,
            space_before=fmt.space_before,
            space_after=fmt.space_after,
            indent=fmt.indent,
            first_line_indent=fmt.first_line_indent,
        )
        self._announce(phrase or "Plain text")

    def cmd_switch_mode(self) -> None:
        """Plain to rich and back -- the two-stop half of Ctrl+Shift+M's ring.

        Not bound to anything any more.
        :meth:`~quill.apps.lite_window_markup.DocumentMarkupMixin.cmd_switch_document_kind`
        holds the key and rings through all four kinds of document, of which
        this pair is two. Kept because it is still exactly the right thing to
        call when what you mean is "make this rich text" -- which is what the
        ring's last stop means, and what several tests mean.
        """
        self.switch_mode(PLAIN if self.editor.mode == RICH else RICH)
