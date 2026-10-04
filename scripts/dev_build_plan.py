"""Decide whether today's Dev build runs, and with which versions (dev-builds.yml).

At most once a day, and only when ``main`` has changed since the last Dev
build. Prints ``build=true|false``, ``reason=...``, and one
``version_<app>=...`` line per app, in the ``$GITHUB_OUTPUT`` format::

    python scripts/dev_build_plan.py --sha "$GITHUB_SHA" >> "$GITHUB_OUTPUT"

Reads the dev-builds repository's releases with ``gh`` (``GH_TOKEN`` must be
able to read it) and the published Stable and Beta tags from the checkout.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quill.tools import release_feed as rf  # noqa: E402


def _tags() -> list[str]:
    result = subprocess.run(
        ["git", "tag", "--list"], check=False, capture_output=True, text=True, cwd=REPO_ROOT
    )
    return result.stdout.split()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sha", required=True)
    parser.add_argument("--repo", default=rf.DEV_REPO)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        raw = json.loads(rf.gh_cli(["api", f"repos/{args.repo}/releases?per_page=100"]) or "[]")
    except (subprocess.CalledProcessError, OSError, ValueError):
        raw = []
    published: dict[str, list[str]] = {key: [] for key in rf.APPS}
    for tag in _tags():
        found = rf.app_for_tag(tag)
        if found:
            published[found[0]].append(found[1])
    plan = rf.dev_build_plan(
        head_sha=args.sha,
        dev_releases=[r for r in raw if isinstance(r, dict)],
        today=datetime.now(UTC).strftime("%Y%m%d"),
        sources={key: rf.source_version(key) for key in rf.APPS},
        published=published,
        force=args.force,
    )
    print(f"build={'true' if plan.build else 'false'}")
    print(f"reason={plan.reason}")
    for key, version in plan.versions.items():
        print(f"version_{key}={version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
