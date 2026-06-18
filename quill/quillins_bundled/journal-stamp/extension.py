"""Journal Stamp — document event handlers.

Fires on document.created, document.after_save, and
document.loaded_from_session. All user-visible behavior is driven by
per-Quillin settings; every mutation is announced so screen reader users
always know what changed.
"""

from __future__ import annotations

from datetime import date


def on_document_created(api, event: dict) -> None:
    if not api.get_setting("enabled", True):
        return

    path: str = event.get("file_path", "")
    pattern_raw: str = api.get_setting("folder_pattern", "journal,diary,notes")
    keywords = [k.strip().lower() for k in pattern_raw.split(",") if k.strip()]
    if keywords and not any(kw in path.lower() for kw in keywords):
        return

    fmt = api.get_setting("date_format", "long")
    if fmt == "iso":
        header = date.today().isoformat()
    elif fmt == "us":
        header = date.today().strftime("%B %-d, %Y")
    elif fmt == "custom":
        pattern = api.get_setting("custom_date_pattern", "%A, %d %B %Y")
        header = date.today().strftime(pattern)
    else:
        header = date.today().strftime("%A, %d %B %Y")

    sep = api.get_setting("header_separator", "blank_line")
    if sep == "blank_line":
        text = f"{header}\n\n"
    elif sep == "dashes":
        text = f"{header}\n{'-' * len(header)}\n\n"
    else:
        text = f"{header}\n"

    api.insert_text(text)
    api.announce(f"Journal header: {header}")


def on_after_save(api, event: dict) -> None:
    mode = api.get_setting("wordcount_mode", "always")
    if mode == "off":
        return

    try:
        text: str = api.get_text()
    except Exception:
        return

    words = len(text.split())
    goal = int(api.get_setting("daily_goal", 0))

    if mode == "goal" and goal <= 0:
        return

    if goal > 0:
        remaining = max(0, goal - words)
        if remaining == 0:
            api.announce(f"Saved. {words} words — goal reached!")
        else:
            api.announce(f"Saved. {words} words. {remaining} to go.")
    else:
        api.announce(f"Saved. {words} words.")


def on_session_restore(api, event: dict) -> None:
    if not api.get_setting("announce_restore", True):
        return
    title: str = event.get("title", "this document")
    api.announce(f"Restored from previous session: {title}")


def on_enabled(api, event: dict) -> None:
    api.log("Journal Stamp enabled — ready to stamp new journal documents.")


def on_settings_changed(api, event: dict) -> None:
    key: str = event.get("key", "")
    value = event.get("value")
    api.log(f"Journal Stamp setting updated: {key} = {value!r}")


def register(api) -> None:
    api.register_command("on_document_created", on_document_created)
    api.register_command("on_after_save", on_after_save)
    api.register_command("on_session_restore", on_session_restore)
    api.register_command("on_enabled", on_enabled)
    api.register_command("on_settings_changed", on_settings_changed)
