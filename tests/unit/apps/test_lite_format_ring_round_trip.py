r"""Ringing Alt+Shift+F round the document kinds must not eat the document.

Reported: "If I have a markdown document and quickly switch between formats
with Alt+Shift+F we lose line endings/CRLF characters and the document becomes
like on one line." The text that came back after a couple of loops was:

    # **First Section This is the body text for the first section. ## Second
    Section ... # Third Section This is the body text for the third section.**

Every word survived and every line break did not, and the whole thing came home
bold underneath one heading marker. Three steps produced it, and only the first
is surprising:

1. The ring re-labels a Markdown buffer **HTML** without rewriting a character
   of it. That is the deliberate rule -- markup-to-markup switches keep the
   text, and QUILL's switcher says so in as many words ("the pin decides the
   tags") -- so the label describes how the *next* insertion is spelled, not
   what the buffer already holds.
2. The next stop, rich text, believed the label and ran the buffer through
   ``html_to_markdown``. That is an HTML parser, and HTML has no significant
   newlines: every blank line between paragraphs is whitespace to be collapsed.
   One line out.
3. ``markdown_to_rtf`` then read that one line as a single Heading 1 -- it does
   begin with ``# `` -- and a heading is bold, so the way home spelled the
   whole document ``**...**`` under one ``#``.

So the test is the loop, not the parser: put a real Markdown document in a
window, ring the whole way round more than once, and require the text to come
back. The conversions themselves were never broken (``markdown_to_rtf`` and
``rtf_to_markdown`` round-trip this document exactly); what was broken was
running the wrong one, which no test of either could see.
"""

from __future__ import annotations

import pytest
import wx

from quill.apps import lite_window_mode as modemod
from quill.core.html_to_markdown import contains_html_markup
from quill.ui.richedit_editing import RICH

DOCUMENT = (
    "# First Section\n"
    "\n"
    "This is the body text for the first section.\n"
    "\n"
    "## Second Section\n"
    "\n"
    "This is the body text for the second section. This is the section used to\n"
    "test heading promotion, demotion, and section movement.\n"
    "\n"
    "# Third Section\n"
    "\n"
    "This is the body text for the third section.\n"
)

#: The four headings and the sentences, in order. Compared instead of the exact
#: characters: a round trip through RTF may or may not keep a trailing newline
#: or a soft-wrapped line's break, and neither is what was reported. What was
#: reported is *structure* -- the blank lines and the heading markers -- so that
#: is what is asserted.
STRUCTURE = (
    ("#", "First Section"),
    ("##", "Second Section"),
    ("#", "Third Section"),
)


@pytest.fixture
def ring(lite_window, monkeypatch):
    """A Markdown document, with the leave-rich warning answered Yes.

    The warning is a real question about losing formatting and is tested
    elsewhere; answering it here is what lets the ring be ridden at all.
    """
    monkeypatch.setattr(modemod, "show_message_box", lambda *_a, **_k: wx.YES)
    window = lite_window(DOCUMENT)
    window.path = None
    window.set_document_language("markdown", announce=False)
    return window


def _headings(text: str) -> tuple[tuple[str, str], ...]:
    found = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            marker, _, title = stripped.partition(" ")
            found.append((marker, title.strip()))
    return tuple(found)


def test_the_document_is_markdown_to_begin_with(ring) -> None:
    # The premise. If this ever stops being true the loop below is testing
    # something else, and would keep passing while doing it.
    assert _headings(ring.control.GetValue()) == STRUCTURE
    assert not contains_html_markup(ring.control.GetValue())


def test_labelling_a_markdown_buffer_html_does_not_rewrite_it(ring) -> None:
    ring.cmd_switch_document_kind()
    assert ring.document_language() == "html"
    assert ring.control.GetValue() == DOCUMENT, (
        "the ring rewrote the buffer on a markup-to-markup switch; it is the "
        "label that changes, not the text"
    )


def test_one_loop_round_the_ring_keeps_every_line(ring) -> None:
    for _ in range(4):  # markdown -> html -> rich -> markdown -> html
        ring.cmd_switch_document_kind()
    text = ring.control.GetValue()
    assert "\n" in text, "the whole document came back as one line"
    assert _headings(text) == STRUCTURE
    assert "**" not in text, (
        "the document came home wrapped in bold: the one-line collapse was read "
        "back as a single heading"
    )


def test_two_loops_round_the_ring_keep_every_line(ring) -> None:
    # "After looping around a couple of times", which is how it was reported.
    # A second lap matters: the damage was cumulative, and a document already
    # flattened once has no blank lines left to lose the second time -- so a
    # one-lap test could be made to pass by something that only looked fixed.
    for _ in range(8):
        ring.cmd_switch_document_kind()
    text = ring.control.GetValue()
    assert _headings(text) == STRUCTURE
    assert "**" not in text
    for sentence in (
        "This is the body text for the first section.",
        "This is the body text for the second section.",
        "This is the body text for the third section.",
    ):
        assert sentence in text


def test_every_stop_on_the_ring_keeps_the_headings(ring) -> None:
    # Checked at each stop rather than only at the end, so a failure names the
    # step that lost the document instead of the lap.
    for step in range(9):
        ring.cmd_switch_document_kind()
        text = ring.control.GetValue()
        kind = "rich" if ring.editor.mode == RICH else ring.document_language()
        assert _headings(text) == STRUCTURE, f"step {step + 1} ({kind}) lost the headings"


def test_a_real_html_document_is_still_converted(lite_window, monkeypatch) -> None:
    """The guard narrows what is converted; it must not switch it off.

    A document that really is HTML still becomes Markdown on the way into rich
    text -- otherwise the fix for the flattening would have traded it for
    angle brackets showing up as literal text in a formatted document.
    """
    monkeypatch.setattr(modemod, "show_message_box", lambda *_a, **_k: wx.YES)
    window = lite_window("<h1>Title</h1>\n<p>Some body text.</p>\n")
    window.path = None
    window.set_document_language("html", announce=False)
    assert contains_html_markup(window.control.GetValue())
    window.switch_mode(RICH)
    assert window.editor.mode == RICH
    text = window.control.GetValue()
    assert "<h1>" not in text, "the HTML was carried into rich text as characters"
    assert "Title" in text
    assert "Some body text." in text


def test_a_markdown_document_labelled_html_saves_as_itself(ring, tmp_path) -> None:
    """Save As ``.md`` from a *labelled* HTML document writes the Markdown.

    The same wrong-parser bug with a worse ending: this one reaches the disk.
    ``plan_markdown_conversion`` flattened the buffer and the caller wrote the
    result under the name the user had just chosen.
    """
    ring.cmd_switch_document_kind()  # markdown -> html, label only
    assert ring.document_language() == "html"
    assert ring.plan_markdown_conversion(tmp_path / "notes.md") is None, (
        "there is no HTML in this document to convert; the buffer is what should be written"
    )
    assert ring.save(tmp_path / "notes.md") is True
    assert _headings((tmp_path / "notes.md").read_text(encoding="utf-8")) == STRUCTURE


def test_real_html_saved_as_markdown_is_still_converted(lite_window, tmp_path) -> None:
    window = lite_window("<h1>Title</h1>\n<p>Some body text.</p>\n")
    window.path = None
    window.set_document_language("html", announce=False)
    converted = window.plan_markdown_conversion(tmp_path / "notes.md")
    assert converted is not None
    assert converted.strip().startswith("# Title")


def test_a_crlf_file_is_still_a_crlf_file_after_a_lap(lite_window, monkeypatch, tmp_path):
    """The other half of the report, in its own words: "we lose line endings".

    Two different things wear that name and only one of them was broken. The
    line *breaks* were being eaten, which is everything above. The line-ending
    *style* -- whether the file is written back with CRLF or LF -- is
    ``self.newline``, read once by ``_load_plain`` and handed to ``encode_text``
    on every save, and no part of the ring touches it. Asserted rather than
    assumed, because "it was never the problem" is exactly the claim that
    deserves a test rather than a sentence.
    """
    monkeypatch.setattr(modemod, "show_message_box", lambda *_a, **_k: wx.YES)
    source = tmp_path / "windows.md"
    source.write_bytes(DOCUMENT.replace("\n", "\r\n").encode("utf-8"))
    window = lite_window("")
    assert window.load(source) is True
    assert window.newline == "\r\n"

    for _ in range(4):
        window.cmd_switch_document_kind()

    assert window.newline == "\r\n", "the ring forgot the file's line-ending style"
    assert window.save(source) is True
    written = source.read_bytes()
    assert b"\r\n" in written
    assert written.count(b"\n") == written.count(b"\r\n"), "a lone LF got in"
    assert _headings(written.decode("utf-8")) == STRUCTURE
