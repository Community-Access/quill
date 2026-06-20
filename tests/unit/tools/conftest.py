"""Conftest for tools/ tests.

Many tooling tests need to import helpers from the repo's ``tools/``
directory, which is not on ``sys.path`` by default. We add it here so
the tests can do a plain ``from generate_build_info import ...``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# tools/ lives at <repo>/tools and is one level above this conftest.
_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
