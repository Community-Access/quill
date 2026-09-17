from __future__ import annotations

from quill.core.external_text import (
    ExternalTextReason,
    OperationStatus,
    SelectionSnapshot,
    TargetSnapshot,
    TargetState,
    TextCapability,
    TextReplacement,
)
from quill.platform.windows.text_injector import InjectionResult
from quill.platform.windows.text_runtime import InkwellTextRuntime


def _target() -> TargetSnapshot:
    return TargetSnapshot(
        target_id="target",
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


def _selection(target: TargetSnapshot) -> SelectionSnapshot:
    return SelectionSnapshot(
        source_target=target,
        selected_text="old",
        selection_start=0,
        selection_end=3,
        revision="1",
    )


def test_runtime_refuses_an_unexpected_window() -> None:
    delivered: list[str] = []
    erased: list[int] = []
    runtime = InkwellTextRuntime(
        target_probe=_target,
        send_text=lambda text: delivered.append(text) or InjectionResult(2, 2),
        send_backspaces=lambda count: erased.append(count) or InjectionResult(2, 2),
    )

    result = runtime.replace_typed_text("new", backspace_count=3, expected_window=99)

    assert result.status is OperationStatus.UNSUPPORTED
    assert result.reason is ExternalTextReason.NO_TARGET
    assert delivered == []
    assert erased == []


def test_runtime_replaces_selection_through_one_validated_service() -> None:
    target = _target()
    delivered: list[str] = []
    runtime = InkwellTextRuntime(
        target_probe=lambda: target,
        selection_capture=lambda _target: _selection(target),
        send_text=lambda text: delivered.append(text) or InjectionResult(6, 6),
    )

    result = runtime.replace_selection(
        TextReplacement(expected_source="old", replacement_text="new")
    )

    assert result.status is OperationStatus.APPLIED
    assert result.reason is ExternalTextReason.APPLIED
    assert delivered == ["new"]
