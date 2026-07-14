"""Generate verification text files by back-translating a golden BRF sample.

For every profile in brf_profiles.json that supports brf-to-text, run the
back-translation and save the output.  The resulting files serve as a
regression corpus: if a future table update changes the back-translation of a
known BRF file, the diff is immediately visible.

Usage::

    python scripts/generate_braille_table_tests.py \\
        --pack-dir liblouis/vendor/braille/pack \\
        --brf-sample liblouis/one_crazy_night.brf \\
        --out-dir liblouis/tests/table_verification
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def translate_brf_to_text(
    exe: Path,
    tables_dir: Path,
    profile: dict[str, Any],
    brf_file: Path,
    prof_id: str,
) -> str | None:
    if "brf-to-text" not in profile.get("direction", []):
        return None
    try:
        os.environ["LOUIS_TABLEPATH"] = str(tables_dir)
        t_name = profile["translation_table"].replace("tables/", "")
        d_name = profile["display_table"].replace("tables/", "")
        with open(brf_file, encoding="utf-8", errors="ignore") as f_in:
            result = subprocess.run(
                [str(exe), "-b", "-d", d_name, t_name],
                input=f_in.read(),
                capture_output=True,
                text=True,
                timeout=10,
            )
        if result.returncode != 0:
            print(f"  Error for {prof_id}: {result.stderr.strip()}")
            return None
        return result.stdout or None
    except Exception as exc:
        print(f"  Exception for {prof_id}: {exc}")
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate braille table verification tests.")
    parser.add_argument(
        "--pack-dir",
        type=Path,
        default=Path("liblouis/vendor/braille/pack"),
        help="Directory containing lou_translate.exe, tables/, and brf_profiles.json",
    )
    parser.add_argument(
        "--brf-sample",
        type=Path,
        default=Path("liblouis/one_crazy_night.brf"),
        help="BRF file to back-translate for all profiles",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("liblouis/tests/table_verification"),
        help="Directory to write per-profile back-translation text files",
    )
    args = parser.parse_args(argv)

    pack_dir: Path = args.pack_dir
    brf_sample: Path = args.brf_sample
    out_dir: Path = args.out_dir

    profiles_file = pack_dir / "brf_profiles.json"
    exe = pack_dir / "lou_translate.exe"
    tables_dir = pack_dir / "tables"

    if not profiles_file.exists():
        print(f"Error: brf_profiles.json not found at {profiles_file}")
        print("Run scripts/build_braille_pack.py first to generate it.")
        return 1
    if not brf_sample.exists():
        print(f"Error: BRF sample not found at {brf_sample}")
        return 1
    if not exe.exists():
        print(f"Error: lou_translate.exe not found at {exe}")
        return 1

    with open(profiles_file, encoding="utf-8") as f:
        data = json.load(f)
    profiles: list[dict[str, Any]] = data.get("profiles", [])

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating tests using {brf_sample.name} ({len(profiles)} profiles)...")

    success_count = 0
    skip_count = 0
    for prof in profiles:
        prof_id = prof["id"]
        if "brf-to-text" not in prof.get("direction", []):
            skip_count += 1
            continue
        text = translate_brf_to_text(exe, tables_dir, prof, brf_sample, prof_id)
        if text and text.strip():
            out_file = out_dir / f"{prof_id}.txt"
            out_file.write_text(text, encoding="utf-8")
            print(f"  OK: {prof_id}")
            success_count += 1
        else:
            print(f"  FAIL: {prof_id}")

    eligible = len(profiles) - skip_count
    print(f"\nDone. {success_count}/{eligible} back-translatable profiles verified.")
    print(f"Tests written to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
