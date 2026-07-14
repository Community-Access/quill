"""Quill package."""

import os as _os
import sys as _sys

# When quill/__main__.py is run as a script instead of "-m quill" (a manual
# "python quill/__main__.py", or any launcher that reuses sys.argv[0]),
# Python puts this package directory itself at sys.path[0]. There,
# quill/platform shadows the stdlib "platform" module and the app dies in
# menu construction with AttributeError: module 'platform' has no attribute
# 'system'. Swap the entry for the package parent so stdlib names resolve
# normally; "import quill" keeps working because the parent is exactly what
# a correct launch would have used.
_pkg_dir = _os.path.dirname(_os.path.abspath(__file__))
if _sys.path and _os.path.abspath(_sys.path[0] or _os.getcwd()) == _pkg_dir:
    _sys.path[0] = _os.path.dirname(_pkg_dir)
_shadowed = _sys.modules.get("platform")
if _shadowed is not None and str(getattr(_shadowed, "__file__", "")).startswith(_pkg_dir):
    # quill/platform is already cached under the stdlib name; drop it so the
    # next "import platform" finds the real module.
    del _sys.modules["platform"]
del _pkg_dir, _shadowed

# Version is defined first so that the build_info module (which imports
# __version__ as a fallback) can do so without a circular import.
__version__ = "0.9.0"

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
    QUILL_KEY_LABEL,
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
    "QUILL_KEY_LABEL",
    "INDEPENDENCE_NOTICE",
]
