"""Screen reader facts for the shared support form.

The user chooses the reader in the form. A process list cannot establish which
of several running readers is speaking, so only an unambiguous result prefills
the choice. Paths and process IDs stay out of mail sent to support.
"""

from __future__ import annotations

import sys


def running_reader_names() -> set[str]:
    if sys.platform != "win32":
        return set()
    try:
        from quill.platform.windows.screen_reader_info import get_running_screen_readers

        names = {str(item["name"]) for item in get_running_screen_readers()}
        from quill.platform.windows.sr_detect import narrator_event_present

        if narrator_event_present():
            names.add("Narrator")
        return names
    except Exception:  # noqa: BLE001 - support must remain available
        return set()


def detected_reader_name() -> str:
    names = running_reader_names()
    return next(iter(names)) if len(names) == 1 else ""


def screen_reader_support_facts(selected: str) -> dict[str, str]:
    """Collect current, selected-reader facts immediately before mail handoff."""
    if sys.platform != "win32" or selected not in {"JAWS", "NVDA"}:
        return {}
    try:
        from quill.platform.windows.screen_reader_info import get_running_screen_readers

        matches = [item for item in get_running_screen_readers() if item.get("name") == selected]
    except Exception:  # noqa: BLE001 - a failed probe must not block a ticket
        return {}
    if not matches:
        return {"Screen reader detection": f"{selected} was selected; no running process was found"}
    facts = {"Screen reader detection": f"{selected} running ({len(matches)} process(es))"}
    versions = sorted({str(item["version"]) for item in matches if item.get("version")})
    file_versions = sorted({
        str(item["file_version"]) for item in matches if item.get("file_version")
    })
    if versions:
        facts["Screen reader version"] = ", ".join(versions)
    if file_versions and file_versions != versions:
        facts["Screen reader file version"] = ", ".join(file_versions)
    if selected == "NVDA":
        if any(item.get("nvda_api_connected") for item in matches):
            facts["NVDA Controller Client"] = "Connected"
    return facts
