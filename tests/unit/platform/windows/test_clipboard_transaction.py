from __future__ import annotations

from collections.abc import Sequence

from quill.platform.windows.clipboard_transaction import (
    CF_UNICODETEXT,
    ClipboardItem,
    ClipboardSnapshot,
    ClipboardStatus,
    ClipboardTransaction,
)


class FakeClipboard:
    def __init__(self) -> None:
        self.sequence = 7
        self.owner = 41
        self.items = (ClipboardItem(CF_UNICODETEXT, b"before\x00\x00"),)
        self.writes: list[tuple[ClipboardItem, ...]] = []

    def capture(self, format_ids: Sequence[int], *, max_bytes: int) -> ClipboardSnapshot | None:
        del format_ids, max_bytes
        return ClipboardSnapshot(self.items, self.sequence, owner=self.owner)

    def current_sequence(self) -> int:
        return self.sequence

    def current_owner(self) -> int:
        return self.owner

    def write(self, items: Sequence[ClipboardItem]) -> bool:
        written = tuple(items)
        self.writes.append(written)
        self.items = written
        self.sequence += 1
        return True


def test_paste_restores_original_clipboard_formats() -> None:
    clipboard = FakeClipboard()
    transaction = ClipboardTransaction(clipboard)

    outcome = transaction.paste_and_restore("replacement", lambda: True)

    assert outcome.status is ClipboardStatus.RESTORED
    assert outcome.paste_completed
    assert len(clipboard.writes) == 2
    assert clipboard.writes[0][0].format_id == CF_UNICODETEXT
    assert clipboard.writes[1] == (ClipboardItem(CF_UNICODETEXT, b"before\x00\x00"),)


def test_clipboard_change_before_write_aborts_without_mutation() -> None:
    clipboard = FakeClipboard()
    transaction = ClipboardTransaction(clipboard)
    assert transaction.capture().status is ClipboardStatus.READY

    clipboard.sequence += 1
    outcome = transaction.write_text("replacement")

    assert outcome.status is ClipboardStatus.CHANGED
    assert not clipboard.writes


def test_clipboard_change_after_paste_skips_restore() -> None:
    clipboard = FakeClipboard()
    transaction = ClipboardTransaction(clipboard)

    def paste_then_external_change() -> bool:
        clipboard.sequence += 1
        return True

    outcome = transaction.paste_and_restore("replacement", paste_then_external_change)

    assert outcome.status is ClipboardStatus.CHANGED
    assert outcome.paste_completed
    assert len(clipboard.writes) == 1


def test_failed_paste_still_restores_when_clipboard_is_ours() -> None:
    clipboard = FakeClipboard()
    transaction = ClipboardTransaction(clipboard)

    outcome = transaction.paste_and_restore("replacement", lambda: False)

    assert outcome.status is ClipboardStatus.FAILED
    assert not outcome.paste_completed
    assert len(clipboard.writes) == 2


def test_text_larger_than_bound_is_not_written() -> None:
    clipboard = FakeClipboard()
    transaction = ClipboardTransaction(clipboard, max_bytes=4)

    outcome = transaction.write_text("too large")

    assert outcome.status is ClipboardStatus.TOO_LARGE
    assert not clipboard.writes


def test_transient_capture_contention_is_retried() -> None:
    clipboard = FakeClipboard()
    attempts = 0

    def capture(format_ids: Sequence[int], *, max_bytes: int) -> ClipboardSnapshot | None:
        nonlocal attempts
        del format_ids, max_bytes
        attempts += 1
        if attempts < 3:
            return None
        return ClipboardSnapshot(clipboard.items, clipboard.sequence, clipboard.owner)

    clipboard.capture = capture  # type: ignore[method-assign]
    transaction = ClipboardTransaction(clipboard, max_attempts=3, retry_delay_s=0)

    outcome = transaction.capture()

    assert outcome.status is ClipboardStatus.READY
    assert attempts == 3


def test_owner_change_aborts_even_when_sequence_is_unchanged() -> None:
    clipboard = FakeClipboard()
    transaction = ClipboardTransaction(clipboard)
    assert transaction.capture().status is ClipboardStatus.READY

    clipboard.owner = 99
    outcome = transaction.write_text("replacement")

    assert outcome.status is ClipboardStatus.CHANGED
    assert not clipboard.writes
