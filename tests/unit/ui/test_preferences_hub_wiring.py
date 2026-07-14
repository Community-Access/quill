"""Source-contract test for the multi-page Preferences hub wiring.

The Preferences hub replaces the old "pick an area, press OK, then the area
opens" ``wx.SingleChoiceDialog`` with a single book control: a left-hand
category list (``wx.Listbook``) on every platform. (macOS deliberately uses
``wx.Listbook`` too — its native ``wx.Toolbook`` selector null-derefs in
``wxToolBarTool::UpdateImages()`` when ``AddPage()`` is called without a
per-tool bitmap, which segfaulted Cmd+, on macOS; see 6d1bc9e.) These
assertions read the source as text (wxPython cannot be imported in
headless CI) and pin the wiring that keeps the hub accessible: a book
selector, first category selected on open, and one open button per area.
"""

from pathlib import Path


def _open_preferences_source() -> str:
    source = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")
    start = source.index("def open_preferences(self)")
    end = source.index("\n    def ", start + 1)
    return source[start:end]


def test_preferences_uses_listbook_on_every_platform() -> None:
    body = _open_preferences_source()
    # Listbook is the selector on every platform; Toolbook is no longer
    # wired because its native toolbar selector needs per-page bitmaps.
    assert "wx.Listbook(" in body
    assert "wx.Toolbook(" not in body


def test_preferences_no_longer_uses_single_choice_picker() -> None:
    body = _open_preferences_source()
    # The old "choose then OK then open" indirection is gone.
    assert "SingleChoiceDialog" not in body


def test_preferences_selects_first_category_on_open() -> None:
    body = _open_preferences_source()
    assert "book.SetSelection(0)" in body


def test_preferences_lands_initial_focus_on_the_selector() -> None:
    body = _open_preferences_source()
    # Focus must land on the category selector so arrow keys and first-letter
    # type-ahead work immediately, and the contract focus heuristic must not
    # steal it back to a button.
    assert "book.SetFocus()" in body
    assert "dialog._quill_keep_initial_focus = True" in body


def test_preferences_enter_opens_highlighted_category() -> None:
    body = _open_preferences_source()
    # Enter on a highlighted category opens it without Tabbing to the button,
    # but a focused button keeps its native Enter behavior.
    assert "wx.EVT_CHAR_HOOK" in body
    assert "isinstance(focused, wx.Button)" in body
    assert "book.GetSelection()" in body


def test_preferences_adds_a_page_and_open_button_per_area() -> None:
    body = _open_preferences_source()
    assert "book.AddPage(" in body
    assert 'open_btn.SetName(f"Open {label}")' in body
    # Each area is launched by its own button after the hub closes.
    assert 'chosen["handler"] = handler' in body


def test_preferences_runs_chosen_handler_after_the_hub_closes() -> None:
    body = _open_preferences_source()
    # Exactly one modal is on screen at a time: the chosen area handler runs
    # only after the hub has closed, and closing without a choice reports it.
    assert 'handler = chosen["handler"]' in body
    assert "if handler is None:" in body
    assert 'self._set_status("Preferences closed")' in body
    assert "handler()" in body


def test_general_settings_search_box_removed() -> None:
    source = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")
    # The "no search button here" requirement: the Settings notebook must no
    # longer build a search box or its enter-to-jump handler.
    assert "Search settings" not in source
    assert "def _on_search(" not in source
