"""The editor surface: one native Windows RichEdit control, two text modes.

Adapted from QUILL for All's quill/ui/richedit_rtf_surface.py. The control is
a wx.TextCtrl with TE_RICH2, which on Windows is RICHEDIT50W from
msftedit.dll. QUILL kept that control for one reason that matters here too:
its IAccessible value is reported correctly to NVDA and JAWS, where the classic
EDIT control's is not.

Plain mode puts the same control into TM_PLAINTEXT, so it behaves like
Notepad (one font, paste is plain text). Rich mode is TM_RICHTEXT, and RTF
load and save go through the Rich Edit Text Object Model (TOM). QUILL found
that EM_STREAMIN with a Python callback hard-crashes msftedit; the TOM path
never calls back into Python, which is why it is used here.

Everything Windows-specific is guarded so the module imports anywhere; on
another platform you get a plain wx.TextCtrl and rich features report as
unavailable.
"""

from __future__ import annotations

import os
import sys
import tempfile
from typing import Any

PLAIN = "plain"
RICH = "rich"

# Rich Edit messages (richedit.h)
_WM_USER = 0x0400
_EM_GETOLEINTERFACE = _WM_USER + 60
_EM_SETTEXTMODE = _WM_USER + 89
_EM_GETTEXTMODE = _WM_USER + 90
_EM_SETTARGETDEVICE = _WM_USER + 72
_EM_SETBKGNDCOLOR = _WM_USER + 67
_EM_SETZOOM = _WM_USER + 225
_TM_PLAINTEXT = 1
_TM_RICHTEXT = 2
_TM_MULTILEVELUNDO = 8
_TM_MULTICODEPAGE = 32

# Text Object Model type library and constants (tom.h)
_TOM_TYPELIB = ("{8CC497C9-A1DF-11CE-8098-00AA0047BE5D}", 1, 0)
_TOM_RTF = 1
_TOM_CREATE_ALWAYS = 32
_TOM_OPEN_EXISTING = 48
# tom.h values. tomTrue is -1: the -9999999 that QUILL for All uses for it is
# actually tomUndefined, which is why assigning it to Font.Bold silently does
# nothing (verified on RICHEDIT50W / Riched20 10.0.26100, two Windows 11 boxes).
_TOM_UNDEFINED = -9999999
_TOM_TOGGLE = -9999998
_TOM_TRUE = -1
_TOM_FALSE = 0
_TOM_UNIT_PARAGRAPH = 4
_TOM_UNIT_STORY = 6
_TOM_AUTOCOLOR = -9999997
_TOM_SUSPEND = -9999995
_TOM_RESUME = -9999994
_TOM_ALIGNMENT = {"left": 0, "center": 1, "right": 2, "justify": 3}
_TOM_ALIGNMENT_NAMES = {v: k for k, v in _TOM_ALIGNMENT.items()}
_MAX_HEADING_SCAN = 100000

# QUILL's heading ladder: bold plus a point size per level, close enough to
# Word's Heading 1 to 4 that a saved RTF reads as headings in Word.
HEADING_POINT_SIZES: dict[int, float] = {1: 20.0, 2: 16.0, 3: 14.0, 4: 12.0}
BODY_POINT_SIZE = 11.0


def heading_level_for_font(size: float, bold: bool) -> int | None:
    if not bold:
        return None
    for level, points in HEADING_POINT_SIZES.items():
        if abs(float(size) - points) < 0.25:
            return level
    return None


class RichEditError(RuntimeError):
    """A native RTF or formatting operation failed."""


_TOM_AVAILABLE = False
if sys.platform == "win32":
    try:
        import ctypes
        from ctypes import wintypes

        _SendMessageW = ctypes.windll.user32.SendMessageW
        _SendMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        _SendMessageW.restype = ctypes.c_ssize_t
        _TOM_AVAILABLE = True
    except Exception:
        _TOM_AVAILABLE = False

_tom_module: Any = None


def _send(hwnd: int, msg: int, wparam: int = 0, lparam: int = 0) -> int:
    if not (_TOM_AVAILABLE and hwnd):
        return 0
    try:
        return int(_SendMessageW(hwnd, msg, wparam, lparam))
    except Exception:
        return 0


def _get_text_document(hwnd: int) -> Any:
    """The control's ITextDocument via EM_GETOLEINTERFACE and QueryInterface."""
    global _tom_module
    if not (_TOM_AVAILABLE and hwnd):
        raise RichEditError("The native Rich Edit text object model is unavailable.")
    try:
        import comtypes  # noqa: PLC0415
        import comtypes.client  # noqa: PLC0415

        ptr = ctypes.c_void_p(0)
        _SendMessageW(hwnd, _EM_GETOLEINTERFACE, 0, ctypes.addressof(ptr))
        if not ptr.value:
            raise RichEditError("EM_GETOLEINTERFACE returned no interface.")
        if _tom_module is None:
            from quilllite.paths import comtypes_gen_dir  # noqa: PLC0415

            try:
                comtypes.client.gen_dir = str(comtypes_gen_dir())
            except Exception:
                comtypes.client.gen_dir = None
            _tom_module = comtypes.client.GetModule(_TOM_TYPELIB)
        unknown = ctypes.cast(ptr.value, ctypes.POINTER(comtypes.IUnknown))
        return unknown.QueryInterface(_tom_module.ITextDocument)
    except RichEditError:
        raise
    except Exception as exc:
        raise RichEditError(f"Could not reach the Rich Edit text object model: {exc}") from exc


class Editor:
    """Wraps the live wx.TextCtrl with mode, wrap, RTF and formatting helpers."""

    def __init__(self, control: Any, mode: str = PLAIN) -> None:
        self.control = control
        self.mode = mode

    # -- handle and capability ------------------------------------------- #

    def hwnd(self) -> int:
        try:
            return int(self.control.GetHandle())
        except Exception:
            return 0

    def native(self) -> bool:
        return bool(_TOM_AVAILABLE and self.hwnd())

    # -- text mode ------------------------------------------------------- #

    def set_mode(self, mode: str) -> None:
        """Switch between plain and rich. The control must be empty, so the
        caller saves and restores the text around this."""
        self.mode = mode
        hwnd = self.hwnd()
        if not hwnd:
            return
        flags = (
            (_TM_PLAINTEXT if mode == PLAIN else _TM_RICHTEXT)
            | _TM_MULTILEVELUNDO
            | _TM_MULTICODEPAGE
        )
        _send(hwnd, _EM_SETTEXTMODE, flags, 0)

    def current_native_mode(self) -> str:
        value = _send(self.hwnd(), _EM_GETTEXTMODE)
        if value & _TM_PLAINTEXT:
            return PLAIN
        if value & _TM_RICHTEXT:
            return RICH
        return "unknown"

    def set_word_wrap(self, wrap: bool) -> None:
        """EM_SETTARGETDEVICE: lParam 0 wraps to the window, 1 never wraps."""
        _send(self.hwnd(), _EM_SETTARGETDEVICE, 0, 0 if wrap else 1)

    def set_background(self, red: int, green: int, blue: int) -> None:
        _send(self.hwnd(), _EM_SETBKGNDCOLOR, 0, red | (green << 8) | (blue << 16))

    def set_zoom(self, numerator: float, denominator: float) -> None:
        """EM_SETZOOM. Both zero restores 100 percent. Used in rich mode so the
        view can be enlarged without rewriting every run's point size."""
        if numerator <= 0 or denominator <= 0:
            _send(self.hwnd(), _EM_SETZOOM, 0, 0)
            return
        _send(self.hwnd(), _EM_SETZOOM, int(round(numerator * 100)), int(round(denominator * 100)))

    def set_whole_document_colour(self, rgb: tuple[int, int, int] | None) -> None:
        """Colour every run in the story, or reset to automatic when rgb is None.

        Undo is suspended around the change so a theme switch never appears in
        the user's undo history. Only used for the dark theme and for the
        automatic-colour reset before a save.
        """
        document = _get_text_document(self.hwnd())
        try:
            try:
                document.Undo(_TOM_SUSPEND)
            except Exception:
                pass
            story = document.Range(0, 0)
            story.Expand(_TOM_UNIT_STORY)
            if rgb is None:
                story.Font.ForeColor = _TOM_AUTOCOLOR
            else:
                red, green, blue = rgb
                story.Font.ForeColor = red | (green << 8) | (blue << 16)
        except Exception as exc:
            raise RichEditError(f"Could not recolour the document: {exc}") from exc
        finally:
            try:
                document.Undo(_TOM_RESUME)
            except Exception:
                pass

    # -- plain text ------------------------------------------------------ #

    def get_text(self) -> str:
        try:
            return str(self.control.GetValue())
        except Exception:
            return ""

    def set_text(self, text: str) -> None:
        self.control.ChangeValue(text)

    # -- RTF via the TOM ------------------------------------------------- #

    def load_rtf(self, path: str) -> None:
        itd = _get_text_document(self.hwnd())
        try:
            itd.Open(str(path), _TOM_OPEN_EXISTING | _TOM_RTF, 0)
        except Exception as exc:
            raise RichEditError(f"Could not open RTF file: {exc}") from exc

    def save_rtf(self, path: str) -> None:
        itd = _get_text_document(self.hwnd())
        try:
            itd.Save(str(path), _TOM_CREATE_ALWAYS | _TOM_RTF, 0)
        except Exception as exc:
            raise RichEditError(f"Could not save RTF file: {exc}") from exc

    def get_rtf(self) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "quilllite.rtf")
            self.save_rtf(path)
            with open(path, "rb") as handle:
                return handle.read()

    def set_rtf(self, data: bytes) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "quilllite.rtf")
            with open(path, "wb") as handle:
                handle.write(data)
            self.load_rtf(path)

    # -- formatting via ITextFont / ITextPara ----------------------------- #

    def _selection(self) -> Any:
        return _get_text_document(self.hwnd()).Selection

    def _format_range(self) -> Any:
        """The range whose formatting the caret is 'in'.

        A collapsed range reports the formatting of the character before it,
        so at a paragraph start it describes the previous paragraph. Screen
        readers describe the character after the caret; so does this.
        """
        document = _get_text_document(self.hwnd())
        selection = document.Selection
        start, end = int(selection.Start), int(selection.End)
        if end > start:
            return selection
        probe = document.Range(start, start + 1)
        if int(probe.End) == start:  # at the very end of the story
            return selection
        return probe

    def _font_attr(self, attr: str) -> Any:
        try:
            return getattr(self._selection().Font, attr)
        except RichEditError:
            raise
        except Exception as exc:
            raise RichEditError(f"Could not read {attr}: {exc}") from exc

    def _apply_font(self, attr: str, value: Any) -> None:
        try:
            setattr(self._selection().Font, attr, value)
        except RichEditError:
            raise
        except Exception as exc:
            raise RichEditError(f"Could not apply {attr}: {exc}") from exc

    def toggle(self, attr: str) -> bool:
        """Toggle Bold, Italic or Underline and return the new state."""
        self._apply_font(attr, _TOM_TOGGLE)
        return int(self._font_attr(attr) or 0) != 0

    def set_font_name(self, name: str) -> None:
        self._apply_font("Name", str(name))

    def set_font_size(self, points: float) -> None:
        self._apply_font("Size", float(points))

    def set_alignment(self, how: str) -> None:
        value = _TOM_ALIGNMENT.get(how)
        if value is None:
            raise RichEditError(f"Unknown alignment: {how!r}")
        try:
            self._selection().Para.Alignment = value
        except RichEditError:
            raise
        except Exception as exc:
            raise RichEditError(f"Could not set alignment: {exc}") from exc

    def set_heading(self, level: int) -> None:
        """Heading 1 to 4 on the paragraph(s) under the selection; 0 is body text."""
        if not 0 <= level <= 4:
            raise RichEditError(f"Heading level out of range: {level}")
        try:
            span = self._selection().Duplicate
            span.Expand(_TOM_UNIT_PARAGRAPH)
            font = span.Font
            if level == 0:
                font.Size = BODY_POINT_SIZE
                font.Bold = _TOM_FALSE
            else:
                font.Size = HEADING_POINT_SIZES[level]
                font.Bold = _TOM_TRUE
        except RichEditError:
            raise
        except Exception as exc:
            raise RichEditError(f"Could not apply heading {level}: {exc}") from exc

    def heading_level_at_caret(self) -> int | None:
        try:
            font = self._format_range().Font
            return heading_level_for_font(float(font.Size or 0), int(font.Bold or 0) != 0)
        except Exception:
            return None

    def describe_caret(self) -> str:
        """Spoken description of the formatting at the caret."""
        try:
            selection = self._format_range()
            font = selection.Font
            parts: list[str] = []
            name = str(getattr(font, "Name", "") or "").strip()
            if name:
                parts.append(name)
            size = float(getattr(font, "Size", 0) or 0)
            if size > 0:
                parts.append(f"{size:g} point")
                heading = heading_level_for_font(size, int(getattr(font, "Bold", 0)) != 0)
                if heading is not None:
                    parts.append(f"heading {heading}")
            if int(getattr(font, "Bold", 0)) != 0:
                parts.append("bold")
            if int(getattr(font, "Italic", 0)) != 0:
                parts.append("italic")
            if int(getattr(font, "Underline", 0)) != 0:
                parts.append("underline")
            phrases = {"center": "centred", "right": "right aligned", "justify": "justified"}
            alignment = _TOM_ALIGNMENT_NAMES.get(int(selection.Para.Alignment))
            if alignment in phrases:
                parts.append(phrases[alignment])
            return ", ".join(parts) if parts else "plain text"
        except RichEditError:
            raise
        except Exception as exc:
            raise RichEditError(f"Could not read caret formatting: {exc}") from exc

    def next_heading(self, from_offset: int, *, reverse: bool) -> tuple[int, int] | None:
        """(start_offset, level) of the next or previous heading paragraph, or None."""
        if not self.native():
            return None
        try:
            document = _get_text_document(self.hwnd())
            probe = document.Range(int(from_offset), int(from_offset))
            step = -1 if reverse else 1
            for _ in range(_MAX_HEADING_SCAN):
                if int(probe.Move(_TOM_UNIT_PARAGRAPH, step)) == 0:
                    return None
                probe.StartOf(_TOM_UNIT_PARAGRAPH, 0)
                start = int(probe.Start)
                if (reverse and start >= from_offset) or (not reverse and start <= from_offset):
                    continue
                para = probe.Duplicate
                para.Expand(_TOM_UNIT_PARAGRAPH)
                font = para.Font
                level = heading_level_for_font(float(font.Size or 0), int(font.Bold or 0) != 0)
                if level is not None:
                    return (start, level)
            return None
        except Exception:
            return None

    def all_headings(self) -> list[tuple[int, int, str]]:
        """Every heading as (start_offset, level, text), in document order."""
        if not self.native():
            return []
        results: list[tuple[int, int, str]] = []
        try:
            document = _get_text_document(self.hwnd())
            probe = document.Range(0, 0)
            probe.StartOf(_TOM_UNIT_PARAGRAPH, 0)
            for _ in range(_MAX_HEADING_SCAN):
                para = probe.Duplicate
                para.Expand(_TOM_UNIT_PARAGRAPH)
                font = para.Font
                level = heading_level_for_font(float(font.Size or 0), int(font.Bold or 0) != 0)
                if level is not None:
                    text = str(para.Text or "").strip()
                    if text:
                        results.append((int(para.Start), level, text))
                if int(probe.Move(_TOM_UNIT_PARAGRAPH, 1)) == 0:
                    break
        except Exception:
            pass
        return results

    def paragraph_text_at(self, offset: int) -> str:
        try:
            document = _get_text_document(self.hwnd())
            para = document.Range(int(offset), int(offset))
            para.Expand(_TOM_UNIT_PARAGRAPH)
            return str(para.Text or "").strip()
        except Exception:
            return ""


def create_editor(wx: Any, parent: Any, mode: str) -> Editor:
    """Build the RichEdit-backed control and wrap it."""
    style = wx.TE_MULTILINE | wx.TE_PROCESS_TAB | wx.TE_NOHIDESEL
    if sys.platform == "win32":
        style |= wx.TE_RICH2
    try:
        control = wx.TextCtrl(parent, style=style)
    except Exception:
        control = wx.TextCtrl(parent, style=wx.TE_MULTILINE | wx.TE_PROCESS_TAB)
    editor = Editor(control, mode)
    editor.set_mode(mode)
    return editor
