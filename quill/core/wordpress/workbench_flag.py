"""The developer flag for the WordPress Workbench window (Phase W1, off by default).

While the window is new (WordPress PRD Part G, W1 to W4) it is reached only
when a developer asks for it: set ``QUILL_WORDPRESS_WORKBENCH_WINDOW=1`` before
starting QUILL or QUILL Lite, and the Tools > WordPress doors (Comments, Media
Library, Categories and Tags, Menus, Site Check, Site Settings, Site Map, and
Manage > Users, Application Passwords and Plugins) open the Workbench at their
node instead of their own windows. Without it nothing changes. One flag for
both editors, read in one place, so QUILL Lite can never get the window first.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

__all__ = ["ENV_VAR", "workbench_window_enabled"]

ENV_VAR = "QUILL_WORDPRESS_WORKBENCH_WINDOW"


def workbench_window_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Whether the Tools > WordPress doors open the Workbench for this run."""
    source = os.environ if environ is None else environ
    return source.get(ENV_VAR, "").strip().lower() in {"1", "true", "yes", "on"}
