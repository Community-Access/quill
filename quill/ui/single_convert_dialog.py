"""Single-file post-conversion prompt (issue #262).

After a successful single-file Import or Export, if the resulting format is
editable in QUILL (Markdown family, HTML, plain text, CSV / TSV), the user is
offered to open the new file in a new window. PDF, DOCX, EPUB, ODT, RTF, and
LaTeX are producible but not directly editable; no prompt for those.

The dialog is intentionally minimal: a single yes / no choice, no busy
chrome. Yes opens the file via ``MainFrame.open_path``; No just dismisses
the dialog and the caller shows a "Converted to: {path}" message.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import wx

from quill.core import pandoc_formats
from quill.core.i18n import _

_log = logging.getLogger(__name__)


def prompt_open_in_new_window(
    parent: wx.Window,
    *,
    output_path: str,
    target_format: str,
    show_modal_fn: Callable[[wx.Dialog, str], int] | None = None,
) -> bool:
    """Show the post-conversion prompt and return ``True`` if the user said Yes.

    Returns ``False`` immediately when ``target_format`` is not editable in
    QUILL (no prompt is shown — non-editable outputs just land on disk).
    Returns ``False`` when the user explicitly says No.
    """

    if not pandoc_formats.is_editable_in_quill(target_format):
        return False

    message = _("Conversion complete. Open {filename} in a new window?").format(
        filename=output_path
    )

    dlg = wx.MessageDialog(
        parent,
        message,
        _("Open in new window?"),
        style=wx.YES_NO | wx.ICON_QUESTION | wx.YES_DEFAULT,
    )
    try:
        if show_modal_fn is not None:
            result = show_modal_fn(dlg, _("Open in new window?"))
        else:
            result = dlg.ShowModal()
        return result == wx.ID_YES
    finally:
        dlg.Destroy()


__all__ = ["prompt_open_in_new_window"]
