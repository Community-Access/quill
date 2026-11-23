"""Inkwell's target-bound external text runtime.

This is the platform-facing entry point for explicit global text operations.
It owns target discovery and delegates mutation to :class:`TextTransaction`;
callers do not need to reach into UIA, clipboard, or ``SendInput`` helpers.

Windows-only, wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from quill.core.external_text import (
    ExternalTextReason,
    OperationResult,
    OperationStatus,
    SelectionSnapshot,
    TargetSnapshot,
    TargetState,
    TextCapability,
    TextReplacement,
)
from quill.platform.windows.clipboard_transaction import ClipboardPort
from quill.platform.windows.external_target import probe_focused_target
from quill.platform.windows.selection_capture import capture_uia_selection
from quill.platform.windows.text_injector import (
    InjectionResult,
    move_caret_left_checked,
    send_backspaces_checked,
    send_paste_checked,
    send_text_checked,
)
from quill.platform.windows.text_transaction import (
    SelectionCapture,
    TargetProbe,
    TextTransaction,
)

__all__ = ["InkwellTextRuntime"]


class InkwellTextRuntime:
    """Provide validated insertion and replacement for Inkwell commands."""

    def __init__(
        self,
        *,
        target_probe: TargetProbe = probe_focused_target,
        selection_capture: SelectionCapture = capture_uia_selection,
        clipboard: ClipboardPort | None = None,
        send_text: Callable[[str], InjectionResult] = send_text_checked,
        send_backspaces: Callable[[int], InjectionResult] = send_backspaces_checked,
        send_paste: Callable[[], InjectionResult] = send_paste_checked,
        move_caret: Callable[[int], InjectionResult] = move_caret_left_checked,
    ) -> None:
        self._target_probe = target_probe
        self._selection_capture = selection_capture
        self._clipboard = clipboard
        self._send_text = send_text
        self._send_paste = send_paste
        self._send_backspaces = send_backspaces
        self._move_caret = move_caret

    def insert_text(
        self,
        text: str,
        *,
        expected_window: int = 0,
        expected_target: TargetSnapshot | None = None,
        use_clipboard: bool = False,
        caret_from_end: int = 0,
    ) -> OperationResult:
        """Insert into the currently focused, optionally expected window.

        *expected_target* is the control the text was meant for, captured when
        the input began (FUX-07): anything else in front -- another control,
        another window, the same program restarted -- types nothing.
        """
        moved = self._moved_from(expected_target)
        if moved is not None:
            return moved
        transaction = self._transaction(expected_window, expected_target)
        return transaction.insert_text(
            text,
            use_clipboard=use_clipboard,
            caret_from_end=caret_from_end,
        )

    def replace_selection(
        self,
        replacement: TextReplacement,
        *,
        expected_window: int = 0,
        use_clipboard: bool = False,
    ) -> OperationResult:
        """Replace a validated selection in the focused target."""
        transaction = self._transaction(expected_window)
        return transaction.replace_selection(
            replacement,
            use_clipboard=use_clipboard,
        )

    def capture_selection(
        self,
        *,
        expected_window: int = 0,
    ) -> SelectionSnapshot | None:
        """Read a bounded selection from the expected focused target."""
        transaction = self._transaction(expected_window)
        captured = transaction.capture_session(
            capability=TextCapability.READ_SELECTION,
            include_selection=True,
        )
        if captured.session is None:
            return None
        return captured.session.selection

    def replace_typed_text(
        self,
        text: str,
        *,
        backspace_count: int,
        expected_window: int = 0,
        expected_target: TargetSnapshot | None = None,
        trailing_text: str = "",
        use_clipboard: bool = False,
        caret_from_end: int = 0,
    ) -> OperationResult:
        """Replace a typed prefix after binding the expected target window
        (and, when given, the expected control: see :meth:`insert_text`)."""
        moved = self._moved_from(expected_target)
        if moved is not None:
            return moved
        transaction = self._transaction(expected_window, expected_target)
        return transaction.replace_typed_text(
            text,
            backspace_count=backspace_count,
            trailing_text=trailing_text,
            use_clipboard=use_clipboard,
            caret_from_end=caret_from_end,
        )

    def _moved_from(self, expected: TargetSnapshot | None) -> OperationResult | None:
        """A refusal when the control in front is not *expected*, else None.

        Asked once before the transaction so the reason is "the focus moved";
        the transaction's own probe enforces the same identity again at the
        moment of typing (:meth:`_transaction`).
        """
        if expected is None:
            return None
        try:
            current = self._target_probe()
        except Exception:  # noqa: BLE001 - "cannot tell" is never "same place"
            return OperationResult(
                OperationStatus.FAILED,
                ExternalTextReason.ADAPTER_UNAVAILABLE,
                "The focused target could not be inspected.",
            )
        if expected.same_identity(current):
            return None
        return OperationResult(
            OperationStatus.STALE,
            ExternalTextReason.STALE_TARGET,
            "The focused target is not the one the text was meant for.",
            target_id=expected.target_id,
        )

    def _transaction(
        self, expected_window: int, expected_target: TargetSnapshot | None = None
    ) -> TextTransaction:
        def probe_expected_window() -> TargetSnapshot:
            target = self._target_probe()
            moved = expected_target is not None and not expected_target.same_identity(target)
            if moved or (expected_window and target.window_handle != expected_window):
                return replace(
                    target,
                    target_id="",
                    state=TargetState.UNKNOWN,
                    capabilities=frozenset(),
                )
            return target

        return TextTransaction(
            probe_expected_window,
            self._selection_capture,
            clipboard=self._clipboard,
            send_text=self._send_text,
            send_backspaces=self._send_backspaces,
            send_paste=self._send_paste,
            move_caret=self._move_caret,
        )
