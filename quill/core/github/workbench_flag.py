"""Which GitHub window the editors open: the Workbench, or the classic two.

GitHub PRD section 11, Phase 6: the GitHub Workbench window is the default in
QUILL and QUILL Lite. GitHub Items and Explore GitHub are parked for one
release (decision 4): Workbench Options, Privacy, **Use the classic GitHub
windows** brings them back, from ``github_workbench.json``
(:mod:`quill.core.github.workbench_prefs`). One answer for both editors, read
in one place, so QUILL Lite can never get the window first.

``QUILL_GITHUB_WORKBENCH_WINDOW`` still overrides the choice for a developer
or a test: ``1`` (or true, yes, on) forces the Workbench, ``0`` (or false, no,
off) forces the classic windows.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

__all__ = ["ENV_VAR", "workbench_window_enabled"]

ENV_VAR = "QUILL_GITHUB_WORKBENCH_WINDOW"

_ON = frozenset({"1", "true", "yes", "on"})
_OFF = frozenset({"0", "false", "no", "off"})


def workbench_window_enabled(
    environ: Mapping[str, str] | None = None, *, use_classic: bool | None = None
) -> bool:
    """Whether the GitHub doors open the Workbench window (the default).

    *use_classic* is the person's Workbench Options choice; when it is not
    given it is read from ``github_workbench.json``.
    """
    source = os.environ if environ is None else environ
    forced = source.get(ENV_VAR, "").strip().lower()
    if forced in _ON:
        return True
    if forced in _OFF:
        return False
    if use_classic is None:
        from quill.core.github.workbench_prefs import load_prefs

        use_classic = load_prefs().use_classic_windows
    return not use_classic
