"""BRF Tools — braille file-type handler.

Beyond its preferences page, BRF Tools registers a file-type handler that fires
when a ``.brf`` or ``.brl`` document opens. It announces the file type and, when
the ``announce_page_count`` preference is on, reports the braille page count.

Demonstrates the ``file_types`` contribution and the ``on_file_opened(api, event)``
handler signature. The event context carries ``file_path``, ``extension``, and
``filename``.
"""

from __future__ import annotations

_api = None

# Braille pages in a BRF/BRL file are separated by ASCII form feeds (0x0C).
_FORM_FEED = "\x0c"


def setup(api) -> None:
    global _api
    _api = api
    api.log("BRF Tools: setup() called")


def register(api) -> None:
    """Layer 2 entry point. BRF Tools has no command handlers, only events."""
    setup(api)


def on_brf_opened(api, event: dict) -> None:
    """Announce a braille file and (optionally) its braille page count."""
    extension = str(event.get("extension", "")).lstrip(".").upper() or "braille"
    filename = str(event.get("filename", "")) or "file"
    message = f"{extension} braille file opened: {filename}."
    if api.get_setting("announce_page_count", True):
        pages = _braille_page_count(api)
        if pages is not None:
            message += f" {pages} braille page{'s' if pages != 1 else ''}."
    api.announce(message)
    api.log(f"BRF Tools: {message}")


def _braille_page_count(api) -> int | None:
    """Count braille pages by form feeds in the open document, or None on error."""
    try:
        text: str = api.get_text()
    except Exception:
        return None
    if not text:
        return 0
    # A trailing form feed does not start a new page; otherwise pages = FFs + 1.
    form_feeds = text.count(_FORM_FEED)
    if text.endswith(_FORM_FEED):
        return form_feeds
    return form_feeds + 1
