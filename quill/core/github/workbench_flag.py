"""The developer flag for the GitHub Workbench window (Phase 1 spike, off by default).

While the window is a spike (GitHub PRD section 11, Phase 1) it is reached only
when a developer asks for it: set ``QUILL_GITHUB_WORKBENCH_WINDOW=1`` before
starting QUILL or QUILL Lite, and the doors that open GitHub Items open the
Workbench window instead. Without it nothing changes. One flag for both
editors, read in one place, so QUILL Lite can never get the window first.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

__all__ = ["ENV_VAR", "workbench_window_enabled"]

ENV_VAR = "QUILL_GITHUB_WORKBENCH_WINDOW"


def workbench_window_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Whether the Workbench window replaces GitHub Items for this run."""
    source = os.environ if environ is None else environ
    return source.get(ENV_VAR, "").strip().lower() in {"1", "true", "yes", "on"}
