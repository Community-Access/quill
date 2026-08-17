"""Sync Quill Radio's rendered docs onto the published site (polish.md P0.5).

``docs/site/`` is the QuillVille family's hand-maintained web presence — a
separate pipeline from the Markdown docs tree (release_readiness deliberately
skips it). Its ``docs/radio-*.html`` pages, however, are not hand-maintained
content: they are *copies* of Quill Radio's own rendered documentation, and
copies rot. The ones found on 2026-08-17 predated Radio 3.0 entirely — the
site was offering a user guide for an app that no longer looked like that,
which is exactly the staleness QUILL's documentation scoping removed from the
user guide the same day.

This script makes the copy mechanical: it overwrites the site's radio pages
from ``standalone/radio/docs``'s current renders. Radio's
``scripts/build_release.ps1`` calls it after ``render_docs.ps1``, so every
release build refreshes the site pages with zero hand steps; run it directly
after editing radio docs outside a release.

``radio-pr.html`` (the 1.0 press release) is deliberately NOT synced: it is a
historical announcement, not living documentation.

Exits non-zero if a source render is missing — a site sync from a tree that
has not rendered is a stale copy with extra steps.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: site page name -> the rendered source it mirrors.
_SYNC: dict[str, Path] = {
    "radio-userguide.html": _REPO_ROOT / "standalone" / "radio" / "docs" / "userguide.html",
    "radio-prd.html": _REPO_ROOT / "standalone" / "radio" / "docs" / "prd.html",
    "radio-release-notes.html": (
        _REPO_ROOT / "standalone" / "radio" / "docs" / "release-notes-3.0.html"
    ),
}


def main() -> int:
    site_docs = _REPO_ROOT / "docs" / "site" / "docs"
    if not site_docs.is_dir():
        print(f"Site docs directory not found: {site_docs}", file=sys.stderr)
        return 2
    failures = 0
    for page, source in sorted(_SYNC.items()):
        if not source.is_file():
            print(f"  missing render: {source} (run standalone/radio/scripts/render_docs.ps1)")
            failures += 1
            continue
        target = site_docs / page
        shutil.copyfile(source, target)
        print(f"  synced {page} <- {source.relative_to(_REPO_ROOT)}")
    if failures:
        print(f"Site sync incomplete: {failures} source(s) missing.", file=sys.stderr)
        return 1
    print("Site radio docs synced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
