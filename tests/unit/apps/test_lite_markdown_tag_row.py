"""Insert > Markdown Tag is on QUILL Lite's menu only in a Markdown document.

Reported from @quillforall: "in either a Rich Text or Plain Text document, I've
noticed that the item for inserting a Markdown tag in the Insert menu is
unavailable." It was dimmed there. The owner's decision is that it is not there
at all outside Markdown, in both editors -- and that its key, pressed in such a
document, says why rather than doing nothing (a dimmed row's key never fired).

The rows are real ``wx.MenuItem`` objects on a real ``wx.Menu``, because what
has to be true is that the row leaves the menu and comes back to the same
place, which a stand-in cannot show. The sweep is the shipped
``DocumentMenuMixin.sync_menu_state``, run by the language change itself: a
QUILL Lite document is an MDI child, so ``EVT_MENU_OPEN`` goes to the shell and
cannot be what keeps the row right.
"""

from __future__ import annotations

import pytest
import wx

from quill.core.lite.format_kinds import FORMAT_COMMAND_KINDS
from quill.ui.markdown_tag_row import MARKDOWN_TAG_REFUSAL, HideableMenuRow
from quill.ui.richedit_editing import RICH


class _Item:
    """Enough of ``wx.MenuItem`` for the Format rows the same sweep dims."""

    def Enable(self, value: bool) -> None:  # noqa: N802 - wx spelling
        self.enabled = bool(value)


def _labels(menu: wx.Menu) -> list[str]:
    return [
        "---" if item.IsSeparator() else item.GetItemLabelText() for item in menu.GetMenuItems()
    ]


@pytest.fixture
def insert_window(lite_window, wx_app):
    """An untitled plain document carrying a real Insert menu and the real sweep."""
    from quill.apps.lite_window_menus import DocumentMenuMixin

    window = lite_window("# Heading one\n\nSome text\n")
    window.path = None
    window._language_override = ""
    menu = wx.Menu()
    menu.Append(wx.ID_ANY, "Lin&k...\tCtrl+K")
    menu.AppendSeparator()
    markdown = menu.Append(wx.ID_ANY, "&Markdown Tag...\tCtrl+Alt+I")
    html = menu.Append(wx.ID_ANY, "&HTML Tag...\tCtrl+Alt+O")
    window.insert_menu = menu
    window._menu_items = {handler: _Item() for handler in FORMAT_COMMAND_KINDS}
    window._menu_items["cmd_insert_markdown_tag"] = markdown
    window._menu_items["cmd_insert_html_tag"] = html
    window._hideable_rows = {"cmd_insert_markdown_tag": HideableMenuRow(menu, markdown)}
    window._sync_enabled_items = lambda: DocumentMenuMixin._sync_enabled_items(window)
    window.sync_menu_state = lambda: DocumentMenuMixin.sync_menu_state(window)
    window.sync_menu_state()
    yield window
    # A row left off its menu is owned by the row object, not by the menu.
    for row in window._hideable_rows.values():
        row.set_shown(True)
    menu.Destroy()


def test_the_row_is_absent_from_a_plain_document(insert_window) -> None:
    assert _labels(insert_window.insert_menu) == ["Link...", "---", "HTML Tag..."]


def test_the_row_appears_in_a_markdown_document_in_its_own_place(insert_window) -> None:
    insert_window.set_document_language("markdown", announce=False)
    assert _labels(insert_window.insert_menu) == [
        "Link...",
        "---",
        "Markdown Tag...",
        "HTML Tag...",
    ]
    row = insert_window._menu_items["cmd_insert_markdown_tag"]
    assert row.IsEnabled()
    # Still advertises its key: every visible row must (the accelerator gate).
    assert row.GetItemLabel().endswith("\tCtrl+Alt+I")


def test_switching_away_and_back_follows_the_document(insert_window) -> None:
    insert_window.set_document_language("markdown", announce=False)
    insert_window.set_document_language("html", announce=False)
    assert "Markdown Tag..." not in _labels(insert_window.insert_menu)
    insert_window.set_document_language("plain", announce=False)
    assert "Markdown Tag..." not in _labels(insert_window.insert_menu)
    insert_window.set_document_language("markdown", announce=False)
    assert _labels(insert_window.insert_menu).count("Markdown Tag...") == 1


def test_a_rich_document_has_no_markdown_row_even_under_a_markdown_name(insert_window) -> None:
    insert_window.set_document_language("markdown", announce=False)
    insert_window.editor.mode = RICH
    insert_window.sync_menu_state()
    assert "Markdown Tag..." not in _labels(insert_window.insert_menu)


def test_the_html_row_is_still_only_dimmed(insert_window) -> None:
    # The decision was about the Markdown row. HTML Tag keeps its old rule.
    assert "HTML Tag..." in _labels(insert_window.insert_menu)
    assert not insert_window._menu_items["cmd_insert_html_tag"].IsEnabled()


@pytest.mark.parametrize("language", ["plain", "html"])
def test_the_key_in_another_kind_of_document_says_why(insert_window, language) -> None:
    insert_window.set_document_language(language, announce=False)
    insert_window.announcements.clear()
    insert_window.cmd_insert_markdown_tag()
    assert insert_window.announcements == [MARKDOWN_TAG_REFUSAL]
    assert MARKDOWN_TAG_REFUSAL == "Markdown tags are for Markdown documents."


def test_the_key_in_a_rich_document_says_why(insert_window) -> None:
    insert_window.editor.mode = RICH
    insert_window.announcements.clear()
    insert_window.cmd_insert_markdown_tag()
    assert insert_window.announcements == [MARKDOWN_TAG_REFUSAL]
