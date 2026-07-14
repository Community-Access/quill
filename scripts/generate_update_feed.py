from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Allow this script to import from the quill package when run directly
# (e.g. ``python scripts/generate_update_feed.py``) without a prior
# ``pip install -e .``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quill.branding import APP_DISPLAY_NAME
from quill.core.updates import manifest_signature


def _resolve_version(source_root: Path) -> str:
    """Read the display version from build/version.toml (0.7.0+ source of truth).

    Falls back to ``quill/__init__.py`` for pre-0.7.0 checkouts where the
    toml is absent. Returns the same display version string the About
    dialog and InnoSetup installer emit, so the running build, the
    installer, and the update manifest can never disagree.
    """
    import tomllib

    toml_path = source_root / "build" / "version.toml"
    if toml_path.exists():
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        base = str(data.get("base_version", "")).strip()
        channel = str(data.get("channel", "stable")).strip().lower()
        pre = int(data.get("prerelease_number", 0))
        if channel == "stable":
            return base
        if channel == "alpha":
            return f"{base} Alpha {pre}"
        if channel == "beta":
            return f"{base} Beta {pre}"
        if channel == "rc":
            return f"{base} Release Candidate {pre}"
        return f"{base} Dev"
    import re

    init_py = source_root / "quill" / "__init__.py"
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_py.read_text(), re.M)
    return match.group(1) if match else "unknown"


def _resolve_product_name(source_root: Path) -> str:
    """Read the user-visible product name from build/version.toml."""
    import tomllib

    toml_path = source_root / "build" / "version.toml"
    if toml_path.exists():
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        name = str(data.get("product_name", "")).strip()
        if name:
            return name
    return APP_DISPLAY_NAME


def _installer_filename(display_version: str) -> str:
    """The actual installer filename the build script emits for ``display_version``.

    Mirrors ``OutputBaseFilename=...`` in ``installer/quill.iss``. Keep in
    sync with :func:`scripts.build_windows_distribution.build_inno_setup_script`.
    """
    return f"Quill-for-All-Setup-{display_version}.exe"


def _github_release_asset_name(installer_name: str) -> str:
    """Return the asset name as GitHub's release-asset CDN serves it.

    GitHub's release asset URLs normalise the filename: any character that
    is unsafe in a URL path (most commonly the space in ``"0.7.0 Beta 1"``)
    is rewritten to a dot. The Inno Setup step keeps the space in the
    on-disk filename, but the URL the running build hits must match what
    GitHub serves, not what Inno Setup wrote.
    """
    return installer_name.replace(" ", ".")


def _default_published_at() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_payload(
    *,
    version: str | None = None,
    download_url: str | None = None,
    notes: str = "",
    published_at: str | None = None,
    source_root: Path = Path("."),
    tag: str = "latest",
    advisories: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Return the signed manifest dict the publisher writes to disk.

    ``version`` and ``download_url`` default to values derived from
    ``build/version.toml`` and the installer's actual filename so the
    feed never drifts from the artifact the running build compares
    against. ``advisories`` (optional) are the remote feature kill switches;
    they are covered by the signature so a client can trust them.
    """
    resolved_version = (version or _resolve_version(source_root)).strip()
    installer_name = _installer_filename(resolved_version)
    asset_name = _github_release_asset_name(installer_name)
    resolved_url = (
        download_url.strip()
        if download_url
        else f"https://github.com/Community-Access/quill/releases/download/{tag}/{asset_name}"
    )
    payload: dict[str, object] = {
        "version": resolved_version,
        "download_url": resolved_url,
        "published_at": (published_at or _default_published_at()).strip(),
        "notes": notes.strip(),
    }
    if advisories:
        payload["advisories"] = advisories
    payload["signature"] = _signature_for(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a signed Quill update feed file.")
    parser.add_argument(
        "--version",
        help=(
            "Release version. If omitted, the script reads it from "
            "build/version.toml (preferred) so the feed always agrees with "
            "the installer and the About dialog."
        ),
    )
    parser.add_argument(
        "--download-url",
        help=(
            "URL users should open to download the installer. If omitted "
            "the script derives it from the product name, version, and "
            "--tag so it matches the file the InnoSetup step produces."
        ),
    )
    parser.add_argument("--notes", default="", help="Short release notes shown in update prompt")
    parser.add_argument(
        "--published-at",
        default=None,
        help="ISO-8601 release time (UTC). Defaults to the current time.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs") / "site" / "updates" / ".quill-update-feed-v1.json",
        help="Target feed file path",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("."),
        help="Repository root that contains build/version.toml and quill/.",
    )
    parser.add_argument(
        "--tag",
        default="latest",
        help=(
            "GitHub release tag used to derive --download-url when it is "
            "not supplied (default: 'latest', producing a /latest/ URL)."
        ),
    )
    parser.add_argument(
        "--lock-feature",
        action="append",
        default=[],
        metavar="FEATURE_ID",
        help=(
            "Remotely disable this feature id (a kill switch). Repeatable. See "
            "quill/core/feature_command_map.py for ids. Signed into the feed."
        ),
    )
    parser.add_argument(
        "--lock-reason",
        default="",
        help="Spoken reason shown to users for the --lock-feature advisories.",
    )
    parser.add_argument(
        "--lock-min-version",
        default="",
        help="Only lock builds at or above this version (empty = no lower bound).",
    )
    parser.add_argument(
        "--lock-max-version",
        default="",
        help="Only lock builds at or below this version (empty = all; how a fix lifts it).",
    )
    args = parser.parse_args()

    # Validate every --lock-feature against the real feature catalog before
    # signing: a typo'd id would sign, publish, and verify fine but silently
    # lock nothing — the dangerous failure for a valve reached for under
    # pressure. Hard-fail with the nearest suggestions instead.
    unknown = _unknown_feature_ids(args.lock_feature)
    if unknown:
        for feature_id, suggestions in unknown.items():
            hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
            print(f"ERROR: unknown --lock-feature id {feature_id!r}.{hint}", file=sys.stderr)
        return 2

    advisories = [
        {
            "feature_id": feature_id,
            "reason": args.lock_reason,
            "min_version": args.lock_min_version,
            "max_version": args.lock_max_version,
            "advisory_id": f"lock-{feature_id}",
        }
        for feature_id in args.lock_feature
    ]

    payload = build_payload(
        version=args.version,
        download_url=args.download_url,
        notes=args.notes,
        published_at=args.published_at,
        source_root=args.source_root,
        tag=args.tag,
        advisories=advisories,
    )
    product_name = _resolve_product_name(args.source_root)
    installer_name = _installer_filename(str(payload["version"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lock_line = (
        f"\n  LOCKS:     {', '.join(args.lock_feature)} (reason: {args.lock_reason or 'none'})"
        if args.lock_feature
        else ""
    )
    print(
        f"Wrote signed update feed to {args.output}\n"
        f"  product:   {product_name}\n"
        f"  version:   {payload['version']}\n"
        f"  installer: {installer_name}\n"
        f"  url:       {payload['download_url']}"
        f"{lock_line}"
    )
    return 0


def _unknown_feature_ids(feature_ids: list[str]) -> dict[str, list[str]]:
    """Map each unknown --lock-feature id to up to 3 nearest known ids.

    An id is "known" when it exists in the feature catalog (the same set the
    client resolves locks against). Empty result = all ids are valid.
    """
    import difflib

    from quill.core.features import FEATURE_DEFINITIONS

    known = set(FEATURE_DEFINITIONS)
    known_sorted = sorted(known)  # deterministic suggestion order
    out: dict[str, list[str]] = {}
    for feature_id in feature_ids:
        if feature_id not in known:
            out[feature_id] = difflib.get_close_matches(feature_id, known_sorted, n=3, cutoff=0.5)
    return out


def _signature_for(payload: dict[str, object]) -> str:
    """Sign the manifest via quill.core.updates so the client can verify it.

    Delegates to the shared :func:`quill.core.updates.manifest_signature` (the
    single source of truth) using the deployment key from
    ``QUILL_UPDATE_MANIFEST_KEY`` when set (HMAC), otherwise the salt-only
    baseline. Because the client verifier reads the same env var and uses the
    same function, the feed this writes always verifies.
    """
    from quill.core.updates import FeatureAdvisory

    # Narrow to a list of dicts instead of a blanket type-ignore: signing an
    # unexpected advisories shape should drop the bad entries, not crash or
    # silently sign garbage (#809 review).
    raw_advisories = payload.get("advisories", [])
    advisory_dicts = (
        [entry for entry in raw_advisories if isinstance(entry, dict)]
        if isinstance(raw_advisories, list)
        else []
    )
    advisories = tuple(
        FeatureAdvisory(
            feature_id=str(a.get("feature_id", "")),
            reason=str(a.get("reason", "")),
            min_version=str(a.get("min_version", "")),
            max_version=str(a.get("max_version", "")),
            advisory_id=str(a.get("advisory_id", "")),
        )
        for a in advisory_dicts
    )
    return manifest_signature(
        version=str(payload["version"]),
        download_url=str(payload["download_url"]),
        published_at=str(payload["published_at"]),
        notes=str(payload["notes"]),
        key=os.getenv("QUILL_UPDATE_MANIFEST_KEY", "").strip() or None,
        advisories=advisories,
    )


if __name__ == "__main__":
    raise SystemExit(main())
