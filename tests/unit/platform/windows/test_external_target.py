from __future__ import annotations

import pytest

from quill.core.external_text import (
    CapabilityConfidence,
    CapabilityEvidence,
    TargetState,
    TextCapability,
)
from quill.platform.windows.external_target import (
    UIAElementSnapshot,
    probe_focused_target,
    snapshot_from_foreground,
)
from quill.platform.windows.foreground import ForegroundWindow


def _foreground(**overrides: object) -> ForegroundWindow:
    values: dict[str, object] = {
        "hwnd": 101,
        "process_name": "notepad.exe",
        "title": "Untitled - Notepad",
        "window_class": "Notepad",
        "process_id": 202,
    }
    values.update(overrides)
    return ForegroundWindow(**values)


def test_unknown_pane_and_custom_controls_are_not_editable() -> None:
    for control_type in (50008, 50033):
        snapshot = snapshot_from_foreground(
            _foreground(),
            element=UIAElementSnapshot(
                control_type=control_type,
                is_keyboard_focusable=True,
                class_name="WebViewHost",
            ),
        )

        assert snapshot.state is TargetState.UNKNOWN
        assert not snapshot.supports(TextCapability.INSERT_TEXT)
        assert not snapshot.supports(TextCapability.REPLACE_SELECTION)
        assert snapshot.confidence is CapabilityConfidence.UNKNOWN


def test_read_only_text_target_keeps_safe_read_capabilities() -> None:
    snapshot = snapshot_from_foreground(
        _foreground(),
        element=UIAElementSnapshot(
            control_type=50030,
            class_name="RichEdit",
            has_value_pattern=True,
            value_is_read_only=True,
            has_text_pattern=True,
            has_selection_pattern=True,
        ),
    )

    assert snapshot.state is TargetState.READ_ONLY
    assert snapshot.supports(TextCapability.READ_SELECTION)
    assert snapshot.supports(TextCapability.READ_CONTEXT)
    assert snapshot.supports(TextCapability.PLAIN_TEXT)
    assert not snapshot.supports(TextCapability.INSERT_TEXT)
    assert not snapshot.supports(TextCapability.REPLACE_SELECTION)


def test_known_native_edit_class_grants_only_native_baseline_capabilities() -> None:
    snapshot = snapshot_from_foreground(
        _foreground(window_class="Edit"),
        focused_control_class="Edit",
        captured_at=12.5,
    )

    assert snapshot.state is TargetState.SUPPORTED
    assert snapshot.family.value == "native_control"
    assert snapshot.confidence is CapabilityConfidence.ADVISORY
    assert CapabilityEvidence.NATIVE_CLASS in snapshot.evidence
    assert snapshot.supports(TextCapability.INSERT_TEXT)
    assert snapshot.supports(TextCapability.EXPAND_TRIGGER)
    assert snapshot.supports(TextCapability.PLAIN_TEXT)
    assert not snapshot.supports(TextCapability.READ_SELECTION)
    assert snapshot.captured_at == 12.5


def test_uia_edit_control_adds_positive_control_type_evidence() -> None:
    snapshot = snapshot_from_foreground(
        _foreground(),
        element=UIAElementSnapshot(
            control_type=50004,
            class_name="Edit",
            is_keyboard_focusable=True,
        ),
    )

    assert snapshot.state is TargetState.SUPPORTED
    assert CapabilityEvidence.UIA_CONTROL_TYPE in snapshot.evidence
    assert snapshot.supports(TextCapability.INSERT_TEXT)


def test_password_targets_are_protected_even_with_text_patterns() -> None:
    snapshot = snapshot_from_foreground(
        _foreground(title="Untitled"),
        element=UIAElementSnapshot(
            control_type=50004,
            class_name="Edit",
            is_password=True,
            has_value_pattern=True,
            has_text_pattern=True,
        ),
    )

    assert snapshot.state is TargetState.PROTECTED
    assert snapshot.protected
    assert not snapshot.capabilities


def test_elevated_target_without_matching_privilege_is_denied() -> None:
    snapshot = snapshot_from_foreground(
        _foreground(),
        element=UIAElementSnapshot(
            control_type=50004,
            class_name="Edit",
            has_value_pattern=True,
        ),
        target_elevated=True,
        own_process_elevated=False,
    )

    assert snapshot.state is TargetState.ELEVATED
    assert snapshot.privilege_match is False
    assert not snapshot.capabilities


def test_no_foreground_window_is_unknown() -> None:
    snapshot = snapshot_from_foreground(ForegroundWindow(), captured_at=4.0)

    assert snapshot.state is TargetState.UNKNOWN
    assert not snapshot.target_id
    assert not snapshot.capabilities


def test_live_probe_does_not_query_uia_for_denied_target(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.platform.windows.external_target as external_target

    monkeypatch.setattr(
        external_target, "foreground_window_info", lambda: _foreground(title="Sign in")
    )
    monkeypatch.setattr(external_target, "is_denied_target", lambda *_args: True)
    monkeypatch.setattr(external_target, "is_elevated_window", lambda _hwnd: False)
    monkeypatch.setattr(external_target, "capture_uia_focus", lambda: pytest.fail("UIA queried"))

    snapshot = probe_focused_target(clock=lambda: 8.0)

    assert snapshot.state is TargetState.DENIED
    assert snapshot.captured_at == 8.0
