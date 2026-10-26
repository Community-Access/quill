"""Named selection must never silently broaden a capture or accept stale identity."""

from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image, ImageGrab

from quill.core.studio_capture import CaptureTarget, validate_region
from quill.platform.windows import studio_capture as capture
from quill.platform.windows.screen_capture import ScreenCaptureError


@pytest.fixture
def displays(monkeypatch):
    targets = [
        CaptureTarget("display", "Left display", (-1920, 0, 0, 1080), device="left"),
        CaptureTarget("display", "Primary", (0, 0, 1920, 1080), device="primary"),
    ]
    monkeypatch.setattr(capture, "display_targets", lambda: targets)
    return targets


def test_desktop_covers_negative_monitor_coordinates(displays):
    assert capture.desktop_target(displays).bounds == (-1920, 0, 1920, 1080)


def test_disconnected_display_fails_instead_of_capturing_desktop(displays):
    with pytest.raises(ScreenCaptureError, match="disconnected"):
        capture.resolve_target(CaptureTarget("display", "Gone", (0, 0, 2, 2), device="gone"))


def test_changed_desktop_topology_requires_review(displays):
    requested = capture.desktop_target(displays)
    displays[0] = replace(displays[0], device="different-physical-display")
    with pytest.raises(ScreenCaptureError, match="layout changed"):
        capture.resolve_target(requested)


def test_recycled_window_handle_fails(displays, monkeypatch):
    target = CaptureTarget("window", "Intended", (0, 0, 10, 10), 123, 50)
    monkeypatch.setattr(capture, "window_target", lambda handle: replace(target, process_id=60))
    with pytest.raises(ScreenCaptureError, match="identity changed"):
        capture.resolve_target(target)


@pytest.mark.parametrize("bounds", [(0, 0, 0, 10), (-20, 0, 10, 10), (0, 0, 11, 10)])
def test_invalid_region_is_rejected(bounds):
    with pytest.raises(ValueError):
        validate_region(bounds, (0, 0, 10, 10))


def test_region_can_start_on_negative_display():
    validate_region((-100, -50, 100, 100), (-1920, -1080, 1920, 1080))


def test_named_window_uses_window_backend_not_desktop(tmp_path, monkeypatch):
    from contextlib import nullcontext

    target = CaptureTarget("window", "Window: Editor", (0, 0, 20, 30), 123, 50)
    monkeypatch.setattr(capture, "physical_pixels", nullcontext)
    monkeypatch.setattr(capture, "resolve_target", lambda requested: target)
    monkeypatch.setattr(capture, "window_target", lambda handle: target)
    seen = []

    def grab(**kwargs):
        seen.append(kwargs)
        return Image.new("RGB", (20, 30), "white")

    monkeypatch.setattr(ImageGrab, "grab", grab)
    evidence = capture.capture_target(tmp_path, target)
    assert seen == [{"window": 123}]
    assert evidence.metadata["window_handle"] == 123
    assert evidence.metadata["uniform_pixels"] is True
    assert Path(evidence.path).is_file()


def test_closed_window_fails_without_grabbing(tmp_path, monkeypatch):
    from contextlib import nullcontext

    monkeypatch.setattr(capture, "physical_pixels", nullcontext)

    def missing(requested):
        raise ScreenCaptureError("The selected window is closed")

    monkeypatch.setattr(capture, "resolve_target", missing)
    monkeypatch.setattr(ImageGrab, "grab", lambda **k: pytest.fail("Grabbed a different target"))
    with pytest.raises(ScreenCaptureError, match="closed"):
        capture.capture_target(tmp_path, CaptureTarget("window", "Gone"))


@pytest.mark.parametrize(
    "changes",
    [
        {"bounds": (110, 100, 910, 700)},
        {"bounds": (100, 100, 1000, 700)},
        {"process_id": 999},
    ],
)
def test_guided_region_rejects_moved_resized_or_replaced_source(displays, monkeypatch, changes):
    from quill.core.studio_capture import guided_region

    source = CaptureTarget("window", "Editor", (100, 100, 900, 700), 123, 456)
    region = guided_region(source, 1, capture.desktop_target(displays).device)
    monkeypatch.setattr(capture, "window_target", lambda handle: replace(source, **changes))
    with pytest.raises(ScreenCaptureError, match="moved, resized or changed"):
        capture.resolve_target(region)


def test_guided_region_source_moving_during_grab_saves_no_image(tmp_path, displays, monkeypatch):
    from contextlib import nullcontext

    from quill.core.studio_capture import guided_region

    source = CaptureTarget("window", "Editor", (100, 100, 900, 700), 123, 456)
    current = [source]
    region = guided_region(source, 1, capture.desktop_target(displays).device)
    monkeypatch.setattr(capture, "physical_pixels", nullcontext)
    monkeypatch.setattr(capture, "window_target", lambda handle: current[0])

    def grab(**kwargs):
        current[0] = replace(source, bounds=(110, 100, 910, 700))
        return Image.new("RGB", (800, 300), "white")

    monkeypatch.setattr(ImageGrab, "grab", grab)
    with pytest.raises(ScreenCaptureError, match="moved, resized or changed"):
        capture.capture_target(tmp_path, region)
    assert not list(tmp_path.glob("*.png"))
