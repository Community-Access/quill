"""Quill package."""

# Version is defined first so that the build_info module (which imports
# __version__ as a fallback) can do so without a circular import.
__version__ = "0.7.0"

# Re-export the new modules so callers can `from quill import branding`
# and `from quill import build_info` without touching the package layout.
from quill import branding, build_info  # noqa: E402, F401
from quill.branding import (  # noqa: E402
    APP_COPYRIGHT,
    APP_DESCRIPTION,
    APP_DISPLAY_NAME,
    APP_FULL_NAME,
    APP_LICENSE_NAME,
    APP_ORGANIZATION,
    APP_SHORT_NAME,
    INDEPENDENCE_NOTICE,
)
from quill.build_info import (  # noqa: E402
    get_display_version,
    get_short_version,
    get_support_info,
    is_release_build,
)

__all__ = [
    "__version__",
    # modules
    "branding",
    "build_info",
    # build_info helpers
    "get_display_version",
    "get_short_version",
    "get_support_info",
    "is_release_build",
    # branding constants
    "APP_DISPLAY_NAME",
    "APP_DESCRIPTION",
    "APP_FULL_NAME",
    "APP_ORGANIZATION",
    "APP_SHORT_NAME",
    "APP_COPYRIGHT",
    "APP_LICENSE_NAME",
    "INDEPENDENCE_NOTICE",
]
