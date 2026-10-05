"""Promote a listed build: Dev to Beta, or Beta to Stable, as the same files (plan 4.3).

    python scripts/promote_release.py --app radio --version 3.3.0 --to stable --dry-run
    python scripts/promote_release.py --app radio --version 3.3.0 --to stable
    python scripts/promote_release.py --app radio --version 3.3.0 --to stable \\
        --skip-soak "fixes a crash on start in 3.2.0; signed off by Jeff"

Every check runs first and is printed as PASS, WARN or FAIL; one FAIL stops
the promotion. ``--dry-run`` prints the list and changes nothing.

* P1  the release exists on GitHub, is not a draft, and is not withdrawn
* P2  every file is downloaded again and matches the feed's size and SHA-256
* P3  the feed's signature is valid and its sequence will go up
* P4  Stable: a final-numbered build (never ``-beta.N``), and it was on Beta first
* P5  Stable: Authenticode-signed files, when ``QUILL_SIGN_REQUIRED=1``
* P6  the tag, the feed version and the file names agree
* P7  nothing this build carries is ahead of that app on the channel
* P8  the changelog has a section for this version
* P9  Stable: a screen-reader sign-off sheet, ``docs/qa/signoffs/<app>-<version>.md``,
      saying ``Result: pass`` with a tester, the screen readers and a date
* P10 at least 7 days on Beta (1 on Dev); shorter only with ``--skip-soak "reason"``,
      and the reason is written into the build's history in the feed
* P11 a warning when going back to the previous Stable will need a saved copy
* P12 the documentation gates pass (``scripts/check_docs_artifacts.py``)

For Stable, the notes are rolled up from the Beta sections since the current
Stable build (``scripts/rollup_release_notes.py``; ``--dry-run`` prints them),
unless ``--notes-file`` gives them; they become the GitHub release body and the
feed's ``notes_summary``.

Then: the GitHub release stops being a prerelease (QUILL's own Stable release
also becomes "Latest"), its title says when it was promoted, the feed lists it
on the new channel with a fresh 90-day expiry, and a line goes into
``docs/release/promotions.log``. The feed is signed with the owner's key, or
left unsigned with ``--no-sign`` (the promote workflow), to be signed with
``scripts/feed_tool.py sign`` before it can merge.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quill.core.updater.feed import ReleaseFeed  # noqa: E402
from quill.core.updater.feed_publish import (  # noqa: E402
    Check,
    blocking,
    promote,
    promotion_checks,
)
from quill.core.updater.notes_rollup import notes_summary  # noqa: E402
from quill.tools import release_feed as rf  # noqa: E402

DocsGate = Callable[[], bool]


def _docs_gate() -> bool:
    result = subprocess.run(  # noqa: S603 - fixed script, argument list
        [sys.executable, str(REPO_ROOT / "scripts" / "check_docs_artifacts.py")],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app", required=True, choices=sorted(rf.APPS))
    parser.add_argument("--version", required=True)
    parser.add_argument("--to", required=True, choices=("beta", "stable"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-soak", default="", metavar="REASON")
    parser.add_argument("--notes-file", type=Path)
    parser.add_argument("--report", type=Path, help="also write the check list here")
    parser.add_argument("--no-sign", action="store_true")
    parser.add_argument("--key-file", type=Path)
    return parser


def gather_checks(
    args: argparse.Namespace,
    *,
    gh: rf.Gh,
    root: Path,
    now: datetime,
    docs_gate: DocsGate,
) -> tuple[ReleaseFeed, list[Check]]:
    feed = rf.load_feed(args.app, root)
    siblings = {key: rf.load_feed(key, root) for key in rf.APPS if key != args.app}
    checks = promotion_checks(
        feed,
        args.version,
        args.to,
        now=now,
        skip_soak_reason=args.skip_soak,
        sibling_feeds=siblings,
    )
    release = feed.release(args.version)
    if release is None:
        return feed, checks
    tag = rf.tag_for(args.app, args.version)
    repo = rf.repo_of(feed, args.version)
    feed_path = rf.feed_dir(root) / f"{args.app}.json"
    checks.append(Check("P3s", "the feed's signature is valid", rf.feed_signature_ok(feed_path)))
    try:
        info = gh(["release", "view", tag, "--repo", repo, "--json", "isDraft,tagName"])
        ok = '"isDraft":false' in info.replace(" ", "")
        checks.append(Check("P1g", f"{tag} is published on {repo}", ok))
    except (subprocess.CalledProcessError, OSError) as error:
        checks.append(Check("P1g", f"{tag} is published on {repo}", False, str(error)))
    mismatched: list[str] = []
    with tempfile.TemporaryDirectory() as scratch:
        try:
            gh(["release", "download", tag, "--repo", repo, "--dir", scratch])
        except (subprocess.CalledProcessError, OSError) as error:
            mismatched.append(f"download failed: {error}")
        for asset in release.assets:
            path = Path(scratch) / asset.name
            if not path.is_file():
                mismatched.append(f"{asset.name} is missing")
                continue
            size, sha = rf.hash_file(path)
            if size != asset.size or sha != asset.sha256:
                mismatched.append(f"{asset.name} does not match the feed")
        if args.to == "stable" and os.environ.get("QUILL_SIGN_REQUIRED") == "1":
            checks.append(_authenticode(Path(scratch), release.assets))
        else:
            checks.append(Check("P5", "Authenticode", True, "not required for this promotion"))
    checks.append(Check("P2", "every file matches the feed", not mismatched, "; ".join(mismatched)))
    # A build (3.2.0+2) is promoted as itself, but its files, changelog section
    # and sign-off sheet carry the release number alone (3.2.0).
    number = rf.file_version_text(args.version)
    names_ok = all(number in a.name for a in release.assets if a.kind != "build-info")
    checks.append(Check("P6", "tag, version and file names agree", names_ok and release.tag == tag))
    checks.append(
        Check("P8", "the changelog has this version", rf.changelog_has(args.app, number, root))
    )
    if args.to == "stable":
        problems = rf.signoff_problems(args.app, number, root)
        checks.append(Check("P9", "screen-reader sign-off", not problems, "; ".join(problems)))
    checks.append(Check("P12", "documentation gates", docs_gate()))
    return feed, checks


def _authenticode(folder: Path, assets: object) -> Check:
    unsigned = []
    for asset in assets:  # type: ignore[attr-defined]
        if not asset.name.lower().endswith(".exe"):
            continue
        result = subprocess.run(  # noqa: S603 - fixed script, argument list
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "code_signing.py"),
                "verify",
                str(folder / asset.name),
            ],
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            unsigned.append(asset.name)
    return Check("P5", "Authenticode-signed installers", not unsigned, ", ".join(unsigned))


def _rolled_up(
    args: argparse.Namespace, feed: ReleaseFeed, root: Path, out: Callable[[str], None]
) -> str:
    """Stable's "What's new since" notes, printed (plan 4.5); "" for Beta or a notes file."""
    if args.to != "stable" or args.notes_file:
        return ""
    result, problems = rf.rolled_up_notes(args.app, args.version, feed=feed, root=root)
    for problem in problems:
        out(f"Note: {problem}")
    if not result.merged:
        return ""
    text = result.markdown()
    out("Stable release notes (the same as scripts/rollup_release_notes.py):")
    out(text.rstrip())
    return text


def run(
    argv: list[str] | None = None,
    *,
    gh: rf.Gh = rf.gh_cli,
    root: Path = rf.REPO_ROOT,
    now: datetime | None = None,
    seed_reader: Callable[[Path | None], bytes] = rf.read_seed,
    docs_gate: DocsGate = _docs_gate,
    out: Callable[[str], None] = print,
) -> int:
    args = build_parser().parse_args(argv)
    moment = now or datetime.now(UTC)
    feed, checks = gather_checks(args, gh=gh, root=root, now=moment, docs_gate=docs_gate)
    lines = [check.line() for check in checks]
    for line in lines:
        out(line)
    if args.report:
        args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    stopped = blocking(checks)
    if stopped:
        out(f"Not promoted: {len(stopped)} check(s) failed.")
        return 1
    rolled = _rolled_up(args, feed, root, out)
    if args.dry_run:
        out(f"Dry run: every check passed; {args.app} {args.version} can go to {args.to}.")
        return 0
    if args.notes_file:
        notes = args.notes_file.read_text(encoding="utf-8")
    else:
        notes = notes_summary(rolled) if rolled else ""
    feed = promote(
        feed,
        args.version,
        args.to,
        now=moment,
        skip_soak_reason=args.skip_soak,
        notes_summary=notes,
    )
    tag = rf.tag_for(args.app, args.version)
    repo = rf.repo_of(feed, args.version)
    if args.to == "stable" and repo == rf.MAIN_REPO:
        title = f"{rf.app(args.app).name} {args.version} (promoted to Stable on {moment:%d %B %Y})"
        latest = "--latest=true" if args.app == "quill" else "--latest=false"
        command = ["release", "edit", tag, "--repo", repo, "--prerelease=false", latest]
        command += ["--title", title, *(["--notes", rolled] if rolled else [])]
        gh(command)
    seed = None if args.no_sign else seed_reader(args.key_file)
    rf.write_feed(feed, seed=seed, root=root)
    reason = f" (shortened soak: {args.skip_soak})" if args.skip_soak else ""
    rf.append_promotion_log(f"{args.app} {args.version} promoted to {args.to}{reason}", root=root)
    out(f"Promoted {args.app} {args.version} to {args.to} (feed sequence {feed.sequence}).")
    if seed is None:
        out(f"Unsigned: run python scripts/feed_tool.py sign --app {args.app}")
    for warning in rf.warnings_now(root, moment):
        out(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
