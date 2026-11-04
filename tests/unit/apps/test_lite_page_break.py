"""Ctrl+Enter in QUILL Lite: Word's page break, in every document that has pages.

A real page break in Word and Rich Text (the shared rich surface, the same one
QUILL's Ctrl+Enter calls), the ``::: pagebreak`` line in Markdown, and a
sentence saying why in plain text -- never silence.
"""

from __future__ import annotations

from quill.core.lite.commands import COMMANDS
from quill.core.tagging import PAGE_BREAK_MARKER


def test_ctrl_enter_is_insert_page_break_on_the_insert_menu():
    rows = [row for row in COMMANDS if row[3] == "cmd_insert_page_break"]
    assert rows == [("&Insert", "&Page Break", "Ctrl+Enter", "cmd_insert_page_break", "")]


def test_a_rich_document_gets_a_real_page_break(lite_window):
    win = lite_window("page one", mode="rich")
    win.cmd_insert_page_break()
    assert ("insert_page_break", None) in win.editor.calls
    assert win.announcements[-1] == "Page break inserted"
    assert win.modified


def test_markdown_gets_the_page_break_line(lite_window):
    win = lite_window("", mode="plain")
    win.set_document_language("markdown", announce=False)
    win.cmd_insert_page_break()
    assert PAGE_BREAK_MARKER in win.control.GetValue()
    assert win.announcements[-1] == "Page break inserted"
    assert win.editor.calls == []


def test_plain_text_says_why_rather_than_nothing(lite_window):
    win = lite_window("hello", mode="plain")
    win.set_document_language("plain", announce=False)
    win.announcements.clear()
    win.cmd_insert_page_break()
    assert win.announcements == ["A page break needs a Word, Rich Text or Markdown document"]
    assert win.control.GetValue() == "hello"
