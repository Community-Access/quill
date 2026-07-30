"""Spotify network-access consent state (one-time user confirmation).

The same shape as :mod:`quill.core.github.consent`: a single flag file under the
app data directory records that the user has accepted the notice explaining that
connecting Spotify will contact Spotify's servers (sign-in, the Web API, and the
Web Playback SDK streaming DRM audio). Signing in is gated on this in addition to
the ``future.spotify`` feature flag and Safe-Mode refusal.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_CONSENT_FILE = "spotify_consent.json"


def load_spotify_consent_complete() -> bool:
    """Return True if the user has already accepted the Spotify access notice."""
    path = _consent_path()
    data = read_json(path, default={}) if path.exists() else {}
    return bool(data.get("accepted", False)) if isinstance(data, dict) else False


def save_spotify_consent_complete() -> None:
    """Record that the user accepted the Spotify network-access consent notice."""
    write_json_atomic(_consent_path(), {"accepted": True})


def _consent_path() -> Path:
    return app_data_dir() / _CONSENT_FILE


__all__ = [
    "load_spotify_consent_complete",
    "save_spotify_consent_complete",
]
