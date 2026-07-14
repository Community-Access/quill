"""Verbosity profile import / export (verbosity §30).

Profiles travel between machines as ``.quill-verbosity-profile.json`` files —
Jeff's quiet meeting setup, Kelly's screen-reader setup, a classroom beginner
setup. Imports are **strictly data**: this module validates structure by hand
against the import/export schema and never executes anything from the file
(there is no ``exec`` / ``eval`` / ``__import__`` path), so a shared profile can
change settings but never run code.

Pure and wx-free.
"""

from __future__ import annotations

import json
from typing import Any

from quill.core.verbosity.profiles import CustomProfile

__all__ = [
    "PROFILE_IO_FORMAT",
    "PROFILE_IO_VERSION",
    "ProfileImportError",
    "export_profile",
    "to_json",
    "import_profile",
    "from_json",
]

PROFILE_IO_FORMAT = "quill-verbosity-profile"
PROFILE_IO_VERSION = "1"


class ProfileImportError(ValueError):
    """Raised when an imported profile is structurally invalid."""


def export_profile(custom: CustomProfile) -> dict[str, Any]:
    """Return the import/export envelope for ``custom``."""
    return {
        "format": PROFILE_IO_FORMAT,
        "version": PROFILE_IO_VERSION,
        "profile": custom.to_dict(),
    }


def to_json(custom: CustomProfile) -> str:
    """Serialize ``custom`` to a pretty, stable JSON string."""
    return json.dumps(export_profile(custom), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def import_profile(data: Any) -> CustomProfile:
    """Validate an import envelope and return the :class:`CustomProfile`.

    Raises :class:`ProfileImportError` for any structural problem. No code from
    the file is ever executed — only typed fields are read.
    """
    if not isinstance(data, dict):
        raise ProfileImportError("Profile file must be a JSON object")
    if data.get("format") != PROFILE_IO_FORMAT:
        raise ProfileImportError(f"Unrecognized format; expected '{PROFILE_IO_FORMAT}'")
    profile = data.get("profile")
    if not isinstance(profile, dict):
        raise ProfileImportError("Missing or invalid 'profile' object")
    name = profile.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ProfileImportError("Profile 'name' is required and must be a non-empty string")
    try:
        return CustomProfile.from_dict(profile)
    except (KeyError, ValueError, TypeError) as error:
        raise ProfileImportError(f"Invalid profile data: {error}") from error


def from_json(text: str) -> CustomProfile:
    """Parse ``text`` as a profile import envelope and return the profile."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProfileImportError(f"Not valid JSON: {error}") from error
    return import_profile(data)
