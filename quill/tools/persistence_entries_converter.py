"""Quill Converter: its reviewed persistence sites.

Split from :mod:`quill.tools.persistence_audit` under GATE-11, as the family,
radio, studio and WordPress entries are. The Auphonic token is never written
to any of these (Credential Manager).
"""

from __future__ import annotations

CONVERTER_ENTRIES: dict[str, str] = {
    "core/converter_settings.py::save": "versioned",
    # Process with Auphonic: what is waiting to be fetched, and every
    # production sent (Production History).
    "core/publish/auphonic_plan.py::save_pending": "versioned",
    "core/publish/auphonic_history.py::save_history": "versioned",
}
