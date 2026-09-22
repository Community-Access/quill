"""Markup in a plain document: what Bold writes, and which picker is offered.

QuillLite has always had two kinds of document -- plain and rich -- and one of
them could not be formatted at all. Ctrl+B in a ``.md`` said "Not available in
plain text. Press Alt Shift F to switch to rich text", which is a true
sentence and an unhelpful one: somebody writing Markdown does not want rich
text, they want two asterisks, and they know it. The key was bound, the feature
existed one product over, and the answer was to go and be in a different kind of
document.

So a plain document now has a **language**, and the language decides what the
formatting keys write:

============ ================== ===================== ========================
Language     Ctrl+B writes      Ctrl+Alt+2 writes     Tag picker offered
============ ================== ===================== ========================
Markdown     ``**bold**``       ``## Heading``        Insert Markdown Tag
HTML         ``<strong>``       ``<h2>Heading</h2>``  Insert HTML Tag
Plain text   nothing, and says  nothing, and says     neither; both greyed
============ ================== ===================== ========================

One rule underneath (:func:`~quill.core.lite.filetypes.markup_language_for`),
so the four consumers cannot disagree -- a document where Ctrl+B wrote ``**``
and the heading key wrote ``<h2>`` would be a document nobody could trust.

And the rule is **the file's name, not its contents**. A ``.md`` is Markdown, a
``.html`` is HTML, and everything else -- a ``.txt``, a ``.py``, a ``.conf``, an
untitled buffer -- is plain, where all four of those consumers stay quiet.
Guessing from the text was considered and rejected: the cost of being wrong is
invisible in one direction (two asterisks written into a plain note) and
relentless in the other ("Heading 1" spoken over every ``#`` in a log).

**The greying-out is the feature, not the polish.** A menu item that is present
and does nothing is indistinguishable, by ear, from one that is present and
broken; a *disabled* one announces itself as unavailable the moment a reader
touches it, which answers the question before it is asked. That is why Insert
HTML Tag is dimmed in a ``.md`` rather than quietly inserting Markdown instead,
and why the keys say why rather than doing nothing.

**And the language is a default, never a verdict.** Writing HTML in a ``.txt``
scratch file is an entirely reasonable thing to do, so the window keeps an
override, reachable three ways, and every consumer reads it before the file
name:

* **Ctrl+Shift+M** rings through all four kinds of document -- plain, Markdown,
  HTML, rich -- which is the fast way when you do not mind hearing the ones in
  between. See :data:`DOCUMENT_KINDS`.
* **Ctrl+Alt+F6** (Format > Document Language) goes straight to one, and says
  what each choice will do before it is made.
* **Enter on the status bar's Language cell** opens that same chooser, because
  the bar is where somebody notices the answer is wrong, and making them leave
  it to fix it would be a menu hunt for a one-word change.

The override lasts as long as the window. It describes what you are typing
rather than what the file is, and a preference that outlived the document would
be wrong more often than right.
"""

from __future__ import annotations

from typing import Any

from quill.apps.lite_dialogs import choose_document_language, choose_searchable
from quill.apps.lite_dialogs_entry import ask_link, ask_text
from quill.core.heading_levels import LevelResult, set_heading_level
from quill.core.html_forms import is_form_snippet
from quill.core.links import build_link_text
from quill.core.lite.filetypes import language_label, markup_language_for
from quill.core.lite.keymap import spoken_key_for
from quill.core.tagging import (
    MARKDOWN_TAG_CHOICES,
    InsertionResult,
    build_html_insertion,
    build_markdown_insertion,
    html_insert_choices,
    parse_attribute_pairs,
    search_html_tag_choices,
    search_markdown_tag_choices,
)
from quill.ui.atomic_edit import replace_as_one_undo
from quill.ui.richedit_editing import PLAIN, RICH

__all__ = ["DOCUMENT_KINDS", "DocumentMarkupMixin", "MARKUP_COMMANDS"]

#: The ring Ctrl+Shift+M walks, in order, and what each stop is called.
#:
#: Four kinds of document, not two. The key has always meant "this document is
#: the wrong kind, make it the other one", and once a plain document has a
#: language there are four kinds rather than two -- so the key rings through all
#: four instead of skipping past three of them. It is the fastest way to answer
#: "what *is* this?", which is a question you can ask by eye in a second and
#: otherwise cannot ask at all.
#:
#: The order is deliberate: the three free stops first, then the one that costs
#: something. Moving between plain, Markdown and HTML changes nothing on disk or
#: in the buffer -- it changes what the *keys* write -- so the ring can be walked
#: as fast as you like. Rich text is a real conversion, which is why it is last
#: and why leaving it asks first (see ``switch_mode``).
DOCUMENT_KINDS: tuple[tuple[str, str], ...] = (
    ("plain", "plain"),
    ("plain", "markdown"),
    ("plain", "html"),
    ("rich", ""),
)

#: The HTML tag for each run-level attribute the Format menu toggles.
#:
#: ``<strong>`` and ``<em>`` rather than ``<b>`` and ``<i>``, because the two
#: pairs are not synonyms to the thing that reads them out: ``<strong>`` carries
#: importance into the accessibility tree and ``<b>`` carries only a typeface.
#: An editor built for listeners that emitted the presentational pair would be
#: making every document it wrote slightly less accessible than it had to be.
#: ``<u>`` has no semantic sibling and stays as it is.
_HTML_RUN_TAGS = {"Bold": "strong", "Italic": "em", "Underline": "u"}

#: The Markdown insertion kind for the same three. Underline is ``<u>`` even in
#: Markdown -- there is no native syntax for it, and inline HTML is what every
#: renderer that supports raw HTML will honour.
_MARKDOWN_RUN_KINDS = {"Bold": "Bold", "Italic": "Italic", "Underline": "Underline"}

#: Handlers the menu builder must grey out when the document's language cannot
#: support them. Read by :meth:`DocumentMenuMixin._sync_enabled_items`, which
#: runs every time a menu opens, so the state is never stale.
MARKUP_COMMANDS: dict[str, tuple[str, ...]] = {
    "cmd_insert_markdown_tag": ("markdown",),
    "cmd_insert_html_tag": ("html",),
}


class DocumentMarkupMixin:
    """The document's markup language, and the two things it decides.

    Mixed into :class:`~quill.apps.lite_window.DocumentFrame`, which supplies
    ``control``, ``editor``, ``path``, ``app``, ``_announce``, ``_set_modified``
    and ``_touch_status``.
    """

    control: Any
    editor: Any
    app: Any
    _announce: Any

    #: The user's override, or ``""`` to follow the file name.
    _language_override: str = ""

    # -- the language ------------------------------------------------------- #

    def document_language(self) -> str:
        """``"markdown"``, ``"html"`` or ``"plain"`` for this document."""
        override = getattr(self, "_language_override", "")
        if override:
            return override
        path = getattr(self, "path", None)
        return markup_language_for(path.name if path is not None else None)

    def default_document_language(self) -> str:
        """What the file name alone says, ignoring any override.

        Shown in the chooser as "(from the file name)" so the override can be
        recognised as an override -- and so returning to it is a choice somebody
        can find rather than a state they have to restart the window to reach.
        """
        path = getattr(self, "path", None)
        return markup_language_for(path.name if path is not None else None)

    def document_kind_label(self) -> str:
        """ "Markdown", "HTML", "Plain text" or "Rich text" -- all four kinds.

        The status bar's Format cell reads this. It used to read "Plain text" or
        "Rich text" and nothing else, which meant ringing Ctrl+Shift+M from plain
        to Markdown to HTML changed the document's behaviour three times and
        changed the cell not at all -- the one place somebody would look to check
        what had just happened. A cell that cannot see two thirds of the states
        its own Enter key produces is worse than no cell.
        """
        if self.editor.mode == RICH:
            return "Rich text"
        return language_label(self.document_language())

    def markup_surface(self) -> str | None:
        """The markup insertions should use, or ``None`` when there is none.

        ``None`` in a rich document as well as a plain-language one: rich text
        has real bold, and inserting ``**`` into it would put two asterisks on
        the page next to a word that is already bold.
        """
        if self.editor.mode == RICH:
            return None
        language = self.document_language()
        return language if language in {"markdown", "html"} else None

    def set_document_language(self, language: str, *, announce: bool = True) -> None:
        """Adopt *language* for this window, and tell everything that cares."""
        self._language_override = language if language in {"markdown", "html", "plain"} else ""
        # The two pickers change availability, the caret cue changes what it can
        # see, and the status bar has a cell for it. All three, or the window
        # disagrees with itself until the next keystroke.
        self.reset_structure_announcer()
        self.sync_structure_announcer()
        self._touch_status()
        if announce:
            self._announce(f"Document language: {language_label(self.document_language())}")

    def plan_markdown_conversion(self, target: Any) -> str | None:
        """The Markdown to write when Save As asks for ``.md``, or ``None``.

        ``None`` means "write the buffer as it stands", which covers three
        cases: the target is not a ``.md``, the document is not HTML (a plain or
        Markdown document saved as ``.md`` is already what it claims to be, and
        running either through the converter would be a round trip that can only
        lose something), or the HTML converts to nothing -- and saving the HTML
        unchanged under a ``.md`` name is the silent-wrong-file case the
        Markdown row was removed for in the first place.

        **Planned, not applied.** It used to ``ChangeValue`` the buffer here and
        then let the caller try the write. If the write failed -- a locked file,
        a full disk -- the window was left holding flattened Markdown under the
        old ``.html`` name, with ``self.path`` still pointing at it, so the next
        Ctrl+S wrote it over the original. And ``ChangeValue`` is off the undo
        stack, so the HTML was gone from the window too (bad.md F1).
        """
        if markup_language_for(getattr(target, "name", "")) != "markdown":
            return None
        if self.editor.mode == RICH or self.document_language() != "html":
            return None

        from quill.core.html_to_markdown import html_to_markdown

        markdown = html_to_markdown(self.control.GetValue())
        return markdown if markdown.strip() else None

    def apply_markdown_conversion(self, markdown: str) -> None:
        """Put the converted Markdown in the window. **After** a successful write.

        Said out loud, because the buffer changes under the caret and a screen
        reader announces nothing about a document being rewritten. Not asked
        about: choosing Markdown in a Save As type list *is* the consent, and a
        confirmation on a conversion somebody just asked for by name is the tax
        that gets a feature left unused.
        """
        self._loading = True
        try:
            self.control.ChangeValue(markdown)
            self.doc_text.invalidate()  # ChangeValue raises no text event
        finally:
            self._loading = False
        # The override, not the language: the file is now a .md, so the NAME
        # should decide from here on. Leaving "html" pinned would show a
        # Markdown file whose Format cell said HTML.
        self._language_override = ""
        self.reset_structure_announcer()
        self.sync_structure_announcer()
        self._touch_status()
        self._announce("Converted HTML to Markdown")

    def cmd_switch_document_kind(self) -> None:
        """Ctrl+Shift+M: ring on to the next kind of document.

        Plain text, then Markdown, then HTML, then rich text, then round again.
        Each stop announces itself, which is the whole point of a ring rather
        than four separate keys: you press it until you hear the one you wanted,
        the way anybody sighted would click through a Format dropdown.

        The rich stop is the only one that changes the document, and
        :meth:`~quill.apps.lite_window_mode.DocumentModeMixin.switch_mode`
        owns that -- including the confirmation for leaving it, which is a
        conversion that rewrites the buffer and must never be one keypress deep.
        If that confirmation is declined the ring stops where it was rather than
        skipping the stop, because a key that quietly moved you somewhere else
        after you said no is worse than one that did nothing.

        **Leaving rich lands on Markdown, not on plain text**, which is the ring
        skipping a stop for the one reason worth skipping one for: the
        conversion produces Markdown. Ringing on to "Plain text" and clearing
        the language would leave a buffer full of ``##`` and ``**`` being called
        text that has no markup in it -- the Format cell lying about the very
        thing it exists to report. One more press reaches plain text, and then
        it is true.
        """
        current = ("rich", "") if self.editor.mode == RICH else ("plain", self.document_language())
        try:
            position = DOCUMENT_KINDS.index(current)
        except ValueError:  # an override the ring does not list; start it over
            position = -1
        mode, language = DOCUMENT_KINDS[(position + 1) % len(DOCUMENT_KINDS)]
        if mode == "rich":
            self.switch_mode(RICH)
            return
        if self.editor.mode == RICH:
            self.switch_mode(PLAIN)
            if self.editor.mode == RICH:
                return  # the conversion was declined; stay where we are
            # Markdown, not the ring's next stop: see the docstring. The ring
            # decides where it lands, here, rather than inheriting whatever
            # switch_mode happened to leave the override on.
            language = "markdown"
        self.set_document_language(language)

    def cmd_set_language(self) -> None:
        """Ctrl+Alt+F6 / the status bar's Language cell: choose the markup."""
        chosen = choose_document_language(
            self,
            current=self.document_language(),
            default_label=self.default_document_language(),
        )
        if chosen is None:
            self.control.SetFocus()
            return
        self.set_document_language(chosen)
        self.control.SetFocus()

    # -- what the language decides ------------------------------------------ #

    def apply_markup_run(self, attribute: str) -> bool:
        """Write *attribute* as markup around the selection. ``False`` if it cannot.

        ``False`` rather than a refusal message, because the caller
        (:class:`~quill.apps.lite_window_format.DocumentFormatCommandsMixin`)
        already owns a better one: it knows whether the honest answer is "switch
        to rich text" or "this document has no markup", and those are two
        different pieces of advice.
        """
        surface = self.markup_surface()
        if surface is None:
            return False
        selected = self.control.GetStringSelection()
        if surface == "markdown":
            result = build_markdown_insertion(_MARKDOWN_RUN_KINDS[attribute], selected)
        else:
            result = build_html_insertion(_HTML_RUN_TAGS[attribute], selected, {})
        self._apply_insertion(result)
        # The wording names the *markup*, not the effect. "Bold on" is what the
        # rich path says and would be a small lie here: nothing on this screen
        # went bold, two asterisks appeared. Somebody who cannot see them needs
        # to be told which of the two things just happened.
        self._announce(f"{attribute} in {language_label(surface)}")
        return True

    def apply_markup_heading(self, level: int) -> bool:
        """Make the caret's line a heading of *level* in markup. ``False`` if not.

        Absolute, and it rewrites: applying Heading 2 to a line that is already
        ``### Notes`` gives ``## Notes``, never ``## ### Notes``. See
        :func:`~quill.core.heading_levels.set_heading_level` -- the reason that
        rewrite lives in core is that nothing on screen tells a listener which
        of the two happened.
        """
        surface = self.markup_surface()
        if surface is None:
            return False
        text = self.control.GetValue()
        caret = int(self.control.GetInsertionPoint())
        change = set_heading_level(text, caret, level, markup_kind=surface)
        if change.result is LevelResult.NOT_A_HEADING:
            self._announce("Already body text")
            return True
        if change.result is not LevelResult.OK:
            return False
        replace_as_one_undo(self.control, change.start, change.end, change.replacement)
        # Hold the caret's place *in the line*, which has just grown or shrunk in
        # front of it by however many hashes or tag characters changed.
        moved = len(change.replacement) - (change.end - change.start)
        self.control.SetInsertionPoint(max(change.start, min(caret + moved, len(text) + moved)))
        self._set_modified(True)
        self._touch_status()
        self._announce(f"Heading {level}" if level else "Body text")
        self.sync_structure_announcer()
        return True

    # -- the pickers --------------------------------------------------------- #

    def cmd_insert_markdown_tag(self) -> None:
        """Insert > Markdown Tag: the whole Markdown vocabulary, searchable."""
        if not self._require_language("markdown", "Insert Markdown Tag"):
            return
        kind = choose_searchable(
            self,
            title="Insert Markdown Tag",
            label="&Markdown tags and snippets:",
            help_text=(
                "Choose one and press Enter. Anything selected in the document "
                "is wrapped; with nothing selected the markup goes in empty with "
                "the cursor in the middle of it, ready to type."
            ),
            choices=list(MARKDOWN_TAG_CHOICES),
            search=search_markdown_tag_choices,
            examples="try heading, link, table",
        )
        if kind is None:
            self.control.SetFocus()
            return
        target = ""
        if kind in {"Link", "Image"}:
            target = (
                ask_text(
                    self,
                    title=f"Insert {kind}",
                    label="&Address:",
                    help_text=(
                        "Where the link points. Leave it as it is to put a "
                        "placeholder in and fill it in later."
                    ),
                    value="https://",
                )
                or ""
            ).strip()
        selected = self.control.GetStringSelection()
        self._apply_insertion(build_markdown_insertion(kind, selected, link_target=target))
        self._announce(f"Inserted {kind}")
        self.control.SetFocus()

    def cmd_insert_html_tag(self) -> None:
        """Insert > HTML Tag: the tag, then its attributes, then the caret inside.

        Two steps rather than one box of syntax, because the second step is the
        one people get wrong and the one nothing can check for them. The
        attribute box is *optional* and Enter alone skips it -- an ``<h2>`` needs
        nothing, and making everybody pass through an empty field to reach the
        common case is the sort of tax that gets a feature left unused.
        """
        if not self._require_language("html", "Insert HTML Tag"):
            return
        tag = choose_searchable(
            self,
            title="Insert HTML Tag",
            label="&HTML tags and form fields:",
            help_text=(
                "Choose one and press Enter. Search by what it does as well as "
                "by its name -- dropdown finds select, checkbox finds input, "
                "collapsible finds details. The Form field rows at the top put "
                "in a whole labelled control at once, with the label joined to "
                "the field so a screen reader reads them together. Anything "
                "selected in the document becomes the label, or is wrapped by "
                "the tag."
            ),
            choices=html_insert_choices(),
            search=search_html_tag_choices,
            examples="try heading, dropdown, radio group",
        )
        if tag is None:
            self.control.SetFocus()
            return
        raw = ""
        if not is_form_snippet(tag):
            # A whole form control arrives with the attributes that make it
            # work -- for, id, name, type -- so asking for more would be asking
            # somebody to add to a thing they have not seen yet. A bare tag is
            # the opposite: it arrives with none.
            answer = ask_text(
                self,
                title="Insert HTML Tag",
                label="&Optional attributes:",
                help_text=(
                    "Separate them with semicolons, for example: "
                    "class=note; id=summary; aria-label=Summary. "
                    "Leave it empty and press Enter if the tag needs none."
                ),
            )
            if answer is None:
                self.control.SetFocus()
                return
            raw = answer
        selected = self.control.GetStringSelection()
        self._apply_insertion(
            build_html_insertion(
                tag,
                selected,
                parse_attribute_pairs(raw),
                # The whole buffer, so a generated id cannot collide with one
                # already in the document.
                self.control.GetValue(),
            )
        )
        self._announce(f"Inserted {tag}" if is_form_snippet(tag) else f"Inserted HTML tag {tag}")
        self.control.SetFocus()

    def cmd_insert_link(self) -> None:
        """Ctrl+K: a link, in whatever markup the document is written in.

        Word's key, and everybody's: a link is the one tag every person who has
        ever written anything has inserted. QuillLite had the kinds and the tag
        pickers and no way to make the one tag that matters (bad.md 4.2, Tier 1).

        Markdown and HTML only. Rich text says so -- a link in a rich document is
        a field the RichEdit control owns, and writing ``[text](url)`` into one
        would put the brackets on the page.
        """
        surface = self.markup_surface()
        if surface is None:
            keymap = getattr(self.app, "keymap", None)
            self._announce(
                "A link needs a Markdown or HTML document. Press "
                f"{spoken_key_for(keymap, 'cmd_set_language')} to set the language, or "
                f"{spoken_key_for(keymap, 'cmd_switch_document_kind')} to change the kind."
            )
            return
        answer = ask_link(self, text=self.control.GetStringSelection())
        if answer is None:
            self.control.SetFocus()
            return
        display, url = answer
        url = url.strip()
        if not url or url == "https://":
            self.control.SetFocus()
            self._announce("No address was given, so nothing was inserted")
            return
        snippet = build_link_text(surface, display, url)
        self._apply_insertion(InsertionResult(inserted_text=snippet, caret_offset=len(snippet)))
        self.control.SetFocus()
        self._announce(f"Inserted link to {url}")

    def cmd_insert_emoji(self) -> None:
        """Insert > Emoji: browse or search, with a description of what it looks like.

        QUILL's picker, imported rather than reimplemented
        (:mod:`quill.ui.main_frame_emoji_picker`) -- a browse-and-search list
        with a written description of every glyph, which is the opposite of the
        picture wall every other emoji picker is and the only shape of this
        feature a listener can use at all.

        Nothing about it is markup, so it is offered in every document including
        a rich one: an emoji is a character, and Windows' own Win+Period picker
        is no more reachable in a ``.md`` than anywhere else.
        """
        from quill.core import emoji_data
        from quill.ui.main_frame_emoji_picker import EmojiPickerDialog

        if not emoji_data.is_available():
            self._announce(
                "The emoji catalogue could not be loaded. You can still type emoji "
                "with the Windows key and full stop."
            )
            return
        chosen = EmojiPickerDialog(self, announce_cb=self._announce).show()
        if chosen is None:
            self.control.SetFocus()
            return
        self.control.WriteText(chosen.char)
        self._set_modified(True)
        # The name, because this is the one insertion whose result the reader
        # cannot describe: a bare emoji character is read as anything from its
        # own name to silence depending on the synthesiser and the voice.
        self._announce(f"Inserted {chosen.name}")
        self._touch_status()
        self.control.SetFocus()

    # -- shared plumbing ------------------------------------------------------ #

    def _require_language(self, wanted: str, what: str) -> bool:
        """True when this document is *wanted*; otherwise say why it is not.

        The menu row for this command is already dimmed, so reaching here means
        the key was pressed or the palette was used. Both deserve the same
        sentence the dimmed row would have given if a reader could ask it.
        """
        if self.editor.mode == RICH:
            self._announce(
                f"{what} works in plain text documents. Press "
                f"{spoken_key_for(getattr(self.app, 'keymap', None), 'cmd_switch_document_kind')}"
                " to switch this one "
                "to plain text."
            )
            return False
        current = self.document_language()
        if current == wanted:
            return True
        self._announce(
            f"{what} needs a {language_label(wanted)} document. "
            f"This one is {language_label(current)}. Press "
            f"{spoken_key_for(getattr(self.app, 'keymap', None), 'cmd_set_language')}"
            " to change the document language."
        )
        return False

    def _apply_insertion(self, result: InsertionResult) -> None:
        """Replace the selection with *result*, and put the caret where it says.

        The caret offset is the whole reason
        :class:`~quill.core.tagging.InsertionResult` carries one: inserting
        ``<strong></strong>`` with nothing selected has to leave the caret
        *between* the tags, because the alternative is a user who types their
        word after the closing tag and cannot see that they have.
        """
        start, end = self.control.GetSelection()
        replace_as_one_undo(self.control, start, end, result.inserted_text)
        self.control.SetInsertionPoint(start + int(result.caret_offset))
        self._set_modified(True)
        self._touch_status()
