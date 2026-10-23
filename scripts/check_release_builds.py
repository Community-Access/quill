"""Check every app in a joint release against its published builds, at once.

``docs/release/RELEASE.md`` ("A joint release of several apps") explains why a
joint release builds each app with ``-SkipPublishedCheck``: each app's own
sibling check names only itself, and fails on the other apps that are not
published yet. That flag also skips the build-number check -- that this
version and build has not shipped already, and that the app's source declares
it -- which the runbook says to do by hand for each app. This does it for all of
them, from the source, so ``build-quill-apps.ps1 -Release`` can run it before
building anything.

Usage::

    python scripts/check_release_builds.py --releasing radio --releasing quilllite
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import check_sibling_versions  # noqa: E402


def check(apps: list[str]) -> list[str]:
    """One line per app that cannot ship as its source says. Empty is a pass."""
    sites = {site.app: site for site in check_sibling_versions.SITES}
    problems = []
    for app in apps:
        site = sites.get(app)
        if site is None:
            problems.append(f"{app}: no version site is known for it")
            continue
        version, _, build = check_sibling_versions.source_version(site).partition("+")
        argv = [
            sys.executable,
            str(_SCRIPTS / "release_build_number.py"),
            "--app",
            app,
            "--version",
            version,
            "--build",
            build or "1",
        ]
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            reason = (result.stderr or result.stdout).strip().splitlines()
            problems.append(
                f"{app} {version} build {build or 1}: {reason[-1] if reason else 'refused'}"
            )
        else:
            print(f"  {app} {version} build {build or 1}: not yet published, as its source says")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--releasing", action="append", default=[], required=True)
    args = parser.parse_args(argv)
    problems = check(args.releasing)
    for problem in problems:
        print(f"Cannot ship: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
