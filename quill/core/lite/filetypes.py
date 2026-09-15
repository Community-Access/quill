"""Which files QuillLite offers, and which of them are rich text.

Two decisions live here, in one wx-free place so the Open dialog, the Save As
dialog, the drag-and-drop path and the mode-switching logic cannot disagree
about them.

**What counts as rich text is the extension, and only ``.rtf``.** Not a sniff of
the first bytes, and not a preference: a file named ``.rtf`` opens in rich mode
and everything else opens as text. That is what Notepad and WordPad do, it is
what the user's file manager already told them, and a rule you can predict from
the name is worth more here than a rule that is right slightly more often.

**What counts as Markdown is the extension too, and `.txt` is not one of them.**
Same argument, one line down: plain text stays plain. See
:func:`markup_language_for`.

**A text editor should open text.** The "all supported files" filter therefore
covers the extensions people actually keep prose, notes and configuration in,
rather than only ``.txt`` -- opening a ``.md`` or a ``.log`` should not require
finding the All Files filter first.

**A third decision joined them: which markup a plain document is written in.**
:func:`markup_language_for` answers ``"markdown"``, ``"html"`` or ``"plain"``
from the name, and that one answer decides four things at once -- what Ctrl+B
inserts, what the heading keys write, which of the two tag pickers is offered
and which is greyed out, and whether the caret cue can say "Bulleted list, 5
items". Deriving all four from one function is the point: a document where bold
inserted ``**`` and the heading key wrote ``<h2>`` would be a document nobody
could trust, and four separate rules is exactly how that happens.

The language is a *default*, not a verdict. Somebody writing HTML in a
``.txt`` scratch file is doing something entirely reasonable, so the window
keeps an override (Format > Document Language, or Enter on the status bar's
Language cell) and every one of the four consumers reads the override first.
"""

from __future__ import annotations

__all__ = [
    "HTML_SUFFIXES",
    "LANGUAGE_CHOICES",
    "LANGUAGE_LABELS",
    "MARKDOWN_HEADING_SUFFIXES",
    "MARKDOWN_SUFFIXES",
    "OPEN_WILDCARD",
    "RICH_SUFFIXES",
    "SAVE_WILDCARD_PLAIN",
    "SAVE_WILDCARD_RICH",
    "has_markdown_headings",
    "is_rich_path",
    "language_label",
    "markup_language_for",
]

#: The one extension that means rich text.
RICH_SUFFIXES = frozenset({".rtf"})

#: The extensions the "all supported files" filter offers, as one wx pattern.
_TEXT_LIKE = "*.txt;*.rtf;*.md;*.log;*.csv;*.json;*.py;*.html;*.htm"

OPEN_WILDCARD = (
    f"All supported files ({_TEXT_LIKE})|{_TEXT_LIKE}|"
    "Text files (*.txt)|*.txt|"
    "Rich Text (*.rtf)|*.rtf|"
    "Markdown (*.md;*.markdown)|*.md;*.markdown|"
    "HTML (*.html;*.htm)|*.html;*.htm|"
    "All files (*.*)|*.*"
)

#: Save As offers the document's own kind first, so Enter does the obvious thing.
#:
#: **Markdown is back (2026-09-15), and only because it now converts.** The row
#: was removed on the argument that a "type" in a Save As box is a promise about
#: what will be written, and picking Markdown wrote the same plain text under a
#: different extension -- a promise the app could not keep. That argument was
#: right, and the answer to it is the writer, not the missing row: saving an
#: **HTML** document as ``.md`` now runs it through
#: :func:`quill.core.html_to_markdown.html_to_markdown`, so the tags really do
#: become Markdown. Saving a plain or Markdown document as ``.md`` writes the
#: text unchanged, which is the honest answer for those: plain text is already
#: what it is, and Markdown is already Markdown.
#:
#: Still **not** in :data:`SAVE_WILDCARD_RICH`. Rich text to Markdown would mean
#: reading formatting back out of the native control and guessing which runs
#: were meant as headings -- a different feature, and a worse one to get wrong.
#: Flatten to plain text first (the Save As dialog already asks) and the
#: Markdown row is there.
SAVE_WILDCARD_PLAIN = (
    "Text files (*.txt)|*.txt|Markdown (*.md)|*.md|Rich Text (*.rtf)|*.rtf|All files (*.*)|*.*"
)
SAVE_WILDCARD_RICH = "Rich Text (*.rtf)|*.rtf|Text files (*.txt)|*.txt|All files (*.*)|*.*"


def is_rich_path(name: str) -> bool:
    """True when a file of this name should be opened (or saved) as rich text."""
    lowered = str(name).lower()
    return any(lowered.endswith(suffix) for suffix in RICH_SUFFIXES)


#: Names for the markup a plain document is written in. ``"plain"`` is a real
#: answer and not a failure: a shopping list in a ``.txt`` has no markup, and
#: pretending otherwise is what makes an editor put ``**`` round a word somebody
#: only wanted emphasised in their own head.
LANGUAGE_CHOICES: tuple[str, ...] = ("plain", "markdown", "html")

#: How each is named on screen -- in the Language cell, in the chooser, and in
#: every spoken confirmation. One table, so the app cannot call HTML two things.
LANGUAGE_LABELS: dict[str, str] = {
    "plain": "Plain text",
    "markdown": "Markdown",
    "html": "HTML",
}

#: Files whose markup is Markdown, and **only** these: a file is Markdown when
#: its name says Markdown.
#:
#: ``.txt`` is deliberately **not** here, and that is the whole rule: *plain text
#: stays plain*. It was here briefly, on the argument that a plain text file is
#: where somebody writes prose with ``#`` headings -- which is true of some
#: ``.txt`` files and false of most, and being wrong about it is expensive in
#: both directions. Ctrl+B silently writing ``**`` into a plain note is a change
#: nobody asked for and nobody can see; "Heading 1" announced over a line
#: beginning ``#`` in a log is a sentence on every one of them. A rule you can
#: predict from the extension is worth more than a rule that is right slightly
#: more often -- the same argument :data:`RICH_SUFFIXES` makes one line up.
#:
#: Somebody who *is* writing Markdown in a ``.txt`` says so in one keystroke:
#: **Ctrl+Shift+M** rings on to Markdown, or **Ctrl+Alt+F6** goes straight to it.
MARKDOWN_SUFFIXES = frozenset({".md", ".markdown", ".mdown", ".mkd", ".mdx"})

#: Files whose markup is HTML. ``.xhtml`` counts: the tags are the same tags,
#: and refusing the tag picker on one would be a distinction without a
#: difference to the person typing into it.
HTML_SUFFIXES = frozenset({".html", ".htm", ".xhtml", ".xht"})


def markup_language_for(name: str | None) -> str:
    """The markup a document of this name is written in.

    ``"markdown"``, ``"html"`` or ``"plain"``, from the extension and nothing
    else. Not from the content: a rule you can predict from the file's name is
    worth more than a rule that is right slightly more often, and a document
    whose Ctrl+B changed meaning as you typed into it would be unusable.

    An untitled buffer is ``"plain"``, and a ``.txt`` is ``"plain"``, and a
    ``.py``, ``.ini``, ``.yml`` or ``.sh`` is emphatically ``"plain"``. **Plain
    text stays plain.** Those are the files a Notepad replacement opens all day;
    a ``#`` in them is a comment, a ``-`` is a flag, and every consumer of this
    function is quieter and duller in one, which is exactly right.

    Nothing is lost by it. A person writing Markdown says so in one keystroke --
    Ctrl+Shift+M or Ctrl+Alt+F6 -- and saving the file as ``.md`` says it
    permanently. What *would* be lost by guessing is the thing nobody can see:
    two asterisks written into a note, or a "Heading 1" spoken over every line
    of a log.
    """
    lowered = str(name or "").lower()
    if any(lowered.endswith(suffix) for suffix in HTML_SUFFIXES):
        return "html"
    if any(lowered.endswith(suffix) for suffix in MARKDOWN_SUFFIXES):
        return "markdown"
    return "plain"


def language_label(language: str) -> str:
    """``"HTML"`` -- how a language is named on screen and aloud."""
    return LANGUAGE_LABELS.get(str(language), "Plain text")


#: The plain-text documents whose ``#`` lines are headings rather than comments.
#:
#: This distinction is load-bearing and easy to miss. QuillLite is a Notepad
#: replacement, so people open ``.py``, ``.sh``, ``.ini``, ``.yml`` and ``.conf``
#: files in it constantly -- and in every one of those a line beginning ``#`` is
#: a **comment**. Treating it as a heading would make the caret cue say
#: "Heading 1" on most lines of a shell script, and would fill the headings list
#: with comments.
#:
#: ``.txt`` is in the list because a plain text file is where somebody writes
#: prose with Markdown-ish headings and nothing conventionally starts a line
#: with ``#``. An untitled document counts too: a buffer somebody is typing
#: ``## Notes`` into has no extension to go on, and the person doing it means a
#: heading. Anything else -- any extension not listed -- has no headings, which
#: is the safe answer because the cost of a false positive is heard on every
#: line and the cost of a false negative is one silent key.
MARKDOWN_HEADING_SUFFIXES = MARKDOWN_SUFFIXES


def has_markdown_headings(name: str | None) -> bool:
    """True when ``#`` at the start of a line means a heading in this document.

    A thin spelling of :func:`markup_language_for` now that the language is a
    first-class answer, and kept because "does ``#`` mean a heading here" is
    still the question several call sites are actually asking. The two cannot
    drift: there is one rule underneath, and it is the file's name.
    """
    return markup_language_for(name) == "markdown"
