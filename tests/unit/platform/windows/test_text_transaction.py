from __future__ import annotations

from collections.abc import Sequence

from quill.core.external_text import (
    ExternalTextReason,
    OperationStatus,
    SelectionSnapshot,
    TargetSnapshot,
    TargetState,
    TextCapability,
    TextReplacement,
)
from quill.platform.windows.clipboard_transaction import (
    CF_UNICODETEXT,
    ClipboardItem,
    ClipboardSnapshot,
)
from quill.platform.windows.text_injector import InjectionResult
from quill.platform.windows.text_transaction import TextTransaction


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class FakeClipboard:
    def __init__(self, *, change_after_capture: bool = False) -> None:
        self.sequence = 7
        self.owner = 41
        self.items = (ClipboardItem(CF_UNICODETEXT, b"before\x00\x00"),)
        self.writes: list[tuple[ClipboardItem, ...]] = []
        self.change_after_capture = change_after_capture

    def capture(self, format_ids: Sequence[int], *, max_bytes: int) -> ClipboardSnapshot | None:
        del format_ids, max_bytes
        snapshot = ClipboardSnapshot(self.items, self.sequence, self.owner)
        if self.change_after_capture:
            self.sequence += 1
        return snapshot

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


def _target(*, target_id: str = "target") -> TargetSnapshot:
    return TargetSnapshot(
        target_id=target_id,
        window_handle=11,
        process_id=22,
        control_id="class:edit",
        state=TargetState.SUPPORTED,
        privilege_match=True,
        capabilities=frozenset({
            TextCapability.INSERT_TEXT,
            TextCapability.REPLACE_SELECTION,
        }),
    )


def _selection(target: TargetSnapshot, text: str, *, revision: str = "1") -> SelectionSnapshot:
    return SelectionSnapshot(
        source_target=target,
        selected_text=text,
        full_text="prefix " + text,
        selection_start=7,
        selection_end=7 + len(text),
        caret_position=7 + len(text),
        revision=revision,
    )


def test_insert_aborts_when_focus_changes_before_mutation() -> None:
    first = _target()
    second = _target(target_id="other")
    calls = iter((first, second))
    delivered: list[str] = []

    transaction = TextTransaction(
        lambda: next(calls),
        send_text=lambda text: delivered.append(text) or InjectionResult(2, 2),
    )

    result = transaction.insert_text("new")

    assert result.status is OperationStatus.STALE
    assert result.reason is ExternalTextReason.STALE_TARGET
    assert not delivered


def test_typed_prefix_replacement_deletes_then_types_one_payload() -> None:
    target = _target()
    events: list[tuple[str, object]] = []

    transaction = TextTransaction(
        lambda: target,
        send_backspaces=lambda count: events.append(("backspaces", count)) or InjectionResult(4, 4),
        send_text=lambda text: events.append(("text", text)) or InjectionResult(8, 8),
        move_caret=lambda steps: events.append(("caret", steps)) or InjectionResult(2, 2),
    )

    result = transaction.replace_typed_text(
        "replacement",
        backspace_count=3,
        trailing_text=". ",
        caret_from_end=4,
    )

    assert result.status is OperationStatus.APPLIED
    assert events == [("backspaces", 3), ("text", "replacement. "), ("caret", 6)]


def test_typed_prefix_replacement_stops_after_partial_deletion() -> None:
    target = _target()
    typed: list[str] = []

    transaction = TextTransaction(
        lambda: target,
        send_backspaces=lambda _count: InjectionResult(4, 2),
        send_text=lambda text: typed.append(text) or InjectionResult(2, 2),
    )

    result = transaction.replace_typed_text("replacement", backspace_count=3)

    assert result.status is OperationStatus.FAILED
    assert result.reason is ExternalTextReason.PARTIAL_INJECTION
    assert typed == []


def test_replace_aborts_when_source_text_changes() -> None:
    target = _target()
    selections = iter((_selection(target, "old"), _selection(target, "new")))
    delivered: list[str] = []

    transaction = TextTransaction(
        lambda: target,
        lambda _target: next(selections),
        send_text=lambda text: delivered.append(text) or InjectionResult(2, 2),
    )

    result = transaction.replace_selection(
        TextReplacement(expected_source="old", replacement_text="new")
    )

    assert result.status is OperationStatus.STALE
    assert result.reason is ExternalTextReason.SOURCE_CHANGED
    assert not delivered


def test_partial_send_input_is_reported_without_clipboard_retry() -> None:
    target = _target()
    delivered: list[str] = []

    transaction = TextTransaction(
        lambda: target,
        send_text=lambda text: delivered.append(text) or InjectionResult(4, 2),
    )

    result = transaction.insert_text("new")

    assert result.status is OperationStatus.FAILED
    assert result.reason is ExternalTextReason.PARTIAL_INJECTION
    assert delivered == ["new"]


def test_clipboard_contention_aborts_before_paste() -> None:
    target = _target()
    clipboard = FakeClipboard(change_after_capture=True)
    pasted: list[bool] = []

    transaction = TextTransaction(
        lambda: target,
        clipboard=clipboard,
        send_paste=lambda: pasted.append(True) or InjectionResult(4, 4),
    )

    result = transaction.insert_text("new", use_clipboard=True)

    assert result.status is OperationStatus.STALE
    assert result.reason is ExternalTextReason.CLIPBOARD_CHANGED
    assert not pasted
    assert not clipboard.writes


def test_clipboard_fallback_pastes_and_restores() -> None:
    target = _target()
    clipboard = FakeClipboard()
    pasted: list[bool] = []

    transaction = TextTransaction(
        lambda: target,
        clipboard=clipboard,
        send_paste=lambda: pasted.append(True) or InjectionResult(4, 4),
    )

    result = transaction.insert_text("new", use_clipboard=True)

    assert result.status is OperationStatus.APPLIED
    assert result.fallback == "clipboard"
    assert pasted == [True]
    assert len(clipboard.writes) == 2
    assert clipboard.writes[-1] == (ClipboardItem(CF_UNICODETEXT, b"before\x00\x00"),)


def test_timeout_aborts_before_input() -> None:
    target = _target()
    clock = FakeClock()
    calls = 0
    delivered: list[str] = []

    def probe() -> TargetSnapshot:
        nonlocal calls
        calls += 1
        if calls == 2:
            clock.value = 2.0
        return target

    transaction = TextTransaction(
        probe,
        send_text=lambda text: delivered.append(text) or InjectionResult(2, 2),
        clock=clock,
        timeout_s=1.0,
    )

    result = transaction.insert_text("new")

    assert result.status is OperationStatus.TIMEOUT
    assert result.reason is ExternalTextReason.TIMEOUT
    assert not delivered
