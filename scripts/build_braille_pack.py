"""Build a signed-ready QUILL Universal Braille Pack archive.

This script implements the three-layer architecture:
1. Layer 1 (Files): Vendored runtime and all table files.
2. Layer 2 (Catalog): Machine-readable inventory of every table file (tables_catalog.json).
3. Layer 3 (Profiles): User-facing translation profiles mapped to tables (brf_profiles.json).

The script also smoke-tests each profile using lou_translate.exe and writes a
manifest.json for verification. The catalog and profiles are written back into the
input directory so they are included in the archive and in the portable staging step.

Usage::

    python scripts/build_braille_pack.py \\
        --input liblouis/vendor/braille/pack \\
        --version 1.0.0 \\
        --liblouis 3.38.0 \\
        --platform win64 \\
        --out dist

Then pass the same directory to build_windows_distribution.py::

    python scripts/build_windows_distribution.py \\
        --braille-pack-dir liblouis/vendor/braille/pack ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from typing import Any

MANIFEST_NAME = "manifest.json"
CATALOG_NAME = "tables_catalog.json"
PROFILES_NAME = "brf_profiles.json"
DEFAULT_DISPLAY_TABLE = "tables/en-us-brf.dis"
SMOKE_TEST_STRING = "Hello Braille World"

CAT_REC_ENG = "Recommended English"
CAT_LEG_ENG = "Legacy English"
CAT_INTL = "Other languages"
CAT_ADV = "Advanced / technical"

STAT_REC = "recommended"
STAT_AVAIL = "available"
STAT_LEG = "legacy"
STAT_ADV = "advanced"
STAT_FAIL = "failed"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_metadata(path: Path) -> dict[str, str]:
    """Extract liblouis table metadata from comment headers."""
    meta: dict[str, str] = {}
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("#+"):
                    parts = line[2:].strip().split(":", 1)
                    if len(parts) == 2:
                        meta[parts[0].strip()] = parts[1].strip()
                elif line.startswith("#-"):
                    parts = line[2:].strip().split(":", 1)
                    if len(parts) == 2:
                        meta[parts[0].strip()] = parts[1].strip()
                if not line.startswith("#"):
                    break
    except Exception:
        pass
    return meta


def classify_table(path: Path, meta: dict[str, str]) -> str:
    """Classify a table file as display, support, translation, or unknown."""
    ext = path.suffix
    if ext == ".dis":
        return "display"
    if ext in (".uti", ".cti", ".dic") or meta.get("type") == "computer":
        return "support"
    if meta.get("type") == "literary":
        return "translation"
    if ext in (".ctb", ".utb", ".tbl"):
        return "translation"
    return "unknown"


def smoke_test(exe: Path, tables_dir: Path, translation_table: str, display_table: str) -> bool:
    """Verify a profile produces non-empty output via lou_translate."""
    try:
        t_path = (tables_dir / translation_table.replace("tables/", "")).absolute()
        d_path = (tables_dir / display_table.replace("tables/", "")).absolute()
        result = subprocess.run(
            [str(exe), "-f", f"{t_path},{d_path}"],
            input=SMOKE_TEST_STRING,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False
        return bool(result.stdout.strip())
    except Exception:
        return False


def build_pack(
    input_dir: Path,
    out_dir: Path,
    *,
    version: str,
    liblouis_version: str,
    platform: str,
    skip_smoke: bool = False,
) -> tuple[Path, str]:
    """Build the Universal BRF Pack: generate catalog + profiles, then zip."""
    if not input_dir.is_dir():
        raise SystemExit(f"input directory not found: {input_dir}")

    tables_dir = input_dir / "tables"
    if not tables_dir.is_dir():
        raise SystemExit(f"tables directory not found: {input_dir}/tables")

    exe = input_dir / "lou_translate.exe"
    if not exe.exists() and not skip_smoke:
        raise SystemExit(
            f"lou_translate.exe not found in {input_dir}; use --skip-smoke to skip tests"
        )

    # --- Layer 2: tables catalog ---
    catalog_entries: list[dict[str, Any]] = []
    translation_files: list[dict[str, Any]] = []

    for p in sorted(tables_dir.rglob("*")):
        if p.is_dir():
            continue
        rel_path = "tables/" + p.relative_to(tables_dir).as_posix()
        meta = extract_metadata(p)
        kind = classify_table(p, meta)
        entry: dict[str, Any] = {
            "file": rel_path,
            "kind": kind,
            "selectable_as_brf_profile": (kind == "translation"),
            "language": meta.get("language", "unknown"),
            "type": meta.get("type", "unknown"),
            "grade": meta.get("grade", "unknown"),
            "contraction": meta.get("contraction", "unknown"),
            "dots": meta.get("dots", "6"),
            "display_name": meta.get("display-name") or meta.get("index-name") or p.stem,
        }
        catalog_entries.append(entry)
        if kind == "translation":
            translation_files.append(entry)

    catalog: dict[str, Any] = {
        "catalog": "quill-liblouis-table-inventory",
        "version": 1,
        "entries": catalog_entries,
    }
    (input_dir / CATALOG_NAME).write_text(
        json.dumps(catalog, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"Wrote {CATALOG_NAME} ({len(catalog_entries)} entries)")

    # --- Layer 3: user-facing BRF profiles ---
    profiles: list[dict[str, Any]] = []

    eng_mappings: list[dict[str, Any]] = [
        {
            "id": "en-ueb-g2-brf",
            "name": "Unified English Braille, contracted BRF",
            "aliases": ["UEB Grade 2", "contracted UEB"],
            "language": "English",
            "language_code": "en",
            "region": "International English",
            "category": CAT_REC_ENG,
            "status": STAT_REC,
            "translation_table": "tables/en-ueb-g2.ctb",
            "display_table": DEFAULT_DISPLAY_TABLE,
            "direction": ["text-to-brf", "brf-to-text"],
            "description": "Recommended default for modern English BRF.",
        },
        {
            "id": "en-ueb-g1-brf",
            "name": "Unified English Braille, uncontracted BRF",
            "aliases": ["UEB Grade 1", "uncontracted UEB"],
            "language": "English",
            "language_code": "en",
            "region": "International English",
            "category": CAT_REC_ENG,
            "status": STAT_REC,
            "translation_table": "tables/en-ueb-g1.ctb",
            "display_table": DEFAULT_DISPLAY_TABLE,
            "direction": ["text-to-brf", "brf-to-text"],
            "description": "Useful for learners, proofreading, and exact text review.",
        },
        {
            "id": "en-us-legacy-g2-brf",
            "name": "American English Braille, legacy contracted BRF",
            "aliases": ["pre-UEB Grade 2", "standard American Grade 2"],
            "language": "English",
            "language_code": "en",
            "region": "United States",
            "category": CAT_LEG_ENG,
            "status": STAT_LEG,
            "translation_table": "tables/en-us-g2.ctb",
            "display_table": DEFAULT_DISPLAY_TABLE,
            "direction": ["text-to-brf", "brf-to-text"],
            "description": "For users who prefer pre-UEB American English contracted braille.",
        },
        {
            "id": "en-us-legacy-g1-brf",
            "name": "American English Braille, legacy uncontracted BRF",
            "aliases": ["pre-UEB Grade 1", "standard American Grade 1"],
            "language": "English",
            "language_code": "en",
            "region": "United States",
            "category": CAT_LEG_ENG,
            "status": STAT_LEG,
            "translation_table": "tables/en-us-g1.ctb",
            "display_table": DEFAULT_DISPLAY_TABLE,
            "direction": ["text-to-brf", "brf-to-text"],
            "description": "Pre-UEB American English uncontracted braille.",
        },
    ]

    for p in eng_mappings:
        ok = (not skip_smoke and exe.exists()) and smoke_test(
            exe, tables_dir, p["translation_table"], p["display_table"]
        )
        if not ok and not skip_smoke:
            p = dict(p)
            p["status"] = STAT_FAIL
        profiles.append(p)

    known_tables = {p["translation_table"] for p in eng_mappings}
    for tf in translation_files:
        if tf["file"] in known_tables:
            continue
        if tf["type"] == "literary" and tf["dots"] == "6":
            prof_id = tf["file"].replace("/", "-").replace(".", "-") + "-brf"
            prof: dict[str, Any] = {
                "id": prof_id,
                "name": f"{tf['display_name']} BRF",
                "aliases": [tf["display_name"]],
                "language": tf["language"] if tf["language"] != "unknown" else "Unknown",
                "language_code": tf["language"] if len(tf["language"]) == 2 else "un",
                "region": "International",
                "category": CAT_INTL,
                "status": STAT_AVAIL,
                "translation_table": tf["file"],
                "display_table": DEFAULT_DISPLAY_TABLE,
                "direction": ["text-to-brf"],
                "description": f"BRF translation for {tf['display_name']}.",
            }
            if not skip_smoke and exe.exists():
                if not smoke_test(
                    exe, tables_dir, prof["translation_table"], prof["display_table"]
                ):
                    prof["status"] = STAT_FAIL
            profiles.append(prof)

    profile_catalog: dict[str, Any] = {
        "catalog": "quill-brf-profiles",
        "version": 1,
        "default_profile": "en-ueb-g2-brf",
        "profiles": profiles,
    }
    (input_dir / PROFILES_NAME).write_text(
        json.dumps(profile_catalog, indent=2, sort_keys=True), encoding="utf-8"
    )
    passed = sum(1 for p in profiles if p.get("status") != STAT_FAIL)
    print(f"Wrote {PROFILES_NAME} ({passed}/{len(profiles)} profiles passed smoke tests)")

    # --- Manifest ---
    files_to_pack = sorted(p for p in input_dir.rglob("*") if p.is_file())
    manifest: dict[str, Any] = {
        "pack": "quill-brf-universal-pack",
        "version": version,
        "liblouis_version": liblouis_version,
        "platform": platform,
        "files": {
            p.relative_to(input_dir).as_posix(): {
                "sha256": _sha256(p),
                "bytes": p.stat().st_size,
            }
            for p in files_to_pack
        },
    }
    (input_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    # --- ZIP ---
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"quill-brf-universal-pack-{version}-{platform}.zip"
    archive = out_dir / archive_name
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files_to_pack:
            zf.write(p, p.relative_to(input_dir).as_posix())

    sha = _sha256(archive)
    return archive, sha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a QUILL Universal Braille Pack archive.")
    parser.add_argument("--input", required=True, type=Path, help="vendored pack directory")
    parser.add_argument("--version", required=True, help="pack version, e.g. 1.0.0")
    parser.add_argument("--liblouis", required=True, help="bundled liblouis version")
    parser.add_argument("--platform", required=True, help="platform tag, e.g. win64")
    parser.add_argument("--out", type=Path, default=Path("dist"), help="output directory")
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="skip lou_translate smoke tests (useful on machines without the runtime)",
    )
    args = parser.parse_args(argv)

    archive, sha = build_pack(
        args.input,
        args.out,
        version=args.version,
        liblouis_version=args.liblouis,
        platform=args.platform,
        skip_smoke=args.skip_smoke,
    )
    print(f"Built {archive}")
    print(f"SHA-256 {sha}")
    print("Pin this SHA-256 in quill.core.braille_pack and publish the archive as a release asset.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
