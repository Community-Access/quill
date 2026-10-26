"""UIA capture uses real identity and rejects protected, stale or moved controls."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from quill.core.studio_capture import CaptureTarget
from quill.platform.windows import screenshot_uia as uia


@pytest.fixture
def window():
    return CaptureTarget("window", "Fixture", (0, 0, 800, 600), 123, 456)


def element(**changes):
    values = dict(
        CurrentIsPassword=False,
        CurrentIsOffscreen=False,
        CurrentProcessId=456,
        CurrentBoundingRectangle=SimpleNamespace(left=10, top=20, right=100, bottom=60),
        CurrentName="Save",
        CurrentLocalizedControlType="button",
        GetRuntimeId=lambda: (42, 3),
    )
    values.update(changes)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    "changes",
    [{"CurrentIsPassword": True}, {"CurrentIsOffscreen": True}, {"CurrentProcessId": 999}],
)
def test_password_offscreen_and_wrong_process_are_not_capture_targets(window, changes):
    assert uia.snapshot(element(**changes), window) is None


def test_element_becomes_exact_capture_target(window):
    control = uia.snapshot(element(), window)
    target = control.target(window)
    assert target.kind == "element"
    assert target.bounds == (10, 20, 100, 60)
    assert target.element_id == (42, 3)
    assert target.reference_bounds == window.bounds


def test_control_changes_are_rejected(window, monkeypatch):
    from quill.platform.windows import studio_capture

    control = uia.snapshot(element(), window)
    monkeypatch.setattr(studio_capture, "window_target", lambda handle: window)
    monkeypatch.setattr(
        uia, "controls_for_window", lambda source: [replace(control, name="Delete")]
    )
    with pytest.raises(Exception, match="moved or changed"):
        uia.resolve_control(control.target(window))
