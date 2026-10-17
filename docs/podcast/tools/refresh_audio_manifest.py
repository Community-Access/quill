#!/usr/bin/env python3
"""Refresh docs/podcast/audio_assets.json from the podcast-v1 release.

The manifest is the site's only record of which QUILL Cast audio really
exists. ``build_feed.py`` links an episode's MP3, and gives it a feed item,
only when the manifest marks it ``published``; the site links gate
(``tests/unit/docs/test_site_links.py``) fails on any podcast audio link the
manifest does not vouch for.

This script is read-only towards GitHub: it runs ``gh release view`` and never
uploads, edits or deletes anything. For each episode in ``episodes.json`` it
derives the asset name the way ``build_feed.py`` does and records one of:

* ``published`` -- the asset exists and was uploaded after the episode's
  script last changed in git, so the recording matches the transcript.
* ``stale`` -- an asset with that exact name exists, but it was uploaded
  before the script's last commit. The 2026-07-02 upload of the old
  36-episode series left four of these (ep01 to ep04 kept their names while
  their scripts grew from about 600 words to about 4,000).
* ``missing`` -- no asset with that name.

Commit a script change *before* uploading its audio, or the fresh upload is
older than the commit and reads as stale.

Usage::

    python docs/podcast/tools/refresh_audio_manifest.py
    python docs/podcast/tools/refresh_audio_manifest.py --check   # exit 1 on drift
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_feed import AUDIO_MANIFEST, PODCAST_ROOT, REPO_ROOT, audio_file_name  # noqa: E402

RELEASE_TAG = "podcast-v1"
REPOSITORY = "Community-Access/quill"


def _release_assets() -> list[dict[str, object]]:
    """Name, size and upload time of every asset on the release (read-only)."""
    completed = subprocess.run(
        ["gh", "release", "view", RELEASE_TAG, "--repo", REPOSITORY, "--json", "assets"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assets = json.loads(completed.stdout)["assets"]
    return sorted(
        (
            {
                "name": str(asset["name"]),
                "size": int(asset["size"]),
                "uploaded_at": str(asset.get("updatedAt") or asset.get("createdAt") or ""),
            }
            for asset in assets
        ),
        key=lambda asset: str(asset["name"]),
    )


def _script_last_changed(slug: str) -> str:
    """ISO time of the last commit that touched the episode's script, or ''."""
    script = (PODCAST_ROOT / "scripts" / f"{slug}.txt").relative_to(REPO_ROOT)
    completed = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", script.as_posix()],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
    )
    return completed.stdout.strip()


def _moment(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def build_manifest(assets: list[dict[str, object]], read_on: str) -> dict[str, object]:
    meta = json.loads((PODCAST_ROOT / "episodes.json").read_text(encoding="utf-8"))
    by_name = {str(asset["name"]): asset for asset in assets}
    episodes: list[dict[str, object]] = []
    for episode in meta["episodes"]:
        slug = episode["slug"]
        name = audio_file_name(slug)
        entry: dict[str, object] = {"slug": slug, "file": name}
        asset = by_name.get(name)
        if asset is None:
            entry["status"] = "missing"
        else:
            uploaded = str(asset["uploaded_at"])
            changed = _script_last_changed(slug)
            if changed and uploaded and _moment(uploaded) < _moment(changed):
                entry["status"] = "stale"
                entry["uploaded_at"] = uploaded
                entry["script_changed_at"] = changed
            else:
                entry["status"] = "published"
        episodes.append(entry)
    return {
        "_about": (
            "Audio that really exists on the podcast-v1 release, and which episode "
            "each file serves. Written by docs/podcast/tools/refresh_audio_manifest.py; "
            "do not edit by hand. build_feed.py links only 'published' episodes."
        ),
        "release": RELEASE_TAG,
        "repository": REPOSITORY,
        "read_on": read_on,
        "assets": assets,
        "episodes": episodes,
    }


def _render(manifest: dict[str, object]) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if the committed manifest differs (ignoring read_on)",
    )
    args = parser.parse_args(argv)

    manifest = build_manifest(_release_assets(), date.today().isoformat())
    counts: dict[str, int] = {}
    for entry in manifest["episodes"]:  # type: ignore[union-attr]
        counts[str(entry["status"])] = counts.get(str(entry["status"]), 0) + 1
    summary = ", ".join(f"{count} {status}" for status, count in sorted(counts.items()))
    print(f"{len(manifest['assets'])} assets on {RELEASE_TAG}; episodes: {summary}")  # type: ignore[arg-type]

    if args.check:
        committed = (
            json.loads(AUDIO_MANIFEST.read_text(encoding="utf-8"))
            if AUDIO_MANIFEST.exists()
            else {}
        )
        committed.pop("read_on", None)
        fresh = dict(manifest)
        fresh.pop("read_on", None)
        if committed != fresh:
            print(f"{AUDIO_MANIFEST.name} is out of date; run without --check to refresh it.")
            return 1
        return 0

    AUDIO_MANIFEST.write_text(_render(manifest), encoding="utf-8", newline="\n")
    print(f"Wrote {AUDIO_MANIFEST.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
