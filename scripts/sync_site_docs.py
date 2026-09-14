"""Sync every app's rendered docs onto the published site — one pass, nine apps.

``docs/site/`` is the QuillVille family's web presence, and its ``docs/*.html``
pages are not hand-maintained content: they are **copies** of each app's own
rendered documentation, and copies rot. Radio's were the first to be mechanised
(2026-08-17, ``sync_site_radio_docs.py``) after the site was found offering a
user guide for an app that no longer looked like that.

Radio was the only app that ever got the treatment, and the rest of the family
was worse off than stale — it was **absent**. Cast, Weather, Audio Studio,
Inkwell, the Converter, the Media Player, Beacon and QuillLite had no page on
the site at all, which is a documentation gap nobody can report: there is no
wrong page to complain about, only a product a reader cannot find anything
about. This script is the per-app bolt-on replaced by one table.

**What is synced.** Each app's user guide, its PRD, and its current release
notes, wherever those exist as a render. Nothing else: tutorials, changelogs,
architecture notes and planning documents are for people working *on* an app,
and the site is for people using one.

**What is deliberately not synced.** ``radio-pr.html`` (the 1.0 press release) is
a historical announcement rather than living documentation. Nothing is synced for
an app with no rendered docs at all.

**Download links are not this script's business.** The site links to an app's
documentation here and to its release on GitHub elsewhere; a page describing a
download that does not exist yet is worse than no page, so the two are separated
and the release links are added when a release exists.

Exits non-zero if a *declared* source render is missing — a site sync from a tree
that has not rendered is a stale copy with extra steps. ``--check`` reports drift
without writing, for CI.

Usage::

    python scripts/sync_site_docs.py                 # every app
    python scripts/sync_site_docs.py --app radio     # one app
    python scripts/sync_site_docs.py --check         # report drift, write nothing
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SITE_DOCS = _REPO_ROOT / "docs" / "site" / "docs"

#: app key -> (site-page suffix -> the render under ``standalone/<app>/docs``).
#:
#: The site page is named ``<app key>-<suffix>.html``, so Radio's existing three
#: pages keep the names they have and every sibling's follow the same rule
#: rather than each app inventing one. An app whose render does not exist is
#: simply not listed: a declared source that is missing is an error, and a
#: source nobody declared is not.
SYNC_MAP: dict[str, dict[str, str]] = {
    "radio": {
        "userguide": "userguide.html",
        "prd": "prd.html",
        "release-notes": "release-notes-3.0.html",
        # The 3.0 announcement. Unlike ``radio-pr.html`` (the 1.0 press release,
        # deliberately left as a historical page) this one is generated from the
        # repo, so it cannot drift from the release it announces.
        "announcement": "announcement-3.0.html",
    },
    "cast": {
        "userguide": "userguide.html",
        "prd": "prd.html",
        "release-notes": "release-notes-2.0.html",
    },
    "weather": {
        "userguide": "userguide.html",
        "prd": "prd.html",
        "release-notes": "release-notes-2.2.html",
    },
    "studio": {
        "userguide": "userguide.html",
        "prd": "prd.html",
        "release-notes": "release-notes-2.2.html",
    },
    "inkwell": {
        "userguide": "userguide.html",
        "prd": "prd.html",
    },
    "converter": {
        "userguide": "userguide.html",
        "prd": "prd.html",
        "release-notes": "release-notes-1.0.html",
    },
    "player": {
        "userguide": "userguide.html",
        "prd": "prd.html",
    },
    "quilllite": {
        "userguide": "userguide.html",
        "prd": "prd.html",
        "release-notes": "release-notes-1.0.html",
    },
}

#: app key -> the folder under ``standalone/`` holding its docs, where the two
#: names differ. Only here so a rename is one line rather than a search.
_DOC_DIRS: dict[str, str] = {}


def _source(app_key: str, render: str) -> Path:
    folder = _DOC_DIRS.get(app_key, app_key)
    return _REPO_ROOT / "standalone" / folder / "docs" / render


def _page(app_key: str, suffix: str) -> Path:
    return _SITE_DOCS / f"{app_key}-{suffix}.html"


def planned(app_key: str | None = None) -> list[tuple[Path, Path]]:
    """Every ``(site page, source render)`` pair this script maintains."""
    pairs: list[tuple[Path, Path]] = []
    for key, renders in sorted(SYNC_MAP.items()):
        if app_key and key != app_key:
            continue
        for suffix, render in sorted(renders.items()):
            pairs.append((_page(key, suffix), _source(key, render)))
    return pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app", help="sync only this app key (e.g. radio)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report pages that are missing or out of date; write nothing",
    )
    args = parser.parse_args(argv)

    if args.app and args.app not in SYNC_MAP:
        known = ", ".join(sorted(SYNC_MAP))
        print(f"Unknown app key {args.app!r}. Known: {known}", file=sys.stderr)
        return 2
    if not _SITE_DOCS.is_dir():
        print(f"Site docs directory not found: {_SITE_DOCS}", file=sys.stderr)
        return 2

    missing_sources: list[str] = []
    stale: list[str] = []
    synced = 0
    for page, source in planned(args.app):
        if not source.is_file():
            missing_sources.append(
                f"  missing render: {source.relative_to(_REPO_ROOT)} "
                f"(run standalone/{source.parents[1].name}/scripts/render_docs.ps1)"
            )
            continue
        up_to_date = page.is_file() and filecmp.cmp(source, page, shallow=False)
        if args.check:
            if not up_to_date:
                stale.append(f"  stale or missing: {page.relative_to(_REPO_ROOT)}")
            continue
        if up_to_date:
            continue
        shutil.copyfile(source, page)
        synced += 1
        print(f"  synced {page.name} <- {source.relative_to(_REPO_ROOT)}")

    for line in missing_sources:
        print(line)
    for line in stale:
        print(line)

    if missing_sources:
        print(f"Site sync incomplete: {len(missing_sources)} source(s) missing.", file=sys.stderr)
        return 1
    if args.check:
        if stale:
            print(
                f"{len(stale)} site page(s) out of date. Run: python scripts/sync_site_docs.py",
                file=sys.stderr,
            )
            return 1
        print("Site docs are up to date.")
        return 0
    print(f"Site docs synced ({synced} page(s) rewritten).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
