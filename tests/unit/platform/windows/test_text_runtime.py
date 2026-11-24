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


# -- FUX-07: the control the text was meant for, captured at input start ---- #


def _other_field() -> TargetSnapshot:
    """The same window and program, but the focus is on a different field."""
    from dataclasses import replace

    return replace(_target(), target_id="other", control_id="hwnd:303")


def _recording_runtime(probe: object) -> tuple[InkwellTextRuntime, list[str], list[int]]:
    delivered: list[str] = []
    erased: list[int] = []
    runtime = InkwellTextRuntime(
        target_probe=probe,  # type: ignore[arg-type]
        send_text=lambda text: delivered.append(text) or InjectionResult(2, 2),
        send_backspaces=lambda count: erased.append(count) or InjectionResult(2, 2),
    )
    return runtime, delivered, erased


def test_runtime_types_nothing_into_another_field_of_the_same_window() -> None:
    runtime, delivered, erased = _recording_runtime(_other_field)

    result = runtime.replace_typed_text(
        "new", backspace_count=3, expected_window=11, expected_target=_target()
    )

    assert result.status is OperationStatus.STALE
    assert result.reason is ExternalTextReason.STALE_TARGET
    assert delivered == []
    assert erased == []


def test_runtime_types_into_the_field_the_text_was_meant_for() -> None:
    runtime, delivered, _erased = _recording_runtime(_target)

    result = runtime.insert_text("new", expected_target=_target())

    assert result.status is OperationStatus.APPLIED
    assert delivered == ["new"]


def test_runtime_refuses_the_same_window_after_its_program_restarted() -> None:
    from dataclasses import replace

    restarted = replace(_target(), process_id=23)
    runtime, delivered, _erased = _recording_runtime(lambda: restarted)

    result = runtime.insert_text("new", expected_target=_target())

    assert result.status is OperationStatus.STALE
    assert delivered == []


def test_runtime_rechecks_the_field_at_the_moment_of_typing() -> None:
    """The focus moves after the first check: the transaction's own probe sees
    it and nothing is typed."""
    seen = iter([_target(), _target(), _other_field(), _other_field()])
    runtime, delivered, erased = _recording_runtime(lambda: next(seen))

    result = runtime.replace_typed_text("new", backspace_count=2, expected_target=_target())

    assert result.status is not OperationStatus.APPLIED
    assert delivered == []
    assert erased == []


def test_runtime_unreadable_focus_is_never_the_same_field() -> None:
    def probe() -> TargetSnapshot:
        raise OSError("no automation")

    runtime, delivered, _erased = _recording_runtime(probe)

    result = runtime.insert_text("new", expected_target=_target())

    assert result.status is OperationStatus.FAILED
    assert result.reason is ExternalTextReason.ADAPTER_UNAVAILABLE
    assert delivered == []
