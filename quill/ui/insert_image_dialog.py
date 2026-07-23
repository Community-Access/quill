"""Insert Image dialog (#899): a mandatory-alt-text insertion flow.

Every other way an image reaches a QUILL document -- pasted, typed by hand,
imported from another format -- can carry no alt text at all, and did until
now. This dialog is the one insertion path that makes the choice explicit:
either write alt text, or deliberately mark the image decorative (the
correct accessible pattern for an image with no informational content --
distinct from an image nobody ever gave alt text to, which is the actual
problem #899 is about).

Two enrichments layer on top of that promise:

* **AI alt text.** When an AI vision model is connected (and not in Safe
  Mode), a "Suggest alt text with AI" button describes the chosen file and
  drops the result into the alt field for the author to check and edit --
  the machine drafts, the human approves. Purely optional; the field stays
  fully hand-editable.
* **HTML sizing.** In an HTML document, the dialog also collects width,
  height, a responsive cap, and an optional caption, so the emitted
  ``<img>``/``<figure>`` lays out correctly on a page (no layout shift,
  never overflowing a column). These fields are hidden in Markdown mode,
  where the syntax cannot carry them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import wx

from quill.core.inline_image_alt import build_image_markdown


@dataclass(frozen=True, slots=True)
class ImageInsertRequest:
    """Everything the caller needs to build Markdown or HTML for the image."""

    path: str
    alt_text: str
    decorative: bool
    width: int | None = None
    height: int | None = None
    responsive: bool = False
    caption: str = ""


class InsertImageDialog:
    """Collect a file path and alt text (or a decorative flag) for Insert Image."""

    def __init__(
        self,
        parent: object,
        announce_cb: Callable[[str], None] | None = None,
        *,
        html_mode: bool = False,
        ai_suggest_cb: Callable[[str], tuple[str | None, str | None]] | None = None,
    ) -> None:
        self._announce = announce_cb or (lambda _msg: None)
        self._html_mode = html_mode
        self._ai_suggest_cb = ai_suggest_cb
        self._result: str | None = None
        self._request: ImageInsertRequest | None = None

        self.dialog = wx.Dialog(
            parent, title="Insert Image", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(480, 320 if html_mode else 260))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(self.dialog, label="Image &file:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8
        )
        path_row = wx.BoxSizer(wx.HORIZONTAL)
        self._path_ctrl = wx.TextCtrl(self.dialog)
        self._path_ctrl.SetName("Image file path")
        path_row.Add(self._path_ctrl, 1)
        self._btn_browse = wx.Button(self.dialog, label="&Browse...")
        path_row.Add(self._btn_browse, 0, wx.LEFT, 4)
        root.Add(path_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        alt_label_row = wx.BoxSizer(wx.HORIZONTAL)
        alt_label_row.Add(
            wx.StaticText(self.dialog, label="&Alt text (what this image shows):"),
            1,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._btn_ai = None
        if self._ai_suggest_cb is not None:
            self._btn_ai = wx.Button(self.dialog, label="&Suggest alt text with AI")
            self._btn_ai.SetName("Describe the chosen image with AI and fill the alt text field")
            alt_label_row.Add(self._btn_ai, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
        root.Add(alt_label_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self._alt_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE)
        self._alt_ctrl.SetName("Alt text")
        root.Add(self._alt_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._decorative_check = wx.CheckBox(
            self.dialog,
            label="This image is &decorative (no informational content -- skip alt text)",
        )
        self._decorative_check.SetName("Decorative image, no alt text needed")
        root.Add(self._decorative_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # HTML-only presentation controls. Markdown cannot carry them, so they
        # only appear when the target document is HTML.
        self._width_ctrl: wx.TextCtrl | None = None
        self._height_ctrl: wx.TextCtrl | None = None
        self._responsive_check: wx.CheckBox | None = None
        self._caption_ctrl: wx.TextCtrl | None = None
        if html_mode:
            size_box = wx.StaticBoxSizer(wx.HORIZONTAL, self.dialog, "Size and layout (HTML)")
            size_box.Add(
                wx.StaticText(self.dialog, label="&Width:"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
                4,
            )
            self._width_ctrl = wx.TextCtrl(self.dialog, size=wx.Size(64, -1))
            self._width_ctrl.SetName("Image width in pixels, optional")
            size_box.Add(self._width_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
            size_box.Add(
                wx.StaticText(self.dialog, label="Hei&ght:"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
                8,
            )
            self._height_ctrl = wx.TextCtrl(self.dialog, size=wx.Size(64, -1))
            self._height_ctrl.SetName("Image height in pixels, optional")
            size_box.Add(self._height_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
            self._responsive_check = wx.CheckBox(
                self.dialog, label="&Responsive (cap to page width)"
            )
            self._responsive_check.SetValue(True)
            self._responsive_check.SetName("Scale down to fit the page, never overflow")
            size_box.Add(self._responsive_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 12)
            root.Add(size_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            root.Add(
                wx.StaticText(self.dialog, label="&Caption (optional, adds a figure caption):"),
                0,
                wx.LEFT | wx.RIGHT,
                8,
            )
            self._caption_ctrl = wx.TextCtrl(self.dialog)
            self._caption_ctrl.SetName("Figure caption")
            root.Add(self._caption_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_insert = wx.Button(self.dialog, wx.ID_OK, label="&Insert")
        btn_cancel = wx.Button(self.dialog, wx.ID_CANCEL, label="C&ancel")
        btn_row.AddStretchSpacer(1)
        btn_row.Add(self._btn_insert, 0, wx.RIGHT, 4)
        btn_row.Add(btn_cancel, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        self.dialog.Layout()

        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Insert",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )

        self._btn_browse.Bind(wx.EVT_BUTTON, self._on_browse)
        self._decorative_check.Bind(wx.EVT_CHECKBOX, self._on_decorative_toggle)
        self._btn_insert.Bind(wx.EVT_BUTTON, self._on_insert)
        if self._btn_ai is not None:
            self._btn_ai.Bind(wx.EVT_BUTTON, self._on_suggest_ai)

        self._path_ctrl.SetFocus()

    # -- public API --

    def show(self) -> str | None:
        """Show modally; return the Markdown to insert, or None if canceled.

        Retained for the Markdown path and existing callers/tests; HTML callers
        use :meth:`show_request` to get every field.
        """
        from quill.ui.dialog_contract import show_modal_dialog

        show_modal_dialog(self.dialog, "Insert Image")
        return self._result

    def show_request(self) -> ImageInsertRequest | None:
        """Show modally; return the full :class:`ImageInsertRequest`, or None."""
        from quill.ui.dialog_contract import show_modal_dialog

        show_modal_dialog(self.dialog, "Insert Image")
        return self._request

    def close(self) -> None:
        self.dialog.Destroy()

    # -- event handlers --

    def _on_browse(self, _event: object) -> None:
        wildcard = (
            "Image files (*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp)"
            "|*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp|All files (*.*)|*.*"
        )
        with wx.FileDialog(
            self.dialog,
            "Choose an image",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as pick:
            if pick.ShowModal() == wx.ID_OK:
                self._path_ctrl.SetValue(pick.GetPath())

    def _on_decorative_toggle(self, _event: object) -> None:
        decorative = self._decorative_check.GetValue()
        self._alt_ctrl.Enable(not decorative)
        if self._btn_ai is not None:
            self._btn_ai.Enable(not decorative)

    def _on_suggest_ai(self, _event: object) -> None:
        if self._ai_suggest_cb is None:
            return
        path = self._path_ctrl.GetValue().strip()
        if not path:
            self._status.SetLabel("Choose an image file first, then ask AI to describe it.")
            self._announce(self._status.GetLabel())
            return
        self._status.SetLabel("Asking AI to describe this image...")
        self._announce("Asking AI to describe this image")
        text, error = self._ai_suggest_cb(path)
        if error:
            self._status.SetLabel(error)
            self._announce(error)
            return
        if not text:
            self._status.SetLabel("AI returned no description. Please write the alt text yourself.")
            self._announce(self._status.GetLabel())
            return
        self._alt_ctrl.SetValue(text)
        self._status.SetLabel("AI drafted alt text -- please review and edit before inserting.")
        self._announce("AI drafted alt text. Review and edit it, then insert.")
        self._alt_ctrl.SetFocus()

    def _read_int(self, ctrl: wx.TextCtrl | None) -> int | None:
        if ctrl is None:
            return None
        raw = ctrl.GetValue().strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            return None
        return value if value > 0 else None

    def _on_insert(self, _event: object) -> None:
        path = self._path_ctrl.GetValue().strip()
        if not path:
            self._status.SetLabel("Choose an image file first.")
            self._announce("Choose an image file first.")
            return
        decorative = self._decorative_check.GetValue()
        alt_text = self._alt_ctrl.GetValue().strip()
        if not decorative and not alt_text:
            self._status.SetLabel("Enter alt text describing this image, or mark it decorative.")
            self._announce("Enter alt text describing this image, or mark it decorative.")
            return
        self._result = build_image_markdown(path, alt_text, decorative=decorative)
        self._request = ImageInsertRequest(
            path=path,
            alt_text=alt_text,
            decorative=decorative,
            width=self._read_int(self._width_ctrl),
            height=self._read_int(self._height_ctrl),
            responsive=bool(self._responsive_check and self._responsive_check.GetValue()),
            caption=self._caption_ctrl.GetValue().strip() if self._caption_ctrl else "",
        )
        if self.dialog.IsModal():
            self.dialog.EndModal(wx.ID_OK)
