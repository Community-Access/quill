"""Keep ``quill/core/data/family_menu_chords.json`` equal to the source it is read from.

The keys written into menu labels and row tables are found by scanning the
source (:func:`quill.core.family_chords.scan_menu_chords`). An installed build
has no source, so the Show and Hide Key picker reads this committed copy
instead -- and a copy nobody regenerates is a picker that happily accepts a key
added last week. ``tests/unit/ui/test_global_hotkeys.py`` fails on drift.

    python -m quill.tools.family_chords_snapshot            # check
    python -m quill.tools.family_chords_snapshot --write    # regenerate
"""

from __future__ import annotations

import argparse
import json
import sys

from quill.core.family_chords import (
    SNAPSHOT_PATH,
    SNAPSHOT_SCHEMA,
    FamilyChord,
    scan_menu_chords,
)


def rendered(chords: list[FamilyChord] | None = None) -> str:
    """The snapshot file's text, as a fresh scan would write it: one row a line,
    so a diff shows exactly which key appeared or went."""
    rows = [
        json.dumps([item.app, item.where, item.chord], ensure_ascii=False)
        for item in (scan_menu_chords() if chords is None else chords)
    ]
    body = ",\n".join(f"  {row}" for row in rows)
    return f'{{\n "schema": {SNAPSHOT_SCHEMA},\n "rows": [\n{body}\n ]\n}}\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="regenerate the snapshot")
    args = parser.parse_args(argv)
    fresh = rendered()
    if args.write:
        SNAPSHOT_PATH.write_bytes(fresh.encode("utf-8"))
        print(f"Wrote {SNAPSHOT_PATH.name}.")
        return 0
    current = SNAPSHOT_PATH.read_bytes().decode("utf-8") if SNAPSHOT_PATH.exists() else ""
    if current == fresh:
        print("Family menu keys: the snapshot matches the source.")
        return 0
    print(
        "Family menu keys: the snapshot is stale. Run "
        "python -m quill.tools.family_chords_snapshot --write"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
