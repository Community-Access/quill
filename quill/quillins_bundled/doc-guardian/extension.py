"""Document Guardian — document event handlers.

Three lifecycle hooks: before_close (warn on short docs), before_save
(stamp an Updated: line), after_save (confirm with path and size).
"""

from __future__ import annotations

import os
from datetime import datetime


def on_before_close(api, event: dict) -> None:
    if not api.get_setting("close_guard_enabled", True):
        return

    file_path: str = event.get("file_path", "")
    if file_path:
        # File already exists on disk — not a brand-new unsaved document.
        # Only warn if it contains the TODO marker.
        marker: str = api.get_setting("todo_marker", "TODO")
        if not marker:
            return
        try:
            text = api.get_text()
        except Exception:
            return
        if marker.lower() in text.lower():
            api.announce(f"This document contains {marker}. Review before closing.")
        return

    # Unsaved new document — check word count.
    try:
        text = api.get_text()
    except Exception:
        return

    words = len(text.split())
    threshold = int(api.get_setting("min_words_threshold", 3))
    if threshold > 0 and 0 < words < threshold:
        api.announce(
            f"Closing unsaved document with only {words} word{'s' if words != 1 else ''}."
            " Press Ctrl+Z to undo if this was accidental."
        )

    marker = api.get_setting("todo_marker", "TODO")
    if marker and marker.lower() in text.lower():
        api.announce(f"This document contains {marker} and is about to close.")


def on_before_save(api, event: dict) -> None:
    if not api.get_setting("save_stamp_enabled", False):
        return

    try:
        text: str = api.get_text()
    except Exception:
        return

    fmt = api.get_setting("stamp_format", "long")
    now = datetime.now()
    if fmt == "iso":
        stamp = now.strftime("%Y-%m-%dT%H:%M:%S")
    elif fmt == "date_only":
        stamp = now.strftime("%Y-%m-%d")
    else:
        stamp = now.strftime("%A, %d %B %Y at %H:%M")

    new_line = f"Updated: {stamp}"
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("updated:"):
            lines[i] = new_line
            api.set_text("\n".join(lines))
            return
    # No existing Updated: line — do nothing.


def on_after_save(api, event: dict) -> None:
    if not api.get_setting("save_confirm_enabled", False):
        return

    file_path: str = event.get("file_path", "")
    if not file_path:
        api.announce("Saved.")
        return

    try:
        size = os.path.getsize(file_path)
        name = os.path.basename(file_path)
        if size < 1024:
            size_str = f"{size} bytes"
        elif size < 1024 * 1024:
            size_str = f"{size // 1024} KB"
        else:
            size_str = f"{size // (1024 * 1024)} MB"
        api.announce(f"Saved: {name}, {size_str}.")
    except OSError:
        api.announce(f"Saved: {os.path.basename(file_path)}.")


def on_enabled(api, event: dict) -> None:
    api.log("Document Guardian enabled — monitoring closes, saves, and sessions.")
    api.announce("Document Guardian is now active.")


def on_disabled(api, event: dict) -> None:
    api.log("Document Guardian disabled.")
    api.announce("Document Guardian is now inactive.")


def on_shutdown(api, event: dict) -> None:
    api.log("Document Guardian: QUILL shutting down, nothing to clean up.")


def register(api) -> None:
    api.register_command("on_before_close", on_before_close)
    api.register_command("on_before_save", on_before_save)
    api.register_command("on_after_save", on_after_save)
    api.register_command("on_enabled", on_enabled)
    api.register_command("on_disabled", on_disabled)
    api.register_command("on_shutdown", on_shutdown)
