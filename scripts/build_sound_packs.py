"""Package the bundled sound packs into distributable ``.qsp`` files.

Each pack directory under ``quill/assets/sound_packs/`` (one holding a
``manifest.json`` plus its WAV files) is zipped into a single ``<name>.qsp``
archive with the manifest and audio at the archive root, which is exactly the
layout the QSP loader expects. A ``SHA256SUMS`` file is written alongside so
downloads can be verified.

Usage::

    python scripts/build_sound_packs.py
    python scripts/build_sound_packs.py --out dist/sound-packs

The produced ``.qsp`` files are distribution artifacts (not committed); upload
them to the release or the GitHub Pages site so users can install custom packs
via Preferences -> Sound.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PACKS_DIR = _REPO_ROOT / "quill" / "assets" / "sound_packs"


def _pack_dirs() -> list[Path]:
    return sorted(p for p in _PACKS_DIR.iterdir() if p.is_dir() and (p / "manifest.json").is_file())


def _build_one(pack_dir: Path, out_dir: Path) -> Path:
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    name = str(manifest.get("name") or pack_dir.name).strip().replace(" ", "_").lower()
    target = out_dir / f"{name}.qsp"
    # Deterministic archive: sorted members, fixed metadata.
    members = sorted(p for p in pack_dir.iterdir() if p.is_file())
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for member in members:
            zf.write(member, arcname=member.name)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Package bundled sound packs into .qsp files.")
    parser.add_argument(
        "--out",
        default=str(_REPO_ROOT / "dist" / "sound-packs"),
        help="Output directory for the .qsp files (default: dist/sound-packs).",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    built: list[Path] = []
    for pack_dir in _pack_dirs():
        target = _build_one(pack_dir, out_dir)
        built.append(target)
        print(f"  built {target.name} from {pack_dir.name}/")

    if not built:
        print("No sound packs found.")
        return 1

    sums = out_dir / "SHA256SUMS"
    lines = []
    for path in built:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(built)} pack(s) and {sums.name} to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
