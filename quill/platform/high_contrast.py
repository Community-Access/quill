"""Platform-neutral accessibility detection (routes to the OS impl)."""

from __future__ import annotations

import sys

if sys.platform == "darwin":
    from quill.platform.macos.high_contrast import is_high_contrast_enabled
elif sys.platform.startswith("win"):
    from quill.platform.windows.high_contrast import is_high_contrast_enabled
else:  # pragma: no cover - other platforms

    def is_high_contrast_enabled() -> bool:
        return False


__all__ = ["is_high_contrast_enabled"]
