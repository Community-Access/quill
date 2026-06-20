from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

_SIGNATURE_SALT = "quill-manifest-signature-v1"


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
    return "QUILL for All"


def _installer_filename(display_version: str) -> str:
    """The actual installer filename the build script emits for ``display_version``.

    Mirrors ``OutputBaseFilename=...`` in ``installer/quill.iss``. Keep in
    sync with :func:`scripts.build_windows_distribution.build_inno_setup_script`.
    """
    return f"Quill-for-All-Setup-{display_version}.exe"


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
) -> dict[str, str]:
    """Return the signed manifest dict the publisher writes to disk.

    ``version`` and ``download_url`` default to values derived from
    ``build/version.toml`` and the installer's actual filename so the
    feed never drifts from the artifact the running build compares
    against.
    """
    resolved_version = (version or _resolve_version(source_root)).strip()
    installer_name = _installer_filename(resolved_version)
    resolved_url = (
        download_url.strip()
        if download_url
        else f"https://github.com/Community-Access/quill/releases/download/{tag}/{installer_name}"
    )
    payload: dict[str, str] = {
        "version": resolved_version,
        "download_url": resolved_url,
        "published_at": (published_at or _default_published_at()).strip(),
        "notes": notes.strip(),
    }
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
    args = parser.parse_args()

    payload = build_payload(
        version=args.version,
        download_url=args.download_url,
        notes=args.notes,
        published_at=args.published_at,
        source_root=args.source_root,
        tag=args.tag,
    )
    product_name = _resolve_product_name(args.source_root)
    installer_name = _installer_filename(payload["version"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote signed update feed to {args.output}\n"
        f"  product:   {product_name}\n"
        f"  version:   {payload['version']}\n"
        f"  installer: {installer_name}\n"
        f"  url:       {payload['download_url']}"
    )
    return 0


def _signature_for(payload: dict[str, str]) -> str:
    canonical = json.dumps(
        {
            "download_url": payload["download_url"],
            "notes": payload["notes"],
            "published_at": payload["published_at"],
            "version": payload["version"],
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(f"{canonical}|{_SIGNATURE_SALT}".encode()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
