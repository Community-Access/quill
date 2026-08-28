"""Settings-documented gate (GATE-SETDOC): every setting is findable in docs.

EdSharp's ``checkOptionsDocumented``, imported 2026-08-27: *"every setting
appears in the documentation -- an undocumented setting is one nobody can
find."* QUILL had the two halves and no bridge: a schema-validated
``Settings`` dataclass on one side, ``check_help_coverage`` for help topics
on the other, and nothing tying a settings *field* to a place a user could
read about it.

Every field of :class:`quill.core.settings.Settings` gets one status in the
committed snapshot (``tests/unit/ui/fixtures/settings_doc_inventory.json``):

* ``documented``    -- found in the documentation corpus (auto-verified on
  every run: the user guide, the help topics, and the docs tree). If the
  docs stop mentioning it, the gate fails until they do again or the field
  is reclassified.
* ``internal``      -- not a user-facing option (caches, timestamps,
  one-shot migration flags, "have we shown this notice" latches). A
  reviewed classification: justify it in the diff.
* ``grandfathered`` -- undocumented and shipped before this gate existed
  (2026-08-27). A ratchet: this set may only shrink -- document the setting
  or reclassify it ``internal``; a field can never *become* grandfathered.
* ``missing``       -- new, undocumented, unclassified. **Fails the build**:
  a new setting cannot ship without either documentation or a deliberate
  ``internal`` classification.

Documented-ness is judged by finding the field's name (verbatim,
backticked, or with underscores read as spaces) in the corpus -- coarse on
purpose: the point is "can a person searching the docs find anything at
all", not prose quality.

Regenerate after adding fields or docs::

    python -m quill.tools.settings_doc_audit --write

and review the diff; every ``missing`` you commit is a failing build.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

SNAPSHOT_PATH = _REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "settings_doc_inventory.json"

DOCUMENTED = "documented"
INTERNAL = "internal"
GRANDFATHERED = "grandfathered"
MISSING = "missing"
STATUSES = frozenset({DOCUMENTED, INTERNAL, GRANDFATHERED, MISSING})

#: Where a user can plausibly find a setting explained.
_CORPUS_PATHS = (
    "docs/user guide/userguide.md",
    "quill/core/help/topics.json",
)
_CORPUS_GLOBS = (
    "docs/apps/*.md",
    "docs/Product Requirement Documents and Specifications/*.md",
)


def setting_fields() -> list[str]:
    from quill.core.settings import Settings

    return [field.name for field in dataclasses.fields(Settings)]


@lru_cache(maxsize=1)
def _corpus() -> str:
    chunks: list[str] = []
    paths = [_REPO_ROOT / rel for rel in _CORPUS_PATHS]
    for pattern in _CORPUS_GLOBS:
        paths.extend(sorted(_REPO_ROOT.glob(pattern)))
    for path in paths:
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="replace").lower())
    return "\n".join(chunks)


def is_documented(field_name: str) -> bool:
    corpus = _corpus()
    lowered = field_name.lower()
    if lowered in corpus:
        return True
    spaced = lowered.replace("_", " ")
    return bool(re.search(r"\b" + re.escape(spaced) + r"\b", corpus))


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items()}


def build_snapshot(committed: dict[str, str]) -> dict[str, str]:
    """The live snapshot: auto-verify ``documented``, keep classifications.

    * A field the corpus documents is ``documented`` regardless of history --
      documentation wins, and the ratchet shrinks by itself.
    * A field the corpus does not document keeps its committed ``internal``
      or ``grandfathered`` classification.
    * Anything else -- new field, or a formerly documented field the docs
      dropped -- is ``missing``.
    * Fields that left the dataclass leave the snapshot.
    """
    live: dict[str, str] = {}
    for name in setting_fields():
        if is_documented(name):
            live[name] = DOCUMENTED
        elif committed.get(name) in (INTERNAL, GRANDFATHERED):
            live[name] = committed[name]
        else:
            live[name] = MISSING
    return dict(sorted(live.items()))


def write_snapshot(snapshot: dict[str, str], path: Path = SNAPSHOT_PATH) -> None:
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="regenerate the snapshot")
    args = parser.parse_args(argv)

    committed = load_snapshot()
    live = build_snapshot(committed)
    if args.write:
        write_snapshot(live)
        print(f"wrote {SNAPSHOT_PATH.relative_to(_REPO_ROOT)}")
    counts: dict[str, int] = {}
    for status in live.values():
        counts[status] = counts.get(status, 0) + 1
    print(", ".join(f"{status}: {count}" for status, count in sorted(counts.items())))
    missing = sorted(name for name, status in live.items() if status == MISSING)
    if missing:
        print("missing documentation or classification:")
        for name in missing:
            print(f"  {name}")
        return 1
    if not args.write and live != committed:
        print("snapshot has drifted; run: python -m quill.tools.settings_doc_audit --write")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
