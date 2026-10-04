"""Insert > Insert Markdown Tag is on QUILL's menu only in a Markdown document.

The QUILL half of the @quillforall report ("the item for inserting a Markdown
tag in the Insert menu is unavailable" in rich and plain documents). QUILL Lite
may never be ahead of QUILL, so the rule, the sentence and the machinery that
moves the row are one shared module, :mod:`quill.ui.markdown_tag_row`, and both
editors are tested against it.

Real ``wx.MenuBar`` objects throughout: whether a row really leaves a menu and
comes back to the same place is a question about wx, not about a stand-in.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from quill.ui.main_frame import MainFrame
from quill.ui.markdown_tag_row import (
    MARKDOWN_TAG_REFUSAL,
    HideableMenuRow,
    markdown_tag_row_shown,
    sync_menu_row,
)


@pytest.fixture
def app():
    existing = wx.GetApp()
    if existing is not None:
        try:
            existing.GetAppName()
            return existing
        except Exception:  # noqa: BLE001 - a dead App is not a usable App
            pass
    return wx.App()


def _labels(menu: wx.Menu) -> list[str]:
    return [
        "---" if item.IsSeparator() else item.GetItemLabelText() for item in menu.GetMenuItems()
    ]


@pytest.mark.parametrize(
    ("kind", "shown"),
    [("markdown", True), ("plain", False), ("rich", False), ("html", False)],
)
def test_only_a_markdown_document_carries_the_row(kind: str, shown: bool) -> None:
    assert markdown_tag_row_shown(kind) is shown


def test_a_hidden_row_returns_below_its_separator(app) -> None:
    menu = wx.Menu()
    menu.Append(wx.ID_ANY, "Lin&k...\tCtrl+K")
    menu.AppendSeparator()
    item = menu.Append(wx.ID_ANY, "&Markdown Tag...\tCtrl+Alt+I")
    menu.Append(wx.ID_ANY, "&HTML Tag...\tCtrl+Alt+O")
    row = HideableMenuRow(menu, item)
    assert row.accel is not None and row.accel.GetKeyCode() == ord("I")
    row.set_shown(False)
    row.set_shown(False)  # idempotent
    assert _labels(menu) == ["Link...", "---", "HTML Tag..."]
    row.set_shown(True)
    row.set_shown(True)
    assert _labels(menu) == ["Link...", "---", "Markdown Tag...", "HTML Tag..."]
    menu.Destroy()


def _quill_frame(*, context: str, mode: str = "markup") -> tuple[MainFrame, wx.MenuBar, wx.Menu]:
    """A MainFrame shell carrying a real menu bar with QUILL's Insert rows."""
    frame = MainFrame.__new__(MainFrame)
    bar = wx.MenuBar()
    insert = wx.Menu()
    ids = {}
    for name, label in (
        ("_id_insert_table", "Insert &Table..."),
        ("_id_insert_html_tag", "I&nsert HTML Tag..."),
        ("_id_insert_markdown_tag", "Insert &Markdown Tag...\tCtrl+Alt+I"),
        ("_id_insert_snippet", "In&sert Snippet..."),
    ):
        ids[name] = insert.Append(wx.ID_ANY, label).GetId()
        setattr(frame, name, ids[name])
    bar.Append(insert, "&Insert")
    for name in (
        "_id_insert_task_list",
        "_id_insert_code_block",
        "_id_insert_footnote",
        *(f"_id_heading_{level}" for level in range(1, 7)),
    ):
        setattr(frame, name, wx.NewIdRef().GetId())
    frame.editor = object()
    frame.frame = SimpleNamespace(GetMenuBar=lambda: bar)
    frame.document = SimpleNamespace(path=None)
    frame._menu_updates_allowed = lambda: True
    frame._current_markup_context = lambda: frame.context
    frame._current_editor_mode = lambda: frame.mode
    frame._active_markup_surface = lambda: frame.context
    frame._refresh_language_menu_radio = lambda _bar: None
    frame._reapply_menu_routes = lambda: None
    frame.context = context
    frame.mode = mode
    return frame, bar, insert


@pytest.mark.parametrize(
    ("context", "mode", "present"),
    [
        ("markdown", "markup", True),
        ("plain", "markup", False),
        ("html", "markup", False),
        ("markdown", "rich", False),
        ("plain", "rich_converted", False),
    ],
)
def test_quill_shows_the_row_only_in_markdown(app, context, mode, present) -> None:
    frame, bar, insert = _quill_frame(context=context, mode=mode)
    frame._refresh_contextual_menu_items()
    assert ("Insert Markdown Tag..." in _labels(insert)) is present
    bar.Destroy()


def test_quill_row_follows_a_change_of_document(app) -> None:
    frame, bar, insert = _quill_frame(context="plain")
    frame._refresh_contextual_menu_items()
    assert "Insert Markdown Tag..." not in _labels(insert)
    frame.context = "markdown"
    frame._refresh_contextual_menu_items()
    assert _labels(insert) == [
        "Insert Table...",
        "Insert HTML Tag...",
        "Insert Markdown Tag...",
        "Insert Snippet...",
    ]
    assert bar.FindItemById(frame._id_insert_markdown_tag).IsEnabled()
    frame.mode = "rich"
    frame._refresh_contextual_menu_items()
    assert "Insert Markdown Tag..." not in _labels(insert)
    frame.mode = "markup"
    frame._refresh_contextual_menu_items()
    assert _labels(insert).count("Insert Markdown Tag...") == 1
    bar.Destroy()


def test_a_row_hidden_from_a_replaced_bar_is_not_put_back_into_it(app) -> None:
    frame, bar, insert = _quill_frame(context="plain")
    frame._refresh_contextual_menu_items()
    other = wx.MenuBar()  # a rebuilt bar without the row (area switched off)
    sync_menu_row(frame, "_markdown_tag_row", other, frame._id_insert_markdown_tag, True)
    assert "Insert Markdown Tag..." not in _labels(insert)
    other.Destroy()
    frame._markdown_tag_row[1].set_shown(True)  # hand the item back before teardown
    bar.Destroy()


@pytest.mark.parametrize(("context", "mode"), [("plain", "markup"), ("markdown", "rich")])
def test_quill_key_in_another_kind_of_document_says_why(context, mode) -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._current_markup_context = lambda: context
    frame._current_editor_mode = lambda: mode
    frame._feature_enabled = lambda _feature: True
    said: list[str] = []
    frame._announce_result = said.append

    def _no_picker(**_kwargs):
        raise AssertionError("the picker must not open outside Markdown")

    frame._choose_searchable_option = _no_picker
    frame.insert_markdown_tag()
    assert said == [MARKDOWN_TAG_REFUSAL]
    assert said == ["Markdown tags are for Markdown documents."]


def test_quill_key_in_a_markdown_document_opens_the_picker() -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._current_markup_context = lambda: "markdown"
    frame._current_editor_mode = lambda: "markup"
    frame._feature_enabled = lambda _feature: True
    opened: list[str] = []
    frame._choose_searchable_option = lambda **kwargs: opened.append(kwargs["title"]) or ""
    frame.insert_markdown_tag()
    assert opened == ["Insert Markdown Tag"]
