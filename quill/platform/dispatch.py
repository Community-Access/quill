"""OS-agnostic access to Quill's platform integrations.

Selects the Windows or macOS implementation lazily at call time, so importing
this module never triggers platform-specific imports. Call sites can migrate
from ``quill.platform.windows.*`` to these helpers over time (see issue #42).

The per-surface helpers delegate to the platform-neutral root modules
(:mod:`quill.platform.high_contrast` and :mod:`quill.platform.sr_detect`), which
gate on ``sys.platform`` once at import time. There is no second copy of the
platform-routing logic here, so a future macOS-routing change applied in the
root module is picked up automatically instead of drifting out of sync (#7).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass


def current_platform() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "other"


def is_high_contrast_enabled() -> bool:
    # Delegate to the module-level-gated helper rather than re-branching on
    # current_platform() here, so there is one routing site to maintain (#7).
    from quill.platform.high_contrast import is_high_contrast_enabled as impl

    return impl()


@dataclass(frozen=True, slots=True)
class ScreenReaderDetection:
    detected: bool
    name: str
    source: str


def detect_screen_reader() -> ScreenReaderDetection:
    # Same delegation rationale as is_high_contrast_enabled(): the root
    # quill.platform.sr_detect module already gates on sys.platform once.
    from quill.platform.sr_detect import detect_screen_reader as impl

    result = impl()
    return ScreenReaderDetection(detected=result.detected, name=result.name, source=result.source)
