"""Prepare a local WinGet manifest draft from a published Quill Stable release.

Examples::

    python -m scripts.winget.prepare --tag quill-radio-v3.0.4 --dry-run
    python -m scripts.winget.prepare --tag quill-radio-v3.0.4

This command only reads the public release API and writes into the selected
local draft folder. It never opens a public pull request.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from quill.core.release_tags import parse_release_tag
from scripts.winget.manifests import (
    WINGET_ROOT,
    build_manifest_draft,
    load_catalog,
    validate_templates,
    write_manifest_draft,
)

API_RELEASE = "https://api.github.com/repos/Community-Access/quill/releases/tags/{}"


def fetch_release(tag: str) -> dict[str, object]:
    url = API_RELEASE.format(quote(tag, safe=""))
    request = Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Quill-WinGet-Manifest"},
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed GitHub API host
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("GitHub did not return a release record.")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True, help="Exact published GitHub release tag.")
    parser.add_argument(
        "--output",
        type=Path,
        default=WINGET_ROOT / "drafts",
        help="Local output folder for the mirrored manifest set.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the set without writing files."
    )
    args = parser.parse_args(argv)

    try:
        validate_templates()
        parsed = parse_release_tag(args.tag)
        if parsed is None:
            raise ValueError(f"{args.tag!r} is not a QuillVille release tag.")
        release = fetch_release(args.tag)
        catalog = load_catalog()
        draft = build_manifest_draft(release, parsed.app_key, catalog=catalog)
        print(f"Package: {draft.package_id} {draft.package_version}")
        print(f"Release: {draft.release_url}")
        print(f"Installer: {draft.asset_name}")
        print(f"SHA-256: {draft.asset_sha256}")
        if args.dry_run:
            for relative, content in sorted(draft.files.items()):
                print(f"\n--- {relative} ---\n{content}", end="")
            return 0
        written = write_manifest_draft(draft, args.output)
        for path in written:
            print(f"Wrote {path}")
        folder = written[0].parent
        print(f"Validate with: winget validate --manifest {folder}")
        print("No public pull request was created.")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"Could not prepare the WinGet draft: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
