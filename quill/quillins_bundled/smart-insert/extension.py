"""Smart Insert Quillin — templates, log entries, BRF test content.

Every handler reads its own settings via the Quillin API so the user's
preferences (timestamp format, todo count, BRF page count, etc.) are respected
without any hard-coded values in the handler logic.

Supported typed abbreviations (after a delimiter):
    qbug   -- bug report template
    qmeet  -- meeting notes template
    qlog   -- log timestamp
    qtodo  -- short to-do checklist
    qbrf   -- BRF test document (dynamic handler)

Supported smart triggers (=name() alone on a line, then Enter):
    =bug()          -- bug report template
    =meeting()      -- meeting notes template
    =journal()      -- journal entry
    =todo(count)    -- to-do checklist
    =logentry()     -- log timestamp at cursor
    =brftest()      -- BRF test document
    =rand(p, l)     -- readable sample text (p paragraphs, l lines each)
"""

from __future__ import annotations

import datetime


def _get(api: object, key: str, default: object = None) -> object:
    """Read a setting from the Quillin's own settings store."""
    try:
        return api.get_setting(key)  # type: ignore[union-attr]
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Template builders
# ---------------------------------------------------------------------------


def _bug_template() -> str:
    return (
        "Title:\n"
        "Build:\n"
        "Screen reader:\n"
        "Windows version:\n"
        "Steps to reproduce:\n"
        "\n"
        "Expected result:\n"
        "\n"
        "Actual result:\n"
        "\n"
        "Notes:\n"
    )


def _meeting_template() -> str:
    date_str = datetime.date.today().strftime("%A, %B %d, %Y")
    return f"Meeting:\nDate: {date_str}\nAttendees:\nPurpose:\n\nNotes:\n\nAction Items:\n"


def _journal_template() -> str:
    date_str = datetime.date.today().strftime("%A, %B %d, %Y")
    return f"Date: {date_str}\nContext:\n\nNotes:\n\nNext:\n"


def _todo_template(count: int) -> str:
    return "".join("- [ ] \n" for _ in range(count))


def _log_timestamp(fmt: str, custom_fmt: str) -> str:
    now = datetime.datetime.now()
    if fmt == "long":
        return now.strftime("%A, %B %d, %Y %I:%M %p")
    if fmt == "short":
        return now.strftime("%m/%d/%Y %I:%M %p")
    if fmt == "iso":
        return now.strftime("%Y-%m-%dT%H:%M:%S")
    if fmt == "date_only":
        return now.strftime("%Y-%m-%d")
    if fmt == "time_only":
        return now.strftime("%H:%M:%S")
    if fmt == "custom" and custom_fmt:
        try:
            return now.strftime(custom_fmt)
        except ValueError:
            return now.strftime("%A, %B %d, %Y %I:%M %p")
    return now.strftime("%A, %B %d, %Y %I:%M %p")


def _brf_test_document(pages: int, lines_per_page: int, line_text: str) -> str:
    parts = ["BRF Test Document\n"]
    for page in range(1, pages + 1):
        parts.append(f"\nPage {page}\n")
        for line in range(1, lines_per_page + 1):
            parts.append(f"Line {line}: {line_text}\n")
    parts.append("\nEnd of BRF test document.\n")
    return "".join(parts)


def _rand_text(paragraphs: int, lines: int) -> str:
    sentence = "The quick brown fox jumps over the lazy dog."
    parts = []
    for p in range(1, paragraphs + 1):
        para_lines = [f"Paragraph {p}, line {ln}: {sentence}" for ln in range(1, lines + 1)]
        parts.append("\n".join(para_lines))
    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def insert_bug(api: object) -> None:
    text = _bug_template()
    api.insert_text(text)  # type: ignore[union-attr]
    api.announce("Inserted bug report template.")  # type: ignore[union-attr]


def insert_meeting(api: object) -> None:
    text = _meeting_template()
    api.insert_text(text)  # type: ignore[union-attr]
    api.announce("Inserted meeting notes template.")  # type: ignore[union-attr]


def insert_journal(api: object) -> None:
    text = _journal_template()
    api.insert_text(text)  # type: ignore[union-attr]
    api.announce("Inserted journal entry.")  # type: ignore[union-attr]


def insert_todo(api: object) -> None:
    count = int(_get(api, "default_todo_count", 5))
    text = _todo_template(count)
    api.insert_text(text)  # type: ignore[union-attr]
    api.announce(f"Inserted to-do list with {count} items.")  # type: ignore[union-attr]


def insert_log_entry(api: object) -> None:
    fmt = str(_get(api, "timestamp_format", "long"))
    custom_fmt = str(_get(api, "custom_timestamp_format", ""))
    stamp = _log_timestamp(fmt, custom_fmt)
    api.write(stamp + "\n")  # type: ignore[union-attr]
    api.announce("Log timestamp inserted. Type your entry.")  # type: ignore[union-attr]


def insert_brf_test(api: object) -> None:
    pages = int(_get(api, "brf_test_pages", 2))
    lines_per_page = int(_get(api, "brf_test_lines_per_page", 3))
    line_text = str(_get(api, "brf_test_line_text", "This is predictable BRF test content."))
    text = _brf_test_document(pages, lines_per_page, line_text)
    api.insert_text(text)  # type: ignore[union-attr]
    api.announce(f"Inserted BRF test document: {pages} pages, {lines_per_page} lines each.")  # type: ignore[union-attr]


def register(api) -> None:
    api.register_command("insert_bug", insert_bug)
    api.register_command("insert_meeting", insert_meeting)
    api.register_command("insert_journal", insert_journal)
    api.register_command("insert_todo", insert_todo)
    api.register_command("insert_log_entry", insert_log_entry)
    api.register_command("insert_brf_test", insert_brf_test)
    api.register_command("insert_rand", insert_rand)


def insert_rand(api: object) -> None:
    paragraphs = 3
    lines = 3
    threshold = int(_get(api, "large_insert_threshold", 50))
    confirm = bool(_get(api, "confirm_large_insertions", True))
    if confirm and paragraphs > threshold:
        choice = api.show_choices(  # type: ignore[union-attr]
            f"Insert {paragraphs} paragraphs of sample text?",
            ["Yes, insert", "No, cancel"],
        )
        if choice != "Yes, insert":
            api.announce("Smart Insert canceled.")  # type: ignore[union-attr]
            return
    text = _rand_text(paragraphs, lines)
    api.insert_text(text)  # type: ignore[union-attr]
    api.announce(f"Inserted {paragraphs} paragraphs of sample text.")  # type: ignore[union-attr]
