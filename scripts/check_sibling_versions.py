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

**Channel-aware since release channels (GATE-SIBVER-CH, plan 6.5).** A build
for the Stable runtime slot (``--channel stable``, the default) keeps the strict
rule, measured against each sibling's newest *Stable* release. A build for the
Beta or Dev slot (``--channel beta`` / ``dev``) may carry a sibling that is
ahead -- that slot is code the listener chose to test, and About already says
"running shared runtime code X" -- and is only refused for being *behind*. The
moment a build enters Stable, ``promote_release.py`` (check P7) applies the
strict rule again.

**Build numbers (2026-10).** A source version is its constant plus its build
constant (``_VERSION = "3.2.0"`` and ``_BUILD = 2`` is ``3.2.0+2``), and a tag
carries its build as ``-build.2``. Builds are compared only when *both* sides
carry one: a release tagged before build numbers (``quill-radio-v3.0.4``) says
nothing about builds, so a source at ``3.0.4`` build 1 agrees with it. Where
both do, a rebuild is held to the same rule as a release: a sibling may not
carry a build nobody can download, and a build that releases an app must bump
its build constant.

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
if str(REPO_ROOT) not in sys.path:  # run as a script from a build: find quill/
    sys.path.insert(0, str(REPO_ROOT))
RELEASE_REPO = "Community-Access/quill"


@dataclass(frozen=True)
class AppVersionSite:
    """Where an app's version lives in source, and how its releases are tagged."""

    app: str
    source: str
    constant: str
    tag_prefix: str
    #: The app's build-number constant beside *constant* (build numbers).
    build_constant: str = ""


#: Every app whose version travels in the shared runtime. An app with no
#: published release under its prefix yet is skipped: there is nothing to be
#: ahead of, and the first release is the one that sets the mark.
SITES: tuple[AppVersionSite, ...] = (
    AppVersionSite("radio", "quill/apps/radio.py", "_VERSION", "quill-radio-v", "_BUILD"),
    AppVersionSite(
        "quilllite", "quill/core/lite/__init__.py", "APP_VERSION", "quill-lite-v", "APP_BUILD"
    ),
    AppVersionSite(
        "converter", "quill/apps/converter.py", "_VERSION", "quill-converter-v", "_BUILD"
    ),
    AppVersionSite("weather", "quill/apps/weather.py", "_VERSION", "quill-weather-v", "_BUILD"),
    AppVersionSite("inkwell", "quill/apps/inkwell.py", "_VERSION", "quill-inkwell-v", "_BUILD"),
    AppVersionSite("player", "quill/apps/player.py", "_VERSION", "quill-player-v", "_BUILD"),
    AppVersionSite(
        "cast", "quill/apps/podcasts_menu.py", "APP_VERSION", "quill-cast-v", "APP_BUILD"
    ),
)


def parse_version(text: str) -> tuple[object, ...]:
    """A sort key for *text*, or ``()`` when it is not a version.

    Delegates to :mod:`quill.core.versioning`, the family's one parser, so a
    pre-release sorts below its plain number and two pre-releases of one
    version are ordered too (``3.3.0-beta.1 < 3.3.0-beta.2 < 3.3.0``). The old
    parser here made every pre-release of a version equal.
    """
    from quill.core.versioning import ReleaseVersion

    parsed = ReleaseVersion.try_parse(text)
    return () if parsed is None else parsed.key()


def source_version(site: AppVersionSite, root: Path = REPO_ROOT) -> str:
    """The app's version in source, with its build: ``3.2.0+2`` (``3.2.0`` when
    the app has no build constant, or it is 0)."""
    text = (root / site.source).read_text(encoding="utf-8")
    match = re.search(rf'^{re.escape(site.constant)}\s*=\s*"([^"]+)"', text, re.M)
    if not match:
        raise ValueError(f'{site.source} has no {site.constant} = "..." line')
    version = match.group(1)
    if site.build_constant:
        build = re.search(rf"^{re.escape(site.build_constant)}\s*=\s*(\d+)", text, re.M)
        if build:
            from quill.core.versioning import with_build

            version = with_build(version, int(build.group(1)))
    return version


def _comparable(source: str, published: str) -> tuple[tuple[object, ...], tuple[object, ...]]:
    """Sort keys for the two, with builds compared only when both carry one."""
    from quill.core.versioning import ReleaseVersion

    src, pub = ReleaseVersion.try_parse(source), ReleaseVersion.try_parse(published)
    if src is None or pub is None:
        return parse_version(source), parse_version(published)
    if not src.build or not pub.build:
        src, pub = src.without_build(), pub.without_build()
    return src.key(), pub.key()


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
    *,
    channel: str = "stable",
) -> list[str]:
    """One sentence per app whose source version disagrees with what is published.

    *sources* and *published* are keyed by app id; a published ``None`` means
    the app has never been released and is skipped. *channel* is the runtime
    slot this build is for: only ``stable`` refuses a sibling that is ahead.
    """
    problems: list[str] = []
    for app, source in sorted(sources.items()):
        latest = published.get(app)
        if latest is None:
            continue
        src, pub = _comparable(source, latest)
        if src > pub and app not in releasing and channel != "stable":
            continue  # a Beta or Dev slot carries siblings ahead by design
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
                f"{source}, which is already published. Bump the version in the release "
                "commit -- or, to ship the same version again, its build number."
            )
    return problems


def _published_tags(*, stable_only: bool = False) -> list[str]:
    """Every release tag in the release repo, read through the gh CLI.

    *stable_only* leaves out prereleases (Beta and release-candidate listings),
    which is what the Stable slot is measured against.
    """
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
            "tagName,isDraft,isPrerelease",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        str(entry["tagName"])
        for entry in json.loads(result.stdout or "[]")
        if not entry.get("isDraft") and not (stable_only and entry.get("isPrerelease"))
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
        "--channel",
        choices=("stable", "beta", "dev"),
        default="stable",
        help="the runtime slot this build is for (GATE-SIBVER-CH)",
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
        tags = _published_tags(stable_only=args.channel == "stable")
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
    problems = disagreements(sources, published, set(args.releasing), channel=args.channel)
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
