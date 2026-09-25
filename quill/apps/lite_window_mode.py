"""Switching a document between plain and rich, without throwing the document away.

Split from :mod:`quill.apps.lite_window_theme`, which is about how a document
*looks*. This is about what it *is*, and the two only looked like one question
while the switch was doing nothing: it used to take ``GetValue()`` -- the plain
characters -- and put them in the other mode. Both directions lost something,
and neither said so.

* **Rich to plain** dropped every heading, every bold run and every list, and
  announced "Plain text mode". A person who had spent an afternoon formatting a
  document and pressed the wrong key got a wall of unmarked text, with the undo
  stack cleared by the ``ChangeValue`` that did it.
* **Plain to rich** left ``## Title`` sitting in the buffer as two hash marks
  and a space. The document *said* it was rich text; nothing in it was.

QUILL has converted both ways since 0.9.0-beta3, through the same wx-free
converters in :mod:`quill.io.rtf`, and warns first about anything the target
cannot carry. QUILL Lite may never be behind QUILL on an editor-core capability
(CLAUDE.md), so it converts too, through the same functions and with the same
warning (bad.md R6).

**What "convert" means in each direction, and why it is not symmetrical.**

Rich to plain is always Markdown: it is the only markup QUILL Lite's converters
write, and a heading that arrives as ``## Title`` is a heading the outline, the
headings list and heading navigation all still find. The document's language is
pinned to Markdown as part of the switch, so the Format cell says what the
buffer actually holds.

Plain to rich converts only what is *known* to be markup -- a Markdown document,
or an HTML one through Markdown on the way. A plain ``.txt`` is left as
characters, because interpreting the asterisks in a shopping list as bold is
inventing formatting the person never asked for, and there is no way back from
it. That asymmetry is the honest one: markup can always be read as text, but
text cannot be assumed to be markup.
"""

from __future__ import annotations

import wx

from quill.core.html_to_markdown import contains_html_markup, html_to_markdown
from quill.core.lite import APP_NAME
from quill.core.lite.filetypes import is_rich_path, save_suffix_for_language
from quill.io.rtf import markdown_to_rtf, rtf_to_markdown
from quill.io.rtf_model import scan_rtf_features
from quill.ui.dialog_contract import show_message_box
from quill.ui.richedit_editing import PLAIN, RICH
from quill.ui.richedit_rtf_surface import RichEditRtfError

__all__ = ["DocumentModeMixin"]

#: The suffix a document takes when it changes mode, so Save can propose a name
#: rather than writing RTF bytes into a ``.txt``. Markdown rather than ``.txt``
#: for the plain direction, because that is what the conversion produces.
_SUFFIX_FOR_MODE = {RICH: ".rtf", PLAIN: ".md"}


class DocumentModeMixin:
    """Plain to rich and back, converting rather than flattening."""

    #: Set when a mode switch has made the current name wrong for what the
    #: buffer now holds. The next plain Save routes through Save As with the
    #: renamed file proposed; an explicit target clears it.
    _pending_suffix: str = ""

    def switch_mode(self, mode: str) -> None:
        """Move this document between plain and rich, converting what it holds.

        The order matters and is the same order the save path learned in F1:
        work out the new text **first**, ask about anything that will not
        survive, and only then touch the window. A cancelled warning leaves the
        document exactly as it was, in the mode it was already in.
        """
        if mode == self.editor.mode:
            return
        if mode == RICH and not self.editor.rtf_available():
            self._announce("Rich text needs the Windows Rich Edit control")
            return

        converted = self._plan_mode_switch(mode)
        if converted is None:
            return
        text, rtf = converted

        caret = self.control.GetInsertionPoint()
        self._loading = True
        try:
            self._set_mode_internal(mode)
            if rtf is not None:
                try:
                    self.editor.set_rtf(rtf.encode("utf-8", errors="replace"))
                except RichEditRtfError:
                    # The conversion is a better document than the characters,
                    # but a control that refuses the RTF is not a reason to lose
                    # the text. Fall back to what the buffer held.
                    self.control.ChangeValue(text)
            else:
                self.control.ChangeValue(text)
            self.doc_text.invalidate()  # neither route raises a text event
            self._apply_rich_theme_colour()
        finally:
            self._loading = False
        self.control.SetInsertionPoint(min(caret, len(self.control.GetValue())))

        if mode == PLAIN:
            # The buffer holds Markdown now, whatever the file is called, so the
            # Format cell and the heading commands have to be told.
            # announce=False: the mode switch already speaks, and two
            # sentences for one key is exactly what GATE-13 is about.
            self.set_document_language("markdown", announce=False)
        self._retarget_after_mode_switch(mode)
        # Rich text dims every markup row and plain text lights the ones the
        # language supports, and neither is the language change above: going
        # *to* rich never touches the override, so nothing else would tell the
        # menu that Promote Heading has just stopped meaning anything.
        self._sync_menu_rows()
        self._set_modified(True)
        self.reset_structure_announcer()
        self.sync_structure_announcer()
        self._announce("Rich text mode" if mode == RICH else "Plain text mode")

    # ------------------------------------------------------------------ #
    # Planning: everything that can refuse, before anything changes
    # ------------------------------------------------------------------ #

    def _plan_mode_switch(self, mode: str) -> tuple[str, str | None] | None:
        """``(plain text, RTF or None)`` for the new mode, or ``None`` to abandon.

        ``None`` is returned only when the user declined a warning. Everything
        else -- a control that will not give up its RTF, a conversion that
        produces nothing -- falls back to the characters, because losing the
        formatting is bad and losing the words is unthinkable.
        """
        if mode == PLAIN:
            return self._plan_rich_to_plain()
        return self._plan_plain_to_rich()

    def _plan_rich_to_plain(self) -> tuple[str, str | None] | None:
        """Markdown for the rich document, after warning about what it cannot hold."""
        rtf = self._current_rtf()
        if rtf is None:
            # No native surface to ask. The old behaviour, and still the only
            # answer available: the characters, with the warning that says so.
            if not self._confirm_plain_switch(
                "Switching to plain text removes all formatting. Continue?"
            ):
                return None
            return self.control.GetValue(), None

        features = scan_rtf_features(rtf)
        if features:
            inventory = ", ".join(features)
            message = (
                f"Switching to plain text cannot carry: {inventory}.\n\n"
                "Headings, bold, italic and lists become Markdown. Continue?"
            )
        else:
            message = (
                "Switching to plain text turns the formatting into Markdown: "
                "headings become #, bold becomes **bold**, lists become - lines.\n\n"
                "Continue?"
            )
        if not self._confirm_plain_switch(message):
            return None

        markdown = rtf_to_markdown(rtf)
        if not markdown.strip():
            # Converting to nothing is not a conversion; the same rule the Save
            # As Markdown row follows.
            return self.control.GetValue(), None
        return markdown, None

    def _plan_plain_to_rich(self) -> tuple[str, str | None] | None:
        """RTF for the plain document, when the plain document is known markup."""
        text = self.control.GetValue()
        language = self.document_language()
        if language == "html" and contains_html_markup(text):
            markdown = html_to_markdown(text)
            if not markdown.strip():
                return text, None
        elif language in {"markdown", "html"}:
            # Including a document merely *labelled* HTML. Ringing Alt+Shift+F
            # from Markdown to HTML changes the label and not one character of
            # the buffer, so the text arriving here is still Markdown -- and
            # html_to_markdown is an HTML parser, in which newlines are
            # insignificant whitespace. It used to run anyway, and the round
            # trip came back as a single enormous line with the ``#`` markers
            # still in it, which markdown_to_rtf then read as one heading and
            # the way home wrapped in ``**``. Reported after "a couple of loops
            # around" the ring. Markdown is what the buffer holds; convert it
            # as Markdown.
            markdown = text
        else:
            # A .txt is characters, not markup. See the module docstring.
            return text, None
        return text, markdown_to_rtf(markdown)

    def _current_rtf(self) -> str | None:
        """The rich document as an RTF string, or ``None`` when it cannot be had."""
        if not self.editor.rtf_available():
            return None
        try:
            return bytes(self.editor.get_rtf()).decode("utf-8", errors="replace")
        except RichEditRtfError:
            return None

    def _confirm_plain_switch(self, message: str) -> bool:
        return (
            show_message_box(
                message,
                APP_NAME,
                # NO_DEFAULT: Enter must not be the key that rewrites a document.
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self,
            )
            == wx.YES
        )

    # ------------------------------------------------------------------ #
    # The name
    # ------------------------------------------------------------------ #

    def _retarget_after_mode_switch(self, mode: str) -> None:
        """Keep the name, and make the next Save propose the right one.

        This used to set ``self.path = None``: a rich document cannot be written
        over a ``.txt``, so the window forgot what it was editing. That is safe
        and unhelpful -- the person still has a file open, still knows which one,
        and now Ctrl+S asks them to find it again with nothing proposed.

        QUILL's answer is better and is what this takes (``_retarget_format_suffix``
        in ``main_frame_rich_mode``): the name is kept, and a *pending suffix*
        makes the next plain Save route through Save As with the renamed file
        already filled in. Save proposes; it never rewrites.
        """
        if self.path is None:
            self._pending_suffix = ""
            return
        if is_rich_path(self.path.name) == (mode == RICH):
            self._pending_suffix = ""
            return
        self._pending_suffix = _SUFFIX_FOR_MODE[mode]

    def proposed_name_for_mode(self) -> str:
        """The file name Save As should offer, honouring a pending mode switch.

        An untitled document is offered under the extension of the language it
        has been *told* it is, not always ``.txt``: somebody who rang
        Ctrl+Shift+M round to Markdown and then pressed Ctrl+S was offered a
        text file, which is the app forgetting the one thing it had just been
        told about the document.
        """
        if self.path is None:
            if self.editor.mode == RICH:
                return "Untitled.rtf"
            return "Untitled" + save_suffix_for_language(self.document_language())
        if not self._pending_suffix:
            return self.path.name
        return self.path.with_suffix(self._pending_suffix).name
