"""List a new build on Beta or Dev, in the signed v2 release feed (plan 4.2).

Two ways in:

* **A local build** (Quill Radio, QUILL Lite, QUILL Cast are built on the
  owner's computer): ``--dist <folder>`` hashes the files the build left there,
  creates the GitHub release (always a prerelease, never "Latest"), uploads
  them, and lists the build::

      python scripts/publish_release.py --app radio --version 3.3.0-beta.1 \\
          --channel beta --dist standalone/radio/dist --notes-file notes.md

* **A release that already exists on GitHub** -- QUILL's own, made by
  ``windows-release.yml``, or a Dev build made by ``dev-builds.yml`` in
  ``Community-Access/quillville-dev-builds`` -- with ``--existing``: the files
  are downloaded and hashed here, never taken from GitHub's word::

      python scripts/publish_release.py --app quill --version 1.0.0-rc.1 \\
          --channel beta --existing
      python scripts/publish_release.py --app radio --version 3.3.0-dev.20261003.1 \\
          --channel dev --existing

**Build numbers.** A Beta or Stable-candidate build carries one: the same
version can ship more than once, and a rebuild must be offered to everyone on
the earlier build (docs/release/RELEASE.md, "Build numbers"). ``--build N``
names it; left out, it is the next build after the newest tag published for
this version, so ``--version 3.2.0`` lists ``3.2.0+2`` under the tag
``quill-radio-v3.2.0-build.2`` when build 1 is out. ``--version 3.2.0+2`` says
the same thing. A Dev build has no build number (its version is unique).

**Code signing (owner decision, 2026-10-04).** Beta and Dev builds are never
Authenticode-signed, and Stable always is. A build's number decides which it
is: a final-numbered build (``3.2.0``) is a Stable candidate, built with
``-Sign``, and every installer and every program in its portable zip must be
signed; a ``-dev``, ``-alpha``, ``-beta`` or ``-rc`` build's installer must not
be. Either mismatch is refused here, before anything is created, so a
candidate that could never reach Stable does not spend a week on Beta first.

Before anything is created it checks the **page budget**: installed Quill
Radio 3.0.4 and QUILL Lite 1.1.2 read only the first 30 releases, so the main
repository may not hold more than 20 newer than any app's newest Stable one.
When a newer Beta supersedes older ones, their GitHub release objects are
deleted (the tags stay) and they leave the feed; ``--keep-superseded`` keeps
them.

The feed is signed here with the owner's key (``QUILL_FEED_KEY_FILE`` or
``~/.config/quill/quill-feed-priv.key``); ``--no-sign`` writes it unsigned for
signing later with ``scripts/feed_tool.py sign``. Every run ends with a
warning for any app's feed that expires within 14 days. Nothing is committed:
review ``docs/site/updates/v2`` and land it through a pull request.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quill.core.release_tags import next_build  # noqa: E402
from quill.core.updater.feed_publish import (  # noqa: E402
    formats_for_build,
    list_release,
    page_budget_problems,
    refresh,
    superseded_prereleases,
)
from quill.core.versioning import ReleaseVersion  # noqa: E402
from quill.tools import release_feed as rf  # noqa: E402

#: Is this release file Authenticode-signed throughout? (code_signing.asset_is_signed)
Authenticode = Callable[[Path], bool]


def _asset_is_signed(path: Path) -> bool:
    from scripts.code_signing import asset_is_signed

    return asset_is_signed(path)


def signing_problems(files: list[Path], version: ReleaseVersion, signed: Authenticode) -> list[str]:
    """Why these files may not be listed as *version*, by the signing rule; [] when fine.

    A final-numbered build is a Stable candidate: its installer and portable
    files must all be signed. Any other build is Beta or Dev: its installer
    must not be. (A portable zip of a Beta build is not checked: it carries
    Python's own signed python.exe whoever built it.)
    """
    shown = version.semver()
    if not version.is_prerelease:
        unsigned = [p.name for p in _kinds(files) if not signed(p)]
        if unsigned:
            return [
                f"{shown} is a Stable candidate, so it must be code-signed when it is built, "
                f"and these are not: {', '.join(unsigned)}. Rebuild it with -Sign and list "
                "that build instead."
            ]
        return []
    stray = [p.name for p in files if rf.asset_kind(p.name) == "installer" and signed(p)]
    if stray:
        return [
            f"{shown} is a Beta or Dev build, and Beta and Dev builds are never code-signed, "
            f"but these are: {', '.join(stray)}. Rebuild it without -Sign."
        ]
    return []


def _kinds(files: list[Path]) -> list[Path]:
    return [p for p in files if rf.asset_kind(p.name) in ("installer", "portable")]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app", required=True, choices=sorted(rf.APPS))
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--build",
        type=int,
        default=0,
        help="the build number (default: the next after the newest published tag)",
    )
    parser.add_argument("--channel", required=True, choices=("beta", "dev"))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dist", type=Path, help="folder holding this build's files")
    source.add_argument("--existing", action="store_true", help="the release is on GitHub")
    parser.add_argument("--repo", default="", help="override the repository")
    parser.add_argument("--notes-file", type=Path)
    parser.add_argument("--keep-superseded", action="store_true")
    parser.add_argument("--no-sign", action="store_true")
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def run(
    argv: list[str] | None = None,
    *,
    gh: rf.Gh = rf.gh_cli,
    root: Path = rf.REPO_ROOT,
    now: datetime | None = None,
    seed_reader: Callable[[Path | None], bytes] = rf.read_seed,
    out: Callable[[str], None] = print,
    authenticode: Authenticode = _asset_is_signed,
) -> int:
    args = build_parser().parse_args(argv)
    moment = now or datetime.now(UTC)
    parsed = ReleaseVersion.try_parse(args.version)
    if parsed is None:
        out(f"{args.version!r} is not a version.")
        return 2
    repo = args.repo or (rf.DEV_REPO if args.channel == "dev" else rf.MAIN_REPO)
    if args.build and parsed.build and args.build != parsed.build:
        out(f"{args.version} is build {parsed.build}, not build {args.build}.")
        return 2
    version = args.version
    feed = rf.load_feed(args.app, root)
    wants_build = parsed.stage != "dev" and args.channel != "dev"
    listing = (
        rf.release_listing(gh, repo)
        if repo == rf.MAIN_REPO or (wants_build and not (parsed.build or args.build))
        else []
    )
    if wants_build:
        build = parsed.build or args.build
        if not build:
            # The tags on GitHub and the builds already in the feed, so a build
            # that fell off the first page of releases still counts.
            known = [listed.tag for listed in listing]
            known += [rf.tag_for(args.app, r.version) for r in feed.releases]
            build = next_build(known, args.app, parsed.plain())
            if args.existing:  # the release is already made: list the newest build of it
                build -= 1
        version = parsed.with_build(build).semver()
    tag = rf.tag_for(args.app, version)
    if feed.release(version) is not None:
        out(f"{version} is already in the {args.app} feed. Nothing to do.")
        return 1

    if repo == rf.MAIN_REPO:
        problems = page_budget_problems(listing, adding=0 if args.existing else 1)
        if problems:
            for line in problems:
                out(f"Refused: {line}")
            return 1

    with tempfile.TemporaryDirectory() as scratch:
        if args.existing:
            gh(["release", "download", tag, "--repo", repo, "--dir", scratch])
            files = [p for p in Path(scratch).iterdir() if rf.asset_kind(p.name)]
        else:
            files = rf.dist_files(args.dist, args.app, version)
        assets = rf.assets_from_files(files, repo=repo, tag=tag)
        refused = signing_problems(list(files), ReleaseVersion.parse(version), authenticode)
    if refused:
        for line in refused:
            out(f"Refused: {line}")
        return 1
    if not any(a.kind in ("installer", "portable") for a in assets):
        out(f"No installer or portable file for {args.app} {version} was found.")
        return 1
    for asset in assets:
        out(f"{asset.kind:10} {asset.name}  {asset.size} bytes  sha256 {asset.sha256}")

    if not args.existing and not args.dry_run:
        title = f"{rf.app(args.app).name} {ReleaseVersion.parse(version).display()}"
        command = ["release", "create", tag, "--repo", repo, "--title", title]
        command += ["--prerelease", "--latest=false"]
        command += ["--notes-file", str(args.notes_file)] if args.notes_file else ["--notes", ""]
        command += [str(p) for p in rf.dist_files(args.dist, args.app, version)]
        gh(command)

    writes, reads, lossy = formats_for_build(args.app)
    notes = args.notes_file.read_text(encoding="utf-8") if args.notes_file else ""
    feed = list_release(
        feed,
        version=version,
        tag=tag,
        channel=args.channel,
        assets=assets,
        now=moment,
        notes_url=f"https://github.com/{repo}/releases/tag/{tag}",
        notes_summary=notes,
        data_formats=writes,
        reads_formats=reads,
        lossy_formats=lossy,
    )
    if not args.keep_superseded and args.channel == "beta":
        old = [
            r
            for r in superseded_prereleases(feed, "beta")
            if any(f"/{rf.MAIN_REPO}/" in a.url for a in r.assets)
        ]
        for release in old:
            out(f"Superseded: {release.version} (its release object goes; the tag stays)")
            if not args.dry_run:
                gh(["release", "delete", release.tag, "--repo", rf.MAIN_REPO, "--yes"])
        if old:
            keep = tuple(r for r in feed.releases if r not in old)
            feed = refresh(replace(feed, releases=keep), moment)

    if args.dry_run:
        out(f"Dry run: {args.app} {version} would be listed on {args.channel}.")
        return 0
    seed = None if args.no_sign else seed_reader(args.key_file)
    path = rf.write_feed(feed, seed=seed, root=root)
    out(f"Listed {args.app} {version} on {args.channel}: {path} (sequence {feed.sequence})")
    if seed is None:
        out("Unsigned: run python scripts/feed_tool.py sign --app " + args.app)
    for warning in rf.warnings_now(root, moment):
        out(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
