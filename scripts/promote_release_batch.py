"""Preflight and promote one complete Dev build batch to Beta.

The Dev release repository contains one release per catalogue app.  A batch
is identified by the exact ``main`` commit written into every release body by
``dev-builds.yml``.  Listing and promotion are delegated to the existing
single-app scripts so their signing, hashing, feed and soak rules stay the
authority.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quill.core.release_catalog import PRODUCTS  # noqa: E402
from quill.core.updater.feed import ReleaseFeed  # noqa: E402
from quill.core.versioning import ReleaseVersion  # noqa: E402
from quill.tools import release_feed as rf  # noqa: E402
from scripts import promote_release, publish_release  # noqa: E402

FULL_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
DEV_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+-dev\.(?P<date>\d{8})\.(?P<number>[1-9]\d*)$")
SOURCE_MARKER_RE = re.compile(r"Built from Community-Access/quill@(?P<sha>[0-9a-fA-F]{40})\.")

ShaVerifier = Callable[[str, Path], None]
DocsGate = Callable[[], bool]


class BatchError(RuntimeError):
    """The Dev releases or their promotion checks do not form a safe batch."""


@dataclass(frozen=True, slots=True)
class DevBuild:
    """One validated release from the Dev-builds repository."""

    app: str
    version: str
    tag: str
    source_sha: str
    published_at: datetime
    checksum_file: str


@dataclass(frozen=True, slots=True)
class AuditRow:
    app: str
    tag: str
    version: str
    source_sha: str
    checksum_file: str
    result: str
    final: str


def catalogue_apps() -> tuple[str, ...]:
    """The ordered channel-enabled catalogue, cross-checked with feed APPS."""
    enabled = tuple(product.key for product in PRODUCTS if product.channels_enabled)
    feed_apps = tuple(rf.APPS)
    if enabled != feed_apps:
        missing = sorted(set(enabled) - set(feed_apps))
        extra = sorted(set(feed_apps) - set(enabled))
        raise BatchError(
            "release catalogue and release-feed app sets differ: "
            f"missing from feed APPS={missing or 'none'}, extra in feed APPS={extra or 'none'}"
        )
    return enabled


def normalize_sha(value: str) -> str:
    """Validate a full commit ID before it can reach a subprocess or report."""
    if FULL_SHA_RE.fullmatch(value) is None:
        raise BatchError("sha must be exactly 40 hexadecimal characters from main")
    return value.lower()


def validate_skip_soak(value: str) -> str:
    """A soak override is one bounded, printable argument, never a shell script."""
    reason = value.strip()
    if len(reason) > 500:
        raise BatchError("skip_soak reason must be 500 characters or fewer")
    if any(ord(character) < 32 or ord(character) == 127 for character in reason):
        raise BatchError("skip_soak reason must be one line of printable text")
    return reason


def verify_main_sha(source_sha: str, root: Path) -> None:
    """Ensure the exact ID is a commit and is contained by the checked-out main."""
    checked = subprocess.run(  # noqa: S603 - fixed executable, validated SHA
        ["git", "rev-parse", "--verify", f"{source_sha}^{{commit}}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if checked.returncode != 0 or checked.stdout.strip().lower() != source_sha:
        raise BatchError(f"{source_sha} is not an existing commit in this checkout")
    ancestor = subprocess.run(  # noqa: S603 - fixed executable, validated SHA
        ["git", "merge-base", "--is-ancestor", source_sha, "origin/main"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if ancestor.returncode == 1:
        raise BatchError(f"{source_sha} is not on origin/main")
    if ancestor.returncode != 0:
        detail = ancestor.stderr.strip() or "origin/main could not be checked"
        raise BatchError(f"could not verify {source_sha} against origin/main: {detail}")


def _flatten_release_pages(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        raise BatchError("GitHub releases response was not a list")
    pages = payload
    if pages and all(isinstance(page, list) for page in pages):
        flattened: list[dict[str, object]] = []
        for page in pages:
            assert isinstance(page, list)
            if not all(isinstance(item, dict) for item in page):
                raise BatchError("GitHub releases response contained an invalid page")
            flattened.extend(page)
        return flattened
    if not all(isinstance(item, dict) for item in pages):
        raise BatchError("GitHub releases response contained a non-release row")
    return pages


def fetch_dev_releases(gh: rf.Gh) -> list[dict[str, object]]:
    """Read every published Dev release without relying on one page."""
    try:
        raw = gh([
            "api",
            f"repos/{rf.DEV_REPO}/releases?per_page=100",
            "--paginate",
            "--slurp",
        ])
    except (subprocess.CalledProcessError, OSError) as error:
        raise BatchError("could not query Dev releases from GitHub") from error
    try:
        return _flatten_release_pages(json.loads(raw or "[]"))
    except (json.JSONDecodeError, TypeError) as error:
        raise BatchError(f"GitHub releases response was not valid JSON: {error}") from error


def _published_at(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("the release has no published_at timestamp")
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        raise ValueError("published_at has no time zone")
    return moment.astimezone(UTC)


def _parse_matching_release(row: dict[str, object], source_sha: str, enabled: set[str]) -> DevBuild:
    tag = str(row.get("tag_name") or "")
    found = rf.app_for_tag(tag)
    if found is None:
        raise ValueError(f"{tag or '<untagged>'} does not name a release-catalogue app")
    app, tagged_version = found
    if app not in enabled:
        raise ValueError(f"{tag} names {app}, which is not channel-enabled")
    if DEV_VERSION_RE.fullmatch(tagged_version) is None:
        raise ValueError(f"{tag} is not a canonical Dev version tag")
    parsed = ReleaseVersion.try_parse(tagged_version)
    if parsed is None or parsed.stage != "dev" or parsed.build:
        raise ValueError(f"{tag} does not describe a build-less Dev release")
    if parsed.semver() != tagged_version or rf.tag_for(app, tagged_version) != tag:
        raise ValueError(f"{tag} and {tagged_version} disagree")
    if row.get("draft") is not False or row.get("prerelease") is not True:
        raise ValueError(f"{tag} must be published and prerelease=true")
    expected_name = f"{rf.app(app).name} {tagged_version} (Dev)"
    if row.get("name") != expected_name:
        raise ValueError(f"{tag} has title {row.get('name')!r}, expected {expected_name!r}")
    expected_line = (
        f"Dev build of {rf.app(app).name}, unsigned. "
        f"Built from Community-Access/quill@{source_sha}."
    )
    body = str(row.get("body") or "")
    if not body.splitlines() or body.splitlines()[0] != expected_line:
        raise ValueError(f"{tag} has a mismatched app, title or source-SHA body line")
    assets = row.get("assets")
    if not isinstance(assets, list):
        raise ValueError(f"{tag} has no release asset metadata")
    names = [
        str(asset.get("name") or "")
        for asset in assets
        if isinstance(asset, dict) and rf.asset_kind(str(asset.get("name") or ""))
    ]
    if not names:
        raise ValueError(f"{tag} has no installer or portable asset")
    prefix = rf.app(app).asset_prefix.lower()
    if any(not name.lower().startswith(prefix) or tagged_version not in name for name in names):
        raise ValueError(f"{tag} has an asset with a mismatched app or version")
    checksum_names = [
        str(asset.get("name") or "")
        for asset in assets
        if isinstance(asset, dict) and asset.get("name") == "SHA256SUMS.txt"
    ]
    if len(checksum_names) != 1:
        raise ValueError(f"{tag} must have exactly one SHA256SUMS.txt")
    return DevBuild(
        app=app,
        version=tagged_version,
        tag=tag,
        source_sha=source_sha,
        published_at=_published_at(row.get("published_at")),
        checksum_file=checksum_names[0],
    )


def resolve_dev_batch(
    releases: Sequence[dict[str, object]],
    source_sha: str,
    *,
    apps: Sequence[str] | None = None,
) -> tuple[DevBuild, ...]:
    """Resolve exactly one shape-valid release for every requested app."""
    source_sha = normalize_sha(source_sha)
    ordered_apps = tuple(apps or catalogue_apps())
    enabled = set(ordered_apps)
    matches: dict[str, list[DevBuild]] = {app: [] for app in ordered_apps}
    invalid: list[str] = []
    for row in releases:
        body = str(row.get("body") or "")
        markers = [match.group("sha").lower() for match in SOURCE_MARKER_RE.finditer(body)]
        if source_sha in markers:
            if len(markers) != 1:
                invalid.append(
                    f"{row.get('tag_name') or '<untagged>'}: multiple source SHA markers"
                )
                continue
            try:
                build = _parse_matching_release(row, source_sha, enabled)
            except (TypeError, ValueError) as error:
                invalid.append(f"{row.get('tag_name') or '<untagged>'}: {error}")
                continue
            matches[build.app].append(build)
        elif source_sha in body.lower():
            invalid.append(
                f"{row.get('tag_name') or '<untagged>'}: "
                "source SHA appears without the trusted body marker"
            )

    missing = [app for app in ordered_apps if not matches[app]]
    duplicates = {
        app: sorted(build.tag for build in matches[app])
        for app in ordered_apps
        if len(matches[app]) > 1
    }
    if missing or duplicates or invalid:
        problems = [f"Dev releases for main {source_sha} do not form one complete batch."]
        if missing:
            problems.append(f"missing: {', '.join(missing)}")
        if duplicates:
            details = "; ".join(f"{app} [{', '.join(tags)}]" for app, tags in duplicates.items())
            problems.append(f"duplicates: {details}")
        if invalid:
            problems.append("mismatched releases:")
            problems.extend(f"  - {problem}" for problem in sorted(invalid))
        raise BatchError("\n".join(problems))
    resolved = tuple(matches[app][0] for app in ordered_apps)
    run_ids = {
        match.group("date") + "." + match.group("number")
        for build in resolved
        if (match := DEV_VERSION_RE.fullmatch(build.version)) is not None
    }
    if len(run_ids) != 1:
        shown = "; ".join(
            f"{build.app}={build.version.rsplit('-dev.', 1)[-1]}" for build in resolved
        )
        raise BatchError(f"Dev release run suffixes differ across apps: {shown}")
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sha", required=True, help="the exact 40-character main commit")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run the existing list and promotion checks without writing feeds",
    )
    parser.add_argument(
        "--skip-soak",
        default="",
        metavar="REASON",
        help="record a reason for bypassing the one-day Dev soak",
    )
    parser.add_argument("--report", type=Path, help="write the deterministic Markdown audit")
    return parser


def _promote_args(build: DevBuild, reason: str, *, dry_run: bool) -> list[str]:
    args = [
        "--app",
        build.app,
        "--version",
        build.version,
        "--to",
        "beta",
    ]
    if reason:
        args += ["--skip-soak", reason]
    if dry_run:
        args.append("--dry-run")
    return args


def _publish_args(build: DevBuild, *, dry_run: bool) -> list[str]:
    args = [
        "--app",
        build.app,
        "--version",
        build.version,
        "--channel",
        "dev",
        "--existing",
        "--repo",
        rf.DEV_REPO,
    ]
    if dry_run:
        args.append("--dry-run")
    return args


def _result_channel(feed: ReleaseFeed, build: DevBuild) -> str:
    release = feed.release(build.version)
    if release is None or not release.listed_on("beta"):
        raise BatchError(f"{build.app} {build.version} is not on Beta after promotion")
    return f"beta / {feed.sequence}"


def _audit_report(rows: Sequence[AuditRow], *, dry_run: bool) -> str:
    mode = "dry-run" if dry_run else "real promotion"
    lines = [
        "# Release feed batch audit",
        "",
        f"Mode: {mode}.",
        "",
        (
            "| App | Dev tag / version | Source SHA | SHA-256 file | Check result "
            "| Final channel / sequence |"
        ),
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.app} | `{row.tag}` / `{row.version}` | `{row.source_sha}` | "
            f"`{row.checksum_file}` | {row.result} | {row.final} |"
        )
    return "\n".join(lines) + "\n"


def _write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _pending_rows(builds: Sequence[DevBuild]) -> list[AuditRow]:
    return [
        AuditRow(
            build.app,
            build.tag,
            build.version,
            build.source_sha,
            build.checksum_file,
            "NOT RUN",
            "not changed",
        )
        for build in builds
    ]


def _run_dry_checks(
    builds: Sequence[DevBuild],
    *,
    gh: rf.Gh,
    root: Path,
    moment: datetime,
    reason: str,
    seed_reader: Callable[[Path | None], bytes],
    docs_gate: DocsGate,
    authenticode: publish_release.Authenticode,
    out: Callable[[str], None],
) -> tuple[list[AuditRow], bool]:
    rows: list[AuditRow] = []
    all_passed = True
    for build in builds:
        app_lines: list[str] = []
        listed: list[ReleaseFeed] = []
        publish_code = publish_release.run(
            _publish_args(build, dry_run=True),
            gh=gh,
            root=root,
            now=build.published_at,
            seed_reader=seed_reader,
            out=app_lines.append,
            authenticode=authenticode,
            feed_preview=listed.append,
        )
        final: list[ReleaseFeed] = []
        promote_code = 1
        if publish_code == 0 and len(listed) == 1:
            promote_code = promote_release.run(
                _promote_args(build, reason, dry_run=True),
                gh=gh,
                root=root,
                now=moment,
                seed_reader=seed_reader,
                docs_gate=docs_gate,
                out=app_lines.append,
                authenticode=authenticode,
                feed_override=listed[0],
                feed_preview=final.append,
            )
        for line in app_lines:
            out(f"[{build.app}] {line}")
        passed = publish_code == 0 and promote_code == 0 and len(final) == 1
        all_passed = all_passed and passed
        if passed:
            final_state = f"{_result_channel(final[0], build)} (preview)"
            result = "PASS (dry list + promote checks)"
        else:
            final_state = "not changed"
            result = "FAIL (list/promote checks)"
        rows.append(
            AuditRow(
                build.app,
                build.tag,
                build.version,
                build.source_sha,
                build.checksum_file,
                result,
                final_state,
            )
        )
    return rows, all_passed


def _run_promotions(
    builds: Sequence[DevBuild],
    *,
    gh: rf.Gh,
    root: Path,
    moment: datetime,
    reason: str,
    seed_reader: Callable[[Path | None], bytes],
    docs_gate: DocsGate,
    authenticode: publish_release.Authenticode,
    out: Callable[[str], None],
) -> tuple[list[AuditRow], bool]:
    rows = _pending_rows(builds)
    for index, build in enumerate(builds):
        app_lines: list[str] = []
        publish_code = publish_release.run(
            _publish_args(build, dry_run=False),
            gh=gh,
            root=root,
            now=build.published_at,
            seed_reader=seed_reader,
            out=app_lines.append,
            authenticode=authenticode,
        )
        promote_code = 1
        final_feed: ReleaseFeed | None = None
        if publish_code == 0:
            promote_code = promote_release.run(
                _promote_args(build, reason, dry_run=False),
                gh=gh,
                root=root,
                now=moment,
                seed_reader=seed_reader,
                docs_gate=docs_gate,
                out=app_lines.append,
                authenticode=authenticode,
            )
            if promote_code == 0:
                final_feed = rf.load_feed(build.app, root)
        for line in app_lines:
            out(f"[{build.app}] {line}")
        if publish_code == 0 and promote_code == 0 and final_feed is not None:
            rows[index] = AuditRow(
                build.app,
                build.tag,
                build.version,
                build.source_sha,
                build.checksum_file,
                "PASS (listed + promoted)",
                _result_channel(final_feed, build),
            )
            continue
        rows[index] = AuditRow(
            build.app,
            build.tag,
            build.version,
            build.source_sha,
            build.checksum_file,
            "FAIL (batch stopped)",
            "not promoted",
        )
        return rows, False
    return rows, True


def run(
    argv: list[str] | None = None,
    *,
    gh: rf.Gh = rf.gh_cli,
    root: Path = REPO_ROOT,
    now: datetime | None = None,
    sha_verifier: ShaVerifier = verify_main_sha,
    seed_reader: Callable[[Path | None], bytes] = rf.read_seed,
    docs_gate: DocsGate = promote_release._docs_gate,
    out: Callable[[str], None] = print,
    authenticode: publish_release.Authenticode = publish_release._asset_is_signed,
) -> int:
    args = build_parser().parse_args(argv)
    source_sha = normalize_sha(args.sha)
    reason = validate_skip_soak(args.skip_soak)
    moment = now or datetime.now(UTC)
    if args.report is not None:
        args.report = Path(args.report)
    try:
        sha_verifier(source_sha, root)
        builds = resolve_dev_batch(fetch_dev_releases(gh), source_sha)
        if any(build.published_at > moment for build in builds):
            future = [build.tag for build in builds if build.published_at > moment]
            raise BatchError(f"Dev releases are published in the future: {', '.join(future)}")
    except BatchError as error:
        if args.report is not None:
            _write_report(
                args.report,
                "# Release feed batch audit\n\nResolution failed:\n\n"
                + "\n".join(f"- {line}" for line in str(error).splitlines())
                + "\n",
            )
        raise

    docs_result: bool | None = None

    def docs_once() -> bool:
        nonlocal docs_result
        if docs_result is None:
            docs_result = docs_gate()
        return docs_result

    if args.dry_run:
        rows, passed = _run_dry_checks(
            builds,
            gh=gh,
            root=root,
            moment=moment,
            reason=reason,
            seed_reader=seed_reader,
            docs_gate=docs_once,
            authenticode=authenticode,
            out=out,
        )
    else:
        rows, passed = _run_promotions(
            builds,
            gh=gh,
            root=root,
            moment=moment,
            reason=reason,
            seed_reader=seed_reader,
            docs_gate=docs_once,
            authenticode=authenticode,
            out=out,
        )
    report = _audit_report(rows, dry_run=args.dry_run)
    if args.report is not None:
        _write_report(args.report, report)
    out(report.rstrip())
    return 0 if passed else 1


def main() -> int:
    try:
        return run()
    except BatchError as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
