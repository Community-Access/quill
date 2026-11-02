"""QUILL Lite's Insert Image: the address, then the alt text, never a placeholder."""

from __future__ import annotations

from typing import Any

from quill.apps.lite_dialogs_entry import ask_text
from quill.core.tagging import InsertionResult

__all__ = ["insert_markdown_image"]


def insert_markdown_image(win: Any, target: str, selected: str) -> None:
    """An image always comes with the question of its alt text.

    A picture inserted with a placeholder for alt text is a picture a
    screen reader announces as "text", which is worse than nothing. So the
    alt text is asked for right after the address, starting from whatever
    was selected; left empty, the image goes in with empty alt text (the
    decorative-image form) and the announcement says how to get a draft.
    """
    alt = (
        ask_text(
            win,
            title="Insert Image",
            label="&Alt text:",
            help_text=(
                "What the picture shows and why it is there, in a short "
                "sentence. Leave it empty only for a decorative image."
            ),
            value=selected,
        )
        or ""
    ).strip()
    markup = f"![{alt}]({target or 'https://example.com/image.png'})"
    win._apply_insertion(InsertionResult(markup, len(markup)))
    if alt:
        win._announce("Inserted Image")
    else:
        win._announce("Inserted Image with no alt text. Tools, AI, Propose Alt Text can draft it.")
    win.control.SetFocus()
