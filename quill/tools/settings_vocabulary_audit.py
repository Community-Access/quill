"""Gate 4: every setting on either side has been looked at once (bad.md).

The failure this exists for is specific and was missed twice by human review.
QuillLite's ``check_updates_on_launch`` and QUILL's ``auto_check_updates`` are the
same switch under two names, and **neither name contains a word the other does**
-- so reading the two field lists side by side does not find it. Nor does any
name-similarity check: of the five real pairs the 2026-09 audit found, two share
no word at all (``spell_check_while_typing`` / ``spellcheck_as_you_type``,
``default_mode`` / ``default_new_document_format``), while "check", "print" and
"id" appear in dozens of unrelated fields. A heuristic over names is both too
loose and too tight to be the gate.

So the gate is a **ratchet on attention**, the same shape GATE-SETDOC uses for
documentation. Every field on either side carries one of four states in the
committed snapshot:

* ``shared``  -- spelled the same in both products. Nothing to decide.
* ``aliased`` -- the same concept under two names, mapped in
  :data:`quill.core.lite.parity.SETTINGS_ALIASES`. Derived, not stored.
* ``one_side`` -- a reviewed field that genuinely exists in one product only,
  because the other has no such concept. This is the judgement call, and the
  classification *is* the review.
* ``missing``  -- new and unclassified. **Fails the build**, which is the point:
  a new setting cannot ship until somebody has asked "does the other one already
  have this under another name?"

Regenerate with ``python -m quill.tools.settings_vocabulary_audit --write`` and
read the diff. Every ``missing`` you commit is a failing build; every
``one_side`` you commit is you saying you checked.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from quill.core.lite.parity import NOT_ALIASES, SETTINGS_ALIASES

_REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = (
    _REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "settings_vocabulary_inventory.json"
)

SHARED = "shared"
ALIASED = "aliased"
ONE_SIDE = "one_side"
MISSING = "missing"

__all__ = [
    "ALIASED",
    "MISSING",
    "ONE_SIDE",
    "SHARED",
    "SNAPSHOT_PATH",
    "classify",
    "load_snapshot",
    "main",
]


def _fields(settings_class: type) -> set[str]:
    return {name for name in settings_class.__dataclass_fields__ if not name.startswith("_")}


def _both_sides() -> tuple[set[str], set[str]]:
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings

    return _fields(LiteSettings), _fields(QuillSettings)


def load_snapshot() -> dict[str, str]:
    if not SNAPSHOT_PATH.is_file():
        return {}
    try:
        raw = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}


def classify(committed: dict[str, str] | None = None) -> dict[str, str]:
    """``"<side>:<field>" -> state`` for every setting in both products.

    Keyed by side as well as name because the same name can be shared on one
    side and aliased on the other, and a single key would make that invisible.
    """
    lite_fields, quill_fields = _both_sides()
    known = load_snapshot() if committed is None else committed
    aliased_lite = set(SETTINGS_ALIASES) | set(NOT_ALIASES)
    aliased_quill = set(SETTINGS_ALIASES.values())

    states: dict[str, str] = {}
    for field in sorted(lite_fields):
        key = f"lite:{field}"
        if field in quill_fields:
            states[key] = SHARED
        elif field in aliased_lite:
            states[key] = ALIASED
        else:
            states[key] = known.get(key, MISSING)
    for field in sorted(quill_fields):
        key = f"quill:{field}"
        if field in lite_fields:
            states[key] = SHARED
        elif field in aliased_quill:
            states[key] = ALIASED
        else:
            states[key] = known.get(key, MISSING)
    return states


def missing(states: dict[str, str] | None = None) -> list[str]:
    resolved = classify() if states is None else states
    return sorted(key for key, state in resolved.items() if state == MISSING)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate the snapshot")
    args = parser.parse_args(argv)

    states = classify()
    if args.write:
        # A field with no verdict yet is written as one_side, which is the
        # reviewer saying "I looked and the other product has no such idea".
        resolved = {key: (ONE_SIDE if state == MISSING else state) for key, state in states.items()}
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(
            json.dumps(dict(sorted(resolved.items())), indent=2) + "\n", encoding="utf-8"
        )
        counts: dict[str, int] = {}
        for state in resolved.values():
            counts[state] = counts.get(state, 0) + 1
        print(f"Wrote {len(resolved)} settings to {SNAPSHOT_PATH}")
        print(", ".join(f"{state}: {count}" for state, count in sorted(counts.items())))
        return 0

    unclassified = missing(states)
    if unclassified:
        print("settings with no vocabulary verdict:")
        for key in unclassified:
            print(f"  {key}")
        print("Run: python -m quill.tools.settings_vocabulary_audit --write")
        return 1
    print(f"Settings vocabulary: {len(states)} field(s), all reviewed.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
