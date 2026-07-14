"""QuillMacRichText — the macOS rich wrapper — exercised over a fake bridge.

CI has no AppKit (and usually no macOS), so these tests drive the full method
surface through an injected fake bridge: API parity with QuillRichEdit, method
routing, RTF round trip, and the failure contract (every failure is a clear
MacRichTextError so the caller stays on converted rich — never a broken
editor). The real-Cocoa acquisition (`GetHandle` -> documentView,
`setRichText_`) plus the VoiceOver pass are the on-device Phase 6 gate.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import quill.ui.nstextview_rtf_surface as mod
import quill.ui.richedit_rtf_surface as win_mod


class _FakeBridge:
    """A stand-in Cocoa boundary: records every call, backs a bytes buffer."""

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.rtf = b"{\\rtf1 fake}"
        self.calls: list[tuple[str, tuple]] = []

    def available(self) -> bool:
        return self._available

    def text_view(self, handle: int) -> object:
        if not self._available or not handle:
            raise mod.MacRichTextError("no view")
        return "view"

    def read_rtf(self, view: object) -> bytes:
        self.calls.append(("read_rtf", (view,)))
        return self.rtf

    def write_rtf(self, view: object, data: bytes) -> None:
        self.calls.append(("write_rtf", (view,)))
        self.rtf = bytes(data)

    def toggle_trait(self, view: object, trait: str) -> None:
        self.calls.append(("toggle_trait", (trait,)))

    def set_attribute(self, view: object, name: str, value: object) -> None:
        self.calls.append(("set_attribute", (name, value)))

    def describe_caret(self, view: object) -> str:
        return "Helvetica, 14 point, bold"


class _FakeSurface:
    def __init__(self, handle: int = 42, value: str = "words") -> None:
        self._handle = handle
        self._value = value

    def GetHandle(self) -> int:  # noqa: N802 - wx shape
        return self._handle

    def GetValue(self) -> str:  # noqa: N802
        return self._value


def _wrapper(available: bool = True, handle: int = 42) -> mod.QuillMacRichText:
    return mod.QuillMacRichText(_FakeSurface(handle), bridge=_FakeBridge(available))


def test_api_parity_with_the_windows_wrapper() -> None:
    """One rich API on both platforms: rich-mode call sites never branch.

    Every formatting/IO method the rich-mode mixin invokes on QuillRichEdit
    must exist with the same name on QuillMacRichText.
    """
    shared = [
        "rtf_available",
        "load_rtf",
        "save_rtf",
        "get_rtf",
        "set_rtf",
        "get_plain_text",
        "apply_bold",
        "apply_italic",
        "apply_underline",
        "set_font_name",
        "set_font_size",
        "set_alignment",
        "set_color",
        "set_highlight",
        "set_heading",
        "caret_format_description",
        "capabilities",
        "accessibility_diagnostic_summary",
    ]
    for name in shared:
        assert callable(getattr(mod.QuillMacRichText, name, None)), f"mac wrapper lacks {name}"
        assert callable(getattr(win_mod.QuillRichEdit, name, None)), f"win wrapper lacks {name}"


def test_heading_ladder_is_shared_across_platforms() -> None:
    # A heading formatted on Windows must read at the same size on the Mac.
    source = inspect.getsource(mod)
    assert "from quill.ui.richedit_rtf_surface import" in source
    assert "HEADING_POINT_SIZES" in source


def test_rtf_round_trip_through_the_bridge() -> None:
    wrapper = _wrapper()
    wrapper.set_rtf(b"{\\rtf1 hello}")
    assert wrapper.get_rtf() == b"{\\rtf1 hello}"
    assert wrapper.get_plain_text() == "words"


def test_rtf_file_io(tmp_path: Path) -> None:
    wrapper = _wrapper()
    target = tmp_path / "doc.rtf"
    wrapper.save_rtf(str(target))
    assert target.read_bytes() == b"{\\rtf1 fake}"
    target.write_bytes(b"{\\rtf1 reloaded}")
    wrapper.load_rtf(str(target))
    assert wrapper.get_rtf() == b"{\\rtf1 reloaded}"


def test_formatting_routes_through_the_bridge() -> None:
    bridge = _FakeBridge()
    wrapper = mod.QuillMacRichText(_FakeSurface(), bridge=bridge)
    wrapper.apply_bold()
    wrapper.apply_italic()
    wrapper.apply_underline()
    wrapper.set_font_name("Helvetica")
    wrapper.set_font_size(14)
    wrapper.set_alignment("center")
    wrapper.set_color("#ff0000")
    wrapper.set_highlight("yellow")
    names = [name for name, _args in bridge.calls]
    assert names.count("toggle_trait") == 2
    assert names.count("set_attribute") == 6
    assert wrapper.caret_format_description() == "Helvetica, 14 point, bold"


def test_heading_maps_to_the_shared_size_ladder() -> None:
    bridge = _FakeBridge()
    wrapper = mod.QuillMacRichText(_FakeSurface(), bridge=bridge)
    wrapper.set_heading(2)
    sizes = [args for name, args in bridge.calls if name == "set_attribute"]
    assert ("NSFontSizeAttribute", float(win_mod.HEADING_POINT_SIZES[2])) in sizes
    wrapper.set_heading(0)  # body text
    sizes = [args for name, args in bridge.calls if name == "set_attribute"]
    assert ("NSFontSizeAttribute", float(win_mod.BODY_POINT_SIZE)) in sizes
    for bad in (-1, 7, "x"):
        try:
            wrapper.set_heading(bad)  # type: ignore[arg-type]
        except mod.MacRichTextError:
            continue
        raise AssertionError(f"heading {bad!r} must raise")  # pragma: no cover


def test_every_failure_is_a_clear_error_never_a_crash() -> None:
    # No bridge availability (PyObjC missing / off-macOS): capability reports
    # False and every operation raises MacRichTextError for the converted-rich
    # fallback — the failsafe contract.
    wrapper = _wrapper(available=False)
    assert wrapper.rtf_available() is False
    for call in (
        wrapper.get_rtf,
        lambda: wrapper.set_rtf(b"x"),
        wrapper.apply_bold,
        lambda: wrapper.set_heading(1),
        lambda: wrapper.set_alignment("center"),
    ):
        try:
            call()
        except mod.MacRichTextError:
            continue
        raise AssertionError("operations without a bridge must raise")  # pragma: no cover
    # Unknown alignment is a clear error even with a live bridge.
    live = _wrapper()
    try:
        live.set_alignment("sideways")
    except mod.MacRichTextError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("unknown alignment must raise")
    # No native handle: capability is False (converted rich).
    assert _wrapper(handle=0).rtf_available() is False


def test_factory_attaches_wrapper_and_falls_back() -> None:
    source = inspect.getsource(mod.create_nstextview_rtf)
    assert "quill_richedit" in source  # same attribute as Windows: no new call sites
    assert "wx_module.TextCtrl(parent, style=style)" in source  # plain fallback
    assert "SURFACE_KIND" in source


def test_pyobjc_stays_a_soft_dependency() -> None:
    # The module must import everywhere (this test IS the import) and AppKit
    # may only be imported inside the darwin-guarded bridge constructor.
    source = inspect.getsource(mod)
    head = source.split("class _AppKitBridge", 1)[0]
    assert "import AppKit" not in head
    assert 'sys.platform == "darwin"' in inspect.getsource(mod._AppKitBridge.__init__)


def test_main_frame_builds_the_mac_editor_through_the_factory() -> None:
    main_frame = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
        encoding="utf-8"
    )
    assert "create_nstextview_rtf(wx, splitter, wx.TE_MULTILINE)" in main_frame


def test_diagnostic_carries_no_document_content() -> None:
    summary = _wrapper().accessibility_diagnostic_summary()
    assert "Document content included: no" in summary
