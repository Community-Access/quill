"""Document-scale editing on top of :class:`~quill.ui.richedit_rtf_surface.QuillRichEdit`.

QUILL's own editor never needed these: it owns one rich surface per tab, in one
text mode, themed by the notebook around it. A *document* window -- one file,
one window, switchable between plain and rich, themed by itself -- needs five
more things from the same native control, and every one of them is a Rich Edit
message or a TOM call rather than anything wx can express:

* **Text mode.** ``EM_SETTEXTMODE`` puts RICHEDIT50W into ``TM_PLAINTEXT`` so it
  behaves like Notepad (one font, paste arrives as plain text) or
  ``TM_RICHTEXT`` so it behaves like WordPad. The control must be empty when the
  mode changes, which is the caller's job and is why the setter says so.
* **Word wrap.** ``EM_SETTARGETDEVICE`` with ``lParam`` 1 turns wrapping off;
  wx has no portable spelling of that for a control that already exists.
* **View colours and zoom.** ``EM_SETBKGNDCOLOR`` and ``EM_SETZOOM``, so a dark
  theme and a text-size control work on the *view* without rewriting a single
  run's point size -- which matters because run point sizes *are* the heading
  ladder, and zooming by editing them would silently re-level every heading.
* **Whole-document recolour.** A theme is presentation, not document content, so
  a themed foreground is applied to the whole story and reset to ``tomAutoColor``
  before every save. Undo is suspended around it: switching theme must never
  land in the user's undo history.
* **Heading enumeration.** :meth:`RichEditDocument.all_headings` reads the same
  size-and-bold ladder :func:`heading_level_for_font` defines, so a headings list
  and heading navigation cannot disagree about what a heading is.

Kept out of ``richedit_rtf_surface`` deliberately: that module is the editor's
surface contract, every document tab in QUILL is built on it, and it sits at its
size budget. This is an *extension* -- a subclass and a factory, no duplicated
plumbing -- so the repository still holds exactly one TOM path, one RTF
reader/writer, and one heading ladder.

Everything Windows/COM is guarded exactly as the base module guards it: this
module imports on every platform, and each capability degrades to a no-op or a
clear :class:`RichEditRtfError` rather than taking the editor down.
"""

from __future__ import annotations

from typing import Any

from quill.ui.richedit_rtf_surface import (
    _MAX_HEADING_SCAN_PARAGRAPHS,
    _TOM_AVAILABLE,
    _TOM_TOGGLE,
    _TOM_UNIT_PARAGRAPH,
    QuillRichEdit,
    RichEditRtfError,
    _get_text_document,
    heading_level_for_font,
)

__all__ = [
    "LINE_SPACING_DOUBLE",
    "LINE_SPACING_ONE_AND_A_HALF",
    "LINE_SPACING_SINGLE",
    "PLAIN",
    "RICH",
    "RichEditDocument",
    "create_richedit_document",
]

#: The two modes a one-document window can be in.
PLAIN = "plain"
RICH = "rich"

_WM_USER = 0x0400
_EM_SETTEXTMODE = _WM_USER + 89
_EM_GETTEXTMODE = _WM_USER + 90
_EM_SETTARGETDEVICE = _WM_USER + 72
_EM_SETBKGNDCOLOR = _WM_USER + 67
_EM_SETZOOM = _WM_USER + 225

# EM_SETTEXTMODE flags (richedit.h). Multi-level undo and multi-codepage are set
# with either mode: without them the control collapses a paste and the typing
# after it into one undo step, and mishandles non-Latin text on load.
_TM_PLAINTEXT = 1
_TM_RICHTEXT = 2
_TM_MULTILEVELUNDO = 8
_TM_MULTICODEPAGE = 32

# tom.h, for the parts of the object model the base surface has no use for.
_TOM_UNIT_STORY = 6
_TOM_AUTOCOLOR = -9999997
_TOM_SUSPEND = -9999995
_TOM_RESUME = -9999994

#: ``ITextPara.ListType`` (tom.h). Only the two a WordPad-scale editor offers:
#: no list, or a bullet. Numbered lists need a numbering format and a start
#: value to be worth anything, and half a numbered list is worse than none.
_TOM_LIST_NONE = 0
_TOM_LIST_BULLET = 1

#: ``ITextPara.SetLineSpacing`` rules (tom.h). The three WordPad offers, on the
#: three chords WordPad uses (Ctrl+1, Ctrl+5, Ctrl+2).
LINE_SPACING_SINGLE = 0
LINE_SPACING_ONE_AND_A_HALF = 1
LINE_SPACING_DOUBLE = 2

#: Point sizes Grow Font and Shrink Font step through, so the steps land on
#: sizes people recognise instead of drifting one point at a time. WordPad's own
#: ladder, plus the heading ladder's sizes so growing a heading stays on it.
_FONT_SIZE_LADDER: tuple[float, ...] = (
    8.0,
    9.0,
    10.0,
    11.0,
    12.0,
    14.0,
    16.0,
    18.0,
    20.0,
    22.0,
    24.0,
    26.0,
    28.0,
    36.0,
    48.0,
    72.0,
)


def _send(hwnd: int, message: int, wparam: int = 0, lparam: int = 0) -> int:
    """``SendMessageW`` to the control, or 0 with no handle / off Windows."""
    if not (_TOM_AVAILABLE and hwnd):
        return 0
    try:
        from quill.ui.richedit_rtf_surface import _SendMessageW

        return int(_SendMessageW(hwnd, message, wparam, lparam))
    except Exception:  # noqa: BLE001 - a control message must never raise
        return 0


def _colorref(red: int, green: int, blue: int) -> int:
    """A Win32 ``COLORREF`` (0x00BBGGRR) from three 0-255 channels."""
    return (int(red) & 0xFF) | ((int(green) & 0xFF) << 8) | ((int(blue) & 0xFF) << 16)


class RichEditDocument(QuillRichEdit):
    """A :class:`QuillRichEdit` that also owns its mode, its view, and its theme."""

    def __init__(self, surface: Any, mode: str = PLAIN) -> None:
        super().__init__(surface)
        #: The mode the *document* is in. :meth:`current_text_mode` reports what
        #: the control actually answers, which is how a probe tells them apart.
        self.mode = RICH if mode == RICH else PLAIN

    # -- text mode ---------------------------------------------------------- #

    def set_text_mode(self, mode: str) -> None:
        """Switch the control between plain and rich text.

        ``EM_SETTEXTMODE`` is refused by the control unless the document is
        empty, so the caller saves the text, calls this, and puts the text back.
        Off Windows the control is a stock ``wx.TextCtrl`` with one mode, and
        this records the intent without changing anything.
        """
        self.mode = RICH if mode == RICH else PLAIN
        flags = (_TM_RICHTEXT if self.mode == RICH else _TM_PLAINTEXT) | (
            _TM_MULTILEVELUNDO | _TM_MULTICODEPAGE
        )
        _send(self.hwnd(), _EM_SETTEXTMODE, flags, 0)

    def current_text_mode(self) -> str:
        """What the control says its mode is: ``plain``, ``rich`` or ``unknown``."""
        value = _send(self.hwnd(), _EM_GETTEXTMODE)
        if value & _TM_PLAINTEXT:
            return PLAIN
        if value & _TM_RICHTEXT:
            return RICH
        return "unknown"

    # -- view: wrap, background, zoom --------------------------------------- #

    def set_word_wrap(self, wrap: bool) -> None:
        """Wrap to the window (``lParam`` 0) or never wrap (``lParam`` 1)."""
        _send(self.hwnd(), _EM_SETTARGETDEVICE, 0, 0 if wrap else 1)

    def set_background_color(self, red: int, green: int, blue: int) -> None:
        """Paint the control's background. ``wParam`` 0 means "use my colour"."""
        _send(self.hwnd(), _EM_SETBKGNDCOLOR, 0, _colorref(red, green, blue))

    def set_zoom(self, numerator: float, denominator: float) -> None:
        """Scale the *view* by ``numerator/denominator``; ``0, 0`` restores 100%.

        Used in rich mode so a text-size control enlarges the document without
        touching any run's point size -- the sizes are the heading ladder, and
        rewriting them would re-level every heading in the document.
        """
        if numerator <= 0 or denominator <= 0:
            _send(self.hwnd(), _EM_SETZOOM, 0, 0)
            return
        _send(
            self.hwnd(),
            _EM_SETZOOM,
            int(round(numerator * 100)),
            int(round(denominator * 100)),
        )

    # -- theme -------------------------------------------------------------- #

    def set_document_color(self, rgb: tuple[int, int, int] | None) -> None:
        """Colour every run in the story, or reset to automatic when *rgb* is None.

        A theme is presentation, so it is applied across the whole story and
        removed again (``tomAutoColor``) before a save -- a dark theme must never
        leak light grey text into somebody's file. Undo is suspended around the
        change, because a theme switch is not an edit and has no business in the
        undo history.
        """
        document = _get_text_document(self.hwnd())
        try:
            try:
                document.Undo(_TOM_SUSPEND)
            except Exception:  # noqa: BLE001 - suspending undo is best effort
                pass
            story = document.Range(0, 0)
            story.Expand(_TOM_UNIT_STORY)
            if rgb is None:
                story.Font.ForeColor = _TOM_AUTOCOLOR
            else:
                story.Font.ForeColor = _colorref(*rgb)
        except Exception as exc:  # noqa: BLE001 - map COM failure to our error
            raise RichEditRtfError(f"Could not recolour the document: {exc}") from exc
        finally:
            try:
                document.Undo(_TOM_RESUME)
            except Exception:  # noqa: BLE001
                pass

    # -- formatting readback ------------------------------------------------ #

    def toggle_font_attr(self, attr: str) -> bool:
        """Toggle ``Bold``/``Italic``/``Underline`` and report the resulting state.

        The base surface's ``apply_bold`` and friends toggle without answering,
        which is right for a toolbar that re-reads the caret afterwards. A window
        that *speaks* the outcome ("Bold on") needs the answer in the same
        breath, so what it announces is the state the control ended in rather
        than the state the caller assumed.
        """
        self._apply_font(attr, _TOM_TOGGLE)
        try:
            return int(getattr(self._selection().Font, attr) or 0) != 0
        except RichEditRtfError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RichEditRtfError(f"Could not read {attr} back: {exc}") from exc

    def set_alignment_justify(self) -> None:
        """Justify the paragraph. ``set_alignment("justify")`` by another name.

        Present so the command layer never has to know the vocabulary string,
        and so justify sits beside the other three alignments at this level
        rather than being the one that goes through a different door.
        """
        self.set_alignment("justify")

    def set_bullets(self, enabled: bool) -> None:
        """Turn a bullet list on or off across the paragraphs under the selection.

        ``ITextPara.ListType``. Numbered lists are deliberately not offered: a
        number needs a format and a start value to be worth anything, and a
        numbered list that cannot be continued or restarted is worse than none.
        """
        try:
            span = self._selection().Duplicate
            span.Expand(_TOM_UNIT_PARAGRAPH)
            span.Para.ListType = _TOM_LIST_BULLET if enabled else _TOM_LIST_NONE
        except RichEditRtfError:
            raise
        except Exception as exc:  # noqa: BLE001 - map COM failure to our error
            raise RichEditRtfError(f"Could not change the list: {exc}") from exc

    def bullets_at_caret(self) -> bool:
        """True when the caret is in a bulleted paragraph. Never raises."""
        try:
            para = self._format_range().Duplicate
            para.Expand(_TOM_UNIT_PARAGRAPH)
            return int(para.Para.ListType or 0) == _TOM_LIST_BULLET
        except Exception:  # noqa: BLE001 - a readback must never break a keypress
            return False

    def set_line_spacing(self, rule: int) -> None:
        """Single, one-and-a-half or double spacing on the selected paragraphs.

        ``ITextPara.SetLineSpacing(rule, spacing)``. The three rules here ignore
        the second argument, so it is passed as 0; the rules that do use it
        (at-least, exactly, multiple) are not offered.
        """
        try:
            span = self._selection().Duplicate
            span.Expand(_TOM_UNIT_PARAGRAPH)
            span.Para.SetLineSpacing(int(rule), 0.0)
        except RichEditRtfError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RichEditRtfError(f"Could not set the line spacing: {exc}") from exc

    def step_font_size(self, *, larger: bool) -> float:
        """Move the selection one step along the size ladder; returns the new size.

        A ladder rather than plus-or-minus-one point, because stepping by a
        point takes eight presses to get anywhere and lands on sizes nobody
        chose. The ladder includes the heading sizes, so growing a heading stays
        on the heading ladder rather than falling off it.
        """
        try:
            font = self._selection().Font
            current = float(getattr(font, "Size", 0) or 0) or 11.0
            if larger:
                nxt = next((s for s in _FONT_SIZE_LADDER if s > current + 0.01), current)
            else:
                nxt = next((s for s in reversed(_FONT_SIZE_LADDER) if s < current - 0.01), current)
            font.Size = nxt
            return float(nxt)
        except RichEditRtfError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RichEditRtfError(f"Could not change the font size: {exc}") from exc

    def heading_level_at_caret(self) -> int | None:
        """The heading level the caret is in, or ``None``. Never raises."""
        try:
            font = self._format_range().Font
            return heading_level_for_font(
                float(getattr(font, "Size", 0) or 0), int(getattr(font, "Bold", 0) or 0) != 0
            )
        except Exception:  # noqa: BLE001 - a readback must never break a keypress
            return None

    def all_headings(self) -> list[tuple[int, int, str]]:
        """Every heading as ``(start_offset, level, text)``, in document order.

        The same ladder :meth:`next_heading` walks, read in one pass, so a
        headings list and Next Heading cannot disagree. Best effort: an empty (or
        partial) list off Windows or on any TOM error, never an exception.
        """
        if not self.rtf_available():
            return []
        results: list[tuple[int, int, str]] = []
        try:
            document = _get_text_document(self.hwnd())
            probe = document.Range(0, 0)
            probe.StartOf(_TOM_UNIT_PARAGRAPH, 0)
            for _ in range(_MAX_HEADING_SCAN_PARAGRAPHS):
                para = probe.Duplicate
                para.Expand(_TOM_UNIT_PARAGRAPH)
                font = para.Font
                level = heading_level_for_font(
                    float(getattr(font, "Size", 0) or 0), int(getattr(font, "Bold", 0) or 0) != 0
                )
                if level is not None:
                    text = str(para.Text or "").strip()
                    if text:
                        results.append((int(para.Start), level, text))
                if int(probe.Move(_TOM_UNIT_PARAGRAPH, 1)) == 0:
                    break
        except Exception:  # noqa: BLE001 - enumeration is best effort
            return results
        return results

    def paragraph_text_at(self, offset: int) -> str:
        """The text of the paragraph containing *offset* ("" on any failure).

        What heading navigation speaks once it has moved: the level alone
        ("Heading 2") tells a listener the shape of the document but not where in
        it they have landed.
        """
        try:
            document = _get_text_document(self.hwnd())
            para = document.Range(int(offset), int(offset))
            para.Expand(_TOM_UNIT_PARAGRAPH)
            return str(para.Text or "").strip()
        except Exception:  # noqa: BLE001 - a readback must never break a keypress
            return ""


def create_richedit_document(wx_module: Any, parent: Any, style: int, mode: str = PLAIN) -> Any:
    """Build a document-scale Rich Edit surface wrapped in :class:`RichEditDocument`.

    Mirrors :func:`~quill.ui.richedit_rtf_surface.create_richedit_rtf` -- the same
    control, the same fallback, the same ``surface_kind`` tag -- and additionally
    puts the control into *mode* before returning it. The wrapper is attached at
    ``quill_richedit``, exactly where the base factory puts it, so anything that
    already talks to a QUILL rich surface talks to this one unchanged.
    """
    from quill.ui.richedit_rtf_surface import SURFACE_KIND

    try:
        surface = wx_module.TextCtrl(
            parent, style=style | wx_module.TE_RICH2 | wx_module.TE_NOHIDESEL
        )
    except Exception:  # noqa: BLE001 - hosting is best effort; fall back to wx
        surface = wx_module.TextCtrl(parent, style=style)
    try:
        surface.surface_kind = SURFACE_KIND
        wrapper = RichEditDocument(surface, mode)
        surface.quill_richedit = wrapper
        wrapper.set_text_mode(mode)
    except Exception:  # noqa: BLE001 - tagging is best effort; the control works
        pass
    return surface
