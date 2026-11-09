"""The language-server switches, read from a settings file.

Kept out of :mod:`quill.core.settings` (GATE-11), the way the dictation fields
are: the fields themselves are on :class:`quill.core.settings.Settings`, under
the same names QUILL Lite uses; this reads them, with their defaults.
"""

from __future__ import annotations

from typing import Any

__all__ = ["language_server_fields"]


def language_server_fields(data: dict[str, Any]) -> dict[str, Any]:
    """The language-server switches in *data*, each with its default."""
    off = data.get("language_servers_off", [])
    return {
        "language_servers_enabled": bool(data.get("language_servers_enabled", True)),
        "language_servers_off": [str(name) for name in off] if isinstance(off, list) else [],
        "language_server_completions": bool(data.get("language_server_completions", True)),
        "language_server_problems": bool(data.get("language_server_problems", True)),
        "parameter_hints_as_you_type": bool(data.get("parameter_hints_as_you_type", False)),
    }
