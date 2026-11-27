"""Keep the rolling Dev release in order: create it, record builds, retire old ones.

``dev-builds.yml`` publishes each Dev build as a few files in ONE prerelease of
this repository (``quill.tools.dev_release`` says why one). This script is the
only thing that writes that release's notes or deletes anything from it:

* ``--ensure`` makes the release if it is not there yet (the ``decide`` job runs
  this once, before eleven apps upload in parallel, so they never race to make
  it);
* ``--sha <commit>`` runs after the uploads. It writes one line into the notes
  for every build whose files have arrived and that has no line yet, naming the
  commit it was built from, then deletes the files of old builds: it keeps the
  newest ``--keep`` builds of each app, **and every build a signed feed in this
  checkout still points at**, so a Beta or Stable build is never pulled out from
  under the people downloading it.

Run only where ``gh`` has ``contents: write`` on the repository (the workflow's
own token is enough; no personal token is involved).
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quill.tools import dev_release as dev  # noqa: E402
from quill.tools import release_feed as rf  # noqa: E402

#: How many builds of each app stay downloadable, beyond any a feed points at.
DEFAULT_KEEP = 3

RELEASE_TITLE = "Dev builds (unsigned)"
NOTES_HEAD = """\
Unsigned Dev builds of every QUILL app, made from `main`. Anyone can download them.

These are for testing and diagnosis, not for everyday use: Windows may say
"unknown publisher", and a Dev build can be rough. Each build's files carry its
version (for example `3.2.0-dev.20261126.1`). The newest few builds of each app
are kept here; older ones are removed automatically.

This one release holds all of them, so it takes a single place in the repository's
release list. A build that has been promoted to Beta or Stable stays here for as
long as the update feed points at it.

Builds, and the commit each was made from:
"""

_FEED_URL_RE = re.compile(r"/releases/download/" + re.escape(dev.DEV_TAG) + r"/([^\"'\s)]+)")


def _version_key(version: str) -> tuple[int, int]:
    """``(date, number)`` of a Dev version, so builds sort oldest to newest."""
    tail = version.rsplit("-dev.", 1)[-1]
    date, _dot, number = tail.partition(".")
    return int(date) if date.isdigit() else 0, int(number) if number.isdigit() else 0


def protected_names(root: Path) -> set[str]:
    """File names in the rolling release that a signed feed in *root* points at."""
    names: set[str] = set()
    folder = rf.feed_dir(root)
    if folder.is_dir():
        for path in folder.glob("*.json"):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            names.update(unquote(m.group(1)) for m in _FEED_URL_RE.finditer(text))
    return names


def ensure_release(gh: rf.Gh, repo: str, *, out: Callable[[str], None] = print) -> bool:
    """Make the rolling release if it is missing. Returns whether it was made."""
    if dev.get_release(gh, repo):
        out(f"The {dev.DEV_TAG} release is there.")
        return False
    with tempfile.TemporaryDirectory() as scratch:
        notes = Path(scratch) / "notes.md"
        notes.write_text(NOTES_HEAD, encoding="utf-8")
        gh([
            "release",
            "create",
            dev.DEV_TAG,
            "--repo",
            repo,
            "--target",
            "main",
            "--title",
            RELEASE_TITLE,
            "--notes-file",
            str(notes),
            "--prerelease",
            "--latest=false",
        ])
    out(f"Made the {dev.DEV_TAG} release.")
    return True


def finalize(
    gh: rf.Gh,
    repo: str,
    sha: str,
    *,
    root: Path = REPO_ROOT,
    keep: int = DEFAULT_KEEP,
    dry_run: bool = False,
    out: Callable[[str], None] = print,
) -> int:
    """Record new builds in the notes and retire old ones. Returns an exit code."""
    if not re.fullmatch(r"[0-9a-fA-F]{40}", sha or ""):
        out("The commit must be a full 40-character SHA.")
        return 2
    release = dev.get_release(gh, repo)
    if not release:
        out(f"There is no {dev.DEV_TAG} release; nothing to record.")
        return 1
    lines = dev.build_lines(str(release.get("body") or ""))
    groups = dev.group_assets(dev._assets(release))

    # A build is recorded once its sound files are there: an installer or a
    # portable zip, not just a checksums file from an upload that stopped.
    recorded = 0
    for (app_key, version), files in sorted(groups.items()):
        tag = rf.tag_for(app_key, version)
        has_files = any(rf.asset_kind(str(f["name"])) in ("installer", "portable") for f in files)
        if tag not in lines and has_files:
            lines[tag] = sha.lower()
            recorded += 1
            out(f"Recorded {tag} (built from {sha[:7]}).")

    protected = protected_names(root)
    by_app: dict[str, list[str]] = {}
    for app_key, version in groups:
        by_app.setdefault(app_key, []).append(version)
    deleted: list[str] = []
    for app_key, versions in sorted(by_app.items()):
        newest_first = sorted(versions, key=_version_key, reverse=True)
        for version in newest_first[keep:]:
            files = groups[(app_key, version)]
            names = [str(f["name"]) for f in files]
            if any(name in protected for name in names):
                out(f"Kept {rf.tag_for(app_key, version)}: an update feed points at it.")
                continue
            for name in names:
                out(f"Retired {name}")
                if not dry_run:
                    gh(["release", "delete-asset", dev.DEV_TAG, name, "--repo", repo, "--yes"])
            deleted.append(rf.tag_for(app_key, version))
            lines.pop(rf.tag_for(app_key, version), None)

    # A line whose files are gone says nothing true; drop it.
    present = {rf.tag_for(a, v) for (a, v) in groups} - set(deleted)
    notes = NOTES_HEAD + "".join(
        f"{tag}: Built from Community-Access/quill@{lines[tag]}.\n"
        for tag in sorted(lines)
        if tag in present
    )
    if notes != str(release.get("body") or "") and not dry_run:
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "notes.md"
            path.write_text(notes, encoding="utf-8")
            gh(["release", "edit", dev.DEV_TAG, "--repo", repo, "--notes-file", str(path)])
    out(f"Dev builds: {recorded} recorded, {len(deleted)} retired.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=rf.MAIN_REPO)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ensure", action="store_true", help="make the release if it is missing")
    mode.add_argument("--sha", help="record new builds as made from this commit, then tidy")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.ensure:
        ensure_release(rf.gh_cli, args.repo)
        return 0
    return finalize(rf.gh_cli, args.repo, args.sha, keep=args.keep, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
