"""Selection semantics of the experimental RichTextCtrl editor surface.

wx.richtext.RichTextCtrl.GetSelection() returns a RichTextSelection object,
but every editor consumer in QUILL unpacks the wx.TextCtrl (start, end) tuple
-- the status bar does so during startup, so selecting the "rtf" surface
crashed the app before the first window appeared. The surface wrapper maps
GetSelectionRange() (which reports -2, -2 for "no selection") onto TextCtrl
semantics (caret, caret).
"""

from quill.ui.rtf_edit_surface import normalize_selection_range


def test_no_selection_maps_to_caret() -> None:
    # RichTextCtrl reports (-2, -2) when nothing is selected.
    assert normalize_selection_range(-2, -2, 7) == (7, 7)


def test_active_selection_passes_through() -> None:
    assert normalize_selection_range(2, 7, 7) == (2, 7)


def test_empty_selection_at_position_passes_through() -> None:
    assert normalize_selection_range(4, 4, 4) == (4, 4)


def test_negative_or_reversed_range_maps_to_caret() -> None:
    assert normalize_selection_range(-1, -1, 3) == (3, 3)
    assert normalize_selection_range(5, 3, 4) == (4, 4)
