"""Platform-neutral appearance/accessibility detection (routes to the OS impl)."""

from __future__ import annotations

import sys

if sys.platform == "darwin":
    from quill.platform.macos.high_contrast import (
        is_dark_mode_enabled,
        is_high_contrast_enabled,
        is_reduce_motion_enabled,
        macos_appearance,
    )
elif sys.platform.startswith("win"):
    from quill.platform.windows.high_contrast import is_high_contrast_enabled

    def is_dark_mode_enabled() -> bool:
        # Windows dark-mode sync is handled via the registry elsewhere; this
        # neutral hook reports the macOS-only detection for cross-platform UI.
        return False

    def is_reduce_motion_enabled() -> bool:
        return False

    def macos_appearance() -> object:  # pragma: no cover - Windows has no macOS appearance
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True)
        class _Appearance:
            high_contrast: bool
            dark_mode: bool
            reduce_motion: bool

        return _Appearance(
            high_contrast=is_high_contrast_enabled(),
            dark_mode=False,
            reduce_motion=False,
        )

else:  # pragma: no cover - other platforms

    def is_high_contrast_enabled() -> bool:
        return False

    def is_dark_mode_enabled() -> bool:
        return False

    def is_reduce_motion_enabled() -> bool:
        return False

    def macos_appearance() -> object:  # pragma: no cover
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True)
        class _Appearance:
            high_contrast: bool
            dark_mode: bool
            reduce_motion: bool

        return _Appearance(high_contrast=False, dark_mode=False, reduce_motion=False)


__all__ = [
    "is_dark_mode_enabled",
    "is_high_contrast_enabled",
    "is_reduce_motion_enabled",
    "macos_appearance",
]
