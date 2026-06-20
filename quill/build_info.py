"""Safe read-only access to QUILL's generated build-identity metadata.

The actual constants live in :mod:`quill._build_info`, which is regenerated
by :mod:`tools.generate_build_info` before every build.  This thin wrapper
imports the generated module lazily and falls back to a minimal stub if
the file is absent (uninstalled development checkout, build environment
without ``build/version.toml``).

Public API:

* :func:`get_display_version` - the full human label, e.g.
  ``"QUILL for All 0.7.0 Beta 1 build 20260620.0"``.
* :func:`get_support_info` - the multi-line block the About dialog copies
  to the clipboard and that crash reports prepend to their bundles.

The fallback path is intentionally conservative: a missing build-info
file must not break the About dialog or crash reporter.
"""

from __future__ import annotations

import sys
from types import ModuleType

from quill import __version__


def _load() -> ModuleType | None:
    """Import the generated module. Returns None on ImportError."""
    try:
        from quill import _build_info  # type: ignore[attr-defined]

        return _build_info
    except Exception:
        return None


_BUILD_INFO = _load()


def get_display_version() -> str:
    """User-visible build label.

    Falls back to ``"QUILL for All <version> (development build)"`` when
    the generated module is unavailable.
    """
    if _BUILD_INFO is None:
        return f"QUILL for All {__version__} (development build)"
    return _BUILD_INFO.FULL_DISPLAY_VERSION


def get_short_version() -> str:
    """Channel-annotated version only, e.g. ``"0.7.0 Beta 1"``."""
    if _BUILD_INFO is None:
        return __version__
    return _BUILD_INFO.DISPLAY_VERSION


def get_support_info() -> str:
    """Multi-line block the About dialog copies to the clipboard."""
    if _BUILD_INFO is None:
        return (
            f"Product: QUILL for All\n"
            f"Version: {__version__}\n"
            "Build: development build\n"
            "Build metadata unavailable.\n"
        )

    python_version = ".".join(str(part) for part in sys.version_info[:3])
    lines = [
        f"Product: {_BUILD_INFO.PRODUCT_NAME}",
        f"Version: {_BUILD_INFO.DISPLAY_VERSION}",
        f"Build: {_BUILD_INFO.BUILD_STAMP}",
        f"Channel: {_BUILD_INFO.CHANNEL}",
        f"Commit: {_BUILD_INFO.GIT_SHA}",
        f"Dirty: {_BUILD_INFO.DIRTY}",
        f"Build date: {_BUILD_INFO.BUILD_DATE}",
        f"Python: {python_version}",
    ]
    return "\n".join(lines)


def is_release_build() -> bool:
    """True when the generated module exists and is the stable channel."""
    return _BUILD_INFO is not None and _BUILD_INFO.CHANNEL == "stable"


def resolve_running_version(*, override: str | None = None) -> str:
    """Pick the version string the running build should report.

    Resolution order:

    1. ``override`` (e.g. when an autoupdate controller caches its own view).
    2. The channel-annotated short version (``"0.7.0 Beta 1"``) so the build
       compares apples-to-apples against the update manifest.
    3. ``__version__`` for partial clones / dev checkouts.
    4. ``"0.0.0"`` as a last-ditch sentinel.
    """
    if override:
        return override
    short = get_short_version()
    if short:
        return short
    if __version__:
        return __version__
    return "0.0.0"


__all__ = [
    "get_display_version",
    "get_short_version",
    "get_support_info",
    "is_release_build",
    "resolve_running_version",
]
