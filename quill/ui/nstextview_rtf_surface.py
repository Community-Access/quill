"""QuillMacRichText — native rich text for macOS over the editor's NSTextView.

The Mac half of One Editor, Every Format (Phase 6). The trick that made
QuillRichEdit low-risk on Windows exists here too: a multiline ``wx.TextCtrl``
on macOS *is* an ``NSTextView`` (inside an ``NSScrollView``), and Cocoa's text
model speaks RTF natively through ``NSAttributedString``. This wrapper mirrors
the :class:`quill.ui.richedit_rtf_surface.QuillRichEdit` API method-for-method
(``load_rtf`` / ``get_rtf`` / ``apply_bold`` / ``set_heading`` / ...), so the
mode-polymorphic command routing gains no new branches — ``editor_mode ==
"rich"`` simply becomes reachable on macOS.

**Failsafe by construction.** PyObjC is a *soft* dependency (the ``mac``
install extra): absent, or on any Cocoa failure, every method raises a clear
:class:`MacRichTextError` and the caller stays on converted rich — never a
broken editor. All Cocoa specifics live in :class:`_AppKitBridge`; the wrapper
takes an injectable ``bridge`` so unit tests exercise the full method surface
with a fake (CI has no AppKit).

**On-device gates before promotion (the Phase 6 spike):** pin the
``GetHandle()`` -> ``documentView`` acquisition on the shipping wxPython, and
verify ``setRichText_`` + attributed edits do not disturb the wx editor
contract (value/caret/selection/EVT_TEXT) or VoiceOver reading. The protocol
mirrors the Windows JAWS+braille A/B.
"""

from __future__ import annotations

import sys
from typing import Any

# The same Word-tracking heading ladder as the Windows wrapper, so a document
# formatted on either platform reads identically on the other.
from quill.ui.richedit_rtf_surface import BODY_POINT_SIZE, HEADING_POINT_SIZES

SURFACE_KIND = "nstextview_rtf"

_ALIGNMENT_VALUES = {"left": 0, "right": 1, "center": 2, "justify": 3}

#: Bold / italic font traits (NSFontTraitMask, AppKit).
_NS_BOLD_MASK = 0x00000002
_NS_ITALIC_MASK = 0x00000001
_NS_UNBOLD_MASK = 0x00000004
_NS_UNITALIC_MASK = 0x01000000
#: NSUnderlineStyleSingle / None.
_NS_UNDERLINE_SINGLE = 1
_NS_UNDERLINE_NONE = 0


class MacRichTextError(RuntimeError):
    """A native Cocoa rich-text operation failed (no PyObjC, no view, Cocoa error).

    UI-layer glue like :class:`~quill.ui.richedit_rtf_surface.RichEditRtfError`
    (outside the error-code audit's scope); the caller degrades to converted
    rich with a clear on-screen message.
    """


class _AppKitBridge:
    """Every Cocoa touchpoint, isolated so tests can substitute a fake.

    Raises :class:`MacRichTextError` from every method when AppKit/PyObjC is
    unavailable — which is the permanent state off-macOS and the soft-dependency
    state on a Mac without the ``mac`` extra installed.
    """

    def __init__(self) -> None:
        self._appkit: Any = None
        self._objc: Any = None
        if sys.platform == "darwin":  # pragma: no cover - macOS only
            try:
                import AppKit
                import objc

                self._appkit = AppKit
                self._objc = objc
            except Exception:  # noqa: BLE001 - soft dependency by design
                self._appkit = None
                self._objc = None

    def available(self) -> bool:
        return self._appkit is not None

    def _require(self) -> Any:  # pragma: no cover - trivial guard
        if self._appkit is None:
            raise MacRichTextError(
                "The macOS rich text bridge (PyObjC) is unavailable. The Mac "
                "app ships it; on a source install add it with "
                "pip install 'quill[mac]'. Documents stay fully editable as "
                "converted text — please report this via Help > Report a Bug."
            )
        return self._appkit

    # Every method below runs only on a real Mac with AppKit; unit tests use a
    # fake bridge, and the on-device pass is the Phase 6 promotion gate.

    def text_view(self, handle: int) -> Any:  # pragma: no cover - needs AppKit
        """Resolve the editor's NSTextView from ``wx.Window.GetHandle()``.

        wx returns the peer NSView; for a multiline text control that is the
        enclosing NSScrollView on current wxPython, whose ``documentView`` is
        the NSTextView (the Phase 6 spike pins this per wx version).
        """
        appkit = self._require()
        objc = self._objc
        if not handle:
            raise MacRichTextError("The editor has no native view handle.")
        try:
            view = objc.objc_object(c_void_p=handle)
            if view.isKindOfClass_(appkit.NSScrollView):
                view = view.documentView()
            if not view.isKindOfClass_(appkit.NSTextView):
                raise MacRichTextError(f"Editor view is not an NSTextView: {view}")
            view.setRichText_(True)
            return view
        except MacRichTextError:
            raise
        except Exception as exc:  # noqa: BLE001 - any ObjC failure maps to ours
            raise MacRichTextError(f"Could not reach the editor's NSTextView: {exc}") from exc

    def read_rtf(self, view: Any) -> bytes:  # pragma: no cover - needs AppKit
        appkit = self._require()
        try:
            storage = view.textStorage()
            rng = appkit.NSMakeRange(0, storage.length())
            data = storage.RTFFromRange_documentAttributes_(
                rng, {appkit.NSDocumentTypeDocumentAttribute: appkit.NSRTFTextDocumentType}
            )
            return bytes(data)
        except Exception as exc:  # noqa: BLE001
            raise MacRichTextError(f"Could not read RTF from the editor: {exc}") from exc

    def write_rtf(self, view: Any, data: bytes) -> None:  # pragma: no cover - needs AppKit
        appkit = self._require()
        try:
            ns_data = appkit.NSData.dataWithBytes_length_(data, len(data))
            attributed, _attrs = appkit.NSAttributedString.alloc().initWithRTF_documentAttributes_(
                ns_data, None
            )
            if attributed is None:
                raise MacRichTextError("The RTF data could not be parsed.")
            view.textStorage().setAttributedString_(attributed)
        except MacRichTextError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MacRichTextError(f"Could not load RTF into the editor: {exc}") from exc

    def selected_range(self, view: Any) -> tuple[int, int]:  # pragma: no cover
        rng = view.selectedRange()
        return int(rng.location), int(rng.length)

    def toggle_trait(self, view: Any, trait: str) -> None:  # pragma: no cover
        """Toggle bold/italic on the selection via NSFontManager trait conversion."""
        appkit = self._require()
        try:
            manager = appkit.NSFontManager.sharedFontManager()
            storage = view.textStorage()
            location, length = self.selected_range(view)
            rng = appkit.NSMakeRange(location, length)
            font = storage.attribute_atIndex_effectiveRange_(
                appkit.NSFontAttributeName, max(0, location), None
            )
            traits = manager.traitsOfFont_(font) if font is not None else 0
            if trait == "bold":
                mask = _NS_UNBOLD_MASK if traits & _NS_BOLD_MASK else _NS_BOLD_MASK
            else:
                mask = _NS_UNITALIC_MASK if traits & _NS_ITALIC_MASK else _NS_ITALIC_MASK
            storage.beginEditing()
            try:

                def _convert(inner_font: Any) -> Any:
                    return manager.convertFont_toHaveTrait_(inner_font, mask)

                index = location
                end = location + max(length, 0)
                while index < end:
                    inner, eff = storage.attribute_atIndex_longestEffectiveRange_inRange_(
                        appkit.NSFontAttributeName, index, None, rng
                    )
                    span_end = int(eff.location + eff.length)
                    if inner is not None:
                        storage.addAttribute_value_range_(
                            appkit.NSFontAttributeName, _convert(inner), eff
                        )
                    index = max(span_end, index + 1)
            finally:
                storage.endEditing()
        except Exception as exc:  # noqa: BLE001
            raise MacRichTextError(f"Could not toggle {trait}: {exc}") from exc

    def set_attribute(self, view: Any, name: str, value: Any) -> None:  # pragma: no cover
        """Set an NSAttributedString attribute over the selection."""
        appkit = self._require()
        try:
            storage = view.textStorage()
            location, length = self.selected_range(view)
            rng = appkit.NSMakeRange(location, length)
            attr = getattr(appkit, name)
            storage.beginEditing()
            try:
                storage.addAttribute_value_range_(attr, value, rng)
            finally:
                storage.endEditing()
        except Exception as exc:  # noqa: BLE001
            raise MacRichTextError(f"Could not apply {name}: {exc}") from exc


class QuillMacRichText:
    """The macOS mirror of :class:`QuillRichEdit` — same API, Cocoa underneath.

    ``surface`` is the live ``wx.TextCtrl``; ``bridge`` is the Cocoa boundary
    (injectable for tests). Every method either succeeds natively or raises
    :class:`MacRichTextError` so the caller can stay on converted rich.
    """

    def __init__(self, surface: Any, bridge: Any | None = None) -> None:
        self._surface = surface
        self._bridge = bridge if bridge is not None else _AppKitBridge()

    # -- identity / capability ---------------------------------------------- #

    def handle(self) -> int:
        try:
            return int(self._surface.GetHandle())
        except Exception:  # noqa: BLE001 - handle access is best-effort
            return 0

    def rtf_available(self) -> bool:
        try:
            return bool(self._bridge.available()) and bool(self.handle())
        except Exception:  # noqa: BLE001 - capability probe never raises
            return False

    def _view(self) -> Any:
        return self._bridge.text_view(self.handle())

    # -- RTF I/O -------------------------------------------------------------- #

    def get_rtf(self) -> bytes:
        return bytes(self._bridge.read_rtf(self._view()))

    def set_rtf(self, data: bytes) -> None:
        self._bridge.write_rtf(self._view(), bytes(data))

    def load_rtf(self, path: str) -> None:
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError as exc:
            raise MacRichTextError(f"Could not open RTF file: {exc}") from exc
        self.set_rtf(data)

    def save_rtf(self, path: str) -> None:
        data = self.get_rtf()
        try:
            with open(path, "wb") as handle:
                handle.write(data)
        except OSError as exc:
            raise MacRichTextError(f"Could not save RTF file: {exc}") from exc

    def get_plain_text(self) -> str:
        try:
            return str(self._surface.GetValue())
        except Exception:  # noqa: BLE001 - never break the plain-text contract
            return ""

    # -- formatting (mirrors QuillRichEdit) ---------------------------------- #

    def apply_bold(self) -> None:
        self._bridge.toggle_trait(self._view(), "bold")

    def apply_italic(self) -> None:
        self._bridge.toggle_trait(self._view(), "italic")

    def apply_underline(self) -> None:
        self._bridge.set_attribute(
            self._view(), "NSUnderlineStyleAttributeName", _NS_UNDERLINE_SINGLE
        )

    def set_font_name(self, name: str) -> None:
        self._bridge.set_attribute(self._view(), "NSFontNameAttribute", str(name))

    def set_font_size(self, points: float) -> None:
        self._bridge.set_attribute(self._view(), "NSFontSizeAttribute", float(points))

    def set_alignment(self, how: str) -> None:
        value = _ALIGNMENT_VALUES.get(str(how).lower())
        if value is None:
            raise MacRichTextError(f"Unknown alignment: {how!r}")
        self._bridge.set_attribute(self._view(), "NSParagraphStyleAttributeName", value)

    def set_color(self, color: str) -> None:
        self._bridge.set_attribute(self._view(), "NSForegroundColorAttributeName", str(color))

    def set_highlight(self, color: str) -> None:
        self._bridge.set_attribute(self._view(), "NSBackgroundColorAttributeName", str(color))

    def set_heading(self, level: int) -> None:
        try:
            level = int(level)
        except (TypeError, ValueError) as exc:
            raise MacRichTextError(f"Unknown heading level: {level!r}") from exc
        if not 0 <= level <= 6:
            raise MacRichTextError(f"Heading level out of range: {level}")
        size = BODY_POINT_SIZE if level == 0 else HEADING_POINT_SIZES[level]
        self._bridge.set_attribute(self._view(), "NSFontSizeAttribute", float(size))
        if level != 0:
            self._bridge.toggle_trait(self._view(), "bold")

    def caret_format_description(self) -> str:
        """Spoken formatting at the caret; the bridge supplies the raw facts."""
        describe = getattr(self._bridge, "describe_caret", None)
        if callable(describe):
            return str(describe(self._view()))
        raise MacRichTextError("Caret formatting is not readable on this bridge.")

    # -- reporting ------------------------------------------------------------ #

    def capabilities(self) -> dict[str, Any]:
        rtf = self.rtf_available()
        return {
            "surface_kind": SURFACE_KIND,
            "native_control": True,
            "rtf_load": rtf,
            "rtf_save": rtf,
            "formatting_commands": rtf,
            "notes": (
                "macOS NSTextView via PyObjC (soft dependency): RTF load/save "
                "through NSAttributedString, bold/italic via NSFontManager "
                "traits. Absent PyObjC, QUILL stays on converted rich."
            ),
        }

    def accessibility_diagnostic_summary(self) -> str:
        return (
            "QuillMacRichText surface (NSTextView)\n"
            f"AppKit bridge available: {'yes' if self.rtf_available() else 'no'}\n"
            "Document content included: no"
        )


def create_nstextview_rtf(wx_module: Any, parent: Any, style: int) -> Any:
    """Build the macOS editor with the rich wrapper attached, or plain fallback.

    Mirrors :func:`quill.ui.richedit_rtf_surface.create_richedit_rtf`: the
    control is the same multiline ``wx.TextCtrl`` macOS always used (VoiceOver
    reads the same NSTextView it reads today); the wrapper rides on
    ``quill_richedit`` so every rich-mode call site works unchanged on both
    platforms. Any failure returns a stock control — the editor can never
    fail to build, and rich mode simply reports unavailable (converted rich).
    """
    try:
        surface = wx_module.TextCtrl(parent, style=style)
    except Exception:  # noqa: BLE001 - hosting is best-effort
        return wx_module.TextCtrl(parent, style=style)
    try:
        surface.surface_kind = SURFACE_KIND  # type: ignore[attr-defined]
        surface.quill_richedit = QuillMacRichText(surface)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - tagging is best-effort
        pass
    return surface
