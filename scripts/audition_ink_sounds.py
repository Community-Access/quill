"""Audition the Ink pack's audio-identity earcons, family by family.

Plays each new sound synchronously with a short gap, printing its name first
so the sequence can be followed in the console. Windows-only (winsound).

    python scripts/audition_ink_sounds.py            # the new identity set
    python scripts/audition_ink_sounds.py --all      # every sound in the pack
"""

from __future__ import annotations

import json
import sys
import time
import winsound
from pathlib import Path

PACK = Path(__file__).parent.parent / "quill" / "assets" / "sound_packs" / "ink"

IDENTITY_TOUR: list[tuple[str, list[str]]] = [
    (
        "Copy tray slots 1 to 12 (marimba taps up the pentatonic)",
        [f"copy_slot_{n}" for n in range(1, 13)],
    ),
    (
        "Quick bookmark slots 0 to 9 (triangle chirps, same scale)",
        [f"bookmark_slot_{n}" for n in range(10)],
    ),
    (
        "Progress ladder, 5 to 100 percent (quarters carry a fifth; 100 resolves)",
        [f"progress_{pct}" for pct in range(5, 101, 5)],
    ),
    ("Progress heartbeat (indeterminate)", ["progress_tick", "progress_tick", "progress_tick"]),
    (
        "Selection started, then completed (a mirrored gate)",
        [
            "selection_started",
            "selection_completed",
        ],
    ),
    (
        "Top of document (ceiling tick), end of document (floor thud)",
        [
            "document_top",
            "document_bottom",
        ],
    ),
    ("Possible misspelling (spell check as you type)", ["spelling_alert"]),
]


def main() -> int:
    events: dict[str, str] = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))[
        "events"
    ]
    if "--all" in sys.argv:
        tour = [("Every sound in the Ink pack", sorted(set(events)))]
    else:
        tour = IDENTITY_TOUR
    for family, ids in tour:
        print()
        print(family)
        time.sleep(0.6)
        for event_id in ids:
            filename = events.get(event_id)
            if not filename:
                print(f"  {event_id}: not in the manifest")
                continue
            print(f"  {event_id}")
            winsound.PlaySound(str(PACK / filename), winsound.SND_FILENAME)
            time.sleep(0.35)
    print()
    print("Audition complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
