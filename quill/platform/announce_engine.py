"""Platform-neutral re-export of the Prism announcement engine.

Prism (``prism``/``prismatoid``) is cross-platform and the engine falls back to
status-only when it isn't present, so this works on Windows and macOS alike.
"""

from __future__ import annotations

from quill.platform.windows.prism_bridge import (  # noqa: F401
    AnnouncementBackendState,
    AnnouncementEngine,
    normalize_backend_name,
    prewarm_tts_engine,
)

__all__ = [
    "AnnouncementBackendState",
    "AnnouncementEngine",
    "normalize_backend_name",
    "prewarm_tts_engine",
]
