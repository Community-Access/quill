"""GATE-SIBVER: no app may ship a sibling's unreleased version number.

Every QuillVille installer ships the shared QuillVille Runtime, and the runtime
carries one frozen copy of the whole ``quill`` package -- every app's code and
every app's version constant. So the version an app *reports* is whatever the
newest runtime on the machine says, whichever installer put it there.

That is how QUILL Lite 1.1.0 failed on 2026-09-29. Lite's version was bumped to
1.1.0 in source on September 25 while the release that day was 1.0.1; Quill
Radio 3.0.3 and 3.0.4 were then built from main and their runtime carried a
QUILL Lite that *said* 1.1.0 without the code 1.1.0 later meant. On every
machine with that runtime, Help > About in QUILL Lite read 1.1.0 and Check for
Updates compared 1.1.0 with the real 1.1.0 release, said "you are up to date",
and never offered it. Users were stuck on a version number.

The rule this gate enforces: **an app's version constant may be ahead of its
newest published release only in a build that is releasing that app.** A build
of Quill Radio must not freeze a QUILL Lite that claims a version nobody can
download yet, and the other way round. A checkout *behind* the published
release fails too: that build would ship older code than users already have.

Run from a build script (``scripts/BuildEnv.ps1`` wraps it) with the app or apps
the build is releasing::

    python scripts/check_sibling_versions.py --releasing quilllite

Exit 0 when every app agrees, 1 with a sentence per disagreement, 2 when the
published releases could not be read (a release build must not guess; a dev
build passes ``--offline-ok``). The comparison is a pure function
(:func:`disagreements`), unit-tested without a network.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_REPO = "Community-Access/quill"


@dataclass(frozen=True)
class AppVersionSite:
    """Where an app's version lives in source, and how its releases are tagged."""

    app: str
    source: str
    constant: str
    tag_prefix: str


#: Every app whose version travels in the shared runtime. An app with no
#: published release under its prefix yet is skipped: there is nothing to be
#: ahead of, and the first release is the one that sets the mark.
SITES: tuple[AppVersionSite, ...] = (
    AppVersionSite("radio", "quill/apps/radio.py", "_VERSION", "quill-radio-v"),
    AppVersionSite("quilllite", "quill/core/lite/__init__.py", "APP_VERSION", "quill-lite-v"),
    AppVersionSite("converter", "quill/apps/converter.py", "_VERSION", "quill-converter-v"),
    AppVersionSite("weather", "quill/apps/weather.py", "_VERSION", "quill-weather-v"),
    AppVersionSite("inkwell", "quill/apps/inkwell.py", "_VERSION", "quill-inkwell-v"),
    AppVersionSite("player", "quill/apps/player.py", "_VERSION", "quill-player-v"),
)


def parse_version(text: str) -> tuple[int, ...]:
    """``"3.1.0"`` -> ``(3, 1, 0)``; a pre-release suffix sorts below the plain number."""
    match = re.match(r"^(\d+(?:\.\d+)*)", text.strip())
    if not match:
        return ()
    numbers = tuple(int(part) for part in match.group(1).split("."))
    tail = text.strip()[match.end() :]
    return (*numbers, 0) if not tail else (*numbers, -1)


def source_version(site: AppVersionSite, root: Path = REPO_ROOT) -> str:
    text = (root / site.source).read_text(encoding="utf-8")
    match = re.search(rf'^{re.escape(site.constant)}\s*=\s*"([^"]+)"', text, re.M)
    if not match:
        raise ValueError(f'{site.source} has no {site.constant} = "..." line')
    return match.group(1)


def newest_published(tags: list[str], prefix: str) -> str | None:
    """The highest version among *tags* that start with *prefix*, or None."""
    versions = [tag[len(prefix) :] for tag in tags if tag.startswith(prefix)]
    if not versions:
        return None
    return max(versions, key=parse_version)


def disagreements(
    sources: dict[str, str],
    published: dict[str, str | None],
    releasing: set[str],
) -> list[str]:
    """One sentence per app whose source version disagrees with what is published.

    *sources* and *published* are keyed by app id; a published ``None`` means
    the app has never been released and is skipped.
    """
    problems: list[str] = []
    for app, source in sorted(sources.items()):
        latest = published.get(app)
        if latest is None:
            continue
        src, pub = parse_version(source), parse_version(latest)
        if src > pub and app not in releasing:
            problems.append(
                f"{app}: source says {source} but the newest published release is {latest}, "
                f"and this build is not releasing {app}. A runtime built now would carry a "
                f"{app} that claims a version nobody can download, and every machine that "
                f"installs it would stop being offered the real one. Release {app} in this "
                f"build (--releasing {app}), or keep its version at {latest} until its "
                "release commit."
            )
        elif src < pub:
            problems.append(
                f"{app}: source says {source} but {latest} is already published. This "
                f"checkout is behind the release; a runtime built from it would carry older "
                f"{app} code than users already have."
            )
        elif src == pub and app in releasing:
            problems.append(
                f"{app}: this build says it is releasing {app}, but source still says "
                f"{source}, which is already published. Bump the version in the release commit."
            )
    return problems


def _published_tags() -> list[str]:
    """Every release tag in the release repo, read through the gh CLI."""
    result = subprocess.run(
        [
            "gh",
            "release",
            "list",
            "--repo",
            RELEASE_REPO,
            "--limit",
            "200",
            "--json",
            "tagName,isDraft",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        str(entry["tagName"])
        for entry in json.loads(result.stdout or "[]")
        if not entry.get("isDraft")
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--releasing",
        action="append",
        default=[],
        metavar="APP",
        help="an app this build is releasing (repeatable)",
    )
    parser.add_argument(
        "--offline-ok",
        action="store_true",
        help="pass when the published releases cannot be read (dev builds only)",
    )
    args = parser.parse_args(argv)
    unknown = set(args.releasing) - {site.app for site in SITES}
    if unknown:
        print(f"check_sibling_versions: unknown app(s) {sorted(unknown)}", file=sys.stderr)
        return 2
    try:
        tags = _published_tags()
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        if args.offline_ok:
            print(f"check_sibling_versions: could not read releases ({error}); skipped.")
            return 0
        print(
            f"check_sibling_versions: could not read the published releases ({error}). "
            "A release build does not guess; pass --offline-ok only for a dev build.",
            file=sys.stderr,
        )
        return 2
    sources = {site.app: source_version(site) for site in SITES}
    published = {site.app: newest_published(tags, site.tag_prefix) for site in SITES}
    problems = disagreements(sources, published, set(args.releasing))
    if problems:
        print("GATE-SIBVER: an app's version is out of step with what is published:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    summary = ", ".join(f"{app} {sources[app]}" for app in sorted(sources) if published[app])
    print(f"GATE-SIBVER: every published app's version agrees ({summary}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
