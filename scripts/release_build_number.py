"""The build number a release build ships as, and the Windows file version for it.

The same version can ship more than once: a rebuild of Quill Radio 3.2.0 with a
fix is 3.2.0 build 2, and Check for Updates offers it to everyone on build 1
(docs/release/RELEASE.md, "Build numbers"). Every ``build_release.ps1`` asks
this script which build it is making, through ``Resolve-QuillReleaseBuild`` in
``scripts/BuildEnv.ps1``::

    python scripts/release_build_number.py --app radio --version 3.2.0
    python scripts/release_build_number.py --app radio --version 3.2.0 --build 2
    python scripts/release_build_number.py --app radio --version 3.3.0-dev.20261003.1 --dev

It prints one line, ``<build> <file version>`` (``2 3.2.0.2``), and refuses --
exit 1, with a sentence -- when:

* the build is already published (a tag for that exact build exists), because
  two different builds under one tag is the thing build numbers end; or
* the app's build constant in source disagrees, because the shared runtime
  carries that constant, and a runtime that says build 1 inside an installer
  that says build 2 is the 2026-09-29 version mix-up again.

Without ``--build`` the build is the next one after the newest tag published
for this version (``release_tags.next_build``). When the published releases
cannot be read, ``--offline-ok`` takes the build constant from source instead
(dev builds and rehearsals); otherwise it exits 2, because a release build does
not guess. A Dev build (``--dev``) has no build number: its version is already
unique.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

#: Where each app keeps its build constant: ``(file, constant)``.
BUILD_CONSTANTS: dict[str, tuple[str, str]] = {
    "quill": ("quill/__init__.py", "__build__"),
    "radio": ("quill/apps/radio.py", "_BUILD"),
    "quilllite": ("quill/core/lite/__init__.py", "APP_BUILD"),
    "cast": ("quill/apps/podcasts_menu.py", "APP_BUILD"),
    "converter": ("quill/apps/converter.py", "_BUILD"),
    "weather": ("quill/apps/weather.py", "_BUILD"),
    "inkwell": ("quill/apps/inkwell.py", "_BUILD"),
    "player": ("quill/apps/player.py", "_BUILD"),
    "studio": ("quill/apps/studio.py", "_BUILD"),
    "beacon": ("quill/apps/beacon/app.py", "_BUILD"),
    "social": ("standalone/social/quill_social/__init__.py", "__build__"),
}


def source_build(app: str, root: Path = REPO_ROOT) -> int:
    """The app's build constant in source, or 0 when it has none."""
    path, constant = BUILD_CONSTANTS[app]
    text = (root / path).read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(constant)}\s*=\s*(\d+)", text, re.M)
    return int(match.group(1)) if match else 0


def _published_tags() -> list[str]:
    from check_sibling_versions import _published_tags as published

    return published()


def resolve(
    app: str,
    version: str,
    *,
    build: int = 0,
    dev: bool = False,
    offline_ok: bool = False,
    tags: Callable[[], list[str]] = _published_tags,
    root: Path = REPO_ROOT,
) -> tuple[int, str, str]:
    """``(build, file_version, problem)``; *problem* is "" when the build may go."""
    from quill.core.release_tags import next_build, release_tag
    from quill.core.versioning import ReleaseVersion

    parsed = ReleaseVersion.parse(version).without_build()
    if dev:
        return 0, parsed.file_version(), ""
    in_source = source_build(app, root)
    try:
        published = tags()
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        if build or offline_ok:
            chosen = build or in_source
            return chosen, parsed.with_build(chosen).file_version(), ""
        return (
            0,
            "",
            (
                f"could not read the published releases ({error}). A release build does not "
                "guess its build number: pass -Build, or -SkipPublishedCheck for a dev build."
            ),
        )
    chosen = build or next_build(published, app, parsed.semver())
    tag = release_tag(app, parsed.with_build(chosen).semver())
    if tag in published:
        return (
            chosen,
            "",
            (
                f"{tag} is already published. A rebuild ships as the next build "
                f"({next_build(published, app, parsed.semver())})."
            ),
        )
    if in_source != chosen:
        path, constant = BUILD_CONSTANTS[app]
        return (
            chosen,
            "",
            (
                f"this is {app} {parsed.plain()} build {chosen}, but {path} says "
                f"{constant} = {in_source}. Set {constant} = {chosen} in the release commit, so "
                "the runtime this build carries says the same build as its installer."
            ),
        )
    return chosen, parsed.with_build(chosen).file_version(), ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app", required=True, choices=sorted(BUILD_CONSTANTS))
    parser.add_argument("--version", required=True)
    parser.add_argument("--build", type=int, default=0, help="this build number (default: next)")
    parser.add_argument("--dev", action="store_true", help="a Dev build: no build number")
    parser.add_argument("--offline-ok", action="store_true")
    args = parser.parse_args(argv)
    if args.build < 0:
        print("release_build_number: --build must be 1 or more.", file=sys.stderr)
        return 2
    build, file_version, problem = resolve(
        args.app, args.version, build=args.build, dev=args.dev, offline_ok=args.offline_ok
    )
    if problem:
        print(f"Build number: {problem}", file=sys.stderr)
        return 2 if not file_version and not build else 1
    print(f"{build} {file_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
