"""Generate a SHA-256 file manifest for distributable Quill files.

The manifest records every file under ``quill/`` that ships in the portable
distribution (excluding ``quill/tools/``, ``__pycache__``, ``*.pyc``,
``*.pyo``).  It is consumed by ``scripts/build_update_zip.py`` to produce
delta update ZIPs.

Usage::

    python scripts/generate_file_manifest.py --version 0.5.0
    python scripts/generate_file_manifest.py --version 0.5.0 --compare-to 0.4.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def _is_distributable(rel: Path) -> bool:
    """Return True if this path should appear in the distribution manifest."""
    parts = rel.parts
    # Exclude quill/tools/ subtree
    if len(parts) >= 2 and parts[0] == "quill" and parts[1] == "tools":
        return False
    # Exclude __pycache__ anywhere in path
    if "__pycache__" in parts:
        return False
    suffix = rel.suffix.lower()
    if suffix in {".pyc", ".pyo"}:
        return False
    return True


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_files(
    source_root: Path,
    install_prefix: str,
) -> list[dict[str, object]]:
    """Return a sorted list of manifest file entries."""
    quill_root = source_root / "quill"
    entries: list[dict[str, object]] = []
    for fpath in sorted(quill_root.rglob("*")):
        if not fpath.is_file():
            continue
        rel = fpath.relative_to(source_root)
        if not _is_distributable(rel):
            continue
        install_path = install_prefix.rstrip("/") + "/" + rel.as_posix()
        entries.append({
            "path": rel.as_posix(),
            "install_path": install_path,
            "sha256": _sha256(fpath),
            "size": fpath.stat().st_size,
        })
    return entries


def load_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_manifests(
    old: dict[str, object],
    new: list[dict[str, object]],
) -> dict[str, object]:
    """Return a diff summary between an old manifest and new file list."""
    old_files: dict[str, dict[str, object]] = {
        str(f["path"]): f  # type: ignore[index]
        for f in old.get("files", [])  # type: ignore[union-attr]
    }
    new_files: dict[str, dict[str, object]] = {str(f["path"]): f for f in new}

    changed: list[str] = []
    added: list[str] = []
    deleted: list[str] = []

    for path, entry in new_files.items():
        if path not in old_files:
            added.append(path)
        elif old_files[path]["sha256"] != entry["sha256"]:
            changed.append(path)

    for path in old_files:
        if path not in new_files:
            deleted.append(path)

    old_size = sum(int(f.get("size", 0)) for f in old_files.values())  # type: ignore[arg-type]
    new_size = sum(int(f.get("size", 0)) for f in new_files.values())  # type: ignore[arg-type]

    return {
        "changed": sorted(changed),
        "added": sorted(added),
        "deleted": sorted(deleted),
        "size_delta_bytes": new_size - old_size,
    }


def normalize_version(version: str) -> str:
    """Strip the git-tag ``v`` prefix so ``v1.0.0`` and ``1.0.0`` are one version.

    CI passes ``github.ref_name`` (e.g. ``v1.0.0``) while manual runs pass the
    plain version; without normalization the two produce differently named
    manifests and the update tooling cannot find its own prior output.
    """
    return version.strip().removeprefix("v").removeprefix("V")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a SHA-256 file manifest for distributable Quill files."
    )
    parser.add_argument("--version", required=True, help="Release version (e.g. 0.5.0)")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("."),
        help="Repository root directory (default: current directory).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output manifest path. Defaults to docs/site/updates/manifests/manifest-{version}.json"
        ),
    )
    parser.add_argument(
        "--install-prefix",
        default="python/Lib/site-packages",
        help="Install prefix prepended to each file's install_path.",
    )
    parser.add_argument(
        "--compare-to",
        metavar="VERSION",
        default=None,
        help="Load an existing manifest for VERSION and print a diff summary.",
    )
    args = parser.parse_args()

    source_root: Path = args.source_root.resolve()
    version: str = normalize_version(args.version)
    output: Path = args.output or (
        source_root / "docs" / "site" / "updates" / "manifests" / f"manifest-{version}.json"
    )

    entries = scan_files(source_root, args.install_prefix)

    manifest: dict[str, object] = {
        "version": version,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "install_prefix": args.install_prefix,
        "files": entries,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    total_size = sum(int(e["size"]) for e in entries)  # type: ignore[arg-type]
    print(f"Manifest written to {output}")
    print(f"  Files: {len(entries)}  Total size: {total_size:,} bytes")

    if args.compare_to:
        compare_path = (
            source_root
            / "docs"
            / "site"
            / "updates"
            / "manifests"
            / f"manifest-{args.compare_to}.json"
        )
        if not compare_path.exists():
            print(f"WARNING: base manifest not found at {compare_path} -- skipping diff")
        else:
            old_manifest = load_manifest(compare_path)
            diff = compare_manifests(old_manifest, entries)
            delta_kb = diff["size_delta_bytes"] / 1024  # type: ignore[operator]
            print(
                f"\nDiff vs {args.compare_to}:"
                f"  changed={len(diff['changed'])}"  # type: ignore[arg-type]
                f"  added={len(diff['added'])}"  # type: ignore[arg-type]
                f"  deleted={len(diff['deleted'])}"  # type: ignore[arg-type]
                f"  size_delta={delta_kb:+.1f} KB"
            )
            for label, items in [
                ("Changed", diff["changed"]),
                ("Added", diff["added"]),
                ("Deleted", diff["deleted"]),
            ]:
                if items:
                    print(f"  {label}:")
                    for item in items:  # type: ignore[union-attr]
                        print(f"    {item}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
