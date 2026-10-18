"""Where a run from a source checkout finds the media tools a built app ships.

A built Quill Radio carries libmpv in ``{app}\\tools``. A developer running
``run-quill-radio.bat`` from the checkout has no ``{app}``: the build scripts
stage the same files in ``build\\deps\\<tool>`` (gitignored), and libmpv has
been found there since 2026-09-29.

One function, so the question is asked in one place and the test suite can
answer it with "nothing staged" in one place (``tests/real_output_guard.py``):
a test must behave the same in the main checkout, where the staging exists, as
in a fresh worktree or on CI, where it does not. Before 2026-10-17 a Radio test
run from the main checkout found the real libmpv and a worktree's did not.

Never in a frozen build: a shipped app must not read a build directory.
wx-free, no I/O beyond one ``is_dir``.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: The checkout root: quill/core/source_tools.py -> quill/core -> quill -> root.
_REPO_ROOT = Path(__file__).resolve().parents[2]


def staged_tool_dir(name: str) -> Path | None:
    """``<checkout>\\build\\deps\\<name>`` when running from source and it exists."""
    if getattr(sys, "frozen", False):
        return None
    candidate = _REPO_ROOT / "build" / "deps" / name
    return candidate if candidate.is_dir() else None


__all__ = ["staged_tool_dir"]
