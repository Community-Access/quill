"""wx.RichTextCtrl editor surface for the experimental "rtf" option.

Selected on the Experimental tab (``experimental_editor_surface = "rtf"``).
``wx.richtext.RichTextCtrl`` is TextCtrl-compatible for the value/caret API
QUILL relies on, with one exception: ``GetSelection()`` returns a
``RichTextSelection`` object where ``wx.TextCtrl`` returns a ``(start, end)``
tuple. Every editor consumer unpacks the tuple -- the status bar does so
while the first document tab is built, so the raw control crashed QUILL at
startup. :class:`RtfEditorSurface` restores the TextCtrl contract from
``GetSelectionRange()``, which reports ``(-2, -2)`` when nothing is selected.

Mirrors the ``win32_edit_surface`` defensive pattern: on any failure the
factory returns a stock ``wx.TextCtrl`` itself, so selecting this surface can
never brick the editor.
"""

from __future__ import annotations

from typing import Any

try:
    import wx.richtext as _rt

    _RICHTEXT = True
except Exception:  # noqa: BLE001 - wx.richtext absent/broken: surface unavailable
    _RICHTEXT = False


def normalize_selection_range(start: int, end: int, insertion_point: int) -> tuple[int, int]:
    """Map a RichTextCtrl selection range onto wx.TextCtrl GetSelection semantics.

    No selection is ``(-2, -2)`` in RichTextCtrl but ``(caret, caret)`` in
    TextCtrl; a well-formed range passes through unchanged (the end is
    already exclusive, matching TextCtrl).
    """
    if start < 0 or end < start:
        return insertion_point, insertion_point
    return int(start), int(end)


if _RICHTEXT:

    class RtfEditorSurface(_rt.RichTextCtrl):  # type: ignore[misc]
        """RichTextCtrl with TextCtrl-compatible ``GetSelection``."""

        def GetSelection(self) -> tuple[int, int]:  # noqa: N802 - wx API
            selection = self.GetSelectionRange()
            return normalize_selection_range(
                int(selection.GetStart()),
                int(selection.GetEnd()),
                int(self.GetInsertionPoint()),
            )


def create_rtf_editor(wx_module: Any, parent: Any, style: int) -> Any:
    """Build the RichTextCtrl surface, or a stock ``wx.TextCtrl`` fallback."""
    if _RICHTEXT:
        try:
            return RtfEditorSurface(parent, style=style)
        except Exception:  # noqa: BLE001 - hosting is best-effort; fall back to wx
            pass
    return wx_module.TextCtrl(parent, style=style)
