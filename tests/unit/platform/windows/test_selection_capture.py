from __future__ import annotations

import sys
import types

from quill.core.external_text import TargetSnapshot
from quill.platform.windows.selection_capture import capture_uia_selection


class FakeTextRange:
    def __init__(self) -> None:
        self.limit = 0

    def GetText(self, limit: int) -> str:
        self.limit = limit
        return "picked"


class FakeRanges:
    Length = 1

    def __init__(self, text_range: FakeTextRange) -> None:
        self.text_range = text_range

    def GetElement(self, index: int) -> FakeTextRange | None:
        return self.text_range if index == 0 else None


class FakePattern:
    def __init__(self, ranges: FakeRanges) -> None:
        self.ranges = ranges

    def GetSelection(self) -> FakeRanges:
        return self.ranges


class FakeElement:
    CurrentNativeWindowHandle = 11
    CurrentProcessId = 22
    CurrentAutomationId = "field"

    def __init__(self, pattern: FakePattern) -> None:
        self.pattern = pattern
        self.pattern_requests = 0

    def GetCurrentPattern(self, _pattern_id: int) -> FakePattern:
        self.pattern_requests += 1
        return self.pattern

    def GetRuntimeId(self) -> tuple[int, int]:
        return (7, 8)


class FakeAutomation:
    def __init__(self, element: FakeElement) -> None:
        self.element = element

    def GetFocusedElement(self) -> FakeElement:
        return self.element


def _target() -> TargetSnapshot:
    return TargetSnapshot(
        target_id="windows:11:22:class:edit",
        window_handle=11,
        process_id=22,
        control_id="class:edit",
    )


def _install_fake_comtypes(monkeypatch, automation: FakeAutomation) -> None:
    client = types.ModuleType("comtypes.client")
    client.GetModule = lambda _name: types.SimpleNamespace(IUIAutomation=object())
    client.CreateObject = lambda *_args, **_kwargs: automation
    package = types.ModuleType("comtypes")
    package.client = client
    monkeypatch.setitem(sys.modules, "comtypes", package)
    monkeypatch.setitem(sys.modules, "comtypes.client", client)


def test_selection_capture_is_bounded_and_identity_checked(monkeypatch) -> None:
    text_range = FakeTextRange()
    element = FakeElement(FakePattern(FakeRanges(text_range)))
    _install_fake_comtypes(monkeypatch, FakeAutomation(element))

    selection = capture_uia_selection(_target(), max_characters=4)

    assert selection is not None
    assert selection.selected_text == "picked"
    assert selection.revision == "uia:7.8"
    assert text_range.limit == 4


def test_selection_capture_refuses_a_different_native_window(monkeypatch) -> None:
    text_range = FakeTextRange()
    element = FakeElement(FakePattern(FakeRanges(text_range)))
    _install_fake_comtypes(monkeypatch, FakeAutomation(element))
    target = TargetSnapshot(
        target_id="other",
        window_handle=99,
        process_id=22,
        control_id="class:edit",
    )

    selection = capture_uia_selection(target)

    assert selection is None
    assert element.pattern_requests == 0
