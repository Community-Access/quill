"""Windows HTML/RTF email-clipboard payload builder -- DEAD CODE (tech debt).

This module builds an HTML/RTF clipboard payload via the Windows CF_HTML
format (ctypes + win32 clipboard APIs). It currently has ZERO callers anywhere
in the tree and is not wired into any menu or command. It is intentionally
retained as a marker for the email-clipboard feature (#900 sends/copies as
email via a different path today): if this is ever revived, it needs a
``quill/platform/macos/clipboard.py`` counterpart using ``NSPasteboard``
instead of CF_HTML, which degrades to plain text on macOS today (see macOS
review finding #52). Flagged here rather than deleted so the Windows-only
assumption is explicit and a future contributor does not assume it works
cross-platform. Tracked in ``docs/planning/review.md`` (#12).
"""

from __future__ import annotations

import ctypes
import html
import os
from dataclasses import dataclass
from typing import Literal

from quill.core.browser_preview import render_preview_body

EmailClipboardFormat = Literal["html", "rtf"]

_CF_UNICODETEXT = 13
_GMEM_MOVEABLE = 0x0002
_HTML_FORMAT_NAME = "HTML Format"
_RTF_FORMAT_NAME = "Rich Text Format"


@dataclass(frozen=True, slots=True)
class EmailClipboardPayload:
    text: str
    html_fragment: str | None = None
    rtf_fragment: str | None = None


if os.name == "nt":
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
else:  # pragma: no cover - Windows-only feature surface
    _user32 = None
    _kernel32 = None


def build_email_clipboard_payload(
    text: str,
    *,
    source_kind: str,
    output_format: EmailClipboardFormat,
) -> EmailClipboardPayload:
    cleaned_text = text.rstrip()
    if output_format == "html":
        if source_kind in {"markdown", "html"}:
            body_fragment = render_preview_body(cleaned_text, source_kind)
        else:
            body_fragment = f"<pre>{html.escape(cleaned_text)}</pre>"
        return EmailClipboardPayload(text=cleaned_text, html_fragment=body_fragment)

    return EmailClipboardPayload(
        text=cleaned_text,
        rtf_fragment=_build_rtf_fragment(cleaned_text),
    )


def copy_email_clipboard(
    payload: EmailClipboardPayload, output_format: EmailClipboardFormat
) -> bool:
    if os.name != "nt":
        return False
    if _user32 is None or _kernel32 is None:
        return False

    unicode_text = _encode_wide_null(payload.text)
    clipboard_items: list[tuple[int, bytes]] = [(_CF_UNICODETEXT, unicode_text)]
    if output_format == "html" and payload.html_fragment is not None:
        clipboard_items.append((
            _register_clipboard_format(_HTML_FORMAT_NAME),
            _build_cf_html(payload.html_fragment),
        ))
    if output_format == "rtf" and payload.rtf_fragment is not None:
        clipboard_items.append((
            _register_clipboard_format(_RTF_FORMAT_NAME),
            payload.rtf_fragment.encode("ascii", errors="ignore") + b"\x00",
        ))

    if not _user32.OpenClipboard(None):
        return False
    try:
        if not _user32.EmptyClipboard():
            return False
        for format_id, data in clipboard_items:
            handle = _global_alloc(data)
            if handle is None:
                return False
            if not _user32.SetClipboardData(format_id, handle):
                return False
        return True
    finally:
        _user32.CloseClipboard()


def _register_clipboard_format(name: str) -> int:
    return int(_user32.RegisterClipboardFormatW(name))


def _global_alloc(data: bytes) -> int | None:
    handle = _kernel32.GlobalAlloc(_GMEM_MOVEABLE, len(data))
    if not handle:
        return None
    pointer = _kernel32.GlobalLock(handle)
    if not pointer:
        return None
    try:
        ctypes.memmove(pointer, data, len(data))
    finally:
        _kernel32.GlobalUnlock(handle)
    return int(handle)


def _encode_wide_null(text: str) -> bytes:
    return text.encode("utf-16le") + b"\x00\x00"


def _build_cf_html(fragment: str) -> bytes:
    html_document = (
        '<!doctype html><html><head><meta charset="utf-8"></head><body>'
        f"<!--StartFragment-->{fragment}<!--EndFragment-->"
        "</body></html>"
    )
    html_bytes = html_document.encode("utf-8")
    marker_start = html_bytes.index(b"<!--StartFragment-->") + len(b"<!--StartFragment-->")
    marker_end = html_bytes.index(b"<!--EndFragment-->")
    header_template = (
        "Version:0.9\r\n"
        "StartHTML:{start_html:010d}\r\n"
        "EndHTML:{end_html:010d}\r\n"
        "StartFragment:{start_fragment:010d}\r\n"
        "EndFragment:{end_fragment:010d}\r\n"
    )
    header_placeholder = header_template.format(
        start_html=0,
        end_html=0,
        start_fragment=0,
        end_fragment=0,
    ).encode("ascii")
    start_html = len(header_placeholder)
    end_html = start_html + len(html_bytes)
    start_fragment = start_html + marker_start
    end_fragment = start_html + marker_end
    header = header_template.format(
        start_html=start_html,
        end_html=end_html,
        start_fragment=start_fragment,
        end_fragment=end_fragment,
    ).encode("ascii")
    return header + html_bytes


def _build_rtf_fragment(text: str) -> str:
    escaped = []
    for character in text:
        code_point = ord(character)
        if character == "\\":
            escaped.append("\\\\")
        elif character == "{":
            escaped.append("\\{")
        elif character == "}":
            escaped.append("\\}")
        elif character == "\n":
            escaped.append("\\par\n")
        elif code_point > 126:
            escaped.append(f"\\u{code_point}?")
        else:
            escaped.append(character)
    return "{\\rtf1\\ansi\\deff0 " + "".join(escaped) + "}"
