"""Create the signed v2 feed for every channel-enabled QuillVille product.

The first rollout is a migration, not a new release. Existing GitHub release
objects are inventoried through the API, their published SHA-256 digests become
feed assets, and products with no public release yet receive a valid empty feed.
Future releases are still added by ``publish_release.py`` and
``promote_release.py``; this script refuses to overwrite an existing v2 feed.

The signing seed is supplied by a protected GitHub Actions environment or a
local key file. It is read by :func:`quill.tools.release_feed.read_seed`,
never printed, and never accepted from a command-line argument value.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quill.core.release_catalog import BY_KEY, PRODUCTS  # noqa: E402
from quill.core.updater.feed import FeedAsset, FeedRelease  # noqa: E402
from quill.core.updater.feed_publish import new_feed, refresh  # noqa: E402
from quill.core.versioning import ReleaseVersion, sort_key  # noqa: E402
from quill.tools import release_feed as rf  # noqa: E402


def _release_rows(gh: rf.Gh, repo: str) -> list[dict[str, Any]]:
    raw = json.loads(gh(["api", f"repos/{repo}/releases?per_page=100"]) or "[]")
    return [item for item in raw if isinstance(item, dict) and not item.get("draft")]


def _channel(version: str, *, prerelease: bool) -> str:
    if not prerelease:
        return "stable"
    parsed = ReleaseVersion.try_parse(version)
    return "dev" if parsed is not None and parsed.stage == "dev" else "beta"


def _canonical_assets(item: dict[str, Any], app_key: str) -> tuple[FeedAsset, ...]:
    product = BY_KEY[app_key]
    prefixes = {product.asset_prefix.casefold(), product.lookup_asset_prefix.casefold()}
    by_kind: dict[str, FeedAsset] = {}
    raw_assets = item.get("assets") or []
    for raw in raw_assets if isinstance(raw_assets, list) else []:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "")
        lower = name.casefold()
        kind = rf.asset_kind(name)
        if not kind or not any(lower.startswith(prefix) for prefix in prefixes):
            continue
        if "offline" in lower:
            continue
        digest = str(raw.get("digest") or "")
        if not digest.startswith("sha256:") or len(digest.removeprefix("sha256:")) != 64:
            raise SystemExit(f"{app_key}: {name} has no SHA-256 digest in the GitHub API")
        url = str(raw.get("browser_download_url") or "")
        try:
            size = int(raw.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if not url.startswith("https://") or size <= 0:
            raise SystemExit(f"{app_key}: {name} has no usable download URL or size")
        candidate = FeedAsset(
            kind=kind,
            name=name,
            url=url,
            size=size,
            sha256=digest.removeprefix("sha256:"),
        )
        old = by_kind.get(kind)
        if old is None or name.casefold() < old.name.casefold():
            by_kind[kind] = candidate
    return tuple(
        by_kind[kind] for kind in ("installer", "portable", "build-info") if kind in by_kind
    )


def _feed_release(item: dict[str, Any], app_key: str, version: str) -> FeedRelease:
    stamp = str(item.get("published_at") or item.get("created_at") or "")
    channel = _channel(version, prerelease=bool(item.get("prerelease")))
    assets = _canonical_assets(item, app_key)
    if not any(asset.kind in ("installer", "portable") for asset in assets):
        raise SystemExit(
            f"{app_key}: {item.get('tag_name')} has no matching installer or portable asset"
        )
    return FeedRelease(
        version=version,
        tag=str(item.get("tag_name") or ""),
        channels=(channel,),
        assets=assets,
        history=({"channel": channel, "at": stamp, "by": "bootstrap_release_feeds.py"},),
        published_at=stamp,
        notes_url=str(item.get("html_url") or ""),
        notes_summary=str(item.get("body") or "")[:4000],
    )


def plan(rows: Sequence[dict[str, Any]]) -> dict[str, tuple[FeedRelease, ...]]:
    grouped: dict[str, dict[str, tuple[str, dict[str, Any]]]] = {}
    for item in rows:
        tag = str(item.get("tag_name") or "")
        found = rf.app_for_tag(tag)
        if found is None or found[0] not in {p.key for p in PRODUCTS if p.channels_enabled}:
            continue
        app_key, version = found
        if ReleaseVersion.try_parse(version) is None:
            continue
        if not any(
            asset.kind in ("installer", "portable") for asset in _canonical_assets(item, app_key)
        ):
            continue
        channel = _channel(version, prerelease=bool(item.get("prerelease")))
        current = grouped.setdefault(app_key, {}).get(channel)
        if current is None or sort_key(version) > sort_key(current[0]):
            grouped[app_key][channel] = (version, item)
    result: dict[str, tuple[FeedRelease, ...]] = {}
    for product in PRODUCTS:
        if not product.channels_enabled:
            continue
        releases = [
            _feed_release(item, product.key, version)
            for version, item in grouped.get(product.key, {}).values()
        ]
        result[product.key] = tuple(
            sorted(releases, key=lambda r: sort_key(r.version), reverse=True)
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=rf.MAIN_REPO)
    parser.add_argument(
        "--app",
        default="all",
        help="one catalogue key, or all (default)",
    )
    parser.add_argument("--key-file", type=Path)
    parser.add_argument(
        "--refresh-all",
        action="store_true",
        help="also re-sign existing feeds with a fresh sequence and expiry",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def run(
    argv: list[str] | None = None,
    *,
    root: Path = REPO_ROOT,
    now: datetime | None = None,
    gh: rf.Gh = rf.gh_cli,
    seed_reader: Callable[[Path | None], bytes] = rf.read_seed,
    out: Callable[[str], None] = print,
) -> int:
    args = build_parser().parse_args(argv)
    active = [product.key for product in PRODUCTS if product.channels_enabled]
    selected = active if args.app == "all" else [args.app]
    unknown = sorted(set(selected) - set(active))
    if unknown:
        out("Unknown or held app(s): " + ", ".join(unknown))
        return 2
    rows = _release_rows(gh, args.repo)
    migration = plan(rows)
    seed = None if args.dry_run else seed_reader(args.key_file)
    moment = now or datetime.now(UTC)
    changed: list[str] = []
    for app_key in selected:
        path = rf.feed_dir(root) / f"{app_key}.json"
        if path.is_file():
            if not args.refresh_all:
                out(f"{app_key}: feed exists; left unchanged")
                continue
            feed = refresh(rf.load_feed(app_key, root), moment)
            action = "refresh"
        else:
            feed = refresh(
                replace(
                    new_feed(app_key, rf.app(app_key).name),
                    releases=migration[app_key],
                ),
                moment,
            )
            action = "create"
        if args.dry_run:
            out(f"{app_key}: would {action} {len(feed.releases)} release(s) and re-sign the feed")
            continue
        written = rf.write_feed(feed, seed=seed, root=root)
        if not rf.feed_signature_ok(written):
            raise SystemExit(
                f"{app_key}: the Actions secret did not match the bundled feed public key"
            )
        changed.append(app_key)
        out(f"{app_key}: signed feed with {len(feed.releases)} release(s)")
    if args.dry_run or not changed:
        return 0
    index = rf.feed_dir(root) / "index.json"
    if not rf.index_signature_ok(index):
        raise SystemExit("The signed release index did not verify")
    out(f"Signed release index for {len(rf.all_feeds(root))} product feeds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
