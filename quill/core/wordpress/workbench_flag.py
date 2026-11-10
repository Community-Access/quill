"""Whether Tools > WordPress leads to the WordPress Workbench (W6, decision 7).

The Workbench is the default in both editors: each Tools > WordPress door
(Comments, Media Library, Categories and Tags, Menus, Site Check, Site
Settings, Site Map, and Manage's Users, Application Passwords, Plugins,
Themes, Fonts, Synced Patterns, Widgets and AI Abilities) opens it at its
node. For one release the old windows stay parked behind the Workbench
Options choice **Use the classic WordPress windows**
(:mod:`quill.core.wordpress.workbench_options`); with it on, every door opens
its own window as before.

``QUILL_WORDPRESS_WORKBENCH_WINDOW`` still decides for a developer: ``1`` (or
true, yes, on) always opens the Workbench, ``0`` (or false, no, off) always
the classic windows, whatever the option says. One answer for both editors,
read in one place, so QUILL Lite can never be ahead.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

__all__ = ["ENV_VAR", "workbench_window_enabled"]

ENV_VAR = "QUILL_WORDPRESS_WORKBENCH_WINDOW"

_ON = {"1", "true", "yes", "on"}
_OFF = {"0", "false", "no", "off"}


def workbench_window_enabled(
    environ: Mapping[str, str] | None = None, *, base: Path | None = None
) -> bool:
    """Whether the Tools > WordPress doors open the Workbench for this run."""
    source = os.environ if environ is None else environ
    said = source.get(ENV_VAR, "").strip().lower()
    if said in _ON:
        return True
    if said in _OFF:
        return False
    from quill.core.wordpress.workbench_options import load_options

    return not load_options(base).classic_windows
