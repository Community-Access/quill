"""Copy With Source onto the clipboard, honouring "Markdown clipboard format".

The decision (which flavour, if any) is :mod:`quill.core.markdown_clipboard`;
this is the wx half that puts plain text and the formatted copy on the
clipboard together. Plain text only goes through the host's own
``_copy_to_clipboard`` exactly as before.
"""

from __future__ import annotations

from typing import Any

from quill.core.markdown_clipboard import FormattedCopy, clipboard_mode, formatted_copy


def copy_with_source_payload(host: Any, payload: str) -> bool:
    """Put *payload* (selection plus source note) on the clipboard. True on success."""
    from quill.core.browser_preview import guess_preview_kind

    document = getattr(host, "document", None)
    kind = guess_preview_kind(getattr(document, "path", None), host.editor.GetValue())
    extra = formatted_copy(payload, document_kind=kind, mode=clipboard_mode(host.settings))
    if extra is None:
        return bool(host._copy_to_clipboard(payload))
    return copy_text_and_formatted(host._wx, payload, extra)


def copy_text_and_formatted(wx: Any, text: str, extra: FormattedCopy) -> bool:
    """Plain text plus one formatted flavour, retried like every clipboard write."""
    from quill.ui.clipboard_retry import with_clipboard_read_retry

    clipboard = getattr(wx, "TheClipboard", None)
    if clipboard is None:
        return False

    def _attempt() -> bool:
        if not clipboard.Open():
            return False
        try:
            composite = wx.DataObjectComposite()
            composite.Add(wx.TextDataObject(text), True)
            if extra.kind == "html":
                composite.Add(wx.HTMLDataObject(extra.data))
            else:
                rtf = wx.CustomDataObject(wx.DataFormat("Rich Text Format"))
                rtf.SetData(extra.data.encode("ascii", errors="ignore"))
                composite.Add(rtf)
            return bool(clipboard.SetData(composite) or True)
        except Exception:  # noqa: BLE001 - a busy clipboard is not a crash
            return False
        finally:
            clipboard.Close()

    return bool(with_clipboard_read_retry(wx, _attempt, surface_errors=False))


__all__ = ["copy_text_and_formatted", "copy_with_source_payload"]
