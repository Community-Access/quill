"""Run the tests that cover ONE app, not the whole nine-minute suite.

WHY THIS EXISTS
---------------
The full suite is the merge gate and stays that way -- but a Radio afternoon
does not need Studio's tests on every iteration. The test tree already maps
cleanly onto the apps (``tests/unit/core/radio``, ``tests/unit/ui/podcasts``,
...), so this resolves an app name to its test paths and hands them to pytest.

The honest part: scoping is only safe while your changes stay inside the
app's own modules. Shared code (``quill/core/storage.py``, ``quill/ui``
mixins, ``quill/stability``) serves every app, so before running, this checks
``git diff`` and WARNS when a changed file falls outside the app's source
scope -- that is the moment to run ``pytest -q`` in full (or at least
``-m smoke``) instead of trusting a green scoped run.

Usage::

    python scripts/test_scope.py radio            # radio's tests
    python scripts/test_scope.py cast -- -x -q    # extra pytest args after --
    python scripts/test_scope.py --list           # show every scope

Always finish a feature with one full ``pytest -q`` (or push and let CI run
it); this is an iteration loop, not a substitute for the gate.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: app -> (test path globs, source prefixes the scope is allowed to touch).
#: Test globs may name files or directories; missing ones are skipped so the
#: map survives refactors without going stale-fatal.
SCOPES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "radio": (
        (
            "tests/unit/core/radio",
            "tests/unit/ui/radio",
            "tests/unit/ui/test_*radio*.py",
            "tests/unit/ui/test_browse_*.py",
            "tests/unit/apps/test_*radio*.py",
            "tests/unit/ui/spotify",
        ),
        (
            "quill/core/radio/",
            "quill/ui/radio/",
            "quill/ui/spotify/",
            "quill/apps/radio.py",
            "standalone/radio/",
        ),
    ),
    "cast": (
        (
            "tests/unit/core/podcasts",
            "tests/unit/ui/podcasts",
            "tests/unit/ui/test_*podcast*.py",
            "tests/unit/apps/test_*cast*.py",
            "tests/unit/apps/test_*podcast*.py",
        ),
        (
            "quill/core/podcasts/",
            "quill/ui/podcasts/",
            "quill/apps/podcasts.py",
            "standalone/cast/",
        ),
    ),
    "studio": (
        (
            "tests/unit/ui/audio_studio",
            "tests/unit/ui/audio",
            "tests/unit/core/audio",
            "tests/unit/apps/test_*studio*.py",
        ),
        ("quill/core/audio", "quill/ui/audio", "quill/apps/studio.py", "standalone/studio/"),
    ),
    "weather": (
        (
            "tests/unit/ui/weather",
            "tests/unit/ui/test_*weather*.py",
            "tests/unit/apps/test_*weather*.py",
        ),
        ("quill/core/weather", "quill/ui/weather/", "quill/apps/weather.py", "standalone/weather/"),
    ),
    "social": (
        ("standalone/social/tests",),
        ("standalone/social/",),
    ),
    "beacon": (
        ("tests/unit/apps/test_*beacon*.py",),
        ("quill/apps/beacon/", "standalone/beacon/"),
    ),
    "inkwell": (
        (
            "tests/unit/ui/expansion",
            "tests/unit/core/expansion",
            "tests/unit/apps/test_*inkwell*.py",
        ),
        (
            "quill/core/expansion",
            "quill/ui/expansion",
            "quill/apps/inkwell.py",
            "standalone/inkwell/",
        ),
    ),
}


def _resolve(globs: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for pattern in globs:
        if any(ch in pattern for ch in "*?["):
            found.extend(sorted(str(p.relative_to(_REPO_ROOT)) for p in _REPO_ROOT.glob(pattern)))
        elif (_REPO_ROOT / pattern).exists():
            found.append(pattern)
    return found


def _changed_files() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def _out_of_scope(changed: list[str], prefixes: tuple[str, ...]) -> list[str]:
    ignorable = ("tests/", "docs/", "local/", ".md", ".txt", ".iss", ".ps1", ".json")
    out = []
    for path in changed:
        if path.startswith(prefixes) or path.startswith(ignorable) or path.endswith(ignorable):
            continue
        out.append(path)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("app", nargs="?", choices=sorted(SCOPES), help="which app's tests to run")
    parser.add_argument("--list", action="store_true", help="show every scope and exit")
    parser.add_argument("--no-diff-check", action="store_true", help="skip the shared-code warning")
    parser.add_argument("pytest_args", nargs="*", help="extra pytest arguments (after --)")
    args = parser.parse_args()

    if args.list or not args.app:
        for app, (globs, _prefixes) in sorted(SCOPES.items()):
            paths = _resolve(globs)
            print(f"{app}: {len(paths)} test path(s)")
            for path in paths:
                print(f"    {path}")
        return 0

    globs, prefixes = SCOPES[args.app]
    paths = _resolve(globs)
    if not paths:
        print(f"No test paths currently exist for '{args.app}'.")
        return 1

    if not args.no_diff_check:
        strays = _out_of_scope(_changed_files(), prefixes)
        if strays:
            print(
                f"WARNING: your working tree changes {len(strays)} file(s) "
                f"OUTSIDE {args.app}'s scope:"
            )
            for path in strays[:10]:
                print(f"    {path}")
            if len(strays) > 10:
                print(f"    ... and {len(strays) - 10} more")
            print("Shared code serves every app -- a green scoped run does not cover these.")
            print("Run the full suite (pytest -q) or at least pytest -m smoke -q.\n")

    command = [sys.executable, "-m", "pytest", "-q", *paths, *args.pytest_args]
    print("Running:", " ".join(command[2:]))
    return subprocess.call(command, cwd=_REPO_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
