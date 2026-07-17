"""Episode > Skip Settings... -- how far Skip Forward/Back jump, and (per
podcast only) automatic intro/outro skipping.

Context-aware the same way Sound Enhancements is: editing the currently
loaded show's own override when one is loaded (host resolves this, not the
dialog itself), the shared default otherwise. Auto-skip has no shared
default of its own -- "skip N seconds of every podcast automatically" isn't
a default anyone wants -- so those two fields are hidden entirely when no
show context is given (``show_title is None``).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


class SkipSettingsDialog:
    """Returns ``(skip_forward_seconds, skip_back_seconds,
    auto_skip_intro_seconds, auto_skip_outro_seconds)``, or ``None`` on
    Cancel. The last two are always ``0`` when constructed with
    ``show_title=None`` (there is no control to read them from)."""

    def __init__(
        self,
        parent: object,
        *,
        skip_forward_seconds: int,
        skip_back_seconds: int,
        auto_skip_intro_seconds: int = 0,
        auto_skip_outro_seconds: int = 0,
        show_title: str | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: tuple[int, int, int, int] | None = None
        self._show_context = show_title is not None

        self.dialog = wx.Dialog(parent, title="Skip Settings")
        root = wx.BoxSizer(wx.VERTICAL)

        subject = show_title or "podcasts without their own override"
        intro = wx.StaticText(
            self.dialog, label=f"How Skip Forward and Skip Back behave for {subject}."
        )
        intro.Wrap(420)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)
        grid.Add(
            wx.StaticText(self.dialog, label="Skip &Forward seconds:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._forward_ctrl = wx.SpinCtrl(self.dialog, min=1, max=600)
        self._forward_ctrl.SetValue(skip_forward_seconds)
        self._forward_ctrl.SetName("Skip Forward seconds")
        grid.Add(self._forward_ctrl, 0)
        grid.Add(
            wx.StaticText(self.dialog, label="Skip &Back seconds:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._back_ctrl = wx.SpinCtrl(self.dialog, min=1, max=600)
        self._back_ctrl.SetValue(skip_back_seconds)
        self._back_ctrl.SetName("Skip Back seconds")
        grid.Add(self._back_ctrl, 0)

        self._intro_ctrl: wx.SpinCtrl | None = None
        self._outro_ctrl: wx.SpinCtrl | None = None
        if self._show_context:
            grid.Add(
                wx.StaticText(self.dialog, label="Auto-skip &intro (0 = off):"),
                0,
                wx.ALIGN_CENTER_VERTICAL,
            )
            self._intro_ctrl = wx.SpinCtrl(self.dialog, min=0, max=600)
            self._intro_ctrl.SetValue(auto_skip_intro_seconds)
            self._intro_ctrl.SetName(
                "Automatically skip this many seconds when an episode starts fresh -- "
                "never applies when resuming a checkpointed position"
            )
            grid.Add(self._intro_ctrl, 0)
            grid.Add(
                wx.StaticText(self.dialog, label="Auto-skip &outro (0 = off):"),
                0,
                wx.ALIGN_CENTER_VERTICAL,
            )
            self._outro_ctrl = wx.SpinCtrl(self.dialog, min=0, max=600)
            self._outro_ctrl.SetValue(auto_skip_outro_seconds)
            self._outro_ctrl.SetName(
                "End the episode this many seconds before its own true end, "
                "exactly as if it had finished naturally"
            )
            grid.Add(self._outro_ctrl, 0)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "&OK")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

        ok_btn.Bind(wx.EVT_BUTTON, self._on_save)

    def show(self) -> tuple[int, int, int, int] | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="OK",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(self.dialog, "Skip Settings", announce=self._announce)
            return self._result if answer == wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    def _on_save(self, _event: object) -> None:
        self._result = (
            self._forward_ctrl.GetValue(),
            self._back_ctrl.GetValue(),
            self._intro_ctrl.GetValue() if self._intro_ctrl is not None else 0,
            self._outro_ctrl.GetValue() if self._outro_ctrl is not None else 0,
        )
        self.dialog.EndModal(self._wx.ID_OK)
