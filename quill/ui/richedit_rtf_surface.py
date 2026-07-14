"""QuillRichEdit — QUILL's one editor surface on Windows.

Promoted from the Experimental tab in 0.9.0-beta3 after live JAWS + braille
testing confirmed the braille fix (#616/#813): every document tab is built by
:func:`create_richedit_rtf`, honoring the two Braille-tab checkboxes
(``braille_editor_system_edit_fix`` -> ``SES_EMULATESYSEDIT``;
``braille_editor_hide_border`` -> a borderless frame, applied by the caller).
Backed by the *same* native Windows Rich Edit control QUILL always shipped as
its default (``RICHEDIT50W`` from msftedit.dll, a ``wx.TextCtrl`` with
``TE_RICH2``). The whole ``EditorSurface`` contract (value / caret / selection /
undo / events) comes for free and unchanged from that proven control.

**Phase 1 adds real RTF load/save via the Rich Edit Text Object Model (TOM).**
The first attempt drove ``EM_STREAMIN`` / ``EM_STREAMOUT`` with a ``ctypes``
``EDITSTREAM`` callback, but on-device testing found that hard-crashes msftedit
(the control access-violates the instant it invokes a Python callback -- see the
post-mortem in ``docs/engineering/editor-surface-history.md``). The TOM path
avoids a Python callback entirely: ``EM_GETOLEINTERFACE`` yields the control's
``IRichEditOle``; we ``QueryInterface`` to ``ITextDocument`` (via ``comtypes`` +
the tom type library) and call ``ITextDocument::Open`` / ``::Save`` with the
``tomRTF`` format flag against a file. Verified end-to-end on a real
``RICHEDIT50W`` with no crash.

Also wired, all through the TOM: **Phase 2** formatting (bold/italic/underline/
font/size/alignment via ``ITextFont`` / ``ITextPara``) and **Phase 3** the
braille instrument (the TOM ``ITextSelection`` localizer plus the
``EM_SETEDITSTYLE`` / ``SES_EMULATESYSEDIT`` lever) for the cell-2 (#616) and
dots-7-8-on-selection (#813) braille bugs. The formatting methods are wired at
the surface; menu/keyboard command routing is the remaining integration.

Everything Windows/COM is guarded so the module imports on every platform, and
every path raises a clear error or falls back -- selecting the surface can never
brick the editor.
"""

from __future__ import annotations

import os
import sys
import tempfile
from typing import Any

SURFACE_KIND = "richedit_rtf"

# EM_GETOLEINTERFACE (richedit.h) -> the control's IRichEditOle.
_EM_GETOLEINTERFACE = 0x0400 + 60
# The Text Object Model type library ("tom"): {8CC497C9-A1DF-11CE-8098-00AA0047BE5D}.
_TOM_TYPELIB = ("{8CC497C9-A1DF-11CE-8098-00AA0047BE5D}", 1, 0)
# tom constants (confirmed from the loaded type library) for Open/Save.
_TOM_RTF = 1
_TOM_CREATE_ALWAYS = 32
_TOM_OPEN_EXISTING = 48

# Edit-style messages + the SES_EMULATESYSEDIT flag (richedit.h). Phase 3 braille
# lever: emulate the classic EDIT control (which JAWS renders from cell 1 with
# selection dots 7-8) while staying a Rich Edit (so IAccessible value reporting is
# unchanged) -- the candidate fix for #616 (cell-2 offset) and #813 (dots 7-8).
_EM_SETEDITSTYLE = 0x0400 + 204
_EM_GETEDITSTYLE = 0x0400 + 205
_SES_EMULATESYSEDIT = 0x00000001

# TOM formatting (Phase 2): ITextFont bool values + ITextPara alignment (tom.h).
_TOM_TOGGLE = -9999998
_TOM_TRUE = -9999999
_TOM_FALSE = 0
_TOM_ALIGNMENT = {"left": 0, "center": 1, "right": 2, "justify": 3}
_TOM_ALIGNMENT_NAMES = {value: name for name, value in _TOM_ALIGNMENT.items()}
# tomParagraph unit for expanding the selection to whole paragraphs (tom.h).
_TOM_UNIT_PARAGRAPH = 4

#: Rich-mode heading presentation: point size + bold per level, chosen to track
#: Word's Heading 1-6 ladder closely enough that a saved RTF reads as headings
#: in Word while staying legible in the editor. Body text is 11 pt.
HEADING_POINT_SIZES: dict[int, float] = {1: 20.0, 2: 16.0, 3: 14.0, 4: 12.0, 5: 11.0, 6: 11.0}
BODY_POINT_SIZE = 11.0

#: Named colors accepted by set_color/set_highlight, mirroring the hidden-codes
#: vocabulary (quill/io/docx_writer.py keeps the same table for export parity).
_COLOR_NAMES: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
}


def _color_to_colorref(color: str) -> int:
    """Convert ``#rrggbb`` or a named color to a Win32 COLORREF (0x00BBGGRR)."""
    value = str(color).strip().lower()
    if value.startswith("#") and len(value) == 7:
        try:
            red = int(value[1:3], 16)
            green = int(value[3:5], 16)
            blue = int(value[5:7], 16)
        except ValueError as exc:
            raise RichEditRtfError(f"Unknown color: {color!r}") from exc
    elif value in _COLOR_NAMES:
        red, green, blue = _COLOR_NAMES[value]
    else:
        raise RichEditRtfError(f"Unknown color: {color!r}")
    return red | (green << 8) | (blue << 16)


class RichEditRtfError(RuntimeError):
    """A native RTF operation failed (no OLE interface, TOM error, file I/O).

    A plain ``RuntimeError`` subclass, not a ``CodedError``: this is UI-layer glue
    (``quill/ui``), outside the error-code audit's scope, and the caller degrades
    to a clear on-screen message + the plain-text fallback.
    """


# --------------------------------------------------------------------------- #
# TOM / COM glue (guarded so the module imports on every platform)
# --------------------------------------------------------------------------- #

_TOM_AVAILABLE = False

if sys.platform == "win32":  # pragma: no cover - Windows + a real HWND only
    try:
        import ctypes
        from ctypes import wintypes

        import comtypes
        import comtypes.client

        _SendMessageW = ctypes.windll.user32.SendMessageW
        _SendMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        _SendMessageW.restype = ctypes.c_ssize_t
        _TOM_AVAILABLE = True
    except Exception:  # noqa: BLE001 - any setup failure disables native RTF
        _TOM_AVAILABLE = False

_tom_module: Any = None


def _get_text_document(hwnd: int) -> Any:  # pragma: no cover - needs a live HWND
    """Return the control's ``ITextDocument`` (TOM), or raise :class:`RichEditRtfError`.

    ``EM_GETOLEINTERFACE`` yields the ``IRichEditOle`` (already AddRef'd); we wrap
    it as ``IUnknown`` and ``QueryInterface`` to ``ITextDocument``. comtypes
    releases both on garbage collection. No Python callback is involved, so the
    msftedit ``EM_STREAM`` crash does not apply.
    """
    global _tom_module
    if not (_TOM_AVAILABLE and hwnd):
        raise RichEditRtfError("The native Rich Edit text-object model is unavailable.")
    try:
        ptr = ctypes.c_void_p(0)
        _SendMessageW(hwnd, _EM_GETOLEINTERFACE, 0, ctypes.addressof(ptr))
        if not ptr.value:
            raise RichEditRtfError("EM_GETOLEINTERFACE returned no interface.")
        if _tom_module is None:
            from quill.platform.windows.comtypes_setup import ensure_comtypes_gen_dir_redirected

            ensure_comtypes_gen_dir_redirected()
            _tom_module = comtypes.client.GetModule(_TOM_TYPELIB)
        unknown = ctypes.cast(ptr.value, ctypes.POINTER(comtypes.IUnknown))
        return unknown.QueryInterface(_tom_module.ITextDocument)
    except RichEditRtfError:
        raise
    except Exception as exc:  # noqa: BLE001 - map any COM failure to our error
        raise RichEditRtfError(f"Could not reach the Rich Edit text object model: {exc}") from exc


def _window_class_name(hwnd: int) -> str:
    """Best-effort Win32 class name for *hwnd* (empty off-Windows/failure).

    Read-only and content-free: confirms the surface is a genuine ``RICHEDIT50W``.
    """
    if sys.platform != "win32" or not hwnd:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(256)
        length = ctypes.windll.user32.GetClassNameW(int(hwnd), buffer, 256)
        return buffer.value if length else ""
    except Exception:  # noqa: BLE001 - diagnostics must never raise
        return ""


class QuillRichEdit:
    """Thin, replaceable wrapper API over the native Rich Edit control.

    Phase 1 wires native RTF load/save through the TOM (``get_rtf``/``set_rtf``/
    ``load_rtf``/``save_rtf``). ``get_plain_text`` returns the control's plain
    value so QUILL's offset-anchored features (search, spell, AI, read aloud,
    braille) keep working unchanged. Formatting (Phase 2) and the braille
    instrument (Phase 3) are also wired here. ``surface`` is the live
    ``wx.TextCtrl``.
    """

    def __init__(self, surface: Any) -> None:
        self._surface = surface

    # -- identity / handle -------------------------------------------------- #

    def hwnd(self) -> int:
        try:
            return int(self._surface.GetHandle())
        except Exception:  # noqa: BLE001 - handle access is best-effort
            return 0

    def rtf_available(self) -> bool:
        """True when native RTF load/save can run (Windows + comtypes + a HWND).

        A lightweight heuristic; the actual COM call in the RTF methods raises a
        clear :class:`RichEditRtfError` if it fails at runtime.
        """
        return bool(_TOM_AVAILABLE and self.hwnd())

    # -- RTF I/O (Phase 1, via the Text Object Model) ----------------------- #

    def load_rtf(self, path: str) -> None:
        """Load an RTF file into the control via ``ITextDocument::Open``."""
        itd = _get_text_document(self.hwnd())
        try:
            itd.Open(str(path), _TOM_OPEN_EXISTING | _TOM_RTF, 0)
        except Exception as exc:  # noqa: BLE001 - map COM/file errors to our type
            raise RichEditRtfError(f"Could not open RTF file: {exc}") from exc

    def save_rtf(self, path: str) -> None:
        """Save the control's content to an RTF file via ``ITextDocument::Save``."""
        itd = _get_text_document(self.hwnd())
        try:
            itd.Save(str(path), _TOM_CREATE_ALWAYS | _TOM_RTF, 0)
        except Exception as exc:  # noqa: BLE001
            raise RichEditRtfError(f"Could not save RTF file: {exc}") from exc

    def get_rtf(self) -> bytes:
        """Return the document as RTF bytes (TOM Save to a temp file)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "quill.rtf")
            self.save_rtf(path)
            try:
                with open(path, "rb") as handle:
                    return handle.read()
            except OSError as exc:
                raise RichEditRtfError(f"Could not read the saved RTF: {exc}") from exc

    def set_rtf(self, data: bytes) -> None:
        """Replace the document with RTF bytes (TOM Open from a temp file)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "quill.rtf")
            try:
                with open(path, "wb") as handle:
                    handle.write(data)
            except OSError as exc:
                raise RichEditRtfError(f"Could not stage RTF for loading: {exc}") from exc
            self.load_rtf(path)

    def get_plain_text(self) -> str:
        """The control's plain text -- what search/spell/AI/read-aloud consume."""
        try:
            return str(self._surface.GetValue())
        except Exception:  # noqa: BLE001 - never break the plain-text contract
            return ""

    # -- braille instrument + levers (Phase 3) ------------------------------ #

    def edit_style(self) -> int:
        """The control's current EM edit-style flags (0 off-Windows/no handle)."""
        hwnd = self.hwnd()
        if not (_TOM_AVAILABLE and hwnd):
            return 0
        try:
            return int(_SendMessageW(hwnd, _EM_GETEDITSTYLE, 0, 0))
        except Exception:  # noqa: BLE001 - a probe must never raise
            return 0

    def set_emulate_system_edit(self, enabled: bool) -> None:
        """Toggle ``SES_EMULATESYSEDIT`` -- ask the Rich Edit to behave like the
        classic EDIT control.

        The braille lever for #616/#813: the plain EDIT control shows text from
        cell 1 and shows selection dots 7-8, while the Rich Edit (which QUILL
        keeps for its correct IAccessible value) shows the cell-2 offset and may
        drop the selection dots. Emulating a system edit control may give the best
        of both. Best-effort; **needs JAWS + a braille display to evaluate.**
        """
        hwnd = self.hwnd()
        if not (_TOM_AVAILABLE and hwnd):
            return
        style = _SES_EMULATESYSEDIT if enabled else 0
        try:
            _SendMessageW(hwnd, _EM_SETEDITSTYLE, style, _SES_EMULATESYSEDIT)
        except Exception:  # noqa: BLE001 - the lever is best-effort, never fatal
            pass

    def selection_diagnostic(self) -> str:
        """Report the selection as the control's TOM sees it vs wx -- localizes #813.

        Offsets and length only, never the selected text. If wx and the TOM agree,
        the control *knows* the selection, so a braille display not showing dots
        7-8 is an AT-rendering gap, not a control-tracking one.
        """
        try:
            wx_sel = tuple(self._surface.GetSelection())
        except Exception:  # noqa: BLE001
            wx_sel = None
        if not self.rtf_available():
            return f"wx={wx_sel}, TOM=(unavailable)"
        try:
            selection = _get_text_document(self.hwnd()).Selection
            tom = (int(selection.Start), int(selection.End))
        except Exception as exc:  # noqa: BLE001 - report, never raise
            return f"wx={wx_sel}, TOM=(error: {exc})"
        agree = wx_sel is not None and wx_sel == tom
        return f"wx={wx_sel}, TOM={tom}, agree={agree}"

    # -- formatting (Phase 2, via the TOM ITextFont / ITextPara) ------------ #

    def _selection(self) -> Any:
        """The control's live ``ITextSelection`` (raises :class:`RichEditRtfError`)."""
        return _get_text_document(self.hwnd()).Selection

    def _apply_font(self, attr: str, value: Any) -> None:
        try:
            setattr(self._selection().Font, attr, value)
        except RichEditRtfError:
            raise
        except Exception as exc:  # noqa: BLE001 - map COM failure to our error
            raise RichEditRtfError(f"Could not apply {attr} formatting: {exc}") from exc

    def apply_bold(self) -> None:
        """Toggle bold on the current selection (ITextFont.Bold)."""
        self._apply_font("Bold", _TOM_TOGGLE)

    def apply_italic(self) -> None:
        """Toggle italic on the current selection."""
        self._apply_font("Italic", _TOM_TOGGLE)

    def apply_underline(self) -> None:
        """Toggle underline on the current selection."""
        self._apply_font("Underline", _TOM_TOGGLE)

    def set_font_name(self, name: str) -> None:
        """Set the font family of the current selection."""
        self._apply_font("Name", str(name))

    def set_font_size(self, points: float) -> None:
        """Set the font size (points) of the current selection."""
        self._apply_font("Size", float(points))

    def set_alignment(self, how: str) -> None:
        """Set paragraph alignment: ``left`` / ``center`` / ``right`` / ``justify``."""
        value = _TOM_ALIGNMENT.get(str(how).lower())
        if value is None:
            raise RichEditRtfError(f"Unknown alignment: {how!r}")
        try:
            self._selection().Para.Alignment = value
        except RichEditRtfError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RichEditRtfError(f"Could not set alignment: {exc}") from exc

    def set_color(self, color: str) -> None:
        """Set the text color of the selection (``#rrggbb`` or a named color)."""
        self._apply_font("ForeColor", _color_to_colorref(color))

    def set_highlight(self, color: str) -> None:
        """Set the highlight (background) color of the selection."""
        self._apply_font("BackColor", _color_to_colorref(color))

    def set_heading(self, level: int) -> None:
        """Style the paragraph(s) under the selection as a Heading 1-6.

        Rich-mode headings are presentational on the native control: the
        Word-tracking point-size ladder plus bold, applied to whole paragraphs
        (the selection is expanded through ``tomParagraph`` so the caret
        anywhere in a line headings the whole line). ``level`` 0 returns the
        paragraph to body text. Saved RTF then reads as sized/bold headings in
        Word; heading *navigation* in rich mode reads the same ladder back
        through :meth:`caret_format_description`.
        """
        try:
            level = int(level)
        except (TypeError, ValueError) as exc:
            raise RichEditRtfError(f"Unknown heading level: {level!r}") from exc
        if not 0 <= level <= 6:
            raise RichEditRtfError(f"Heading level out of range: {level}")
        try:
            selection = self._selection()
            span = selection.Duplicate
            span.Expand(_TOM_UNIT_PARAGRAPH)
            font = span.Font
            if level == 0:
                font.Size = BODY_POINT_SIZE
                font.Bold = _TOM_FALSE
            else:
                font.Size = HEADING_POINT_SIZES[level]
                font.Bold = _TOM_TRUE
        except RichEditRtfError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RichEditRtfError(f"Could not apply heading {level}: {exc}") from exc

    def caret_format_description(self) -> str:
        """A spoken-friendly description of the formatting at the caret.

        Read live from the TOM (``ITextFont``/``ITextPara``), so Describe
        Formatting in rich mode answers from the real control instead of
        parsing markup: "Arial, 14 point, bold, centered". Raises
        :class:`RichEditRtfError` when the TOM is unreachable.
        """
        try:
            selection = self._selection()
            font = selection.Font
            parts: list[str] = []
            name = str(getattr(font, "Name", "") or "").strip()
            if name:
                parts.append(name)
            size = float(getattr(font, "Size", 0) or 0)
            if size > 0:
                point = f"{size:g} point"
                parts.append(point)
                heading = next(
                    (
                        lvl
                        for lvl, pts in HEADING_POINT_SIZES.items()
                        if lvl <= 4 and abs(size - pts) < 0.25
                    ),
                    None,
                )
                if heading is not None and int(getattr(font, "Bold", 0)) != 0 and heading != 5:
                    parts.append(f"heading {heading}")
            if int(getattr(font, "Bold", 0)) != 0:
                parts.append("bold")
            if int(getattr(font, "Italic", 0)) != 0:
                parts.append("italic")
            if int(getattr(font, "Underline", 0)) != 0:
                parts.append("underline")
            alignment_phrases = {
                "center": "centered",
                "right": "right aligned",
                "justify": "justified",
            }
            alignment = _TOM_ALIGNMENT_NAMES.get(int(selection.Para.Alignment))
            phrase = alignment_phrases.get(alignment or "")
            if phrase:
                parts.append(phrase)
            return ", ".join(parts) if parts else "plain text"
        except RichEditRtfError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RichEditRtfError(f"Could not read caret formatting: {exc}") from exc

    # -- reporting ---------------------------------------------------------- #

    def capabilities(self) -> dict[str, Any]:
        """A wx-free report of what this surface can do right now (honest by rule)."""
        rtf = self.rtf_available()
        return {
            "surface_kind": SURFACE_KIND,
            "phase": 1,
            "native_control": True,
            "rtf_load": rtf,
            "rtf_save": rtf,
            "formatting_commands": rtf,
            "notes": (
                "Native Windows Rich Edit (RICHEDIT50W): RTF load/save and "
                "bold/italic/underline/font/size/alignment via the Text Object "
                "Model, plus the Phase 3 braille instrument (selection localizer + "
                "emulate-system-edit lever)."
            ),
        }

    def self_test_rtf_roundtrip(self) -> tuple[bool, str]:
        """Push a known RTF snippet in and read it back -- a tester's one-click check.

        DESTRUCTIVE (replaces the document); returns ``(ok, detail)`` and never
        raises, so it is safe to wire to a deliberate menu/hotkey action.
        """
        sample = (
            rb"{\rtf1\ansi\deff0{\fonttbl{\f0 Segoe UI;}}"
            rb"\f0 QuillRichEdit round-trip test.\par}"
        )
        try:
            self.set_rtf(sample)
            out = self.get_rtf()
            text = self.get_plain_text()
            ok = "round-trip test" in text and out[:5] == b"{\\rtf"
            return ok, (
                f"RTF round-trip {'OK' if ok else 'MISMATCH'}: read back "
                f"{len(out)} RTF bytes; plain text = {text.strip()!r}"
            )
        except Exception as exc:  # noqa: BLE001 - a self-test must report, not raise
            return False, f"RTF round-trip failed: {exc}"

    def _rtf_out_probe(self) -> str:
        """A safe, read-only RTF-out check for the diagnostic (no document content).

        Saves the current document to RTF (non-destructive) and reports only its
        size and whether it carries the RTF signature.
        """
        if not self.rtf_available():
            return "unavailable (no native handle or comtypes)"
        try:
            data = self.get_rtf()
        except RichEditRtfError as exc:
            return f"failed ({exc})"
        signed = data[:6].startswith(b"{\\rtf")
        return f"{len(data)} bytes, RTF signature: {'yes' if signed else 'no'}"

    def accessibility_diagnostic_summary(self) -> str:
        """A short, read-only summary for Copy Diagnostic Summary (no document content)."""
        class_name = _window_class_name(self.hwnd()) or "(unavailable)"
        return (
            "QuillRichEdit surface (Phase 1 + Phase 3 instrument)\n"
            f"Win32 class name: {class_name}\n"
            f"RTF (TOM) available: {'yes' if self.rtf_available() else 'no'}\n"
            f"RTF save probe: {self._rtf_out_probe()}\n"
            f"Edit style (EM_GETEDITSTYLE): {hex(self.edit_style())} "
            f"(SES_EMULATESYSEDIT {'ON' if self.edit_style() & _SES_EMULATESYSEDIT else 'off'})\n"
            f"Selection (#813 localizer): {self.selection_diagnostic()}\n"
            "Document content included: no"
        )


def create_richedit_rtf(
    wx_module: Any, parent: Any, style: int, *, emulate_system_edit: bool = False
) -> Any:
    """Build the native Rich Edit surface, or a stock ``wx.TextCtrl`` fallback.

    The surface is a ``wx.TextCtrl`` with ``TE_RICH2 | TE_NOHIDESEL`` (the same
    RICHEDIT50W the default editor uses), tagged with ``surface_kind`` and a
    :class:`QuillRichEdit` wrapper on ``quill_richedit`` for RTF I/O + later
    phases. When ``emulate_system_edit`` is set (the experimental braille lever),
    ``SES_EMULATESYSEDIT`` is applied so a tester can A/B the #616/#813 braille
    behaviour. Any failure -- including off-Windows, where TE_RICH2 is a no-op --
    returns a plain multiline control so selecting this surface can never brick
    the editor.
    """
    try:
        rich_style = style | wx_module.TE_RICH2 | wx_module.TE_NOHIDESEL
        surface = wx_module.TextCtrl(parent, style=rich_style)
    except Exception:  # noqa: BLE001 - hosting is best-effort; fall back to wx
        return wx_module.TextCtrl(parent, style=style)
    try:
        surface.surface_kind = SURFACE_KIND  # type: ignore[attr-defined]
        wrapper = QuillRichEdit(surface)
        surface.quill_richedit = wrapper  # type: ignore[attr-defined]
        if emulate_system_edit:
            wrapper.set_emulate_system_edit(True)
    except Exception:  # noqa: BLE001 - tagging is best-effort; the control still works
        pass
    return surface
