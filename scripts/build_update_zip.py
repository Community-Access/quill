"""Build a delta or full update ZIP for the Quill autoupdate pipeline.

The produced ZIP is consumed by ``quill/_vendor/autoupdate/autoupdate.py``.
Its bootstrapper entry-point (``bootstrap.exe`` / ``bootstrap-{platform}.sh``)
must be at the ZIP root so the autoupdate library can locate it after
extraction.

Usage::

    python scripts/build_update_zip.py --version 0.5.0
    python scripts/build_update_zip.py --version 0.5.0 --mode full
    python scripts/build_update_zip.py \\
        --version 0.5.0 --mode delta --base-version 0.4.0 --platform windows
"""

from __future__ import annotations

import argparse
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from scripts.generate_file_manifest import scan_files

_PLATFORM_BOOTSTRAPPER: dict[str, str] = {
    "windows": "bootstrap.exe",
    "macos": "bootstrap-mac.sh",
    "linux": "bootstrap-lin.sh",
}

_DEFAULT_BOOTSTRAPPER_DIR = Path("quill/_vendor/autoupdate/bootstrappers")
_MANIFEST_DIR = Path("docs/site/updates/manifests")


def _find_latest_base_version(current_version: str, manifest_dir: Path) -> str | None:
    """Return highest version < current_version from available manifests (no packaging dep)."""
    current_parts = tuple(int(x) for x in current_version.split("."))
    best: tuple[int, ...] | None = None
    best_str: str | None = None
    for p in manifest_dir.glob("manifest-*.json"):
        stem = p.stem
        ver_str = stem[len("manifest-") :]
        try:
            parts = tuple(int(x) for x in ver_str.split("."))
        except ValueError:
            continue
        if parts < current_parts:
            if best is None or parts > best:
                best = parts
                best_str = ver_str
    return best_str


def load_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_update_zip(
    *,
    version: str,
    mode: str,
    base_version: str | None,
    platform: str,
    bootstrapper_dir: Path,
    source_root: Path,
    output: Path,
    install_prefix: str,
    manifest_dir: Path,
) -> int:
    bootstrapper_name = _PLATFORM_BOOTSTRAPPER[platform]
    bootstrapper_path = bootstrapper_dir / bootstrapper_name

    if not bootstrapper_path.exists():
        print(
            f"ERROR: bootstrapper not found at {bootstrapper_path}. "
            "Run scripts/fetch_bootstrappers.py first."
        )
        return 1

    # --- resolve base version for delta -----------------------------------------
    resolved_base: str | None = base_version
    if mode == "delta" and resolved_base is None:
        resolved_base = _find_latest_base_version(version, manifest_dir)
        if resolved_base is None:
            print("No previous manifest found; falling back to full mode.")
            mode = "full"
        else:
            print(f"Auto-detected base version: {resolved_base}")

    base_manifest: dict[str, object] | None = None
    if mode == "delta" and resolved_base is not None:
        base_manifest_path = manifest_dir / f"manifest-{resolved_base}.json"
        if not base_manifest_path.exists():
            print(f"ERROR: base manifest not found at {base_manifest_path}")
            return 1
        base_manifest = load_manifest(base_manifest_path)

    # --- hash all current distributable files ------------------------------------
    entries = scan_files(source_root, install_prefix)
    current_hashes: dict[str, str] = {str(e["path"]): str(e["sha256"]) for e in entries}

    # --- determine which files to include ----------------------------------------
    old_hashes: dict[str, str] = {}
    if base_manifest is not None:
        old_hashes = {
            str(f["path"]): str(f["sha256"])  # type: ignore[index]
            for f in base_manifest.get("files", [])  # type: ignore[union-attr]
        }

    files_to_include: list[dict[str, object]] = []
    deleted_paths: list[str] = []

    if mode == "full":
        files_to_include = list(entries)
    else:
        for entry in entries:
            path_key = str(entry["path"])
            if path_key not in old_hashes or old_hashes[path_key] != entry["sha256"]:
                files_to_include.append(entry)
        # Detect deletions
        current_path_set = set(current_hashes.keys())
        for old_path in old_hashes:
            if old_path not in current_path_set:
                deleted_paths.append(old_path)

    # --- build UPDATE_MANIFEST.json ----------------------------------------------
    update_manifest = {
        "version": version,
        "base_version": resolved_base,
        "mode": mode,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "platform": platform,
        "file_count": len(files_to_include),
        "files": [
            {
                "install_path": str(f["install_path"]),
                "action": "update",
                "sha256": str(f["sha256"]),
            }
            for f in files_to_include
        ],
        "deleted": [install_prefix.rstrip("/") + "/" + p for p in deleted_paths],
    }

    # --- write ZIP ---------------------------------------------------------------
    output.parent.mkdir(parents=True, exist_ok=True)

    if not files_to_include:
        print("No changed files detected; ZIP will contain only the bootstrapper.")

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # bootstrapper always at ZIP root
        zf.write(bootstrapper_path, bootstrapper_name)

        # UPDATE_MANIFEST.json at ZIP root
        zf.writestr("UPDATE_MANIFEST.json", json.dumps(update_manifest, indent=2) + "\n")

        for entry in files_to_include:
            rel_path = source_root / str(entry["path"])
            archive_path = str(entry["install_path"])
            zf.write(rel_path, archive_path)

    zip_size = output.stat().st_size
    total_distributable_size = sum(int(e["size"]) for e in entries)  # type: ignore[arg-type]

    print(f"Built {mode} update ZIP: {output}")
    print(f"  Platform:      {platform}")
    print(f"  Files included: {len(files_to_include)}")
    print(f"  Deleted (logged only): {len(deleted_paths)}")
    print(f"  ZIP size:      {zip_size:,} bytes")
    if mode == "delta":
        savings = total_distributable_size - zip_size
        print(f"  vs full estimate: {savings:+,} bytes savings")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a delta or full update ZIP for the Quill autoupdate pipeline."
    )
    parser.add_argument("--version", required=True, help="Release version (e.g. 0.5.0)")
    parser.add_argument(
        "--mode",
        choices=["full", "delta"],
        default=None,
        help="full or delta (default: delta if a previous manifest exists, else full)",
    )
    parser.add_argument(
        "--base-version",
        default=None,
        help="Base version for delta mode (auto-detected from available manifests if omitted)",
    )
    parser.add_argument(
        "--platform",
        choices=list(_PLATFORM_BOOTSTRAPPER.keys()),
        default="windows",
        help="Target platform (default: windows)",
    )
    parser.add_argument(
        "--bootstrapper-dir",
        type=Path,
        default=_DEFAULT_BOOTSTRAPPER_DIR,
        help="Directory containing bootstrapper binaries",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("."),
        help="Repository root directory (default: current directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output ZIP path (default: release-artifacts/quill-{version}-update-{platform}.zip)",
    )
    parser.add_argument(
        "--install-prefix",
        default="python/Lib/site-packages",
        help="Install prefix for file entries within the ZIP",
    )
    args = parser.parse_args()

    version: str = args.version.strip()
    platform: str = args.platform
    source_root: Path = args.source_root.resolve()
    manifest_dir = source_root / _MANIFEST_DIR

    output: Path = args.output or (
        source_root / "release-artifacts" / f"quill-{version}-update-{platform}.zip"
    )

    # Determine mode: default to delta if a previous manifest can be found, else full
    mode = args.mode
    if mode is None:
        probe = _find_latest_base_version(version, manifest_dir)
        mode = "delta" if probe is not None else "full"

    return build_update_zip(
        version=version,
        mode=mode,
        base_version=args.base_version,
        platform=platform,
        bootstrapper_dir=args.bootstrapper_dir,
        source_root=source_root,
        output=output,
        install_prefix=args.install_prefix,
        manifest_dir=manifest_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
