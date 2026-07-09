"""Send / Copy as Email (#900): hand a Fragment off to the user's mail client.

Two hand-off shapes, both built on the same Fragment spine #897/#895 use:

- **Send as Email** builds a ``mailto:`` URL (subject + body, both
  percent-encoded) and opens it via the OS default handler -- the simplest,
  safest option, reusing exactly the mechanism ``main_frame_power_tools.py``
  already uses to open an email link found in the document.
- **Copy as Email Body** renders the Fragment in the chosen format and puts
  it on the clipboard, for the common case where a mail client silently
  truncates or rejects a long ``mailto:`` body.

No SMTP, no account management, no Outlook COM -- a hand-off convenience,
not a mail client. Pure and wx-free; ``main_frame_power_tools.py``/a mixin
does the actual ``webbrowser.open``/clipboard call.
"""

from __future__ import annotations

from urllib.parse import quote

from quill.core.fragment import Fragment, FragmentFormat, render_fragment

__all__ = ["build_mailto"]


def build_mailto(frag: Fragment, fmt: FragmentFormat, *, subject: str = "") -> str:
    """Build a ``mailto:`` URL whose body is *frag* rendered in *fmt*.

    Subject defaults to the Fragment's title, or a generic fallback when
    neither is given. Pure and testable -- no ``webbrowser``, no wx.
    """
    body = render_fragment(frag, fmt)
    resolved_subject = subject or frag.title or "Shared from QUILL"
    query = f"subject={quote(resolved_subject)}&body={quote(body)}"
    return f"mailto:?{query}"
