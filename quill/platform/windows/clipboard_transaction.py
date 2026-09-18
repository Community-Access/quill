"""Bounded clipboard borrowing for explicit external-text operations.

This module owns only operation-scoped clipboard state. It does not read a
clipboard manager's history and it does not require one to be running. A
sequence-number change between write and restore means another application may
own the clipboard, so restoration is refused rather than overwriting newer
content.

Windows-only, wx-free.
"""

from __future__ import annotations

import ctypes
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

__all__ = [
    "CF_UNICODETEXT",
    "ClipboardItem",
    "ClipboardOutcome",
    "ClipboardPort",
    "ClipboardSnapshot",
    "ClipboardStatus",
    "ClipboardTransaction",
    "WindowsClipboardPort",
]

CF_UNICODETEXT = 13
_DEFAULT_MAX_BYTES = 1024 * 1024
_DEFAULT_MAX_ATTEMPTS = 5
_DEFAULT_RETRY_DELAY_S = 0.02


class ClipboardStatus(StrEnum):
    """Outcome of one bounded clipboard transaction step."""

    READY = "ready"
    UNAVAILABLE = "unavailable"
    TOO_LARGE = "too_large"
    CHANGED = "changed"
    WRITTEN = "written"
    RESTORED = "restored"
    TIMEOUT = "timeout"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ClipboardItem:
    """One clipboard format captured as bounded bytes."""

    format_id: int
    data: bytes


@dataclass(frozen=True, slots=True)
class ClipboardSnapshot:
    """Clipboard formats and ownership facts captured at one instant."""

    items: tuple[ClipboardItem, ...]
    sequence_number: int
    owner: int = 0

    def item(self, format_id: int) -> ClipboardItem | None:
        """Return the captured item for *format_id*, if present."""
        return next((item for item in self.items if item.format_id == format_id), None)


@dataclass(frozen=True, slots=True)
class ClipboardOutcome:
    """Document-safe status for one clipboard transaction."""

    status: ClipboardStatus
    paste_completed: bool = False


class ClipboardPort(Protocol):
    """Small clipboard boundary used by the transaction and its tests."""

    def capture(self, format_ids: Sequence[int], *, max_bytes: int) -> ClipboardSnapshot | None:
        """Capture requested formats, or return None when unavailable."""
        ...

    def current_sequence(self) -> int:
        """Return the current OS clipboard sequence number."""
        ...

    def current_owner(self) -> int:
        """Return the current clipboard owner handle, when available."""
        ...

    def write(self, items: Sequence[ClipboardItem]) -> bool:
        """Replace clipboard contents with the supplied formats."""
        ...


class ClipboardTransaction:
    """Borrow the clipboard for one explicit paste and restore it safely."""

    def __init__(
        self,
        clipboard: ClipboardPort,
        *,
        format_ids: Sequence[int] = (CF_UNICODETEXT,),
        max_bytes: int = _DEFAULT_MAX_BYTES,
        timeout_s: float = 1.0,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
        retry_delay_s: float = _DEFAULT_RETRY_DELAY_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._clipboard = clipboard
        self._format_ids = tuple(int(format_id) for format_id in format_ids)
        self._max_bytes = max(0, int(max_bytes))
        self._timeout_s = max(0.0, float(timeout_s))
        self._max_attempts = max(1, int(max_attempts))
        self._retry_delay_s = max(0.0, float(retry_delay_s))
        self._clock = clock
        self._before: ClipboardSnapshot | None = None
        self._written_sequence: int | None = None
        self._written_owner: int | None = None
        self._started_at = 0.0

    @property
    def snapshot(self) -> ClipboardSnapshot | None:
        """The pre-operation snapshot, when capture succeeded."""
        return self._before

    @property
    def has_written(self) -> bool:
        """Whether this transaction may have replaced clipboard contents."""
        return self._written_sequence is not None

    def capture(self) -> ClipboardOutcome:
        """Capture the current clipboard before changing it."""
        self._started_at = self._clock()
        for attempt in range(self._max_attempts):
            snapshot = self._clipboard.capture(self._format_ids, max_bytes=self._max_bytes)
            if snapshot is not None:
                if self._expired():
                    return ClipboardOutcome(ClipboardStatus.TIMEOUT)
                self._before = snapshot
                self._written_sequence = None
                self._written_owner = None
                return ClipboardOutcome(ClipboardStatus.READY)
            if self._expired():
                return ClipboardOutcome(ClipboardStatus.TIMEOUT)
            if attempt + 1 < self._max_attempts:
                self._retry_sleep()
        return ClipboardOutcome(ClipboardStatus.UNAVAILABLE)

    def write_text(self, text: str) -> ClipboardOutcome:
        """Write bounded Unicode text after checking the captured sequence."""
        if self._before is None:
            captured = self.capture()
            if captured.status is not ClipboardStatus.READY:
                return captured
        if self._expired():
            return ClipboardOutcome(ClipboardStatus.TIMEOUT)
        encoded = _encode_unicode_text(text)
        if len(encoded) > self._max_bytes:
            return ClipboardOutcome(ClipboardStatus.TOO_LARGE)
        before = self._before
        if not self._sequence_matches(before):
            return ClipboardOutcome(ClipboardStatus.CHANGED)
        for attempt in range(self._max_attempts):
            if not self._clipboard.write((ClipboardItem(CF_UNICODETEXT, encoded),)):
                sequence = self._clipboard.current_sequence()
                if sequence > 0 and sequence != before.sequence_number:
                    self._written_sequence = sequence
                    self._written_owner = self._clipboard.current_owner()
                    return ClipboardOutcome(ClipboardStatus.FAILED)
                if self._expired():
                    return ClipboardOutcome(ClipboardStatus.TIMEOUT)
                if attempt + 1 < self._max_attempts:
                    self._retry_sleep()
                    continue
                return ClipboardOutcome(ClipboardStatus.FAILED)
            sequence = self._clipboard.current_sequence()
            if sequence <= 0:
                return ClipboardOutcome(ClipboardStatus.FAILED)
            self._written_sequence = sequence
            self._written_owner = self._clipboard.current_owner()
            return ClipboardOutcome(ClipboardStatus.WRITTEN)
        return ClipboardOutcome(ClipboardStatus.FAILED)

    def paste_and_restore(self, text: str, paste: Callable[[], bool]) -> ClipboardOutcome:
        """Write *text*, invoke one paste action, and safely restore state."""
        written = self.write_text(text)
        if written.status is not ClipboardStatus.WRITTEN:
            if self.has_written:
                restored = self.restore()
                if restored.status is not ClipboardStatus.RESTORED:
                    return restored
            return written
        try:
            paste_completed = bool(paste())
        except Exception:  # noqa: BLE001
            paste_completed = False
        timed_out = self._expired()
        restored = self.restore()
        if restored.status is not ClipboardStatus.RESTORED:
            return ClipboardOutcome(restored.status, paste_completed)
        if timed_out:
            return ClipboardOutcome(ClipboardStatus.TIMEOUT, paste_completed)
        if not paste_completed:
            return ClipboardOutcome(ClipboardStatus.FAILED)
        return ClipboardOutcome(ClipboardStatus.RESTORED, True)

    def restore(self) -> ClipboardOutcome:
        """Restore the original formats only if the transaction still owns it."""
        if self._before is None or self._written_sequence is None:
            return ClipboardOutcome(ClipboardStatus.UNAVAILABLE)
        if not self._written_state_matches():
            return ClipboardOutcome(ClipboardStatus.CHANGED)
        for attempt in range(self._max_attempts):
            if self._clipboard.write(self._before.items):
                return ClipboardOutcome(ClipboardStatus.RESTORED)
            if not self._written_state_matches():
                return ClipboardOutcome(ClipboardStatus.CHANGED)
            if attempt + 1 < self._max_attempts:
                self._retry_sleep()
        return ClipboardOutcome(ClipboardStatus.FAILED)

    def _sequence_matches(self, snapshot: ClipboardSnapshot | None) -> bool:
        if snapshot is None:
            return False
        current = self._clipboard.current_sequence()
        if current <= 0 or current != snapshot.sequence_number:
            return False
        if snapshot.owner:
            return self._clipboard.current_owner() == snapshot.owner
        return True

    def _written_state_matches(self) -> bool:
        current = self._clipboard.current_sequence()
        if current <= 0 or current != self._written_sequence:
            return False
        if self._written_owner:
            return self._clipboard.current_owner() == self._written_owner
        return True

    def _expired(self) -> bool:
        return self._clock() - self._started_at > self._timeout_s

    def _retry_sleep(self) -> None:
        if self._retry_delay_s > 0:
            time.sleep(self._retry_delay_s)


class WindowsClipboardPort:
    """Best-effort pywin32 clipboard port with bounded reads."""

    def capture(self, format_ids: Sequence[int], *, max_bytes: int) -> ClipboardSnapshot | None:
        try:
            import win32clipboard  # noqa: PLC0415 - optional Windows dependency
        except ImportError:
            return None

        start_sequence = _clipboard_sequence()
        owner = _clipboard_owner()
        items: list[ClipboardItem] = []
        total = 0
        try:
            win32clipboard.OpenClipboard()
            try:
                for format_id in format_ids:
                    if not win32clipboard.IsClipboardFormatAvailable(int(format_id)):
                        continue
                    value = win32clipboard.GetClipboardData(int(format_id))
                    data = _clipboard_value_bytes(int(format_id), value)
                    if data is None or len(data) > max_bytes - total:
                        return None
                    items.append(ClipboardItem(int(format_id), data))
                    total += len(data)
            finally:
                win32clipboard.CloseClipboard()
        except Exception:  # noqa: BLE001
            return None
        end_sequence = _clipboard_sequence()
        if start_sequence <= 0 or end_sequence <= 0 or start_sequence != end_sequence:
            return None
        return ClipboardSnapshot(tuple(items), end_sequence, owner)

    def current_sequence(self) -> int:
        return _clipboard_sequence()

    def current_owner(self) -> int:
        return _clipboard_owner()

    def write(self, items: Sequence[ClipboardItem]) -> bool:
        try:
            import win32clipboard  # noqa: PLC0415 - optional Windows dependency
        except ImportError:
            return False
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                for item in items:
                    value = _clipboard_value_for_write(item)
                    win32clipboard.SetClipboardData(item.format_id, value)
            finally:
                win32clipboard.CloseClipboard()
            return True
        except Exception:  # noqa: BLE001
            return False


def _clipboard_sequence() -> int:
    try:
        return int(ctypes.windll.user32.GetClipboardSequenceNumber())
    except Exception:  # noqa: BLE001
        return 0


def _clipboard_owner() -> int:
    try:
        return int(ctypes.windll.user32.GetClipboardOwner() or 0)
    except Exception:  # noqa: BLE001
        return 0


def _encode_unicode_text(text: str) -> bytes:
    return text.encode("utf-16-le") + b"\x00\x00"


def _clipboard_value_bytes(format_id: int, value: object) -> bytes | None:
    if format_id == CF_UNICODETEXT and isinstance(value, str):
        return _encode_unicode_text(value)
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    return None


def _clipboard_value_for_write(item: ClipboardItem) -> str | bytes:
    if item.format_id == CF_UNICODETEXT:
        return item.data.decode("utf-16-le").rstrip("\x00")
    return item.data
