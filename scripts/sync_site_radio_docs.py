"""Sync Quill Radio's rendered docs onto the published site.

Kept as its own entry point because Quill Radio's ``scripts/build_release.ps1``
calls it by name after ``render_docs.ps1``, and a release script is the last
place a rename should reach. The work itself moved to
:mod:`scripts.sync_site_docs` on 2026-09-10, when the same treatment was
extended to the other eight apps: Radio was the only app whose site pages were
ever mechanised, and the rest of the family was not stale but **absent**, which
is the documentation gap nobody can report -- there is no wrong page to complain
about, only a product a reader can find nothing about.

Run ``python scripts/sync_site_docs.py`` for the whole family, or this for Radio
alone.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sync_site_docs import main as _sync  # noqa: E402


def main() -> int:
    return _sync(["--app", "radio"])


if __name__ == "__main__":
    raise SystemExit(main())
