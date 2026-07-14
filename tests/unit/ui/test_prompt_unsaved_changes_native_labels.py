"""#23: the unsaved-changes Save/Don't Save dialog must use the platform's
native Yes / No / Cancel buttons and accelerators. We previously overrode
the labels with SetYesNoCancelLabels("Save", "Don't Save", "Cancel"), which
on at least macOS Cocoa also disabled the built-in Y / N / Esc keyboard
accelerators that wx.MessageDialog wires up against its synthesised
buttons -- users had to Tab to a button and press Space. Native labels =
native accelerators, and these tests lock in that contract so a future
contributor can't reintroduce the label override without realising they
will break the keyboard shortcuts."""

from __future__ import annotations

import wx

from quill.ui.main_frame import MainFrame


class _Frame:
    pass


def _build_frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.frame = _Frame()
    frame._status: list[str] = []
    frame._set_status = lambda message: frame._status.append(message)  # type: ignore[method-assign]
    return frame


class _CapturingMessageDialog:
    """Stub wx.MessageDialog that records every interaction.

    Realistic enough for the prompt: knows about the style flags we use,
    the result codes the platform would return, and crucially records any
    call to SetYesNoCancelLabels so a regression to the pre-#23 behaviour
    fails this test loudly.
    """

    instances: list[_CapturingMessageDialog] = []

    def __init__(self, parent: object, message: str, title: str, style: int) -> None:
        self.parent = parent
        self.message = message
        self.title = title
        self.style = style
        self.set_label_calls: list[tuple[str, str, str]] = []
        self.show_modal_result: int = wx.ID_CANCEL
        self.destroyed = False
        _CapturingMessageDialog.instances.append(self)

    def SetYesNoCancelLabels(self, yes: str, no: str, cancel: str) -> bool:
        self.set_label_calls.append((yes, no, cancel))
        return True

    def ShowModal(self) -> int:
        return self.show_modal_result

    def Destroy(self) -> None:
        self.destroyed = True


def _install_wx_stub(frame: MainFrame) -> type[_CapturingMessageDialog]:
    """Replace frame._wx with a stub module that exposes the dialog class."""
    _CapturingMessageDialog.instances.clear()

    def _show_modal_dialog(dialog: _CapturingMessageDialog, _label: str, **_kwargs: object) -> int:
        # Forward ShowModal() so the test can drive the result, then
        # return it unchanged -- mirroring the real helper's contract.
        return dialog.ShowModal()

    frame._show_modal_dialog = _show_modal_dialog  # type: ignore[method-assign]

    class _WX:
        MessageDialog = _CapturingMessageDialog
        YES_NO = 0x4000
        CANCEL = 0x8000
        ICON_WARNING = 0x100
        ID_YES = 5103
        ID_NO = 5104
        ID_CANCEL = 5102

    frame._wx = _WX()  # type: ignore[attr-defined]
    return _CapturingMessageDialog


def test_prompt_does_not_call_set_yes_no_cancel_labels() -> None:
    frame = _build_frame()
    dialog_cls = _install_wx_stub(frame)

    frame._prompt_unsaved_changes_action(
        "Unsaved changes",
        "You have unsaved changes. Save before closing?",
    )

    assert len(dialog_cls.instances) == 1
    # The contract: SetYesNoCancelLabels must not be called. The pre-#23
    # code did call it with ("Save", "Don't Save", "Cancel"), which on
    # macOS Cocoa disabled the Y/N keyboard accelerators.
    assert dialog_cls.instances[0].set_label_calls == []


def test_prompt_requests_yes_no_cancel_with_warning_icon() -> None:
    frame = _build_frame()
    dialog_cls = _install_wx_stub(frame)

    frame._prompt_unsaved_changes_action(
        "Unsaved changes",
        "You have unsaved changes. Save before closing?",
    )

    dialog = dialog_cls.instances[0]
    wx_stub = frame._wx
    # The three flags must be present so the platform synthesises Yes, No
    # and Cancel buttons (and the corresponding Y/N/Esc accelerators).
    assert dialog.style & wx_stub.YES_NO
    assert dialog.style & wx_stub.CANCEL
    assert dialog.style & wx_stub.ICON_WARNING


def test_prompt_returns_show_modal_result_unchanged() -> None:
    frame = _build_frame()
    dialog_cls = _install_wx_stub(frame)

    for expected in (wx.ID_YES, wx.ID_NO, wx.ID_CANCEL):
        dialog_cls.instances.clear()
        # Configure the next-constructed dialog to return ``expected``
        # by patching __init__ to record the desired return code on the
        # new instance, then restoring the original init afterwards.
        original_init = dialog_cls.__init__

        def init_with(
            self: _CapturingMessageDialog,
            parent: object,
            message: str,
            title: str,
            style: int,
            *,
            _result: int = expected,
            _orig: object = original_init,
        ) -> None:
            _orig(self, parent, message, title, style)  # type: ignore[call-arg]
            self.show_modal_result = _result

        dialog_cls.__init__ = init_with  # type: ignore[assignment]
        try:
            result = frame._prompt_unsaved_changes_action(
                "Unsaved changes",
                "You have unsaved changes. Save before closing?",
            )
        finally:
            dialog_cls.__init__ = original_init  # type: ignore[assignment]

        assert result == expected


def test_prompt_passes_through_message_title_and_parent() -> None:
    frame = _build_frame()
    dialog_cls = _install_wx_stub(frame)

    frame._prompt_unsaved_changes_action(
        "Unsaved changes",
        "Body text the user will see.",
    )

    dialog = dialog_cls.instances[0]
    assert dialog.parent is frame.frame
    assert dialog.title == "Unsaved changes"
    assert dialog.message == "Body text the user will see."


def test_prompt_destroys_dialog_after_show_modal() -> None:
    frame = _build_frame()
    dialog_cls = _install_wx_stub(frame)

    frame._prompt_unsaved_changes_action(
        "Unsaved changes",
        "You have unsaved changes. Save before closing?",
    )

    # The try/finally in _prompt_unsaved_changes_action must Destroy() the
    # dialog so the C++ peer is freed even if ShowModal raises.
    assert dialog_cls.instances[0].destroyed is True
