"""Fail-closed transactions for editing text in external Windows targets.

A target probe is advisory until this module captures a session and revalidates
it immediately before mutation. Selection text is treated as a compare-before-
write value. The transaction never logs document text and never falls back from
a partial keyboard injection, because a partial write may already have changed
the target.

Windows-only, wx-free.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

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
from quill.platform.windows.clipboard_transaction import (
    ClipboardOutcome,
    ClipboardPort,
    ClipboardStatus,
    ClipboardTransaction,
    WindowsClipboardPort,
)
from quill.platform.windows.text_injector import (
    InjectionResult,
    move_caret_left_checked,
    send_backspaces_checked,
    send_paste_checked,
    send_text_checked,
)

__all__ = [
    "SelectionCapture",
    "TargetProbe",
    "TextSession",
    "TextSessionCapture",
    "TextTransaction",
]

_DEFAULT_TIMEOUT_S = 1.0


class TargetProbe(Protocol):
    """Callable boundary for capturing the focused target."""

    def __call__(self) -> TargetSnapshot:
        """Return the current target snapshot."""
        ...


class SelectionCapture(Protocol):
    """Callable boundary for capturing text from one target."""

    def __call__(self, target: TargetSnapshot) -> SelectionSnapshot | None:
        """Return a bounded selection snapshot for *target*."""
        ...


@dataclass(frozen=True, slots=True)
class TextSession:
    """The target and optional selection captured before an operation."""

    target: TargetSnapshot
    selection: SelectionSnapshot | None = None


@dataclass(frozen=True, slots=True)
class TextSessionCapture:
    """Result of capturing a target session without raising platform errors."""

    session: TextSession | None
    result: OperationResult | None = None


class TextTransaction:
    """Capture, revalidate, and perform one external text operation."""

    def __init__(
        self,
        target_probe: TargetProbe,
        selection_capture: SelectionCapture | None = None,
        *,
        clipboard: ClipboardPort | None = None,
        send_text: Callable[[str], InjectionResult] = send_text_checked,
        send_backspaces: Callable[[int], InjectionResult] = send_backspaces_checked,
        send_paste: Callable[[], InjectionResult] = send_paste_checked,
        move_caret: Callable[[int], InjectionResult] = move_caret_left_checked,
        clock: Callable[[], float] = time.monotonic,
        timeout_s: float = _DEFAULT_TIMEOUT_S,
    ) -> None:
        self._target_probe = target_probe
        self._selection_capture = selection_capture
        self._clipboard = clipboard
        self._send_text = send_text
        self._send_backspaces = send_backspaces
        self._send_paste = send_paste
        self._move_caret = move_caret
        self._clock = clock
        self._timeout_s = max(0.0, float(timeout_s))
        self._started_at = 0.0

    def capture_session(
        self,
        *,
        capability: TextCapability,
        include_selection: bool = False,
    ) -> TextSessionCapture:
        """Capture and validate a target before any external mutation."""
        self._started_at = self._clock()
        try:
            target = self._target_probe()
        except Exception:  # noqa: BLE001
            return TextSessionCapture(
                None,
                self._result(
                    OperationStatus.FAILED,
                    ExternalTextReason.ADAPTER_UNAVAILABLE,
                    "The focused target could not be inspected.",
                    capability=capability,
                ),
            )

        problem = self._target_policy_result(target, capability)
        if problem is not None:
            return TextSessionCapture(None, problem)
        if self._expired():
            return TextSessionCapture(
                None,
                self._timeout_result(target, capability),
            )

        selection = None
        if include_selection:
            selection_result = self._capture_selection(target, capability)
            if isinstance(selection_result, OperationResult):
                return TextSessionCapture(None, selection_result)
            selection = selection_result
        return TextSessionCapture(TextSession(target, selection))

    def insert_text(
        self,
        text: str,
        *,
        use_clipboard: bool = False,
        caret_from_end: int = 0,
    ) -> OperationResult:
        """Insert *text* at a validated external caret."""
        captured = self.capture_session(capability=TextCapability.INSERT_TEXT)
        if captured.session is None:
            return captured.result or self._generic_failure()
        session = captured.session
        problem = self._revalidate(session, TextCapability.INSERT_TEXT)
        if problem is not None:
            return problem
        return self._deliver(
            session,
            text,
            capability=TextCapability.INSERT_TEXT,
            use_clipboard=use_clipboard,
            caret_from_end=max(0, int(caret_from_end)),
        )

    def replace_selection(
        self,
        replacement: TextReplacement,
        *,
        use_clipboard: bool = False,
    ) -> OperationResult:
        """Replace one captured selection after compare-before-write checks."""
        captured = self.capture_session(
            capability=TextCapability.REPLACE_SELECTION,
            include_selection=True,
        )
        if captured.session is None:
            return captured.result or self._generic_failure()
        session = captured.session
        if session.selection is None:
            return self._result(
                OperationStatus.UNSUPPORTED,
                ExternalTextReason.NO_CAPABILITY,
                "The target did not provide a selection.",
                target=session.target,
                capability=TextCapability.REPLACE_SELECTION,
            )

        problem = self._validate_selection(
            session.selection,
            session.target,
            replacement.expected_source,
            capability=TextCapability.REPLACE_SELECTION,
        )
        if problem is not None:
            return problem
        problem = self._revalidate(
            session,
            TextCapability.REPLACE_SELECTION,
            expected_source=replacement.expected_source,
            selection_before=session.selection,
        )
        if problem is not None:
            return problem
        return self._deliver(
            session,
            replacement.replacement_text,
            capability=TextCapability.REPLACE_SELECTION,
            use_clipboard=use_clipboard,
            operation_message="Selection replaced.",
            affected_characters=len(replacement.replacement_text),
            expected_source=replacement.expected_source,
            selection_before=session.selection,
        )

    def replace_typed_text(
        self,
        text: str,
        *,
        backspace_count: int,
        trailing_text: str = "",
        use_clipboard: bool = False,
        caret_from_end: int = 0,
    ) -> OperationResult:
        """Replace a just-typed prefix in one target-bound operation."""
        captured = self.capture_session(capability=TextCapability.INSERT_TEXT)
        if captured.session is None:
            return captured.result or self._generic_failure()
        session = captured.session
        problem = self._revalidate(session, TextCapability.INSERT_TEXT)
        if problem is not None:
            return problem
        return self._deliver(
            session,
            text,
            capability=TextCapability.INSERT_TEXT,
            use_clipboard=use_clipboard,
            trailing_text=trailing_text,
            backspace_count=max(0, int(backspace_count)),
            caret_from_end=max(0, int(caret_from_end)),
        )

    def _capture_selection(
        self, target: TargetSnapshot, capability: TextCapability
    ) -> SelectionSnapshot | OperationResult:
        if self._selection_capture is None:
            return self._result(
                OperationStatus.UNSUPPORTED,
                ExternalTextReason.ADAPTER_UNAVAILABLE,
                "The target has no selection reader.",
                target=target,
                capability=capability,
            )
        try:
            selection = self._selection_capture(target)
        except Exception:  # noqa: BLE001
            return self._result(
                OperationStatus.FAILED,
                ExternalTextReason.ADAPTER_UNAVAILABLE,
                "The target selection could not be inspected.",
                target=target,
                capability=capability,
            )
        if selection is None:
            return self._result(
                OperationStatus.UNSUPPORTED,
                ExternalTextReason.NO_CAPABILITY,
                "The target did not provide a readable selection.",
                target=target,
                capability=capability,
            )
        if not selection.belongs_to(target):
            return self._result(
                OperationStatus.STALE,
                ExternalTextReason.STALE_TARGET,
                "The selection belongs to a different focused target.",
                target=target,
                capability=capability,
            )
        if self._expired():
            return self._timeout_result(target, capability)
        return selection

    def _revalidate(
        self,
        session: TextSession,
        capability: TextCapability,
        *,
        expected_source: str | None = None,
        selection_before: SelectionSnapshot | None = None,
    ) -> OperationResult | None:
        try:
            current_target = self._target_probe()
        except Exception:  # noqa: BLE001
            return self._result(
                OperationStatus.FAILED,
                ExternalTextReason.ADAPTER_UNAVAILABLE,
                "The focused target could not be revalidated.",
                target=session.target,
                capability=capability,
            )
        if not session.target.same_identity(current_target):
            return self._result(
                OperationStatus.STALE,
                ExternalTextReason.STALE_TARGET,
                "The focused target changed before the operation could be applied.",
                target=session.target,
                capability=capability,
            )
        problem = self._target_policy_result(current_target, capability)
        if problem is not None:
            return problem
        if selection_before is not None and expected_source is not None:
            current_selection = self._capture_selection(current_target, capability)
            if isinstance(current_selection, OperationResult):
                return current_selection
            problem = self._validate_selection(
                current_selection,
                current_target,
                expected_source,
                capability=capability,
                previous=selection_before,
            )
            if problem is not None:
                return problem
        if self._expired():
            return self._timeout_result(current_target, capability)
        return None

    def _deliver(
        self,
        session: TextSession,
        text: str,
        *,
        capability: TextCapability,
        use_clipboard: bool,
        operation_message: str = "Text inserted.",
        affected_characters: int | None = None,
        expected_source: str | None = None,
        selection_before: SelectionSnapshot | None = None,
        caret_from_end: int = 0,
        backspace_count: int = 0,
        trailing_text: str = "",
    ) -> OperationResult:
        payload = text + trailing_text
        affected = len(payload) if affected_characters is None else affected_characters
        if not use_clipboard:
            erased = self._send_backspaces(backspace_count)
            if not erased.complete:
                return self._result(
                    OperationStatus.FAILED,
                    ExternalTextReason.PARTIAL_INJECTION,
                    "Only part of the keyboard input was delivered.",
                    target=session.target,
                    capability=capability,
                )
            if self._expired():
                return self._timeout_result(session.target, capability, affected)
            injection = self._send_text(payload)
            if not injection.complete:
                return self._result(
                    OperationStatus.FAILED,
                    ExternalTextReason.PARTIAL_INJECTION,
                    "Only part of the keyboard input was delivered.",
                    target=session.target,
                    capability=capability,
                )
            if caret_from_end:
                caret_move = self._move_caret(caret_from_end + len(trailing_text))
                if not caret_move.complete:
                    return self._result(
                        OperationStatus.FAILED,
                        ExternalTextReason.PARTIAL_INJECTION,
                        "Only part of the caret movement was delivered.",
                        target=session.target,
                        capability=capability,
                    )
            if self._expired():
                return self._timeout_result(session.target, capability, affected)
            return self._result(
                OperationStatus.APPLIED,
                ExternalTextReason.APPLIED,
                operation_message,
                target=session.target,
                capability=capability,
                affected_characters=affected,
            )

        clipboard = self._clipboard or WindowsClipboardPort()
        clipboard_transaction = ClipboardTransaction(
            clipboard,
            clock=self._clock,
            timeout_s=self._timeout_s,
        )
        captured = clipboard_transaction.capture()
        problem = self._clipboard_problem(
            captured,
            target=session.target,
            capability=capability,
        )
        if problem is not None:
            return problem

        problem = self._revalidate(
            session,
            capability,
            expected_source=expected_source,
            selection_before=selection_before,
        )
        if problem is not None:
            return self._restore_or_return(clipboard_transaction, problem)

        erased = self._send_backspaces(backspace_count)
        if not erased.complete:
            return self._result(
                OperationStatus.FAILED,
                ExternalTextReason.PARTIAL_INJECTION,
                "Only part of the keyboard input was delivered.",
                target=session.target,
                capability=capability,
                fallback="clipboard",
            )
        if self._expired():
            return self._timeout_result(
                session.target,
                capability,
                affected,
                fallback="clipboard",
            )

        problem = self._revalidate(
            session,
            capability,
            expected_source=expected_source,
            selection_before=selection_before,
        )
        if problem is not None:
            return self._restore_or_return(clipboard_transaction, problem)

        written = clipboard_transaction.write_text(payload)
        problem = self._clipboard_problem(
            written,
            target=session.target,
            capability=capability,
        )
        if problem is not None:
            return self._restore_or_return(clipboard_transaction, problem)

        problem = self._revalidate(
            session,
            capability,
            expected_source=expected_source,
            selection_before=selection_before,
        )
        if problem is not None:
            return self._restore_or_return(clipboard_transaction, problem)

        try:
            injection = self._send_paste()
        except Exception:  # noqa: BLE001
            injection = InjectionResult(4, 0)
        caret_move = InjectionResult(0, 0)
        if injection.complete and caret_from_end:
            try:
                caret_move = self._move_caret(caret_from_end + len(trailing_text))
            except Exception:  # noqa: BLE001
                caret_move = InjectionResult(1, 0)
        restored = clipboard_transaction.restore()
        restore_problem = self._clipboard_problem(
            restored,
            target=session.target,
            capability=capability,
        )
        if restore_problem is not None:
            return restore_problem
        if not injection.complete:
            return self._result(
                OperationStatus.FAILED,
                ExternalTextReason.PARTIAL_INJECTION,
                "Only part of the paste keyboard input was delivered.",
                target=session.target,
                capability=capability,
                fallback="clipboard",
            )
        if not caret_move.complete:
            return self._result(
                OperationStatus.FAILED,
                ExternalTextReason.PARTIAL_INJECTION,
                "Only part of the caret movement was delivered.",
                target=session.target,
                capability=capability,
                fallback="clipboard",
            )
        if self._expired():
            return self._timeout_result(
                session.target,
                capability,
                affected,
                fallback="clipboard",
            )
        return self._result(
            OperationStatus.APPLIED,
            ExternalTextReason.APPLIED,
            operation_message,
            target=session.target,
            capability=capability,
            fallback="clipboard",
            affected_characters=affected,
        )

    def _validate_selection(
        self,
        selection: SelectionSnapshot,
        target: TargetSnapshot,
        expected_source: str,
        *,
        capability: TextCapability,
        previous: SelectionSnapshot | None = None,
    ) -> OperationResult | None:
        if not selection.belongs_to(target):
            return self._result(
                OperationStatus.STALE,
                ExternalTextReason.SELECTION_CHANGED,
                "The selection changed before the operation could be applied.",
                target=target,
                capability=capability,
            )
        if selection.selected_text is None:
            return self._result(
                OperationStatus.UNSUPPORTED,
                ExternalTextReason.NO_CAPABILITY,
                "The target did not provide selected text.",
                target=target,
                capability=capability,
            )
        if selection.selected_text != expected_source:
            return self._result(
                OperationStatus.STALE,
                ExternalTextReason.SOURCE_CHANGED,
                "The selected source text changed before the operation could be applied.",
                target=target,
                capability=capability,
            )
        if previous is not None and self._selection_revision_changed(previous, selection):
            return self._result(
                OperationStatus.STALE,
                ExternalTextReason.SELECTION_CHANGED,
                "The selection changed before the operation could be applied.",
                target=target,
                capability=capability,
            )
        return None

    @staticmethod
    def _selection_revision_changed(
        previous: SelectionSnapshot, current: SelectionSnapshot
    ) -> bool:
        if (
            previous.selection_start != current.selection_start
            or previous.selection_end != current.selection_end
            or previous.caret_position != current.caret_position
        ):
            return True
        if previous.revision and current.revision and previous.revision != current.revision:
            return True
        if previous.full_text is not None and current.full_text is not None:
            return previous.full_text != current.full_text
        return False

    def _target_policy_result(
        self, target: TargetSnapshot, capability: TextCapability
    ) -> OperationResult | None:
        if not target.target_id:
            return self._result(
                OperationStatus.UNSUPPORTED,
                ExternalTextReason.NO_TARGET,
                "No focused text target was found.",
                target=target,
                capability=capability,
            )
        if target.privilege_match is False or target.state == TargetState.ELEVATED:
            return self._result(
                OperationStatus.DENIED,
                ExternalTextReason.ELEVATED_TARGET,
                "The focused application requires matching privilege.",
                target=target,
                capability=capability,
            )
        if target.state == TargetState.DENIED:
            return self._result(
                OperationStatus.DENIED,
                ExternalTextReason.DENIED_TARGET,
                "This focused target is protected by policy.",
                target=target,
                capability=capability,
            )
        if target.state == TargetState.PROTECTED or target.protected:
            return self._result(
                OperationStatus.PROTECTED,
                ExternalTextReason.PROTECTED_TARGET,
                "This focused target cannot be edited by Inkwell.",
                target=target,
                capability=capability,
            )
        if target.state == TargetState.READ_ONLY:
            if target.supports(capability):
                return None
            return self._result(
                OperationStatus.UNSUPPORTED,
                ExternalTextReason.READ_ONLY,
                "The focused target is read-only.",
                target=target,
                capability=capability,
            )
        if target.state == TargetState.UNKNOWN:
            return self._result(
                OperationStatus.UNSUPPORTED,
                ExternalTextReason.UNKNOWN_TARGET,
                "The focused target could not prove the requested capability.",
                target=target,
                capability=capability,
            )
        if target.state != TargetState.SUPPORTED or not target.supports(capability):
            return self._result(
                OperationStatus.UNSUPPORTED,
                ExternalTextReason.NO_CAPABILITY,
                "The focused target does not support this text operation.",
                target=target,
                capability=capability,
            )
        return None

    def _clipboard_problem(
        self,
        outcome: ClipboardOutcome,
        *,
        target: TargetSnapshot,
        capability: TextCapability,
    ) -> OperationResult | None:
        messages = {
            ClipboardStatus.UNAVAILABLE: (
                OperationStatus.FAILED,
                ExternalTextReason.ADAPTER_UNAVAILABLE,
                "The clipboard could not be used for this operation.",
            ),
            ClipboardStatus.TOO_LARGE: (
                OperationStatus.FAILED,
                ExternalTextReason.FAILED,
                "The replacement text exceeds the clipboard transaction limit.",
            ),
            ClipboardStatus.CHANGED: (
                OperationStatus.STALE,
                ExternalTextReason.CLIPBOARD_CHANGED,
                "The clipboard changed during the operation; newer contents were preserved.",
            ),
            ClipboardStatus.TIMEOUT: (
                OperationStatus.TIMEOUT,
                ExternalTextReason.TIMEOUT,
                "The clipboard operation exceeded its time limit.",
            ),
            ClipboardStatus.FAILED: (
                OperationStatus.FAILED,
                ExternalTextReason.FAILED,
                "The clipboard operation failed before it completed.",
            ),
        }
        message = messages.get(outcome.status)
        if message is None:
            return None
        status, reason, text = message
        return self._result(
            status,
            reason,
            text,
            target=target,
            capability=capability,
            fallback="clipboard",
        )

    def _restore_or_return(
        self,
        clipboard_transaction: ClipboardTransaction,
        problem: OperationResult,
    ) -> OperationResult:
        if not clipboard_transaction.has_written:
            return problem
        restored = clipboard_transaction.restore()
        if restored.status is ClipboardStatus.CHANGED:
            return self._result(
                OperationStatus.STALE,
                ExternalTextReason.CLIPBOARD_CHANGED,
                "The clipboard changed during the operation; newer contents were preserved.",
                target_id=problem.target_id,
                capability=problem.capability,
                fallback="clipboard",
            )
        if restored.status is not ClipboardStatus.RESTORED:
            return self._result(
                OperationStatus.FAILED,
                ExternalTextReason.FAILED,
                "The operation stopped and the clipboard could not be restored.",
                target_id=problem.target_id,
                capability=problem.capability,
                fallback="clipboard",
            )
        return problem

    def _result(
        self,
        status: OperationStatus,
        reason: ExternalTextReason,
        message: str,
        *,
        target: TargetSnapshot | None = None,
        target_id: str | None = None,
        capability: TextCapability | None = None,
        fallback: str | None = None,
        affected_characters: int = 0,
    ) -> OperationResult:
        return OperationResult(
            status=status,
            reason=reason,
            message=message,
            target_id=target_id if target_id is not None else (target.target_id if target else ""),
            capability=capability,
            fallback=fallback,
            affected_characters=affected_characters,
        )

    def _timeout_result(
        self,
        target: TargetSnapshot,
        capability: TextCapability,
        affected_characters: int = 0,
        *,
        fallback: str | None = None,
    ) -> OperationResult:
        return self._result(
            OperationStatus.TIMEOUT,
            ExternalTextReason.TIMEOUT,
            "The text operation exceeded its time limit.",
            target=target,
            capability=capability,
            fallback=fallback,
            affected_characters=affected_characters,
        )

    def _expired(self) -> bool:
        return self._clock() - self._started_at > self._timeout_s

    def _generic_failure(self) -> OperationResult:
        return self._result(
            OperationStatus.FAILED,
            ExternalTextReason.FAILED,
            "The text operation failed.",
        )
